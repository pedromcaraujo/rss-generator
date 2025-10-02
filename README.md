# RSS Feed Generator

A modern CLI tool for generating RSS feeds from websites and uploading them to MinIO.

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

# Check configuration
rss-generator check
```

## Configuration

Create a `.env` file:

```env
MINIO_ACCESS_KEY=your-access-key
MINIO_SECRET_KEY=your-secret-key
MINIO_ENDPOINT=https://minio.example.com
```

## Currently Supported Sites

- **Immich Blog** - https://immich.app/blog
- **Diario do Minho** - https://www.diariodominho.pt/

## Want to Add a Site?

[Create an issue](https://github.com/pedromcaraujo/rss-generator/issues/new) with the website URL and I'll add support for it!

## License

MIT
