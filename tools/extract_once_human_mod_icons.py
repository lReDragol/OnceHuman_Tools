#!/usr/bin/env python3
"""Extract real Once Human mod glyph icons from local game packs.

The calculator stores mod icons under `data/icons/mods/...` using human-readable
mod names. The game stores the same glyphs inside `res_normal_pack_*.npk`
archives as PVR textures with internal asset names.

This tool:
1. extracts `mods_icon_cbt2/*.pvr` files from known Once Human packs via QuickBMS
2. decompresses them to PNG via PVRTexToolCLI
3. matches them to existing calculator mod icons by hashing the alpha channel
4. overwrites the local icon files with the closest real game assets

It is intentionally conservative: files with a distance above the threshold are
left untouched and reported.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Iterable

from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[1]
MODS_CONFIG_PATH = REPO_ROOT / "data" / "menu" / "calc" / "bd_json" / "mods_config.json"
MOD_ICONS_ROOT = REPO_ROOT / "data" / "icons" / "mods"
DEFAULT_PACK_IDS = [112, 238, 268, 288, 304, 317, 319, 327]


def safe_display_filename(name: str) -> str:
    invalid = '<>:"/\\|?*'
    cleaned = "".join("_" if char in invalid else char for char in name).strip().rstrip(".")
    return cleaned or "unnamed"


def discover_temp_candidates(patterns: Iterable[str]) -> list[Path]:
    temp_dir = Path(tempfile.gettempdir())
    matches: list[Path] = []
    for pattern in patterns:
        matches.extend(path for path in temp_dir.glob(pattern) if path.exists())
    return sorted(matches, key=lambda path: path.stat().st_mtime, reverse=True)


def resolve_tool_path(explicit: str | None, label: str, patterns: Iterable[str]) -> Path:
    if explicit:
        path = Path(explicit)
        if not path.exists():
            raise FileNotFoundError(f"{label} not found: {path}")
        return path

    for candidate in discover_temp_candidates(patterns):
        return candidate

    found_on_path = shutil.which(label)
    if found_on_path:
        return Path(found_on_path)
    raise FileNotFoundError(f"Unable to locate {label}. Pass it explicitly via CLI arguments.")


def load_mod_entries() -> list[tuple[str, str]]:
    payload = json.loads(MODS_CONFIG_PATH.read_text(encoding="utf-8"))
    entries: list[tuple[str, str]] = []
    for mod_key, mods in payload.items():
        if not isinstance(mods, list):
            continue
        for mod in mods:
            name = mod.get("name")
            if name:
                entries.append((mod_key, name))
    return entries


def resolve_existing_icon_path(mod_key: str, mod_name: str) -> Path | None:
    canonical = MOD_ICONS_ROOT / mod_key / f"{safe_display_filename(mod_name)}.png"
    if canonical.exists():
        return canonical

    normalized = MOD_ICONS_ROOT / mod_key / f"{mod_name.lower().replace(' ', '_')}.png"
    if normalized.exists():
        return normalized
    return None


def alpha_hash(path: Path, hash_size: int = 16) -> tuple[int, ...]:
    with Image.open(path).convert("RGBA") as image:
        alpha = image.getchannel("A").resize((hash_size, hash_size), Image.Resampling.LANCZOS)
        pixels = list(alpha.getdata())
    if not pixels:
        return tuple()
    threshold = sum(pixels) / len(pixels)
    return tuple(1 if pixel >= threshold else 0 for pixel in pixels)


def hamming_distance(left: tuple[int, ...], right: tuple[int, ...]) -> int:
    return sum(left_bit != right_bit for left_bit, right_bit in zip(left, right))


def run_quickbms(quickbms: Path, bms_script: Path, game_path: Path, output_dir: Path, pack_ids: list[int]) -> list[Path]:
    extracted: list[Path] = []
    for pack_id in pack_ids:
        pack_path = game_path / f"res_normal_pack_{pack_id}.npk"
        if not pack_path.exists():
            continue
        command = [
            str(quickbms),
            "-q",
            "-o",
            "-f",
            "{}mods_icon_cbt2{}.pvr",
            str(bms_script),
            str(pack_path),
            str(output_dir),
        ]
        subprocess.run(command, check=True)
    extracted.extend(sorted(output_dir.rglob("*.pvr")))
    if not extracted:
        raise RuntimeError("No mod PVR files were extracted. Check the game path and pack ids.")
    return extracted


def convert_pvr_to_png(pvr_cli: Path, pvr_path: Path, extract_root: Path, png_root: Path) -> Path:
    relative_path = pvr_path.relative_to(extract_root).with_suffix(".png")
    output_path = png_root / relative_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [str(pvr_cli), "-i", str(pvr_path), "-d", str(output_path), "-noout", "-shh"]
    subprocess.run(command, check=True)
    return output_path


def build_reference_icon_list() -> list[Path]:
    seen: set[Path] = set()
    paths: list[Path] = []
    for mod_key, mod_name in load_mod_entries():
        path = resolve_existing_icon_path(mod_key, mod_name)
        if path and path not in seen:
            seen.add(path)
            paths.append(path)
    if not paths:
        raise RuntimeError("No existing mod icons were found under data/icons/mods.")
    return paths


def match_icons(reference_icons: list[Path], extracted_pngs: list[Path], max_distance: int) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    unique_extracted: dict[tuple[int, ...], Path] = {}
    for extracted_path in extracted_pngs:
        hashed = alpha_hash(extracted_path)
        if hashed and hashed not in unique_extracted:
            unique_extracted[hashed] = extracted_path

    extracted_pairs = list(unique_extracted.items())
    matched: list[dict[str, object]] = []
    skipped: list[dict[str, object]] = []

    for icon_path in reference_icons:
        icon_hash = alpha_hash(icon_path)
        best_distance: int | None = None
        best_source: Path | None = None
        for extracted_hash, extracted_path in extracted_pairs:
            distance = hamming_distance(icon_hash, extracted_hash)
            if best_distance is None or distance < best_distance:
                best_distance = distance
                best_source = extracted_path
                if distance == 0:
                    break

        result = {
            "target": str(icon_path),
            "source": str(best_source) if best_source else None,
            "distance": best_distance if best_distance is not None else -1,
        }
        if best_source is not None and best_distance is not None and best_distance <= max_distance:
            matched.append(result)
        else:
            skipped.append(result)
    return matched, skipped


def apply_matches(matched: list[dict[str, object]]) -> None:
    for entry in matched:
        source = Path(str(entry["source"]))
        target = Path(str(entry["target"]))
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-path", required=True, help="Path to the Once Human game root.")
    parser.add_argument("--quickbms", help="Path to quickbms.exe.")
    parser.add_argument("--bms-script", help="Path to Once_Human_Beta_NPK.bms.")
    parser.add_argument("--pvr-cli", help="Path to PVRTexToolCLI.exe.")
    parser.add_argument("--extract-dir", help="Temporary directory for extracted PVR files.")
    parser.add_argument("--png-dir", help="Temporary directory for converted PNG files.")
    parser.add_argument("--packs", help="Comma-separated pack ids. Default: known mod icon packs.")
    parser.add_argument("--max-distance", type=int, default=4, help="Maximum alpha-hash distance allowed for overwrite.")
    parser.add_argument("--workers", type=int, default=max(4, (os.cpu_count() or 8) // 2), help="Parallel conversion workers.")
    parser.add_argument("--dry-run", action="store_true", help="Only print the match summary.")
    parser.add_argument("--keep-temp", action="store_true", help="Do not delete temporary extraction folders.")
    parser.add_argument("--report", help="Optional JSON report path.")
    args = parser.parse_args()

    game_path = Path(args.game_path)
    if not game_path.exists():
        raise FileNotFoundError(f"Game path not found: {game_path}")

    quickbms = resolve_tool_path(
        args.quickbms,
        "quickbms.exe",
        [
            "quickbms_*\\dist\\quickbms.exe",
            "quickbms\\quickbms.exe",
        ],
    )
    bms_script = resolve_tool_path(
        args.bms_script,
        "Once_Human_Beta_NPK.bms",
        [
            "dkdave_scripts_*\\QuickBMS\\Once_Human_Beta_NPK.bms",
        ],
    )
    pvr_cli = resolve_tool_path(
        args.pvr_cli,
        "PVRTexToolCLI.exe",
        [
            "PVRTexToolExtract\\Imgtec\\PowerVR_Tools\\PVRTexTool\\CLI\\Windows_x86_64\\PVRTexToolCLI.exe",
            "PVRTexTool*\\Imgtec\\PowerVR_Tools\\PVRTexTool\\CLI\\Windows_x86_64\\PVRTexToolCLI.exe",
        ],
    )

    pack_ids = DEFAULT_PACK_IDS
    if args.packs:
        pack_ids = [int(value.strip()) for value in args.packs.split(",") if value.strip()]

    temp_root = Path(tempfile.gettempdir())
    extract_dir = Path(args.extract_dir) if args.extract_dir else temp_root / "once_human_mod_pvr_extract"
    png_dir = Path(args.png_dir) if args.png_dir else temp_root / "once_human_mod_png_extract"

    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    if png_dir.exists():
        shutil.rmtree(png_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)
    png_dir.mkdir(parents=True, exist_ok=True)

    try:
        pvr_files = run_quickbms(quickbms, bms_script, game_path, extract_dir, pack_ids)
        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
            png_files = list(executor.map(lambda path: convert_pvr_to_png(pvr_cli, path, extract_dir, png_dir), pvr_files))

        reference_icons = build_reference_icon_list()
        matched, skipped = match_icons(reference_icons, png_files, args.max_distance)

        if not args.dry_run:
            apply_matches(matched)

        summary = {
            "matched": len(matched),
            "skipped": len(skipped),
            "pvr_files": len(pvr_files),
            "png_files": len(png_files),
            "reference_icons": len(reference_icons),
            "max_distance": args.max_distance,
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))

        if skipped:
            print("Skipped icons:")
            for entry in skipped[:20]:
                print(f"  dist={entry['distance']}: {entry['target']}")

        if args.report:
            report_path = Path(args.report)
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(
                json.dumps({"summary": summary, "matched": matched, "skipped": skipped}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
    finally:
        if not args.keep_temp:
            shutil.rmtree(extract_dir, ignore_errors=True)
            shutil.rmtree(png_dir, ignore_errors=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
