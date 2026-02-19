import sys
import os
import pandas as pd
import pytest
# from kobo_notes_exporter.core import parser

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import core.parser as parser

def setup_fake_books():
    return pd.DataFrame({
        "Title": ["Book A", "Book B"],
        "ContentID": ["id_a", "id_b"],
        "Attribution": ["Author A", "Author B"]
    })


def test_get_volumeID_from_title_success(monkeypatch):
    fake_books = setup_fake_books()

    # Override global df_books inside parser
    monkeypatch.setattr(parser, "df_books", fake_books)

    result = parser.get_volumeID_from_title("Book A")

    assert result == "id_a"


def test_get_volumeID_from_title_not_found(monkeypatch):
    fake_books = setup_fake_books()

    monkeypatch.setattr(parser, "df_books", fake_books)

    with pytest.raises(ValueError):
        parser.get_volumeID_from_title("Nonexistent Book")


def test_get_volumeID_from_title_duplicate(monkeypatch):
    fake_books = pd.DataFrame({
        "Title": ["Book A", "Book A"],
        "ContentID": ["id_a1", "id_a2"],
        "Attribution": ["Author A", "Author A"]
    })

    monkeypatch.setattr(parser, "df_books", fake_books)

    with pytest.raises(ValueError):
        parser.get_volumeID_from_title("Book A")



def test_get_books_by_author(monkeypatch):
    fake_books = pd.DataFrame({
        "Title": ["Book A", "Book B"],
        "ContentID": ["id_a", "id_b"],
        "Attribution": ["Author A", "Author A"]
    })

    fake_highlights = pd.DataFrame({
        "VolumeID": ["id_a"]
    })

    monkeypatch.setattr(parser, "df_books", fake_books)
    monkeypatch.setattr(parser, "df_highlights", fake_highlights)

    result = parser.get_books_by_author("Author A")

    assert result == ["id_a"]

def test_get_filtered_books_by_title(monkeypatch):
    fake_books = pd.DataFrame({
        "VolumeID": ["id_a", "id_b"],
        "Title": ["Book A", "Book B"],
        "Attribution": ["Author A", "Author B"],
        "HighlightCount": [5, 3],
        "LatestHighlight": pd.to_datetime(["2024-01-01", "2024-01-02"])
    })

    monkeypatch.setattr(parser, "get_highlight_counts", lambda: fake_books)

    result = parser.get_filtered_books(title="Book A")

    assert len(result) == 1
    assert result.iloc[0]["Title"] == "Book A"    

def test_get_filtered_books_by_author(monkeypatch):
    fake_books = pd.DataFrame({
        "VolumeID": ["id_a", "id_b"],
        "Title": ["Book A", "Book B"],
        "Attribution": ["Author A", "Author B"],
        "HighlightCount": [5, 3],
        "LatestHighlight": pd.to_datetime(["2024-01-01", "2024-01-02"])
    })

    monkeypatch.setattr(parser, "get_highlight_counts", lambda: fake_books)

    result = parser.get_filtered_books(author="Author A")

    assert len(result) == 1
    assert result.iloc[0]["Title"] == "Book A"

    
def test_get_filtered_books_latest_limit(monkeypatch):
    fake_books = pd.DataFrame({
        "VolumeID": ["id_a", "id_b", "id_c"],
        "Title": ["A", "B", "C"],
        "Attribution": ["Auth", "Auth", "Auth"],
        "HighlightCount": [1, 2, 3],
        "LatestHighlight": pd.to_datetime([
            "2024-01-01",
            "2024-01-02",
            "2024-01-03"
        ])
    })

    monkeypatch.setattr(parser, "get_highlight_counts", lambda: fake_books)

    result = parser.get_filtered_books(latest=2)

    assert len(result) == 2
    assert result.iloc[0]["Title"] == "C"


