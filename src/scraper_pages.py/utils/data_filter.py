from urllib.parse import urlparse


SOCIAL_DOMAIN = {
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "twitter.com",
    "x.com",
    "tiktok.com",
    "threads.net",
    "pinterest.com",
    "github.com",
    "medium.com",
    "farcaster.xyz",
    "notion.site"
}

APP_DOMAIN = {
    "apps.apple.com",
    "play.google.com"
}

NEWS_DOMAIN = {
    "df.cl",
    "emol.com",
    "fintechile.org",
    "energiesmedia.com",
    "chocale.cl",
    "algorand.co",
    "axios.com"
}

PROPERTY_DOMAIN = {
    "airbnb.cl"
}

LEGAL_DOMAIN = {
    "sii.cl",
    "buk.cl",
    "digitaloceanspaces.com"
}

TO_BE_IGNORED = {
    "intercom.com",
    "googleapis.com"
}

MULTIMEDIA_DOMAIN = {
    "intercomcdn.com"
}

YOUTUBE_DOMAIN = "youtube.com"

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
        for d in SOCIAL_DOMAIN
    )

def is_youtube_profile(link):
    netloc = _netloc(link)
    path = urlparse(link).path
    return netloc == YOUTUBE_DOMAIN and path.startswith("/@")


def is_multimedia(link):
    netloc = _netloc(link)
    return any(
        netloc == d or netloc.endswith("." + d)
        for d in MULTIMEDIA_DOMAIN
    )

def is_youtube_video(link):
    netloc = _netloc(link)
    path = urlparse(link).path
    return netloc == YOUTUBE_DOMAIN and path.startswith("/watch")


def is_app_store(link):
    netloc = _netloc(link)
    return any(
        netloc == d or netloc.endswith("." + d)
        for d in APP_DOMAIN
    )


def is_news(link):
    netloc = _netloc(link)
    return any(
        netloc == d or netloc.endswith("." + d)
        for d in NEWS_DOMAIN
    )


def is_property(link):
    netloc = _netloc(link)
    return any(
        netloc == d or netloc.endswith("." + d)
        for d in PROPERTY_DOMAIN
    )


def is_legal(link):
    netloc = _netloc(link)
    return any(
        netloc == d or netloc.endswith("." + d)
        for d in LEGAL_DOMAIN
    )


def is_to_be_ignored(link):
    netloc = _netloc(link)
    return any(
        netloc == d or netloc.endswith("." + d)
        for d in TO_BE_IGNORED
    )