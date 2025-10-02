#!/usr/bin/env python3
"""
Daily RSS feed generator for Immich blog.
Scrapes https://immich.app/blog and generates an RSS feed.
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

import boto3
from bs4 import BeautifulSoup
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from feedgen.feed import FeedGenerator
from playwright.sync_api import sync_playwright

# Load environment variables from .env file
load_dotenv()


def fetch_blog_posts(url: str) -> list[dict]:
    """
    Fetch blog posts from the Immich blog page using Playwright for JS rendering.

    Args:
        url: The blog URL to scrape

    Returns:
        List of dictionaries containing post information
    """
    posts = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until='networkidle')

            # Wait for content to load
            page.wait_for_timeout(2000)

            html_content = page.content()
            browser.close()

    except Exception as e:
        print(f"Error fetching {url}: {e}", file=sys.stderr)
        return []

    soup = BeautifulSoup(html_content, 'html.parser')

    # Try to find blog post articles
    articles = soup.find_all(['article', 'div'], class_=lambda x: x and ('post' in x.lower() or 'blog' in x.lower()))

    if not articles:
        # Fallback: look for links that might be blog posts
        articles = soup.find_all('a', href=lambda x: x and '/blog/' in x and x != '/blog' and x != '/blog/')

    for article in articles:
        post = {}

        # Extract title
        title_elem = article.find(['h1', 'h2', 'h3', 'h4'])
        if title_elem:
            post['title'] = title_elem.get_text(strip=True)
        elif article.name == 'a':
            post['title'] = article.get_text(strip=True)
        else:
            continue

        # Extract link
        link_elem = article.find('a', href=True) if article.name != 'a' else article
        if link_elem:
            post['link'] = urljoin(url, link_elem['href'])
        else:
            continue

        # Extract date
        date_elem = article.find(['time', 'span', 'div'], class_=lambda x: x and 'date' in x.lower())
        if date_elem:
            date_text = date_elem.get('datetime') or date_elem.get_text(strip=True)
            post['date'] = date_text
        else:
            post['date'] = datetime.now().isoformat()

        # Extract description/excerpt
        desc_elem = article.find(['p', 'div'], class_=lambda x: x and ('excerpt' in x.lower() or 'description' in x.lower()))
        if desc_elem:
            post['description'] = desc_elem.get_text(strip=True)
        else:
            # Try to get first paragraph
            p_elem = article.find('p')
            post['description'] = p_elem.get_text(strip=True) if p_elem else post['title']

        if post.get('title') and post.get('link'):
            posts.append(post)

    return posts


def generate_rss_feed(posts: list[dict], output_file: str, blog_url: str):
    """
    Generate an RSS feed from blog posts.

    Args:
        posts: List of post dictionaries
        output_file: Path to save the RSS feed
        blog_url: The blog URL
    """
    fg = FeedGenerator()
    fg.id(blog_url)
    fg.title('Immich Blog')
    fg.author({'name': 'Immich', 'email': 'noreply@immich.app'})
    fg.link(href=blog_url, rel='alternate')
    fg.description('Latest posts from the Immich blog')
    fg.language('en')

    for post in posts:
        fe = fg.add_entry()
        fe.id(post['link'])
        fe.title(post['title'])
        fe.link(href=post['link'])
        fe.description(post.get('description', post['title']))

        # Handle date parsing
        try:
            if isinstance(post.get('date'), str):
                # Try to parse common date formats
                for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d', '%B %d, %Y', '%b %d, %Y']:
                    try:
                        dt = datetime.strptime(post['date'], fmt)
                        fe.published(dt)
                        break
                    except ValueError:
                        continue
        except Exception:
            pass

    # Write RSS feed
    fg.rss_file(output_file)
    print(f"RSS feed generated: {output_file}")
    print(f"Found {len(posts)} blog posts")


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
    blog_url = 'https://immich.app/blog'
    output_file = 'immich_blog_feed.xml'
    bucket_name = 'rss-feeds'

    # Always regenerate the feed (remove the file if it exists)
    if os.path.exists(output_file):
        os.remove(output_file)
        print(f"Removed existing feed file to regenerate")

    print(f"Fetching blog posts from {blog_url}...")
    posts = fetch_blog_posts(blog_url)

    if not posts:
        print("No blog posts found. The page structure may have changed.", file=sys.stderr)
        sys.exit(1)

    generate_rss_feed(posts, output_file, blog_url)

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
