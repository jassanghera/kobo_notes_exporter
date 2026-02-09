import sqlite3
import pandas as pd # pip install pandas
import re

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

def load_data(db):

    with sqlite3.connect(db) as connection:

        cursor = connection.cursor()

        # general purpose fn to create dataframe from SQL query
        def create_df(query):
            rows = cursor.execute(query)
            records = rows.fetchall()
            columns = [col[0] for col in rows.description]
            df = pd.DataFrame(records, columns=columns)
            return df
        
        return {
            "books": create_df(books_query),
            "epub": create_df(epub_chapters_query),
            "kepub": create_df(kepub_chapters_query),
            "highlights": create_df(highlights_query),
        }

db = 'KoboReader.sqlite'
data = load_data(db)

df_books = data["books"]
df_epub_chapters = data["epub"]
df_kepub_chapters = data["kepub"]
df_highlights = data["highlights"]

df_highlights["DateModified"] = pd.to_datetime(df_highlights["DateModified"])


# build a lookup dict for kepub ContentIDs and VolumeIndex
kepub_id_lookup = dict(zip(df_kepub_chapters['ContentID'], df_kepub_chapters['VolumeIndex']))

# ----------------------------------------------------------------------------------
# MATCHING KEPUB CONTENTIDs - helper fn
# ----------------------------------------------------------------------------------

# pass in a highlight ContentID, return the VolumeIndex if prefix match kepub ContentID
def lookup_kepub_index(content_id):

    for ch_id, vol_idx in kepub_id_lookup.items():
        if ch_id.startswith(content_id):
            return vol_idx
    return None

# -----------------------------------------------------------------------------------
# ATTACH KEPUB VOLUMEINDEX TO HIGHLIGHTS (epub as backup)
# -----------------------------------------------------------------------------------

def add_v_idx_to_kepub():

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
    highlights_with_v_idx = add_v_idx_to_kepub()
    return highlights_with_v_idx.sort_values(by=['VolumeID', 'VolumeIndex'])


# ----------------------------------------------------------------------------------
# CHAPTERS & HIGHLIGHTS FOR A GIVEN BOOK
# ----------------------------------------------------------------------------------

def map_chapters_to_highlights(volume_id):

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
    book = df_books[df_books['ContentID'] == volume_id]
    title = book.iloc[0]['Title']
    return title

def get_book_author(volume_id):
    book = df_books[df_books['ContentID'] == volume_id]
    author = book.iloc[0]['Attribution']
    return author

def get_volumeID_from_title(title): # only for highlights 
        
    matches = df_books[df_books["Title"].str.lower() == title.lower()]

    if matches.empty:
        raise ValueError(f"No book found with title: {title}")

    if len(matches) > 1:
        raise ValueError(f"Multiple books found with title: {title}")
    
    return matches.iloc[0]["ContentID"]

def get_books_by_author(author):

    matches = df_books[df_books["Attribution"].str.lower() == author.lower()]

    if matches.empty:
        return []
    
    volume_ids = matches["ContentID"].tolist()

    # keep only books that actually have highlights
    highlighted_ids = set(df_highlights["VolumeID"])

    return [vid for vid in volume_ids if vid in highlighted_ids]

# ------------------------------------------------------------------------------------------------
# logic for filtering books to be used in CLI commands
# ------------------------------------------------------------------------------------------------

def get_filtered_books(author=None, title=None, since=None, latest=None):

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


# -------------------------------------------------------------------------------------------------
# make safe file names - no [\\/*?:"<>|] allowed
# -------------------------------------------------------------------------------------------------

def safe_filename(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "", name)


# -------------------------------------------------------------------------------------------------
# EXPORT TO TXT FILE
# -------------------------------------------------------------------------------------------------

def export_txt(volumeID, output_dir):

    title = get_book_title(volumeID)
    author = get_book_author(volumeID)

    filename = safe_filename(f'{title} - {author}.txt')
    filepath = output_dir / f"{filename}"

    with open(filepath, 'w', encoding='utf-8') as f:

        f.write(title + "\n")
        f.write(author + "\n\n")
        
        chap_and_hl = map_chapters_to_highlights(volumeID)

        for ch, hl in chap_and_hl.items():
            f.write("_______________________________________________________________" + "\n")
            f.write(f'Chapter: {ch}' + '\n\n')
        
            for h in hl:
                f.write(f'- {h}' + '\n')
            f.write("\n")
        f.write("\n")

        print(f'Wrote to {f.name} successfully!')


# ------------------------------------------------------------------------------------------------
# EXPORT TO MARKDOWN FILE
# ------------------------------------------------------------------------------------------------

def export_md(volumeID, output_dir):

    title = get_book_title(volumeID)
    author = get_book_author(volumeID)

    filename = safe_filename(f'{title} - {author}.md')
    filepath = output_dir / f"{filename}"

    with open(filepath, 'w', encoding='utf-8') as f:

        f.write(f'# {title}\n')
        f.write(f'## {author}\n\n')
        
        chap_and_hl = map_chapters_to_highlights(volumeID)

        for ch, hl in chap_and_hl.items():
            f.write("_______________________________________________________________" + "\n")
            f.write(f'### {ch}\n\n')
        
            for h in hl:
                f.write(f'- {h}\n')
            f.write("\n")
        f.write("\n")

        print(f'Wrote to {f.name} successfully!')


# ------------------------------------------------------------------------------------------------
# main
# ------------------------------------------------------------------------------------------------

def main():

    VolumeID_list = df_highlights['VolumeID'].unique().tolist()
    sample_VolumeID = VolumeID_list[1]

    export_md(sample_VolumeID)
    export_txt(sample_VolumeID)

    print("Export complete!")



    
if __name__ == "__main__":

    main()

