"""
kobo_notes_exporter.cli

Command-line interface for Kobo Notes Exporter.

This module defines the Typer app and user-facing commands. It is responsible for:
- parsing CLI options/arguments
- printing user-friendly output (Rich)
- orchestrating calls into core modules (device, sync_db, parser, exporter)

Business logic (data parsing, filtering, exporting) lives in `kobo_notes_exporter.core`.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Annotated, Optional

import pandas as pd
import typer
from rich.console import Console
from rich.progress import Progress
from rich.table import Table

from kobo_notes_exporter.core import device, exporter, parser, sync_db

# --------------------------------------------------------------------------
# APP SETUP
# --------------------------------------------------------------------------

console = Console()
app = typer.Typer(help="This is a really friendly CLI tool to help you export your ereader highlights :)")

# Stores the most recent `books` selection so `export` can run without filters.
CACHE_FILE = Path("./data/kobo_last_query.json")

# --------------------------------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------------------------------

def resolve_export_path(output_dir: Optional[str]) -> Path:
    """Return the directory where exports should be written.

    If `output_dir` is not provided, defaults to `<cwd>/exports`.
    Ensures the directory exists.

    The directory is created if it does not exist.
    """
    if output_dir:
        path = Path(output_dir)
    else:
        path = Path.cwd() / "exports"

    path.mkdir(parents=True, exist_ok=True)
    return path

def write_cache(volume_ids: list[str]):
    """Persist the list of visible VolumeIDs so `export` can run without filters."""
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(volume_ids, f)

def read_cache() -> list[str]:
    """Load the cached list of VolumeIDs from the last `books` command."""
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def clear_cache():
    """Clear the cached selection used by `export` when no filters are provided."""
    write_cache([])

def show_sync_status():
    """Print the last sync time if local sync metadata is available."""

    metadata_path = Path("./data/sync_metadata.json")

    if not metadata_path.exists():
        console.print("[yellow]⚠ No local database found.[/yellow]")
        console.print("[dim]Run 'sync' to create a local copy.[/dim]")
        return

    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        last_sync = metadata.get("last_sync")

        if last_sync:
            try:
                dt = datetime.fromisoformat(last_sync)
                formatted = dt.strftime("%d-%m-%Y %H:%M") # format: 17-02-2026 13:05
                # formatted = dt.strftime("%d %b %Y at %H:%M") # format: 17 Feb 2026 13:05
                console.print(f"[dim]Database last synced:[/dim] {formatted}")
            except ValueError:
                console.print(f"[dim]Database last synced:[/dim] {last_sync}")
        else:
            console.print("[yellow]⚠ Sync metadata incomplete.[/yellow]")

    except Exception:
        console.print("[yellow]⚠ Could not read sync metadata.[/yellow]")


# --------------------------------------------------------------------------
# COMMANDS
# --------------------------------------------------------------------------

@app.command()
def hello(name: str = typer.Argument(help="Person to greet")):
    """
    Say hello to someone
    """
    console.print(f"[green]hello {name}[/green] :smile:")

@app.command()
def detect():
    """
    Detect attached Kobo device and display database path (no sync)
    """

    db_path = device.find_kobo_db()

    if not db_path:
        console.print(f"[red]No Kobo device detected[/red]")
        raise typer.Exit(code=1)

    console.print(f"[green]Kobo database found at:[/green] {db_path}")   

@app.command()
def sync():
    """Copy the Kobo database locally for safe processing""" 
    console.print(f"[bold]Looking for Kobo device...[/bold]")
    db_path = device.find_kobo_db()

    if not db_path:
        console.print(f"[red]No Kobo device detected.[/red]")
        console.print("Please connect your device and run [bold cyan]sync[/bold cyan] again.")
        raise typer.Exit(code=1)

    metadata = sync_db.perform_sync(db_path)
    console.print(f"[bold green]✔ Sync complete![/bold green]")
    console.print(f"[dim]Last sync: {metadata['last_sync']}[/dim]") 


@app.command()
def books(
            author: Annotated[Optional[str], typer.Option("--author", "-a", help="Filter by author")] = None,
            title: Annotated[Optional[str], typer.Option("--title", "-t", help="Filter by title")] = None,
            since: Annotated[Optional[int], typer.Option("--since", help="Filter books updated in last N days")] = None,
            latest: Annotated[Optional[int], typer.Option("--latest", help="Filter top N most recently updated books")] = None,
            limit: Annotated[Optional[int], typer.Option("--limit", "-l", help="Limit number of results shown")] = 10,
            all: Annotated[bool, typer.Option(help="Show all books")] = False
        ):
    """Show books with highlight counts, options to filter by author/title/recency"""
    
    sync_db.ensure_local_db()
    
    console.print()
    show_sync_status()

    console.print("[dim]Loading highlight data...[/dim]")

    # Filter + sort logic lives in the parser module
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
        console.print("[dim]Try adjusting your filters or run [bold cyan]books --all[/bold cyan] to see everything.[/dim]")
        console.print()
        raise typer.Exit()

    if all:
        pass
    elif limit:
        books = books.head(limit)
    
    # format table for display
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

    # Cache the visible books so `export` can run without repeating filters
    visible_volume_ids = books["VolumeID"].tolist()
    write_cache(visible_volume_ids)


@app.command()
def export(    
            author: Annotated[Optional[str], typer.Option("--author", "-a", help="Filter by author")] = None,
            title: Annotated[Optional[str], typer.Option("--title", "-t", help="Filter by title")] = None,
            since: Annotated[Optional[int], typer.Option("--since", help="Filter books updated in last N days")] = None,
            latest: Annotated[Optional[int], typer.Option("--latest", help="Filter top N most recently updated books")] = None,
            txt: Annotated[bool, typer.Option(help="export to txt format")] = False,
            output_dir: Annotated[Optional[str],typer.Option("--output-dir", "-o", help="Specify directory to export files into")] = None
        ):
    """
    Export highlights for selected books to Markdown (default) or TXT
    """

    sync_db.ensure_local_db()
    
    console.print()
    show_sync_status()
    console.print()

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
            console.print("[yellow]No books matched your filters.[/yellow]")
            raise typer.Exit()
        
        books = books["VolumeID"].tolist()

    # CASE 2: no filters provided --> use cache
    else: 
        books = read_cache()

        if not books:
            console.print("No books selected")
            console.print("Run 'books' first or provide filters")
            raise typer.Exit()
        
        used_cache = True

    export_path = resolve_export_path(output_dir)
    console.print(f"[bold]Preparing to export {len(books)} book(s)...[/bold]")

    # export formatting lives in exporter module
    for book_id in books:

        title = parser.get_book_title(book_id)

        if txt:
            console.print(f"Exporting {title} as txt...")
            exporter.export_txt(book_id, export_path)
        else:
            console.print(f"Exporting {title}...")
            exporter.export_md(book_id, export_path)

    console.print(f"[bold green]✔ Exported {len(books)} book(s).[/bold green]")
    console.print()
    console.print(f"[dim]Location:[/dim] {export_path.resolve()}")
    console.print()


    # Clear the cache only when we consumed it (prevents surprising behavior)
    if used_cache:
        clear_cache()
        # console.print("Selection cleared.")


@app.command()
def export_all(
    force: Annotated[bool, typer.Option(prompt="Are you sure you want to export all?")],
    txt: Annotated[bool, typer.Option(help="export to txt format")] = False,
    output_dir: Annotated[Optional[str],typer.Option("--output-dir", "-o", help="Directory to export files into")] = None
    ):
    """
    Export highlights for every book found to Markdown (default) or TXT
    """

    sync_db.ensure_local_db()
    
    console.print()
    show_sync_status()
    console.print()


    if force:
        books = parser.get_df_highlights()['VolumeID'].unique().tolist()

        # specify export path
        export_path = resolve_export_path(output_dir)

        # start msg to user
        console.print(f"[bold]Exporting {len(books)} books...[/bold]")

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
        console.print()

    else:
        console.print("[yellow]Operation cancelled.[/yellow]")

@app.command()
def version():
    """Show installed version"""
    console.print("Kobo Notes Exporter v0.1.0")

# --------------------------------------------------------------------------
# MAIN
# --------------------------------------------------------------------------

def main():
    """CLI entrypoint with simple error handling"""
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


