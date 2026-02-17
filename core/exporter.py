import core.parser as parse
import re
from pathlib import Path


# -------------------------------------------------------------------------------------------------
# make safe file names - no [\\/*?:"<>|] allowed
# -------------------------------------------------------------------------------------------------

def safe_filename(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "", name)


# -------------------------------------------------------------------------------------------------
# EXPORT TO TXT FILE
# -------------------------------------------------------------------------------------------------

def export_txt(volumeID, output_dir):

    title = parse.get_book_title(volumeID)
    author = parse.get_book_author(volumeID)

    filename = safe_filename(f'{title} - {author}.txt')
    filepath = output_dir / f"{filename}"

    with open(filepath, 'w', encoding='utf-8') as f:

        f.write(title + "\n")
        f.write(author + "\n\n")
        
        chap_and_hl = parse.map_chapters_to_highlights(volumeID)

        for ch, hl in chap_and_hl.items():
            f.write("_______________________________________________________________" + "\n")
            f.write(f'Chapter: {ch}' + '\n\n')
        
            for h in hl:
                f.write(f'- {h}' + '\n')
            f.write("\n")
        f.write("\n")

        # print(f'Wrote to {f.name} successfully!')


# ------------------------------------------------------------------------------------------------
# EXPORT TO MARKDOWN FILE
# ------------------------------------------------------------------------------------------------

def export_md(volumeID, output_dir):

    title = parse.get_book_title(volumeID)
    author = parse.get_book_author(volumeID)

    filename = safe_filename(f'{title} - {author}.md')
    filepath = output_dir / f"{filename}"

    with open(filepath, 'w', encoding='utf-8') as f:

        f.write(f'# {title}\n')
        f.write(f'## {author}\n\n')
        
        chap_and_hl = parse.map_chapters_to_highlights(volumeID)

        for ch, hl in chap_and_hl.items():
            f.write("_______________________________________________________________" + "\n")
            f.write(f'### {ch}\n\n')
        
            for h in hl:
                f.write(f'- {h}\n')
            f.write("\n")
        f.write("\n")

        # print(f'Wrote to {f.name} successfully!')
