# Once Human Tools

Once Human Tools is a multi-tool project for Once Human with three maintained deliverables:

- Main desktop application `V4.6`
- Portable fishing bot `V4`
- Portable calculator `V2.8`

## Main features

- Photo and video replacement for in-game media folders
- Piano bot with MIDI playback controls
- Fishing bot with OCR checks, automatic OCR installation, Telegram notifications, and zone-based tracking
- Damage calculator with weapons, armor, sets, mods, synced game icons, and a local deviation/pet catalog
- Data tools for importing and probing game files

## Project structure

- Main application entrypoint: `main.py`
- Portable fishing bot: `onli_fish_bot/main.py`
- Portable calculator: `portable_calc_v2/main.py`
- The `portable_calc_v2` folder is now self-contained and includes its own local calculator runtime
- Calculator data tools: [`tools/README_en.md`](tools/README_en.md)
- Automatic game decompile docs: [`tools/DECOMPILE_PIPELINE_en.md`](tools/DECOMPILE_PIPELINE_en.md)
- Usage policy: [`README_policy_en.md`](README_policy_en.md)

## Setup

Install dependencies:

```powershell
pip install -r requirements.txt
```

Run the main app:

```powershell
python main.py
```

Run the portable fishing bot:

```powershell
python onli_fish_bot/main.py
```

Run the portable calculator:

```powershell
python portable_calc_v2/main.py
```

## Fishing bot notes

- Before starting tracking, check OCR in the UI.
- If Tesseract or the `eng` / `rus` language packs are missing, use the automatic installer button.
- Zone creation now starts directly from the Windows snipping flow and then opens the zone editor on the captured screenshot.

## Calculator notes

- The calculator database now includes expanded weapons, armor, sets, mods, and synced icons.
- The calculator can now load a local deviation/pet catalog extracted from the game `decompile` cache.
- Character stats are displayed with readable names instead of raw internal keys.
- Target dummy HP is shown in rounded form in the UI.

## Documentation

- [Usage policy in English](README_policy_en.md)
- [Data tools in English](tools/README_en.md)
- [Automatic Once Human Decompile Pipeline](tools/DECOMPILE_PIPELINE_en.md)
- [Русская документация](README_ru.md)
