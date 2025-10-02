"""Tests for sites configuration module."""

from rss_generator.sites import (
    SITES,
    get_site_config,
    list_sites,
    get_all_sites,
)


class TestSitesConfiguration:
    """Tests for site configuration data."""

    def test_sites_dict_exists(self):
        """Test that SITES dictionary exists and is not empty."""
        assert SITES is not None
        assert isinstance(SITES, dict)
        assert len(SITES) > 0

    def test_all_sites_have_required_fields(self):
        """Test that all site configurations have required fields."""
        required_fields = [
            "id",
            "name",
            "url",
            "output_file",
            "parser",
            "language",
            "description",
            "email",
        ]

        for site_id, config in SITES.items():
            for field in required_fields:
                assert field in config, (
                    f"Site '{site_id}' missing required field '{field}'"
                )

    def test_site_ids_match_keys(self):
        """Test that site 'id' field matches the dictionary key."""
        for site_id, config in SITES.items():
            assert config["id"] == site_id

    def test_site_urls_are_valid(self):
        """Test that site URLs are valid HTTP(S) URLs."""
        for site_id, config in SITES.items():
            url = config["url"]
            assert url.startswith("http://") or url.startswith("https://"), (
                f"Site '{site_id}' has invalid URL: {url}"
            )

    def test_site_parsers_are_strings(self):
        """Test that parser field is a string."""
        for site_id, config in SITES.items():
            assert isinstance(config["parser"], str), (
                f"Site '{site_id}' parser is not a string"
            )

    def test_site_languages_are_valid(self):
        """Test that language codes are lowercase."""
        for site_id, config in SITES.items():
            lang = config["language"]
            assert lang.islower(), f"Site '{site_id}' language should be lowercase"
            assert len(lang) == 2, f"Site '{site_id}' language should be 2-letter code"

    def test_output_files_have_xml_extension(self):
        """Test that output files have .xml extension."""
        for site_id, config in SITES.items():
            output_file = config["output_file"]
            assert output_file.endswith(".xml"), (
                f"Site '{site_id}' output_file should end with .xml"
            )

    def test_wait_time_is_positive(self):
        """Test that wait_time is positive if specified."""
        for site_id, config in SITES.items():
            if "wait_time" in config:
                assert config["wait_time"] > 0, (
                    f"Site '{site_id}' wait_time should be positive"
                )

    def test_max_articles_is_positive(self):
        """Test that max_articles is positive if specified."""
        for site_id, config in SITES.items():
            if "max_articles" in config:
                assert config["max_articles"] > 0, (
                    f"Site '{site_id}' max_articles should be positive"
                )


class TestGetSiteConfig:
    """Tests for get_site_config function."""

    def test_returns_config_for_valid_site(self):
        """Test that function returns config for valid site ID."""
        # Get first site ID from SITES
        site_id = list(SITES.keys())[0]
        config = get_site_config(site_id)

        assert config is not None
        assert isinstance(config, dict)
        assert config["id"] == site_id

    def test_returns_none_for_invalid_site(self):
        """Test that function returns None for invalid site ID."""
        config = get_site_config("nonexistent_site")
        assert config is None

    def test_returns_immich_config(self):
        """Test that immich configuration can be retrieved."""
        config = get_site_config("immich")
        assert config is not None
        assert config["name"] == "Immich Blog"
        assert "immich.app" in config["url"]

    def test_returns_diariodominho_config(self):
        """Test that diariodominho configuration can be retrieved."""
        config = get_site_config("diariodominho")
        assert config is not None
        assert "Diário do Minho" in config["name"]
        assert "diariodominho.pt" in config["url"]


class TestListSites:
    """Tests for list_sites function."""

    def test_returns_list_of_site_ids(self):
        """Test that function returns a list of site IDs."""
        sites = list_sites()
        assert isinstance(sites, list)
        assert len(sites) > 0

    def test_returns_all_site_ids(self):
        """Test that function returns all site IDs from SITES."""
        sites = list_sites()
        assert len(sites) == len(SITES)
        for site_id in sites:
            assert site_id in SITES

    def test_includes_immich(self):
        """Test that immich is in the list."""
        sites = list_sites()
        assert "immich" in sites

    def test_includes_diariodominho(self):
        """Test that diariodominho is in the list."""
        sites = list_sites()
        assert "diariodominho" in sites


class TestGetAllSites:
    """Tests for get_all_sites function."""

    def test_returns_dict(self):
        """Test that function returns a dictionary."""
        all_sites = get_all_sites()
        assert isinstance(all_sites, dict)

    def test_returns_all_sites(self):
        """Test that function returns all sites."""
        all_sites = get_all_sites()
        assert len(all_sites) == len(SITES)

    def test_returns_same_as_sites_constant(self):
        """Test that function returns the SITES constant."""
        all_sites = get_all_sites()
        assert all_sites == SITES
