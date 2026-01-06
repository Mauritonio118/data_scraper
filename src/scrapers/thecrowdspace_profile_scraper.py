import requests
from bs4 import BeautifulSoup, Tag
from typing import Dict, Any, Optional, List
from datetime import datetime
import re

# Adjust import based on project structure
try:
    from src.scrapers.utils.html_spliter_head_header_main_footer import html_spliter_head_header_main_footer
except ImportError:
    # Fallback for direct execution or different path structure
    import sys
    import os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))
    from src.scrapers.utils.html_spliter_head_header_main_footer import html_spliter_head_header_main_footer

def resolve_final_url(url: str) -> str:
    """
    Follows redirects to get the final URL.
    Returns the original URL if an error occurs.
    """
    if not url:
        return url
        
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        # Use stream=True to avoid downloading large content
        response = requests.get(url, headers=headers, allow_redirects=True, stream=True, timeout=15)
        return response.url
    except requests.RequestException:
        return url

def thecrowdspace_profile_scraper(url: str, html_content: Optional[str] = None) -> Dict[str, Any]:
    """
    Scrapes a company profile from TheCrowdSpace.
    
    Args:
        url: The URL of the company profile.
        html_content: Optional raw HTML content to parse (avoids HTTP request if provided).
        
    Returns:
        A dictionary with the extracted data formatted according to the platforms_model.
    """
    
    if html_content is None:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            html_content = response.text
        except requests.RequestException as e:
            print(f"Error fetching URL {url}: {e}")
            return {}

    # Split HTML to get main content
    sections = html_spliter_head_header_main_footer(html_content)
    main_html = sections.get('main', '')
    
    if not main_html:
        # Fallback if split fails or empty
        main_html = html_content

    soup = BeautifulSoup(main_html, 'lxml')
    
    data: Dict[str, Any] = {
        "theCrowdSpaceUrl": url,
        "lastScrapedAt": datetime.utcnow().isoformat() + "Z"
    }
    
    # helper for text extraction
    def get_text(element: Optional[Tag]) -> Optional[str]:
        return element.get_text(strip=True) if element else None

    # ===================================
    # Hero Section
    # ===================================
    hero_data = {}
    
    # Logo
    logo_block = soup.select_one('.company-profile-hero__logo-block.single img')
    if logo_block:
        urls = set()
        # Main src
        src = logo_block.get('src')
        if src:
            urls.add(src)
            
        # Srcset
        srcset = logo_block.get('srcset')
        if srcset:
            parts = srcset.split(',')
            for part in parts:
                trimmed = part.strip()
                if trimmed:
                    url_part = trimmed.split(' ')[0]
                    if url_part:
                        urls.add(url_part)
        
        if urls:
            hero_data['logoUrls'] = list(urls)
        
    # ECSP License
    hero_data['ecspLicense'] = bool(soup.select_one('.ecsp'))
    
    # Verified
    hero_data['isVerified'] = bool(soup.select_one('.listing-card__company-verified'))
    
    # Description
    desc_elem = soup.select_one('.company-profile-hero__description')
    if desc_elem:
        hero_data['description'] = get_text(desc_elem)
        
    # Industries
    industries_container = soup.select_one('.company-profile-hero__industries')
    if industries_container:
        industries = [get_text(tag) for tag in industries_container.find_all(['a', 'span'])]
        industries = [i for i in industries if i]
        if industries:
            hero_data['industries'] = industries

    if hero_data:
        data['hero'] = hero_data

    # ===================================
    # Content / Tabs Body
    # ===================================
    content_data = {}
    tabs_body = soup.select_one('.tabs-body')
    
    if tabs_body:
        # Top Cards
        top_cards = []
        for card in tabs_body.select('.content-top-card'):
            card_texts = list(card.stripped_strings)
            if len(card_texts) >= 2:
                top_cards.append({
                    "title": card_texts[0],
                    "value": " ".join(card_texts[1:])
                })
        if top_cards:
            content_data['topCards'] = top_cards
            
        # Descriptions
        descriptions = []
        for desc_block in tabs_body.select('.title-description'):
            # Title is in div.title
            title_node = desc_block.select_one('.title')
            title_text = get_text(title_node)
            
            # Description is in div.description, usually paragraphs
            desc_node = desc_block.select_one('.description')
            if desc_node:
                paragraphs = [p.get_text(strip=True) for p in desc_node.find_all('p')]
                if paragraphs:
                    desc_text = "\n".join(paragraphs)
                else:
                    desc_text = get_text(desc_node)
            else:
                desc_text = None

            if title_text and desc_text:
                descriptions.append({
                    "title": title_text,
                    "text": desc_text
                })
        if descriptions:
            content_data['descriptions'] = descriptions

    if content_data:
        data['content'] = content_data
        
    # ===================================
    # Sidebar
    # ===================================
    sidebar_data = {}
    sidebar = soup.select_one('.sidebar')
    
    if sidebar:
        # Stats
        stats_data = {}
        # Identify specific "Operates in" row to handle separately or inside stats
        operates_in_row = None
        
        for stat_row in sidebar.select('.stats.sidebar-section .sidebar-item, .stats.sidebar-section li, .stats.sidebar-section > div'): 
            row_texts = list(stat_row.stripped_strings)
            if len(row_texts) >= 2:
                key = row_texts[0].strip(':')
                
                if "operates in" in key.lower():
                    operates_in_row = stat_row
                    continue 
                
                value = row_texts[1:]
                clean_values = [v for v in value if v != ',']
                
                if len(clean_values) == 1:
                    stats_data[key] = clean_values[0]
                else:
                    stats_data[key] = clean_values
        
        if stats_data:
            sidebar_data['stats'] = stats_data
            
        # Operates in
        if operates_in_row:
            region_link = operates_in_row.select_one('.region-link')
            region = get_text(region_link) if region_link else "Unknown"
            
            if region == "Unknown":
                 raw_values = list(operates_in_row.stripped_strings)[1:]
                 if raw_values:
                     region = raw_values[0]

            countries = []
            for wrapper in operates_in_row.select('.country-flag-wrapper'):
                c_name = wrapper.get('title')
                if c_name:
                    countries.append(c_name)
                    
            if not countries:
                for link in operates_in_row.select('a'):
                    if 'region-link' in link.get('class', []): continue
                    c_name = link.get('title') or get_text(link)
                    if c_name and c_name != region:
                        countries.append(c_name)

            sidebar_data['operatesIn'] = {
                "region": region,
                "countries": countries
            }

        # Reviews (Trustpilot)
        trustpilot_link = sidebar.select_one('a[href*="trustpilot.com"]')
        if trustpilot_link:
            sidebar_data['trustpilot'] = {"url": trustpilot_link['href']}

        # Visit Website & Status
        # Looking for .stats-button wrapper
        stats_btns = sidebar.select('.stats-button')
        
        status_val = "uncertain"
        website_url = None
        
        for btn_wrapper in stats_btns:
            # Check for Active: <a> with "Visit website"
            active_link = btn_wrapper.find('a', string=lambda s: s and 'visit website' in s.lower())
            if active_link:
                status_val = "active"
                raw_url = active_link.get('href')
                if raw_url and raw_url.strip() != '#' and 'javascript' not in raw_url.lower():
                    resolved = resolve_final_url(raw_url)
                    # Filter out trackmytarget or other tracking if resolution failed to leave the domain
                    if resolved and "trackmytarget.com" not in resolved:
                        website_url = resolved
                break # Found active, stop checking
            
            # Check for Inactive: <button> with "Platform is inactive"
            inactive_btn = btn_wrapper.find('button', string=lambda s: s and 'platform is inactive' in s.lower())
            if inactive_btn:
                status_val = "inactive"
                break
        
        sidebar_data['status'] = status_val
        if website_url:
            sidebar_data['websiteUrl'] = website_url
        
        # Socials
        socials_container = sidebar.select_one('.socials')
        if socials_container:
            social_links = [a['href'] for a in socials_container.find_all('a', href=True)]
            if social_links:
                sidebar_data['socials'] = social_links
                
        # Features (Sidebar List)
        features = []
        feature_section = sidebar.select_one('.sidebar-list.sidebar-section')
        if feature_section:
            items = feature_section.select('li')
            
            for item in items:
                span = item.select_one('span')
                if not span: continue
                
                text_parts = list(span.stripped_strings)
                text = text_parts[0] if text_parts else ""
                
                checkbox = item.select_one('.checkbox')
                is_checked = False
                if checkbox:
                    if 'checked' in checkbox.get('class', []):
                        is_checked = True
                
                link = item.find('a')
                meta_url = link['href'] if link else None
                
                feature_obj = {
                    "name": text,
                    "available": is_checked
                }
                if meta_url:
                    feature_obj["metaUrl"] = meta_url
                    
                features.append(feature_obj)
        if features:
            sidebar_data['features'] = features
            
        if sidebar_data:
            data['sidebar'] = sidebar_data

    # ===================================
    # Sidebar P2P Analysis
    # ===================================
    p2p_data = {}
    sidebar_p2p = soup.select_one('.sidebar.p2p')
    if sidebar_p2p:
        # Sneakypeer Scoring
        scoring_elem = sidebar_p2p.select_one('.sidebar-p2p.scoring .inside-circle')
        if scoring_elem:
            p2p_data['sneakypeerScoring'] = get_text(scoring_elem)
            
        # Transparency
        transparency_elem = sidebar_p2p.select_one('.sidebar-p2p.transparency .progress-bar-percent')
        if transparency_elem:
            val = get_text(transparency_elem)
            if val:
                p2p_data['transparency'] = val.replace(' ', '').strip()
            
        # Red Flags
        flags_container = sidebar_p2p.select_one('.sidebar-p2p.flags')
        if flags_container:
            flag_items = flags_container.select('.item span')
            flags = [get_text(span) for span in flag_items]
            flags = [f for f in flags if f]
            if flags:
                p2p_data['redFlags'] = flags
                
        if p2p_data:
            data['p2p'] = p2p_data

    # ===================================
    # Team
    # ===================================
    team_data = []
    team_section = soup.select_one('.team')
    if team_section:
        for member in team_section.select('.team-item'):
            name = get_text(member.select_one('.team-item-name'))
            position = get_text(member.select_one('.team-item-position'))
            
            if name: # Position might be empty
                team_data.append({
                    "name": name,
                    "position": position
                })
    
    if team_data:
        data['team'] = team_data

    return data
