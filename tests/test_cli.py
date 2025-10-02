"""Tests for CLI module."""

from unittest.mock import Mock, patch

from typer.testing import CliRunner

from rss_generator.cli import app, process_site


runner = CliRunner()


class TestListCommand:
    """Tests for the list command."""

    def test_list_command_succeeds(self):
        """Test that list command runs successfully."""
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0

    def test_list_command_shows_sites(self):
        """Test that list command displays available sites."""
        result = runner.invoke(app, ["list"])
        assert "immich" in result.stdout.lower()
        assert (
            "diariodominho" in result.stdout.lower()
            or "diário do minho" in result.stdout.lower()
        )

    def test_list_command_shows_table(self):
        """Test that list command displays a table."""
        result = runner.invoke(app, ["list"])
        # Should contain table formatting
        assert "Available Sites" in result.stdout or "ID" in result.stdout


class TestCheckCommand:
    """Tests for the check command."""

    def test_check_command_succeeds(self):
        """Test that check command runs successfully."""
        result = runner.invoke(app, ["check"])
        assert result.exit_code == 0

    def test_check_command_shows_config(self):
        """Test that check command displays configuration."""
        result = runner.invoke(app, ["check"])
        assert (
            "Configuration Check" in result.stdout
            or "credentials" in result.stdout.lower()
        )

    def test_check_command_shows_sites_count(self):
        """Test that check command shows number of configured sites."""
        result = runner.invoke(app, ["check"])
        assert "sites configured" in result.stdout.lower()


class TestGenerateCommand:
    """Tests for the generate command."""

    def test_generate_requires_site_or_all_flag(self):
        """Test that generate command requires either site ID or --all flag."""
        result = runner.invoke(app, ["generate"])
        assert result.exit_code == 1
        assert "Error" in result.stdout or "Provide a site ID" in result.stdout

    def test_generate_with_invalid_site(self):
        """Test that generate command fails with invalid site ID."""
        with patch("rss_generator.cli.process_site") as mock_process:
            mock_process.return_value = False
            result = runner.invoke(app, ["generate", "invalid-site"])
            assert result.exit_code == 1

    @patch("rss_generator.cli.fetch_page_with_playwright")
    @patch("rss_generator.cli.generate_rss_feed")
    @patch("rss_generator.cli.upload_to_minio")
    def test_generate_with_valid_site_no_upload(
        self, mock_upload, mock_generate, mock_fetch
    ):
        """Test generate command with valid site and --no-upload flag."""
        mock_fetch.return_value = "<html><body>Test</body></html>"
        mock_generate.return_value = True

        runner.invoke(app, ["generate", "immich", "--no-upload"])

        # Should not upload when --no-upload is specified
        mock_upload.assert_not_called()

    @patch("rss_generator.cli.process_site")
    def test_generate_all_flag(self, mock_process):
        """Test generate command with --all flag."""
        mock_process.return_value = True

        runner.invoke(app, ["generate", "--all"])

        # Should call process_site for each configured site
        assert mock_process.call_count >= 2  # At least immich and diariodominho

    def test_generate_with_custom_bucket(self):
        """Test generate command with custom bucket."""
        with patch("rss_generator.cli.process_site") as mock_process:
            mock_process.return_value = True

            runner.invoke(
                app, ["generate", "immich", "--bucket", "custom-bucket", "--no-upload"]
            )

            # Check that bucket parameter was passed
            call_kwargs = mock_process.call_args[1]
            assert call_kwargs["bucket_name"] == "custom-bucket"

    def test_generate_with_xsl_url(self):
        """Test generate command with custom XSL URL."""
        with patch("rss_generator.cli.process_site") as mock_process:
            mock_process.return_value = True

            runner.invoke(
                app,
                [
                    "generate",
                    "immich",
                    "--xsl-url",
                    "https://example.com/feed.xsl",
                    "--no-upload",
                ],
            )

            # Check that xsl_url parameter was passed
            call_kwargs = mock_process.call_args[1]
            assert call_kwargs["xsl_url"] == "https://example.com/feed.xsl"


class TestUploadXslCommand:
    """Tests for the upload-xsl command."""

    @patch("rss_generator.cli.check_minio_credentials")
    def test_upload_xsl_fails_without_credentials(self, mock_check):
        """Test that upload-xsl fails without credentials."""
        mock_check.return_value = False

        result = runner.invoke(app, ["upload-xsl"])

        assert result.exit_code == 1
        assert "credentials not configured" in result.stdout.lower()

    @patch("rss_generator.cli.check_minio_credentials")
    @patch("rss_generator.cli.upload_to_minio")
    def test_upload_xsl_succeeds_with_credentials(
        self, mock_upload, mock_check, monkeypatch
    ):
        """Test that upload-xsl succeeds with credentials."""
        mock_check.return_value = True
        mock_upload.return_value = True
        monkeypatch.setenv("S3_PUBLIC_URL", "https://cdn.example.com")

        result = runner.invoke(app, ["upload-xsl"])

        assert result.exit_code == 0
        mock_upload.assert_called_once()

    @patch("rss_generator.cli.check_minio_credentials")
    @patch("rss_generator.cli.upload_to_minio")
    def test_upload_xsl_with_custom_bucket(self, mock_upload, mock_check):
        """Test upload-xsl with custom bucket."""
        mock_check.return_value = True
        mock_upload.return_value = True

        runner.invoke(app, ["upload-xsl", "--bucket", "custom-bucket"])

        # Check that custom bucket was used
        call_args = mock_upload.call_args[0]
        assert "custom-bucket" in call_args


