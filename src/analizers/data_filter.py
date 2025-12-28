from urllib.parse import urlparse
from src.analizers import domain_lists


def _netloc(link):
    netloc = urlparse(link).netloc.lower()
    if ":" in netloc:            # strip port
        netloc = netloc.split(":")[0]
    return netloc


def is_in_root_domain(link, root_domain):
    netloc = _netloc(link)
    root_domain = root_domain.lower()
    return netloc == root_domain or netloc.endswith("." + root_domain)


def is_social_media(link):
    netloc = _netloc(link)
    return any(
        netloc == d or netloc.endswith("." + d)
        for d in domain_lists.SOCIAL_GENERIC_DOMAINS
    )

def is_youtube_profile(link):
    netloc = _netloc(link)
    path = urlparse(link).path
    return "youtube.com" in netloc and path.startswith("/@")


def is_multimedia(link):
    netloc = _netloc(link)
    return any(
        netloc == d or netloc.endswith("." + d)
        for d in domain_lists.CDN_DOMAINS
    )

def is_youtube_video(link):
    netloc = _netloc(link)
    path = urlparse(link).path
    return "youtube.com" in netloc and path.startswith("/watch")


def is_app_store(link):
    netloc = _netloc(link)
    return any(
        netloc == d or netloc.endswith("." + d)
        for d in domain_lists.STORE_DOMAINS
    )


def is_news(link):
    netloc = _netloc(link)
    return any(
        netloc == d or netloc.endswith("." + d)
        for d in domain_lists.NEWS_DOMAINS
    )


def is_property(link):
    netloc = _netloc(link)
    return any(
        netloc == d or netloc.endswith("." + d)
        for d in domain_lists.THIRD_PARTY_DOMAINS
    )


def is_legal(link):
    netloc = _netloc(link)
    return any(
        netloc == d or netloc.endswith("." + d)
        for d in domain_lists.REGULATOR_DOMAINS
    )


def is_to_be_ignored(link):
    netloc = _netloc(link)
    return any(
        netloc == d or netloc.endswith("." + d)
        for d in domain_lists.IGNORE_DOMAINS
    )
