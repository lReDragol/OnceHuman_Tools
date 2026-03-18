#!/usr/bin/env python3
from __future__ import annotations

import argparse
import concurrent.futures
import json
import marshal
import mmap
import os
import struct
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import zstandard as zstd

RECORD_SIZE = 0x1C


@dataclass(frozen=True)
class NpkEntry:
    index: int
    name: str
    misc1: int
    offset: int
    zsize: int
    size: int
    misc2: int
    misc3: int
    comp_type: int


def parse_names(data: bytes, files: int, names_off: int) -> list[str]:
    names_blob = data[names_off + 16 :]
    names: list[str] = []
    current = bytearray()
    for byte in names_blob:
        if byte == 0:
            if current:
                name = bytes(current).decode('utf-8', 'ignore').replace('/', '\\')
                if name:
                    names.append(name)
                    if len(names) == files:
                        break
                current.clear()
            continue
        current.append(byte)
    if len(names) != files:
        raise RuntimeError(f'Failed to recover all entry names: got {len(names)} of {files}')
    return names


def parse_npk(data: bytes | mmap.mmap, path: Path) -> list[NpkEntry]:
    if data[:4] != b'NXPK':
        raise RuntimeError(f'{path} is not an NXPK archive')
    files = struct.unpack_from('<I', data, 4)[0]
    entry_off = struct.unpack_from('<I', data, 0x14)[0]
    names_off = entry_off + files * RECORD_SIZE + 0x10
    names = parse_names(data, files, names_off)
    entries: list[NpkEntry] = []
    for index, name in enumerate(names):
        rec_off = entry_off + index * RECORD_SIZE
        misc1, offset, zsize, size, misc2, misc3, comp_type = struct.unpack_from('<7I', data, rec_off)
        entries.append(
            NpkEntry(
                index=index,
                name=name,
                misc1=misc1,
                offset=offset,
                zsize=zsize,
                size=size,
                misc2=misc2,
                misc3=misc3,
                comp_type=comp_type,
            )
        )
    return entries


def safe_output_path(root: Path, relative_name: str) -> Path:
    parts = [part for part in relative_name.replace('/', '\\').split('\\') if part not in ('', '.', '..')]
    return root.joinpath(*parts)


def extract_payload(data: bytes | mmap.mmap, entry: NpkEntry, dctx: zstd.ZstdDecompressor) -> bytes:
    chunk = data[entry.offset : entry.offset + entry.zsize]
    if entry.zsize == entry.size:
        return chunk
    if entry.comp_type == 3:
        return dctx.decompress(chunk, max_output_size=entry.size)
    if entry.comp_type == 2:
        raise RuntimeError('LZ4-compressed entries are not supported by this extractor yet')
    raise RuntimeError(f'Unsupported compression type {entry.comp_type} for {entry.name}')


