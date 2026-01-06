import re
import requests
import logging
from urllib.parse import urlparse, parse_qs, urlunparse, urlencode
from typing import List, Dict, Any, Optional, Set
from src.DB.platforms_querys import get_platform_by_slug, upsert_social_profile

# Timeout for requests
TIMEOUT = 10
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# Supported platforms mapping (domain keyword -> platform name)
# Ordered by priority or specificity if needed
PLATFORM_MAPPING = {
    "linkedin.com": "linkedin",
    "twitter.com": "X",
    "x.com": "X",
    "facebook.com": "facebook",
    "fb.com": "facebook",
    "instagram.com": "instagram",
    "instagr.am": "instagram",
    "youtube.com": "youtube",
    "youtu.be": "youtube",
    "t.me": "telegram",
    "telegram.me": "telegram",
    "discord.com": "discord",
    "discord.gg": "discord",
    "tiktok.com": "tiktok",
    "pinterest.com": "pinterest",
    "medium.com": "medium",
    "reddit.com": "reddit",
    "wa.me": "whatsapp",
    "whatsapp.com": "whatsapp"
}

def analyze_and_store_social_profiles(slug: str) -> Dict[str, Any]:
    """
    Main function to find, analyze, verify, and store social profiles for a company.
    
    Steps:
    1. Get candidates from DB (dataSources w/ role='official_social_profile' + theCrowdSpace.sidebar.socials).
    2. Clean and Identify Platform for each URL.
    3. Deduplicate.
    4. Verify existence (HTTP check).
    5. Check for duplicates per platform (Warning).
    6. Store in DB.
    """
    
    # 1. Get Candidates
    candidates = _get_candidates(slug)
    
    if not candidates:
        logging.info(f"[{slug}] No candidates found.")
        return {"candidates_found": 0, "valid_profiles": 0, "stored": 0}

    # 2. Process Candidates (Clean + Identify)
    processed_list = []
    seen_urls = set()

    for url in candidates:
        # Basic cleanup
        clean_url = _clean_url(url)
        if not clean_url:
            continue
            
        # Identify Platform
        platform = _identify_platform(clean_url)
        if not platform:
            # If we strictly only want identifiable social profiles, skip.
            # Requirement says: "Definir el 'platform' de cada url." implies we need it.
            # If null, maybe generic or skip? Usually skip if not "social".
            continue

        # Standardize X
        if platform == "X":
            clean_url = _standardize_twitter_url(clean_url)
            
        # Dedupe
        if clean_url in seen_urls:
            continue
        seen_urls.add(clean_url)
        
        processed_list.append({
            "url": clean_url,
            "platform": platform
        })

    # 3. Verify Existence
    valid_profiles = []
    
    # We verify unique URLs
    urls_to_verify = [p['url'] for p in processed_list]
    verified_urls = _verify_urls_existence(urls_to_verify)
    
    for p in processed_list:
        if p['url'] in verified_urls:
            valid_profiles.append(p)

    # 3.5 Resolve LinkedIn Redirects
    valid_profiles = _resolve_linkedin_redirects(valid_profiles)

    # Re-Dedupe after resolution (in case multiple inputs resolved to same final)
    # We need to re-dedupe based on URL only
    unique_map = {}
    for p in valid_profiles:
        unique_map[p['url']] = p
    valid_profiles = list(unique_map.values())

    # 4. Dictionary for checking duplicates per platform
    platform_counts = {}
    for p in valid_profiles:
        plat = p['platform']
        platform_counts[plat] = platform_counts.get(plat, 0) + 1
        
    # Warning if multiple
    for plat, count in platform_counts.items():
        if count > 1:
            logging.warning(f"Company {slug} has multiple {plat} profiles: {count}")

    # 5. Store in DB
    stored_count = 0
    for p in valid_profiles:
        # upsert_social_profile(slug, url, platform)
        upsert_social_profile(slug, p['url'], p['platform'])
        stored_count += 1
        
    return {
        "candidates_found": len(candidates),
        "valid_profiles": len(valid_profiles),
        "stored": stored_count
    }

