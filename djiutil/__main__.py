# TODO:
# - mode to process .SRT (flight data subtitle) files (convert to GPX, then render to video?)
#
# Resources:
# - https://github.com/time4tea/gopro-dashboard-overlay

from functools import lru_cache
from typing import Any, Optional
import argparse
import json
import os
import sys
import types

from djiutil.convert import convert_srt_to_gpx
from djiutil.files import (
    DateFilter,
    JSON_OUTPUT_FORMAT,
    PLAIN_OUTPUT_FORMAT,
    cleanup_all_files,
    cleanup_low_resolution_video_files,
    cleanup_subtitle_files,
    cleanup_video_files,
    import_files,
    play_video_file,
    show_dji_files_in_directory,
)


commands = types.SimpleNamespace()
commands.CLEANUP = 'cleanup'
commands.CONVERT = 'convert'
commands.IMPORT = 'import'
commands.LIST = 'list'
commands.PLAY = 'play'

CLEANUP_FUNCTIONS = {
    'all': cleanup_all_files,
    'lrf': cleanup_low_resolution_video_files,
    'srt': cleanup_subtitle_files,
    'video': cleanup_video_files,
}

DEFAULT_CONFIG_FILE_PATH = '~/.djiutil.json'

DIR_PATH_CONFIG_KEY = 'dji_dir_path'
DIR_PATH_ENVIRONMENT_KEY = 'DJIUTIL_DIR_PATH'


# Type aliases.
JSONConfig = dict[str, Any]


@lru_cache(maxsize=32)
def load_config_file(file_path: str = DEFAULT_CONFIG_FILE_PATH) -> Optional[JSONConfig]:
    file_path = os.path.expanduser(file_path)
    if not os.path.exists(file_path):
        return None
    with open(file_path) as f:
        return json.load(f)


def resolve_dir_path(cli_config: argparse.Namespace) -> Optional[str]:
    if cli_dir_path := getattr(cli_config, 'dir_path', None):  # Highest precedence: provided on the command line.
        return cli_dir_path
    if DIR_PATH_ENVIRONMENT_KEY in os.environ:  # Second-highest precedence: environment variable.
        return os.environ[DIR_PATH_ENVIRONMENT_KEY]
    if (file_config := load_config_file()) and DIR_PATH_CONFIG_KEY in file_config:  # Lowest precedence: config file.
        return file_config[DIR_PATH_CONFIG_KEY]
    return None


