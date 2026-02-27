import kobo_notes_exporter.core.database as database
import pandas as pd

# lazy loading of dataframes
df_books = None
df_epub_chapters = None
df_kepub_chapters = None
df_highlights = None
kepub_id_lookup = None

def _ensure_loaded():
    global df_books, df_epub_chapters, df_kepub_chapters, df_highlights, kepub_id_lookup

    if df_books is None:
        data = database.load_data()
        df_books = data["books"]
        df_epub_chapters = data["epub"]
        df_kepub_chapters = data["kepub"]
        df_highlights = data["highlights"]

        df_highlights["DateModified"] = pd.to_datetime(df_highlights["DateModified"])

        kepub_id_lookup = dict(zip(df_kepub_chapters['ContentID'], df_kepub_chapters['VolumeIndex']))

# ----------------------------------------------------------------------------------
# MATCHING KEPUB CONTENTIDs - helper fn
# ----------------------------------------------------------------------------------

# pass in a highlight ContentID, return the VolumeIndex if prefix match kepub ContentID
def lookup_kepub_index(content_id):
    _ensure_loaded()

    for ch_id, vol_idx in kepub_id_lookup.items():
        if ch_id.startswith(content_id):
            return vol_idx
    return None

# -----------------------------------------------------------------------------------
# ATTACH KEPUB VOLUMEINDEX TO HIGHLIGHTS (epub as backup)
# -----------------------------------------------------------------------------------

def add_v_idx_to_kepub():
    _ensure_loaded()

    # add kepub VolumeIndex column to highlights df manually using the lookup function
    df_highlights['VolumeIndex'] = df_highlights['ContentID'].apply(lookup_kepub_index)


    # insert epub VolumeIndex as backup where kepub VolumeIndex is missing, consider exact match of ContentID
    
    rowidx_vidx = {} # (row_index : volume_index), rows from highlight table, vidx from epub chapter VolumeIndex
 
    for _i, row in df_highlights.iterrows():
        ContentID = row['ContentID']
        VolumeIndex = row['VolumeIndex']
        if pd.isna(VolumeIndex):                                                            # if highlight VolumeIndex is NaN
            epub_row = df_epub_chapters.loc[df_epub_chapters['ContentID'] == ContentID]     # get epub_chapter row with matching ContentID
            epub_vidx = epub_row.iloc[0]['VolumeIndex']                                     # get value of epub VolumeIndex

            rowidx_vidx[_i] = epub_vidx    # store epub VolumeIndex in dict with corresponding highlight index

    # update highlight VolumeIndex column with vidx values from dict at row with index rowidx

    for idx, val in rowidx_vidx.items():
        df_highlights.at[idx, 'VolumeIndex'] = val

    return df_highlights



#------------------------------------------------------------------------------------
# SORT HIGHLIGHTS BY CHAPTER INDICES
#------------------------------------------------------------------------------------

def sort_highlights_by_v_idx():
    _ensure_loaded()
    highlights_with_v_idx = add_v_idx_to_kepub()
    return highlights_with_v_idx.sort_values(by=['VolumeID', 'VolumeIndex'])


# ----------------------------------------------------------------------------------
# CHAPTERS & HIGHLIGHTS FOR A GIVEN BOOK
# ----------------------------------------------------------------------------------

def map_chapters_to_highlights(volume_id):
    _ensure_loaded()

    df_highlights_sorted = sort_highlights_by_v_idx()

    # get all highlights for the given VolumeID
    book_highlights = df_highlights_sorted[df_highlights_sorted['VolumeID'] == volume_id]
    

    # create dict to map chapter titles to list of highlights
    chapters_to_highlights = {}
    for _, row in book_highlights.iterrows():
        ContentID = row['ContentID']
        highlight_text = row['Text']

        # find chapter title from kepub chapters df first
        chapter_row = df_kepub_chapters[df_kepub_chapters['ContentID'].str.startswith(ContentID)]
        if chapter_row.empty:
            # if not found, try epub chapters
            chapter_row = df_epub_chapters[df_epub_chapters['ContentID'] == ContentID]

        # get chapter title
        if not chapter_row.empty:
            chapter_title = chapter_row.iloc[0]['Title']
        else:
            chapter_title = "Unknown Chapter"

        # map highlight to chapter
        if chapter_title not in chapters_to_highlights:
            chapters_to_highlights[chapter_title] = []
        chapters_to_highlights[chapter_title].append(highlight_text)

    return chapters_to_highlights

