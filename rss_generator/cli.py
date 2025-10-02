"""CLI interface for RSS feed generator using Typer."""

import os
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from .common import (
    XSL_FILE,
    check_minio_credentials,
    fetch_page_with_playwright,
    generate_rss_feed,
    upload_to_minio,
)
from .parsers import get_parser
from .sites import get_all_sites, get_site_config, list_sites

app = typer.Typer(
    name="rss-generator",
    help="Generate RSS feeds from websites and upload to MinIO",
    add_completion=True,
)
console = Console()


def process_site(
    site_id: str,
    upload: bool = True,
    bucket_name: str = "rss-feeds"
) -> bool:
    """
    Process a single site: fetch, parse, generate RSS, and optionally upload.

    Args:
        site_id: Site identifier
        upload: Whether to upload to MinIO
        bucket_name: MinIO bucket name

    Returns:
        True if successful, False otherwise
    """
    site_config = get_site_config(site_id)
    if not site_config:
        console.print(f"[red]Site '{site_id}' not found[/red]")
        return False

    output_file = site_config['output_file']

    # Remove existing file
    if os.path.exists(output_file):
        os.remove(output_file)

    # Fetch page
    console.print(f"[cyan]Fetching {site_config['name']}...[/cyan]")
    html_content = fetch_page_with_playwright(
        site_config['url'],
        site_config.get('wait_time', 2000)
    )

    if not html_content:
        console.print(f"[red]Failed to fetch page for {site_id}[/red]")
        return False

    # Parse articles
    parser_func = get_parser(site_config['parser'])
    if not parser_func:
        console.print(f"[red]Parser '{site_config['parser']}' not found[/red]")
        return False

    articles = parser_func(html_content, site_config['url'])

    if not articles:
        console.print(f"[yellow]No articles found for {site_id}[/yellow]")
        return False

    console.print(f"[green]Found {len(articles)} articles[/green]")

    # Generate RSS feed
    if not generate_rss_feed(articles, output_file, site_config):
        console.print(f"[red]Failed to generate RSS feed for {site_id}[/red]")
        return False

    console.print(f"[green]RSS feed generated: {output_file}[/green]")

    # Upload to MinIO if requested
    if upload and check_minio_credentials():
        console.print(f"[cyan]Uploading to MinIO...[/cyan]")

        # Upload the RSS feed
        if not upload_to_minio(output_file, bucket_name):
            console.print(f"[red]Failed to upload RSS feed to MinIO[/red]")
            return False

        # Upload the XSL stylesheet (once per bucket)
        xsl_uploaded_marker = f".{bucket_name}_xsl_uploaded"
        if not os.path.exists(xsl_uploaded_marker):
            if upload_to_minio(str(XSL_FILE), bucket_name, "feed.xsl"):
                # Create marker file to avoid re-uploading XSL
                Path(xsl_uploaded_marker).touch()

        console.print(
            f"[green]Uploaded to https://minio.example.com/{bucket_name}/{output_file}[/green]"
        )
    elif upload:
        console.print("[yellow]MinIO credentials not configured, skipping upload[/yellow]")

    return True


@app.command()
def generate(
    site: Optional[str] = typer.Argument(
        None,
        help="Site ID to generate RSS feed for (or use --all for all sites)"
    ),
    all: bool = typer.Option(
        False,
        "--all",
        "-a",
        help="Generate RSS feeds for all configured sites"
    ),
    no_upload: bool = typer.Option(
        False,
        "--no-upload",
        help="Skip uploading to MinIO (local generation only)"
    ),
    bucket: str = typer.Option(
        "rss-feeds",
        "--bucket",
        "-b",
        help="MinIO bucket name"
    ),
):
    """Generate RSS feed(s) from configured websites."""

    if not all and not site:
        console.print("[red]Error: Provide a site ID or use --all[/red]")
        console.print("Run 'rss-generator list' to see available sites")
        raise typer.Exit(1)

    if all:
        # Process all sites
        sites_to_process = list_sites()
        console.print(f"[bold]Processing {len(sites_to_process)} sites...[/bold]\n")

        success_count = 0
        failed_sites = []

        for site_id in sites_to_process:
            console.print(f"\n[bold blue]{'='*60}[/bold blue]")
            console.print(f"[bold]Processing: {site_id}[/bold]")
            console.print(f"[bold blue]{'='*60}[/bold blue]\n")

            if process_site(site_id, upload=not no_upload, bucket_name=bucket):
                success_count += 1
            else:
                failed_sites.append(site_id)

        # Summary
        console.print(f"\n[bold blue]{'='*60}[/bold blue]")
        console.print(f"[bold]Summary[/bold]")
        console.print(f"[bold blue]{'='*60}[/bold blue]")
        console.print(f"[green]Successful: {success_count}/{len(sites_to_process)}[/green]")

        if failed_sites:
            console.print(f"[red]Failed: {', '.join(failed_sites)}[/red]")
            raise typer.Exit(1)
    else:
        # Process single site
        if not process_site(site, upload=not no_upload, bucket_name=bucket):
            raise typer.Exit(1)


@app.command()
def list():
    """List all available sites."""
    sites = get_all_sites()

    table = Table(title="Available Sites", show_header=True, header_style="bold magenta")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="green")
    table.add_column("URL", style="blue")
    table.add_column("Language", style="yellow")

    for site_id, config in sites.items():
        table.add_row(
            site_id,
            config['name'],
            config['url'],
            config['language']
        )

    console.print(table)


@app.command()
def check():
    """Check configuration and environment."""
    console.print("[bold]RSS Generator Configuration Check[/bold]\n")

    # Check MinIO credentials
    if check_minio_credentials():
        console.print("[green]✓[/green] MinIO credentials configured")
        endpoint = os.getenv('MINIO_ENDPOINT', 'https://minio.example.com')
        console.print(f"  Endpoint: {endpoint}")
    else:
        console.print("[red]✗[/red] MinIO credentials NOT configured")
        console.print("  Set MINIO_ACCESS_KEY and MINIO_SECRET_KEY in .env file")

    # List configured sites
    sites = list_sites()
    console.print(f"\n[green]✓[/green] {len(sites)} sites configured: {', '.join(sites)}")

    # Check .env file
    if os.path.exists('.env'):
        console.print("[green]✓[/green] .env file found")
    else:
        console.print("[yellow]![/yellow] .env file not found")


@app.callback()
def callback():
    """RSS Feed Generator - Generate RSS feeds from websites."""
    pass


def main():
    """Entry point for the CLI."""
    app()
