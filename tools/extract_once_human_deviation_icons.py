#!/usr/bin/env python3
"""Extract Once Human deviation/pet icons from local game packs."""

from __future__ import annotations

import argparse
import json
import mmap
import struct
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import zstandard as zstd
from PIL import Image

try:
    import texture2ddecoder
except ImportError as exc:  # pragma: no cover - CLI dependency guard
    raise SystemExit(
        "texture2ddecoder is required for PVR decoding. Install it with: pip install texture2ddecoder"
    ) from exc


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.decompile_once_human import extract_payload, parse_npk


DEVIATIONS_JSON = REPO_ROOT / "data" / "menu" / "calc" / "bd_json" / "deviations.json"
DEVIATION_ICONS_ROOT = REPO_ROOT / "data" / "icons" / "deviations"
PVR_HEADER_STRUCT = struct.Struct("<13I")
PVR_VERSION = 0x03525650
MAX_OUTPUT_SIZE = 384


@dataclass(frozen=True)
class IconCandidate:
    pack_path: Path
    entry_name: str
    stem: str


def build_stem_variants(icon_asset: str) -> list[str]:
    stem = Path(str(icon_asset or "")).stem.lower()
    if not stem:
        return []
    variants = [stem]
    if stem.startswith("icon_"):
        variants.append(stem[5:])
    else:
        variants.append(f"icon_{stem}")
    return list(dict.fromkeys(variants))


def load_requested_icons(deviations_json: Path, *, combat_only: bool) -> list[dict[str, Any]]:
    payload = json.loads(deviations_json.read_text(encoding="utf-8"))
    requests: list[dict[str, Any]] = []
    for deviation in payload.get("deviations", []):
        icon_asset = str(deviation.get("icon_asset") or deviation.get("boss_icon_asset") or "").strip()
        deviation_id = str(deviation.get("id") or "").strip()
        if not deviation_id or not icon_asset:
            continue
        if combat_only and not deviation.get("is_combat"):
            continue
        stem_variants = build_stem_variants(icon_asset)
        if not stem_variants:
            continue
        requests.append(
            {
                "id": deviation_id,
                "name": deviation.get("name", ""),
                "display_name": ((deviation.get("localization") or {}).get("ru") or {}).get("name") or deviation.get("name", ""),
                "me_code": str(deviation.get("me_code") or "").lower(),
                "icon_asset": icon_asset,
                "stem_variants": stem_variants,
                "is_combat": bool(deviation.get("is_combat")),
            }
        )
    return requests


def score_candidate(request: dict[str, Any], candidate: IconCandidate) -> float:
    entry_name = candidate.entry_name.casefold()
    exact_stem = request["stem_variants"][0]
    score = 0.0
    if candidate.stem == exact_stem:
        score += 40.0
    if candidate.stem in request["stem_variants"]:
        score += 22.0
    me_code = request.get("me_code", "")
    if me_code and me_code in candidate.stem:
        score += 8.0

    if "\\containment_icon\\" in entry_name:
        score += 12.0
    elif "\\containment_icon_2\\" in entry_name:
        score += 9.0
    elif "\\containment_icon_3\\" in entry_name:
        score += 7.0
    elif "\\season_activity\\" in entry_name:
        score -= 4.0

    if "share_" in entry_name:
        score -= 10.0
    if any(marker in entry_name for marker in ("fashion", "skin", "_sp", "season_activity")):
        score -= 8.0
    if candidate.stem.count("_") > exact_stem.count("_"):
        score -= 1.0
    return score


def scan_icon_candidates(game_path: Path, requests: list[dict[str, Any]]) -> tuple[dict[str, list[IconCandidate]], dict[str, list[IconCandidate]], list[int]]:
    requested_stems = {stem for request in requests for stem in request["stem_variants"]}
    requested_me_codes = {request["me_code"] for request in requests if request.get("me_code")}
    by_stem: dict[str, list[IconCandidate]] = defaultdict(list)
    by_me_code: dict[str, list[IconCandidate]] = defaultdict(list)
    scanned_pack_ids: list[int] = []

    for pack_path in sorted(game_path.glob("res_normal_pack_*.npk")):
        suffix = pack_path.stem.rsplit("_", 1)[-1]
        if suffix.isdigit():
            scanned_pack_ids.append(int(suffix))
        with pack_path.open("rb") as handle, mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ) as data:
            try:
                entries = parse_npk(data, pack_path)
            except Exception:
                continue
            for entry in entries:
                lower_name = entry.name.casefold()
                if not lower_name.endswith(".pvr"):
                    continue
                if (
                    "containment_icon" not in lower_name
                    and "season_activity" not in lower_name
                    and "boss_head" not in lower_name
                ):
                    continue
                stem = Path(entry.name).stem.casefold()
                relevant_me_codes = [me_code for me_code in requested_me_codes if me_code and me_code in stem]
                if stem not in requested_stems and not relevant_me_codes:
                    continue
                candidate = IconCandidate(pack_path=pack_path, entry_name=entry.name, stem=stem)
                if stem in requested_stems:
                    by_stem[stem].append(candidate)
                for me_code in relevant_me_codes:
                    by_me_code[me_code].append(candidate)
    return by_stem, by_me_code, scanned_pack_ids


def choose_icon_candidate(
    request: dict[str, Any],
    by_stem: dict[str, list[IconCandidate]],
    by_me_code: dict[str, list[IconCandidate]],
) -> IconCandidate | None:
    candidates: list[IconCandidate] = []
    for stem in request["stem_variants"]:
        candidates.extend(by_stem.get(stem, []))
    if not candidates and request.get("me_code"):
        candidates.extend(by_me_code.get(request["me_code"], []))
    if not candidates:
        return None
    ranked = sorted(
        {candidate: score_candidate(request, candidate) for candidate in candidates}.items(),
        key=lambda item: item[1],
        reverse=True,
    )
    return ranked[0][0]


