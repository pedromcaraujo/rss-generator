"""Site-specific parsers for extracting articles from HTML."""

import re
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Comment
from rich.console import Console

console = Console()


def clean_html_content(html: str) -> str:
    """
    Clean HTML content by removing unwanted elements and attributes.

    Args:
        html: Raw HTML content

    Returns:
        Cleaned HTML string
    """
    try:
        soup = BeautifulSoup(html, "html.parser")

        # Remove unwanted elements
        unwanted_tags = [
            "nav",
            "header",
            "footer",
            "aside",
            "script",
            "style",
            "svg",
            "button",
            "form",
        ]
        for tag_name in unwanted_tags:
            for element in soup.find_all(tag_name):
                element.decompose()

        # Remove HTML comments
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        # Remove elements with 'muted' class (typically navigation breadcrumbs)
        for element in soup.find_all(class_="muted"):
            element.decompose()

        # Remove short ul/ol lists that are likely navigation
        for ul in list(soup.find_all(["ul", "ol"])):
            text = ul.get_text(strip=True)
            links = ul.find_all("a")
            # If it's short and has links, probably navigation
            if len(text) < 100 and len(links) > 0:
                ul.decompose()

        # Clean up attributes - keep only essential ones
        allowed_attrs = {"href", "src", "alt", "title", "class"}
        for tag in soup.find_all(True):
            attrs_to_remove = [
                attr for attr in list(tag.attrs.keys()) if attr not in allowed_attrs
            ]
            for attr in attrs_to_remove:
                del tag[attr]

        # Get the cleaned HTML
        cleaned = str(soup)

        # Remove excessive whitespace
        cleaned = re.sub(r"\n\s*\n", "\n", cleaned)
        cleaned = re.sub(r"  +", " ", cleaned)

        return cleaned
    except Exception as e:
        console.print(f"[red]Error in clean_html_content: {e}[/red]")
        # Return original HTML if cleaning fails
        return html