def build_bindict_sidecar(raw: bytes, output_path: Path) -> None:
    try:
        code = marshal.loads(raw[16:])
    except Exception:
        return
    if tuple(getattr(code, 'co_names', ())) != ('bindict', 'data', 'timezone_related'):
        return
    consts = getattr(code, 'co_consts', ())
    if len(consts) < 3 or not isinstance(consts[2], (bytes, bytearray)):
        return
    blob = bytes(consts[2])
    if len(blob) < 8:
        return
    count = struct.unpack_from('<I', blob, 0)[0]
    if count <= 0 or len(blob) < 8 + count * 4:
        return
    offsets = [struct.unpack_from('<I', blob, 8 + i * 4)[0] for i in range(count)]
    data_start = 8 + count * 4
    prev = 0
    strings: list[str] = []
    for end in offsets:
        if data_start + end > len(blob) or end < prev:
            break
        strings.append(blob[data_start + prev : data_start + end].decode('utf-8', 'ignore'))
        prev = end
    if not strings:
        return
    last_end = offsets[len(strings) - 1]
    sidecar = {
        'string_count': count,
        'strings_end': data_start + last_end,
        'tail_bytes': max(0, len(blob) - (data_start + last_end)),
        'strings': strings,
    }
    sidecar_path = output_path.with_suffix(output_path.suffix + '.bindict_strings.json')
    sidecar_path.write_text(json.dumps(sidecar, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def should_attempt_bindict_sidecar(output_path: Path) -> bool:
    normalized = str(output_path).replace('/', '\\').lower()
    stem = output_path.stem.lower()
    if output_path.suffix.lower() != '.pyc':
        return False
    if '\\game_common\\data\\' not in normalized:
        return False
    return stem.endswith('_data') or stem.endswith('_lib') or stem.endswith('_config')


def extract_archive(
    archive_path: Path,
    output_root: Path,
    *,
    workers: int,
    write_bindict_sidecars: bool,
) -> dict[str, Any]:
    t0 = time.time()
    raw_root = output_root / 'raw'
    raw_root.mkdir(parents=True, exist_ok=True)
    counter_lock = threading.Lock()
    progress = {'done': 0, 'written': 0, 'skipped': 0, 'errors': 0}
    dctx_local = threading.local()

    with archive_path.open('rb') as handle, mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ) as data:
        entries = parse_npk(data, archive_path)
        total = len(entries)
        print(f'Parsed {total} entries from {archive_path.name}')

        def get_dctx() -> zstd.ZstdDecompressor:
            dctx = getattr(dctx_local, 'instance', None)
            if dctx is None:
                dctx = zstd.ZstdDecompressor()
                dctx_local.instance = dctx
            return dctx

        def worker(entry: NpkEntry) -> tuple[str, str | None]:
            try:
                payload = extract_payload(data, entry, get_dctx())
                output_path = safe_output_path(raw_root, entry.name)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                if output_path.exists() and output_path.stat().st_size == len(payload):
                    status = 'skipped'
                else:
                    output_path.write_bytes(payload)
                    status = 'written'
                if write_bindict_sidecars and should_attempt_bindict_sidecar(output_path):
                    build_bindict_sidecar(payload, output_path)
                return status, None
            except Exception as exc:
                return 'error', f'{entry.name}: {exc}'

        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
            for status, error in executor.map(worker, entries, chunksize=32):
                with counter_lock:
                    progress['done'] += 1
                    if status == 'written':
                        progress['written'] += 1
                    elif status == 'skipped':
                        progress['skipped'] += 1
                    elif status == 'error':
                        progress['errors'] += 1
                    done = progress['done']
                    if done % 2000 == 0 or done == total:
                        print(
                            f'[{archive_path.name}] {done}/{total} '
                            f'written={progress["written"]} skipped={progress["skipped"]} errors={progress["errors"]}'
                        )
                if error:
                    print(error)

    manifest = {
        'archive': str(archive_path),
        'output_root': str(output_root),
        'files': total,
        'written': progress['written'],
        'skipped': progress['skipped'],
        'errors': progress['errors'],
        'duration_seconds': round(time.time() - t0, 2),
    }
    (output_root / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return manifest


def run_stage(label: str, func) -> dict[str, Any]:
    started = time.time()
    try:
        result = func()
        return {
            'stage': label,
            'status': 'ok',
            'duration_seconds': round(time.time() - started, 2),
            'result': result,
        }
    except Exception as exc:
        return {
            'stage': label,
            'status': 'error',
            'duration_seconds': round(time.time() - started, 2),
            'error': str(exc),
        }


def run_mod_attribute_extraction(decompile_dir: Path, output_path: Path) -> dict[str, Any]:
    script_path = Path(__file__).with_name('extract_once_human_mod_attributes.py')
    command = [
        sys.executable,
        str(script_path),
        '--decompile-dir',
        str(decompile_dir),
        '--output',
        str(output_path),
    ]
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    return {
        'command': command,
        'stdout': completed.stdout.strip(),
        'stderr': completed.stderr.strip(),
        'output': str(output_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description='One-click Once Human decompile pipeline. Extracts script.npk into <game>/decompile and can decode mod attributes.'
    )
    parser.add_argument('--game-path', type=Path, required=True, help='Path to the Once Human game root.')
    parser.add_argument('--output-dir', type=Path, help='Output directory. Defaults to <game-path>/decompile.')
    parser.add_argument(
        '--workers',
        type=int,
        default=1,
        help='Worker threads. Default is 1 because concurrent extraction is not fully stable on Windows yet.',
    )
    parser.add_argument(
        '--bindict-sidecars',
        action='store_true',
        help='Generate experimental bindict string sidecars for recognized data tables.',
    )
    parser.add_argument('--skip-extract', action='store_true', help='Skip NXPK extraction and only run later stages against an existing decompile folder.')
    parser.add_argument('--extract-mod-attributes', action='store_true', help='Run mod secondary attribute extraction after decompile.')
    parser.add_argument('--mod-attributes-output', type=Path, help='Output JSON path for extracted mod attribute metadata.')
    parser.add_argument('--report-output', type=Path, help='Pipeline report path. Defaults to <output-dir>/pipeline_report.json.')
    args = parser.parse_args()

    game_path = args.game_path.resolve()
    output_dir = (args.output_dir or (game_path / 'decompile')).resolve()
    report_output = (args.report_output or (output_dir / 'pipeline_report.json')).resolve()
    mod_attributes_output = args.mod_attributes_output.resolve() if args.mod_attributes_output else (output_dir / 'mod_secondary_attributes.json')
    output_dir.mkdir(parents=True, exist_ok=True)

    stages: list[dict[str, Any]] = []
    archives = [
        ('root_script', game_path / 'script.npk'),
        ('documents_script', game_path / 'Documents' / 'script.npk'),
    ]

    if not args.skip_extract:
        for label, archive_path in archives:
            if not archive_path.exists():
                stages.append(
                    {
                        'stage': f'extract:{label}',
                        'status': 'skipped',
                        'reason': f'Missing archive: {archive_path}',
                    }
                )
                print(f'SKIP missing archive: {archive_path}')
                continue
            target_root = output_dir / label
            print(f'Extracting {archive_path} -> {target_root}')
            stages.append(
                run_stage(
                    f'extract:{label}',
                    lambda archive_path=archive_path, target_root=target_root: extract_archive(
                        archive_path=archive_path,
                        output_root=target_root,
                        workers=args.workers,
                        write_bindict_sidecars=args.bindict_sidecars,
                    ),
                )
            )

    if args.extract_mod_attributes:
        print(f'Extracting mod secondary attributes -> {mod_attributes_output}')
        stages.append(
            run_stage(
                'decode:mod_secondary_attributes',
                lambda: run_mod_attribute_extraction(output_dir, mod_attributes_output),
            )
        )

    summary = {
        'game_path': str(game_path),
        'output_dir': str(output_dir),
        'bindict_sidecars': args.bindict_sidecars,
        'extract_mod_attributes': args.extract_mod_attributes,
        'stages': stages,
        'generated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
    }
    report_output.parent.mkdir(parents=True, exist_ok=True)
    report_output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Saved pipeline report to: {report_output}')
    failed = [stage for stage in stages if stage.get('status') == 'error']
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
