#!/usr/bin/env python3
"""
Elementor-Aware Scraper — Handles WordPress Elementor page builder sites.
Uses Playwright to render pages and extracts team members from:
1. Elementor e-con containers (person cards)
2. Standard HTML patterns (headings + images)
3. Grid/card layouts

Runs on ALL 46 partners for a clean re-scrape.
"""

import json
import os
import re
import sys
import time
import hashlib
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from PIL import Image
from playwright.sync_api import sync_playwright

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}
PHOTO_DIR = "photos"
OUTPUT_FILE = "scraped_data_enhanced.json"
TIMEOUT = 10

# ─── URL patterns ───────────────────────────────────────────────────────────

TEAM_SLUGS = [
    "staff", "team", "our-team", "our-staff",
    "leadership", "our-leadership", "leadership-team",
    "about/team", "about/staff", "about/leadership",
    "about/our-team", "about/our-staff",
    "board-of-directors", "board", "about/board",
    "people", "meet-the-team", "meet-our-team",
    "executive-team", "management",
    "who-we-are/leadership", "who-we-are/team", "who-we-are/staff",
    "about-us/team", "about-us/staff", "about-us/leadership",
    "about-us/our-team",
]

ABOUT_SLUGS = [
    "about", "about-us", "our-story", "who-we-are", "our-mission",
    "mission", "about/mission", "about/our-story",
]

TEAM_LINK_SCORE = {
    "team": 10, "our team": 15, "meet our team": 20, "meet the team": 20,
    "staff": 10, "our staff": 15, "meet our staff": 18,
    "leadership": 12, "our leadership": 16, "leadership team": 18,
    "board": 8, "board of directors": 10,
    "people": 8, "our people": 12,
    "executive": 7, "executive team": 14,
    "who we are": 5, "about us": 3, "about": 2,
}


def safe_filename(name: str) -> str:
    return re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_')[:80]

def fix_url(url: str) -> str:
    if not url: return url
    url = url.strip()
    if url.startswith("//"): return "https:" + url
    if not url.startswith(("http://", "https://")): return "https://" + url
    return url

def get_base_domain(url: str) -> str:
    return urlparse(fix_url(url)).netloc.replace("www.", "")


# ─── Person Validation ──────────────────────────────────────────────────────

REJECT_NAMES = {
    "follow us", "subscribe", "stay connected", "social media", "blog",
    "our mission", "our values", "our vision", "mission", "vision", "values",
    "core values", "cookie", "privacy", "board of directors",
    "foundation board", "board of trustees", "directors", "staff",
    "executive leadership", "executive leadership team", "operations team",
    "development team", "human resources team", "all center staff",
    "stay up to date", "contact us", "resources", "about us",
    "location", "donate", "home", "menu", "search", "login",
}

REJECT_CONTAINS = [
    "cookie", "privacy", "newsletter", "sign up", "follow us",
    "stay connected", "copyright", "terms of", "donate now",
    "you have the power", "governing body", "abc's of",
    "strictly necessary", "targeting cookie", "performance cookie",
    "functional cookie", "click to view", "center staff",
    "all staff", "leadership team",
]

def is_valid_person(name: str, role: str = "") -> bool:
    if not name or len(name) < 3 or len(name) > 80: return False
    nl = name.lower().strip()
    if nl in REJECT_NAMES: return False
    for rw in REJECT_CONTAINS:
        if rw in nl: return False
    if nl.startswith(("http", "www", "/", "1.", "2.", "3.", "4.", "5.")): return False
    if name.isupper() and len(name) > 20: return False
    if " " not in name and not role: return False
    return True


# ─── Elementor-specific extraction ──────────────────────────────────────────

