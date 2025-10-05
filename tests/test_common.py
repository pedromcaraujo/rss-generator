"""Tests for common utilities module."""

import os
from unittest.mock import patch, MagicMock


from rss_generator.common import (
    generate_rss_feed,
    check_minio_credentials,
    check_playwright_browsers,
    upload_to_minio,
)


class TestGenerateRssFeed:
    """Tests for generate_rss_feed function."""

    def test_generates_valid_rss_feed(
        self, sample_articles, sample_site_config, temp_output_file
    ):
        """Test that a valid RSS feed is generated."""
        result = generate_rss_feed(
            sample_articles,
            temp_output_file,
            sample_site_config,
        )
        assert result is True
        assert os.path.exists(temp_output_file)

        # Read and verify content
        with open(temp_output_file, "r") as f:
            content = f.read()
            assert "<?xml version=" in content
            assert '<rss version="2.0"' in content
            assert "Test Article 1" in content
            assert "Test Article 2" in content

    def test_includes_channel_info(
        self, sample_articles, sample_site_config, temp_output_file
    ):
        """Test that channel information is included."""
        generate_rss_feed(sample_articles, temp_output_file, sample_site_config)

        with open(temp_output_file, "r") as f:
            content = f.read()
            assert sample_site_config["name"] in content
            assert sample_site_config["url"] in content
            assert sample_site_config["description"] in content

    def test_includes_article_content(
        self, sample_articles, sample_site_config, temp_output_file
    ):
        """Test that article content is included when available."""
        generate_rss_feed(sample_articles, temp_output_file, sample_site_config)

        with open(temp_output_file, "r") as f:
            content = f.read()
            assert "Full content here" in content

    def test_includes_article_image(
        self, sample_articles, sample_site_config, temp_output_file
    ):
        """Test that article images are included when available."""
        generate_rss_feed(sample_articles, temp_output_file, sample_site_config)

        with open(temp_output_file, "r") as f:
            content = f.read()
            assert "https://example.com/image.jpg" in content

    def test_includes_author(
        self, sample_articles, sample_site_config, temp_output_file
    ):
        """Test that author information is included when available."""
        generate_rss_feed(sample_articles, temp_output_file, sample_site_config)

        with open(temp_output_file, "r") as f:
            content = f.read()
            assert "John Doe" in content

    def test_handles_xsl_url(
        self, sample_articles, sample_site_config, temp_output_file
    ):
        """Test that XSL URL is included when provided."""
        xsl_url = "https://example.com/feed.xsl"
        generate_rss_feed(
            sample_articles, temp_output_file, sample_site_config, xsl_url=xsl_url
        )

        with open(temp_output_file, "r") as f:
            content = f.read()
            assert xsl_url in content

    def test_generates_xsl_url_from_bucket(
        self, sample_articles, sample_site_config, temp_output_file, mock_env_vars
    ):
        """Test that XSL URL is generated from bucket name."""
        generate_rss_feed(
            sample_articles,
            temp_output_file,
            sample_site_config,
            bucket_name="test-bucket",
        )

        with open(temp_output_file, "r") as f:
            content = f.read()
            # Should contain generated XSL URL
            assert "test-bucket" in content or "feed.xsl" in content

    def test_parses_various_date_formats(self, sample_site_config, temp_output_file):
        """Test parsing of various date formats."""
        articles = [
            {"title": "Test 1", "link": "http://example.com/1", "date": "2023-12-30"},
            {
                "title": "Test 2",
                "link": "http://example.com/2",
                "date": "December 30, 2023",
            },
            {"title": "Test 3", "link": "http://example.com/3", "date": "Dec 30, 2023"},
            {
                "title": "Test 4",
                "link": "http://example.com/4",
                "date": "2023-12-30T10:00:00",
            },
        ]

        result = generate_rss_feed(articles, temp_output_file, sample_site_config)
        assert result is True

    def test_handles_missing_dates(self, sample_site_config, temp_output_file):
        """Test handling of articles without dates."""
        articles = [
            {"title": "Test Article", "link": "http://example.com/test"},
        ]

        result = generate_rss_feed(articles, temp_output_file, sample_site_config)
        assert result is True

    def test_handles_empty_articles_list(self, sample_site_config, temp_output_file):
        """Test handling of empty articles list."""
        result = generate_rss_feed([], temp_output_file, sample_site_config)
        assert result is True

        with open(temp_output_file, "r") as f:
            content = f.read()
            assert "<rss" in content


