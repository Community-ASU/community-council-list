#!/usr/bin/env python3
"""
Community Partner Document Generator
Reads scraped data and generates a beautifully formatted HTML report
with AI-generated summaries, team member photos, names, and roles.
"""

import json
import os
import re
import base64
import sys
from pathlib import Path


# ─── Configuration ───────────────────────────────────────────────────────────

INPUT_FILE = "scraped_data.json"
OUTPUT_FILE = "Community_Partners_Report.html"


# ─── Summary Generation ─────────────────────────────────────────────────────

def generate_summary(partner: dict) -> str:
    """Generate a clean, beautified summary from the scraped data."""
    org = partner.get("organization", "Unknown Organization")
    about = partner.get("about", {})

    raw_text = about.get("raw_text", "")
    mission = about.get("mission", "")
    description = about.get("description", "")
    meta_desc = about.get("meta_description", "")

    # Build a meaningful summary from available data
    summary_parts = []

    # Use meta description as a quick overview if available
    if meta_desc and len(meta_desc) > 30:
        summary_parts.append(meta_desc)

    # Use the explicit description
    if description and description != meta_desc and len(description) > 30:
        summary_parts.append(description)

    # Add mission statement if found
    if mission and len(mission) > 20:
        summary_parts.append(f"**Mission:** {mission}")

    # Extract the best paragraphs from raw text
    if raw_text:
        paragraphs = [p.strip() for p in raw_text.split("\n\n") if len(p.strip()) > 40]

        # Filter out navigation-like text, cookie notices, etc.
        filtered = []
        skip_keywords = [
            "cookie", "privacy", "subscribe", "newsletter", "sign up",
            "follow us", "social media", "copyright", "all rights reserved",
            "terms of", "donate now", "click here", "learn more about our",
        ]
        for p in paragraphs:
            p_lower = p.lower()
            if not any(kw in p_lower for kw in skip_keywords):
                filtered.append(p)

        # Take the best paragraphs (first ones are usually most relevant)
        for p in filtered[:4]:
            if p not in summary_parts and p != mission and p != description:
                summary_parts.append(p)

    if not summary_parts:
        summary_parts.append(
            f"{org} is a community partner organization in the ASU Community Council."
        )

    # Join and clean up
    summary = "\n\n".join(summary_parts)

    # Clean up any HTML artifacts
    summary = re.sub(r'<[^>]+>', '', summary)
    summary = re.sub(r'\s+', ' ', summary).strip()

    # Limit overall length
    if len(summary) > 1500:
        summary = summary[:1497] + "..."

    return summary


def embed_image_base64(filepath: str) -> str:
    """Convert a local image file to a base64 data URI."""
    if not filepath or not os.path.exists(filepath):
        return ""

    try:
        with open(filepath, "rb") as f:
            data = f.read()

        ext = Path(filepath).suffix.lower()
        mime_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        mime = mime_types.get(ext, "image/jpeg")

        encoded = base64.b64encode(data).decode("utf-8")
        return f"data:{mime};base64,{encoded}"
    except Exception:
        return ""


# ─── HTML Template ───────────────────────────────────────────────────────────