def extract_elementor_members(soup: BeautifulSoup, base_url: str) -> list:
    """Extract team members from Elementor page builder layouts."""
    members = []
    
    # Find leaf-level e-con containers (person cards)
    # These are e-child containers with image + text widgets
    for con in soup.find_all('div', class_=lambda c: c and 'e-con' in c):
        classes = con.get('class', [])
        class_str = ' '.join(classes)
        
        # Skip parent containers — look for child/leaf containers
        # A leaf container has no child e-con divs
        child_cons = con.find_all('div', class_=lambda c: c and 'e-con' in c, recursive=False)
        if child_cons:
            continue  # This is a parent, skip
        
        # Must have an image
        img = con.find('img')
        if not img:
            continue
        src = img.get('src') or img.get('data-src') or img.get('data-lazy-src') or ''
        if not src or 'upload' not in src:
            continue
        if any(skip in src.lower() for skip in ['logo', 'seal', 'favicon', 'icon', 'banner', 'campaign', 'arizona-state', 'background']):
            continue
        
        # Get all text from widgets
        texts = []
        for tw in con.find_all('div', class_=lambda c: c and ('elementor-widget-text-editor' in c or 'elementor-widget-heading' in c)):
            # Get direct text content only (not from nested children)
            for el in tw.find_all(['h1','h2','h3','h4','h5','h6','p','span','div']):
                t = el.get_text(strip=True)
                if t and len(t) > 1 and t not in texts:
                    texts.append(t)
                    break  # Only first text per widget
        
        if len(texts) >= 1:
            name = texts[0]
            role = texts[1] if len(texts) > 1 else ''
            photo_url = urljoin(base_url, src)
            
            # Clean name
            name = re.sub(r'\s*(Leader Profile|LinkedIn|Read More|View Bio|Click to view).*', '', name, flags=re.I).strip()
            role = re.sub(r'\s*(Leader Profile|LinkedIn|Read More|View Bio|Click to view).*', '', role, flags=re.I).strip()
            
            if is_valid_person(name, role) and not any(m['name'].lower() == name.lower() for m in members):
                members.append({
                    'name': name,
                    'role': role,
                    'photo_url': photo_url,
                    'bio': '',
                    'local_photo': '',
                })
    
    return members


# ─── Standard HTML extraction ───────────────────────────────────────────────

def extract_standard_members(soup: BeautifulSoup, base_url: str) -> list:
    """Extract team members from standard HTML layouts."""
    members = []
    if not soup: return members
    
    for tag in soup.find_all(["script", "style", "noscript", "iframe"]):
        tag.decompose()
    
    main = soup.find("main") or soup.find("article") or soup.find("div", class_=re.compile(r"content|main|page", re.I)) or soup.body
    if not main: return members
    
    # Strategy 1: Cards with team-related classes
    cards = main.find_all(["div", "article", "li", "figure"], class_=re.compile(r"team|staff|member|person|profile|bio|leader|employee", re.I))
    if len(cards) >= 2:
        for card in cards:
            m = _parse_card(card, base_url)
            if m and is_valid_person(m['name'], m['role']) and not any(x['name'].lower() == m['name'].lower() for x in members):
                members.append(m)
    
    # Strategy 2: Grid children
    if len(members) < 2:
        for grid in main.find_all(["div", "ul", "section"], class_=re.compile(r"grid|list|team|staff|people|cards|row|flex|gallery|directory|roster", re.I)):
            children = grid.find_all(["div", "li", "article", "figure"], recursive=False)
            if 2 <= len(children) <= 100:
                for child in children:
                    m = _parse_card(child, base_url)
                    if m and is_valid_person(m['name'], m['role']) and not any(x['name'].lower() == m['name'].lower() for x in members):
                        members.append(m)
                if len(members) >= 2: break
    
    # Strategy 3: Image + nearby heading
    if len(members) < 2:
        for img in main.find_all("img"):
            src = img.get("src", "") or img.get("data-src", "")
            if any(skip in src.lower() for skip in ["logo", "icon", "banner", ".svg", "bg-", "background"]):
                continue
            el = img.parent
            for _ in range(4):
                if el is None or el.name in ("body", "html"): break
                m = _parse_card(el, base_url)
                if m and is_valid_person(m['name'], m['role']) and not any(x['name'].lower() == m['name'].lower() for x in members):
                    members.append(m)
                    break
                el = el.parent
    
    return members


