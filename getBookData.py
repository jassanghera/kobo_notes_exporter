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

# general purpose fn to create dataframe from SQL query
def create_df(query):
    rows = cursor.execute(query)
    records = rows.fetchall()
    columns = [col[0] for col in rows.description]
    df = pd.DataFrame(records, columns=columns)
    return df

df_books = create_df(books_query)
df_epub_chapters = create_df(epub_chapters_query)
df_kepub_chapters = create_df(kepub_chapters_query)
df_highlights = create_df(highlights_query)

# ----------------------------------------------------------------------------------
# PRINTING for testing
# ----------------------------------------------------------------------------------

# # print kepub chapters VolumeIndex column sample
# print("KEPUB Chapters VolumeIndex Sample:")
# print(df_kepub_chapters[['Title', 'VolumeIndex']].head(10))
# print("\n")

# # print epub chapters VolumeIndex column sample
# print("EPUB Chapters VolumeIndex Sample:")
# print(df_epub_chapters[['Title', 'VolumeIndex']].head(10))
# print("\n")

# --------------------------------------------------------------------------------
# MATCHING KEPUB CONTENTIDs
# ----------------------------------------------------------------------------------

# build a lookup dict for kepub ContentIDs and VolumeIndex
kepub_id_lookup = dict(
    zip(df_kepub_chapters['ContentID'], df_kepub_chapters['VolumeIndex'])
)

# pass in a highlight ContentID, return the VolumeIndex if prefix match kepub ContentID
def lookup_kepub_index(content_id):

    for ch_id, vol_idx in kepub_id_lookup.items():
        if ch_id.startswith(content_id):
            return vol_idx
    return None

# print sample of dictionary
# print("Kepub ContentID to VolumeIndex Lookup Sample:")
# for i, (ch_id, vol_idx) in enumerate(kepub_id_lookup.items()):
#     if i >= 5:
#         break
#     print(f"{ch_id} -> {vol_idx}")

# print('\n')

# -----------------------------------------------------------------------------------
# ATTACH KEPUB VOLUMEINDEX TO HIGHLIGHTS (epub as backup)
# ----------------------------------------------------------------------------------

# add kepub VolumeIndex column to highlights df manually using the lookup function
df_highlights['VolumeIndex'] = df_highlights['ContentID'].apply(lookup_kepub_index)
# print("Highlights with KEPUB VolumeIndex:")
# print(df_highlights[['ContentID', 'VolumeIndex']].tail(20))
# print("\n")

# insert epub VolumeIndex as backup where kepub VolumeIndex is missing, consider exact match of ContentID
    
rowidx_vidx = {} # (row_index : volume_index), rows from highlight table, vidx from epub chapter VolumeIndex

df1 = df_highlights.iterrows()  
for _i, row in df1:
    ContentID = row['ContentID']
    VolumeIndex = row['VolumeIndex']
    if pd.isna(VolumeIndex):                                                            # if highlight VolumeIndex is NaN
        epub_row = df_epub_chapters.loc[df_epub_chapters['ContentID'] == ContentID]     # get epub_chapter row with matching ContentID
        epub_vidx = epub_row.iloc[0]['VolumeIndex']                                     # get value of epub VolumeIndex
        # print(epub_vidx)

        rowidx_vidx[_i] = epub_vidx    # store epub VolumeIndex in dict with corresponding highlight index
        # print(rowidx_vidx)

        # print(_i)
        # df_highlights.at[_i, 'VolumeIndex'] = epub_vidx
        # print(df_highlights.loc[_i,'VolumeIndex'])
        
# print("Highlights with KEPUB VolumeIndex AFTER EPUB BACKUP:")
# print(df_highlights[['ContentID', 'VolumeIndex']].tail(20))
# print("\n")

# update highlight VolumeIndex column with vidx values from dict at row with index rowidx

for idx, val in rowidx_vidx.items():
    print(idx, val)
    df_highlights.at[idx, 'VolumeIndex'] = val

print("Highlights with KEPUB VolumeIndex AFTER EPUB BACKUP ATTEMPT 2:")
print(df_highlights[['ContentID', 'VolumeIndex']].tail(10))
print("\n")


# -----------------------------------------------------------------------------------
# PRINTING FOR TESTING
# ----------------------------------------------------------------------------------

# print("HIGHLIGHT:")
# print(df_highlights['ContentID'].iloc[0])
# print("\n")