def create_parsers() -> tuple[argparse.ArgumentParser, dict[str, argparse.ArgumentParser]]:
    parser = argparse.ArgumentParser(description='manipulate files created by DJI drones')
    subparsers = parser.add_subparsers(dest='command')
    command_parsers = {}

    cleanup_parser = subparsers.add_parser(commands.CLEANUP, help='clean up unwanted DJI files (LRF, SRT, etc.)')
    cleanup_parser.add_argument('file_type', choices=('lrf', 'srt', 'video', 'all'),
                                help='type of files to clean up (video includes .mov and .mp4 files)')
    cleanup_parser.add_argument('dir_path', nargs='?', help='path to the directory where DJI files are located')
    cleanup_filter_group = cleanup_parser.add_mutually_exclusive_group()
    cleanup_filter_group.add_argument('-d', '--date-filter', type=DateFilter.parse,
                                      help='filter deleted files by date or age (examples: "<1d", ">1w", "2023-08-28").'
                                           ' Supported units are: h (hours), d (days), w (weeks), m (months), and'
                                           ' y (years).')
    cleanup_filter_group.add_argument('-i', '--index', '--index-numbers',
                                      help='index number(s) of the video file(s) to delete, as returned by the list '
                                           'subcommand (examples: "1-4", "5,7,8", "21-23,26-29,32")')
    cleanup_parser.add_argument('-y', '--yes', '--assume-yes', action='store_true',
                                help='skip user confirmation before cleaning up files (default: false)')
    command_parsers[commands.CLEANUP] = cleanup_parser

    convert_parser = subparsers.add_parser(commands.CONVERT, help='convert DJI subtitle files to GPX format')
    convert_parser.add_argument('srt_file_path',
                                help='path to the subtitle (.srt) file to convert, '
                                     'or a directory where subtitle files are located')
    convert_parser.add_argument('gpx_file_path', nargs='?',
                                help='output GPX file path (inferred from srt_file_path if not specified)')
    command_parsers[commands.CONVERT] = convert_parser

    import_parser = subparsers.add_parser(commands.IMPORT, help='import DJI video and subtitle files')
    import_parser.add_argument('dir_path', nargs='?', help='path to the directory where DJI files are located')
    import_parser.add_argument('dest_path', help='path to the directory to import the files to')
    import_filter_group = import_parser.add_mutually_exclusive_group()
    import_filter_group.add_argument('-d', '--date-filter', type=DateFilter.parse,
                                     help='filter imported files by date or age (examples: "<1d", ">1w", "2023-08-28").'
                                          ' Supported units are: h (hours), d (days), w (weeks), m (months), and'
                                          ' y (years).')
    import_filter_group.add_argument('-i', '--index', '--index-numbers',
                                     help='index number(s) of the video file(s) to import, as returned by the list '
                                          'subcommand (examples: "1-4", "5,7,8", "21-23,26-29,32")')
    import_parser.add_argument('-s', '--srt', '--include-srt', action='store_true',
                               help='import SRT (subtitle) files in addition to video files (default: false)')
    import_parser.add_argument('-y', '--yes', '--assume-yes', action='store_true',
                               help='skip user confirmation before importing files (default: false)')
    command_parsers[commands.IMPORT] = import_parser

    list_parser = subparsers.add_parser(commands.LIST, help='list DJI files in a directory')
    list_parser.add_argument('dir_path', nargs='?', help='path to the directory where DJI files are located')
    list_filter_group = list_parser.add_mutually_exclusive_group()
    list_filter_group.add_argument('-d', '--date-filter', type=DateFilter.parse,
                                   help='filter results by date or age (examples: "<1d", ">1w", "2023-08-28").'
                                   ' Supported units are: h (hours), d (days), w (weeks), m (months), and'
                                   ' y (years).')
    list_filter_group.add_argument('-i', '--index', '--index-numbers',
                                   help='index number(s) of the video file(s) to import, as returned by the list '
                                        'subcommand (examples: "1-4", "5,7,8", "21-23,26-29,32")')
    list_parser.add_argument('-o', '--output', '--output-format',
                             choices=(JSON_OUTPUT_FORMAT, PLAIN_OUTPUT_FORMAT),
                             help='desired output format (plain format or JSON); default: pretty tabular format')
    list_parser.add_argument('-p', '--include-file-path', action='store_true',
                             help='include video file paths in the listing (default: false)')
    command_parsers[commands.LIST] = list_parser

    play_parser = subparsers.add_parser(commands.PLAY, help='play a DJI video file by index number')
    play_parser.add_argument('dir_path', nargs='?', help='path to the directory where DJI files are located')
    play_parser.add_argument('play_index', metavar='index', type=int,
                             help='index number of the video file to play (as returned by the list subcommand)')
    command_parsers[commands.PLAY] = play_parser

    return parser, command_parsers


def parse_index_numbers(index_str: Optional[str]) -> Optional[list[int]]:
    if not index_str:
        return None

    index_numbers = []
    index_parts = index_str.strip().split(',')
    for part in index_parts:
        index_range = part.strip().split('-')
        if len(index_range) == 1:
            index_numbers.append(int(index_range[0]))
        elif len(index_range) == 2:
            range_start, range_end = index_range
            index_numbers.extend(list(range(int(range_start), int(range_end) + 1)))
        else:
            raise ValueError(f'Invalid index value "{part}": expected a single index like "23" or a range like "1-4"')
    return sorted(index_numbers)


def main(args: Optional[list[str]] = None) -> None:
    if args is None:
        args = sys.argv[1:]

    top_level_parser, command_parsers = create_parsers()
    config = top_level_parser.parse_args(args)
    date_filter = getattr(config, 'date_filter', None)
    index_numbers = parse_index_numbers(getattr(config, 'index', None))

    dir_path = None
    if config.command != commands.CONVERT:  # All commands except 'convert' require a dir_path.
        if not (dir_path := resolve_dir_path(config)):
            command_parsers[config.command].print_usage()
            return
        dir_path = os.path.expanduser(dir_path)
        if not os.path.exists(dir_path):
            print(f'Failed to locate directory {dir_path}!')
            sys.exit(1)

    match config.command:
        case commands.CLEANUP:
            if not (cleanup := CLEANUP_FUNCTIONS.get(config.file_type)):
                command_parsers[config.command].print_usage()
                return
            cleanup(dir_path, date_filter=date_filter, index_numbers=index_numbers, assume_yes=config.yes)
        case commands.CONVERT:
            convert_srt_to_gpx(config.srt_file_path, config.gpx_file_path)
        case commands.IMPORT:
            import_files(
                dir_path,
                config.dest_path,
                date_filter=date_filter,
                index_numbers=index_numbers,
                include_srt_files=config.srt,
                assume_yes=config.yes,
            )
        case commands.LIST:
            show_dji_files_in_directory(
                dir_path,
                date_filter=date_filter,
                index_numbers=index_numbers,
                include_file_path=config.include_file_path,
                output_format=getattr(config, 'output', None),
            )
        case commands.PLAY:
            play_video_file(dir_path, config.play_index)
        case _:
            top_level_parser.print_usage()


if __name__ == '__main__':
    main()