def parse_immich(html_content: str, url: str) -> list[dict]:
    """
    Parse Immich blog posts.

    Args:
        html_content: HTML content of the page
        url: Base URL for resolving relative links

    Returns:
        List of article dictionaries
    """
    soup = BeautifulSoup(html_content, "html.parser")
    posts = []

    # Try to find blog post articles
    articles = soup.find_all(
        ["article", "div"],
        class_=lambda x: x and ("post" in x.lower() or "blog" in x.lower()),
    )

    if not articles:
        # Fallback: look for links that might be blog posts
        articles = soup.find_all(
            "a", href=lambda x: x and "/blog/" in x and x != "/blog" and x != "/blog/"
        )

    for article in articles:
        post = {}

        # Extract title
        title_elem = article.find(["h1", "h2", "h3", "h4"])
        if title_elem:
            title_text = title_elem.get_text(strip=True)
        elif article.name == "a":
            title_text = article.get_text(strip=True)
        else:
            continue

        # Clean title - remove date and author suffix patterns
        # Patterns like "TitleDecember 30, 2023— Author"
        title_text = re.sub(
            r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}.*$",
            "",
            title_text,
        )
        title_text = re.sub(
            r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4}.*$",
            "",
            title_text,
        )
        # Remove author patterns like "— AuthorName"
        title_text = re.sub(r"—\s*.*$", "", title_text)
        post["title"] = title_text.strip()

        # Extract link
        link_elem = article.find("a", href=True) if article.name != "a" else article
        if link_elem:
            post["link"] = urljoin(url, link_elem["href"])
        else:
            continue

        # Extract date - try multiple methods
        post["date"] = None

        # Try 1: Look for time element with datetime attribute
        time_elem = article.find("time")
        if time_elem and time_elem.get("datetime"):
            post["date"] = time_elem["datetime"]

        # Try 2: Look for elements with date in class name
        if not post["date"]:
            date_elem = article.find(
                ["time", "span", "div"], class_=lambda x: x and "date" in x.lower()
            )
            if date_elem:
                post["date"] = date_elem.get("datetime") or date_elem.get_text(
                    strip=True
                )

        # Try 3: Extract from URL pattern (e.g., /2023-12-30-title)
        if not post["date"] and link_elem:
            link_text = link_elem["href"]
            date_match = re.search(r"/(\d{4})-(\d{2})-(\d{2})", link_text)
            if date_match:
                post["date"] = (
                    f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"
                )

        # Try 4: Look in article text for common date patterns
        if not post["date"]:
            text = article.get_text()
            # Match patterns like "December 30, 2023", "Dec 30, 2023"
            date_patterns = [
                r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}",
                r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4}",
            ]
            for pattern in date_patterns:
                match = re.search(pattern, text)
                if match:
                    post["date"] = match.group(0)
                    break

        # Fallback: use current date if nothing found
        if not post["date"]:
            post["date"] = datetime.now().strftime("%Y-%m-%d")

        # Extract description/excerpt
        desc_elem = article.find(
            ["p", "div"],
            class_=lambda x: x
            and ("excerpt" in x.lower() or "description" in x.lower()),
        )
        if desc_elem:
            post["description"] = desc_elem.get_text(strip=True)
        else:
            # Try to get first paragraph
            p_elem = article.find("p")
            post["description"] = (
                p_elem.get_text(strip=True) if p_elem else post["title"]
            )

        if post.get("title") and post.get("link"):
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
    soup = BeautifulSoup(html_content, "html.parser")
    articles_list = []
    seen_links = set()

    # Find all article links
    articles = soup.find_all("a", href=lambda x: x and "/noticias/" in x)

    for article in articles:
        # Extract link
        link = article.get("href")
        if not link:
            continue

        # Make absolute URL
        full_link = urljoin(url, link)

        # Skip duplicates
        if full_link in seen_links:
            continue
        seen_links.add(full_link)

        article_data = {"link": full_link}

        # Extract title - try different elements
        title_elem = article.find(["h1", "h2", "h3", "h4", "span"])
        if title_elem:
            title = title_elem.get_text(strip=True)
            if title and len(title) > 5:
                article_data["title"] = title
            else:
                title = article.get_text(strip=True)
                if title and len(title) > 5:
                    article_data["title"] = title
                else:
                    continue
        else:
            title = article.get_text(strip=True)
            if title and len(title) > 5:
                article_data["title"] = title
            else:
                continue

        # Try to extract date from URL (format: 2025-10-01)
        date_match = re.search(r"/(\d{4}-\d{2}-\d{2})-", full_link)
        if date_match:
            article_data["date"] = date_match.group(1)
        else:
            article_data["date"] = datetime.now().strftime("%Y-%m-%d")

        # Extract category from URL
        category_match = re.search(r"/noticias/([^/]+)/", full_link)
        if category_match:
            article_data["category"] = category_match.group(1).title()

        # Try to find description
        desc_elem = article.find("p")
        if desc_elem:
            article_data["description"] = desc_elem.get_text(strip=True)
        else:
            article_data["description"] = article_data["title"]

        if article_data.get("title") and article_data.get("link"):
            articles_list.append(article_data)

    return articles_list


