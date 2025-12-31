import re
import requests
from urllib.parse import urlparse, parse_qs, urlunparse, quote
from typing import List, Dict, Optional, Set

# Timeout settings for requests
TIMEOUT = 10
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def analyze_store_links(urls: List[str]) -> List[str]:
    """
    Analyzes a list of URLs (presumably store listings), resolves redirects,
    filters for valid Google Play and Apple App Store links, and returns
    a list containing the optimal link for each platform (max 1 per platform).
    
    Prioritizes:
    - Direct App Store/Play Store links over search results.
    - English (us/en) versions over other languages.
    """
    
    google_play_candidates = []
    apple_store_candidates = []
    
    # Pre-compiled regex for extracting IDs
    # Google Play: id=<package_name>
    play_id_pattern = re.compile(r'id=([a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)+)')
    # Apple App Store: /id<numbers> or just id<numbers>
    apple_id_pattern = re.compile(r'id(\d+)')

    processed_urls = set()
    
    # Blacklist of generic apps (Authenticator, Authy, etc) that should not be selected
    BLACKLISTED_IDS = {
        'com.google.android.apps.authenticator2', # Google Authenticator (Android)
        '388497605',                              # Google Authenticator (iOS)
        'com.authy.authy',                        # Authy (Android)
        '494168017'                               # Authy (iOS)
    }

    for url in urls:
        if not url:
            continue
        
        # Clean URL of potential JSON artifacts or weird formatting
        url = url.strip().replace('\\', '').replace('"', '').replace("'", "")
        
        if url in processed_urls:
            continue
        processed_urls.add(url)

        # Attempt to resolve if it's not clearly a store link or looks like a tracking link
        # This now returns a list because a single tracking link could contain multiple store links (iOS/Android)
        resolved_urls = _resolve_urls(url)
        
        for final_url in resolved_urls:
            parsed = urlparse(final_url)
            domain = parsed.netloc.lower()

            if 'play.google.com' in domain:
                # Check if it is a details link
                if '/store/apps/details' in parsed.path:
                    match = play_id_pattern.search(parsed.query)
                    if match:
                        package_id = match.group(1)
                        if package_id in BLACKLISTED_IDS:
                            continue
                        
                        # Extract existing params to preserve region if present
                        qs = parse_qs(parsed.query)
                        # We default to US/en if NOT present, but if present we keep them.
                        # User wants to avoid forcing locations "without criterion".
                        # But also wants to favor US if available.
                        # Scoring logic handles priority. Here we ensure the URL reflects the source.
                        existing_gl = qs.get('gl', [])
                        current_hl = qs.get('hl', ['en'])[0]

                        normalized = f"https://play.google.com/store/apps/details?id={package_id}&hl={current_hl}"
                        if existing_gl:
                            normalized += f"&gl={existing_gl[0]}"
                        
                        # Store tuple (priority, url, original_lang_score)
                        # Priority: 1 (Direct ID)
                        # Lang Score: Check original params for language preference
                        lang_score = _get_lang_score_google(parsed.query)
                        google_play_candidates.append({'id': package_id, 'url': normalized, 'score': lang_score})
                elif '/store/search' in parsed.path:
                    # It's a search link. Only useful if we absolutely find nothing else, 
                    # but user asked for "link de la aplicacion".
                    pass
                    
            elif 'apps.apple.com' in domain or 'itunes.apple.com' in domain:
                # Check for ID
                # URL structure: https://apps.apple.com/us/app/name/id123456
                # or https://apps.apple.com/app/id123456
                match = apple_id_pattern.search(parsed.path) or apple_id_pattern.search(parsed.query)
                if match:
                    app_id = match.group(1)
                    if app_id in BLACKLISTED_IDS:
                        continue
                    
                    # Determine "name" slug if present to correct the URL structure
                    name_slug = "app" # Default
                    path_parts = parsed.path.strip('/').split('/')
                    
                    # Check for country code at start of path
                    country_code = 'us' # default fallback
                    # Heuristic: if first part is len 2, treat as country.
                    if len(path_parts) > 0 and len(path_parts[0]) == 2:
                        country_code = path_parts[0]
                    
                    if 'app' in path_parts:
                        idx = path_parts.index('app')
                        if idx + 1 < len(path_parts) and not path_parts[idx+1].startswith('id'):
                             name_slug = path_parts[idx+1]

                    # Normalize using the DETECTED country code, do not force US unless it was US or missing.
                    if name_slug != "app":
                        normalized = f"https://apps.apple.com/{country_code}/app/{name_slug}/id{app_id}"
                    else:
                        normalized = f"https://apps.apple.com/{country_code}/app/id{app_id}"

                    lang_score = _get_lang_score_apple(parsed.path, parsed.query)
                    apple_store_candidates.append({'id': app_id, 'url': normalized, 'score': lang_score})

    # Select best candidates
    optimal_links = []
    
    if google_play_candidates:
        grouped = {}
        for c in google_play_candidates:
            if c['id'] not in grouped:
                grouped[c['id']] = c
            else:
                if c['score'] < grouped[c['id']]['score']:
                    grouped[c['id']] = c
        
        # Simple heuristic: Just take the first ID found.
        best_play = list(grouped.values())[0]
        optimal_links.append(best_play['url'])

    if apple_store_candidates:
        grouped = {}
        for c in apple_store_candidates:
            if c['id'] not in grouped:
                grouped[c['id']] = c
            else:
                if c['score'] < grouped[c['id']]['score']:
                    grouped[c['id']] = c
        
        best_apple = list(grouped.values())[0]
        optimal_links.append(best_apple['url'])

    return optimal_links

