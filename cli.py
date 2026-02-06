import typer
from rich import print
from rich.table import Table
from rich.console import Console
import getBookData

console = Console()
app = typer.Typer(help="This is a really friendly CLI tool :)")


@app.command()
def hello(name: str = typer.Argument(help="Person to greet")):
    """
    say hello to someone
    """
    print(f"[green]hello {name}[/green]")

@app.command()
def goodbye(name: str = typer.Argument(help="Person to greet"),
            iq : int = typer.Argument(help="Person's IQ")):
    """
    say bye bye to someone and tell them their iq
    """
    print(f"[red]bye bye {name}[/red]")
    print(f"your iq is {iq}")

@app.command()
def books():
    """
    Show books with highlight counts
    """
    books = getBookData.get_highlight_counts()

    table = Table(title="Books With Highlights")

    table.add_column("Title", style="bold")
    table.add_column("Author")
    table.add_column("Highlights", justify="right")

    for _, row in books.iterrows():
        table.add_row(
            row["Title"],
            row["Attribution"],
            str(row["HighlightCount"])
        )

    console.print(table)

@app.command()
def export(title):
    """
    export highlights to md for given title
    """
    book_id = getBookData.get_volumeID_from_title(title)

    getBookData.export_md(book_id)
    print(f'Exported {title}!')

@app.command()
def exporta(author):
    """
    export all highlights from given author
    """
    books = getBookData.get_books_by_author(author)

    for book_id in books:
        getBookData.export_md(book_id)
        title = getBookData.get_book_title(book_id)
        author = getBookData.get_book_author(book_id)
        print(f'Exported {title} by {author}!')

@app.command()
def exportall():
    """
    export all highlights to md
    """
    books = getBookData.df_highlights['VolumeID'].unique().tolist()

    for book_id in books:
        getBookData.export_md(book_id)
        title = getBookData.get_book_title(book_id)
        author = getBookData.get_book_author(book_id)
        print(f'Exported {title} by {author}!')



if __name__ == "__main__":
    app()


# GOALS:
# command to export specific book's highlights
# command to export all highlights