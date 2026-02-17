import sqlite3
import pandas as pd
from pathlib import Path
import core.sync_db as sync_db

# ----------------------------------------------------------------------------------
# SQL QUERIES -> DATAFRAMES
# ----------------------------------------------------------------------------------

books_query = """
SELECT Title, Attribution, ContentID
FROM content
WHERE ContentType = '6';
"""

epub_chapters_query = """
SELECT Title, ContentID, BookID, VolumeIndex
FROM content
WHERE ContentType = '9';
"""

kepub_chapters_query = """
SELECT Title, ContentID, BookID, VolumeIndex
FROM content
WHERE ContentType = '899';
"""

highlights_query = """
SELECT BookmarkID, ContentID, VolumeID, Text, DateModified FROM Bookmark;
"""

def load_data():
    """
    Loads Kobo db from local synced copy.
    Returns dictionary of DataFrames.
    """
    db_path = sync_db.get_local_db_path()

    if not db_path:
        raise RuntimeError("No local database found. Please run sync.")
    
    with sqlite3.connect(db_path) as connection:
        cursor = connection.cursor()

        def create_df(query):
            rows = cursor.execute(query)
            records = rows.fetchall()
            columns = [col[0] for col in rows.description]
            return pd.DataFrame(records, columns=columns)

        data = {
            "books": create_df(books_query),
            "epub": create_df(epub_chapters_query),
            "kepub": create_df(kepub_chapters_query),
            "highlights": create_df(highlights_query),
        }

    # Convert dates
    data["highlights"]["DateModified"] = pd.to_datetime(
        data["highlights"]["DateModified"]
    )
    print("done loading data")
    return data
    