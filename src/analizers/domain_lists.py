"""
Centralized lists of domains and patterns for URL classification and filtering.
Used by RoleClassifier, DataFilter and other analyzers.
"""

# SOCIAL MEDIA
SOCIAL_PROFILE_DOMAINS = [
    "linkedin.com/company/", "linkedin.com/in/",
    "instagram.com/", "youtube.com/@", "youtube.com/c/", "youtube.com/channel/",
    "twitter.com/", "x.com/",
    "facebook.com/", "fb.com/",
    "tiktok.com/@",
    "github.com/",
    "medium.com/@",
    "pinterest.com/",
    "spotify.com/",
    "telegram.me/", "t.me/",
    "discord.gg/", "discord.com/",
    "wa.me/", "whatsapp.com/",
    "threads.net/", "farcaster.xyz/", "notion.site/"
]

SOCIAL_GENERIC_DOMAINS = [
    "linkedin.com", "instagram.com", "youtube.com", "twitter.com", "x.com",
    "facebook.com", "fb.com", "tiktok.com", "github.com", "medium.com", 
    "pinterest.com", "spotify.com", "telegram.me", "t.me", "discord.gg", 
    "discord.com", "wa.me", "whatsapp.com", "threads.net", "farcaster.xyz", 
    "notion.site"
]

SOCIAL_CONTENT_PATTERNS = [
    "/post/", "/video/", "/watch", "/status/", "/p/", "/reel/",
    "/photo/", "/album/", "/story/"
]

# APP STORES
STORE_DOMAINS = [
    "play.google.com",
    "play.google.com/store",
    "apps.apple.com",
    "microsoft.com/store",
    "galaxy.store",
    "appgallery.huawei.com"
]

# REGULATORS / LEGAL
REGULATOR_DOMAINS = [
    "register.fca.org.uk", "fca.org.uk",
    "sec.gov", "finra.org",
    "cftc.gov", "fincen.gov",
    "cnmv.es", "cmf.cl",
    "consob.it", "amf-france.org",
    "bafin.de", "fsma.be",
    "fsra.ae", "dfsa.ae", "sca.gov.ae",
    "vara.ae", "ecsp.com",
    "sii.cl"
]

REGULATOR_PROFILE_INDICATORS = ["firm", "register", "company", "entity", "license"]

# NEWS AND MEDIA
NEWS_DOMAINS = [
    "bbc.com", "cnn.com", "reuters.com", "bloomberg.com",
    "forbes.com", "techcrunch.com", "businessinsider.com",
    "wsj.com", "nytimes.com", "theguardian.com",
    "emol.com", "latercera.com", "elmostrador.cl",
    "df.cl", "t13.cl", "nexnews.cl", "fintechile.org",
    "energiesmedia.com", "chocale.cl", "axios.com",
    "pauta.cl", "theclinic.cl"
]

# THIRD PARTY DIRECTORIES
THIRD_PARTY_DOMAINS = [
    "crunchbase.com", "trustpilot.com", "thecrowdspace.com",
    "producthunt.com", "g2.com", "capterra.com", "airbnb.cl"
]

# WEB UTILITIES / RESOURCES / MULTIMEDIA
IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".ico"]
VIDEO_EXTENSIONS = [".mp4", ".webm", ".avi", ".mov", ".mkv"]
RESOURCE_PATHS = ["/assets/", "/static/", "/images/", "/img/", "/css/", "/js/", "/fonts/"]
CDN_DOMAINS = [
    "cdn.", "static.", "assets.", "media.", 
    "intercomcdn.com", "digitaloceanspaces.com"
]

# DOCUMENTS
DOCUMENT_EXTENSIONS = [
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".txt", ".csv", ".zip", ".rar", ".7z"
]

# TO BE IGNORED
IGNORE_DOMAINS = [
    "intercom.com",
    "googleapis.com"
]
