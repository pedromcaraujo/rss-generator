# RSS Feed Generator

A modern CLI tool for generating RSS feeds from websites and uploading them to S3-compatible storage (AWS S3, MinIO, etc.).

## Installation

```bash
# Using uvx (recommended)
uvx rss-generator --help

# Using pip
pip install rss-generator
```

## Usage

```bash
# List available sites
rss-generator list

# Generate feed for a specific site
rss-generator generate immich

# Generate all feeds
rss-generator generate --all

# Generate with custom bucket
rss-generator generate --all --bucket my-feeds

# Upload XSL stylesheet and get URL
rss-generator upload-xsl

# Generate with custom XSL stylesheet
rss-generator generate immich --xsl-url https://example.com/feed.xsl

# Check configuration
rss-generator check
```

## Configuration

Create a `.env` file with your S3 credentials:

### For AWS S3:

```env
S3_ACCESS_KEY=your-aws-access-key
S3_SECRET_KEY=your-aws-secret-key
S3_REGION=us-east-1
S3_BUCKET=my-rss-feeds
S3_PUBLIC_URL=https://my-bucket.s3.amazonaws.com
```

### For MinIO or S3-compatible storage:

```env
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key
S3_ENDPOINT=https://minio.example.com
S3_BUCKET=rss-feeds
S3_PUBLIC_URL=https://minio.example.com  # Public URL for accessing files
```

### Legacy MinIO configuration (still supported):

```env
MINIO_ACCESS_KEY=your-access-key
MINIO_SECRET_KEY=your-secret-key
MINIO_ENDPOINT=https://minio.example.com
```

### Environment Variables Reference:

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `S3_ACCESS_KEY` | S3 access key (or `MINIO_ACCESS_KEY`) | Yes | None |
| `S3_SECRET_KEY` | S3 secret key (or `MINIO_SECRET_KEY`) | Yes | None |
| `S3_ENDPOINT` | S3 endpoint URL (not needed for AWS S3) | No* | None |
| `S3_BUCKET` | Bucket name for uploads | No | `rss-feeds` |
| `S3_REGION` | AWS region | No | `us-east-1` |
| `S3_PUBLIC_URL` | Public base URL for accessing feeds | Recommended | Falls back to `S3_ENDPOINT` |
| `XSL_URL` | XSL stylesheet URL for browser-friendly RSS | No | Auto-generated from bucket |

\* Required for MinIO and S3-compatible services. Not needed for AWS S3.

## Currently Supported Sites

- **Immich Blog** - https://immich.app/blog
- **Diario do Minho** - https://www.diariodominho.pt/

## Want to Add a Site?

[Create an issue](https://github.com/pedromcaraujo/rss-generator/issues/new) with the website URL and I'll add support for it!

## Features

- **Automated RSS Generation**: Scrape websites and generate valid RSS 2.0 feeds
- **JavaScript Rendering**: Handle dynamic content with Playwright browser automation
- **S3-Compatible Storage**: Upload feeds to AWS S3, MinIO, or any S3-compatible service
- **Multiple Sites**: Support for multiple websites with easy configuration
- **Beautiful CLI**: Rich terminal interface with progress indicators
- **Optional XSL Styling**: Apply XSL stylesheets for browser-friendly RSS viewing

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=rss_generator --cov-report=html

# Run tests on multiple Python versions
tox
```

### Supported Python Versions

- Python 3.12
- Python 3.13

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed development instructions.

## License

MIT
