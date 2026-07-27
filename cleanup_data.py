#!/usr/bin/env python3
"""
Data Cleanup & Quality Script
Fixes all data quality issues in the scraped data:
1. Cleans up dirty roles (removes "Leader Profile|LinkedIn", etc.)
2. Cleans up dirty names (splits concatenated name+role strings)
3. Removes fake/non-person entries (section headings, cookie banners, etc.)
4. Deduplicates members within each organization
5. Deduplicates photos (by file hash)
6. Validates photo quality (removes tiny/corrupt/logo images)
7. Regenerates the docx with clean data
"""

import json
import os
import re
import hashlib
from PIL import Image

INPUT_FILE = "scraped_data_enhanced.json"
OUTPUT_FILE = "scraped_data_clean.json"

# ─── Name/Role Cleanup ──────────────────────────────────────────────────────

# Patterns to strip from names and roles
STRIP_PATTERNS = [
    r'Leader\s*Profile\|?LinkedIn',
    r'Leader\s*Profile',
    r'\|?\s*LinkedIn',
    r'Read\s*More',
    r'View\s*Bio(graphy)?',
    r'View\s*Profile',
    r'Learn\s*More',
    r'Click\s*to\s*view\s*biography',
    r'Phone\d[\d\-\s]+',
    r'Add(ress)?$',
]

def clean_text(text: str) -> str:
    """Remove junk suffixes from names/roles."""
    for pattern in STRIP_PATTERNS:
        text = re.sub(pattern, '', text, flags=re.I).strip()
    # Remove trailing pipe, dash, comma
    text = re.sub(r'[\|,\-]+\s*$', '', text).strip()
    return text


def split_concatenated_name_role(name: str) -> tuple:
    """Split 'John SmithChief Executive Officer' into ('John Smith', 'Chief Executive Officer')."""
    # Common title keywords that mark where the role starts
    role_prefixes = [
        'Chief ', 'Vice President', 'VP ', 'President', 'Director',
        'Executive Director', 'CEO', 'CFO', 'COO', 'CTO', 'CMO',
        'Manager', 'Coordinator', 'Supervisor', 'Officer',
        'Specialist', 'Administrator', 'Founder', 'Head of',
        'Senior ', 'Associate ', 'Assistant ', 'Board ', 'Chair',
    ]
    
    for prefix in role_prefixes:
        # Look for a title keyword that appears mid-string without space separation
        # e.g., "Swati WebbChief Financial Officer"
        pattern = re.compile(r'^(.+?)(' + re.escape(prefix) + r'.*)$')
        match = pattern.match(name)
        if match:
            potential_name = match.group(1).strip()
            potential_role = match.group(2).strip()
            # Validate: name should have at least 2 parts and be reasonable length
            if ' ' in potential_name and 3 <= len(potential_name) <= 50:
                return potential_name, potential_role
    
    return name, ""


# ─── Person Validation ──────────────────────────────────────────────────────

REJECT_EXACT = {
    "follow us", "subscribe", "stay connected", "social media", "blog",
    "our mission", "our values", "our vision", "mission", "vision", "values",
    "core values", "cookie and privacy settings", "stay up to date",
    "board of directors", "foundation board", "board of trustees",
    "board of governors", "international board of directors",
    "global mission board", "t1d fund board of directors",
    "executive leadership", "operations team", "development team",
    "human resources team", "staff", "directors", "management team",
    "tempe office", "location", "resources", "about us", "contact us",
    "keep learning", "thrift boutique", "financials", "press",
    "the whirling arrow", "fax numbers", "care across the valley",
}

REJECT_CONTAINS = [
    "cookie", "privacy", "newsletter", "sign up", "follow us",
    "stay connected", "social media", "copyright", "terms of",
    "donate now", "you have the power", "help us reach",
    "straight to your inbox", "choose one of our",
    "medical, dental", "insurance", "learn more about",
    "governing body is tasked", "abc's of", "father's day",
    "exclusive to", "strictly necessary", "targeting cookie",
    "performance cookie", "functional cookie",
    "click to view", "we're all in this together",
    "stay up to date", "keep learning with free",
]

REJECT_STARTSWITH = [
    "1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.",
    "http", "www", "/",
]


def is_valid_person(name: str, role: str = "") -> bool:
    """Strictly validate if this is a real person entry."""
    if not name or len(name) < 3 or len(name) > 80:
        return False
    
    name_lower = name.lower().strip()
    
    # Exact match rejection
    if name_lower in REJECT_EXACT:
        return False
    
    # Contains rejection
    for rw in REJECT_CONTAINS:
        if rw in name_lower:
            return False
    
    # Starts with rejection
    for sw in REJECT_STARTSWITH:
        if name_lower.startswith(sw):
            return False
    
    # Must look like a person name (has first + last name typically)
    # Allow single names only if they have a role
    words = name.split()
    if len(words) < 2 and not role:
        # Single word — likely not a person unless it's a known short name
        if len(name) > 15:  # Long single words are likely not names
            return False
    
    # Reject ALL CAPS entries longer than 15 chars (likely headings)
    if name.isupper() and len(name) > 15:
        return False
    
    # Reject if it looks like a role/title was used as name
    role_only_patterns = [
        r'^chief\s', r'^vice\s', r'^president$', r'^director$',
        r'^executive\s', r'^ceo$', r'^cfo$', r'^coo$',
    ]
    for rp in role_only_patterns:
        if re.match(rp, name_lower):
            return False
    
    return True


# ─── Photo Validation ───────────────────────────────────────────────────────

