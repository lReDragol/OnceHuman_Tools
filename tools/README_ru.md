# Инструменты для данных Once Human

В этой папке лежат вспомогательные скрипты, которыми наполняется калькулятор игровыми данными и иконками.

## Что здесь есть

`import_once_human_db.py`
- Подтягивает публичные datamined-данные и сливает их с JSON-базой калькулятора.
- Обновляет оружие, броню/предметы, сеты и моды.
- По возможности сохраняет уже написанные вручную механики.

Использование:
```powershell
python tools/import_once_human_db.py --summary-only
python tools/import_once_human_db.py --write
```

`once_human_game_probe.py`
- Сканирует локальные файлы клиента Once Human и ищет таблицы-кандидаты с оружием, бронёй, модами, звёздами и другой игровой логикой.
- Лучше всего работает по уже извлечённому `script.npk`, но может стартовать и от корня игры.

Использование:
```powershell
python tools/once_human_game_probe.py --game-path "E:\SteamLibrary\steamapps\common\Once Human"
python tools/once_human_game_probe.py --game-path "E:\SteamLibrary\steamapps\common\Once Human" --extracted-dir "C:\temp\oncehuman_script" --output once_human_probe.json
```

`sync_once_human_db_icons.py`
- Скачивает иконки для калькулятора под уже синхронизированную базу оружия, брони и модов.
- Заполняет локальные папки с иконками, которые использует интерфейс калькулятора.

Использование:
```powershell
python tools/sync_once_human_db_icons.py
python tools/sync_once_human_db_icons.py --force
```

`extract_once_human_mod_icons.py`
- Вытаскивает настоящие mod-глифы из локальных `.npk` клиента Once Human.
- Использует QuickBMS для извлечения `mods_icon_cbt2/*.pvr`, затем PVRTexToolCLI для конвертации в PNG.
- Сопоставляет извлечённые игровые глифы с локальными иконками калькулятора и перезаписывает совпавшие файлы.

Использование:
```powershell
python tools/extract_once_human_mod_icons.py --game-path "E:\SteamLibrary\steamapps\common\Once Human"
python tools/extract_once_human_mod_icons.py --game-path "E:\SteamLibrary\steamapps\common\Once Human" --dry-run --keep-temp
```

`extract_once_human_attachment_icons.py`
- Вытаскивает реальные иконки оружейных обвесов из локальных `.npk` клиента Once Human.
- Использует QuickBMS для извлечения `icon_accessory*.pvr` из известных pack-файлов и PVRTexToolCLI для конвертации в PNG.
- Обновляет `weapon_attachments.json` и перезаписывает `data/icons/attachments/*.png` по id обвесов.

Использование:
```powershell
python tools/extract_once_human_attachment_icons.py --game-path "E:\SteamLibrary\steamapps\common\Once Human"
python tools/extract_once_human_attachment_icons.py --game-path "E:\SteamLibrary\steamapps\common\Once Human" --report attachment_icons_report.json
```

## Типовой порядок работы

1. Запусти `once_human_game_probe.py` на локальных файлах игры, чтобы найти полезные таблицы.
2. Запусти `import_once_human_db.py --write`, чтобы обновить JSON-данные калькулятора.
3. Запусти `sync_once_human_db_icons.py`, чтобы подтянуть оружие/броню и базовые mod-иконки.
4. Запусти `extract_once_human_mod_icons.py`, если хочешь заменить mod-иконки на прямые ассеты из локального клиента.
5. Запусти `extract_once_human_attachment_icons.py`, чтобы обновить игровые иконки обвесов.

## Примечания

- `once_human_game_probe.py` сейчас нужен как инструмент разведки. Он помогает найти полезные файлы, но ещё не декодирует полностью каждый bindict payload.
- `import_once_human_db.py` пока использует публичный датамайн как мост, пока прямой импорт из клиента не завершён.
- `sync_once_human_db_icons.py` берёт иконки из синхронизированного публичного датасета, основанного на игровых ассетах.
- `extract_once_human_mod_icons.py` требует локально доступные `quickbms.exe`, `Once_Human_Beta_NPK.bms` и `PVRTexToolCLI.exe`. Скрипт сначала пытается найти их автоматически во временной папке.
- `extract_once_human_attachment_icons.py` использует тот же набор утилит, но извлекает игровые иконки оружейных аксессуаров.
