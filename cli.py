import typer
from rich import print
from rich.table import Table
from rich.console import Console
from typing import Annotated, Optional 
import getBookData
import pandas as pd

console = Console()
app = typer.Typer(help="This is a really friendly CLI tool :)")


@app.command()
def hello(name: str = typer.Argument(help="Person to greet")):
    """
    say hello to someone
    """
    print(f"[green]hello {name}[/green] :smile:")

@app.command()
def goodbye(name: str = typer.Argument(help="Person to greet"),
            iq : int = typer.Argument(help="Person's IQ")):
    """
    say bye bye to someone and tell them their iq
    """
    print(f"[red]bye bye {name}[/red]")
    print(f"your iq is {iq}")

@app.command()
def books(
    author: Annotated[Optional[str], typer.Option("--author", "-a", help="Filter by author")] = None,
    title: Annotated[Optional[str], typer.Option("--title", "-t", help="Filter by title")] = None,
    since: Annotated[Optional[int], typer.Option("--since", help="Show books updated in last N days")] = None,
    latest: Annotated[Optional[int], typer.Option("--latest", help="Show top N most recently updated books")] = None
):
    """
    Show books with highlight counts
    """

    books = getBookData.get_highlight_counts()
    books = books.sort_values("LatestHighlight", ascending=False)

    if author:
        books = books[books["Attribution"].str.contains(author, case=False, na=False)]

    if title:
        books = books[books["Title"].str.contains(title, case=False, na=False)]
    
    if since:
        cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=since)
        books = books[books["LatestHighlight"] >= cutoff]

    if latest:
        books = books.sort_values("LatestHighlight", ascending=False).head(latest)
    

    # formatting table for display
    table = Table(title="Books With Highlights")

    table.add_column("Title", style="bold")
    table.add_column("Author")
    table.add_column("Highlights", style="cyan bold", justify="right")
    table.add_column("Last Highlighted", style="green")

    for _, row in books.iterrows():
        table.add_row(
            row["Title"],
            row["Attribution"],
            str(row["HighlightCount"]),
            str(row["LatestHighlight"])
        )

    console.print()
    console.print(table)
    console.print()



@app.command()
def export_title(
    title: str = typer.Argument(help="title of selected book, case insensitive"),
    txt: Annotated[bool, typer.Option(help="export to txt format")] = False
    ):
    """
    export highlights to md for given title, --txt as option
    """
    book_id = getBookData.get_volumeID_from_title(title)

    if txt:
        getBookData.export_txt(book_id)
        print("you chose txt")
    else:
        getBookData.export_md(book_id)
        print(f'Exported {title}!')

@app.command()
def export_author(
    author: str = typer.Argument(help="author name of selected book, case insensitive"),
    txt: Annotated[bool, typer.Option(help="export to txt format")] = False
    ):
    """
    export all highlights from given author, with --txt as option
    """
    books = getBookData.get_books_by_author(author)

    if txt:
        for book_id in books:
            getBookData.export_txt(book_id)
            print("you chose txt")
    else:
        for book_id in books:
            getBookData.export_md(book_id)
            title = getBookData.get_book_title(book_id)
            author = getBookData.get_book_author(book_id)
            print(f'Exported {title} by {author}!')

@app.command()
def export_all(
    force: Annotated[bool, typer.Option(prompt="Are you sure you want to export all?")],
    txt: Annotated[bool, typer.Option(help="export to txt format")] = False
    ):
    """
    export all highlights to md, with --txt as option
    """
    if force:
        books = getBookData.df_highlights['VolumeID'].unique().tolist()

        if txt:
            for book_id in books:
                getBookData.export_txt(book_id)
                print('you chose txt')
        else:
            for book_id in books:
                getBookData.export_md(book_id)
                title = getBookData.get_book_title(book_id)
                author = getBookData.get_book_author(book_id)
                print(f'Exported {title} by {author}!')
    else:
        print("Operation cancelled")



if __name__ == "__main__":
    app()

