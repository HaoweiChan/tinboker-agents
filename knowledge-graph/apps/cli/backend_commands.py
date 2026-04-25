from typing import Annotated

import typer
from rich.console import Console


app = typer.Typer()
console = Console()

@app.command()
def list_backend_graphs(
    backend_url: Annotated[str | None, typer.Option("--backend", help="Backend API URL (defaults to BACKEND_URL env var)")] = None,
    backend_token: Annotated[str | None, typer.Option("--token", help="Backend API token (defaults to BACKEND_API_TOKEN env var)")] = None,
):
    from services.backend_client import BackendAPIClient

    console.print("[bold]Listing graphs from backend[/bold]")

    client = BackendAPIClient(base_url=backend_url, api_token=backend_token)

    try:
        graphs = client.list_graphs()
        console.print(f"[green]Found {len(graphs)} graphs[/green]")
        for graph in graphs:
            console.print(f"  - {graph.get('graph_name')} ({graph.get('graph_id')})")
    except Exception as e:
        console.print(f"[red]✗ Error: {str(e)}[/red]")
        raise typer.Exit(1)