def _parse_card(el, base_url: str) -> dict:
    m = {"name": "", "role": "", "photo_url": "", "bio": "", "local_photo": ""}
    
    for tag_name in ["h2", "h3", "h4", "h5", "h6", "strong", "b"]:
        tag = el.find(tag_name)
        if tag:
            name = tag.get_text(strip=True)
            name = re.sub(r'\s*(Leader Profile|LinkedIn|Read More|View Bio).*', '', name, flags=re.I).strip()
            m["name"] = name
            break
    
    if not m["name"]:
        for child in el.children:
            if hasattr(child, 'get_text'):
                text = child.get_text(strip=True)
                if 3 <= len(text) <= 60: m["name"] = text; break
    
    if m["name"]:
        for tag in el.find_all(["p", "span", "div", "em", "small"]):
            text = tag.get_text(strip=True)
            text = re.sub(r'\s*(Leader Profile|LinkedIn|Read More|View Bio).*', '', text, flags=re.I).strip()
            if text and text != m["name"] and 3 < len(text) < 150:
                m["role"] = text; break
    
    img = el.find("img")
    if img:
        src = img.get("src") or img.get("data-src") or img.get("data-lazy-src") or ""
        if src and not any(skip in src.lower() for skip in [".svg", "logo", "icon", "spacer", "pixel"]):
            m["photo_url"] = urljoin(base_url, src.strip())
    
    if not m["photo_url"]:
        for div in el.find_all(["div", "span", "figure"], style=True):
            bg = re.search(r"background-image:\s*url\(['\"]?([^'\")\s]+)", div.get("style", ""))
            if bg: m["photo_url"] = urljoin(base_url, bg.group(1)); break
    
    return m


# ─── Combined extraction ────────────────────────────────────────────────────

def extract_all_members(soup: BeautifulSoup, base_url: str) -> list:
    """Try Elementor extraction first, then standard HTML."""
    if not soup: return []
    
    # Check if page uses Elementor
    is_elementor = bool(soup.find('div', class_=lambda c: c and 'elementor' in c))
    
    members = []
    if is_elementor:
        members = extract_elementor_members(soup, base_url)
    
    if len(members) < 2:
        std_members = extract_standard_members(soup, base_url)
        # Merge, avoiding duplicates
        for m in std_members:
            if not any(x['name'].lower() == m['name'].lower() for x in members):
                members.append(m)
    
    return members


# ─── Navigation discovery ───────────────────────────────────────────────────

def discover_team_links(soup: BeautifulSoup, base_url: str, site_domain: str) -> list:
    if not soup: return []
    links = []
    seen = set()
    for a in soup.find_all("a", href=True):
        href = a.get("href", "").strip()
        text = a.get_text(strip=True).lower()
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")): continue
        full_url = urljoin(base_url + "/", href)
        ld = urlparse(full_url).netloc.replace("www.", "")
        if site_domain not in ld and ld not in site_domain: continue
        if full_url in seen: continue
        seen.add(full_url)
        score = 0
        for kw, pts in TEAM_LINK_SCORE.items():
            if kw in text or kw.replace(" ", "-") in href.lower():
                score = max(score, pts)
        path = urlparse(full_url).path.lower()
        for kw in ["team", "staff", "leadership", "board", "people", "meet"]:
            if kw in path: score += 5
        if score > 0:
            links.append({"url": full_url, "text": text, "score": score})
    links.sort(key=lambda x: x["score"], reverse=True)
    return links


# ─── Photo download (Playwright) ────────────────────────────────────────────

def download_photo(page, photo_url: str, org_name: str, member_name: str) -> str:
    if not photo_url or any(skip in photo_url.lower() for skip in ["placeholder", "coming_soon", "default"]):
        return ""
    try:
        org_dir = os.path.join(PHOTO_DIR, safe_filename(org_name))
        os.makedirs(org_dir, exist_ok=True)
        fn = safe_filename(member_name) or hashlib.md5(photo_url.encode()).hexdigest()[:12]
        
        response = page.request.get(photo_url)
        if not response.ok: return ""
        body = response.body()
        ct = response.headers.get("content-type", "")
        ext = ".png" if "png" in ct else ".webp" if "webp" in ct else ".jpg"
        fp = os.path.join(org_dir, fn + ext)
        with open(fp, "wb") as f: f.write(body)
        
        img = Image.open(fp)
        w, h = img.size
        img.verify()
        if w < 40 or h < 40:
            os.remove(fp); return ""
        if max(w,h) / min(w,h) > 5:
            os.remove(fp); return ""
        return fp
    except Exception:
        return ""


