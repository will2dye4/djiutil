from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
import json
import os
import os.path
import re
import subprocess
import types

from tabulate import tabulate, SEPARATING_LINE


__all__ = [
    'DateFilter', 'DJIFile', 'JSON_OUTPUT_FORMAT', 'PLAIN_OUTPUT_FORMAT', 'cleanup_low_resolution_video_files',
    'cleanup_subtitle_files', 'file_exts', 'import_files', 'list_dji_files_in_directory', 'play_video_file',
    'resolve_dji_directory', 'show_dji_files_in_directory',
]


DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'

JSON_OUTPUT_FORMAT = 'json'
PLAIN_OUTPUT_FORMAT = 'plain'

DEFAULT_TABLE_FORMAT = 'rounded_outline'
PLAIN_TABLE_FORMAT = 'simple'

LIST_TABLE_ALIGN = ['right', 'center', 'center', 'center', 'center']
LIST_TABLE_HEADERS = ['#', 'LRF', 'SRT', 'Created', 'Size']

GAP_THRESHOLD_SECONDS = 10 * 60  # 10 minutes

file_exts = types.SimpleNamespace()
file_exts.LRF = '.lrf'
file_exts.MOV = '.mov'
file_exts.MP4 = '.mp4'
file_exts.SRT = '.srt'

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

RSYNC_VERSION_PATTERN = re.compile(r'rsync\s+version\s+(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)')


@dataclass
class DJIFile:
    file_name: str
    file_ext: str
    file_created: datetime
    file_size_bytes: int
    file_index: Optional[int] = None
    has_lrf_file: bool = False
    has_srt_file: bool = False

    @property
    def file_path(self) -> str:
        return self.file_name + self.file_ext

    @property
    def srt_file_path(self) -> Optional[str]:
        if self.has_srt_file:
            return self.file_name + file_exts.SRT
        return None


@dataclass
class DateFilter:
    min_date: Optional[datetime] = None
    max_date: Optional[datetime] = None

    _DAYS_PER_MONTH = 30
    _DAYS_PER_YEAR = 365
    _PATTERN = re.compile(
        r'^((?P<match_type>[<>])(?P<age>\d+)(?P<unit>[dhmwy])|(?P<date>\d{4}-\d{2}-\d{2}))$',
        re.IGNORECASE
    )

    @classmethod
    def parse(cls, date_filter: str) -> 'DateFilter':
        date_filter = (date_filter or '').strip()
        if (filter_match := cls._PATTERN.match(date_filter)) is None:
            raise ValueError(f'Invalid date filter "{date_filter}": must be like "<1d" or ">1w" or "2023-08-28"')
        if date := filter_match.group('date'):
            min_date = datetime.strptime(date, '%Y-%m-%d')
            max_date = min_date + timedelta(days=1)
            return DateFilter(min_date, max_date)
        age = int(filter_match.group('age'))
        if age == 0:
            raise ValueError(f'Invalid date filter "{date_filter}": age must not be zero')
        filter_delta = None
        match filter_match.group('unit'):
            case 'h':
                filter_delta = timedelta(hours=age)
            case 'd':
                filter_delta = timedelta(days=age)
            case 'w':
                filter_delta = timedelta(weeks=age)
            case 'm':
                filter_delta = timedelta(days=cls._DAYS_PER_MONTH * age)
            case 'y':
                filter_delta = timedelta(days=cls._DAYS_PER_YEAR * age)
        if filter_delta is None:
            raise ValueError(f'Invalid date filter "{date_filter}": unit must be one of "d", "h", "m", "w", or "y"')
        filter_date = datetime.now() - filter_delta
        min_date = max_date = None
        if filter_match.group('match_type') == '<':
            min_date = filter_date
        else:
            max_date = filter_date
        return DateFilter(min_date, max_date)

    def matches(self, date: datetime) -> bool:
        return (self.min_date is None or date >= self.min_date) and (self.max_date is None or date <= self.max_date)


# Auto-convert directory path if incomplete, e.g., '/Volumes/Mavic' --> '/Volumes/Mavic/DCIM/DJI_001'.
def resolve_dji_directory(dir_path: str) -> str:
    dir_contents = os.listdir(dir_path)
    if DCIM_PATH in dir_contents:
        dir_path = os.path.join(dir_path, DCIM_PATH)
        dir_contents = os.listdir(dir_path)
        if DJI_001_PATH in dir_contents:
            dir_path = os.path.join(dir_path, DJI_001_PATH)
    return dir_path


