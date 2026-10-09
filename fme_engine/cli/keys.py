"""Free Media Engine (FME) — Key Management CLI Commands."""
from __future__ import annotations

import asyncio
import typer
from rich.console import Console
from rich.table import Table

from fme_engine.core.auth import generate_api_key
from fme_engine.db.database import init_db, close_db
from fme_engine.db.crud import create_api_key, list_api_keys, revoke_api_key

app = typer.Typer(help="Manage API keys with zero-downtime rotation and revocation")
console = Console()


@app.command("create")
def create_key(
    name: str = typer.Option(..., "--name", "-n", help="Descriptive label for this key (e.g., 'mobile-client')"),
):
    """Generate a new high-entropy API key and record its SHA-256 hash."""
    async def _run():
        await init_db()
        raw_key, key_hash, key_prefix = generate_api_key()
        record = await create_api_key(name=name, key_hash=key_hash, key_prefix=key_prefix)
        await close_db()

        console.print("\n[bold green][OK] API Key Created Successfully![/bold green]")
        console.print(f"  [bold]ID:[/bold]          {record['id']}")
        console.print(f"  [bold]Name:[/bold]        {record['name']}")
        console.print(f"  [bold]Prefix:[/bold]      {record['key_prefix']}...")
        console.print(f"  [bold]Status:[/bold]      {record['status']}")
        console.print("\n[bold yellow]Save this key now. It cannot be recovered later:[/bold yellow]")
        console.print(f"[bold cyan]{raw_key}[/bold cyan]\n")

    asyncio.run(_run())


@app.command("list")
def list_keys():
    """List all active and revoked API keys."""
    async def _run():
        await init_db()
        keys = await list_api_keys()
        await close_db()

        if not keys:
            console.print("[yellow]No API keys found.[/yellow]")
            return

        table = Table(title="Free Media Engine — API Keys", header_style="bold magenta")
        table.add_column("ID", justify="right", style="cyan")
        table.add_column("Name", style="white")
        table.add_column("Key Prefix", style="dim")
        table.add_column("Status", justify="center")
        table.add_column("Created At", style="dim")
        table.add_column("Last Used At", style="dim")

        for k in keys:
            status_style = "[green]active[/green]" if k["status"] == "active" else "[red]revoked[/red]"
            table.add_row(
                str(k["id"]),
                k["name"],
                f"{k['key_prefix']}...",
                status_style,
                k["created_at"],
                k["last_used_at"] or "Never",
            )

        console.print(table)

    asyncio.run(_run())


@app.command("revoke")
def revoke_key(
    identifier: str = typer.Argument(..., help="Key ID, Prefix, or Name to immediately revoke"),
):
    """Instantly revoke an API key with zero downtime."""
    async def _run():
        await init_db()
        success = await revoke_api_key(identifier)
        await close_db()

        if success:
            console.print(f"[bold green][OK] Key '{identifier}' has been instantly revoked.[/bold green]")
            console.print("[dim]Subsequent requests using this key will immediately return 401 Unauthorized.[/dim]")
        else:
            console.print(f"[bold red][ERROR] No matching key found for identifier: '{identifier}'.[/bold red]")

    asyncio.run(_run())
