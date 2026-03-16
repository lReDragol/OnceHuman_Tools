#!/usr/bin/env python3
"""Extract Once Human weapon attachment icons from local game packs.

This script syncs calculator attachment icons under `data/icons/attachments`
with real game assets. It uses the local `weapon_attachments.json` mapping,
extracts known attachment icon packs via QuickBMS, converts PVR textures to PNG,
and writes one icon per attachment id.
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


REPO_ROOT = Path(__file__).resolve().parents[1]
ATTACHMENTS_JSON = REPO_ROOT / "data" / "menu" / "calc" / "bd_json" / "weapon_attachments.json"
ATTACHMENTS_ICONS_ROOT = REPO_ROOT / "data" / "icons" / "attachments"
DEFAULT_PACK_IDS = [331, 327, 259]
ATTACHMENT_ICON_ALIASES = {
    "620_large_stock_01": "icon_accessory_stock_combat_01.png",
    "620_rs2_stock_01": "icon_accessory_stock_combat_02.png",
    "620_tac_stock_01": "icon_accessory_stock_combat_03.png",
    "620_strike_stock_01": "icon_accessory_stock_combat_05.png",
    "420_lmg_med_drum_02": "icon_accessory_sg_drum_01.png",
    "420_pis_med_mag_02": "icon_accessory_ar_light_mag_01.png",
    "420_pis_spr_mag_02": "icon_accessory_ar_tac_mag_01.png",
    "420_rif_med_mag_03": "icon_accessory_ar_light_mag_01.png",
    "420_smg_med_mag_04": "icon_accessory_ar_light_mag_01.png",
    "420_sr_med_mag_05": "icon_accessory_ar_light_mag_01.png",
    "420_ex_mag_rust": "icon_accessory_ar_ex_mag_01.png",
    "420_tac_mag_rust": "icon_accessory_ar_tac_mag_01.png",
}
GENERIC_ICON_ALIASES = {
    "icon_folding_gunstock.png": "icon_accessory_stock_combat_05.png",
    "icon_gunstock.png": "icon_accessory_stock_combat_01.png",
    "icon_retractable_gunstock.png": "icon_accessory_stock_combat_03.png",
    "icon_magazine.png": "icon_accessory_ar_light_mag_01.png",
}


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


def run_quickbms(quickbms: Path, bms_script: Path, game_path: Path, output_dir: Path, pack_ids: list[int]) -> list[Path]:
    extracted: list[Path] = []
    for pack_id in pack_ids:
        pack_path = game_path / f"res_normal_pack_{pack_id}.npk"
        if not pack_path.exists():
            continue
        subprocess.run(
            [str(quickbms), "-q", "-o", "-f", "{}icon_accessory{}.pvr", str(bms_script), str(pack_path), str(output_dir)],
            check=True,
        )
        extracted.extend(sorted(output_dir.rglob("*.pvr")))

    if not extracted:
        raise RuntimeError("No attachment PVR files were extracted. Check the game path and pack ids.")
    return sorted(set(extracted))


def convert_pvr_to_png(pvr_cli: Path, pvr_path: Path, output_dir: Path) -> Path:
    output_path = output_dir / f"{pvr_path.stem}.png"
    subprocess.run([str(pvr_cli), "-i", str(pvr_path), "-d", str(output_path), "-noout", "-shh"], check=True)
    return output_path


def load_source_pngs(paths: Iterable[Path]) -> dict[str, Path]:
    source_by_name: dict[str, Path] = {}
    for path in paths:
        source_by_name.setdefault(path.name, path)
    return source_by_name


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-path", required=True, help="Path to the Once Human game root.")
    parser.add_argument("--quickbms", help="Path to quickbms.exe.")
    parser.add_argument("--bms-script", help="Path to Once_Human_Beta_NPK.bms.")
    parser.add_argument("--pvr-cli", help="Path to PVRTexToolCLI.exe.")
    parser.add_argument("--packs", help="Comma-separated pack ids. Default: discovered attachment icon packs.")
    parser.add_argument("--extract-dir", help="Temporary directory for extracted PVR files.")
    parser.add_argument("--png-dir", help="Temporary directory for converted PNG files.")
    parser.add_argument("--workers", type=int, default=max(4, (os.cpu_count() or 8) // 2), help="Parallel conversion workers.")
    parser.add_argument("--report", help="Optional JSON report path.")
    args = parser.parse_args()

    game_path = Path(args.game_path)
    if not game_path.exists():
        raise FileNotFoundError(f"Game path not found: {game_path}")

    quickbms = resolve_tool_path(
        args.quickbms,
        "quickbms.exe",
        ["quickbms_*\\dist\\quickbms.exe", "quickbms\\quickbms.exe"],
    )
    bms_script = resolve_tool_path(
        args.bms_script,
        "Once_Human_Beta_NPK.bms",
        ["dkdave_scripts_*\\QuickBMS\\Once_Human_Beta_NPK.bms"],
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
    extract_dir = Path(args.extract_dir) if args.extract_dir else temp_root / "once_human_attachment_pvr_extract"
    png_dir = Path(args.png_dir) if args.png_dir else temp_root / "once_human_attachment_png_extract"

    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    if png_dir.exists():
        shutil.rmtree(png_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)
    png_dir.mkdir(parents=True, exist_ok=True)

    try:
        pvr_files = run_quickbms(quickbms, bms_script, game_path, extract_dir, pack_ids)
        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
            png_files = list(executor.map(lambda path: convert_pvr_to_png(pvr_cli, path, png_dir), pvr_files))
        source_by_name = load_source_pngs(png_files)

        payload = json.loads(ATTACHMENTS_JSON.read_text(encoding="utf-8"))
        attachments = payload.get("attachments", [])
        ATTACHMENTS_ICONS_ROOT.mkdir(parents=True, exist_ok=True)

        missing: list[dict[str, str]] = []
        synced = 0
        for attachment in attachments:
            icon_name = ATTACHMENT_ICON_ALIASES.get(attachment["id"]) or attachment.get("game_icon_name")
            icon_name = GENERIC_ICON_ALIASES.get(icon_name, icon_name)
            source_path = source_by_name.get(icon_name or "")
            if not source_path:
                missing.append(
                    {
                        "id": attachment["id"],
                        "name": attachment.get("name", ""),
                        "requested_icon": attachment.get("game_icon_name", ""),
                        "resolved_icon": icon_name or "",
                    }
                )
                continue
            attachment["game_icon_name"] = icon_name
            shutil.copy2(source_path, ATTACHMENTS_ICONS_ROOT / f"{attachment['id']}.png")
            synced += 1

        ATTACHMENTS_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        summary = {
            "synced": synced,
            "missing": len(missing),
            "attachments": len(attachments),
            "packs": pack_ids,
            "pvr_files": len(pvr_files),
            "png_files": len(png_files),
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))

        if args.report:
            report_path = Path(args.report)
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(
                json.dumps({"summary": summary, "missing": missing}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
    finally:
        shutil.rmtree(extract_dir, ignore_errors=True)
        shutil.rmtree(png_dir, ignore_errors=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
