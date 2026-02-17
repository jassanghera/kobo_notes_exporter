import string
from pathlib import Path

def find_kobo_db():

    print("Scanning drives...")

    for letter in string.ascii_uppercase:
        drive = Path(f"{letter}:/")

        # if drive.exists():
            # print(f"Found drive: {drive}")

        if drive.exists():
            db_path = drive / ".kobo" / "KoboReader.sqlite"
            # print(f"Checking: {db_path}")

            if db_path.exists():
                # print("Database found!")
                return db_path
            
    # print("Database found!")
    return None