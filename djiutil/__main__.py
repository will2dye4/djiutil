# TODO:
# - mode to clean up .LRF (low-resolution video) files on a mounted volume
# - mode to list files from a mounted volume
# - mode to import specified or all files from a mounted volume (with or without .SRT files)
# - mode to process .SRT (flight data subtitle) files (convert to GPX, then render to video?)

# Resources:
# - https://github.com/time4tea/gopro-dashboard-overlay

from typing import Optional
import argparse
import sys

from djiutil.convert import convert_srt_to_gpx


def main(args: Optional[list[str]] = None) -> None:
    if args is None:
        args = sys.argv[1:]
    parser = argparse.ArgumentParser(description='manipulate files created by DJI drones')
    subparsers = parser.add_subparsers()
    convert_parser = subparsers.add_parser('convert', help='convert DJI subtitle files to GPX format')
    convert_parser.add_argument('srt_file_path', help='path to the subtitle (.srt) file to convert')
    convert_parser.add_argument('gpx_file_path', nargs='?',
                                help='output GPX file path (inferred from srt_file_path if not specified)')
    config = parser.parse_args(args)
    if config.srt_file_path:
        convert_srt_to_gpx(config.srt_file_path, config.gpx_file_path)


if __name__ == '__main__':
    main()
