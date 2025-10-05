"""Common utilities for RSS feed generation."""

import os
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from typing import Optional

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright
from rich.console import Console

# Load environment variables
load_dotenv()

console = Console()

# Path to XSL stylesheet
XSL_FILE = Path(__file__).parent / "feed.xsl"


def check_playwright_browsers() -> bool:
    """
    Check if Playwright browsers are installed.

    Returns:
        True if browsers are installed, False otherwise
    """
    try:
        with sync_playwright() as p:
            # Try to launch browser - if it fails, browsers aren't installed
            browser = p.chromium.launch(headless=True)
            browser.close()
            return True
    except Exception as e:
        error_msg = str(e)
        if "Executable doesn't exist" in error_msg or "browsers" in error_msg.lower():
            return False
        # For other errors, assume browsers are installed but something else is wrong
        return True

# Setup Jinja2 environment
TEMPLATE_DIR = Path(__file__).parent / "templates"
jinja_env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))


def fetch_page_with_playwright(url: str, wait_time: int = 2000) -> Optional[str]:
    """
    Fetch a page using Playwright for JavaScript rendering.

    Args:
        url: The URL to fetch
        wait_time: Time to wait for page load in milliseconds

    Returns:
        HTML content as string, or None if error
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="networkidle")
            page.wait_for_timeout(wait_time)
            html_content = page.content()
            browser.close()
            return html_content
    except Exception as e:
        error_msg = str(e)

        # Check if it's a missing browser error
        if "Executable doesn't exist" in error_msg or "browsers" in error_msg.lower():
            console.print("[red]Error: Playwright browsers are not installed![/red]\n")
            console.print("[yellow]Please run ONE of the following commands to install browsers:[/yellow]")
            console.print("  [cyan]rss-generator setup[/cyan]")
            console.print("  [cyan]uv run playwright install chromium[/cyan]")
            console.print("  [cyan]python -m playwright install chromium[/cyan]")
            console.print("  [cyan]playwright install chromium[/cyan]")
            console.print("\n[dim]This is a one-time setup required for web scraping.[/dim]")
        else:
            console.print(f"[red]Error fetching {url}: {e}[/red]")

        return None


def generate_rss_feed(
    articles: list[dict],
    output_file: str,
    site_config: dict,
    bucket_name: Optional[str] = None,
    xsl_url: Optional[str] = None,
) -> bool:
    """
    Generate an RSS feed from articles using Jinja2 template.

    Args:
        articles: List of article dictionaries with title, link, description, date, etc.
        output_file: Path to save the RSS feed
        site_config: Site configuration dictionary
        bucket_name: S3 bucket name for default XSL URL
        xsl_url: Custom XSL stylesheet URL (overrides default)

    Returns:
        True if successful, False otherwise
    """
    try:
        # Determine XSL URL
        final_xsl_url = None
        if xsl_url:
            final_xsl_url = xsl_url
        elif os.getenv("XSL_URL"):
            final_xsl_url = os.getenv("XSL_URL")
        elif bucket_name or os.getenv("S3_BUCKET"):
            if bucket_name is None:
                bucket_name = os.getenv("S3_BUCKET", "rss-feeds")
            s3_endpoint = os.getenv("S3_ENDPOINT") or os.getenv("MINIO_ENDPOINT")
            s3_public_url = os.getenv("S3_PUBLIC_URL") or s3_endpoint
            if s3_public_url:
                public_base = s3_public_url.replace("https://", "").replace(
                    "http://", ""
                )
                final_xsl_url = f"https://{public_base}/{bucket_name}/feed.xsl"

        # Prepare channel data
        channel = {
            "title": site_config["name"],
            "link": site_config["url"],
            "description": site_config.get(
                "description", f"Latest posts from {site_config['name']}"
            ),
            "language": site_config.get("language", "en"),
            "author": {
                "name": site_config["name"],
                "email": site_config.get("email", "noreply@example.com"),
            },
            "last_build_date": format_datetime(datetime.now(timezone.utc)),
        }

        # Prepare items data
        items = []
        for article in articles:
            item = {
                "title": article["title"],
                "link": article["link"],
                "description": article.get("description", article["title"]),
            }

            # Add author if available
            if article.get("author"):
                item["author"] = {
                    "name": article["author"],
                    "email": "noreply@example.com",
                }

            # Add full content if available
            if article.get("content"):
                item["content"] = article["content"]

            # Add featured image
            if article.get("image"):
                item["image"] = article["image"]

            # Add category
            if article.get("category"):
                item["category"] = article["category"]

            # Parse and format date
            if article.get("date"):
                try:
                    if isinstance(article["date"], str):
                        date_str = article["date"].strip()
                        date_formats = [
                            "%Y-%m-%d",
                            "%Y-%m-%dT%H:%M:%S",
                            "%B %d, %Y",
                            "%b %d, %Y",
                        ]
                        for fmt in date_formats:
                            try:
                                dt = datetime.strptime(date_str, fmt)
                                dt = dt.replace(tzinfo=timezone.utc)
                                item["pub_date"] = format_datetime(dt)
                                break
                            except (ValueError, AttributeError):
                                continue

                        if "pub_date" not in item:
                            console.print(
                                f"[yellow]Could not parse date '{date_str}' for article '{article.get('title')}'[/yellow]"
                            )
                except Exception as e:
                    console.print(f"[yellow]Error parsing date: {e}[/yellow]")

            items.append(item)

        # Render RSS feed from template
        template = jinja_env.get_template("rss_feed.xml")
        rss_content = template.render(
            xsl_url=final_xsl_url, channel=channel, items=items
        )

        # Write to file
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(rss_content)

        return True
    except Exception as e:
        console.print(f"[red]Error generating RSS feed: {e}[/red]")
        import traceback

        traceback.print_exc()
        return False


def upload_to_minio(
    file_path: str, bucket_name: str, object_name: Optional[str] = None
) -> bool:
    """
    Upload a file to S3-compatible bucket (MinIO, AWS S3, etc.).

    Args:
        file_path: Path to file to upload
        bucket_name: Name of the bucket
        object_name: S3 object name. If not specified, file_path basename is used

    Returns:
        True if file was uploaded, else False
    """
    # Get credentials from environment variables (support both S3 and MINIO prefixes)
    access_key = os.getenv("S3_ACCESS_KEY", os.getenv("MINIO_ACCESS_KEY"))
    secret_key = os.getenv("S3_SECRET_KEY", os.getenv("MINIO_SECRET_KEY"))
    endpoint = os.getenv("S3_ENDPOINT", os.getenv("MINIO_ENDPOINT"))

    if not access_key or not secret_key:
        console.print("[yellow]S3 credentials not found in environment[/yellow]")
        return False

    # If S3 object_name was not specified, use file_path basename
    if object_name is None:
        object_name = os.path.basename(file_path)

    # Get region (required for AWS S3, optional for MinIO)
    region = os.getenv("S3_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1"

    # Create S3 client config
    s3_config = {
        "aws_access_key_id": access_key,
        "aws_secret_access_key": secret_key,
        "region_name": region,
    }

    # Only set endpoint_url if provided (for MinIO/S3-compatible services)
    # AWS S3 doesn't need endpoint_url
    if endpoint:
        # Ensure endpoint has protocol
        if not endpoint.startswith("http"):
            endpoint = f"https://{endpoint}"
        s3_config["endpoint_url"] = endpoint

    # Create S3 client
    s3_client = boto3.client("s3", **s3_config)

    try:
        s3_client.upload_file(
            file_path,
            bucket_name,
            object_name,
            ExtraArgs={"ContentType": "application/rss+xml"},
        )
        return True
    except ClientError as e:
        console.print(f"[red]Error uploading to S3: {e}[/red]")
        return False


def check_minio_credentials() -> bool:
    """Check if S3 credentials are configured."""
    access_key = os.getenv("S3_ACCESS_KEY", os.getenv("MINIO_ACCESS_KEY"))
    secret_key = os.getenv("S3_SECRET_KEY", os.getenv("MINIO_SECRET_KEY"))
    return bool(access_key and secret_key)