# ---------------------------------------------------------------------------------------------------
# highlight counts + date modified
# ---------------------------------------------------------------------------------------------------

def get_highlight_counts():
    _ensure_loaded()

    # group highlights by VolumeID
    grouped = (
        df_highlights
        .groupby("VolumeID")
        .agg(
            HighlightCount=("VolumeID", "count"),
            LatestHighlight=("DateModified", "max")
        )
        .reset_index()
    )

    # merge with books table
    books_with_highlights = grouped.merge(
        df_books,
        left_on="VolumeID",
        right_on="ContentID",
        how="left"
    )

    return books_with_highlights[
        ["VolumeID", "Title", "Attribution", "HighlightCount", "LatestHighlight"]
    ]



# # --------------------------------------------------------------------------------------------------
# # GET LIST OF CHAPTER TITLES FOR A GIVEN BOOK
# # --------------------------------------------------------------------------------------------------

def get_chapter_titles(volume_id):
    _ensure_loaded()

    # try kepub chapters first
    kepub_chapters = df_kepub_chapters[df_kepub_chapters['BookID'] == volume_id].sort_values('VolumeIndex')
    if not kepub_chapters.empty:
        return kepub_chapters['Title'].tolist()

    # if no kepub chapters, try epub chapters
    epub_chapters = df_epub_chapters[df_epub_chapters['BookID'] == volume_id].sort_values('VolumeIndex')
    if not epub_chapters.empty:
        return epub_chapters['Title'].tolist()

    return []

# -------------------------------------------------------------------------------------------------
# getters - book title, author, volumeID
# -------------------------------------------------------------------------------------------------

def get_book_title(volume_id):
    _ensure_loaded()
    book = df_books[df_books['ContentID'] == volume_id]
    title = book.iloc[0]['Title']
    return title

def get_book_author(volume_id):
    _ensure_loaded()
    book = df_books[df_books['ContentID'] == volume_id]
    author = book.iloc[0]['Attribution']
    return author

def get_volumeID_from_title(title): # only for highlights 
    _ensure_loaded()
        
    matches = df_books[df_books["Title"].str.lower() == title.lower()]

    if matches.empty:
        raise ValueError(f"No book found with title: {title}")

    if len(matches) > 1:
        raise ValueError(f"Multiple books found with title: {title}")
    
    return matches.iloc[0]["ContentID"]

def get_books_by_author(author):
    _ensure_loaded()

    matches = df_books[df_books["Attribution"].str.lower() == author.lower()]

    if matches.empty:
        return []
    
    volume_ids = matches["ContentID"].tolist()

    # keep only books that actually have highlights
    highlighted_ids = set(df_highlights["VolumeID"])

    return [vid for vid in volume_ids if vid in highlighted_ids]

# ------------------------------------------------------------------------------------------------
# logic for filtering books to be used in CLI commands "books" and "export"
# ------------------------------------------------------------------------------------------------

def get_filtered_books(author=None, title=None, since=None, latest=None):
    _ensure_loaded()   

    books = get_highlight_counts()
    books = books.sort_values("LatestHighlight", ascending=False)

    
    if author:
        books = books[books["Attribution"].str.contains(author, case=False, na=False)]

    if title:
        books = books[books["Title"].str.contains(title, case=False, na=False)]

    if since:
        cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=since)
        books = books[books["LatestHighlight"] >= cutoff]

    if latest:
        books = books.head(latest)

    return books

def get_df_highlights():
    _ensure_loaded()
    return df_highlights



