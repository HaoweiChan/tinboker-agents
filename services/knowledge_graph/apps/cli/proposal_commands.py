from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from services.proposal_service import GraphProposalService

app = typer.Typer()
console = Console()


@app.command()
def create_proposal(
    source: Annotated[str, typer.Option("--source", "-s", help="Data source (gdelt)")] = "gdelt",
    query: Annotated[str, typer.Option("--q", help="News query string")] = "",
    graph_name: Annotated[str, typer.Option("--name", "-n", help="Graph name")] = "",
    days: Annotated[int, typer.Option("--days", "-d", help="Number of days to look back")] = 7,
    pipeline: Annotated[str, typer.Option("--pipeline", "-p", help="Extraction pipeline")] = "rules+openie",
    backend_url: Annotated[str | None, typer.Option("--backend", help="Backend API URL")] = None,
    backend_token: Annotated[str | None, typer.Option("--token", help="Backend API token")] = None,
    description: Annotated[str, typer.Option("--description", help="Graph description")] = "",
    tags: Annotated[str, typer.Option("--tags", help="Comma-separated tags")] = "",
    save: Annotated[bool, typer.Option("--save", help="Save proposal to backend")] = False,
):
    console.print(f"[bold]Creating proposal from news: {graph_name}[/bold]")

    if not graph_name:
        graph_name = f"News Graph: {query[:50]}"

    service = GraphProposalService(backend_url=backend_url, backend_token=backend_token)
    tag_list = [t.strip() for t in tags.split(",")] if tags else None

    try:
        result = service.create_proposal_from_news(
            source=source,
            query=query,
            graph_name=graph_name,
            days=days,
            pipeline=pipeline,
            description=description,
            tags=tag_list,
        )

        if result["status"] == "success":
            proposal = result["proposal"]
            console.print(f"[green]✓ Proposal created![/green]")
            console.print(f"  Proposal ID: {proposal['proposal_id']}")
            console.print(f"  Status: {proposal['status']}")
            console.print(f"  Stock IDs: {len(proposal['nodes'])}")
            console.print(f"  Edges: {len(proposal['edges'])}")
            console.print(f"  Entities extracted: {proposal['metadata']['entities_extracted']}")
            console.print(f"  Documents processed: {proposal['metadata']['docs_processed']}")

            if save:
                saved = service.save_proposal(proposal)
                console.print(f"[green]✓ Proposal saved to backend (Graph ID: {saved.get('graph_id')})[/green]")
            else:
                console.print("[yellow]⚠ Proposal not saved. Use --save to save to backend.[/yellow]")
        else:
            console.print(f"[yellow]⚠ {result['message']}[/yellow]")

    except Exception as e:
        console.print(f"[red]✗ Error: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command()
def list_proposals(
    backend_url: Annotated[str | None, typer.Option("--backend", help="Backend API URL")] = None,
    backend_token: Annotated[str | None, typer.Option("--token", help="Backend API token")] = None,
):
    from services.backend_client import BackendAPIClient

    console.print("[bold]Listing proposal graphs[/bold]")

    client = BackendAPIClient(base_url=backend_url, api_token=backend_token)

    try:
        graphs = client.list_graphs()
        proposals = [g for g in graphs if "[PROPOSAL]" in g.get("graph_name", "")]

        if not proposals:
            console.print("[yellow]No proposals found[/yellow]")
            return

        table = Table(title="Graph Proposals")
        table.add_column("Graph ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Created", style="yellow")
        table.add_column("Status", style="magenta")

        for prop in proposals:
            table.add_row(
                prop.get("graph_id", "")[:8],
                prop.get("graph_name", "").replace("[PROPOSAL] ", ""),
                prop.get("created_at", "")[:10] if prop.get("created_at") else "",
                "pending",
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]✗ Error: {str(e)}[/red]")
        raise typer.Exit(1)

