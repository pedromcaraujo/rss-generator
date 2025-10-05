"""Pytest configuration and shared fixtures."""

import pytest


@pytest.fixture
def sample_immich_html():
    """Sample HTML from Immich blog for testing."""
    return """
    <html>
        <body>
            <article class="blog-post">
                <h2>Immich Version 1.0.0 Released</h2>
                <a href="/blog/2023-12-30-version-1.0.0">Read more</a>
                <time datetime="2023-12-30T00:00:00">December 30, 2023</time>
                <p>We're excited to announce the release of Immich 1.0.0.</p>
            </article>
            <article class="blog-post">
                <h2>Feature Update: Machine Learning</h2>
                <a href="/blog/2023-12-15-ml-update">Read more</a>
                <time datetime="2023-12-15T00:00:00">December 15, 2023</time>
                <p>New machine learning features added.</p>
            </article>
        </body>
    </html>
    """


@pytest.fixture
def sample_diariodominho_html():
    """Sample HTML from Diário do Minho for testing."""
    return """
    <html>
        <body>
            <div class="news-list">
                <a href="/noticias/local/2025-10-02-title-of-news">
                    <h3>Title of News Article</h3>
                    <p>This is the description of the news article.</p>
                </a>
                <a href="/noticias/sports/2025-10-01-sports-news">
                    <h3>Sports News Title</h3>
                    <p>Sports article description.</p>
                </a>
            </div>
        </body>
    </html>
    """


@pytest.fixture
def sample_newalbumreleases_metal_html():
    """Load sample HTML from New Album Releases metal category for testing."""
    import pathlib

    fixture_path = pathlib.Path(__file__).parent / "fixtures" / "newalbumreleases_metal.html"
    return fixture_path.read_text()


@pytest.fixture
def sample_article_content_html():
    """Sample article content for extraction testing."""
    return """
    <html>
        <body>
            <article>
                <h1>Article Title</h1>
                <p>— Author Name</p>
                <img src="/images/featured.jpg" alt="Featured image">
                <p>This is the main content of the article.</p>
                <p>Multiple paragraphs of content here.</p>
            </article>
        </body>
    </html>
    """


@pytest.fixture
def sample_articles():
    """Sample article data for RSS generation testing."""
    return [
        {
            "title": "Test Article 1",
            "link": "https://example.com/article-1",
            "description": "Description of article 1",
            "date": "2023-12-30",
            "author": "John Doe",
        },
        {
            "title": "Test Article 2",
            "link": "https://example.com/article-2",
            "description": "Description of article 2",
            "date": "2023-12-29",
            "content": "<p>Full content here</p>",
            "image": "https://example.com/image.jpg",
        },
    ]


@pytest.fixture
def sample_site_config():
    """Sample site configuration for testing."""
    return {
        "id": "test-site",
        "name": "Test Site",
        "url": "https://example.com",
        "output_file": "test_feed.xml",
        "parser": "parse_immich",
        "language": "en",
        "description": "Test site description",
        "email": "test@example.com",
        "wait_time": 2000,
        "max_articles": 10,
    }


@pytest.fixture
def temp_output_file(tmp_path):
    """Temporary file path for RSS output testing."""
    return str(tmp_path / "test_feed.xml")


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables for S3 testing."""
    monkeypatch.setenv("S3_ACCESS_KEY", "test-access-key")
    monkeypatch.setenv("S3_SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("S3_BUCKET", "test-bucket")
    monkeypatch.setenv("S3_ENDPOINT", "https://s3.example.com")
    monkeypatch.setenv("S3_PUBLIC_URL", "https://cdn.example.com")
