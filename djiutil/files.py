from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import os
import os.path

from tabulate import tabulate


__all__ = [
    'DJIFile', 'cleanup_low_resolution_video_files', 'cleanup_subtitle_files', 'list_dji_files_in_directory',
    'resolve_dji_directory', 'show_dji_files_in_directory',
]


DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'

LIST_TABLE_FORMAT = 'rounded_outline'
LIST_TABLE_ALIGN = ('right', 'center', 'center', 'center', 'center')
LIST_TABLE_HEADERS = ['#', 'LRF', 'SRT', 'Created', 'Size']

GAP_THRESHOLD_SECONDS = 10 * 60  # 10 minutes

# DJI firmware creates a directory structure like the following:
# /
# ├── DCIM
# │   └── DJI_001
# │       ├── DJI_20230828172510_0001_D.LRF
# │       ├── DJI_20230828172510_0001_D.MP4
# │       ├── DJI_20230828172510_0001_D.SRT
# │       ├── DJI_20230828172754_0002_D.LRF
# │       ├── DJI_20230828172754_0002_D.MP4
# │       ├── DJI_20230828172754_0002_D.SRT
# │       └── ...
# └── MISC
#     └── ...
DCIM_PATH = 'DCIM'
DJI_001_PATH = 'DJI_001'


@dataclass
class DJIFile:
    file_name: str
    file_ext: str
    file_created: datetime
    file_size_bytes: int
    file_index: Optional[int] = None
    has_lrf_file: bool = False
    has_srt_file: bool = False


# Auto-convert directory path if incomplete, e.g., '/Volumes/Mavic' --> '/Volumes/Mavic/DCIM/DJI_001'.
def resolve_dji_directory(dir_path: str) -> str:
    dir_contents = os.listdir(dir_path)
    if DCIM_PATH in dir_contents:
        dir_path = os.path.join(dir_path, DCIM_PATH)
        dir_contents = os.listdir(dir_path)
        if DJI_001_PATH in dir_contents:
            dir_path = os.path.join(dir_path, DJI_001_PATH)
    return dir_path


def list_dji_files_in_directory(dir_path: str) -> list[DJIFile]:
    dir_path = resolve_dji_directory(dir_path)
    video_files = set()
    lrf_files = set()
    srt_files = set()
    for path in os.listdir(dir_path):
        file_name, file_ext = os.path.splitext(os.path.basename(path))
        match file_ext.lower():
            case '.mov' | '.mp4':
                video_files.add((file_name, file_ext))
            case '.lrf':
                lrf_files.add(file_name)
            case '.srt':
                srt_files.add(file_name)

    dji_files = []
    for file_name, file_ext in video_files:
        index = None
        name_parts = file_name.split('_')
        for part in name_parts[::-1]:
            if part.isdigit():
                index = int(part)
                break
        has_lrf = file_name in lrf_files
        has_srt = file_name in srt_files
        file_info = os.stat(os.path.join(dir_path, file_name + file_ext))
        created = datetime.fromtimestamp(file_info.st_ctime)
        dji_files.append(DJIFile(file_name=file_name, file_ext=file_ext, file_created=created,
                                 file_size_bytes=file_info.st_size, file_index=index, has_lrf_file=has_lrf,
                                 has_srt_file=has_srt))
    return sorted(dji_files, key=lambda f: (f.file_created, f.file_index))


# Reference: https://stackoverflow.com/a/1094933
def format_file_size(size_in_bytes: int) -> str:
    for unit in ('B', 'K', 'M', 'G'):
        if abs(size_in_bytes) < 1024.0:
            precision = 1 if unit == 'G' or size_in_bytes < 10.0 else 0
            return f'{size_in_bytes:3.{precision}f}{unit}'
        size_in_bytes /= 1024.0
    return f'{size_in_bytes:.1f}T'


def show_dji_files_in_directory(dir_path: str) -> None:
    dji_files = list_dji_files_in_directory(dir_path)
    if not dji_files:
        print(f'No DJI files found in directory {dir_path}!')
        return

    files_table = []
    prev_file = None
    for dji_file in dji_files:
        name = dji_file.file_name if dji_file.file_index is None else f'{dji_file.file_index:,}'
        lrf = '✓' if dji_file.has_lrf_file else ''
        srt = '✓' if dji_file.has_srt_file else ''
        created = dji_file.file_created.strftime(DATETIME_FORMAT)
        size = format_file_size(dji_file.file_size_bytes)
        if prev_file and (dji_file.file_created - prev_file.file_created).total_seconds() > GAP_THRESHOLD_SECONDS:
            files_table.append(['───', '─────', '─────', '───────────────────', '────'])
        files_table.append([name, lrf, srt, created, size])
        prev_file = dji_file

    print(tabulate(files_table, headers=LIST_TABLE_HEADERS, tablefmt=LIST_TABLE_FORMAT, colalign=LIST_TABLE_ALIGN))


def cleanup_low_resolution_video_files(dir_path: str) -> None:
    cleanup_files_by_type(dir_path, file_type='LRF')


def cleanup_subtitle_files(dir_path: str) -> None:
    cleanup_files_by_type(dir_path, file_type='SRT')


def cleanup_files_by_type(dir_path: str, file_type: str) -> None:
    dir_path = resolve_dji_directory(dir_path)
    cleanup_file_ext = f'.{file_type.lower()}'
    cleanup_files = []
    total_size_bytes = 0
    for path in os.listdir(dir_path):
        file_name, file_ext = os.path.splitext(os.path.basename(path))
        if file_ext.lower() == cleanup_file_ext:
            abs_path = os.path.join(dir_path, path)
            cleanup_files.append(abs_path)
            total_size_bytes += os.stat(abs_path).st_size

    if not cleanup_files:
        print(f'No {file_type} files found in directory {dir_path}!')
        return

    files_pluralized = 'file' if len(cleanup_files) == 1 else 'files'
    pronoun = 'it' if len(cleanup_files) == 1 else 'them'
    try:
        resp = input(f'Found {len(cleanup_files)} {file_type} {files_pluralized} totaling '
                     f'{format_file_size(total_size_bytes).strip()}. Do you wish to delete {pronoun}? (y/N) ')
    except EOFError:
        resp = ''
    if resp.lower() not in {'y', 'ye', 'yes', 'yee'}:
        return

    for cleanup_file in cleanup_files:
        print(f'Deleting {cleanup_file}...')
        os.remove(cleanup_file)

    print(f'Successfully deleted {len(cleanup_files)} {file_type} {files_pluralized}.')


def import_files(dir_path: str, include_srt_files: bool = False) -> None:
    pass  # TODO