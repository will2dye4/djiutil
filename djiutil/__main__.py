# TODO:
# - mode to process .SRT (flight data subtitle) files (convert to GPX, then render to video?)
#
# Resources:
# - https://github.com/time4tea/gopro-dashboard-overlay

from typing import Callable, Optional
import argparse
import sys

from djiutil.convert import convert_srt_to_gpx
from djiutil.files import (
    DateFilter,
    JSON_OUTPUT_FORMAT,
    PLAIN_OUTPUT_FORMAT,
    cleanup_low_resolution_video_files,
    cleanup_subtitle_files,
    import_files,
    play_video_file,
    show_dji_files_in_directory,
)


# Type aliases.
UsageFn = Callable[[], None]


def parse_args(args: list[str]) -> tuple[argparse.Namespace, UsageFn]:
    parser = argparse.ArgumentParser(description='manipulate files created by DJI drones')
    subparsers = parser.add_subparsers()

    cleanup_parser = subparsers.add_parser('cleanup', help='clean up unwanted DJI files (LRF, SRT, etc.)')
    cleanup_parser.add_argument('file_type', choices=('lrf', 'srt'), help='type of files to clean up')
    cleanup_parser.add_argument('cleanup_dir_path', metavar='dir_path',
                                help='path to the directory where DJI files are located')
    cleanup_parser.add_argument('-y', '--yes', '--assume-yes', action='store_true',
                                help='skip user confirmation before cleaning up files (default: false)')

    convert_parser = subparsers.add_parser('convert', help='convert DJI subtitle files to GPX format')
    convert_parser.add_argument('srt_file_path',
                                help='path to the subtitle (.srt) file to convert, '
                                     'or a directory where subtitle files are located')
    convert_parser.add_argument('gpx_file_path', nargs='?',
                                help='output GPX file path (inferred from srt_file_path if not specified)')

    import_parser = subparsers.add_parser('import', help='import DJI video and subtitle files')
    import_parser.add_argument('import_dir_path', metavar='dir_path',
                               help='path to the directory where DJI files are located')
    import_parser.add_argument('import_dest_path', metavar='dest_path',
                               help='path to the directory to import the files to')
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

    list_parser = subparsers.add_parser('list', help='list DJI files in a directory')
    list_parser.add_argument('list_dir_path', metavar='dir_path',
                             help='path to the directory where DJI files are located')
    list_parser.add_argument('-d', '--date-filter', type=DateFilter.parse,
                             help='filter results by date or age (examples: "<1d", ">1w", "2023-08-28").'
                                  ' Supported units are: h (hours), d (days), w (weeks), m (months), and'
                                  ' y (years).')
    list_parser.add_argument('-o', '--output', '--output-format',
                             choices=(JSON_OUTPUT_FORMAT, PLAIN_OUTPUT_FORMAT),
                             help='desired output format (plain format or JSON); default: pretty tabular format')
    list_parser.add_argument('-p', '--include-file-path', action='store_true',
                             help='include video file paths in the listing (default: false)')

    play_parser = subparsers.add_parser('play', help='play a DJI video file by index number')
    play_parser.add_argument('play_dir_path', metavar='dir_path',
                             help='path to the directory where DJI files are located')
    play_parser.add_argument('play_index', metavar='index', type=int,
                             help='index number of the video file to play (as returned by the list subcommand)')

    return parser.parse_args(args), parser.print_usage


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

    config, print_usage = parse_args(args)
    if hasattr(config, 'cleanup_dir_path'):
        if config.file_type == 'lrf':
            cleanup_low_resolution_video_files(config.cleanup_dir_path, assume_yes=config.yes)
        elif config.file_type == 'srt':
            cleanup_subtitle_files(config.cleanup_dir_path, assume_yes=config.yes)
        else:
            print_usage()
    elif hasattr(config, 'srt_file_path'):
        convert_srt_to_gpx(config.srt_file_path, config.gpx_file_path)
    elif hasattr(config, 'import_dir_path'):
        index_numbers = parse_index_numbers(getattr(config, 'index', None))
        import_files(
            config.import_dir_path,
            config.import_dest_path,
            date_filter=getattr(config, 'date_filter', None),
            index_numbers=index_numbers,
            include_srt_files=config.srt,
            assume_yes=config.yes,
        )
    elif hasattr(config, 'list_dir_path'):
        show_dji_files_in_directory(
            config.list_dir_path,
            date_filter=getattr(config, 'date_filter', None),
            include_file_path=config.include_file_path,
            output_format=getattr(config, 'output', None),
        )
    elif hasattr(config, 'play_dir_path'):
        play_video_file(config.play_dir_path, config.play_index)
    else:
        print_usage()


if __name__ == '__main__':
    main()
