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

## Typical workflow

1. Run `once_human_game_probe.py` against the local game files to discover useful tables.
2. Run `import_once_human_db.py --write` to update the calculator JSON data.
3. Run `sync_once_human_db_icons.py` to pull matching icons.

## Notes

- `once_human_game_probe.py` is a reconnaissance tool. It helps identify useful files but does not fully decode every bindict payload yet.
- `import_once_human_db.py` uses public datamined sources as a bridge until direct extraction is complete.
- `sync_once_human_db_icons.py` uses the synced public dataset to fetch icons derived from real game assets.
