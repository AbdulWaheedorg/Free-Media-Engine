"""Free Media Engine (FME) — Unified CLI Client.

Allows command-line dispatch, real-time status streaming, asset downloads,
and API key administration.
"""
from __future__ import annotations

import asyncio
import os
import sys
import time
import httpx
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from fme_engine.cli.keys import app as keys_app
from fme_engine.core.config import settings

app = typer.Typer(
    name="fme",
    help="Free Media Engine (FME) — AI Video & Photo Generation CLI Client",
    add_completion=False,
)
app.add_typer(keys_app, name="keys")
console = Console()


def get_base_url() -> str:
    url = os.getenv("FME_API_URL")
    if url:
        return url.rstrip("/")
    if settings.DOMAIN_NAME:
        return f"https://{settings.DOMAIN_NAME}"
    return f"http://{settings.DAEMON_HOST}:{settings.DAEMON_PORT}"


def get_api_key() -> str:
    key = os.getenv("FME_API_KEY") or settings.FME_MASTER_KEY
    return key.strip() if key else ""


@app.command("generate")
def generate(
    prompt: str = typer.Argument(..., help="Prompt describing the scene, motion, or character"),
    mode: str = typer.Option("t2v", "--mode", "-m", help="Modality: t2v, i2v, t2i, references, upscale"),
    model: str = typer.Option("omni_flash", "--model", help="Engine model: omni_flash or veo"),
    aspect: str = typer.Option("16:9", "--aspect", "-a", help="Aspect ratio: 16:9, 9:16, 1:1"),
    image: str = typer.Option(None, "--image", "-i", help="First-frame image URL for i2v"),
    last_frame: str = typer.Option(None, "--last-frame", help="End-frame image URL for interpolation"),
    duration: int = typer.Option(5, "--duration", "-d", help="Duration in seconds (5-10)"),
    wait: bool = typer.Option(True, "--wait/--no-wait", help="Wait and stream progress until completion"),
    output: str = typer.Option(None, "--output", "-o", help="Target output file path to save asset"),
):
    """Submit a generation job and optionally wait for completion."""
    base_url = get_base_url()
    api_key = get_api_key()

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "prompt": prompt,
        "mode": mode,
        "model": model,
        "aspect_ratio": aspect,
        "seed_image_url": image,
        "last_frame_image_url": last_frame,
        "duration_seconds": duration,
    }

    console.print(f"[bold cyan]Submitting generation job to {base_url}...[/bold cyan]")
    try:
        with httpx.Client(timeout=30.0, verify=False) as client:
            resp = client.post(f"{base_url}/api/v1/generate", json=payload, headers=headers)
            if resp.status_code != 202:
                console.print(f"[bold red][ERROR] API returned {resp.status_code}: {resp.text}[/bold red]")
                raise typer.Exit(code=1)

            data = resp.json()
            job_id = data["job_id"]
            pos = data.get("queue_position", 1)
            console.print(f"[bold green][OK] Job submitted successfully![/bold green]")
            console.print(f"  [bold]Job ID:[/bold]         {job_id}")
            console.print(f"  [bold]Queue Position:[/bold] {pos}")

    except Exception as e:
        console.print(f"[bold red][ERROR] Failed to submit job: {e}[/bold red]")
        raise typer.Exit(code=1)

    if not wait:
        console.print(f"[dim]Use 'fme status {job_id}' to check progress.[/dim]")
        return

    # Wait loop with progress bar
    ext = ".png" if mode == "t2i" else ".mp4"
    out_file = output or f"{job_id}{ext}"

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress_bar:
        task = progress_bar.add_task(f"[yellow]Processing {mode.upper()}...[/yellow]", total=100)

        with httpx.Client(timeout=30.0, verify=False) as client:
            while True:
                time.sleep(3.0)
                try:
                    stat_resp = client.get(f"{base_url}/api/v1/jobs/{job_id}", headers=headers)
                    if stat_resp.status_code != 200:
                        continue
                    stat_data = stat_resp.json()
                    current_status = stat_data.get("status")
                    current_prog = stat_data.get("progress", 0)

                    progress_bar.update(task, completed=current_prog, description=f"[{current_status}] {prompt[:30]}...")

                    if current_status == "COMPLETED":
                        progress_bar.update(task, completed=100, description="[bold green]COMPLETED![/bold green]")
                        break
                    elif current_status in ("FAILED", "CANCELLED", "STALLED"):
                        console.print(f"\n[bold red][ERROR] Job {current_status}: {stat_data.get('error_message')}[/bold red]")
                        raise typer.Exit(code=1)

                except Exception:
                    pass

    # Download asset
    console.print(f"[cyan]Downloading asset to {out_file}...[/cyan]")
    download_url = f"{base_url}/api/v1/assets/{job_id}"
    try:
        with httpx.Client(timeout=120.0, verify=False) as client:
            dl_resp = client.get(download_url, headers=headers)
            if dl_resp.status_code == 200:
                with open(out_file, "wb") as f:
                    f.write(dl_resp.content)
                console.print(f"[bold green][OK] Asset saved to {out_file}[/bold green]\n")
            else:
                console.print(f"[bold red]Download failed ({dl_resp.status_code}): {dl_resp.text}[/bold red]")
    except Exception as e:
        console.print(f"[bold red]Download error: {e}[/bold red]")


