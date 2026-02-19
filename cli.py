import typer
# import getBookData
import pandas as pd
import json
from rich import print
from rich.table import Table
from rich.console import Console
from rich.progress import Progress
from typing import Annotated, Optional 
from pathlib import Path
import core.device as device
import core.sync_db as sync_db
# import core.database as database
import core.parser as parser
import core.exporter as exporter

CACHE_FILE = Path("./data/kobo_last_query.json")
console = Console()
app = typer.Typer(help="This is a really friendly CLI tool to help you export your ereader highlights :)")

# --------------------------------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------------------------------

def resolve_export_path(output_dir: Optional[str]) -> Path:
    if output_dir:
        path = Path(output_dir)
    else:
        path = Path.cwd() / "exports"

    path.mkdir(parents=True, exist_ok=True)
    return path


def write_cache(volume_ids: list[str]):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(volume_ids, f)

def read_cache() -> list[str]:
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def clear_cache():
    write_cache([])

# --------------------------------------------------------------------------
# COMMANDS
# --------------------------------------------------------------------------


@app.command()
def hello(name: str = typer.Argument(help="Person to greet")):
    """
    say hello to someone
    """
    console.print(f"[green]hello {name}[/green] :smile:")

@app.command()
def err_test():
    """
    test command for development
    """
    print("This is a test command. Hello world!")

    try:
        x = int("abc")
    except ValueError:
        print("Invalid number")


@app.command()
def detect():
    """
    detect attached kobo device and locate database
    """

    db_path = device.find_kobo_db()

    if not db_path:
        print(f"[red]No Kobo device detected[/red]")
        raise typer.Exit(code=1)

    print(f"[green]Kobo database found at:[/green] {db_path}")   

@app.command()
def sync():
    """
    Sync Kobo database locally 
    """
    print(f"Looking for Kobo device...")
    db_path = device.find_kobo_db()

    if not db_path:
        print(f"[red]No Kobo device detected. Please connect your device and try again.[/red]")
        return

    metadata = sync_db.perform_sync(db_path)
    print(f"[green]Sync complete![/green]")
    print(f"Last sync: {metadata['last_sync']}") 


@app.command()
def books(
            author: Annotated[Optional[str], typer.Option("--author", "-a", help="Filter by author")] = None,
            title: Annotated[Optional[str], typer.Option("--title", "-t", help="Filter by title")] = None,
            since: Annotated[Optional[int], typer.Option("--since", help="Show books updated in last N days")] = None,
            latest: Annotated[Optional[int], typer.Option("--latest", help="Show top N most recently updated books")] = None,
            limit: Annotated[Optional[int], typer.Option("--limit", "-l", help="Limit number of results shown")] = 10,
            all: Annotated[bool, typer.Option(help="show all books")] = False
        ):
    """
    Show books with highlight counts
    """
    
    sync_db.ensure_local_db()

    books = parser.get_highlight_counts()
    books = books.sort_values("LatestHighlight", ascending=False)

    books = parser.get_filtered_books(
        author=author,
        title=title,
        since=since,
        latest=latest
    )

    if books.empty:
        console.print("[yellow]No books matched your filters.[/yellow]")
        raise typer.Exit()


    if all:
        pass
    elif limit:
        books = books.head(limit)
    
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

    # store book_ids in cache
    visible_volume_ids = books["VolumeID"].tolist()
    write_cache(visible_volume_ids)


@app.command()
def export(    
            author: Annotated[Optional[str], typer.Option("--author", "-a")] = None,
            title: Annotated[Optional[str], typer.Option("--title", "-t")] = None,
            since: Annotated[Optional[int], typer.Option("--since")] = None,
            latest: Annotated[Optional[int], typer.Option("--latest")] = None,
            txt: Annotated[bool, typer.Option(help="export to txt format")] = False,
            output_dir: Annotated[Optional[str],typer.Option("--output-dir", "-o", help="Directory to export files into")] = None
        ):
    """
    Export books matching filters to markdown file
    """

    sync_db.ensure_local_db()

    filters_used = any([author, title, since, latest])
    used_cache = False

    # CASE 1: filter provided --> compute fresh selection
    if filters_used:
        books = parser.get_filtered_books(
            author=author,
            title=title,
            since=since,
            latest=latest
        )

        if books.empty:
            typer.echo("No books matched your filters.")
            raise typer.Exit()
        
        books = books["VolumeID"].tolist()

    # CASE 2: no filters provided --> use cache
    else: 
        books = read_cache()

        if not books:
            typer.echo("No books selected")
            typer.echo("Run 'books' first or provide filters")
            raise typer.Exit()
        
        used_cache = True

    # specify export path
    export_path = resolve_export_path(output_dir)

    # export selected books
    for book_id in books:

        if txt:
            typer.echo(f"Exporting {book_id} as txt...")
            exporter.export_txt(book_id, export_path)
        else:
            typer.echo(f"Exporting {book_id}...")
            exporter.export_md(book_id, export_path)

    typer.echo(f"Exported {len(books)} book(s).")

    typer.echo("Export complete.")

    # clear cache if used
    if used_cache:
        clear_cache()
        typer.echo("Selection cleared.")


@app.command()
def export_all(
    force: Annotated[bool, typer.Option(prompt="Are you sure you want to export all?")],
    txt: Annotated[bool, typer.Option(help="export to txt format")] = False,
    output_dir: Annotated[Optional[str],typer.Option("--output-dir", "-o", help="Directory to export files into")] = None
    ):
    """
    export all highlights to md, with --txt as option
    """

    sync_db.ensure_local_db()

    if force:
        books = parser.get_df_highlights()['VolumeID'].unique().tolist()

        # specify export path
        export_path = resolve_export_path(output_dir)

        # with Progress() as progress:

        #     task = progress.add_task("Exporting books...", total=len(books))
        #     if txt:
        #         for book_id in books:
        #             getBookData.export_txt(book_id, export_path)
        #             print('you chose txt')
        #             progress.advance(task)
        #     else:
        #         for book_id in books:
        #             getBookData.export_md(book_id, export_path)
        #             title = getBookData.get_book_title(book_id)
        #             author = getBookData.get_book_author(book_id)
        #             print(f'Exported {title} by {author}!')
        #             progress.advance(task)

        with Progress() as progress:
            task = progress.add_task("Exporting books...", total=len(books))

            for book_id in books:
                title = parser.get_book_title(book_id)

                progress.update(task, description=f"Exporting [cyan]{title}[/cyan]")

                if txt:
                    exporter.export_txt(book_id, export_path)
                else:
                    exporter.export_md(book_id, export_path)

                progress.advance(task)

        console.print("\n[bold green]✔ Export complete.[/bold green]\n")

        
        
    else:
        print("Operation cancelled")


def main():
    try:
        app()
    except ValueError as e:
        console.print(f"[red]❌ Error:[/red] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print("[red]❌ Unexpected error occurred.[/red]")
        console.print(f"[dim]{e}[/dim]")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    main()