class TestProcessSite:
    """Tests for the process_site function."""

    def test_process_site_returns_false_for_invalid_site(self):
        """Test that process_site returns False for invalid site ID."""
        result = process_site("invalid-site", upload=False)
        assert result is False

    @patch("rss_generator.cli.fetch_page_with_playwright")
    def test_process_site_returns_false_on_fetch_failure(self, mock_fetch):
        """Test that process_site returns False when fetching fails."""
        mock_fetch.return_value = None

        result = process_site("immich", upload=False)
        assert result is False

    @patch("rss_generator.cli.fetch_page_with_playwright")
    @patch("rss_generator.cli.get_parser")
    def test_process_site_returns_false_on_parser_failure(
        self, mock_parser, mock_fetch
    ):
        """Test that process_site returns False when parser is not found."""
        mock_fetch.return_value = "<html>Test</html>"
        mock_parser.return_value = None

        result = process_site("immich", upload=False)
        assert result is False

    @patch("rss_generator.cli.fetch_page_with_playwright")
    @patch("rss_generator.cli.get_parser")
    def test_process_site_returns_false_when_no_articles(self, mock_parser, mock_fetch):
        """Test that process_site returns False when no articles are found."""
        mock_fetch.return_value = "<html>Test</html>"
        mock_parser_func = Mock(return_value=[])
        mock_parser.return_value = mock_parser_func

        result = process_site("immich", upload=False)
        assert result is False

    @patch("rss_generator.cli.fetch_page_with_playwright")
    @patch("rss_generator.cli.get_parser")
    @patch("rss_generator.cli.generate_rss_feed")
    def test_process_site_limits_articles(self, mock_generate, mock_parser, mock_fetch):
        """Test that process_site respects max_articles limit."""
        mock_fetch.return_value = "<html>Test</html>"

        # Create 20 articles
        articles = [
            {"title": f"Article {i}", "link": f"http://example.com/{i}"}
            for i in range(20)
        ]
        mock_parser_func = Mock(return_value=articles)
        mock_parser.return_value = mock_parser_func
        mock_generate.return_value = True

        process_site("immich", upload=False)

        # Check that only max_articles were passed to generate_rss_feed
        # Immich config has max_articles: 10
        call_args = mock_generate.call_args[0]
        articles_passed = call_args[0]
        assert len(articles_passed) <= 10

    @patch("rss_generator.cli.fetch_page_with_playwright")
    @patch("rss_generator.cli.get_parser")
    @patch("rss_generator.cli.generate_rss_feed")
    @patch("rss_generator.cli.check_minio_credentials")
    @patch("rss_generator.cli.upload_to_minio")
    def test_process_site_uploads_when_requested(
        self, mock_upload, mock_check, mock_generate, mock_parser, mock_fetch
    ):
        """Test that process_site uploads when upload=True and credentials exist."""
        mock_fetch.return_value = "<html>Test</html>"
        articles = [{"title": "Test", "link": "http://example.com/test"}]
        mock_parser_func = Mock(return_value=articles)
        mock_parser.return_value = mock_parser_func
        mock_generate.return_value = True
        mock_check.return_value = True
        mock_upload.return_value = True

        result = process_site("immich", upload=True)

        assert result is True
        # Should upload both RSS and XSL
        assert mock_upload.call_count >= 1

    @patch("rss_generator.cli.fetch_page_with_playwright")
    @patch("rss_generator.cli.get_parser")
    @patch("rss_generator.cli.generate_rss_feed")
    @patch("rss_generator.cli.check_minio_credentials")
    def test_process_site_skips_upload_without_credentials(
        self, mock_check, mock_generate, mock_parser, mock_fetch
    ):
        """Test that process_site skips upload when credentials are missing."""
        mock_fetch.return_value = "<html>Test</html>"
        articles = [{"title": "Test", "link": "http://example.com/test"}]
        mock_parser_func = Mock(return_value=articles)
        mock_parser.return_value = mock_parser_func
        mock_generate.return_value = True
        mock_check.return_value = False

        result = process_site("immich", upload=True)

        # Should still succeed even without upload
        assert result is True
