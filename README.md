# RSS Feed Generator

A modern CLI tool for generating RSS feeds from websites and uploading them to MinIO.

## Features

- Modern CLI with beautiful output (powered by Typer & Rich)
- Easy to add new sites - just add configuration and parser
- Automatic upload to MinIO S3
- Generate single or all feeds at once
- Configuration validation
- Colored output and progress indicators

## Installation

### Using uvx (recommended)

```bash
# Install from PyPI and run
uvx rss-generator --help

# Or run directly from GitHub
uvx --from git+https://github.com/pedromcaraujo/rss-generator rss-generator --help

# Or clone and run locally
git clone https://github.com/pedromcaraujo/rss-generator.git
cd rss-generator
uvx --from . rss-generator --help
```

### Using pip

```bash
pip install rss-generator
rss-generator --help
```

### Development

```bash
git clone https://github.com/pedromcaraujo/rss-generator.git
cd rss-generator
uv sync
uv run rss-generator --help
```

## Configuration

Create a `.env` file in the project root:

```env
MINIO_ACCESS_KEY=your-access-key
MINIO_SECRET_KEY=your-secret-key
MINIO_ENDPOINT=https://minio.example.com
```

## Usage

### List available sites

```bash
rss-generator list
```

### Check configuration

```bash
rss-generator check
```

### Generate RSS feed for a specific site

```bash
rss-generator generate immich
rss-generator generate diariodominho
```

### Generate all RSS feeds

```bash
rss-generator generate --all
```

### Generate without uploading to MinIO

```bash
rss-generator generate immich --no-upload
```

### Specify custom bucket

```bash
rss-generator generate --all --bucket my-bucket
```

## Adding a New Site

Adding a new site is simple - just 2 steps:

### 1. Add site configuration to `rss_generator/sites.py`

```python
SITES = {
    # ... existing sites ...
    'mynewsite': {
        'id': 'mynewsite',
        'name': 'My New Site',
        'url': 'https://example.com',
        'output_file': 'mynewsite_feed.xml',
        'parser': 'parse_mynewsite',
        'language': 'en',
        'description': 'Latest posts from My New Site',
        'email': 'noreply@example.com',
        'wait_time': 2000,
    },
}
```

### 2. Add parser function to `rss_generator/parsers.py`

```python
def parse_mynewsite(html_content: str, url: str) -> list[dict]:
    """Parse My New Site articles."""
    soup = BeautifulSoup(html_content, 'html.parser')
    articles = []

    # Your parsing logic here
    # Return list of dicts with: title, link, description, date, category (optional)

    return articles

# Don't forget to register the parser
PARSERS = {
    # ... existing parsers ...
    'parse_mynewsite': parse_mynewsite,
}
```

That's it! The new site will automatically appear in `list` and be available for generation.

## Current Sites

- **Immich Blog** - https://immich.app/blog
- **Diario do Minho** - https://www.diariodominho.pt/

## RSS Feed URLs

After generation, feeds are available at:
- Immich: https://minio.example.com/rss-feeds/immich_blog_feed.xml
- Diario do Minho: https://minio.example.com/rss-feeds/diariodominho_feed.xml

## Running Daily

Add to crontab to run daily at 9 AM:

```bash
0 9 * * * cd /path/to/rss-generator && uvx rss-generator generate --all
```

## Project Structure

```
rss-generator/
├── rss_generator/
│   ├── __init__.py
│   ├── __main__.py       # Entry point
│   ├── cli.py            # CLI interface (Typer)
│   ├── common.py         # Shared utilities
│   ├── sites.py          # Site configurations
│   └── parsers.py        # Site-specific parsers
├── .env                  # Environment variables (gitignored)
├── .gitignore
├── pyproject.toml
└── README.md
```

## Legacy Scripts

The original scripts (`main.py` and `diariodominho.py`) are kept for reference but the new CLI is recommended for all operations.

## License

MIT
