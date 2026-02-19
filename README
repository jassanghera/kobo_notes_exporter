## Kobo Notes Exporter

A Python command-line tool that extracts highlights from a Kobo eReader and exports them to structured Markdown or plain text files.

The tool reads from the device’s internal SQLite database (KoboReader.sqlite), processes highlight data locally, and generates clean, readable note exports.

### Features

- Detects a connected Kobo device
- Creates a local copy of the Kobo database for safe processing
- Lists books with highlight counts
- Filters books by author, title, or recency
- Exports highlights to:
  - Markdown (.md)
  - Plain text (.txt)
- Exports selected books or all highlights
- Displays progress indicators during export
- Stores last sync time and selected books for 

### Project Structure

```
  cli.py                 CLI commands and user interaction
  core/
      parser.py          Data processing and filtering
      exporter.py        Export logic (Markdown/TXT)
      sync_db.py         Local database synchronization
      device.py          Kobo device detection
  tests/
      test_parser.py     Unit tests
```

The CLI layer handles user interaction and error handling.
Core modules handle database access, filtering, and export logic.


### Installation

1. Clone the repository

    git clone <link>
    cd kobo_notes_exporter

2. Create a virtual environment

  Windows:

    python -m venv venv
    venv\Scripts\activate

  macOS/Linux:

    python -m venv venv
    source venv/bin/activate

3. Install dependencies

    pip install -r requirements.txt


### Basic Usage Instructions

  instructions coming soon :)

### Notes

The Kobo device must be mounted as a drive.
A local copy of the database is required before listing or exporting.
The tool displays the last sync time when running database-dependent commands.