def decode_pvr_image(payload: bytes) -> Image.Image:
    if len(payload) < PVR_HEADER_STRUCT.size:
        raise RuntimeError("PVR payload is too small to contain a valid header.")
    header = PVR_HEADER_STRUCT.unpack(payload[: PVR_HEADER_STRUCT.size])
    version, _, pixel_format_low, pixel_format_high, _, _, height, width, _, _, _, _, metadata_size = header
    if version != PVR_VERSION:
        raise RuntimeError(f"Unsupported PVR version: 0x{version:08x}")
    if pixel_format_high != 0:
        raise RuntimeError(f"Unsupported 64-bit PVR pixel format: {pixel_format_high}:{pixel_format_low}")

    image_data = payload[PVR_HEADER_STRUCT.size + metadata_size :]
    if pixel_format_low == 11:
        rgba = texture2ddecoder.decode_bc3(image_data, width, height)
    elif pixel_format_low == 7:
        rgba = texture2ddecoder.decode_bc1(image_data, width, height)
    elif pixel_format_low == 6:
        rgba = texture2ddecoder.decode_etc1(image_data, width, height)
    elif pixel_format_low == 23:
        rgba = texture2ddecoder.decode_etc2a8(image_data, width, height)
    else:
        raise RuntimeError(f"Unsupported deviation icon pixel format: {pixel_format_low}")

    image = Image.frombytes("RGBA", (width, height), rgba)
    alpha = image.getchannel("A")
    bbox = alpha.getbbox()
    if bbox:
        left, top, right, bottom = bbox
        padding = 4
        bbox = (
            max(0, left - padding),
            max(0, top - padding),
            min(image.width, right + padding),
            min(image.height, bottom + padding),
        )
        image = image.crop(bbox)
    if max(image.size) > MAX_OUTPUT_SIZE:
        image.thumbnail((MAX_OUTPUT_SIZE, MAX_OUTPUT_SIZE), Image.LANCZOS)
    return image


def extract_icons(
    requests: list[dict[str, Any]],
    by_stem: dict[str, list[IconCandidate]],
    by_me_code: dict[str, list[IconCandidate]],
    output_dir: Path,
) -> tuple[int, list[dict[str, Any]]]:
    selected: dict[str, IconCandidate] = {}
    missing: list[dict[str, Any]] = []
    for request in requests:
        candidate = choose_icon_candidate(request, by_stem, by_me_code)
        if candidate is None:
            missing.append(
                {
                    "id": request["id"],
                    "name": request["name"],
                    "display_name": request["display_name"],
                    "icon_asset": request["icon_asset"],
                    "me_code": request["me_code"],
                }
            )
            continue
        selected[request["id"]] = candidate

    grouped_requests: dict[Path, list[tuple[str, IconCandidate]]] = defaultdict(list)
    for deviation_id, candidate in selected.items():
        grouped_requests[candidate.pack_path].append((deviation_id, candidate))

    output_dir.mkdir(parents=True, exist_ok=True)
    synced = 0
    for pack_path, entries in grouped_requests.items():
        wanted_names = {candidate.entry_name for _, candidate in entries}
        with pack_path.open("rb") as handle, mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ) as data:
            archive_entries = {entry.name: entry for entry in parse_npk(data, pack_path) if entry.name in wanted_names}
            dctx = zstd.ZstdDecompressor()
            for deviation_id, candidate in entries:
                archive_entry = archive_entries.get(candidate.entry_name)
                if archive_entry is None:
                    missing.append(
                        {
                            "id": deviation_id,
                            "entry_name": candidate.entry_name,
                            "pack": str(pack_path),
                            "reason": "entry_missing_after_selection",
                        }
                    )
                    continue
                payload = extract_payload(data, archive_entry, dctx)
                image = decode_pvr_image(payload)
                output_path = output_dir / f"{deviation_id}.png"
                image.save(output_path)
                synced += 1
    return synced, missing


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-path", required=True, help="Path to the Once Human game root.")
    parser.add_argument("--deviations-json", default=str(DEVIATIONS_JSON), help="Path to deviations.json.")
    parser.add_argument("--output-dir", default=str(DEVIATION_ICONS_ROOT), help="Output directory for PNG icons.")
    parser.add_argument("--combat-only", action="store_true", help="Only extract icons for combat deviations.")
    parser.add_argument("--report", help="Optional JSON report path.")
    args = parser.parse_args()

    game_path = Path(args.game_path)
    deviations_json = Path(args.deviations_json)
    output_dir = Path(args.output_dir)
    if not game_path.exists():
        raise FileNotFoundError(f"Game path not found: {game_path}")
    if not deviations_json.exists():
        raise FileNotFoundError(f"deviations.json not found: {deviations_json}")

    requests = load_requested_icons(deviations_json, combat_only=args.combat_only)
    by_stem, by_me_code, scanned_pack_ids = scan_icon_candidates(game_path, requests)
    synced, missing = extract_icons(requests, by_stem, by_me_code, output_dir)

    summary = {
        "requested": len(requests),
        "synced": synced,
        "missing": len(missing),
        "combat_only": bool(args.combat_only),
        "scanned_packs": len(scanned_pack_ids),
        "output_dir": str(output_dir),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(
                {
                    "summary": summary,
                    "missing": missing,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
