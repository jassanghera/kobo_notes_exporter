r"""
kobo_notes_exporter.core.device

Device detection utilities.

This module locates the Kobo SQLite database on a mounted Kobo eReader.

Windows note:
- Kobo devices typically mount as a drive letter (e.g., E:/) and store the DB at:
  <DRIVE>:/\.kobo\KoboReader.sqlite

Future work:
- For cross-platform support, this module could be extended to detect mount
  points on macOS/Linux.
"""

from __future__ import annotations
import string
from pathlib import Path

def find_kobo_db() -> Path | None:
    """Scan mounted drives and return the path to the Kobo SQLite database.

    Returns:
        Path to `.kobo/KoboReader.sqlite` if a Kobo device is found, otherwise None.
    """

    for letter in string.ascii_uppercase:
        drive = Path(f"{letter}:/")

        if drive.exists():
            db_path = drive / ".kobo" / "KoboReader.sqlite"

            if db_path.exists():
                return db_path
            
    return None