def test_get_filtered_books_since(monkeypatch):
    fake_books = pd.DataFrame({
        "VolumeID": ["id_a", "id_b"],
        "Title": ["Old Book", "New Book"],
        "Attribution": ["Auth", "Auth"],
        "HighlightCount": [1, 1],
        "LatestHighlight": pd.to_datetime([
            "2024-01-01",
            "2024-12-01"
        ])
    })

    monkeypatch.setattr(parser, "get_highlight_counts", lambda: fake_books)

    # Mock current time to 2024-12-31
    monkeypatch.setattr(
        pd.Timestamp,
        "now",
        classmethod(lambda cls, tz=None: pd.Timestamp("2024-12-31"))
    )

    result = parser.get_filtered_books(since=30)

    assert len(result) == 1
    assert result.iloc[0]["Title"] == "New Book"

def test_get_highlight_counts(monkeypatch):
    import pandas as pd

    # Prevent real loading
    monkeypatch.setattr(parser, "_ensure_loaded", lambda: None)

    fake_books = pd.DataFrame({
        "ContentID": ["book1", "book2"],
        "Title": ["Book One", "Book Two"],
        "Attribution": ["Author A", "Author B"]
    })

    fake_highlights = pd.DataFrame({
        "VolumeID": ["book1", "book1", "book2"],
        "DateModified": pd.to_datetime([
            "2024-01-01",
            "2024-01-05",
            "2024-02-01"
        ])
    })

    monkeypatch.setattr(parser, "df_books", fake_books)
    monkeypatch.setattr(parser, "df_highlights", fake_highlights)

    result = parser.get_highlight_counts()

    # Book1 should have 2 highlights
    book1 = result[result["VolumeID"] == "book1"].iloc[0]
    assert book1["HighlightCount"] == 2
    assert book1["LatestHighlight"] == pd.Timestamp("2024-01-05")

    # Book2 should have 1 highlight
    book2 = result[result["VolumeID"] == "book2"].iloc[0]
    assert book2["HighlightCount"] == 1
    assert book2["LatestHighlight"] == pd.Timestamp("2024-02-01")


# kepub exists
def test_get_chapter_titles_kepub(monkeypatch):
    import pandas as pd

    monkeypatch.setattr(parser, "_ensure_loaded", lambda: None)

    fake_kepub = pd.DataFrame({
        "BookID": ["book1", "book1"],
        "Title": ["Chapter 1", "Chapter 2"],
        "VolumeIndex": [1, 2]
    })

    fake_epub = pd.DataFrame(columns=["BookID", "Title", "VolumeIndex"])

    monkeypatch.setattr(parser, "df_kepub_chapters", fake_kepub)
    monkeypatch.setattr(parser, "df_epub_chapters", fake_epub)

    result = parser.get_chapter_titles("book1")

    assert result == ["Chapter 1", "Chapter 2"]


# fallback to epub
def test_get_chapter_titles_epub_fallback(monkeypatch):
    import pandas as pd

    monkeypatch.setattr(parser, "_ensure_loaded", lambda: None)

    fake_kepub = pd.DataFrame(columns=["BookID", "Title", "VolumeIndex"])

    fake_epub = pd.DataFrame({
        "BookID": ["book1"],
        "Title": ["Epub Chapter"],
        "VolumeIndex": [1]
    })

    monkeypatch.setattr(parser, "df_kepub_chapters", fake_kepub)
    monkeypatch.setattr(parser, "df_epub_chapters", fake_epub)

    result = parser.get_chapter_titles("book1")

    assert result == ["Epub Chapter"]

# no chapter titles found
def test_get_chapter_titles_none(monkeypatch):
    import pandas as pd

    monkeypatch.setattr(parser, "_ensure_loaded", lambda: None)

    fake_kepub = pd.DataFrame(columns=["BookID", "Title", "VolumeIndex"])
    fake_epub = pd.DataFrame(columns=["BookID", "Title", "VolumeIndex"])

    monkeypatch.setattr(parser, "df_kepub_chapters", fake_kepub)
    monkeypatch.setattr(parser, "df_epub_chapters", fake_epub)

    result = parser.get_chapter_titles("book1")

    assert result == []