def _get_candidates(slug: str) -> List[str]:
    """
    Retrieves candidate URLs from:
    - dataSources (role='official_social_profile')
    - theCrowdSpace -> sidebar -> socials
    """
    doc = get_platform_by_slug(slug, {"dataSources": 1, "theCrowdSpace": 1})
    if not doc:
        return []
        
    candidates = []
    
    # From dataSources
    data_sources = doc.get("dataSources") or []
    if isinstance(data_sources, list):
        for ds in data_sources:
            if isinstance(ds, dict) and ds.get("role") == "official_social_profile":
                u = ds.get("url")
                if u:
                    candidates.append(u)
                    
    # From theCrowdSpace
    tcs = doc.get("theCrowdSpace") or {}
    sidebar = tcs.get("sidebar") or {}
    socials = sidebar.get("socials") or []
    
    if isinstance(socials, list):
        for s in socials:
            if isinstance(s, str) and s.strip():
                candidates.append(s)
                
    return candidates

def _identify_platform(url: str) -> Optional[str]:
    """
    Identifies the platform based on the domain.
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
            
        # Strict check (exact match or subdomain)
        for key, plat in PLATFORM_MAPPING.items():
            if domain == key or domain.endswith("." + key):
                return plat
                
        return None
    except Exception:
        return None

def _clean_url(url: str) -> Optional[str]:
    """
    Cleans the URL:
    - Strips query params (except for critical ones like id, but most social profiles rely on path).
    - Removes trailing slashes.
    - Removes sub-paths like /posts, /jobs, /mycompany, /videos if they are secondary views.
    """
    if not url:
        return None
        
    # Basic sanitize
    url = url.strip()
    
    try:
        parsed = urlparse(url)
    except Exception:
        return None
        
    scheme = parsed.scheme
    netloc = parsed.netloc.lower()
    path = parsed.path
    query = parsed.query
    
    # Exceptions where query is important
    # Facebook profile.php
    if "facebook.com" in netloc and "profile.php" in path:
        # Keep 'id' param
        qs = parse_qs(query)
        if 'id' in qs:
            new_query = urlencode({'id': qs['id'][0]})
            return urlunparse((scheme, netloc, path, '', new_query, ''))
        return url # fallback
        
    # Whatsapp api
    if "api.whatsapp.com" in netloc or "wa.me" in netloc:
        # Keep phone/text
        return url
        
    # Youtube watch?v= (Wait, watch is a video, not profile. But if it's there...)
    # We want profiles. youtube.com/watch?v=... is NOT a profile. 
    # But for the sake of "cleaning", we strip params generally.
    
    # General Rule: Strip query params for profiles
    new_query = ""
    
    # Path Cleanups
    # Remove trailing slash
    if path.endswith('/'):
        path = path[:-1]
        
    # Remove common non-profile suffixes
    # Examples: /posts, /jobs, /videos, /about, /mycompany
    parts = path.split('/')
    if parts:
        last_part = parts[-1].lower()
        # List of suffixes to strip
        suffixes_to_strip = {'posts', 'jobs', 'videos', 'about', 'mycompany', 'reviews', 'photos', 'featured'}
        
        if last_part in suffixes_to_strip:
            # Remove last part
            path = "/".join(parts[:-1])
            
    # Rebuild
    # Remove subdomains for known platforms (e.g. br.linkedin.com -> linkedin.com, www.instagram.com -> instagram.com)
    # This effectively handles www, country codes, and other prefixes.
    # We iterate sorted by length desc to match specific domains first if any overlap exists (though keys are mostly unique)
    sorted_keys = sorted(PLATFORM_MAPPING.keys(), key=len, reverse=True)
    for key in sorted_keys:
        if netloc == key or netloc.endswith("." + key):
            netloc = key
            break
    
    # Enforce HTTPS
    if scheme in ['http', 'https', '']:
        scheme = 'https'

    # Youtube Cleanups
    if netloc == "youtube.com" or netloc == "youtu.be":
        if path.startswith("/c/"):
            path = "/@" + path[3:]
            
    clean = urlunparse((scheme, netloc, path, '', new_query, ''))
    
    # Enforce lowercase
    return clean.lower()

def _standardize_twitter_url(url: str) -> str:
    """
    Changes twitter.com to x.com
    """
    parsed = urlparse(url)
    if "twitter.com" in parsed.netloc.lower():
        new_netloc = parsed.netloc.lower().replace("twitter.com", "x.com")
        return urlunparse((parsed.scheme, new_netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))
    return url

def _verify_urls_existence(urls: List[str]) -> Set[str]:
    """
    Verifies a list of URLs using HEAD/GET checks.
    Returns a set of valid URLs (200-299).
    """
    valid = set()
    session = requests.Session()
    session.headers.update(HEADERS)
    
    for url in urls:
        # Identify if we need simple verification or specific
        try:
            # Try HEAD
            resp = session.head(url, timeout=5, allow_redirects=True)
            if resp.status_code == 405: # Method not allowed
                resp = session.get(url, timeout=5, stream=True, allow_redirects=True)
                
            if 200 <= resp.status_code < 300: # OR 403/999 (LinkedIn often blocks bots but link exists)?
                # IMPORTANT: Social networks (LinkedIn, Facebook, Instagram) OFTEN return 999 or 403 to bots aka scrapers.
                # If we get 403/999, it likely EXISTS but we are blocked.
                # If we get 404, it definitely doesn't exist.
                # User requirement: "Si el link no existe (por ejemplo error 404) eliminar".
                # So we should be careful about 429/403/999.
                # For safety, I will only exclude 404 and maybe 410.
                valid.add(url)
            elif resp.status_code in [403, 429, 999]:
                # Assume valid if blocked, because we found it in our DB/source which suggests it was once valid.
                # We only want to prune dead links (404).
                # Logging this nuance might be good.
                valid.add(url) 
            else:
                logging.debug(f"  [Verification Fail] {url} -> {resp.status_code}")
                
        except requests.RequestException as e:
            logging.warning(f"  [Verification Error] {url} -> {e}")
            # If connection error, usually we can't verify. 
            # If DNS error, it's invalid.
            # For now, let's treat requests component errors as failures to verify -> remove?
            # Or keep? Safe to remove if we want high quality.
            pass
            
    return valid

def _resolve_linkedin_redirects(profiles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Follows redirects for LinkedIn profiles to find the canonical URL.
    E.g. linkedin.com/company/foo often redirects to linkedin.com/company/foo-inc or similar.
    """
    resolved_profiles = []
    session = requests.Session()
    session.headers.update(HEADERS)

    for p in profiles:
        if p['platform'] == 'linkedin':
            try:
                # We specifically want to follow redirects
                resp = session.get(p['url'], timeout=10, allow_redirects=True)
                
                # Check status
                if 200 <= resp.status_code < 300:
                    final_url = resp.url
                    # Clean the final URL to ensure it matches our standards (lowercase, no www, etc)
                    clean_final = _clean_url(final_url)
                    
                    if clean_final and clean_final != p['url']:
                        # Logging happens at debug level to avoid clutter unless we want to see it
                        logging.info(f"  [LinkedIn Redirect] {p['url']} -> {clean_final}")
                        p['url'] = clean_final
                        
                else:
                    # If blocked or error, keep original
                    pass
                    
            except Exception as e:
                # On error, keep original
                logging.debug(f"  [LinkedIn Resolve Error] {p['url']} -> {e}")
                pass
        
        resolved_profiles.append(p)
    
    return resolved_profiles
