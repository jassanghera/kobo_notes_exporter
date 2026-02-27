"""
kobo_notes_exporter.core.sync_db

Local database synchronization utilities.

This module copies the Kobo SQLite database from the mounted device into a local
working directory (./data) so the rest of the application can query it safely
offline. It also writes minimal metadata (e.g., last sync time) for display in
the CLI.

Design choice:
- Runtime data lives in the user's current working directory (CWD).
  This keeps behavior predictable for CLI users and simplifies debugging.
"""

import shutil
import json
import typer
from pathlib import Path
from datetime import datetime
from rich import print

# -----------------------------------------------------------------------------
# Paths (relative to the directory where the CLI is executed)
# -----------------------------------------------------------------------------
DATA_DIR = Path("data")
LOCAL_DB_PATH = DATA_DIR / "KoboReader.sqlite"
METADATA_PATH = DATA_DIR / "sync_metadata.json"

# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------
def ensure_data_dir() -> None:
    """Create the runtime data directory if it doesn't already exist."""
    DATA_DIR.mkdir(exist_ok=True)

def perform_sync(device_db_path: Path) -> dict:
    """Copy the Kobo database locally and write sync metadata.

    Args:
        device_db_path: Path to the KoboReader.sqlite file on the mounted device.

    Returns:
        A metadata dict containing at least:
        - last_sync: ISO8601 timestamp string
        - db_path: local database path as a string
    """
    ensure_data_dir()

    # Copy the database from the device into the local runtime folder
    # We never query the device DB directly to avoid disconnect/locking issues
    shutil.copy2(device_db_path, LOCAL_DB_PATH)

    # update metadata
    metadata = {
        "last_sync": datetime.now().isoformat(),
        "db_path": str(LOCAL_DB_PATH)
    }

    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4)

    return metadata

def get_last_sync() -> str | None:
    """Return the last sync time (ISO string) if metadata exists, otherwise None."""
    if not METADATA_PATH.exists():
        return None
    
    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        metadata = json.load(f)
    
    return metadata.get("last_sync")

def get_local_db_path() -> Path | None:
    """Return the path to the locally synced Kobo database, or None if missing."""
    if LOCAL_DB_PATH.exists():
        return LOCAL_DB_PATH
    return None

def ensure_local_db() -> None:
    """Exit cleanly if no local database exists.

    This is used by CLI commands that require a synced database (books/export).
    """
    if not get_local_db_path():
        print("[red]No local database found.[/red]")
        print("Run [bold cyan]kobo sync[/bold cyan] to create a local copy.")
        print()
        raise typer.Exit(code=1)

def has_previous_sync() -> bool:
    """Return True if both the local database and metadata file exist."""
    return METADATA_PATH.exists() and LOCAL_DB_PATH.exists()