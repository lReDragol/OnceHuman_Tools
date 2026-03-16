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

## Типовой порядок работы

1. Запусти `once_human_game_probe.py` на локальных файлах игры, чтобы найти полезные таблицы.
2. Запусти `import_once_human_db.py --write`, чтобы обновить JSON-данные калькулятора.
3. Запусти `sync_once_human_db_icons.py`, чтобы подтянуть подходящие иконки.

## Примечания

- `once_human_game_probe.py` сейчас нужен как инструмент разведки. Он помогает найти полезные файлы, но ещё не декодирует полностью каждый bindict payload.
- `import_once_human_db.py` пока использует публичный датамайн как мост, пока прямой импорт из клиента не завершён.
- `sync_once_human_db_icons.py` берёт иконки из синхронизированного публичного датасета, основанного на игровых ассетах.