# print("\nCHAPTER:")
# print(df_kepub_chapters['ContentID'].iloc[0])
# print("\n")

# sample_highlight = df_highlights['ContentID'].iloc[0]

# matches = [
#     ch_id for ch_id in df_kepub_chapters['ContentID']
#     if ch_id.startswith(sample_highlight)
# ]

# print("MATCHES:")
# print(len(matches))
# print(matches[:5])
# print("\n")

#----------------------------------------------------------------------------------
# SORT HIGHLIGHTS BY CHAPTER INDICES
#----------------------------------------------------------------------------------

def sort_highlights(df):
    return df.sort_values(by=['VolumeID', 'VolumeIndex'])

df_highlights_sorted = sort_highlights(df_highlights)

# print("Sorted Highlights Sample:")
# print(df_highlights_sorted[['ContentID', 'VolumeIndex']].tail(10))
# print("\n")

# print(df_highlights_sorted.iloc[122])

# ----------------------------------------------------------------------------------
# CHAPTERS & HIGHLIGHTS FOR A GIVEN BOOK
# ----------------------------------------------------------------------------------

VolumeID_list = df_highlights['VolumeID'].unique().tolist()
sample_VolumeID = VolumeID_list[5]

def map_chapters_to_highlights(volume_id):


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


# # pretty print chapter titles & highlights
# def print_mapped_highlights(mapped_highlights):

#     print("Mapped Highlights to Chapters:")
#     print('\n')

#     for chapter, highlights in mapped_highlights.items():
#         print(f'Chapter: {chapter}')
#         for highlight in highlights:
#             print(f'- {highlight}')
#         print("\n")
#     print("\n")

# # example usage
# mapped_highlights = map_chapters_to_highlights(sample_VolumeID)
# print_mapped_highlights(mapped_highlights)


# --------------------------------------------------------------------------------------------------
# GET LIST OF HIGHLIGHTED BOOKS WITH COUNT OF HIGHLIGHTS FOR EACH
# --------------------------------------------------------------------------------------------------

def get_highlight_counts():
    highlight_counts = df_highlights['VolumeID'].value_counts().reset_index() # value_counts gives a Series, reset_index to convert to DataFrame

    # rename columns
    highlight_counts.columns = ['VolumeID', 'HighlightCount']

    # merge with book data to get titles and authors
    books_with_highlights = highlight_counts.merge(df_books, left_on='VolumeID', right_on='ContentID', how='left')

    # select relevant columns
    return books_with_highlights[['Title', 'Attribution', 'HighlightCount']]


# print("Books with Highlights:")
# print(get_highlight_counts())
# print("\n")


# # --------------------------------------------------------------------------------------------------
# # GET LIST OF CHAPTER TITLES FOR A GIVEN BOOK
# # --------------------------------------------------------------------------------------------------

# write a function that gets the chapter titles for a given VolumeID from either the kepub or epub chapters dataframes
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


# # example usage
# chapter_titles = get_chapter_titles(sample_VolumeID)

# # pretty print all chapter titles
# print("Chapter Titles:")
# for title in chapter_titles:
#     print(f"- {title}")
# print("\n")


# -------------------------------------------------------------------------------------------------
# getters - book title, author
# -------------------------------------------------------------------------------------------------

def get_book_title(volume_id):
    book = df_books[df_books['ContentID'] == volume_id]
    title = book.iloc[0]['Title']
    return title

# book_title = get_book_title(sample_VolumeID)
# print(f'The sample book is: {book_title}')

def get_book_author(volume_id):
    book = df_books[df_books['ContentID'] == volume_id]
    author = book.iloc[0]['Attribution']
    return author

# book_author = get_book_author(sample_VolumeID)
# print(f'The same book author is: {book_author}')


# -------------------------------------------------------------------------------------------------
# EXPORT TO TXT FILE
# -------------------------------------------------------------------------------------------------
file = 'test.txt'
with open(file, 'w', encoding='utf-8') as f:

    f.write(get_book_title(sample_VolumeID) + "\n")
    f.write(get_book_author(sample_VolumeID) + "\n\n")
    
    chap_and_hl = map_chapters_to_highlights(sample_VolumeID)

    for ch, hl in chap_and_hl.items():
        f.write("_______________________________________________________________" + "\n")
        f.write(f'Chapter: {ch}' + '\n\n')
    
        for h in hl:
            f.write(f'- {h}' + '\n')
        f.write("\n")
    f.write("\n")

    print(f'Wrote to {f.name} successfully!')

