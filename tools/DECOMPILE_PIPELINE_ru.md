# Автоматическая декомпиляция Once Human

Этот документ описывает текущий автоматический pipeline для сценария:

1. Выбрать папку игры Once Human.
2. Нажать одну кнопку.
3. Получить рядом папку `decompile` с распакованными игровыми скриптами и промежуточными артефактами декода.

## Инструменты

`tools/decompile_once_human.py`
- Главный CLI-pipeline.
- Создаёт `<папка игры>/decompile`.
- Распаковывает `script.npk` и `Documents/script.npk`.
- По желанию сразу декодирует mod secondary attributes.

`tools/decompile_once_human_ui.py`
- Простой PySide6-лаунчер поверх CLI-pipeline.
- Для сценария `выбрал папку игры -> нажал Запустить`.

`tools/extract_once_human_mod_attributes.py`
- Второй этап дешифровки bindict-таблиц с модовыми вторичными атрибутами.
- Работает уже по готовой папке `decompile`.

## Что происходит по этапам

### Этап 1. Поиск архивов

Pipeline ищет два архива:

- `<game>/script.npk`
- `<game>/Documents/script.npk`

Если один из них отсутствует, стадия помечается как `skipped`, но общий pipeline не падает.

### Этап 2. Разбор NXPK

Файл `.npk` разбирается как контейнер `NXPK`:

- читается заголовок;
- считывается число файлов;
- извлекается таблица записей;
- восстанавливаются имена файлов.

На выходе получаем список внутренних путей и метаданных по каждому payload:

- `offset`
- `zsize`
- `size`
- `comp_type`

### Этап 3. Декомпрессия payload

Поддерживается:

- raw payload без сжатия;
- `comp_type == 3` через `zstandard`.

Пока не поддерживается:

- `comp_type == 2` (`LZ4`) для редких записей.

Распакованные файлы складываются в:

- `<game>/decompile/root_script/raw/...`
- `<game>/decompile/documents_script/raw/...`

### Этап 4. Генерация bindict sidecars

Если включена опция sidecars, pipeline пытается генерировать их только для bindict-похожих таблиц из `game_common/data`, а не для каждого `.pyc` подряд.

По умолчанию этот этап выключен, потому что он нужен в основном для reverse engineering и ещё дорабатывается.

1. читает `marshal` payload;
2. ищет embedded `bindict` blob;
3. отделяет строковую таблицу;
4. сохраняет рядом файл:
   - `*.pyc.bindict_strings.json`

Эти sidecar-файлы нужны не для финального калькулятора, а для reverse engineering:

- быстро смотреть строки из bindict;
- искать игровые family/tier key без повторной распаковки;
- проверять гипотезы при декоде binary tail.

### Этап 5. Частичный декод bindict

Скрипт `extract_once_human_mod_attributes.py` уже автоматически:

- читает `mod_entry_data.pyc`;
- читает `mod_sub_entry_lib.pyc`;
- читает `mod_level_lib_data.pyc`;
- вытаскивает семейства вторичных атрибутов модов;
- вытаскивает tier-коды;
- вытаскивает category metadata;
- вытаскивает часть точных игровых значений tier-уровней.
- формирует полный каталог из `108` игровых семейств mod secondary attributes для калькулятора.

Результат сохраняется в JSON, который можно сразу использовать в калькуляторе.

### Этап 6. Сборка отчёта pipeline

После выполнения создаётся:

- `<game>/decompile/pipeline_report.json`

В нём лежат:

- список стадий;
- длительность каждой стадии;
- статус `ok/skipped/error`;
- пути к выходным файлам.

## Что уже автоматизировано полностью

- создание папки `decompile` рядом с игрой;
- распаковка `script.npk`;
- повторный инкрементальный запуск без перезаписи одинаковых файлов;
- генерация bindict string sidecars;
- базовый отчёт по стадиям;
- извлечение mod secondary attributes в отдельный JSON.

## Что пока не декодировано полностью

Главное ограничение сейчас в bindict binary tail после строковой таблицы:

- часть записей с object/reference-узлами ещё не декодирована generic-алгоритмом;
- из-за этого не все multi-stat структуры и не все tier-лестницы читаются напрямую;
- часть значений сейчас восстанавливается по найденным игровым точкам и нормализации профиля.

То есть pipeline уже полностью автоматический на уровне `распаковать и получить рабочую исследовательскую базу`, но ещё не полностью автоматический на уровне `идеально прочитать любой bindict-объект игры без ручных гипотез`.

## Как запустить

### CLI

```powershell
python tools/decompile_once_human.py --game-path "E:\SteamLibrary\steamapps\common\Once Human" --extract-mod-attributes
```

Инкрементальный запуск по уже существующей папке `decompile`:

```powershell
python tools/decompile_once_human.py --game-path "E:\SteamLibrary\steamapps\common\Once Human" --skip-extract --extract-mod-attributes
```

### UI

```powershell
python tools/decompile_once_human_ui.py
```

Безопасный дефолт сейчас `workers=1`. Многопоточная распаковка на Windows ещё требует отдельной стабилизации.
`bindict sidecars` сейчас тоже опциональны и не входят в дефолтный one-click путь.

## Структура результата

Пример:

```text
Once Human/
  decompile/
    root_script/
      raw/
        game_common/
          data/
            mod_entry_data.pyc
            mod_entry_data.pyc.bindict_strings.json
    documents_script/
      raw/
        ...
    mod_secondary_attributes.json
    pipeline_report.json
```

## Зачем это нужно калькулятору

Из `decompile` можно дальше автоматизировать:

- оружие и их коэффициенты;
- броню и сетовые бонусы;
- оружейные обвесы;
- моды и их вторичные атрибуты;
- игровые иконки;
- часть скрытых механик, если они сидят в script-таблицах.

То есть `decompile/` теперь становится постоянным локальным кэшем для всех следующих extractor-скриптов.