def list_dji_files_in_directory(dir_path: str, date_filter: Optional[DateFilter] = None) -> list[DJIFile]:
    dir_path = resolve_dji_directory(dir_path)
    video_files = set()
    lrf_files = set()
    srt_files = set()
    for path in os.listdir(dir_path):
        if path.startswith('.'):
            continue
        file_name, file_ext = os.path.splitext(os.path.basename(path))
        match file_ext.lower():
            case file_exts.MOV | file_exts.MP4:
                video_files.add((file_name, file_ext))
            case file_exts.LRF:
                lrf_files.add(file_name)
            case file_exts.SRT:
                srt_files.add(file_name)

    dji_files = []
    for file_name, file_ext in video_files:
        file_info = os.stat(os.path.join(dir_path, file_name + file_ext))
        created = datetime.fromtimestamp(file_info.st_ctime)
        if date_filter is None or date_filter.matches(created):
            index = None
            name_parts = file_name.split('_')
            for part in name_parts[::-1]:
                if part.isdigit():
                    index = int(part)
                    break
            has_lrf = file_name in lrf_files
            has_srt = file_name in srt_files
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


def format_dji_files_as_table(dir_path: str, dji_files: list[DJIFile], include_file_path: bool = False,
                              output_format: Optional[str] = None) -> str:
    output_format = (output_format or '').lower()
    table_format = PLAIN_TABLE_FORMAT if output_format == PLAIN_OUTPUT_FORMAT else DEFAULT_TABLE_FORMAT
    headers = LIST_TABLE_HEADERS.copy()
    col_align = LIST_TABLE_ALIGN.copy()
    path_divider = None
    if include_file_path:
        headers.append('Video File Path')
        col_align.append('left')
        if not output_format:
            path_divider = '─' * len(os.path.join(dir_path, dji_files[0].file_path))

    files_table = []
    prev_file = None
    for dji_file in dji_files:
        name = dji_file.file_name if dji_file.file_index is None else f'{dji_file.file_index:,}'
        lrf = '✓' if dji_file.has_lrf_file else ''
        srt = '✓' if dji_file.has_srt_file else ''
        created = dji_file.file_created.strftime(DATETIME_FORMAT)
        size = format_file_size(dji_file.file_size_bytes)
        if prev_file and (dji_file.file_created - prev_file.file_created).total_seconds() > GAP_THRESHOLD_SECONDS:
            if output_format == PLAIN_OUTPUT_FORMAT:
                divider_row = SEPARATING_LINE
            else:
                divider_row = ['───', '─────', '─────', '───────────────────', '────']
                if include_file_path:
                    divider_row.append(path_divider)
            files_table.append(divider_row)
        file_row = [name, lrf, srt, created, size]
        if include_file_path:
            file_row.append(os.path.join(dir_path, dji_file.file_path))
        files_table.append(file_row)
        prev_file = dji_file

    return tabulate(files_table, headers=headers, tablefmt=table_format, colalign=col_align)


def format_dji_files_as_json(dir_path: str, dji_files: list[DJIFile], include_file_path: bool = False) -> str:
    json_files = []
    for dji_file in dji_files:
        json_file = {
            'index': dji_file.file_index,
            'has_lrf': dji_file.has_lrf_file,
            'has_srt': dji_file.has_srt_file,
            'created': dji_file.file_created.isoformat(),
            'size': format_file_size(dji_file.file_size_bytes),
            'size_in_bytes': dji_file.file_size_bytes,
        }
        if include_file_path:
            json_file['path'] = os.path.join(dir_path, dji_file.file_path)
        json_files.append(json_file)
    return json.dumps(json_files)


def show_dji_files_in_directory(dir_path: str, date_filter: Optional[DateFilter] = None,
                                include_file_path: bool = False, output_format: Optional[str] = None) -> None:
    dir_path = resolve_dji_directory(dir_path)
    dji_files = list_dji_files_in_directory(dir_path, date_filter)
    if not dji_files:
        filter_error = f' matching the provided date filter' if date_filter else ''
        print(f'No DJI files found in directory {dir_path}{filter_error}!')
        return

    output_format = (output_format or '').lower()
    if output_format == JSON_OUTPUT_FORMAT:
        output = format_dji_files_as_json(dir_path, dji_files, include_file_path)
    else:
        output = format_dji_files_as_table(dir_path, dji_files, include_file_path, output_format)
    print(output)


def cleanup_low_resolution_video_files(dir_path: str, assume_yes: bool = False) -> None:
    cleanup_files_by_type(dir_path, file_type='LRF', assume_yes=assume_yes)


