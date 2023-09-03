# TODO:
# - mode to import specified or all files from a mounted volume (with or without .SRT files)
# - mode to process .SRT (flight data subtitle) files (convert to GPX, then render to video?)

# Resources:
# - https://github.com/time4tea/gopro-dashboard-overlay

from typing import Callable, Optional
import argparse
import sys

from djiutil.convert import convert_srt_to_gpx
from djiutil.files import cleanup_low_resolution_video_files, cleanup_subtitle_files, show_dji_files_in_directory


# Type aliases.
UsageFn = Callable[[], None]


def parse_args(args: list[str]) -> tuple[argparse.Namespace, UsageFn]:
    parser = argparse.ArgumentParser(description='manipulate files created by DJI drones')
    subparsers = parser.add_subparsers()

    cleanup_parser = subparsers.add_parser('cleanup', help='clean up unwanted DJI files (LRF, SRT, etc.)')
    cleanup_parser.add_argument('file_type', choices=('lrf', 'srt'), help='type of files to clean up')
    cleanup_parser.add_argument('cleanup_dir_path', metavar='dir_path',
                                help='path to the directory where DJI files are located')

    convert_parser = subparsers.add_parser('convert', help='convert DJI subtitle files to GPX format')
    convert_parser.add_argument('srt_file_path', help='path to the subtitle (.srt) file to convert')
    convert_parser.add_argument('gpx_file_path', nargs='?',
                                help='output GPX file path (inferred from srt_file_path if not specified)')

    list_parser = subparsers.add_parser('list', help='list DJI files in a directory')
    list_parser.add_argument('list_dir_path', metavar='dir_path',
                             help='path to the directory where DJI files are located')

    return parser.parse_args(args), parser.print_usage


def main(args: Optional[list[str]] = None) -> None:
    if args is None:
        args = sys.argv[1:]

    config, print_usage = parse_args(args)
    if hasattr(config, 'cleanup_dir_path'):
        if config.file_type == 'lrf':
            cleanup_low_resolution_video_files(config.cleanup_dir_path)
        elif config.file_type == 'srt':
            cleanup_subtitle_files(config.cleanup_dir_path)
        else:
            print_usage()
    elif hasattr(config, 'srt_file_path'):
        convert_srt_to_gpx(config.srt_file_path, config.gpx_file_path)
    elif hasattr(config, 'list_dir_path'):
        show_dji_files_in_directory(config.list_dir_path)
    else:
        print_usage()


if __name__ == '__main__':
    main()
