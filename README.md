# clamAV-Utils

Utilities for running ClamAV virus scans efficiently on Linux systems. The main tool is a Python 3 wrapper (`antivirus.py`) that parallelizes scanning across multiple CPU cores using `multiprocessing`. A legacy Bash alternative (`cleanVirus.sh`) is also included.

---

## Features

- Recursive directory traversal with configurable directory exclusions
- Parallel scanning via `multiprocessing.Pool` — splits files into batches and processes them concurrently
- Progress bar powered by `tqdm`
- Automatic detection of `clamdscan` (preferred) or `clamscan`
- Optional quarantine: infected files are moved to a designated directory via `--move=<dir>` passed to the scanner
- Structured logging to a configurable log file
- Optional virus database update via `freshclam` before scanning (`--update-db`)
- Graceful handling of unreadable files and keyboard interrupts

---

## Requirements

- Python 3.6 or later
- ClamAV installed and accessible in `$PATH` (`clamdscan` or `clamscan`)
- Python dependency: `tqdm`

Install the Python dependency:

```bash
pip install tqdm
```

---

## Installation

```bash
git clone https://github.com/stevenvo780/clamAV-Utils.git
cd clamAV-Utils
pip install tqdm
```

No additional setup is required. The script uses only standard library modules plus `tqdm`.

---

## Usage

```
python3 antivirus.py [options] <directory> [<directory> ...]
```

### Arguments

| Argument | Description |
|---|---|
| `directories` | One or more directories to scan (positional, required) |
| `-j`, `--jobs` | Number of parallel worker processes (default: CPU count minus free cores) |
| `--nucleos-libres N` | Number of CPU cores to leave idle (default: 0) |
| `--exclude-dirs DIR ...` | Directories to exclude from scanning (default: `/proc /sys /dev /run /tmp /var/lib /var/run`) |
| `--quarantine-dir DIR` | Directory to move infected files into |
| `--log-file FILE` | Path to the log file (default: `clamav_scan.log`) |
| `--batch-size N` | Files per batch sent to each worker process (default: 500) |
| `--update-db` | Run `freshclam` to update virus definitions before scanning |

### Examples

Scan the home directory using all available cores:

```bash
python3 antivirus.py /home
```

Scan two directories, leave 2 cores free, move infected files to quarantine:

```bash
python3 antivirus.py /home /mnt/data --nucleos-libres 2 --quarantine-dir /var/quarantine
```

Update virus definitions first, then scan with 8 workers and a custom log file:

```bash
python3 antivirus.py /home --update-db -j 8 --log-file /var/log/clamav_custom.log
```

Scan with a smaller batch size and exclude additional directories:

```bash
python3 antivirus.py /srv --batch-size 100 --exclude-dirs /proc /sys /dev /srv/cache
```

---

## Output

Upon completion the script prints:

- Total files scanned
- Elapsed time and throughput (files/second)
- List of infected files with the scanner's detection message

Infected files are also written to the log file. If `--quarantine-dir` is set, infected files are moved there by the scanner before the summary is printed.

---

## cleanVirus.sh

`cleanVirus.sh` is an older Bash implementation using GNU Parallel and `pv` for progress display. It auto-installs missing dependencies (`parallel`, `clamav`, `pv`) via `apt` on Debian/Ubuntu systems and creates a quarantine directory at `~/quarantine`.

Usage:

```bash
bash cleanVirus.sh /home /mnt/data
```

`antivirus.py` supersedes this script for most use cases, offering finer-grained control and cross-distribution compatibility. `cleanVirus.sh` is kept for environments where Python is unavailable or a simple one-shot scan is preferred.

---

## License

This project does not currently carry an explicit license. All rights reserved by the author unless otherwise stated.