def parse_newalbumreleases_metal(html_content: str, url: str) -> list[dict]:
    """
    Parse New Album Releases metal category.

    Args:
        html_content: HTML content of the page
        url: Base URL for resolving relative links

    Returns:
        List of article dictionaries
    """
    soup = BeautifulSoup(html_content, "html.parser")
    albums = []
    seen_links = set()

    # Find all album entries
    singles = soup.find_all("div", class_="single")

    for single in singles:
        album = {}

        # Extract title and link
        h2 = single.find("h2")
        if not h2:
            continue

        link_elem = h2.find("a", href=True)
        if not link_elem:
            continue

        album["title"] = link_elem.get_text(strip=True)
        album["link"] = link_elem["href"]

        # Skip duplicates
        if album["link"] in seen_links:
            continue
        seen_links.add(album["link"])

        # Extract date from the date div
        date_div = single.find("div", class_="date")
        if date_div:
            clock_span = date_div.find("span", class_="clock")
            if clock_span:
                # Format: " On September - 29 - 2025"
                date_text = clock_span.get_text(strip=True)
                date_match = re.search(
                    r"On\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+-\s+(\d{1,2})\s+-\s+(\d{4})",
                    date_text,
                )
                if date_match:
                    month_name = date_match.group(1)
                    day = date_match.group(2).zfill(2)
                    year = date_match.group(3)

                    # Convert month name to number
                    month_map = {
                        "January": "01",
                        "February": "02",
                        "March": "03",
                        "April": "04",
                        "May": "05",
                        "June": "06",
                        "July": "07",
                        "August": "08",
                        "September": "09",
                        "October": "10",
                        "November": "11",
                        "December": "12",
                    }
                    month = month_map.get(month_name, "01")
                    album["date"] = f"{year}-{month}-{day}"
                else:
                    album["date"] = datetime.now().strftime("%Y-%m-%d")
            else:
                album["date"] = datetime.now().strftime("%Y-%m-%d")
        else:
            album["date"] = datetime.now().strftime("%Y-%m-%d")

        # Extract album details from the entry div
        entry_div = single.find("div", class_="entry")
        if entry_div:
            # Extract image
            img = entry_div.find("img")
            if img and img.get("src"):
                album["image"] = img["src"]

            # Extract all the details from the text
            entry_text = entry_div.get_text()

            # Extract Artist
            artist_match = re.search(r"Artist:\s*([^\n]+)", entry_text)
            if artist_match:
                album["artist"] = artist_match.group(1).strip()

            # Extract Album name
            album_match = re.search(r"Album:\s*([^\n]+)", entry_text)
            if album_match:
                album["album_name"] = album_match.group(1).strip()

            # Extract Released year
            released_match = re.search(r"Released:\s*([^\n]+)", entry_text)
            if released_match:
                album["released"] = released_match.group(1).strip()

            # Extract Style/Genre
            style_match = re.search(r"Style:\s*([^\n]+)", entry_text)
            if style_match:
                album["style"] = style_match.group(1).strip()

            # Extract Format
            format_match = re.search(r"Format:\s*([^\n]+)", entry_text)
            if format_match:
                album["format"] = format_match.group(1).strip()

            # Extract Size
            size_match = re.search(r"Size:\s*([^\n]+)", entry_text)
            if size_match:
                album["size"] = size_match.group(1).strip()

            # Build rich HTML description with all info
            description_parts = []
            if album.get("image"):
                description_parts.append(
                    f'<p><img src="{album["image"]}" alt="Album cover" /></p>'
                )

            description_parts.append("<p><strong>Album Details:</strong></p>")
            description_parts.append("<ul>")
            if album.get("artist"):
                description_parts.append(f"<li><strong>Artist:</strong> {album['artist']}</li>")
            if album.get("album_name"):
                description_parts.append(f"<li><strong>Album:</strong> {album['album_name']}</li>")
            if album.get("released"):
                description_parts.append(f"<li><strong>Released:</strong> {album['released']}</li>")
            if album.get("style"):
                description_parts.append(f"<li><strong>Style:</strong> {album['style']}</li>")
            if album.get("format"):
                description_parts.append(f"<li><strong>Format:</strong> {album['format']}</li>")
            if album.get("size"):
                description_parts.append(f"<li><strong>Size:</strong> {album['size']}</li>")
            description_parts.append("</ul>")

            album["description"] = "".join(description_parts)
        else:
            album["description"] = album["title"]

        if album.get("title") and album.get("link"):
            albums.append(album)

    return albums


# Parser registry - maps parser names to functions
PARSERS = {
    "parse_immich": parse_immich,
    "parse_diariodominho": parse_diariodominho,
    "parse_newalbumreleases_metal": parse_newalbumreleases_metal,
}


def get_parser(parser_name: str):
    """Get parser function by name."""
    return PARSERS.get(parser_name)


