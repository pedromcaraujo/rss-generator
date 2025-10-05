"""CLI interface for RSS feed generator using Typer."""

import os
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from .common import (
    XSL_FILE,
    check_minio_credentials,
    check_playwright_browsers,
    fetch_page_with_playwright,
    generate_rss_feed,
    upload_to_minio,
)
from .parsers import get_parser, get_content_extractor, get_metadata_extractor
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
    bucket_name: Optional[str] = None,
    xsl_url: Optional[str] = None,
) -> bool:
    """
    Process a single site: fetch, parse, generate RSS, and optionally upload.

    Args:
        site_id: Site identifier
        upload: Whether to upload to MinIO
        bucket_name: MinIO bucket name
        xsl_url: Custom XSL stylesheet URL

    Returns:
        True if successful, False otherwise
    """
    site_config = get_site_config(site_id)
    if not site_config:
        console.print(f"[red]Site '{site_id}' not found[/red]")
        return False

    # Get bucket name from parameter or environment
    if bucket_name is None:
        bucket_name = os.getenv("S3_BUCKET", "rss-feeds")

    output_file = site_config["output_file"]

    # Remove existing file
    if os.path.exists(output_file):
        os.remove(output_file)

    # Fetch page
    console.print(f"[cyan]Fetching {site_config['name']}...[/cyan]")
    html_content = fetch_page_with_playwright(
        site_config["url"], site_config.get("wait_time", 2000)
    )

    if not html_content:
        console.print(f"[red]Failed to fetch page for {site_id}[/red]")
        return False

    # Parse articles
    parser_func = get_parser(site_config["parser"])
    if not parser_func:
        console.print(f"[red]Parser '{site_config['parser']}' not found[/red]")
        return False

    articles = parser_func(html_content, site_config["url"])

    if not articles:
        console.print(f"[yellow]No articles found for {site_id}[/yellow]")
        return False

    console.print(f"[green]Found {len(articles)} articles[/green]")

    # Limit articles if configured
    max_articles = site_config.get("max_articles")
    if max_articles and len(articles) > max_articles:
        console.print(f"[cyan]Limiting to {max_articles} most recent articles[/cyan]")
        articles = articles[:max_articles]

    # Fetch full content and metadata for each article
    content_extractor = get_content_extractor(site_config["parser"])
    metadata_extractor = get_metadata_extractor(site_config["parser"])

    if content_extractor or metadata_extractor:
        console.print("[cyan]Fetching full content and metadata for articles...[/cyan]")
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Processing articles...", total=len(articles))

            for article in articles:
                if article.get("link"):
                    article_html = fetch_page_with_playwright(
                        article["link"], site_config.get("wait_time", 2000)
                    )
                    if article_html:
                        # Extract content
                        if content_extractor:
                            content = content_extractor(article_html)
                            if content:
                                article["content"] = content

                        # Extract metadata (author, image)
                        if metadata_extractor:
                            metadata = metadata_extractor(article_html)
                            if metadata.get("author"):
                                article["author"] = metadata["author"]
                            if metadata.get("image"):
                                article["image"] = metadata["image"]

                progress.update(task, advance=1)

    # Generate RSS feed
    if not generate_rss_feed(articles, output_file, site_config, bucket_name, xsl_url):
        console.print(f"[red]Failed to generate RSS feed for {site_id}[/red]")
        return False

    console.print(f"[green]RSS feed generated: {output_file}[/green]")

    # Upload to MinIO if requested
    if upload and check_minio_credentials():
        console.print("[cyan]Uploading to MinIO...[/cyan]")

        # Upload the RSS feed
        if not upload_to_minio(output_file, bucket_name):
            console.print("[red]Failed to upload RSS feed to MinIO[/red]")
            return False

        # Upload the XSL stylesheet (once per bucket)
        xsl_uploaded_marker = f".{bucket_name}_xsl_uploaded"
        if not os.path.exists(xsl_uploaded_marker):
            if upload_to_minio(str(XSL_FILE), bucket_name, "feed.xsl"):
                # Create marker file to avoid re-uploading XSL
                Path(xsl_uploaded_marker).touch()

        # Construct public URL from environment or endpoint
        s3_public_url = (
            os.getenv("S3_PUBLIC_URL")
            or os.getenv("S3_ENDPOINT")
            or os.getenv("MINIO_ENDPOINT")
        )

        if s3_public_url:
            public_base = s3_public_url.replace("https://", "").replace("http://", "")
            console.print(
                f"[green]Uploaded to https://{public_base}/{bucket_name}/{output_file}[/green]"
            )
        else:
            console.print(
                f"[green]Uploaded to bucket: {bucket_name}/{output_file}[/green]"
            )
    elif upload:
        console.print("[yellow]S3 credentials not configured, skipping upload[/yellow]")

    return True


