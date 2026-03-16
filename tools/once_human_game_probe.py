#!/usr/bin/env python3
"""Probe Once Human script data for promising game_common tables.

This tool does not fully decode bindict blobs yet. It automates the initial
recon stage against an extracted `script.npk` directory by:

- reading numeric `.dat` script payloads
- zstd-streaming the header bytes when possible
- recovering embedded `*.py` module paths from the payload head
- filtering interesting modules related to weapons, armor, mods, and scoring

Typical usage:

    python tools/once_human_game_probe.py ^
      --game-path "E:\\SteamLibrary\\steamapps\\common\\Once Human" ^
      --extracted-dir C:\\temp\\oncehuman_script ^
      --output once_human_probe.json

If you only have `script.npk`, first extract it with an external extractor,
then pass the extracted directory here.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


DEFAULT_KEYWORDS = [
    "armor",
    "cbg_item",
    "equip",
    "gun",
    "item",
    "mod",
    "prototype",
    "score",
    "star",
    "store_data",
    "weapon",
]

PYC_MAGICS = {
    bytes.fromhex("a80d0d0a"): "pyc-like-a80d0d0a",
    bytes.fromhex("cb0d0d0a"): "pyc-like-cb0d0d0a",
}

MODULE_PATH_RE = re.compile(rb"[A-Za-z0-9_./\\-]+\.py")
PATH_MARKERS = (
    "dcs_extend\\",
    "engine\\",
    "game_common\\",
    "ui\\",
    "ui_auto\\",
    "utils\\",
)


def try_import_zstd():
    try:
        import zstandard as zstd  # type: ignore
    except ImportError:
        return None
    return zstd


def resolve_script_npk(game_path: Path | None, script_npk: Path | None) -> Path | None:
    if script_npk:
        return script_npk
    if not game_path:
        return None
    candidate = game_path / "script.npk"
    if candidate.exists():
        return candidate
    doc_candidate = game_path / "Documents" / "script.npk"
    if doc_candidate.exists():
        return doc_candidate
    return None


def maybe_extract(script_npk: Path, extractor: Path | None) -> Path:
    if not extractor:
        raise FileNotFoundError(
            "No extracted directory was supplied and no extractor path was provided. "
            "Extract script.npk first or pass --extractor."
        )
    if not extractor.exists():
        raise FileNotFoundError(f"Extractor not found: {extractor}")

    subprocess.run([sys.executable, str(extractor), str(script_npk)], check=True)
    extracted_dir = script_npk.with_suffix("")
    if not extracted_dir.exists():
        raise FileNotFoundError(
            f"Extractor finished but expected output directory was not found: {extracted_dir}"
        )
    return extracted_dir


def read_head_bytes(path: Path, head_bytes: int, zstd_module: Any) -> tuple[bytes, str]:
    raw = path.read_bytes()
    if zstd_module is None:
        return raw[:head_bytes], "raw"

    try:
        dctx = zstd_module.ZstdDecompressor()
        with dctx.stream_reader(io.BytesIO(raw)) as reader:
            return reader.read(head_bytes), "zstd_head"
    except Exception:
        return raw[:head_bytes], "raw"


def recover_module_paths(head: bytes) -> list[str]:
    hits = {
        clean_module_path(match.decode("utf-8", "ignore"))
        for match in MODULE_PATH_RE.findall(head)
    }
    return sorted(hit for hit in hits if hit)


def clean_module_path(path: str) -> str:
    normalized = path.replace("/", "\\")
    for marker in PATH_MARKERS:
        index = normalized.lower().find(marker.lower())
        if index != -1:
            return normalized[index:]
    return normalized.lstrip(".0123456789_\\")


def select_candidate(paths: list[str]) -> str | None:
    if not paths:
        return None
    preferred = [
        path
        for path in paths
        if path.lower().startswith(("game_common\\", "game_common/", "ui\\", "ui/"))
    ]
    source = preferred if preferred else paths
    return max(source, key=len)


def keyword_hits(value: str, keywords: list[str]) -> list[str]:
    lower = value.lower()
    return [keyword for keyword in keywords if keyword.lower() in lower]


def candidate_rank(candidate_path: str | None) -> int:
    if not candidate_path:
        return 9
    lower = candidate_path.lower()
    if lower.startswith(("game_common\\data\\", "game_common/data/")) and re.search(
        r"(?:_data|_param|_const|prototype_data)\.py$",
        lower,
    ):
        return 0
    if lower.startswith(("game_common\\data\\", "game_common/data/")):
        return 1
    if lower.startswith(("game_common\\mod\\", "game_common/mod/")):
        return 2
    if lower.startswith(("game_common\\guncore\\", "game_common/guncore/")):
        return 3
    if lower.startswith(("ui\\", "ui_auto\\", "ui/")):
        return 4
    if lower.startswith(("client_data\\", "client_data/")):
        return 5
    return 6


def probe_extracted_dir(
    extracted_dir: Path,
    keywords: list[str],
    head_bytes: int,
    max_files: int | None,
) -> dict[str, Any]:
    zstd_module = try_import_zstd()
    files = sorted(path for path in extracted_dir.iterdir() if path.is_file())
    if max_files is not None:
        files = files[:max_files]

    results: list[dict[str, Any]] = []
    interesting: list[dict[str, Any]] = []

    for path in files:
        head, transport = read_head_bytes(path, head_bytes, zstd_module)
        paths = recover_module_paths(head)
        candidate = select_candidate(paths)
        magic = PYC_MAGICS.get(head[:4])
        entry = {
            "file": path.name,
            "transport": transport,
            "magic": magic,
            "candidate_path": candidate,
            "recovered_paths": paths[:10],
            "keyword_hits": keyword_hits(candidate or "", keywords),
        }
        results.append(entry)

        is_interesting = bool(entry["keyword_hits"]) or (
            candidate is not None and candidate.lower().startswith(("game_common\\data", "game_common/data"))
        )
        if is_interesting:
            interesting.append(entry)

    interesting.sort(
        key=lambda item: (
            candidate_rank(item["candidate_path"]),
            0 if item["magic"] else 1,
            -(len(item["keyword_hits"])),
            item["candidate_path"] or item["file"],
        )
    )

    return {
        "extracted_dir": str(extracted_dir),
        "zstandard_available": zstd_module is not None,
        "scanned_files": len(files),
        "interesting_files": len(interesting),
        "interesting": interesting,
        "sample": interesting[:50],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-path", type=Path, help="Once Human game root")
    parser.add_argument("--script-npk", type=Path, help="Path to script.npk")
    parser.add_argument("--extracted-dir", type=Path, help="Directory produced by a script.npk extractor")
    parser.add_argument("--extractor", type=Path, help="Optional external extractor.py path")
    parser.add_argument("--output", type=Path, help="Optional JSON report path")
    parser.add_argument("--head-bytes", type=int, default=4096, help="Bytes to inspect from each payload head")
    parser.add_argument("--max-files", type=int, help="Limit scanned files for quick tests")
    parser.add_argument(
        "--keywords",
        nargs="+",
        default=DEFAULT_KEYWORDS,
        help="Keywords used to rank interesting modules",
    )
    args = parser.parse_args()

    extracted_dir = args.extracted_dir
    if extracted_dir is None:
        script_npk = resolve_script_npk(args.game_path, args.script_npk)
        if script_npk is None:
            raise SystemExit("Could not resolve script.npk. Pass --game-path, --script-npk, or --extracted-dir.")
        extracted_dir = maybe_extract(script_npk, args.extractor)

    if not extracted_dir.exists():
        raise SystemExit(f"Extracted directory not found: {extracted_dir}")

    report = probe_extracted_dir(
        extracted_dir=extracted_dir,
        keywords=args.keywords,
        head_bytes=max(256, args.head_bytes),
        max_files=args.max_files,
    )

    if args.output:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    preview = {
        "extracted_dir": report["extracted_dir"],
        "scanned_files": report["scanned_files"],
        "interesting_files": report["interesting_files"],
        "zstandard_available": report["zstandard_available"],
        "top_hits": report["sample"][:15],
    }
    print(json.dumps(preview, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