def cleanup_subtitle_files(dir_path: str, assume_yes: bool = False) -> None:
    cleanup_files_by_type(dir_path, file_type='SRT', assume_yes=assume_yes)


def cleanup_files_by_type(dir_path: str, file_type: str, assume_yes: bool = False) -> None:
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
    if assume_yes:
        print(f'Deleting {len(cleanup_files):,} {file_type} {files_pluralized} totaling '
              f'{format_file_size(total_size_bytes).strip()}...')
    else:
        try:
            resp = input(f'Found {len(cleanup_files):,} {file_type} {files_pluralized} totaling '
                         f'{format_file_size(total_size_bytes).strip()}. Do you wish to delete {pronoun}? (y/N) ')
        except EOFError:
            resp = ''
        if resp.lower() not in {'y', 'ye', 'yes', 'yee'}:
            return

    for cleanup_file in cleanup_files:
        print(f'Deleting {cleanup_file}...')
        os.remove(cleanup_file)

    print(f'Successfully deleted {len(cleanup_files)} {file_type} {files_pluralized}.')


def check_rsync_major_version() -> int:
    which_result = subprocess.run(['which', 'rsync'], stdout=subprocess.DEVNULL)
    if which_result.returncode != 0:
        raise RuntimeError('Must have rsync installed to import files!')
    version_result = subprocess.run(['rsync', '--version'], capture_output=True)
    for line in version_result.stdout.splitlines():
        if match := RSYNC_VERSION_PATTERN.match(line.decode('utf-8')):
            return int(match.group('major'))
    raise RuntimeError('Failed to parse `rsync --version` output!')


def import_files(dir_path: str, dest_path: str, date_filter: Optional[DateFilter] = None,
                 index_numbers: Optional[list[int]] = None, include_srt_files: bool = False,
                 assume_yes: bool = False) -> None:
    if date_filter and index_numbers:
        raise ValueError(f'Must provide either date_filter or index_numbers, but not both!')

    dir_path = resolve_dji_directory(dir_path)
    dji_files = list_dji_files_in_directory(dir_path, date_filter)
    if index_numbers:
        dji_files = [f for f in dji_files if f.file_index in index_numbers]
    if not dji_files:
        filter_error = ' matching the provided date filter' if date_filter else ''
        index_error = ' matching the provided indices' if index_numbers else ''
        print(f'No DJI files found in directory {dir_path}{filter_error}{index_error}!')
        return

    srt_count = 0
    srt_result = ''
    if include_srt_files:
        srt_count = sum(1 for f in dji_files if f.has_srt_file)
        srt_result = f' (+ {srt_count:,} SRT {"file" if srt_count == 1 else "files"})'

    files_pluralized = 'file' if len(dji_files) == 1 else 'files'
    pronoun = 'it' if len(dji_files) == 1 and srt_count == 0 else 'them'
    total_size_bytes = sum(f.file_size_bytes for f in dji_files)
    if assume_yes:
        print(f'Importing {len(dji_files):,} video {files_pluralized} totaling '
              f'{format_file_size(total_size_bytes).strip()}{srt_result}...')
    else:
        try:
            resp = input(f'Found {len(dji_files):,} video {files_pluralized} totaling '
                         f'{format_file_size(total_size_bytes).strip()}{srt_result}. Do you wish to import {pronoun}? '
                         '(Y/n) ')
        except EOFError:
            resp = ''
        if resp.lower() in {'n', 'no', 'nope'}:
            return

    if not os.path.exists(dest_path):
        print(f'Creating directory {dest_path}...')
        os.makedirs(dest_path)

    file_paths = [os.path.join(dir_path, f.file_path) for f in dji_files]
    if include_srt_files:
        file_paths.extend([os.path.join(dir_path, f.srt_file_path) for f in dji_files if f.has_srt_file])

    rsync_version = check_rsync_major_version()
    rsync_args = [
        'rsync', '-a', '-h',
        '--info=progress2' if rsync_version >= 3 else '--progress',
        *file_paths,
        dest_path,
    ]
    subprocess.run(rsync_args)


def play_video_file(dir_path: str, index: int) -> None:
    dir_path = resolve_dji_directory(dir_path)
    dji_files = list_dji_files_in_directory(dir_path)
    if (dji_file := next((f for f in dji_files if f.file_index == index), None)) is None:
        print(f'Failed to find video file with index #{index} in directory {dir_path}!')
        return
    file_path = os.path.join(dir_path, dji_file.file_path)
    print(f'Opening {file_path}...')
    subprocess.Popen(['open', file_path])
