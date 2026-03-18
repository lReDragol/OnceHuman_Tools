# Once Human Data Tools

This folder contains helper scripts used to fill the calculator with real game data and icons.

## Included scripts

`import_once_human_db.py`
- Pulls public datamined data and merges it into the calculator JSON database.
- Updates weapons, armor/items, sets, and mods.
- Keeps existing hand-written mechanics where possible.

Usage:
```powershell
python tools/import_once_human_db.py --summary-only
python tools/import_once_human_db.py --write
```

`once_human_game_probe.py`
- Scans local Once Human client files to find promising script tables for weapons, armor, mods, stars, and other gameplay data.
- Works best with an extracted `script.npk`, but can also start from the game root.

Usage:
```powershell
python tools/once_human_game_probe.py --game-path "E:\SteamLibrary\steamapps\common\Once Human"
python tools/once_human_game_probe.py --game-path "E:\SteamLibrary\steamapps\common\Once Human" --extracted-dir "C:\temp\oncehuman_script" --output once_human_probe.json
```

`sync_once_human_db_icons.py`
- Downloads calculator icons that match the synced weapon, armor, and mod database.
- Fills the local folders used by the calculator UI.

Usage:
```powershell
python tools/sync_once_human_db_icons.py
python tools/sync_once_human_db_icons.py --force
```

`extract_once_human_mod_icons.py`
- Pulls the real mod glyph assets from local Once Human `.npk` packs.
- Uses QuickBMS to extract `mods_icon_cbt2/*.pvr`, then PVRTexToolCLI to convert them to PNG.
- Matches the extracted game glyphs to the calculator mod icon files and overwrites the matched targets.

Usage:
```powershell
python tools/extract_once_human_mod_icons.py --game-path "E:\SteamLibrary\steamapps\common\Once Human"
python tools/extract_once_human_mod_icons.py --game-path "E:\SteamLibrary\steamapps\common\Once Human" --dry-run --keep-temp
```

`extract_once_human_attachment_icons.py`
- Pulls the real weapon attachment icons from local Once Human `.npk` packs.
- Uses QuickBMS to extract `icon_accessory*.pvr` files from the known pack set and PVRTexToolCLI to convert them to PNG.
- Updates `weapon_attachments.json` and rewrites `data/icons/attachments/*.png` by attachment id.

Usage:
```powershell
python tools/extract_once_human_attachment_icons.py --game-path "E:\SteamLibrary\steamapps\common\Once Human"
python tools/extract_once_human_attachment_icons.py --game-path "E:\SteamLibrary\steamapps\common\Once Human" --report attachment_icons_report.json
```

`extract_once_human_deviations.py`
- Builds the deviation/pet catalog directly from the local `decompile` cache.
- Extracts `deviation_id`, names, descriptions, asset names, combat/non-combat classification, in-game RU/EN localization, baseline combat profiles, and exact skill coefficients from the client bindict tables (`deviation_base_data.pyc`, `deviation_preview_skill_data.pyc`, `deviation_combat_config_data.pyc`, `deviation_skills_data.pyc`, `translate_data_ru.pyc`, `translate_data_en.pyc`).
- Generates `data/menu/calc/bd_json/deviations.json`, which the calculator uses for deviation selection and baseline combat deviation simulation.

Usage:
```powershell
python tools/extract_once_human_deviations.py --decompile-dir "E:\SteamLibrary\steamapps\common\Once Human\decompile" --output data\menu\calc\bd_json\deviations.json
```

`extract_once_human_deviation_icons.py`
- Pulls real deviation/pet icons from local Once Human `.npk` packs.
- No longer needs `QuickBMS` or `PVRTexToolCLI`: it scans the pack index directly, decodes the in-game `PVR` icon payloads in Python, and matches them by `icon_asset` / `me_code`.
- Writes the synced icons to `data/icons/deviations/<deviation_id>.png`.

Usage:
```powershell
python tools/extract_once_human_deviation_icons.py --game-path "E:\SteamLibrary\steamapps\common\Once Human"
python tools/extract_once_human_deviation_icons.py --game-path "E:\SteamLibrary\steamapps\common\Once Human" --combat-only --report deviation_icons_report.json
```

`decompile_once_human.py`
- Main automatic decompile pipeline.
- Creates a `decompile` folder next to the game.
- Extracts `script.npk`, writes bindict sidecars, and can immediately run mod secondary attribute decoding.
- The current mod secondary attribute decode exports all `108` discovered in-game families into the calculator JSON.
- The safe extraction default is currently `workers=1`.
- `bindict sidecars` are currently experimental and disabled by default.

Usage:
```powershell
python tools/decompile_once_human.py --game-path "E:\SteamLibrary\steamapps\common\Once Human" --extract-mod-attributes
python tools/decompile_once_human.py --game-path "E:\SteamLibrary\steamapps\common\Once Human" --skip-extract --extract-mod-attributes
```

`decompile_once_human_ui.py`
- PySide6 wrapper around the automatic pipeline.
- Intended for the `pick the game folder -> click Run -> get decompile` workflow.
- Sidecar generation is exposed as a separate option because it is mainly useful for reverse engineering.

Usage:
```powershell
python tools/decompile_once_human_ui.py
```

## Typical workflow

1. Run `decompile_once_human.py` or `decompile_once_human_ui.py` to build a local `decompile` cache.
2. Run `once_human_game_probe.py` against `decompile` to discover useful tables.
3. Run `import_once_human_db.py --write` to update the calculator JSON data.
4. Run `sync_once_human_db_icons.py` to pull weapon, armor, and baseline mod icons.
5. Run `extract_once_human_mod_icons.py` if you want to replace mod icons with direct assets from the local client.
6. Run `extract_once_human_attachment_icons.py` to refresh the direct in-game attachment icons.
7. Run `extract_once_human_deviations.py` to refresh the deviation/pet catalog used by the calculator.
8. Run `extract_once_human_deviation_icons.py` to sync the direct in-game deviation icons.

## Full decompile docs

- [Automatic Once Human Decompile Pipeline](DECOMPILE_PIPELINE_en.md)

## Notes

- `once_human_game_probe.py` is a reconnaissance tool. It helps identify useful files but does not fully decode every bindict payload yet.
- `import_once_human_db.py` uses public datamined sources as a bridge until direct extraction is complete.
- `sync_once_human_db_icons.py` uses the synced public dataset to fetch icons derived from real game assets.
- `extract_once_human_mod_icons.py` needs local access to `quickbms.exe`, `Once_Human_Beta_NPK.bms`, and `PVRTexToolCLI.exe`. The script tries to auto-discover them in the temp directory first.
- `extract_once_human_attachment_icons.py` uses the same toolchain, but targets weapon attachment icons instead of mod glyphs.
- `extract_once_human_deviations.py` now also localizes deviation names/descriptions directly from the client, but not every hidden combat id / cooldown field from bindict is decoded yet.
- `extract_once_human_deviation_icons.py` requires the Python package `texture2ddecoder`, but no longer depends on external `QuickBMS` / `PVRTexToolCLI`.
- `decompile_once_human.py` already automates creation of the `decompile` cache, but the generic bindict tail decoder is not finished yet.
