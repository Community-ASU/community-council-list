# ASU Community Partners Document

Generates a formatted Word report (`ASU_Community_Partners_Report.docx`) of ASU
Community Council partner organizations. For each partner, the report includes
an AI-written summary of the organization plus team member names, roles, and
photos scraped from their websites.

## Pipeline

The document is produced in three steps:

1. **Scrape** — `final_scraper.py` reads the partner list from
   `asu_community_council.json`, visits each organization's website using
   Playwright, finds about/team pages, and extracts member names, roles, bios,
   and photos. Writes `scraped_data_enhanced.json` and downloads photos into
   `photos/`.

2. **Clean** — `cleanup_data.py` fixes data quality issues in the scraped data:
   strips junk from names/roles, removes non-person entries (section headings,
   cookie banners), deduplicates members and photos, and validates image files.
   Writes `scraped_data_clean.json` and also updates
   `scraped_data_enhanced.json` in place.

3. **Generate document** — `generate_docx.py` reads the cleaned data and builds
   `ASU_Community_Partners_Report.docx` with embedded photos.

Additionally, `generate_document.py` produces a standalone HTML report
(`Community_Partners_Report.html`) from `scraped_data.json`.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install playwright python-docx
playwright install chromium
```

## Usage

```bash
python3 final_scraper.py      # scrape websites -> scraped_data_enhanced.json + photos/
python3 cleanup_data.py       # clean data       -> scraped_data_clean.json
python3 generate_docx.py      # build report     -> ASU_Community_Partners_Report.docx
python3 generate_document.py  # optional HTML    -> Community_Partners_Report.html
```

## Files

| File | Purpose |
| --- | --- |
| `asu_community_council.json` | Source list of 46 partner organizations |
| `final_scraper.py` | Playwright-based website scraper |
| `cleanup_data.py` | Data cleanup and quality script |
| `generate_docx.py` | Word document generator |
| `generate_document.py` | HTML report generator |
| `scraped_data_enhanced.json` | Raw/cleaned scrape results |
| `scraped_data_clean.json` | Cleaned data snapshot |
| `photos/` | Downloaded team member photos |
| `ASU_Community_Partners_Report.docx` | Final Word report |
| `Community_Partners_Report.html` | HTML version of the report |

## Data format

Each record in the scraped JSON has this shape:

```json
{
  "organization": "...",
  "website": "...",
  "council_member": "...",
  "council_position": "...",
  "scrape_status": "ok",
  "about": { "raw_text": "", "mission": "", "description": "", "about_url": "" },
  "team": {
    "team_url": "",
    "members": [
      { "name": "", "role": "", "bio": "", "photo_url": "", "local_photo": "photos/..." }
    ]
  }
}
```