@app.command("status")
def status_cmd(
    job_id: str = typer.Argument(..., help="UUID of the generation job"),
):
    """Query progress and download URL for a specific job."""
    base_url = get_base_url()
    headers = {}
    key = get_api_key()
    if key:
        headers["Authorization"] = f"Bearer {key}"

    try:
        with httpx.Client(timeout=15.0, verify=False) as client:
            resp = client.get(f"{base_url}/api/v1/jobs/{job_id}", headers=headers)
            if resp.status_code == 404:
                console.print(f"[bold red]Job '{job_id}' not found.[/bold red]")
                raise typer.Exit(code=1)
            elif resp.status_code != 200:
                console.print(f"[bold red]Error ({resp.status_code}): {resp.text}[/bold red]")
                raise typer.Exit(code=1)

            data = resp.json()
            console.print("\n[bold magenta]Free Media Engine — Job Status[/bold magenta]")
            console.print(f"  [bold]Job ID:[/bold]         {data['job_id']}")
            console.print(f"  [bold]Status:[/bold]         {data['status']}")
            console.print(f"  [bold]Progress:[/bold]       {data['progress']}%")
            console.print(f"  [bold]Mode:[/bold]           {data['mode']}")
            console.print(f"  [bold]Prompt:[/bold]         {data['prompt']}")
            if data.get("download_url"):
                console.print(f"  [bold]Download URL:[/bold]   {base_url}{data['download_url']}")
            if data.get("error_message"):
                console.print(f"  [bold red]Error:[/bold red]          {data['error_message']}")
            console.print("")

    except Exception as e:
        console.print(f"[bold red]Failed to get job status: {e}[/bold red]")


@app.command("download")
def download_cmd(
    job_id: str = typer.Argument(..., help="UUID of the completed job"),
    output: str = typer.Option(None, "--output", "-o", help="Target filename on disk"),
):
    """Download a completed media asset to the local machine."""
    base_url = get_base_url()
    headers = {}
    key = get_api_key()
    if key:
        headers["Authorization"] = f"Bearer {key}"

    out_file = output or f"{job_id}.mp4"
    console.print(f"[cyan]Downloading asset for job {job_id}...[/cyan]")
    try:
        with httpx.Client(timeout=120.0, verify=False) as client:
            resp = client.get(f"{base_url}/api/v1/assets/{job_id}", headers=headers)
            if resp.status_code == 200:
                with open(out_file, "wb") as f:
                    f.write(resp.content)
                console.print(f"[bold green][OK] Saved to {out_file}[/bold green]")
            else:
                console.print(f"[bold red]Failed to download ({resp.status_code}): {resp.text}[/bold red]")
    except Exception as e:
        console.print(f"[bold red]Download error: {e}[/bold red]")


@app.command("health")
def health_cmd():
    """Check engine status, extension link, and queue depth."""
    base_url = get_base_url()
    try:
        with httpx.Client(timeout=10.0, verify=False) as client:
            resp = client.get(f"{base_url}/api/v1/health")
            if resp.status_code == 200:
                data = resp.json()
                console.print("\n[bold green]Free Media Engine Status: HEALTHY[/bold green]")
                console.print(f"  [bold]Version:[/bold]             {data['version']}")
                console.print(f"  [bold]Extension Linked:[/bold]    {'[green]YES[/green]' if data['extension_connected'] else '[red]NO[/red]'}")
                console.print(f"  [bold]Active Project:[/bold]      {data['active_project_id']}")
                console.print(f"  [bold]Queue Depth:[/bold]         {data['queue_depth']}")
                console.print(f"  [bold]Uptime:[/bold]              {data['uptime_seconds']}s\n")
            else:
                console.print(f"[bold red]Unhealthy response ({resp.status_code}): {resp.text}[/bold red]")
    except Exception as e:
        console.print(f"[bold red]Failed to reach engine at {base_url}: {e}[/bold red]")


if __name__ == "__main__":
    app()