@app.command()
def generate(
    ctx: typer.Context,
    site: Optional[str] = typer.Argument(
        None, help="Site ID to generate RSS feed for (or use --all for all sites)"
    ),
    all: bool = typer.Option(
        False, "--all", "-a", help="Generate RSS feeds for all configured sites"
    ),
    no_upload: bool = typer.Option(
        False, "--no-upload", help="Skip uploading to MinIO (local generation only)"
    ),
    bucket: Optional[str] = typer.Option(
        None,
        "--bucket",
        "-b",
        help="S3 bucket name (defaults to S3_BUCKET env var or 'rss-feeds')",
    ),
    xsl_url: Optional[str] = typer.Option(
        None,
        "--xsl-url",
        "-x",
        help="Custom XSL stylesheet URL for browser-friendly RSS display",
    ),
):
    """Generate RSS feed(s) from configured websites."""

    if not all and not site:
        # Show help
        console.print(ctx.get_help())
        console.print("\n")

        # Show available sites
        sites = get_all_sites()
        table = Table(
            title="Available Sites", show_header=True, header_style="bold magenta"
        )
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Name", style="green")
        table.add_column("URL", style="blue")
        table.add_column("Language", style="yellow")

        for site_id, config in sites.items():
            table.add_row(site_id, config["name"], config["url"], config["language"])

        console.print(table)
        raise typer.Exit(0)

    if all:
        # Process all sites
        sites_to_process = list_sites()
        console.print(f"[bold]Processing {len(sites_to_process)} sites...[/bold]\n")

        success_count = 0
        failed_sites = []

        for site_id in sites_to_process:
            console.print(f"\n[bold blue]{'=' * 60}[/bold blue]")
            console.print(f"[bold]Processing: {site_id}[/bold]")
            console.print(f"[bold blue]{'=' * 60}[/bold blue]\n")

            if process_site(
                site_id, upload=not no_upload, bucket_name=bucket, xsl_url=xsl_url
            ):
                success_count += 1
            else:
                failed_sites.append(site_id)

        # Summary
        console.print(f"\n[bold blue]{'=' * 60}[/bold blue]")
        console.print("[bold]Summary[/bold]")
        console.print(f"[bold blue]{'=' * 60}[/bold blue]")
        console.print(
            f"[green]Successful: {success_count}/{len(sites_to_process)}[/green]"
        )

        if failed_sites:
            console.print(f"[red]Failed: {', '.join(failed_sites)}[/red]")
            raise typer.Exit(1)
    else:
        # Process single site
        if not process_site(
            site, upload=not no_upload, bucket_name=bucket, xsl_url=xsl_url
        ):
            raise typer.Exit(1)


@app.command()
def list():
    """List all available sites."""
    sites = get_all_sites()

    table = Table(
        title="Available Sites", show_header=True, header_style="bold magenta"
    )
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="green")
    table.add_column("URL", style="blue")
    table.add_column("Language", style="yellow")

    for site_id, config in sites.items():
        table.add_row(site_id, config["name"], config["url"], config["language"])

    console.print(table)


