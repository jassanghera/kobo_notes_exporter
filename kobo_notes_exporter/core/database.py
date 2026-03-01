"""
kobo_notes_exporter.core.database

SQLite access layer for Kobo Notes Exporter.

This module is responsible for:
- connecting to the *locally synced* Kobo SQLite database
- executing a small set of read-only SQL queries
- returning results as pandas DataFrames

It intentionally does NOT perform business logic (filtering/mapping/exporting).
That work belongs in `kobo_notes_exporter.core.parser`.
"""

from __future__ import annotations
import sqlite3
import pandas as pd
import kobo_notes_exporter.core.sync_db as sync_db

# ----------------------------------------------------------------------------------
# SQL Queries -> DataFrames
# ----------------------------------------------------------------------------------

# Books / main content records
BOOKS_QUERY = """
SELECT Title, Attribution, ContentID
FROM content
WHERE ContentType = '6';
"""

# Chapter rows for EPUB books (exact ContentID match)
EPUB_CHAPTERS_QUERY = """
SELECT Title, ContentID, BookID, VolumeIndex
FROM content
WHERE ContentType = '9';
"""

# Chapter rows for KEPUB books (ContentID often behaves like a prefix)
KEPUB_CHAPTERS_QUERY = """
SELECT Title, ContentID, BookID, VolumeIndex
FROM content
WHERE ContentType = '899';
"""

# Highlights live in Bookmark table. We load raw fields and interpret in parser.py.
HIGHLIGHTS_QUERY = """
SELECT BookmarkID, ContentID, VolumeID, Text, DateModified FROM Bookmark;
"""

def load_data() -> dict[str, pd.DataFrame]:
    """Load Kobo data from the locally synced SQLite database.

    Returns:
        Dict of DataFrames:
        - "books": Title/Author/ContentID for books
        - "epub": EPUB chapter rows
        - "kepub": KEPUB chapter rows
        - "highlights": Bookmark table rows (highlights)

    Raises:
        RuntimeError: If no local database exists (user must run `kobo sync` first).
    """
    db_path = sync_db.get_local_db_path()

    if not db_path:
        raise RuntimeError("No local database found. Please run sync.")
    

    def create_df(cursor: sqlite3.Cursor, query: str) -> pd.DataFrame:
        """Execute a query and return results as a DataFrame."""
        rows = cursor.execute(query)
        records = rows.fetchall()
        columns = [col[0] for col in rows.description]
        return pd.DataFrame(records, columns=columns)

    with sqlite3.connect(db_path) as connection:
        cursor = connection.cursor()

        data = {
            "books": create_df(cursor, BOOKS_QUERY),
            "epub": create_df(cursor, EPUB_CHAPTERS_QUERY),
            "kepub": create_df(cursor, KEPUB_CHAPTERS_QUERY),
            "highlights": create_df(cursor, HIGHLIGHTS_QUERY),
        }

    # Normalize date column once here so downstream code can assume datetime.
    data["highlights"]["DateModified"] = pd.to_datetime(
        data["highlights"]["DateModified"]
    )
    
    return data
    