def validate_photo(filepath: str) -> bool:
    """Check if a photo is a valid headshot (not a logo, icon, or decorative image)."""
    if not filepath or not os.path.exists(filepath):
        return False
    
    try:
        img = Image.open(filepath)
        w, h = img.size
        
        # Too small — likely an icon or spacer
        if w < 60 or h < 60:
            return False
        
        # Extremely wide/tall — likely a banner
        aspect = max(w, h) / min(w, h) if min(w, h) > 0 else 999
        if aspect > 4:
            return False
        
        # Check file size — tiny files are likely placeholders
        file_size = os.path.getsize(filepath)
        if file_size < 2000:  # Less than 2KB
            return False
        
        return True
    except Exception:
        return False


def get_photo_hash(filepath: str) -> str:
    """Get MD5 hash of a photo file."""
    if not filepath or not os.path.exists(filepath):
        return ""
    try:
        with open(filepath, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception:
        return ""


# ─── Main Cleanup ────────────────────────────────────────────────────────────

def cleanup_data(data: list) -> list:
    """Clean up all scraped data."""
    cleaned = []
    
    total_removed_members = 0
    total_removed_photos = 0
    total_fixed_roles = 0
    total_fixed_names = 0
    total_deduped = 0
    
    for partner in data:
        org = partner.get("organization", "")
        members = partner.get("team", {}).get("members", [])
        
        clean_members = []
        seen_names = set()
        seen_photo_hashes = set()
        
        for m in members:
            name = m.get("name", "").strip()
            role = m.get("role", "").strip()
            photo = m.get("local_photo", "")
            photo_url = m.get("photo_url", "")
            
            # 1. Clean name
            name = clean_text(name)
            
            # 2. Check if name has a concatenated role
            split_name, split_role = split_concatenated_name_role(name)
            if split_role:
                name = split_name
                if not role or len(split_role) > len(role):
                    role = split_role
                total_fixed_names += 1
            
            # 3. Clean role
            original_role = role
            role = clean_text(role)
            
            # Also remove the person's own name from the role if it got concatenated
            if name and role.startswith(name):
                role = role[len(name):].strip()
            
            if role != original_role:
                total_fixed_roles += 1
            
            # 4. Validate person
            if not is_valid_person(name, role):
                total_removed_members += 1
                # Remove any downloaded photo for invalid entries
                if photo and os.path.exists(photo):
                    os.remove(photo)
                    total_removed_photos += 1
                continue
            
            # 5. Deduplicate by name
            name_key = name.lower().strip()
            if name_key in seen_names:
                total_deduped += 1
                continue
            seen_names.add(name_key)
            
            # 6. Validate photo
            if photo:
                if not validate_photo(photo):
                    # Remove invalid photo
                    if os.path.exists(photo):
                        os.remove(photo)
                    photo = ""
                    total_removed_photos += 1
                else:
                    # Check for duplicate photos
                    ph = get_photo_hash(photo)
                    if ph and ph in seen_photo_hashes:
                        # Duplicate photo — remove it
                        os.remove(photo)
                        photo = ""
                        total_removed_photos += 1
                    elif ph:
                        seen_photo_hashes.add(ph)
            
            clean_members.append({
                "name": name,
                "role": role,
                "photo_url": photo_url,
                "local_photo": photo,
                "bio": m.get("bio", ""),
            })
        
        # Update partner data
        partner_clean = dict(partner)
        partner_clean["team"]["members"] = clean_members
        
        if len(members) != len(clean_members):
            print(f"  {org}: {len(members)} → {len(clean_members)} members")
        
        cleaned.append(partner_clean)
    
    print(f"\n  📊 Cleanup Summary:")
    print(f"     Invalid members removed: {total_removed_members}")
    print(f"     Duplicate members removed: {total_deduped}")
    print(f"     Bad photos removed: {total_removed_photos}")
    print(f"     Names fixed: {total_fixed_names}")
    print(f"     Roles cleaned: {total_fixed_roles}")
    
    return cleaned


def main():
    print("=" * 60)
    print("  Data Cleanup & Quality Fix")
    print("=" * 60)
    
    input_path = os.path.join(os.path.dirname(__file__) or ".", INPUT_FILE)
    with open(input_path) as f:
        data = json.load(f)
    
    print(f"\nLoaded {len(data)} partners")
    
    # Before stats
    total_before = sum(len(p.get("team", {}).get("members", [])) for p in data)
    photos_before = sum(1 for p in data for m in p.get("team", {}).get("members", []) if m.get("local_photo") and os.path.exists(m["local_photo"]))
    
    print(f"  Before: {total_before} members, {photos_before} photos")
    print(f"\nCleaning data...\n")
    
    cleaned = cleanup_data(data)
    
    # After stats
    total_after = sum(len(p.get("team", {}).get("members", [])) for p in cleaned)
    photos_after = sum(1 for p in cleaned for m in p.get("team", {}).get("members", []) if m.get("local_photo") and os.path.exists(m["local_photo"]))
    orgs_with_team = sum(1 for p in cleaned if p.get("team", {}).get("members"))
    
    print(f"\n  After:  {total_after} members, {photos_after} photos")
    print(f"  Organizations with team data: {orgs_with_team}/46")
    
    # Save cleaned data
    output_path = os.path.join(os.path.dirname(__file__) or ".", OUTPUT_FILE)
    with open(output_path, "w") as f:
        json.dump(cleaned, f, indent=2, ensure_ascii=False)
    
    # Also overwrite the enhanced data so generate_docx uses the clean version
    with open(input_path, "w") as f:
        json.dump(cleaned, f, indent=2, ensure_ascii=False)
    
    print(f"\n  ✓ Clean data saved to: {OUTPUT_FILE}")
    print(f"  ✓ Also updated: {INPUT_FILE}")
    print(f"\n  Now run: python3 generate_docx.py")


if __name__ == "__main__":
    main()
