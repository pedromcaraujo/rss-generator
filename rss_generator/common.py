"""Common utilities for RSS feed generation."""

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from feedgen.feed import FeedGenerator
from playwright.sync_api import sync_playwright
from rich.console import Console

# Load environment variables
load_dotenv()

console = Console()

# Path to XSL stylesheet
XSL_FILE = Path(__file__).parent / "feed.xsl"


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
            page.goto(url, wait_until='networkidle')
            page.wait_for_timeout(wait_time)
            html_content = page.content()
            browser.close()
            return html_content
    except Exception as e:
        console.print(f"[red]Error fetching {url}: {e}[/red]", file=sys.stderr)
        return None


def generate_rss_feed(
    articles: list[dict],
    output_file: str,
    site_config: dict
) -> bool:
    """
    Generate an RSS feed from articles.

    Args:
        articles: List of article dictionaries with title, link, description, date, etc.
        output_file: Path to save the RSS feed
        site_config: Site configuration dictionary

    Returns:
        True if successful, False otherwise
    """
    try:
        fg = FeedGenerator()
        fg.id(site_config['url'])
        fg.title(site_config['name'])
        fg.author({'name': site_config['name'], 'email': site_config.get('email', 'noreply@example.com')})
        fg.link(href=site_config['url'], rel='alternate')
        fg.description(site_config.get('description', f"Latest posts from {site_config['name']}"))
        fg.language(site_config.get('language', 'en'))

        for article in articles:
            fe = fg.add_entry()
            fe.id(article['link'])
            fe.title(article['title'])
            fe.link(href=article['link'])
            fe.description(article.get('description', article['title']))

            # Add category if available
            if article.get('category'):
                fe.category(term=article['category'])

            # Handle date parsing
            if article.get('date'):
                try:
                    if isinstance(article['date'], str):
                        # Try to parse common date formats
                        for fmt in ['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%B %d, %Y', '%b %d, %Y']:
                            try:
                                dt = datetime.strptime(article['date'], fmt)
                                fe.published(dt)
                                break
                            except ValueError:
                                continue
                except Exception:
                    pass

        # Write RSS feed
        fg.rss_file(output_file)

        # Add XSL stylesheet reference to make it browser-friendly
        _add_xsl_stylesheet(output_file)

        return True
    except Exception as e:
        console.print(f"[red]Error generating RSS feed: {e}[/red]", file=sys.stderr)
        return False


def _add_xsl_stylesheet(xml_file: str):
    """
    Add XSL stylesheet reference to XML file for browser display.

    Args:
        xml_file: Path to XML file
    """
    try:
        with open(xml_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Add XSL stylesheet processing instruction after XML declaration
        xsl_pi = '<?xml-stylesheet type="text/xsl" href="feed.xsl"?>\n'

        if '<?xml-stylesheet' not in content:
            # Insert after XML declaration
            content = content.replace(
                '<?xml version=\'1.0\' encoding=\'UTF-8\'?>\n',
                f'<?xml version=\'1.0\' encoding=\'UTF-8\'?>\n{xsl_pi}',
                1
            )

            with open(xml_file, 'w', encoding='utf-8') as f:
                f.write(content)
    except Exception as e:
        console.print(f"[yellow]Warning: Could not add XSL stylesheet: {e}[/yellow]")


def upload_to_minio(
    file_path: str,
    bucket_name: str,
    object_name: Optional[str] = None
) -> bool:
    """
    Upload a file to MinIO bucket.

    Args:
        file_path: Path to file to upload
        bucket_name: Name of the bucket
        object_name: S3 object name. If not specified, file_path basename is used

    Returns:
        True if file was uploaded, else False
    """
    # Get credentials from environment variables
    access_key = os.getenv('MINIO_ACCESS_KEY')
    secret_key = os.getenv('MINIO_SECRET_KEY')
    endpoint = os.getenv('MINIO_ENDPOINT', 'https://minio.example.com')

    if not access_key or not secret_key:
        console.print("[yellow]MinIO credentials not found in environment[/yellow]")
        return False

    # If S3 object_name was not specified, use file_path basename
    if object_name is None:
        object_name = os.path.basename(file_path)

    # Ensure endpoint has protocol
    if not endpoint.startswith('http'):
        endpoint = f'https://{endpoint}'

    # Create S3 client
    s3_client = boto3.client(
        's3',
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name='us-east-1'
    )

    try:
        s3_client.upload_file(
            file_path,
            bucket_name,
            object_name,
            ExtraArgs={'ContentType': 'application/rss+xml'}
        )
        return True
    except ClientError as e:
        console.print(f"[red]Error uploading to MinIO: {e}[/red]", file=sys.stderr)
        return False


def check_minio_credentials() -> bool:
    """Check if MinIO credentials are configured."""
    return bool(os.getenv('MINIO_ACCESS_KEY') and os.getenv('MINIO_SECRET_KEY'))