def extract_immich_content(html_content: str) -> Optional[str]:
    """
    Extract full article content from an Immich blog post page.

    Args:
        html_content: HTML content of the article page

    Returns:
        Article content as HTML string, or None if extraction fails
    """
    try:
        soup = BeautifulSoup(html_content, "html.parser")

        # Immich uses a specific structure: find h1, then go up to container
        h1 = soup.find("h1")
        if h1 and h1.parent and h1.parent.parent:
            # The grandparent div contains all the article content
            content_container = h1.parent.parent
            # Extract as string first, then clean in a new soup
            content_html = str(content_container)
            if content_html:
                return clean_html_content(content_html)

        # Fallback: try to find article or main tags
        article = soup.find("article")
        if not article:
            article = soup.find("main")

        if article:
            article_html = str(article)
            if article_html:
                return clean_html_content(article_html)

        return None
    except Exception as e:
        console.print(
            f"[yellow]Warning: Could not extract Immich content: {e}[/yellow]"
        )
        return None


def extract_immich_metadata(html_content: str) -> dict:
    """
    Extract metadata (author, image) from Immich blog post.

    Args:
        html_content: HTML content of the article page

    Returns:
        Dictionary with 'author' and 'image' keys
    """
    metadata = {"author": None, "image": None}

    try:
        soup = BeautifulSoup(html_content, "html.parser")

        # Extract author - look for text after "—"
        for p in soup.find_all("p"):
            text = p.get_text(strip=True)
            if text.startswith("—"):
                # Remove the "—" and clean
                metadata["author"] = text.replace("—", "").strip()
                break

        # Extract featured image - look for first img tag in content
        h1 = soup.find("h1")
        if h1 and h1.parent and h1.parent.parent:
            container = h1.parent.parent
            img = container.find("img")
            if img and img.get("src"):
                src = img["src"]
                # Make absolute URL if needed
                if src.startswith("/"):
                    src = f"https://immich.app{src}"
                metadata["image"] = src

    except Exception as e:
        console.print(
            f"[yellow]Warning: Could not extract Immich metadata: {e}[/yellow]"
        )

    return metadata


def extract_diariodominho_content(html_content: str) -> Optional[str]:
    """
    Extract full article content from a Diário do Minho article page.

    Args:
        html_content: HTML content of the article page

    Returns:
        Article content as HTML string, or None if extraction fails
    """
    try:
        soup = BeautifulSoup(html_content, "html.parser")

        # Look for article content
        article = soup.find("article")
        if not article:
            # Try finding by class patterns
            article = soup.find(
                ["div", "section"],
                class_=lambda x: x
                and ("article" in x.lower() or "content" in x.lower()),
            )

        if article:
            article_html = str(article)
            if article_html:
                return clean_html_content(article_html)

        return None
    except Exception as e:
        console.print(
            f"[yellow]Warning: Could not extract Diário do Minho content: {e}[/yellow]"
        )
        return None


def extract_diariodominho_metadata(html_content: str) -> dict:
    """
    Extract metadata (author, image) from Diário do Minho article.

    Args:
        html_content: HTML content of the article page

    Returns:
        Dictionary with 'author' and 'image' keys
    """
    metadata = {"author": None, "image": None}

    try:
        soup = BeautifulSoup(html_content, "html.parser")

        # Extract author - look for byline or author meta
        author_elem = soup.find(
            ["span", "div", "p"], class_=lambda x: x and "author" in x.lower()
        )
        if author_elem:
            metadata["author"] = author_elem.get_text(strip=True)

        # Extract featured image
        article = soup.find("article")
        if article:
            img = article.find("img")
            if img and img.get("src"):
                src = img["src"]
                # Make absolute URL if needed
                if src.startswith("/"):
                    src = f"https://www.diariodominho.pt{src}"
                metadata["image"] = src

    except Exception as e:
        console.print(
            f"[yellow]Warning: Could not extract Diário do Minho metadata: {e}[/yellow]"
        )

    return metadata


# Content extractor registry
CONTENT_EXTRACTORS = {
    "parse_immich": extract_immich_content,
    "parse_diariodominho": extract_diariodominho_content,
}

# Metadata extractor registry
METADATA_EXTRACTORS = {
    "parse_immich": extract_immich_metadata,
    "parse_diariodominho": extract_diariodominho_metadata,
}


def get_content_extractor(parser_name: str):
    """Get content extractor function by parser name."""
    return CONTENT_EXTRACTORS.get(parser_name)


def get_metadata_extractor(parser_name: str):
    """Get metadata extractor function by parser name."""
    return METADATA_EXTRACTORS.get(parser_name)
