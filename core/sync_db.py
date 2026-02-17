import shutil
import json
from pathlib import Path
from datetime import datetime
from rich import print

# define paths
DATA_DIR = Path("data")
LOCAL_DB_PATH = DATA_DIR / "KoboReader.sqlite"
METADATA_PATH = DATA_DIR / "metadata.json"

def ensure_data_dir():
    DATA_DIR.mkdir(exist_ok=True)

def perform_sync(device_db_path: Path):
    """
    Copies the Kobo database locally and updates metadata with last sync time
    """
    ensure_data_dir()

    # copy the db
    shutil.copy2(device_db_path, LOCAL_DB_PATH)

    # update metadata
    metadata = {
        "last_sync": datetime.now().isoformat(),
        "db_path": str(LOCAL_DB_PATH)
    }

    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4)

    return metadata

def get_last_sync():
    """
    Returns last sync time if available
    """
    if not METADATA_PATH.exists():
        return None
    
    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        metadata = json.load(f)
    
    return metadata.get("last_sync")

def get_local_db_path():
    """
    Returns the path to the locally stored Kobo database if it exists
    """
    if LOCAL_DB_PATH.exists():
        return LOCAL_DB_PATH
    return None

def ensure_local_db():
    if not get_local_db_path():
        print("[red]No local database found.[/red]")
        print("Please connect your Kobo and run:")
        print("   python cli.py sync")

def has_previous_sync():
    return METADATA_PATH.exists() and LOCAL_DB_PATH.exists()