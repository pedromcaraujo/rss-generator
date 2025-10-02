#!/usr/bin/env python3
"""
Daily RSS feed generator for Diário do Minho.
Scrapes https://www.diariodominho.pt/ and generates an RSS feed.
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin
import re

import boto3
from bs4 import BeautifulSoup
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from feedgen.feed import FeedGenerator
from playwright.sync_api import sync_playwright

# Load environment variables from .env file
load_dotenv()


def fetch_news_articles(url: str) -> list[dict]:
    """
    Fetch news articles from Diário do Minho using Playwright for JS rendering.

    Args:
        url: The website URL to scrape

    Returns:
        List of dictionaries containing article information
    """
    articles_list = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until='networkidle')

            # Wait for content to load
            page.wait_for_timeout(3000)

            html_content = page.content()
            browser.close()

    except Exception as e:
        print(f"Error fetching {url}: {e}", file=sys.stderr)
        return []

    soup = BeautifulSoup(html_content, 'html.parser')

    # Find all article links
    articles = soup.find_all('a', href=lambda x: x and '/noticias/' in x)

    seen_links = set()

    for article in articles:
        # Extract link
        link = article.get('href')
        if not link:
            continue

        # Make absolute URL
        full_link = urljoin(url, link)

        # Skip duplicates
        if full_link in seen_links:
            continue
        seen_links.add(full_link)

        article_data = {}
        article_data['link'] = full_link

        # Extract title - try different elements
        title_elem = article.find(['h1', 'h2', 'h3', 'h4', 'span'])
        if title_elem:
            title = title_elem.get_text(strip=True)
            if title and len(title) > 5:  # Filter out very short titles
                article_data['title'] = title
            else:
                # Try getting title from the article tag itself
                title = article.get_text(strip=True)
                if title and len(title) > 5:
                    article_data['title'] = title
                else:
                    continue
        else:
            # Try getting title from the article tag itself
            title = article.get_text(strip=True)
            if title and len(title) > 5:
                article_data['title'] = title
            else:
                continue

        # Try to extract date from URL (format: 2025-10-01)
        date_match = re.search(r'/(\d{4}-\d{2}-\d{2})-', full_link)
        if date_match:
            article_data['date'] = date_match.group(1)
        else:
            article_data['date'] = datetime.now().strftime('%Y-%m-%d')

        # Extract category from URL
        category_match = re.search(r'/noticias/([^/]+)/', full_link)
        if category_match:
            article_data['category'] = category_match.group(1).title()

        # Try to find description
        desc_elem = article.find('p')
        if desc_elem:
            article_data['description'] = desc_elem.get_text(strip=True)
        else:
            article_data['description'] = article_data['title']

        if article_data.get('title') and article_data.get('link'):
            articles_list.append(article_data)

    return articles_list


def generate_rss_feed(articles: list[dict], output_file: str, site_url: str):
    """
    Generate an RSS feed from news articles.

    Args:
        articles: List of article dictionaries
        output_file: Path to save the RSS feed
        site_url: The website URL
    """
    fg = FeedGenerator()
    fg.id(site_url)
    fg.title('Diário do Minho')
    fg.author({'name': 'Diário do Minho', 'email': 'noreply@diariodominho.pt'})
    fg.link(href=site_url, rel='alternate')
    fg.description('Últimas notícias do Diário do Minho')
    fg.language('pt')

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
        try:
            if isinstance(article.get('date'), str):
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
    print(f"RSS feed generated: {output_file}")
    print(f"Found {len(articles)} articles")


def upload_to_minio(file_path: str, bucket_name: str, object_name: str = None) -> bool:
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
        print("Error: MINIO_ACCESS_KEY and MINIO_SECRET_KEY environment variables must be set", file=sys.stderr)
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
        region_name='us-east-1'  # MinIO doesn't care about region, but boto3 requires it
    )

    try:
        s3_client.upload_file(
            file_path,
            bucket_name,
            object_name,
            ExtraArgs={'ContentType': 'application/rss+xml'}
        )
        print(f"Successfully uploaded {file_path} to {bucket_name}/{object_name}")
        print(f"Public URL: https://minio.example.com/{bucket_name}/{object_name}")
        return True
    except ClientError as e:
        print(f"Error uploading to MinIO: {e}", file=sys.stderr)
        return False


def main():
    """Main entry point."""
    site_url = 'https://www.diariodominho.pt/'
    output_file = 'diariodominho_feed.xml'
    bucket_name = 'rss-feeds'

    # Always regenerate the feed (remove the file if it exists)
    if os.path.exists(output_file):
        os.remove(output_file)
        print(f"Removed existing feed file to regenerate")

    print(f"Fetching news articles from {site_url}...")
    articles = fetch_news_articles(site_url)

    if not articles:
        print("No articles found. The page structure may have changed.", file=sys.stderr)
        sys.exit(1)

    generate_rss_feed(articles, output_file, site_url)

    # Check if MinIO credentials are available
    access_key = os.getenv('MINIO_ACCESS_KEY')
    secret_key = os.getenv('MINIO_SECRET_KEY')

    if access_key and secret_key:
        # Upload to MinIO
        print(f"\nUploading to MinIO...")
        success = upload_to_minio(output_file, bucket_name)

        if not success:
            print("Failed to upload to MinIO", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"\nMinIO credentials not found in environment variables.")
        print(f"RSS feed saved locally: {output_file}")
        print(f"To enable MinIO upload, create a .env file with MINIO_ACCESS_KEY and MINIO_SECRET_KEY")


if __name__ == '__main__':
    main()