def verify_links_existence(urls: List[str]) -> List[str]:
    """
    Verifies a list of URLs by making HTTP requests.
    Returns only the URLs that respond with a successful status code (200-299).
    Filters out 404s and other errors.
    """
    valid_links = []
    
    # Use a session for connection pooling
    session = requests.Session()
    session.headers.update(headers)
    
    print(f"Verifying existence of {len(urls)} links...")
    
    for url in urls:
        if not url:
            continue
            
        try:
            # Try HEAD first for speed. allow_redirects=True is key for some store links
            resp = session.head(url, timeout=5, allow_redirects=True)
            
            # If 405 Method Not Allowed, fallback to GET
            if resp.status_code == 405:
                resp = session.get(url, timeout=5, stream=True, allow_redirects=True)
                
            if 200 <= resp.status_code < 300:
                valid_links.append(url)
            else:
                print(f"  [Dropped] {url} (Status: {resp.status_code})")
                
        except requests.RequestException:
             # Fallback to GET if HEAD failed with network error
            try:
                resp = session.get(url, timeout=5, stream=True, allow_redirects=True)
                if 200 <= resp.status_code < 300:
                    valid_links.append(url)
                else:
                    print(f"  [Dropped] {url} (Status: {resp.status_code})")
            except Exception as e:
                print(f"  [Dropped] {url} (Error: {str(e)})")
                
    return valid_links

def format_store_links_for_model(urls: List[str]) -> List[Dict[str, str]]:
    """
    Takes a list of valid store URLs and formats them for the companies data model.
    Output structure:
    [
        {"url": "...", "store": "google_play"},
        {"url": "...", "store": "apple_store"}
    ]
    """
    formatted_links = []
    
    for url in urls:
        if not url:
            continue
            
        store_type = None
        if 'play.google.com' in url:
            store_type = "google_play"
        elif 'apps.apple.com' in url or 'itunes.apple.com' in url:
            store_type = "apple_store"
            
        if store_type:
            formatted_links.append({
                "url": url,
                "store": store_type
            })
            
    return formatted_links

def _resolve_urls(url: str) -> List[str]:
    """
    Follows redirects to find the final URL(s).
    Returns a list because a single input might unpack into multiple store links.
    """
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    
    # helper to find embedded URLs in query params (fallback or optimization)
    nested = _extract_nested_store_urls(url)
    if nested:
        return nested

    # If already a store domain, return as is (checking after nested in case a store link has params?? 
    # Unlikely to have nested store links inside a store link, but safe order)
    if 'play.google.com' in domain or 'apps.apple.com' in domain or 'itunes.apple.com' in domain:
        return [url]

    # List of known tracking/redirect domains or common shorteners
    tracking_domains = ['adjust.com', 'onelink.me', 'bit.ly', 'goo.gl', 't.co', 'app.link', 'branch.io', 'appsflyer.com', 'firebaseio.com', 'google.com']

    pass_heuristic = False
    for td in tracking_domains:
        if td in domain:
            pass_heuristic = True
            break
            
    if not pass_heuristic:
        return [url]

    try:
        # Try HEAD first
        try:
            resp = requests.head(url, headers=headers, allow_redirects=True, timeout=5)
            if _is_store_url(resp.url):
                return [resp.url]
        except Exception:
            pass # Fallback to GET
            
        # Try GET with stream to avoid downloading big content
        resp = requests.get(url, headers=headers, stream=True, allow_redirects=True, timeout=5)
        if _is_store_url(resp.url):
            return [resp.url]
    except Exception as e:
        pass

    return [url]

def _extract_nested_store_urls(url: str) -> List[str]:
    """
    Extracts potential store URLs embedded in query parameters.
    Returns all unique found store URLs.
    """
    found = set()
    try:
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        
        # Common parameters that might hold a target URL
        candidates_params = ['url', 'af_web_dp', 'af_dp', 'redirect', 'redirect_macos', 'redirect_windows', 'link', 'android_url', 'ios_url']
        
        for param in candidates_params:
            if param in qs:
                for val in qs[param]:
                    if _is_store_url(val):
                        found.add(val)
    except Exception:
        pass
    
    return list(found)

def _is_store_url(url: str) -> bool:

    try:
        domain = urlparse(url).netloc.lower()
        return 'play.google.com' in domain or 'apps.apple.com' in domain or 'itunes.apple.com' in domain
    except:
        return False

def _get_lang_score_google(query_string: str) -> int:
    """
    Returns a score for language priority.
    0: English/US (hl=en, gl=US or similar)
    1: English (hl=en)
    2: Spanish (hl=es)
    3: Others
    4: None specified
    """
    qs = parse_qs(query_string)
    hl = qs.get('hl', [''])[0].lower()
    gl = qs.get('gl', [''])[0].lower()
    
    if 'en' in hl:
        if 'us' in gl:
            return 0
        return 1
    if 'es' in hl:
        return 2
    if hl:
        return 3
    return 4

def _get_lang_score_apple(path: str, query_string: str) -> int:
    """
    Apple Store: /us/app/... or l=en parameter
    """
    # Check path for country code
    path_parts = path.split('/')
    country = ''
    if len(path_parts) > 1 and len(path_parts[1]) == 2:
        country = path_parts[1].lower()
        
    qs = parse_qs(query_string)
    l_param = qs.get('l', [''])[0].lower()
    
    if country == 'us' or 'en' in l_param:
        return 0
    if country == 'gb' or country == 'uk' or country == 'en':
        return 1
    if 'es' in country or 'es' in l_param:
        return 2
    if country:
        return 3
    return 4
