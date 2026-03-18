# Once Human Portable Calculator V2

This folder is self-contained.

You can take only `portable_calc_v2` from the repository and run the calculator without cloning the full project.

## Files included

- `main.py` - portable calculator entrypoint
- `config.py` - local config loader
- `translations.json` - local UI translations
- `data/menu/calc_and_mod_tab.py` - calculator UI
- `data/menu/calc/*` - calculator runtime and combat logic
- `data/menu/calc/bd_json/*` - local weapon, armor, mod, attachment, deviation, and attribute database
- `data/icons/*` - local game icons used by the calculator
- `data/file/ru.ttf` - bundled fallback font for Cyrillic and CJK text

## Run

```powershell
pip install -r requirements.txt
python main.py
```

## Notes

- The folder is synchronized from the main project through `tools/sync_portable_calc_v2.ps1`.
- The portable build produced from this folder is `OnceHumanCalcPortable_V2.8.exe`.
