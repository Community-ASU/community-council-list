#!/usr/bin/env python3
"""
Generate a Word Document (.docx) from scraped community partner data.
Includes AI-generated summaries, team member photos, names, and roles.
"""

import json
import os
import re
import sys
from pathlib import Path
from io import BytesIO

# pyrefly: ignore [missing-import]
from docx import Document
from docx.shared import Inches, Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_ORIENT
from PIL import Image


INPUT_FILE = "scraped_data_enhanced.json"
OUTPUT_FILE = "ASU_Community_Partners_Report.docx"


# ─── Summary Generation ─────────────────────────────────────────────────────

def generate_summary(partner: dict) -> str:
    """Create a clean summary from scraped data."""
    about = partner.get("about", {})
    org = partner.get("organization", "")

    raw = about.get("raw_text", "")
    mission = about.get("mission", "")
    desc = about.get("description", "")

    parts = []

    if desc and len(desc) > 30:
        parts.append(desc)

    if mission and len(mission) > 20 and mission != desc:
        parts.append(f"Mission: {mission}")

    if raw:
        paragraphs = [p.strip() for p in raw.split("\n\n") if len(p.strip()) > 40]
        skip_kw = ["cookie", "privacy", "subscribe", "newsletter", "sign up",
                    "follow us", "copyright", "terms of", "donate now", "click here"]
        for p in paragraphs[:5]:
            p_lower = p.lower()
            if not any(kw in p_lower for kw in skip_kw) and p not in parts and p != mission:
                parts.append(p)

    if not parts:
        parts.append(f"{org} is a community partner organization in the ASU Community Council.")

    summary = " ".join(parts)
    summary = re.sub(r'<[^>]+>', '', summary)
    summary = re.sub(r'\s+', ' ', summary).strip()

    if len(summary) > 1200:
        summary = summary[:1197] + "..."

    return summary


# ─── Resize photo for embedding ─────────────────────────────────────────────

