"""Site configurations for RSS feed generation."""

SITES = {
    "immich": {
        "id": "immich",
        "name": "Immich Blog",
        "url": "https://immich.app/blog",
        "output_file": "immich_blog_feed.xml",
        "parser": "parse_immich",
        "language": "en",
        "description": "Latest posts from the Immich blog",
        "email": "noreply@immich.app",
        "wait_time": 2000,
        "max_articles": 10,  # Limit to most recent articles
    },
    "diariodominho": {
        "id": "diariodominho",
        "name": "Diário do Minho",
        "url": "https://www.diariodominho.pt/",
        "output_file": "diariodominho_feed.xml",
        "parser": "parse_diariodominho",
        "language": "pt",
        "description": "Últimas notícias do Diário do Minho",
        "email": "noreply@diariodominho.pt",
        "wait_time": 3000,
        "max_articles": 10,  # Limit to most recent articles
    },
    "newalbumreleases_metal": {
        "id": "newalbumreleases_metal",
        "name": "New Album Releases - Metal",
        "url": "https://www.newalbumreleases.cc/category/metal/",
        "output_file": "newalbumreleases_metal_feed.xml",
        "parser": "parse_newalbumreleases_metal",
        "language": "en",
        "description": "Latest metal album releases from NewAlbumReleases.cc",
        "email": "noreply@newalbumreleases.cc",
        "wait_time": 2000,
        "max_articles": 20,  # Limit to most recent albums
    },
}


def get_site_config(site_id: str) -> dict:
    """Get configuration for a specific site."""
    return SITES.get(site_id)


def list_sites() -> list[str]:
    """Get list of all available site IDs."""
    return list(SITES.keys())


def get_all_sites() -> dict:
    """Get all site configurations."""
    return SITES