HTML_HEADER = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ASU Community Council — Partner Organizations Report</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Outfit:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #0a0a0f;
            --bg-secondary: #12121a;
            --bg-card: #1a1a28;
            --bg-card-hover: #22223a;
            --text-primary: #f0f0f5;
            --text-secondary: #a0a0b8;
            --text-muted: #6a6a82;
            --accent-1: #6366f1;
            --accent-2: #8b5cf6;
            --accent-3: #a78bfa;
            --accent-gradient: linear-gradient(135deg, #6366f1, #8b5cf6, #a78bfa);
            --accent-glow: rgba(99, 102, 241, 0.15);
            --border-color: rgba(255, 255, 255, 0.06);
            --border-accent: rgba(99, 102, 241, 0.3);
            --success: #34d399;
            --warning: #fbbf24;
            --shadow-lg: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
            --shadow-card: 0 4px 24px rgba(0, 0, 0, 0.3);
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.7;
            min-height: 100vh;
        }

        /* ── Hero Header ── */
        .hero {
            position: relative;
            padding: 80px 40px;
            text-align: center;
            background: linear-gradient(180deg, #12121a 0%, #0a0a0f 100%);
            overflow: hidden;
        }

        .hero::before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle at 50% 50%, rgba(99, 102, 241, 0.08) 0%, transparent 50%);
            animation: pulse-glow 8s ease-in-out infinite;
        }

        @keyframes pulse-glow {
            0%, 100% { opacity: 0.5; transform: scale(1); }
            50% { opacity: 1; transform: scale(1.1); }
        }

        .hero-content {
            position: relative;
            z-index: 1;
        }

        .hero-badge {
            display: inline-block;
            padding: 6px 16px;
            background: var(--accent-glow);
            border: 1px solid var(--border-accent);
            border-radius: 100px;
            font-size: 0.75rem;
            font-weight: 600;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            color: var(--accent-3);
            margin-bottom: 24px;
        }

        .hero h1 {
            font-family: 'Outfit', sans-serif;
            font-size: clamp(2.5rem, 5vw, 4rem);
            font-weight: 800;
            background: var(--accent-gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 16px;
            line-height: 1.1;
        }

        .hero p {
            font-size: 1.15rem;
            color: var(--text-secondary);
            max-width: 650px;
            margin: 0 auto 32px;
        }

        .hero-stats {
            display: flex;
            justify-content: center;
            gap: 48px;
            flex-wrap: wrap;
        }

        .stat {
            text-align: center;
        }

        .stat-number {
            font-family: 'Outfit', sans-serif;
            font-size: 2.5rem;
            font-weight: 700;
            background: var(--accent-gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .stat-label {
            font-size: 0.8rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-top: 4px;
        }

        /* ── Main Content ── */
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 40px 24px;
        }

        /* ── Partner Card ── */
        .partner-card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            padding: 40px;
            margin-bottom: 32px;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }

        .partner-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: var(--accent-gradient);
            opacity: 0;
            transition: opacity 0.3s ease;
        }

        .partner-card:hover {
            border-color: var(--border-accent);
            box-shadow: var(--shadow-card);
            transform: translateY(-2px);
        }

        .partner-card:hover::before {
            opacity: 1;
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 20px;
            margin-bottom: 24px;
            flex-wrap: wrap;
        }

        .org-info h2 {
            font-family: 'Outfit', sans-serif;
            font-size: 1.6rem;
            font-weight: 700;
            color: var(--text-primary);
            margin-bottom: 4px;
        }

        .org-info h2 a {
            color: inherit;
            text-decoration: none;
            transition: color 0.2s;
        }

        .org-info h2 a:hover {
            color: var(--accent-3);
        }

        .council-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 12px;
            background: rgba(99, 102, 241, 0.1);
            border: 1px solid rgba(99, 102, 241, 0.2);
            border-radius: 8px;
            font-size: 0.8rem;
            color: var(--accent-3);
            margin-top: 8px;
        }

        .council-badge .dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: var(--accent-1);
        }

        .website-link {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 8px 20px;
            background: transparent;
            border: 1px solid var(--border-accent);
            border-radius: 10px;
            color: var(--accent-3);
            text-decoration: none;
            font-size: 0.85rem;
            font-weight: 500;
            transition: all 0.2s;
            white-space: nowrap;
        }

        .website-link:hover {
            background: var(--accent-glow);
            border-color: var(--accent-1);
        }

        .website-link svg {
            width: 14px;
            height: 14px;
        }

        /* ── Summary Section ── */
        .summary-section {
            margin-bottom: 28px;
        }

        .section-label {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.7rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--text-muted);
            margin-bottom: 12px;
        }

        .section-label::after {
            content: '';
            flex: 1;
            height: 1px;
            background: var(--border-color);
        }

        .summary-text {
            color: var(--text-secondary);
            font-size: 0.95rem;
            line-height: 1.8;
        }

        .summary-text strong {
            color: var(--accent-3);
            font-weight: 600;
        }

        /* ── Team Section ── */
        .team-section {
            margin-top: 28px;
        }

        .team-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
            gap: 16px;
            margin-top: 16px;
        }

        .team-member {
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 14px;
            padding: 16px;
            text-align: center;
            transition: all 0.3s ease;
        }

        .team-member:hover {
            border-color: var(--border-accent);
            transform: translateY(-3px);
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
        }

        .member-photo {
            width: 90px;
            height: 90px;
            border-radius: 50%;
            object-fit: cover;
            margin: 0 auto 12px;
            display: block;
            border: 2px solid var(--border-color);
            transition: border-color 0.3s;
        }

        .team-member:hover .member-photo {
            border-color: var(--accent-1);
        }

        .member-photo-placeholder {
            width: 90px;
            height: 90px;
            border-radius: 50%;
            background: linear-gradient(135deg, var(--accent-1), var(--accent-2));
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 12px;
            font-size: 1.6rem;
            font-weight: 700;
            color: white;
            text-transform: uppercase;
        }

        .member-name {
            font-weight: 600;
            font-size: 0.9rem;
            color: var(--text-primary);
            margin-bottom: 4px;
        }

        .member-role {
            font-size: 0.75rem;
            color: var(--text-muted);
            line-height: 1.4;
        }

        /* ── Status Badges ── */
        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 3px 10px;
            border-radius: 6px;
            font-size: 0.7rem;
            font-weight: 600;
        }

        .status-success {
            background: rgba(52, 211, 153, 0.1);
            color: var(--success);
            border: 1px solid rgba(52, 211, 153, 0.2);
        }

        .status-partial {
            background: rgba(251, 191, 36, 0.1);
            color: var(--warning);
            border: 1px solid rgba(251, 191, 36, 0.2);
        }

        .status-error {
            background: rgba(239, 68, 68, 0.1);
            color: #ef4444;
            border: 1px solid rgba(239, 68, 68, 0.2);
        }

        /* ── No Data ── */
        .no-data {
            color: var(--text-muted);
            font-style: italic;
            font-size: 0.85rem;
            padding: 12px 16px;
            background: rgba(255, 255, 255, 0.02);
            border-radius: 8px;
            border: 1px dashed var(--border-color);
        }

        /* ── Table of Contents ── */
        .toc {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            padding: 32px;
            margin-bottom: 40px;
        }

        .toc h2 {
            font-family: 'Outfit', sans-serif;
            font-size: 1.3rem;
            margin-bottom: 20px;
            color: var(--text-primary);
        }

        .toc-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 8px;
        }

        .toc-item {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 12px;
            border-radius: 8px;
            color: var(--text-secondary);
            text-decoration: none;
            font-size: 0.85rem;
            transition: all 0.2s;
        }

        .toc-item:hover {
            background: var(--accent-glow);
            color: var(--accent-3);
        }

        .toc-number {
            font-weight: 700;
            font-size: 0.7rem;
            color: var(--text-muted);
            min-width: 24px;
        }

        /* ── Footer ── */
        .footer {
            text-align: center;
            padding: 60px 24px;
            color: var(--text-muted);
            font-size: 0.8rem;
        }

        .footer-line {
            width: 60px;
            height: 2px;
            background: var(--accent-gradient);
            margin: 0 auto 20px;
            border-radius: 2px;
        }

        /* ── Responsive ── */
        @media (max-width: 768px) {
            .hero { padding: 48px 20px; }
            .partner-card { padding: 24px; }
            .card-header { flex-direction: column; }
            .team-grid { grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); }
            .hero-stats { gap: 24px; }
        }

        /* ── Print Styles ── */
        @media print {
            body { background: white; color: #1a1a1a; }
            .partner-card { 
                border: 1px solid #ddd; 
                box-shadow: none;
                break-inside: avoid;
            }
            .hero { background: white; }
            .hero h1 { -webkit-text-fill-color: #6366f1; }
        }
    </style>
</head>
<body>
"""

HTML_FOOTER = """
    <footer class="footer">
        <div class="footer-line"></div>
        <p>ASU Community Council — Partner Organizations Report</p>
        <p style="margin-top: 8px;">Generated from community partner website data</p>
    </footer>
</body>
</html>
"""


# ─── HTML Generation ─────────────────────────────────────────────────────────

def generate_partner_html(partner: dict, index: int) -> str:
    """Generate HTML for a single partner card."""
    org = partner.get("organization", "Unknown Organization")
    member = partner.get("council_member", "")
    position = partner.get("council_position", "")
    website = partner.get("website", "")
    status = partner.get("scrape_status", "")
    about = partner.get("about", {})
    team = partner.get("team", {})

    # Generate summary
    summary = generate_summary(partner)

    # Status badge
    status_class = {
        "success": "status-success",
        "partial": "status-partial",
        "error": "status-error",
        "no_website": "status-error",
    }.get(status, "status-partial")

    status_text = {
        "success": "✓ Scraped",
        "partial": "◐ Partial",
        "error": "✗ Error",
        "no_website": "⚠ No Website",
    }.get(status, "Unknown")

    # Build HTML
    html = f'''
    <div class="partner-card" id="partner-{index}">
        <div class="card-header">
            <div class="org-info">
                <h2><a href="{website}" target="_blank" rel="noopener">{org}</a></h2>
                <div class="council-badge">
                    <span class="dot"></span>
                    {member} — {position}
                </div>
            </div>
            <div style="display: flex; align-items: center; gap: 12px;">
                <span class="status-badge {status_class}">{status_text}</span>
    '''

    if website:
        html += f'''
                <a href="{website}" target="_blank" rel="noopener" class="website-link">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                        <path fill-rule="evenodd" d="M4.25 5.5a.75.75 0 00-.75.75v8.5c0 .414.336.75.75.75h8.5a.75.75 0 00.75-.75v-4a.75.75 0 011.5 0v4A2.25 2.25 0 0112.75 17h-8.5A2.25 2.25 0 012 14.75v-8.5A2.25 2.25 0 014.25 4h5a.75.75 0 010 1.5h-5z" clip-rule="evenodd"/>
                        <path fill-rule="evenodd" d="M6.194 12.753a.75.75 0 001.06.053L16.5 4.44v2.81a.75.75 0 001.5 0v-4.5a.75.75 0 00-.75-.75h-4.5a.75.75 0 000 1.5h2.553l-9.056 8.194a.75.75 0 00-.053 1.06z" clip-rule="evenodd"/>
                    </svg>
                    Visit Website
                </a>
    '''

    html += '''
            </div>
        </div>
    '''

    # Summary section
    html += '''
        <div class="summary-section">
            <div class="section-label">About the Organization</div>
    '''

    if summary:
        # Convert markdown bold to HTML
        formatted = summary.replace("**", "<strong>", 1)
        while "**" in formatted:
            formatted = formatted.replace("**", "</strong>", 1)
            if "**" in formatted:
                formatted = formatted.replace("**", "<strong>", 1)
        html += f'            <div class="summary-text">{formatted}</div>\n'
    else:
        html += '            <div class="no-data">No about information could be scraped from this website.</div>\n'

    html += '        </div>\n'

    # Team section
    members = team.get("members", [])
    if members:
        html += '''
        <div class="team-section">
            <div class="section-label">Team & Staff</div>
            <div class="team-grid">
    '''
        for m in members:
            name = m.get("name", "Unknown")
            role = m.get("role", "")
            local_photo = m.get("local_photo", "")
            photo_url = m.get("photo_url", "")

            # Try embedded photo first, then external URL
            photo_data = embed_image_base64(local_photo) if local_photo else ""

            html += '                <div class="team-member">\n'

            if photo_data:
                html += f'                    <img src="{photo_data}" alt="{name}" class="member-photo" loading="lazy">\n'
            elif photo_url:
                html += f'                    <img src="{photo_url}" alt="{name}" class="member-photo" loading="lazy" onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'flex\'">\n'
                initials = "".join(w[0] for w in name.split()[:2] if w).upper()
                html += f'                    <div class="member-photo-placeholder" style="display:none">{initials}</div>\n'
            else:
                initials = "".join(w[0] for w in name.split()[:2] if w).upper()
                html += f'                    <div class="member-photo-placeholder">{initials}</div>\n'

            html += f'                    <div class="member-name">{name}</div>\n'
            if role:
                html += f'                    <div class="member-role">{role}</div>\n'
            html += '                </div>\n'

        html += '''
            </div>
        </div>
    '''
    else:
        html += '''
        <div class="team-section">
            <div class="section-label">Team & Staff</div>
            <div class="no-data">No team/staff information could be found on this website.</div>
        </div>
    '''

    html += '    </div>\n'
    return html


def generate_report(data: list) -> str:
    """Generate the complete HTML report."""

    # Stats
    total = len(data)
    total_members = sum(len(r.get("team", {}).get("members", [])) for r in data)
    success_count = sum(1 for r in data if r.get("scrape_status") in ("success", "partial"))

    html = HTML_HEADER

    # Hero section
    html += f'''
    <div class="hero">
        <div class="hero-content">
            <div class="hero-badge">Community Impact Report</div>
            <h1>ASU Community Council<br>Partner Organizations</h1>
            <p>A comprehensive overview of {total} community partner organizations, their missions, and the people who lead them.</p>
            <div class="hero-stats">
                <div class="stat">
                    <div class="stat-number">{total}</div>
                    <div class="stat-label">Partner Organizations</div>
                </div>
                <div class="stat">
                    <div class="stat-number">{total_members}</div>
                    <div class="stat-label">Team Members Found</div>
                </div>
                <div class="stat">
                    <div class="stat-number">{success_count}</div>
                    <div class="stat-label">Sites Successfully Scraped</div>
                </div>
            </div>
        </div>
    </div>
    '''

    # Table of contents
    html += '''
    <div class="container">
        <div class="toc">
            <h2>📋 Partner Directory</h2>
            <div class="toc-grid">
    '''
    for i, partner in enumerate(data, 1):
        org = partner.get("organization", "Unknown")
        html += f'                <a href="#partner-{i}" class="toc-item"><span class="toc-number">{i:02d}</span> {org}</a>\n'

    html += '''
            </div>
        </div>
    '''

    # Partner cards
    for i, partner in enumerate(data, 1):
        html += generate_partner_html(partner, i)

    html += '    </div>\n'
    html += HTML_FOOTER

    return html


def main():
    """Main entry point."""
    print("=" * 60)
    print("  Community Partner Document Generator")
    print("=" * 60)

    # Load scraped data
    input_path = os.path.join(os.path.dirname(__file__) or ".", INPUT_FILE)
    if not os.path.exists(input_path):
        print(f"\n✗ Error: {input_path} not found.")
        print("  Run scraper.py first to generate the scraped data.")
        sys.exit(1)

    with open(input_path, "r") as f:
        data = json.load(f)

    print(f"\nLoaded {len(data)} partner records")

    # Generate HTML report
    print("Generating HTML report...")
    html = generate_report(data)

    # Save report
    output_path = os.path.join(os.path.dirname(__file__) or ".", OUTPUT_FILE)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    file_size = os.path.getsize(output_path)
    print(f"\n✓ Report generated: {output_path}")
    print(f"  File size: {file_size / 1024:.1f} KB")

    # Stats
    total_members = sum(len(r.get("team", {}).get("members", [])) for r in data)
    total_photos = sum(
        1 for r in data
        for m in r.get("team", {}).get("members", [])
        if m.get("local_photo") and os.path.exists(m["local_photo"])
    )
    orgs_with_about = sum(1 for r in data if r.get("about", {}).get("raw_text"))
    orgs_with_team = sum(1 for r in data if r.get("team", {}).get("members"))

    print(f"\n  📊 Summary:")
    print(f"     Organizations with about info: {orgs_with_about}/{len(data)}")
    print(f"     Organizations with team data:  {orgs_with_team}/{len(data)}")
    print(f"     Total team members:            {total_members}")
    print(f"     Photos embedded:               {total_photos}")
    print(f"\n  Open {OUTPUT_FILE} in your browser to view the report!")


if __name__ == "__main__":
    main()
