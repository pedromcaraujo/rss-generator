"""Site-specific parsers for extracting articles from HTML."""

import re
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup


def parse_immich(html_content: str, url: str) -> list[dict]:
    """
    Parse Immich blog posts.

    Args:
        html_content: HTML content of the page
        url: Base URL for resolving relative links

    Returns:
        List of article dictionaries
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    posts = []

    # Try to find blog post articles
    articles = soup.find_all(
        ['article', 'div'],
        class_=lambda x: x and ('post' in x.lower() or 'blog' in x.lower())
    )

    if not articles:
        # Fallback: look for links that might be blog posts
        articles = soup.find_all(
            'a',
            href=lambda x: x and '/blog/' in x and x != '/blog' and x != '/blog/'
        )

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
        date_elem = article.find(
            ['time', 'span', 'div'],
            class_=lambda x: x and 'date' in x.lower()
        )
        if date_elem:
            date_text = date_elem.get('datetime') or date_elem.get_text(strip=True)
            post['date'] = date_text
        else:
            post['date'] = datetime.now().isoformat()

        # Extract description/excerpt
        desc_elem = article.find(
            ['p', 'div'],
            class_=lambda x: x and ('excerpt' in x.lower() or 'description' in x.lower())
        )
        if desc_elem:
            post['description'] = desc_elem.get_text(strip=True)
        else:
            # Try to get first paragraph
            p_elem = article.find('p')
            post['description'] = p_elem.get_text(strip=True) if p_elem else post['title']

        if post.get('title') and post.get('link'):
            posts.append(post)

    return posts


def parse_diariodominho(html_content: str, url: str) -> list[dict]:
    """
    Parse Diário do Minho news articles.

    Args:
        html_content: HTML content of the page
        url: Base URL for resolving relative links

    Returns:
        List of article dictionaries
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    articles_list = []
    seen_links = set()

    # Find all article links
    articles = soup.find_all('a', href=lambda x: x and '/noticias/' in x)

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

        article_data = {'link': full_link}

        # Extract title - try different elements
        title_elem = article.find(['h1', 'h2', 'h3', 'h4', 'span'])
        if title_elem:
            title = title_elem.get_text(strip=True)
            if title and len(title) > 5:
                article_data['title'] = title
            else:
                title = article.get_text(strip=True)
                if title and len(title) > 5:
                    article_data['title'] = title
                else:
                    continue
        else:
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


# Parser registry - maps parser names to functions
PARSERS = {
    'parse_immich': parse_immich,
    'parse_diariodominho': parse_diariodominho,
}


def get_parser(parser_name: str):
    """Get parser function by name."""
    return PARSERS.get(parser_name)
