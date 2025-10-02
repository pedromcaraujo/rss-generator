# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

RSS Generator is a CLI tool and Python package for generating RSS feeds from websites that don't provide them. Currently supports Immich Blog and Diário do Minho. Uses Playwright for JavaScript rendering, BeautifulSoup for parsing, and uploads to S3-compatible storage.

## Development Commands

This project uses `uv` for dependency management. All commands should use `uv run` prefix.

### Testing
```bash
# Run all tests
uv run pytest

# Single test file
uv run pytest tests/test_parsers.py

# Single test
uv run pytest tests/test_parsers.py::TestParseImmich::test_parses_basic_structure

# With coverage
uv run pytest --cov=rss_generator --cov-report=html

# Multi-version testing
tox
```

### Code Quality
```bash
# Lint (must pass with zero errors)
uv run ruff check rss_generator tests

# Auto-fix linting issues
uv run ruff check --fix rss_generator tests

# Format code
uv run ruff format rss_generator tests
```

### Running the CLI
```bash
# List configured sites
uv run python -m rss_generator list

# Generate RSS for a site
uv run python -m rss_generator generate immich --no-upload

# Check environment configuration
uv run python -m rss_generator check
```

## Architecture

### Parser Registry Pattern

The codebase uses a registry pattern for extensibility. Parsers are functions registered in dictionaries:

**`rss_generator/parsers.py`**:
- `PARSERS` dict maps parser names to parsing functions
- `CONTENT_EXTRACTORS` dict maps parser names to content extraction functions
- `METADATA_EXTRACTORS` dict maps parser names to metadata extraction functions

Each site parser receives HTML and returns `list[dict]` with article data. The registry allows `cli.py` to dynamically call the correct parser based on site configuration.

### Site Configuration System

**`rss_generator/sites.py`** contains the `SITES` dict mapping site IDs to configuration:
```python
{
    'id': str,           # Unique site identifier
    'name': str,         # Display name
    'url': str,          # Site URL to scrape
    'output_file': str,  # Where to save RSS XML
    'parser': str,       # Parser function name from PARSERS dict
    'language': str,     # ISO language code
    'max_articles': int, # Limit for feed size
    'wait_time': int,    # Playwright page load wait (ms)
}
```

The CLI looks up sites from this dict and uses the `parser` field to retrieve the correct parser function from the registry.

### RSS Generation Flow

1. **`cli.py:process_site()`** - Main orchestrator
2. Fetches HTML via **`common.py:fetch_page_with_playwright()`**
3. Calls parser from registry to extract article list
4. Optionally fetches full content for each article
5. **`common.py:generate_rss_feed()`** renders Jinja2 template at `templates/rss_feed.xml`
6. Optionally uploads to S3 via **`common.py:upload_to_minio()`**

### Testing Strategy

- **Mock external dependencies**: Playwright, S3 client (boto3)
- **Fixtures in conftest.py**: Sample HTML, articles, site configs
- **Sample HTML in tests/fixtures/**: For parser integration testing
- Use `@patch` decorators to mock functions like `fetch_page_with_playwright`

The test suite achieves 82% coverage by mocking external I/O and focusing on logic.

## Adding a New Site

1. Add site config to `SITES` dict in `rss_generator/sites.py`
2. Create `parse_<sitename>()` function in `rss_generator/parsers.py`
3. Register in `PARSERS = {'parse_<sitename>': parse_<sitename>}`
4. (Optional) Add content extractor to `CONTENT_EXTRACTORS` dict
5. (Optional) Add metadata extractor to `METADATA_EXTRACTORS` dict
6. Add tests to `tests/test_parsers.py` with sample HTML
7. Add fixture HTML to `tests/fixtures/<sitename>.html`

## Important Constraints

- **Rich Console**: Uses `rich.console.Console()` for output. Does NOT support `file=sys.stderr` parameter (will cause TypeError)
- **uv dependency management**: Use `uv add <package>` for dependencies, `uv add --dev <package>` for dev dependencies. Don't use pip directly.
- **Python 3.12+ required**: Uses modern type hints like `list[dict]` instead of `List[Dict]`
- **Playwright browsers**: Must run `playwright install chromium` after setup for headless browser functionality

## Root Scripts

- **`immich_blog.py`** - Standalone RSS generator for Immich Blog (https://immich.app/blog)
- **`diariodominho.py`** - Standalone RSS generator for Diário do Minho (https://www.diariodominho.pt/)

These are **independent implementations** that directly use Playwright + BeautifulSoup + feedgen. They do NOT use the `rss_generator` package. Keep these as they provide alternative implementations and can be run directly via `python immich_blog.py` or `python diariodominho.py`.

## Environment Variables

S3 credentials read from `.env` file:
- `S3_ACCESS_KEY` / `S3_SECRET_KEY` - Required for uploads
- `S3_ENDPOINT` - For MinIO/S3-compatible (not AWS S3)
- `S3_BUCKET` - Defaults to 'rss-feeds'
- `S3_PUBLIC_URL` - Public URL for accessing uploaded feeds
- Legacy `MINIO_*` prefixes still supported for backward compatibility

Code checks credentials with `check_minio_credentials()` before upload attempts.

## CI/CD

GitHub Actions workflow at `.github/workflows/test.yml` runs on push/PR:
- Tests on Python 3.12 and 3.13 matrix
- Installs Playwright browsers via apt dependencies
- Runs ruff linting
- Generates coverage reports

Ensure all tests pass and linting is clean before committing.