class TestCheckMinioCredentials:
    """Tests for check_minio_credentials function."""

    def test_returns_true_with_s3_credentials(self, monkeypatch):
        """Test that function returns True when S3 credentials are set."""
        monkeypatch.setenv("S3_ACCESS_KEY", "test-key")
        monkeypatch.setenv("S3_SECRET_KEY", "test-secret")
        assert check_minio_credentials() is True

    def test_returns_true_with_minio_credentials(self, monkeypatch):
        """Test that function returns True when MINIO credentials are set."""
        monkeypatch.setenv("MINIO_ACCESS_KEY", "test-key")
        monkeypatch.setenv("MINIO_SECRET_KEY", "test-secret")
        assert check_minio_credentials() is True

    def test_returns_false_without_credentials(self, monkeypatch):
        """Test that function returns False when credentials are missing."""
        monkeypatch.delenv("S3_ACCESS_KEY", raising=False)
        monkeypatch.delenv("S3_SECRET_KEY", raising=False)
        monkeypatch.delenv("MINIO_ACCESS_KEY", raising=False)
        monkeypatch.delenv("MINIO_SECRET_KEY", raising=False)
        assert check_minio_credentials() is False

    def test_returns_false_with_partial_credentials(self, monkeypatch):
        """Test that function returns False when only one credential is set."""
        monkeypatch.setenv("S3_ACCESS_KEY", "test-key")
        monkeypatch.delenv("S3_SECRET_KEY", raising=False)
        monkeypatch.delenv("MINIO_ACCESS_KEY", raising=False)
        monkeypatch.delenv("MINIO_SECRET_KEY", raising=False)
        assert check_minio_credentials() is False


class TestCheckPlaywrightBrowsers:
    """Tests for check_playwright_browsers function."""

    @patch("rss_generator.common.sync_playwright")
    def test_returns_true_when_browsers_installed(self, mock_playwright):
        """Test that function returns True when browsers are installed."""
        mock_context = MagicMock()
        mock_browser = MagicMock()
        mock_context.__enter__.return_value.chromium.launch.return_value = mock_browser
        mock_playwright.return_value = mock_context

        assert check_playwright_browsers() is True
        mock_browser.close.assert_called_once()

    @patch("rss_generator.common.sync_playwright")
    def test_returns_false_when_executable_missing(self, mock_playwright):
        """Test that function returns False when browser executable is missing."""
        mock_context = MagicMock()
        mock_context.__enter__.return_value.chromium.launch.side_effect = Exception(
            "Executable doesn't exist at /path/to/browser"
        )
        mock_playwright.return_value = mock_context

        assert check_playwright_browsers() is False

    @patch("rss_generator.common.sync_playwright")
    def test_returns_true_for_other_errors(self, mock_playwright):
        """Test that function returns True for non-browser-missing errors."""
        mock_context = MagicMock()
        mock_context.__enter__.return_value.chromium.launch.side_effect = Exception(
            "Some other error"
        )
        mock_playwright.return_value = mock_context

        assert check_playwright_browsers() is True