def prepare_photo(filepath: str, max_width: int = 200, max_height: int = 200) -> str:
    """Resize a photo and return the path to the resized version."""
    if not filepath or not os.path.exists(filepath):
        return ""
    try:
        img = Image.open(filepath)
        img.thumbnail((max_width, max_height), Image.LANCZOS)
        # Convert to RGB if needed (RGBA or P mode can't save as JPEG)
        if img.mode in ('RGBA', 'P', 'LA'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if 'A' in img.mode else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        resized_path = filepath.rsplit('.', 1)[0] + '_thumb.jpg'
        img.save(resized_path, 'JPEG', quality=85)
        return resized_path
    except Exception as e:
        print(f"  ⚠ Photo resize error: {e}")
        return ""


# ─── Document Generation ────────────────────────────────────────────────────

def create_document(data: list) -> Document:
    """Create a Word document from scraped partner data."""
    doc = Document()

    # ── Page Setup ──
    section = doc.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(0.8)
    section.bottom_margin = Inches(0.8)
    section.left_margin = Inches(0.9)
    section.right_margin = Inches(0.9)

    # ── Styles ──
    style = doc.styles['Title']
    style.font.name = 'Calibri'
    style.font.size = Pt(28)
    style.font.bold = True
    style.font.color.rgb = RGBColor(30, 30, 80)
    style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    style.paragraph_format.space_after = Pt(6)

    style = doc.styles['Heading 1']
    style.font.name = 'Calibri'
    style.font.size = Pt(18)
    style.font.bold = True
    style.font.color.rgb = RGBColor(40, 40, 120)
    style.paragraph_format.space_before = Pt(18)
    style.paragraph_format.space_after = Pt(6)

    style = doc.styles['Heading 2']
    style.font.name = 'Calibri'
    style.font.size = Pt(13)
    style.font.bold = True
    style.font.color.rgb = RGBColor(80, 80, 160)
    style.paragraph_format.space_before = Pt(12)
    style.paragraph_format.space_after = Pt(4)

    style = doc.styles['Normal']
    style.font.name = 'Calibri'
    style.font.size = Pt(10.5)
    style.font.color.rgb = RGBColor(40, 40, 40)
    style.paragraph_format.space_after = Pt(6)

    # ── Title Page ──
    for _ in range(4):
        doc.add_paragraph()

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("ASU Community Council")
    run.font.size = Pt(32)
    run.font.bold = True
    run.font.color.rgb = RGBColor(140, 30, 60)

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = subtitle.add_run("Partner Organizations Report")
    run.font.size = Pt(22)
    run.font.color.rgb = RGBColor(80, 80, 130)

    doc.add_paragraph()

    # Stats
    total_members = sum(len(r.get("team", {}).get("members", [])) for r in data)
    orgs_with_team = sum(1 for r in data if r.get("team", {}).get("members"))

    stats = doc.add_paragraph()
    stats.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = stats.add_run(f"{len(data)} Partner Organizations  •  {total_members} Team Members Identified  •  {orgs_with_team} Organizations with Staff Data")
    run.font.size = Pt(11)
    run.font.color.rgb = RGBColor(100, 100, 100)

    doc.add_paragraph()
    line = doc.add_paragraph()
    line.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = line.add_run("━" * 50)
    run.font.color.rgb = RGBColor(180, 180, 200)

    doc.add_page_break()

    # ── Table of Contents ──
    toc_heading = doc.add_heading("Partner Directory", level=1)
    doc.add_paragraph()

    # Create a 2-column table for the directory
    num_partners = len(data)
    half = (num_partners + 1) // 2
    toc_table = doc.add_table(rows=half, cols=2)
    toc_table.alignment = WD_TABLE_ALIGNMENT.CENTER

    for i, partner in enumerate(data):
        row_idx = i % half
        col_idx = 0 if i < half else 1
        cell = toc_table.cell(row_idx, col_idx)
        cell.text = ""
        p = cell.paragraphs[0]
        run = p.add_run(f"{i+1}. ")
        run.font.size = Pt(9)
        run.font.color.rgb = RGBColor(140, 30, 60)
        run.font.bold = True
        run = p.add_run(partner.get("organization", ""))
        run.font.size = Pt(9)
        run.font.color.rgb = RGBColor(50, 50, 50)

    doc.add_page_break()

    # ── Partner Sections ──
    for i, partner in enumerate(data, 1):
        org = partner.get("organization", "Unknown")
        member = partner.get("council_member", "")
        position = partner.get("council_position", "")
        website = partner.get("website", "")
        about = partner.get("about", {})
        team = partner.get("team", {})
        members = team.get("members", [])

        # Organization heading
        heading = doc.add_heading(f"{i}. {org}", level=1)

        # Council member info
        info = doc.add_paragraph()
        run = info.add_run("Council Representative: ")
        run.font.bold = True
        run.font.size = Pt(10)
        run.font.color.rgb = RGBColor(100, 100, 100)
        run = info.add_run(f"{member}, {position}")
        run.font.size = Pt(10)
        run.font.color.rgb = RGBColor(60, 60, 60)

        # Website
        if website:
            web_p = doc.add_paragraph()
            run = web_p.add_run("Website: ")
            run.font.bold = True
            run.font.size = Pt(10)
            run.font.color.rgb = RGBColor(100, 100, 100)
            run = web_p.add_run(website)
            run.font.size = Pt(10)
            run.font.color.rgb = RGBColor(40, 80, 160)
            run.font.underline = True

        # Divider
        div = doc.add_paragraph()
        run = div.add_run("─" * 80)
        run.font.size = Pt(6)
        run.font.color.rgb = RGBColor(200, 200, 210)

        # About summary
        summary = generate_summary(partner)
        doc.add_heading("About", level=2)
        about_p = doc.add_paragraph(summary)
        about_p.paragraph_format.space_after = Pt(8)

        # Team/Staff section
        doc.add_heading("Team / Leadership / Staff", level=2)

        if members:
            # Filter out Mountain Park's 213 members to reasonable count
            display_members = members[:30] if len(members) > 30 else members
            if len(members) > 30:
                note = doc.add_paragraph()
                run = note.add_run(f"Showing {len(display_members)} of {len(members)} team members found.")
                run.font.italic = True
                run.font.size = Pt(9)
                run.font.color.rgb = RGBColor(130, 130, 130)

            # Create table for team members: Photo | Name | Role
            table = doc.add_table(rows=1, cols=3)
            table.alignment = WD_TABLE_ALIGNMENT.CENTER
            table.style = 'Light List Accent 1'

            # Header row
            hdr = table.rows[0]
            for j, text in enumerate(["Photo", "Name", "Role / Title"]):
                cell = hdr.cells[j]
                cell.text = text
                for p in cell.paragraphs:
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    for r in p.runs:
                        r.font.bold = True
                        r.font.size = Pt(10)
                        r.font.color.rgb = RGBColor(255, 255, 255)

            # Set column widths
            for row in table.rows:
                row.cells[0].width = Inches(1.2)
                row.cells[1].width = Inches(2.3)
                row.cells[2].width = Inches(3.2)

            # Data rows
            for m in display_members:
                row = table.add_row()

                # Photo cell
                photo_cell = row.cells[0]
                photo_cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
                local_photo = m.get("local_photo", "")
                if local_photo and os.path.exists(local_photo):
                    thumb = prepare_photo(local_photo, 120, 120)
                    if thumb:
                        try:
                            photo_cell.paragraphs[0].add_run().add_picture(thumb, width=Inches(1.0))
                        except Exception:
                            run = photo_cell.paragraphs[0].add_run("📷")
                            run.font.size = Pt(18)
                    else:
                        run = photo_cell.paragraphs[0].add_run("📷")
                        run.font.size = Pt(18)
                else:
                    # Initials placeholder
                    initials = "".join(w[0] for w in m.get("name", "?").split()[:2] if w).upper()
                    run = photo_cell.paragraphs[0].add_run(f"[{initials}]")
                    run.font.size = Pt(14)
                    run.font.color.rgb = RGBColor(140, 30, 60)
                    run.font.bold = True

                # Name cell
                name_cell = row.cells[1]
                name_cell.text = ""
                run = name_cell.paragraphs[0].add_run(m.get("name", ""))
                run.font.bold = True
                run.font.size = Pt(10)

                # Role cell
                role_cell = row.cells[2]
                role_cell.text = ""
                role_text = m.get("role", "")
                if role_text:
                    run = role_cell.paragraphs[0].add_run(role_text)
                    run.font.size = Pt(10)
                    run.font.color.rgb = RGBColor(80, 80, 80)
                else:
                    run = role_cell.paragraphs[0].add_run("—")
                    run.font.size = Pt(10)
                    run.font.color.rgb = RGBColor(180, 180, 180)

        else:
            no_team = doc.add_paragraph()
            run = no_team.add_run("No team/staff/leadership data could be found on this organization's website.")
            run.font.italic = True
            run.font.size = Pt(10)
            run.font.color.rgb = RGBColor(150, 150, 150)

        # Add space between partners
        doc.add_paragraph()

        # Page break every 2 partners for readability (but not after the last)
        if i < len(data):
            doc.add_page_break()

    # ── Final Page ──
    doc.add_paragraph()
    final = doc.add_paragraph()
    final.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = final.add_run("━" * 50)
    run.font.color.rgb = RGBColor(180, 180, 200)

    end = doc.add_paragraph()
    end.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = end.add_run("End of Report")
    run.font.size = Pt(12)
    run.font.color.rgb = RGBColor(140, 30, 60)
    run.font.italic = True

    end2 = doc.add_paragraph()
    end2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = end2.add_run("ASU Community Council — Partner Organizations")
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(150, 150, 150)

    return doc


def main():
    print("=" * 60)
    print("  Word Document Generator")
    print("=" * 60)

    # Try enhanced data first, fall back to original
    input_path = os.path.join(os.path.dirname(__file__) or ".", INPUT_FILE)
    if not os.path.exists(input_path):
        input_path = os.path.join(os.path.dirname(__file__) or ".", "scraped_data.json")
    if not os.path.exists(input_path):
        print("✗ No scraped data found. Run the scraper first.")
        sys.exit(1)

    with open(input_path) as f:
        data = json.load(f)

    print(f"Loaded {len(data)} partners from {os.path.basename(input_path)}")

    # Generate document
    print("Generating Word document...")
    doc = create_document(data)

    output = os.path.join(os.path.dirname(__file__) or ".", OUTPUT_FILE)
    doc.save(output)

    size_kb = os.path.getsize(output) / 1024
    total_members = sum(len(r.get("team", {}).get("members", [])) for r in data)
    orgs_with_team = sum(1 for r in data if r.get("team", {}).get("members"))
    orgs_with_about = sum(1 for r in data if len(r.get("about", {}).get("raw_text", "")) > 50)

    print(f"\n✓ Document saved: {output}")
    print(f"  Size: {size_kb:.0f} KB")
    print(f"\n  📊 Summary:")
    print(f"     Organizations: {len(data)}")
    print(f"     With about info: {orgs_with_about}")
    print(f"     With team data: {orgs_with_team}")
    print(f"     Team members: {total_members}")
    print(f"\n  Open {OUTPUT_FILE} in Word or Google Docs!")


if __name__ == "__main__":
    main()