# ─── Render page ────────────────────────────────────────────────────────────

def render_page(page, url: str, wait_ms: int = 3000) -> BeautifulSoup:
    try:
        page.goto(fix_url(url), timeout=20000, wait_until="domcontentloaded")
        page.wait_for_timeout(wait_ms)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight / 3)")
        page.wait_for_timeout(800)
        page.evaluate("window.scrollTo(0, 2 * document.body.scrollHeight / 3)")
        page.wait_for_timeout(800)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(1000)
        return BeautifulSoup(page.content(), "lxml")
    except Exception as e:
        print(f"    ⚠ {e}")
        return None


# ─── About extraction ───────────────────────────────────────────────────────

def extract_about(soup: BeautifulSoup) -> dict:
    result = {"raw_text": "", "mission": "", "description": "", "about_url": ""}
    if not soup: return result
    
    for meta in [soup.find("meta", attrs={"name": "description"}), soup.find("meta", attrs={"property": "og:description"})]:
        if meta and meta.get("content"):
            result["description"] = meta["content"]; break
    
    for tag in soup.find_all(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()
    main = soup.find("main") or soup.find("article") or soup.body
    if main:
        paras = [p.get_text(strip=True) for p in main.find_all("p") if len(p.get_text(strip=True)) > 25]
        skip = ["cookie", "privacy", "subscribe", "newsletter", "follow us", "copyright"]
        paras = [p for p in paras if not any(s in p.lower() for s in skip)]
        result["raw_text"] = "\n\n".join(paras[:12])
    
    return result


# ─── Main scraper ────────────────────────────────────────────────────────────

def scrape_partner(partner: dict, browser) -> dict:
    org = partner.get("organization", "")
    website = fix_url(partner.get("website", ""))
    domain = get_base_domain(website)
    
    print(f"\n{'='*60}")
    print(f"  {org}")
    print(f"  {website}")
    print(f"{'='*60}")
    
    result = {
        "council_member": partner.get("name", ""),
        "council_position": partner.get("position", ""),
        "organization": org,
        "website": website,
        "about": {"raw_text": "", "mission": "", "description": "", "about_url": ""},
        "team": {"team_url": "", "members": []},
        "scrape_status": "success",
    }
    
    if not website:
        result["scrape_status"] = "no_website"; return result
    
    ctx = browser.new_context(user_agent=HEADERS["User-Agent"], viewport={"width": 1440, "height": 900}, ignore_https_errors=True)
    page = ctx.new_page()
    
    try:
        # 1. Homepage
        print("  🏠 Loading homepage...")
        homepage = render_page(page, website, 3000)
        if not homepage:
            result["scrape_status"] = "error"; ctx.close(); return result
        
        # 2. Discover links
        print("  🔍 Discovering links...")
        team_links = discover_team_links(homepage, website, domain)
        pattern_urls = [{"url": urljoin(website.rstrip("/") + "/", slug), "text": slug, "score": 5} for slug in TEAM_SLUGS]
        
        # Merge discovered + pattern URLs
        seen = {l["url"] for l in team_links}
        for pu in pattern_urls:
            if pu["url"] not in seen:
                team_links.append(pu)
                seen.add(pu["url"])
        team_links.sort(key=lambda x: x["score"], reverse=True)
        
        about_links = [l for l in discover_team_links(homepage, website, domain) if any(kw in l["text"] for kw in ["about", "mission", "who we", "our story"])]
        about_pattern_urls = [urljoin(website.rstrip("/") + "/", slug) for slug in ABOUT_SLUGS]
        
        print(f"  📊 {len(team_links)} team candidates")
        for tl in team_links[:5]:
            print(f"    [{tl['score']:2d}] {tl['text'][:35]:35s} → {tl['url'][:55]}")
        
        # 3. About page
        print("  📄 About page...")
        best_about = extract_about(homepage)
        best_about["about_url"] = website
        
        for url in about_pattern_urls[:4]:
            soup = render_page(page, url, 2000)
            if soup:
                about = extract_about(soup)
                if len(about["raw_text"]) > len(best_about["raw_text"]):
                    best_about = about
                    best_about["about_url"] = url
                if len(about["raw_text"]) > 300: break
        result["about"] = best_about
        print(f"  ✓ About: {len(best_about['raw_text'])} chars")
        
        # 4. Team page
        print("  👥 Team page...")
        best_members = []
        best_url = ""
        
        for tl in team_links[:10]:
            print(f"    → {tl['text'][:30]:30s} ({tl['url'][:50]})")
            soup = render_page(page, tl["url"], 3000)
            if soup:
                members = extract_all_members(soup, tl["url"])
                print(f"      {len(members)} members")
                if len(members) > len(best_members):
                    best_members = members
                    best_url = tl["url"]
                if len(members) >= 5: break
        
        # Also try sub-nav from about pages
        if len(best_members) < 2:
            for al in about_links[:2]:
                soup = render_page(page, al["url"], 2000)
                if soup:
                    sub_links = discover_team_links(soup, al["url"], domain)
                    for sl in sub_links[:3]:
                        soup2 = render_page(page, sl["url"], 3000)
                        if soup2:
                            members = extract_all_members(soup2, sl["url"])
                            if len(members) > len(best_members):
                                best_members = members
                                best_url = sl["url"]
                            if len(members) >= 3: break
                if len(best_members) >= 3: break
        
        # Try homepage itself
        if len(best_members) < 2:
            members = extract_all_members(homepage, website)
            if len(members) > len(best_members):
                best_members = members
                best_url = website
        
        result["team"]["team_url"] = best_url
        result["team"]["members"] = best_members
        print(f"  ✓ Team: {len(best_members)} members")
        
        # 5. Download photos
        if best_members:
            print(f"  📷 Downloading photos...")
            dl = 0
            for m in best_members:
                if m.get("photo_url"):
                    lp = download_photo(page, m["photo_url"], org, m["name"])
                    m["local_photo"] = lp
                    if lp: dl += 1
                else:
                    m["local_photo"] = ""
            print(f"  ✓ {dl}/{len(best_members)} photos saved")
    
    except Exception as e:
        print(f"  ✗ Error: {e}")
        result["scrape_status"] = "error"
    finally:
        ctx.close()
    
    time.sleep(0.3)
    return result


def main():
    print("=" * 60)
    print("  Elementor-Aware Full Scraper")
    print("  Playwright + BeautifulSoup")
    print("=" * 60)
    
    with open(os.path.join(os.path.dirname(__file__) or ".", "asu_community_council.json")) as f:
        partners = json.load(f)
    
    if len(sys.argv) > 1:
        try:
            partners = partners[:int(sys.argv[1])]
        except ValueError:
            pass
    
    print(f"\nScraping {len(partners)} partners")
    os.makedirs(PHOTO_DIR, exist_ok=True)
    
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        results = []
        for i, p in enumerate(partners, 1):
            print(f"\n[{i}/{len(partners)}]")
            results.append(scrape_partner(p, browser))
        browser.close()
    
    with open(os.path.join(os.path.dirname(__file__) or ".", OUTPUT_FILE), "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    orgs_team = sum(1 for r in results if r.get("team", {}).get("members"))
    total_m = sum(len(r.get("team", {}).get("members", [])) for r in results)
    total_p = sum(1 for r in results for m in r.get("team", {}).get("members", []) if m.get("local_photo"))
    
    print(f"\n{'='*60}")
    print(f"  COMPLETE")
    print(f"  Team data: {orgs_team}/{len(results)}")
    print(f"  Members: {total_m}")
    print(f"  Photos: {total_p}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
