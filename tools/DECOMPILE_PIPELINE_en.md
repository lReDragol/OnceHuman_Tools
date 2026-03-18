# Automatic Once Human Decompile Pipeline

This document describes the current automatic pipeline for the workflow:

1. Pick the Once Human game folder.
2. Press one button.
3. Get a sibling `decompile` folder with extracted script files and decode artifacts.

## Tools

`tools/decompile_once_human.py`
- Main CLI pipeline.
- Creates `<game>/decompile`.
- Extracts `script.npk` and `Documents/script.npk`.
- Can optionally decode mod secondary attributes immediately after extraction.

`tools/decompile_once_human_ui.py`
- Lightweight PySide6 launcher on top of the CLI pipeline.
- Intended for the `pick folder -> click Run` workflow.

`tools/extract_once_human_mod_attributes.py`
- Second-stage bindict decoder for mod secondary attributes.
- Works from an existing `decompile` folder.

## Pipeline stages

### Stage 1. Archive discovery

The pipeline looks for:

- `<game>/script.npk`
- `<game>/Documents/script.npk`

If one archive is missing, that stage is marked as `skipped` and the rest of the pipeline still continues.

### Stage 2. NXPK parsing

Each `.npk` file is parsed as an `NXPK` container:

- read the header;
- read the file count;
- parse the record table;
- reconstruct the internal file names.

This produces the internal path list and payload metadata:

- `offset`
- `zsize`
- `size`
- `comp_type`

### Stage 3. Payload decompression

Currently supported:

- raw uncompressed payloads;
- `comp_type == 3` via `zstandard`.

Not fully supported yet:

- `comp_type == 2` (`LZ4`) for rare records.

Extracted files are written into:

- `<game>/decompile/root_script/raw/...`
- `<game>/decompile/documents_script/raw/...`

### Stage 4. bindict sidecar generation

When sidecars are enabled, the pipeline generates them only for bindict-like tables under `game_common/data`, not for every `.pyc` file.

This stage is disabled by default because it is mainly for reverse engineering and still needs more hardening.

1. read the `marshal` payload from supported `.pyc` files;
2. locate the embedded `bindict` blob;
3. split out the string table;
4. write a sibling file:
   - `*.pyc.bindict_strings.json`

These sidecars are not meant for the final calculator directly. They exist for reverse engineering:

- inspect bindict strings quickly;
- search game family and tier keys without re-extracting archives;
- validate binary-tail decoding hypotheses.

### Stage 5. Partial bindict decode

`extract_once_human_mod_attributes.py` already automates:

- reading `mod_entry_data.pyc`;
- reading `mod_sub_entry_lib.pyc`;
- reading `mod_level_lib_data.pyc`;
- extracting mod secondary attribute families;
- extracting tier codes;
- extracting category metadata;
- extracting part of the exact in-game tier values.
- building a full calculator-facing catalog of all `108` discovered mod secondary attribute families.

The result is written into a JSON file that the calculator can consume directly.

### Stage 6. Pipeline report

Each run writes:

- `<game>/decompile/pipeline_report.json`

The report contains:

- the stage list;
- per-stage duration;
- `ok/skipped/error` status;
- output file locations.

## What is already fully automated

- creating the `decompile` folder next to the game;
- extracting `script.npk`;
- incremental reruns without rewriting matching files;
- generating bindict string sidecars;
- writing a basic stage report;
- extracting mod secondary attributes into a standalone JSON.

## What is still not fully decoded

The current limit is the bindict binary tail after the string table:

- some object/reference nodes are not decoded by a fully generic parser yet;
- because of that, not every multi-stat structure and not every tier ladder is recovered directly;
- some values are still reconstructed from exact in-game points plus normalized profiles.

So the pipeline is already fully automatic at the level of `extract and build a usable research cache`, but not yet fully automatic at the level of `perfectly decode every bindict object in the game without any remaining heuristics`.

## How to run it

### CLI

```powershell
python tools/decompile_once_human.py --game-path "E:\SteamLibrary\steamapps\common\Once Human" --extract-mod-attributes
```

Incremental run against an existing `decompile` cache:

```powershell
python tools/decompile_once_human.py --game-path "E:\SteamLibrary\steamapps\common\Once Human" --skip-extract --extract-mod-attributes
```

### UI

```powershell
python tools/decompile_once_human_ui.py
```

The safe default is currently `workers=1`. Concurrent extraction on Windows still needs more stabilization.
`bindict sidecars` are also optional and not part of the default one-click path yet.

## Output layout

Example:

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

## Why this matters for the calculator

Once `decompile/` exists, it becomes a persistent local cache for future extractors:

- weapons and coefficients;
- armor and set bonuses;
- weapon attachments;
- mods and secondary attributes;
- game icons;
- some hidden mechanics when they live in script tables.

That means `decompile/` is now the base working directory for the rest of the Once Human data tooling.