class TestUploadToMinio:
    """Tests for upload_to_minio function."""

    @patch("rss_generator.common.boto3.client")
    def test_uploads_file_successfully(
        self, mock_boto_client, temp_output_file, mock_env_vars
    ):
        """Test successful file upload to MinIO."""
        # Create a test file
        with open(temp_output_file, "w") as f:
            f.write("test content")

        # Mock the S3 client
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        result = upload_to_minio(temp_output_file, "test-bucket")

        assert result is True
        mock_s3.upload_file.assert_called_once()

    @patch("rss_generator.common.boto3.client")
    def test_uses_custom_object_name(
        self, mock_boto_client, temp_output_file, mock_env_vars
    ):
        """Test upload with custom object name."""
        with open(temp_output_file, "w") as f:
            f.write("test content")

        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        result = upload_to_minio(temp_output_file, "test-bucket", "custom_name.xml")

        assert result is True
        call_args = mock_s3.upload_file.call_args
        assert call_args[0][2] == "custom_name.xml"

    def test_returns_false_without_credentials(self, temp_output_file, monkeypatch):
        """Test that upload fails gracefully without credentials."""
        monkeypatch.delenv("S3_ACCESS_KEY", raising=False)
        monkeypatch.delenv("S3_SECRET_KEY", raising=False)
        monkeypatch.delenv("MINIO_ACCESS_KEY", raising=False)
        monkeypatch.delenv("MINIO_SECRET_KEY", raising=False)

        result = upload_to_minio(temp_output_file, "test-bucket")
        assert result is False

    @patch("rss_generator.common.boto3.client")
    def test_handles_upload_error(
        self, mock_boto_client, temp_output_file, mock_env_vars
    ):
        """Test handling of upload errors."""
        from botocore.exceptions import ClientError

        with open(temp_output_file, "w") as f:
            f.write("test content")

        mock_s3 = MagicMock()
        mock_s3.upload_file.side_effect = ClientError(
            {"Error": {"Code": "NoSuchBucket", "Message": "Bucket not found"}},
            "upload_file",
        )
        mock_boto_client.return_value = mock_s3

        result = upload_to_minio(temp_output_file, "test-bucket")
        assert result is False

    @patch("rss_generator.common.boto3.client")
    def test_configures_endpoint_url(
        self, mock_boto_client, temp_output_file, mock_env_vars
    ):
        """Test that endpoint URL is configured correctly."""
        with open(temp_output_file, "w") as f:
            f.write("test content")

        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        upload_to_minio(temp_output_file, "test-bucket")

        # Check that boto3.client was called with endpoint_url
        call_kwargs = mock_boto_client.call_args[1]
        assert "endpoint_url" in call_kwargs
        assert call_kwargs["endpoint_url"] == "https://s3.example.com"

    @patch("rss_generator.common.boto3.client")
    def test_sets_correct_content_type(
        self, mock_boto_client, temp_output_file, mock_env_vars
    ):
        """Test that correct content type is set for RSS feeds."""
        with open(temp_output_file, "w") as f:
            f.write("test content")

        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        upload_to_minio(temp_output_file, "test-bucket")

        # Check ExtraArgs contains ContentType
        call_args = mock_s3.upload_file.call_args
        extra_args = call_args[1]["ExtraArgs"]
        assert extra_args["ContentType"] == "application/rss+xml"


class TestFetchPageWithPlaywright:
    """Tests for fetch_page_with_playwright function.

    Note: These tests are intentionally minimal as they require
    a full browser setup. Consider using integration tests for
    comprehensive testing of this functionality.
    """

    @patch("rss_generator.common.sync_playwright")
    def test_returns_html_content(self, mock_playwright):
        """Test that function returns HTML content."""
        from rss_generator.common import fetch_page_with_playwright

        # Mock the playwright context manager and browser
        mock_p = MagicMock()
        mock_browser = MagicMock()
        mock_page = MagicMock()
        mock_page.content.return_value = "<html>Test content</html>"
        mock_browser.new_page.return_value = mock_page
        mock_p.chromium.launch.return_value = mock_browser
        mock_playwright.return_value.__enter__.return_value = mock_p

        result = fetch_page_with_playwright("https://example.com")

        assert result == "<html>Test content</html>"
        mock_page.goto.assert_called_once()
        mock_browser.close.assert_called_once()

    @patch("rss_generator.common.sync_playwright")
    def test_returns_none_on_error(self, mock_playwright):
        """Test that function returns None on error."""
        from rss_generator.common import fetch_page_with_playwright

        mock_playwright.side_effect = Exception("Network error")

        result = fetch_page_with_playwright("https://example.com")
        assert result is None
