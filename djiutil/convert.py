from datetime import datetime, timezone
from typing import Any, Optional
from xml.etree import ElementTree as ET
import os.path
import re

import srt

from djiutil.files import file_exts


# Sample DJI SRT data:
# FrameCnt: 6469, DiffTime: 16ms
# 2023-08-28 17:26:58.889
# [iso: 160] [shutter: 1/297.91] [fnum: 2.8] [ev: 0] [color_md: default] [focal_len: 24.00] [latitude: 36.27423] [longitude: -41.36214] [rel_alt: 46.000 abs_alt: 19.621] [ct: 5895]


__all__ = ['DJIRecord', 'convert_srt_to_gpx', 'parse_dji_subtitle', 'parse_dji_subtitles']


FRAME_RE = re.compile(r'FrameCnt: (?P<frame_count>\d+), DiffTime: (?P<diff_time>\d+)ms')
HTML_RE = re.compile('<[^<]+?>')
TAG_RE = re.compile(r'\[(?P<data>[^[]+?)]')

FLOAT_TAG_KEYS = {'fnum', 'focal_len'}
INT_TAG_KEYS = {'ct', 'ev', 'iso'}

ELEVATION_KEY = 'rel_alt'

GPX_DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
GPX_VERSION = '1.1'
GPX_XMLNS = 'https://www.topografix.com/GPX/1/1'

# Type aliases.
DJIRecord = dict[str, Any]


def parse_dji_subtitle(subtitle: srt.Subtitle) -> DJIRecord:
    stripped = HTML_RE.sub('', subtitle.content).strip()
    lines = stripped.splitlines()
    if len(lines) != 3:
        raise ValueError(f'Unexpected format for SRT record: expected 3 lines but got {len(lines)}!\n{stripped}')
    if (match := FRAME_RE.match(lines[0])) is None:
        raise ValueError(f'Unexpected first line in SRT record: {lines[0]}')
    dji_data = {
        'frame_count': int(match.group('frame_count')),
        'diff_time_ms': int(match.group('diff_time')),
        'timestamp': datetime.strptime(lines[1], '%Y-%m-%d %H:%M:%S.%f'),
    }

    # One tag (set of square brackets) may contain multiple key/value pairs!
    # Example: [rel_alt: 46.000 abs_alt: 19.621]
    for tag in TAG_RE.findall(lines[2]):
        items = tag.split()
        if len(items) % 2 > 0:
            raise ValueError(f'Invalid metadata tag in SRT record: {tag}')
        key = None
        for i, item in enumerate(items):
            if i % 2 == 0:
                key = item.rstrip(':')
            else:
                if key in FLOAT_TAG_KEYS:
                    item = float(item)
                elif key in INT_TAG_KEYS:
                    item = int(item)
                dji_data[key] = item

    return dji_data


def parse_dji_subtitles(subtitles: list[srt.Subtitle]) -> list[DJIRecord]:
    frame_count = 1
    records = []
    for subtitle in subtitles:
        record = parse_dji_subtitle(subtitle)
        if record['frame_count'] != frame_count:
            raise ValueError(f'Unexpected frame count: expected {frame_count} but got {record["frame_count"]}!')
        frame_count += 1
        records.append(record)
    return records


# Reference: https://www.topografix.com/gpx/1/1/
def build_gpx_document(records: list[DJIRecord]) -> ET.ElementTree:
    root = ET.Element('gpx', version=GPX_VERSION, creator='djiutil', xmlns=GPX_XMLNS)
    track = ET.SubElement(root, 'trk')
    name = ET.SubElement(track, 'name')
    name.text = 'Track 1'
    segment = ET.SubElement(track, 'trkseg')
    for record in records:
        point = ET.SubElement(segment, 'trkpt', lat=record['latitude'], lon=record['longitude'])
        time = ET.SubElement(point, 'time')
        time.text = record['timestamp'].astimezone(timezone.utc).strftime(GPX_DATETIME_FORMAT)
        if ELEVATION_KEY in record:
            ele = ET.SubElement(point, 'ele')
            ele.text = record[ELEVATION_KEY]
    return ET.ElementTree(root)


def convert_srt_to_gpx(srt_file_path: str, gpx_file_path: Optional[str] = None) -> None:
    if os.path.isdir(srt_file_path):
        if gpx_file_path:
            raise ValueError('Must not provide gpx_file_path when converting a directory of SRT files!')
        srt_files = [
            os.path.join(srt_file_path, p)
            for p in os.listdir(srt_file_path)
            if p.lower().endswith(file_exts.SRT)
        ]
    else:
        srt_files = [srt_file_path]

    for srt_path in srt_files:
        print(f'Loading records from {srt_path}...')
        with open(srt_path) as srt_file:
            srt_data = srt_file.read()

        subtitles = list(srt.parse(srt_data))
        records = parse_dji_subtitles(subtitles)
        print(f'Loaded {len(subtitles):,} records from {srt_path}.')

        if gpx_file_path is None:
            base_path, _ = os.path.splitext(srt_path)
            gpx_path = f'{base_path}.gpx'
        else:
            gpx_path = gpx_file_path

        xml = build_gpx_document(records)
        with open(gpx_path, 'wb') as gpx_file:
            xml.write(gpx_file, xml_declaration=True, encoding='utf-8')
        print(f'Successfully wrote {gpx_path}.')
