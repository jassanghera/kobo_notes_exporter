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




