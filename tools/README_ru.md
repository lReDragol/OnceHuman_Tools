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

`extract_once_human_deviations.py`
- Собирает каталог девиаций/питомцев напрямую из локального `decompile`.
- Вытаскивает `deviation_id`, имя, описание, asset-имена, боевую/небоевую классификацию, локализацию RU/EN из игровых translation-таблиц, базовые боевые профили и точные skill-коэффициенты из игровых bindict-таблиц (`deviation_base_data.pyc`, `deviation_preview_skill_data.pyc`, `deviation_combat_config_data.pyc`, `deviation_skills_data.pyc`, `translate_data_ru.pyc`, `translate_data_en.pyc`).
- Генерирует `data/menu/calc/bd_json/deviations.json`, который использует калькулятор для выбора питомца и базовой симуляции боевых девиаций.

Использование:
```powershell
python tools/extract_once_human_deviations.py --decompile-dir "E:\SteamLibrary\steamapps\common\Once Human\decompile" --output data\menu\calc\bd_json\deviations.json
```

`extract_once_human_deviation_icons.py`
- Вытаскивает локальные игровые иконки девиаций/питомцев из `.npk` клиента Once Human.
- Больше не требует `QuickBMS` и `PVRTexToolCLI`: читает `.npk` напрямую, декодирует игровые `PVR`-иконки в Python и сопоставляет их по `icon_asset`/`me_code`.
- Складывает иконки в `data/icons/deviations/<deviation_id>.png`.

Использование:
```powershell
python tools/extract_once_human_deviation_icons.py --game-path "E:\SteamLibrary\steamapps\common\Once Human"
python tools/extract_once_human_deviation_icons.py --game-path "E:\SteamLibrary\steamapps\common\Once Human" --combat-only --report deviation_icons_report.json
```

`decompile_once_human.py`
- Главный автоматический pipeline декомпиляции.
- Создаёт рядом с игрой папку `decompile`.
- Распаковывает `script.npk`, создаёт bindict sidecars и может сразу запустить декод модовых вторичных атрибутов.
- Текущий декод модовых secondary attributes выгружает все `108` найденных игровых семейств в JSON калькулятора.
- Безопасный дефолт для распаковки сейчас `workers=1`.
- `bindict sidecars` сейчас экспериментальны и выключены по умолчанию.

Использование:
```powershell
python tools/decompile_once_human.py --game-path "E:\SteamLibrary\steamapps\common\Once Human" --extract-mod-attributes
python tools/decompile_once_human.py --game-path "E:\SteamLibrary\steamapps\common\Once Human" --skip-extract --extract-mod-attributes
```

`decompile_once_human_ui.py`
- PySide6-обёртка над автоматическим pipeline.
- Сценарий `выбрал папку игры -> нажал Запустить -> получил decompile`.
- Генерация sidecars вынесена в отдельную опцию, потому что она нужна в основном для reverse engineering.

Использование:
```powershell
python tools/decompile_once_human_ui.py
```

## Типовой порядок работы

1. Запусти `decompile_once_human.py` или `decompile_once_human_ui.py`, чтобы получить локальную папку `decompile`.
2. Запусти `once_human_game_probe.py` на `decompile`, чтобы найти полезные таблицы.
3. Запусти `import_once_human_db.py --write`, чтобы обновить JSON-данные калькулятора.
4. Запусти `sync_once_human_db_icons.py`, чтобы подтянуть оружие/броню и базовые mod-иконки.
5. Запусти `extract_once_human_mod_icons.py`, если хочешь заменить mod-иконки на прямые ассеты из локального клиента.
6. Запусти `extract_once_human_attachment_icons.py`, чтобы обновить игровые иконки обвесов.
7. Запусти `extract_once_human_deviations.py`, чтобы обновить каталог девиаций/питомцев для калькулятора.
8. Запусти `extract_once_human_deviation_icons.py`, чтобы подтянуть игровые иконки девиаций.

## Полная документация по декомпиляции

- [Автоматическая декомпиляция Once Human](DECOMPILE_PIPELINE_ru.md)

## Примечания

- `once_human_game_probe.py` сейчас нужен как инструмент разведки. Он помогает найти полезные файлы, но ещё не декодирует полностью каждый bindict payload.
- `import_once_human_db.py` пока использует публичный датамайн как мост, пока прямой импорт из клиента не завершён.
- `sync_once_human_db_icons.py` берёт иконки из синхронизированного публичного датасета, основанного на игровых ассетах.
- `extract_once_human_mod_icons.py` требует локально доступные `quickbms.exe`, `Once_Human_Beta_NPK.bms` и `PVRTexToolCLI.exe`. Скрипт сначала пытается найти их автоматически во временной папке.
- `extract_once_human_attachment_icons.py` использует тот же набор утилит, но извлекает игровые иконки оружейных аксессуаров.
- `extract_once_human_deviations.py` теперь ещё и локализует имена/описания питомцев прямо из клиента, но не все скрытые combat id / cooldown-поля из bindict декодированы полностью.
- `extract_once_human_deviation_icons.py` требует Python-пакет `texture2ddecoder`, зато не зависит от внешних `QuickBMS` / `PVRTexToolCLI`.
- `decompile_once_human.py` сейчас полностью автоматизирует создание кэша `decompile`, но generic-декод bindict-хвоста ещё не завершён на 100%.
