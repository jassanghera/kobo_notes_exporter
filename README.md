# Kobo Notes Exporter

A Python command-line tool that extracts highlights from a Kobo eReader and exports them to structured Markdown or plain text files.

The tool copies the Kobo device’s internal SQLite database locally, processes highlight data offline, and generates clean, readable exports.

⚠ Currently supports Windows only (device detection relies on drive-letter scanning).

## Features

- Detects a connected Kobo device (Windows)
- Safely copies the Kobo database locally before processing
- Lists books with highlight counts
- Filter books by:
  - Author
  - Title
  - Recency
- Export highlights to:
  - Markdown (`.md`)
  - Plain text (`.txt`)
- Export selected books or all highlights
- Displays last sync time and progress indicators

## 🏗 Architecture Overview

The application follows a layered structure:

```
CLI (Typer + Rich)
    ↓
Parser (Business Logic)
    ↓
Database Loader (SQLite → pandas)
    ↓
Sync Layer (Local DB copy)
    ↓
Device Detection
```

### Project Structure

```
kobo_notes_exporter/
│
├── cli.py              # CLI commands and presentation layer
├── core/
│   ├── database.py     # SQLite access
│   ├── device.py       # Kobo device detection
│   ├── sync_db.py      # Local database synchronization
│   ├── parser.py       # Data transformation and filtering logic
│   └── exporter.py     # Markdown/TXT export logic
│
├── tests/              # Unit tests (pytest)
├── pyproject.toml      # Poetry configuration
└── README.md
```

The CLI layer is responsible for user interaction and presentation.
The core/ modules implement database access, data transformation, and export logic.


Key design decisions:

- The Kobo database is **never queried directly from the device**.
- A local copy is created to avoid disconnect and locking issues.
- Business logic lives in `core/`, while `cli.py` handles presentation.
- Runtime data is stored in the directory where the tool is executed.

## 📦 Installation

### Option 1 – Install from source (development)

```bash
git clone <repo-url>
cd kobo_notes_exporter
poetry install
```
Run with:
```bash
poetry run kobo --help
```

### Option 2 - Install from built wheel

```pip install <filename>```

Then run:

``` kobo --help```

## Usage

Detect device
```bash
kobo detect
```

Sync local database
```bash
kobo sync
```

List books

```bash
kobo books
kobo books --author "John Green"
kobo books --latest 5
```

Export highlights
```bash
kobo export --latest 2
kobo export --author "Herman Melville"
kobo export --latest 1 --txt
```

Export all highlights
```bash
kobo export-all --force
```

Exports are written to:
```code
./exports/
```

A data/ folder is created in the current working directory to store:

- Local copy of KoboReader.sqlite
- Sync metadata
- Cached selections

## Future Improvements

- Cross-platform device detection
- Configurable runtime data directory
- PyPI publication
- Improved export formatting options
- GUI frontend

## Notes

The Kobo device must be mounted as a drive (Windows).

A local copy of the database is required before listing or exporting.

The tool displays the last sync time when running database-dependent commands.

## License

This project is licensed under the MIT License.


