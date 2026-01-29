import sqlite3
import pandas as pd # pip install pandas

# connect to the KoboReader sqlite database

connection = sqlite3.connect('KoboReader.sqlite')
cursor = connection.cursor()

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
SELECT BookmarkID, ContentID, VolumeID, Text FROM Bookmark;
"""

# make df of books from content table with their ContentIDs, titles, and authors
def get_book_list():
    rows = cursor.execute(books_query)
    records = rows.fetchall()
    columns = [col[0] for col in rows.description]
    df = pd.DataFrame(records, columns=columns)
    return df

df_books = get_book_list()
# print("Book List:")
# print(get_book_list().head())
# print("\n")

# make df of epub chapters from content table with their ContentIDs, BookIDs, and titles
def get_epub_chapters():
    rows = cursor.execute(epub_chapters_query)
    records = rows.fetchall()
    columns = [col[0] for col in rows.description]
    df = pd.DataFrame(records, columns=columns)
    return df

df_epub_chapters = get_epub_chapters()
# print("EPUB Chapters:")
# print(get_epub_chapters().head())
# print("\n")

# make df of kepub chapters from content table with their ContentIDs, BookIDs, and titles
def get_kepub_chapters():
    rows = cursor.execute(kepub_chapters_query)
    records = rows.fetchall()
    columns = [col[0] for col in rows.description]
    df = pd.DataFrame(records, columns=columns)
    return df

df_kepub_chapters = get_kepub_chapters()
print("KEPUB Chapters:")
print(get_kepub_chapters().head())
print("\n")


# make df of highlights from the Bookmark table with their ContentID, VolumeID (=BookID), and Text
def get_all_highlights():
    rows = cursor.execute(highlights_query)
    records = rows.fetchall()
    columns = [col[0] for col in rows.description]
    df = pd.DataFrame(records, columns=columns)
    return df

df_highlights = get_all_highlights()
# print("All Highlights:")
# print(get_all_highlights().head())
# print("\n")

# ----------------------------------------------------------------------------------
# PRINTING
# ----------------------------------------------------------------------------------

# print kepub chapters VolumeIndex column sample
print("KEPUB Chapters VolumeIndex Sample:")
print(df_kepub_chapters[['Title', 'VolumeIndex']].tail(10))
print("\n")

# print epub chapters VolumeIndex column sample
print("EPUB Chapters VolumeIndex Sample:")
print(df_epub_chapters[['Title', 'VolumeIndex']].tail(10))
print("\n")

# --------------------------------------------------------------------------------
# MATCHING KEPUB CONTENTIDs
# ----------------------------------------------------------------------------------

# build a lookup dict for kepub ContentIDs and VolumeIndex
kepub_id_lookup = dict(
    zip(df_kepub_chapters['ContentID'], df_kepub_chapters['VolumeIndex'])
)

def lookup_kepub_index(content_id):

    for ch_id, vol_idx in kepub_id_lookup.items():
        if content_id.startswith(ch_id):
            return vol_idx
    return None

# print sample of dictionary
print("Kepub ContentID to VolumeIndex Lookup Sample:")
for i, (ch_id, vol_idx) in enumerate(kepub_id_lookup.items()):
    if i >= 5:
        break
    print(f"{ch_id} -> {vol_idx}")

# ----------------------------------------------------------------------------------
# JOIN CHAPTER INDICES TO HIGHLIGHTS
# ----------------------------------------------------------------------------------

def join_hl_to_VolumeIndex():

    # create minimal kepub chapter index - only keep ContentID and VolumeIndex
    df_kepub_index = (
        df_kepub_chapters[['ContentID', 'VolumeIndex']]
        .rename(columns={'VolumeIndex': 'VolumeIndex_kepub'})
    )

    # create minimal epub chapter index
    df_epub_index = (
        df_epub_chapters[['ContentID', 'VolumeIndex']]
        .rename(columns={'VolumeIndex': 'VolumeIndex_epub'})
    )

    # join highlights with kepub VolumeIndex on ContentID exact match

    df_hl_with_kepub = df_highlights.merge(
        df_kepub_index,
        on='ContentID',
        how='left'
    )

    df_hl_with_all_index = df_hl_with_kepub.merge(
        df_epub_index,
        on='ContentID',
        how='left'
    )

    return df_hl_with_all_index

df_highlights_with_indices = join_hl_to_VolumeIndex()
print("Highlights with Chapter Indices:")
print(df_highlights_with_indices.tail())
print("\n")

# print first row in readable format
check_row = df_highlights_with_indices.iloc[100]
print("First Highlight with Indices:")
print(check_row)
print("\n")

# sanity check
print("Sample of Highlights with Volume Indices:")
print(df_highlights_with_indices[['VolumeIndex_kepub', 'VolumeIndex_epub']].tail(10))




#----------------------------------------------------------------------------------
# SORT HIGHLIGHTS BY CHAPTER INDICES
#----------------------------------------------------------------------------------

def sort_highlights_by_VolumeIndex():
    pass


# --------------------------------------------------------------------------------------------------
# HIGHLIGHT BOOKS with COUNTS
# --------------------------------------------------------------------------------------------------

# def get_highlight_counts():
#     highlight_counts = df_highlights['VolumeID'].value_counts().reset_index() # value_counts gives a Series, reset_index to convert to DataFrame

#     # rename columns
#     highlight_counts.columns = ['VolumeID', 'HighlightCount']

#     # merge with book data to get titles and authors
#     books_with_highlights = highlight_counts.merge(df_books, left_on='VolumeID', right_on='ContentID', how='left')

#     # select relevant columns
#     return books_with_highlights[['Title', 'Attribution', 'HighlightCount']]


# print("Books with Highlights:")
# print(get_highlight_counts())
# print("\n")


# ----------------------------------------------------------------------------------
# CHAPTERS & HIGHLIGHTS FOR A GIVEN BOOK
# ----------------------------------------------------------------------------------

VolumeID_list = df_highlights['VolumeID'].unique().tolist()
sample_VolumeID = VolumeID_list[2]

def map_chapters_to_highlights(volume_id):

    # get all highlights for the given VolumeID
    book_highlights = df_highlights[df_highlights['VolumeID'] == volume_id]
    # print(book_highlights)

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

# example usage
mapped_highlights = map_chapters_to_highlights(sample_VolumeID)
print("Mapped Highlights to Chapters:")
print('\n')
for chapter, highlights in mapped_highlights.items():
    print(f"Chapter: {chapter}")
    for highlight in highlights:
        print(f"- {highlight}")
        print("\n")
    print("\n")
print("\n")





# # --------------------------------------------------------------------------------------------------
# # GET LIST OF CHAPTER TITLES FOR A GIVEN BOOK
# # ------------------------------------------------------------------------------------------------__

# # write a function that gets the chapter titles for a given VolumeID from either the kepub or epub chapters dataframes
# def get_chapter_titles(volume_id):
#     # try kepub chapters first
#     kepub_chapters = df_kepub_chapters[df_kepub_chapters['BookID'] == volume_id].sort_values('VolumeIndex')
#     if not kepub_chapters.empty:
#         return kepub_chapters['Title'].tolist()

#     # if no kepub chapters, try epub chapters
#     epub_chapters = df_epub_chapters[df_epub_chapters['BookID'] == volume_id].sort_values('VolumeIndex')
#     if not epub_chapters.empty:
#         return epub_chapters['Title'].tolist()

#     return []


# # example usage
# chapter_titles = get_chapter_titles(sample_VolumeID)

# # pretty print all chapter titles
# print("Chapter Titles:")
# for title in chapter_titles:
#     print(f"- {title}")
# print("\n")




