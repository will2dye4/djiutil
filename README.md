# djiutil - manipulate files created by DJI drones

`djiutil` is a command-line utility and Python package for working with files created by
[DJI](https://www.dji.com) drones. The utility provides subcommands to assist with the following
tasks:

* **cleaning up** unwanted files (supports LRF, SRT, and video files)
* **converting** DJI subtitle (SRT) files to GPX format
* **importing** DJI files (video and subtitle) from a mounted volume
* **listing** DJI files on a mounted volume
* **playing** DJI video files by index number

## Installation

The easiest way to install the package is to download it from [PyPI](https://pypi.org) using `pip`.
Run the following command in a shell (a UNIX-like environment is assumed):

```
$ pip install djiutil
```

The package does depend on a few external Python packages available on PyPI. If you wish to
sandbox your installation inside a virtual environment, you may choose to use
[virtualenvwrapper](https://virtualenvwrapper.readthedocs.io/en/latest/) or a similar
utility to do so.

When successfully installed, a program called `djiutil` will be placed on your `PATH`. See the
Usage section below for details about how to use this program.

### Dependencies

* The utility expects [`rsync`](https://linux.die.net/man/1/rsync) to be installed when importing
  DJI video files. Modern distributions of Linux and macOS ship with `rsync` preinstalled, so you
  likely do not need to install it separately. However, the version that is preinstalled on macOS
  (as of macOS version 13.5) is an older version (2.x), and it is recommended to install `rsync`
  version 3 or newer (using [Homebrew](https://brew.sh) or your preferred package manager) for the
  best experience.

## Usage

The `djiutil` program is a command-line interface for working with files created by DJI drones.

At any time, you can use the `-h` or `--help` flags to see a summary of options that
the program accepts.

```
$ djiutil -h
usage: djiutil [-h] {cleanup,convert,import,list,play} ...

manipulate files created by DJI drones

positional arguments:
  {cleanup,convert,import,list,play}
    cleanup             clean up unwanted DJI files (LRF, SRT, etc.)
    convert             convert DJI subtitle files to GPX format
    import              import DJI video and subtitle files
    list                list DJI files in a directory
    play                play a DJI video file by index number

options:
  -h, --help            show this help message and exit
```

To see more details about a specific subcommand and the options that it accepts, use
`djiutil <subcommand> -h`, for example:

```
$ djiutil play -h
usage: djiutil play [-h] [dir_path] index

positional arguments:
  dir_path    path to the directory where DJI files are located
  index       index number of the video file to play (as returned by the list subcommand)

options:
  -h, --help  show this help message and exit
```

### Path Resolution

DJI drones create a directory structure like the following on their storage device (microSD or
internal SSD):

```
/
├── DCIM
│   └── DJI_001
│       └── ...
└── MISC
```

The video (and subtitle) files created by the drone are stored under the `/DCIM/DJI_001` directory.
When mounted to a computer for viewing and transferring the files, these files might be located
at a path such as `/Volumes/Mavic/DCIM/DJI_001`. For convenience, `djiutil` will resolve the path
`/Volumes/Mavic` to the path `/Volumes/Mavic/DCIM/DJI_001` automatically. You only need to specify
the path to the mount point for the storage device, not the full path to the directory where the
files are stored.

### File Filtering

Several `djiutil` subcommands support filtering DJI files by date, age, or index number. This can
be helpful when working with a subset of the files stored on a mounted volume instead of all files.

#### Filtering by Date and Age

To filter files by date, use the `-d`/`--date-filter` option. In its simplest form, this filter
accepts a date in the format `YYYY-MM-DD`, for example, `2023-08-28`. When used in this way, this
filter selects only files created on the specified date.

The `-d` option also supports filtering files by age, using the syntax `("<"|">")<value><unit>`.
For example, `<1d` selects only files created within the past day, while `>3m` selects only files
created more than three months ago. Supported units are: `h` (hours), `d` (days), `w` (weeks),
`m` (months), and `y` (years). Note that the argument passed to `-d` must be quoted when using the
age syntax, since `<` and `>` have special meaning to the shell for input/output redirection.

#### Filtering by File Index

DJI drones assign an incrementing index number to each set of files they create. This index number
is displayed by the `djiutil list` subcommand. The `-i`/`--index`/`--index-numbers` option may be
used with other subcommands to select specific files by index.

The argument passed to `-i` may be a single index (e.g., `12`), a range of indices separated by a
hyphen (e.g., `5-8`), or a sequence of indices or ranges separated by commas (e.g., `4,8,15,16` or
`9,11-15,17-21,23`). Ranges are inclusive on both ends, e.g., `5-8` means indices 5, 6, 7, and 8.

### Cleaning Up Files

```
$ djiutil cleanup -h
usage: djiutil cleanup [-h] [-d DATE_FILTER | -i INDEX] [-y] {lrf,srt,video,all} [dir_path]

positional arguments:
  {lrf,srt,video,all}   type of files to clean up (video includes .mov and .mp4 files)
  dir_path              path to the directory where DJI files are located

options:
  -h, --help            show this help message and exit
  -d DATE_FILTER, --date-filter DATE_FILTER
                        filter deleted files by date or age (examples: "<1d", ">1w", "2023-08-28"). Supported units are: h (hours), d (days), w (weeks),
                        m (months), and y (years).
  -i INDEX, --index INDEX, --index-numbers INDEX
                        index number(s) of the video file(s) to delete, as returned by the list subcommand (examples: "1-4", "5,7,8", "21-23,26-29,32")
  -y, --yes, --assume-yes
                        skip user confirmation before cleaning up files (default: false)
```

DJI drones typically store their files on microSD cards (or a small internal SSD on some models).
A drone can quickly fill up even a fairly large microSD card, so it's common to need to clean up
files that are no longer wanted in order to free up space on the SD card or internal SSD.

#### File Types

The `djiutil cleanup <type> <directory>` command will delete DJI files of the specified type from
the specified directory. The following file types are supported:

* `lrf` - low-resolution video files created by the drone to preview on the remote controller's
  built-in display (or a connected mobile device)
* `srt` - subtitle files containing information about the drone's location, altitude, and camera
  settings during the recording of a video (see the section on converting SRT to GPX, below, for
  more details)
* `video` - high-resolution video files recorded by the drone (includes `.mov` and `.mp4` formats)
* `all` - all of the above: LRF, SRT, and video files

#### File Filtering

In addition to checking the file type, the files to be cleaned up may be further filtered by
providing a date filter or index list; see the section on filtering, above, for more details.

#### Bypassing Confirmation

By default, when running in an interactive environment (e.g., a shell), `djiutil` will prompt the
user for confirmation before cleaning up any files. To bypass this prompt, use the
`-y`/`--yes`/`--assume-yes` flag.

#### Examples

Use the following command to clean up video files created more than two weeks ago
from the directory `/Volumes/Mavic`:

```
$ djiutil cleanup video /Volumes/Mavic -d '>2w'
```

Use the following command to clean up all files with index numbers 10-14 (inclusive)
from the directory `/Volumes/Mavic` without prompting for confirmation:

```
$ djiutil cleanup all /Volumes/Mavic -i 10-14 -y
```

### Converting SRT to GPX

```
$ djiutil convert -h
usage: djiutil convert [-h] srt_file_path [gpx_file_path]

positional arguments:
  srt_file_path  path to the subtitle (.srt) file to convert, or a directory where subtitle files are located
  gpx_file_path  output GPX file path (inferred from srt_file_path if not specified)

options:
  -h, --help     show this help message and exit
```

Some DJI drones have the option to create [SRT](https://docs.fileformat.com/video/srt/) (subtitle)
files along with the video files they record. These files capture information about the drone's
location, altitude, and camera settings throughout the recording of a video. Using a media player
such as [VLC](https://www.videolan.org/vlc/), these SRT files can be paired with the corresponding
video files to display the flight data over the video as subtitles; [this article](https://www.rev.com/blog/resources/how-to-add-captions-and-subtitles-to-vlc-media-player-videos-and-movies)
describes how to do this (see the section called "Method 2").

Useful though this feature is, the SRT format is limited in terms of its compatibility with other
software. The SRT files generated by DJI drones contain the drone's GPS location and altitude, but
this data is embedded in the text of the captions and is not easy to extract or interpret for use
in other applications besides viewing the flight data as a subtitle. In contrast, [GPX](https://www.topografix.com/gpx.asp),
or the GPS Exchange Format, is supported by a range of software and applications that work with
GPS and map data (for example, [GPX Studio](https://gpx.studio)).

The `djiutil convert <srt_file> [<gpx_file>]` command will convert the specified SRT file to the
GPX format. The resulting GPX file will either be given the specified GPX file name, or the file
name will be inferred from the SRT file if no GPX file name is provided.

#### Converting All SRT Files in a Directory

If the SRT file path passed to `djiutil convert` is a directory, all SRT files in the provided
directory will be converted to GPX format. Note that no GPX file name may be provided when
converting an entire directory; the GPX file names will be inferred from the source SRT file names.

#### Examples

Use the following command to convert the file `/Volumes/Mavic/0001.srt` to the file
`/tmp/output.gpx`:

```
$ djiutil convert /Volumes/Mavic/0001.srt /tmp/output.gpx
```

Use the following command to convert all SRT files in the directory `/Volumes/Mavic` to GPX format:

```
$ djiutil convert /Volumes/Mavic
```

### Importing Files

```
$ djiutil import -h
usage: djiutil import [-h] [-d DATE_FILTER | -i INDEX] [-s] [-y] [dir_path] dest_path

positional arguments:
  dir_path              path to the directory where DJI files are located
  dest_path             path to the directory to import the files to

options:
  -h, --help            show this help message and exit
  -d DATE_FILTER, --date-filter DATE_FILTER
                        filter imported files by date or age (examples: "<1d", ">1w", "2023-08-28"). Supported units are: h (hours), d (days), w (weeks),
                        m (months), and y (years).
  -i INDEX, --index INDEX, --index-numbers INDEX
                        index number(s) of the video file(s) to import, as returned by the list subcommand (examples: "1-4", "5,7,8", "21-23,26-29,32")
  -s, --srt, --include-srt
                        import SRT (subtitle) files in addition to video files (default: false)
  -y, --yes, --assume-yes
                        skip user confirmation before importing files (default: false)
```

DJI drones typically store their files on microSD cards (or a small internal SSD on some models).
It's common to need to transfer the recorded video files from the microSD card or SSD to a more
permanent storage medium.

The `djiutil import <source_directory> <destination_directory>` command will copy video files from
the specified source directory to the specified destination directory, creating the destination
directory if it does not exist.

#### File Filtering

The files to be imported may be filtered by providing a date filter or index list; see the section
on filtering, above, for more details.

#### Importing SRT Files

By default, `djiutil import` imports only video (`.mov` and `.mp4`) files. Use the
`-s`/`--srt`/`--include-srt` flag to import SRT (subtitle) files as well as video files. See the
section on converting SRT to GPX, above, for more about these files.

#### Bypassing Confirmation

By default, when running in an interactive environment (e.g., a shell), `djiutil` will prompt the
user for confirmation before importing any files. To bypass this prompt, use the
`-y`/`--yes`/`--assume-yes` flag.

#### Examples

Use the following command to import all video files created within the past week
from the directory `/Volumes/Mavic` to the directory `/var/video`:

```
$ djiutil import /Volumes/Mavic /var/video -d '<1w'
```

Use the following command to import all video and SRT files with index numbers 22-26 (inclusive)
from the directory `/Volumes/Mavic` to the directory `/var/video` without prompting for
confirmation:

```
$ djiutil import /Volumes/Mavic /var/video -i 22-26 -s -y
```

### Listing Files

```
$ djiutil list -h
usage: djiutil list [-h] [-d DATE_FILTER | -i INDEX] [-o {json,plain}] [-p] [dir_path]

positional arguments:
  dir_path              path to the directory where DJI files are located

options:
  -h, --help            show this help message and exit
  -d DATE_FILTER, --date-filter DATE_FILTER
                        filter results by date or age (examples: "<1d", ">1w", "2023-08-28"). Supported units are: h (hours), d (days), w (weeks), m
                        (months), and y (years).
  -i INDEX, --index INDEX, --index-numbers INDEX
                        index number(s) of the video file(s) to import, as returned by the list subcommand (examples: "1-4", "5,7,8", "21-23,26-29,32")
  -o {json,plain}, --output {json,plain}, --output-format {json,plain}
                        desired output format (plain format or JSON); default: pretty tabular format
  -p, --include-file-path
                        include video file paths in the listing (default: false)
```

The `djiutil list <directory>` command will list all DJI video files in the specified directory.
The listing also indicates whether corresponding LRF (low-resolution video) and/or SRT (subtitle)
files exist for each of the video files.

#### File Filtering

The files listed may be filtered by providing a date filter or index list; see the section on
filtering, above, for more details.

#### Including File Paths

Use the `-p`/`--include-file-path` flag to include the full path to each video file in the listing.
The path is hidden by default.

#### Output Formats

The default output format is a pretty-printed tabular format that looks like the following:

```
╭─────┬───────┬───────┬─────────────────────┬────────╮
│   # │  LRF  │  SRT  │       Created       │  Size  │
├─────┼───────┼───────┼─────────────────────┼────────┤
│  31 │       │       │ 2023-09-02 17:24:03 │  3.5G  │
│  32 │       │   ✓   │ 2023-09-02 17:27:00 │  2.6G  │
│  33 │   ✓   │   ✓   │ 2023-09-02 17:29:43 │  2.3G  │
╰─────┴───────┴───────┴─────────────────────┴────────╯
```

In the default mode, consecutive files that were created more than 10 minutes apart are separated
by a horizontal dividing line in the table. This is intended to serve as a quick visual reference
for which files were recorded during the same flight or session.

The default output format is intended for human consumption, but it is not ideal for being passed
to or parsed by other utilities. If you are processing the output of `djiutil list`
programmatically, you may wish to use the `-o`/`--output`/`--output-format` option to control the
output format.

Use the `plain` output format for a simpler tabular format that looks like the following:

```
  #   LRF    SRT         Created         Size
---  -----  -----  -------------------  ------
 31                2023-09-02 17:24:03   3.5G
 32           ✓    2023-09-02 17:27:00   2.6G
 33    ✓      ✓    2023-09-02 17:29:43   2.3G
```

This format is well suited to processing by utilities such as `awk` or `sed`.

Use the `json` output format for JSON formatted data that looks like the following:

```
[
  {
    "index": 31,
    "has_lrf": false,
    "has_srt": false,
    "created": "2023-09-02T17:24:03.900000",
    "size": "3.5G",
    "size_in_bytes": 3760740181
  },
  {
    "index": 32,
    "has_lrf": false,
    "has_srt": true,
    "created": "2023-09-02T17:27:00.350000",
    "size": "2.6G",
    "size_in_bytes": 2760949500
  },
  {
    "index": 33,
    "has_lrf": true,
    "has_srt": true,
    "created": "2023-09-02T17:29:43.270000",
    "size": "2.3G",
    "size_in_bytes": 2433459466
  }
]
```

The JSON format gives the most flexibility in terms of processing by other software, but it
is also the most verbose and may be overkill for most situations.

#### Examples

Use the following command to list all DJI files in the directory `/Volumes/Mavic` that were created
less than a month ago:

```
$ djiutil list /Volumes/Mavic -d '<1m'
```

Use the following command to list all DJI files in the directory `/Volumes/Mavic` with index
numbers in the range 33-37 (inclusive) and to include the full path to each file in the output:

```
$ djiutil list /Volumes/Mavic -i 33-37 -p
```

Use the following command to list all DJI files in the directory `/Volumes/Mavic` in JSON format:

```
$ djiutil list /Volumes/Mavic -o json
```

### Playing Video Files

```
$ djiutil play -h
usage: djiutil play [-h] [dir_path] index

positional arguments:
  dir_path    path to the directory where DJI files are located
  index       index number of the video file to play (as returned by the list subcommand)

options:
  -h, --help  show this help message and exit
```

The `djiutil play <directory> <index>` command is a simple shortcut to play the video file in the
specified directory with the specified index. The index number is the same one returned by the
`list` subcommand (see above).

#### Example

Use the following command to play the video file with index 42 from the directory `/Volumes/Mavic`:

```
$ djiutil play /Volumes/Mavic 42
```

### Configuring a Default Directory Path

All `djiutil` subcommands except `djiutil convert` require specifying the path to a directory where
DJI files are located. The sections above describe how to specify this directory path on the
command line when invoking `djiutil`. However, the directory path does not change frequently (if
ever) when working with the files created by a single drone, and typing the path repeatedly for
every `djiutil` command can become tiresome.

To alleviate the amount of repetitive typing required, `djiutil` supports configuring a default
directory path via environment variable and/or config file. If no directory path is specified on
the command line, `djiutil` will attempt to find the path to use in an environment variable called
`DJIUTIL_DIR_PATH`. If this environment variable is not defined (or empty), the value will be taken
from the `dji_dir_path` found in the file `~/.djiutil.json`, if it exists (see below).

#### Example Config File

As described above, you may optionally choose to create a config file to store the default
directory path for `djiutil` to use. The following is an example config file, which should be
located at `~/.djiutil.json`:

```json
{
  "dji_dir_path": "/Volumes/Mavic"
}
```
