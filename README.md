# patro-sort

`patro-sort` is a highly specialized command-line utility designed to scan,
parse, and recursively organize your media files (images, videos, and audio)
into a structured folder hierarchy based on the **Bikram Sambat (BS)** Nepali
calendar system.

The application utilizes high-performance metadata extraction to pull true
creation timestamps via `ExifTool`, fallback elegantly to filesystem birth
times when metadata is stripped, and rename targets cleanly into cross-platform
safe ISO-8601-like timestamps.

---

## Features

* **Bikram Sambat (BS) Bucketing**: Places media systematically into
  `<dest_dir>/<BS_year>/<BS_month_two_digit>/`.
* **Robust Metadata Extraction**: Leverages an optimized, batch-processed
  `ExifTool` implementation to resolve accuracy anomalies across variant EXIF,
  XMP, and IPTC schemas.
* **Deterministic Native Fallback**: Optional tracking of true filesystem
  creation times (`st_birthtime` on macOS/BSD, and native `statx` syscall
  tracking on Linux) when EXIF blocks are missing.
* **Cross-Device Performance**: Automatically attempts atomic **hard-linking**
  to save storage space and eliminate I/O lag, falling back transparently to deep
  copying (`shutil.copy2`) only when dealing with cross-device boundary
  adjustments.
* **Smart Collision Resolution**: Dynamically calculates distinct paths (e.g.,
  `_1`, `_2`) if multiple files produce identical structural time
* **Unsortable Preservation**: Automatically groups unrecognizable files or
  media with corrupted timestamps inside an `unsorted/` directory, mirroring the
  exact subfolder scheme they originally occupied.
* **Fail-Safe Dry Runs**: Operates in a protective, non-destructive simulation
  mode by default (`--wet-run` is required to perform actual disk modifications).

---

## Prerequisites

Before executing the tool, your system must have **ExifTool** installed
globally.

* **macOS** (via Homebrew):

  ```bash
  brew install exiftool

* **Linux (Ubuntu/Debian)**:

  ```bash
  sudo apt-get update && sudo apt-get install exiftool
  ```

* **Windows**: Download the executable directly from the official [ExifTool website](https://exiftool.org/)
and place it directly into your system's environment `PATH`.

---

## Installation & Setup

First, clone the project repository from GitHub and navigate into the project
root directory:

```bash
git clone https://github.com/FosRexx/patro-sort.git
cd patro-sort
```

`patro-sort` requires Python **3.14 or higher**. You can launch this software
seamlessly using **`uv`** (recommended for speed and isolated environment
setup) or traditional **`python/pip`**.

### Method A: Running with `uv` (Recommended)

`uv` handles dependency isolation on-the-fly without permanently installing
packages to your global python environment.

```bash
uv run main.py [source_directory] [destination_directory]
```

### Method B: Running via Standard Python & Virtual Environments

If `uv` is not present on your workstation, set up a standard environment using
Python's native toolchain:

```bash
# 1. Create and activate a clean virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate

# 2. Upgrade pip and install project requirements
pip install --upgrade pip
pip install -r pyproject.toml # Or pip install nepali-datetime pyexiftool pystatx python-dateutil

# 3. Execute the program
python main.py [source_directory] [destination_directory]
```

---

## Command Line Reference

```text
usage: patro-sort [-h] [-v] [-w] [--fs-ctime-fb] [--fn-inc-year] [--log-file LOG_FILE] src_dir dest_dir

Sort media files (images, videos, audio) into a Bikram Sambat calendar folder structure. Files are renamed to their creation timestamp and organised by BS year and month.

positional arguments:
  src_dir              Source directory to scan for media files (searched recursively).
  dest_dir             Destination directory for the sorted output (must be empty or absent).

options:
  -h, --help           show this help message and exit
  -v, --verbose        Enable debug logging.
  -w, --wet-run        Perform the sort for real. By default the program runs in dry-run mode and only logs what it would do without writing any files.
  --fs-ctime-fb        Fall back to the filesystem birth time when ExifTool cannot supply a creation date.
  --fn-inc-year        Should the dest media filename include year
  --log-file LOG_FILE  Optional file path to write logs to. If not specified, logs print to the console.
```

---

## Real-World Examples

### 1. Perform a Safe Dry Run (Simulated Verification)

By default, running the program performs a non-destructive analysis. It
displays planned file structures, link mechanics, and errors without editing
anything on your disk.

```bash
uv run main.py ~/Pictures/Unsorted_Camera_Roll ~/Pictures/Sorted_Bikram_Sambat
```

### 2. Execute a Wet Run (Real Disk Modifications)

Add the `-w` (or `--wet-run`) flag to apply the reorganization on your storage drive:

```bash
uv run main.py ~/Pictures/Unsorted_Camera_Roll ~/Pictures/Sorted_Bikram_Sambat -w
```

### 3. Fallback to File-System Creation Times and Include Years in Name

For assets scrubbed of metadata (e.g., downloaded via social messaging apps),
allow filesystem allocation timestamps (`--fs-ctime-fb`) and inject the full
Gregorian/BS timestamp validation parameters into the modified filename
(`--fn-inc-year`):

```bash
uv run main.py -w --fs-ctime-fb --fn-inc-year ~/Pictures/Unsorted_Camera_Roll ~/Pictures/Sorted_Bikram_Sambat
```

---

## Output Architecture Example

Once executed in real mode, your destination directory will be formatted like this:

```text
Sorted_Bikram_Sambat/
├── 2080/
│   ├── 01/
│   │   ├── 14T10-15-30+0545.jpg
│   │   └── 15T16-22-11+0545.mp4
│   └── 02/
│       └── 01T08-05-00+0545.wav
├── 2081/
│   └── 04/
│       └── 2081-04-15T12-30-00+0545.jpg   <- (If --fn-inc-year was toggled)
└── unsorted/
    └── WhatsApp/
        └── Sent/
            └── Unknown_Document.pdf       <- (Retains structural integrity from source)

```

## Architecture Note

The code is fully built on top of an abstract calendar-agnostic core
(`CalendarDateTime`). While it defaults natively to `BikramSambatDateTime`
paired with Nepal Standard Time (NST, `UTC+05:45`), it can be scaled up to
target any regional calendar scheme simply by subclassing `CalendarDateTime`
and providing an alternative factory to the `FileIndex`.
