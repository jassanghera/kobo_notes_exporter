import typer
from rich import print

app = typer.Typer(help="This is a really friendly CLI tool :)")

@app.command()
def hello(name: str = typer.Argument(help="Person to greet")):
    """
    say hello to someone
    """
    print(f"[green]hello {name}[/green]")

@app.command()
def goodbye(name: str = typer.Argument(help="Person to greet")):
    """
    say bye bye to someone
    """
    print(f"[red]bye bye {name}[/red]")

if __name__ == "__main__":
    app()


# GOALS:
# command to export specific book's highlights
# command to export all highlights