@app.command()
def upload_xsl(
    bucket: Optional[str] = typer.Option(
        None,
        "--bucket",
        "-b",
        help="S3 bucket name (defaults to S3_BUCKET env var or 'rss-feeds')",
    ),
):
    """Generate and upload XSL stylesheet, returning the public URL."""
    if not check_minio_credentials():
        console.print("[red]Error: S3 credentials not configured[/red]")
        console.print("Set S3_ACCESS_KEY and S3_SECRET_KEY in .env file")
        raise typer.Exit(1)

    # Get bucket name from parameter or environment
    if bucket is None:
        bucket = os.getenv("S3_BUCKET", "rss-feeds")

    console.print(f"[cyan]Uploading XSL stylesheet to bucket '{bucket}'...[/cyan]")

    # Upload the XSL stylesheet
    if not upload_to_minio(str(XSL_FILE), bucket, "feed.xsl"):
        console.print("[red]Failed to upload XSL stylesheet[/red]")
        raise typer.Exit(1)

    # Construct and display public URL
    s3_public_url = (
        os.getenv("S3_PUBLIC_URL")
        or os.getenv("S3_ENDPOINT")
        or os.getenv("MINIO_ENDPOINT")
    )

    if s3_public_url:
        public_base = s3_public_url.replace("https://", "").replace("http://", "")
        xsl_url = f"https://{public_base}/{bucket}/feed.xsl"
        console.print("[green]✓[/green] XSL stylesheet uploaded successfully")
        console.print(f"\n[bold]XSL URL:[/bold] {xsl_url}")
        console.print("\nUse this URL with the --xsl-url flag:")
        console.print(f"  rss-generator generate <site> --xsl-url {xsl_url}")
    else:
        console.print(f"[green]✓[/green] Uploaded to {bucket}/feed.xsl")
        console.print(
            "[yellow]Warning: S3_PUBLIC_URL not set, cannot display full URL[/yellow]"
        )


@app.command()
def setup():
    """Install Playwright browsers (required for web scraping)."""
    console.print("[bold]Setting up RSS Generator...[/bold]\n")
    console.print("[cyan]Installing Playwright browsers...[/cyan]")

    import subprocess
    import sys

    try:
        # Try to run playwright install chromium
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            console.print("[green]✓[/green] Playwright browsers installed successfully!")
            console.print("\n[bold]Setup complete![/bold] You can now use rss-generator.")
            console.print("\nTry: [cyan]rss-generator list[/cyan] to see available sites")
        else:
            console.print("[red]✗[/red] Failed to install Playwright browsers")
            console.print(f"\n{result.stderr}")
            console.print("\n[yellow]Please try manually:[/yellow]")
            console.print("  [cyan]uv run playwright install chromium[/cyan]")
            console.print("  [cyan]python -m playwright install chromium[/cyan]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]Error during setup: {e}[/red]")
        console.print("\n[yellow]Please try manually:[/yellow]")
        console.print("  [cyan]uv run playwright install chromium[/cyan]")
        console.print("  [cyan]python -m playwright install chromium[/cyan]")
        raise typer.Exit(1)


@app.command()
def check():
    """Check configuration and environment."""
    console.print("[bold]RSS Generator Configuration Check[/bold]\n")

    # Check Playwright browsers
    if check_playwright_browsers():
        console.print("[green]✓[/green] Playwright browsers installed")
    else:
        console.print("[red]✗[/red] Playwright browsers NOT installed")
        console.print("  Run: [cyan]rss-generator setup[/cyan] to install")

    # Check S3 credentials
    console.print()
    if check_minio_credentials():
        console.print("[green]✓[/green] S3 credentials configured")
        endpoint = (
            os.getenv("S3_ENDPOINT")
            or os.getenv("MINIO_ENDPOINT")
            or "Not set (AWS S3)"
        )
        bucket = os.getenv("S3_BUCKET", "rss-feeds")
        region = (
            os.getenv("S3_REGION")
            or os.getenv("AWS_DEFAULT_REGION")
            or "us-east-1 (default)"
        )
        public_url = os.getenv("S3_PUBLIC_URL") or "Not set"

        console.print(f"  Endpoint: {endpoint}")
        console.print(f"  Region: {region}")
        console.print(f"  Bucket: {bucket}")
        console.print(f"  Public URL: {public_url}")
    else:
        console.print("[red]✗[/red] S3 credentials NOT configured")
        console.print("  Set S3_ACCESS_KEY and S3_SECRET_KEY in .env file")
        console.print(
            "  Or use MINIO_ACCESS_KEY and MINIO_SECRET_KEY for backward compatibility"
        )

    # List configured sites
    sites = list_sites()
    console.print(
        f"\n[green]✓[/green] {len(sites)} sites configured: {', '.join(sites)}"
    )

    # Check .env file
    if os.path.exists(".env"):
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
