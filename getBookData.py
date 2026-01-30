import sqlite3
import pandas as pd # pip install pandas
import re

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

# --------------------------------------------------------------------------------
# MATCHING KEPUB CONTENTIDs - helper fn
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

# -----------------------------------------------------------------------------------
# ATTACH KEPUB VOLUMEINDEX TO HIGHLIGHTS (epub as backup)
# ----------------------------------------------------------------------------------

# add kepub VolumeIndex column to highlights df manually using the lookup function
df_highlights['VolumeIndex'] = df_highlights['ContentID'].apply(lookup_kepub_index)


# insert epub VolumeIndex as backup where kepub VolumeIndex is missing, consider exact match of ContentID
    
rowidx_vidx = {} # (row_index : volume_index), rows from highlight table, vidx from epub chapter VolumeIndex

df1 = df_highlights.iterrows()  
for _i, row in df1:
    ContentID = row['ContentID']
    VolumeIndex = row['VolumeIndex']
    if pd.isna(VolumeIndex):                                                            # if highlight VolumeIndex is NaN
        epub_row = df_epub_chapters.loc[df_epub_chapters['ContentID'] == ContentID]     # get epub_chapter row with matching ContentID
        epub_vidx = epub_row.iloc[0]['VolumeIndex']                                     # get value of epub VolumeIndex

        rowidx_vidx[_i] = epub_vidx    # store epub VolumeIndex in dict with corresponding highlight index

# update highlight VolumeIndex column with vidx values from dict at row with index rowidx

for idx, val in rowidx_vidx.items():
    df_highlights.at[idx, 'VolumeIndex'] = val

#----------------------------------------------------------------------------------
# SORT HIGHLIGHTS BY CHAPTER INDICES
#----------------------------------------------------------------------------------

def sort_highlights(df):
    return df.sort_values(by=['VolumeID', 'VolumeIndex'])

df_highlights_sorted = sort_highlights(df_highlights)

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

# -------------------------------------------------------------------------------------------------
# getters - book title, author
# -------------------------------------------------------------------------------------------------

def get_book_title(volume_id):
    book = df_books[df_books['ContentID'] == volume_id]
    title = book.iloc[0]['Title']
    return title

def get_book_author(volume_id):
    book = df_books[df_books['ContentID'] == volume_id]
    author = book.iloc[0]['Attribution']
    return author

# -------------------------------------------------------------------------------------------------
# make safe file names - no [\\/*?:"<>|] allowed
# -------------------------------------------------------------------------------------------------

def safe_filename(filename):
    return re.sub(r'[\\/*?:"<>|]', "", filename)


# -------------------------------------------------------------------------------------------------
# EXPORT TO TXT FILE
# -------------------------------------------------------------------------------------------------

def export_txt(volumeID):

    title = get_book_title(volumeID)
    author = get_book_author(volumeID)

    filename = safe_filename(f'{title} - {author}.txt')

    with open(filename, 'w', encoding='utf-8') as f:

        f.write(title + "\n")
        f.write(author + "\n\n")
        
        chap_and_hl = map_chapters_to_highlights(sample_VolumeID)

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

def export_md(volumeID):

    title = get_book_title(volumeID)
    author = get_book_author(volumeID)

    filename = safe_filename(f'{title} - {author}.md')
    with open(filename, 'w', encoding='utf-8') as f:

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
# driver
# ------------------------------------------------------------------------------------------------

VolumeID_list = df_highlights['VolumeID'].unique().tolist()
sample_VolumeID = VolumeID_list[1]
export_md(sample_VolumeID)
print(f'Successfully called md function')
export_txt(sample_VolumeID)
print(f'Successfully called txt function')



