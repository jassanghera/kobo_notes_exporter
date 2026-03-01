"""
kobo_notes_exporter.core.exporter

Export layer for Kobo Notes Exporter.

This module is responsible for:
- formatting highlights into Markdown or plain text
- writing exported files to disk
- ensuring filenames are filesystem-safe

It does NOT query the database directly. It relies on `parser.py` to provide:
- book title/author
- chapter -> highlights mapping
"""

from __future__ import annotations
from kobo_notes_exporter.core import parser
import re
from pathlib import Path


# -------------------------------------------------------------------------------------------------
# Filename and Path Utilities
# -------------------------------------------------------------------------------------------------

_INVALID_FILENAME_CHARS = r'[<>:"/\\|?*]'

def safe_filename(name: str) -> str:
    """Return a filesystem-safe filename by stripping invalid characters.

    Windows forbids: < > : " / \\ | ? *
    We remove those characters to prevent write failures.
    """
    return re.sub(_INVALID_FILENAME_CHARS, "", name).strip()

def _build_export_path(volume_id: str, output_dir: Path, ext: str) -> Path:
    """Build the output filepath for a given book export."""
    title = parser.get_book_title(volume_id)
    author = parser.get_book_author(volume_id)

    filename = safe_filename(f"{title} - {author}.{ext}")
    return output_dir / filename

# ------------------------------------------------------------------------------------------------
# EXPORT TO MARKDOWN FILE
# ------------------------------------------------------------------------------------------------

def export_md(volume_id: str, output_dir: Path) -> Path:
    """Export highlights for a single book to a Markdown (.md) file.

    Args:
        volume_id: Kobo VolumeID identifying the book.
        output_dir: Directory to write the export file into.

    Returns:
        Path to the written file.
    """
    filepath = _build_export_path(volume_id, output_dir, "md")

    title = parser.get_book_title(volume_id)
    author = parser.get_book_author(volume_id)
    chapters = parser.map_chapters_to_highlights(volume_id)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n")
        f.write(f"## {author}\n\n")

        for chapter_title, highlights in chapters.items():
            f.write("_" * 63 + "\n")
            f.write(f"### {chapter_title}\n\n")

            for text in highlights:
                f.write(f"- {text}\n")

            f.write("\n")

    return filepath

# -------------------------------------------------------------------------------------------------
# EXPORT TO TXT FILE
# -------------------------------------------------------------------------------------------------

def export_txt(volume_id: str, output_dir: Path) -> Path:
    """Export highlights for a single book to a .txt file.

    Args:
        volume_id: Kobo VolumeID identifying the book.
        output_dir: Directory to write the export file into.

    Returns:
        Path to the written file.
    """
    filepath = _build_export_path(volume_id, output_dir, "txt")

    title = parser.get_book_title(volume_id)
    author = parser.get_book_author(volume_id)
    chapters = parser.map_chapters_to_highlights(volume_id)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(title + "\n")
        f.write(author + "\n\n")

        for chapter_title, highlights in chapters.items():
            f.write("_" * 63 + "\n")
            f.write(f"Chapter: {chapter_title}\n\n")

            for text in highlights:
                f.write(f"- {text}\n")

            f.write("\n")

    return filepath
