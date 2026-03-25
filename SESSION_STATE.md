# Session State — SAP Business AI / Joule Capabilities Explorer

## Project Overview
Building easyassap.com — a website explaining SAP Business AI features (Joule, Embedded AI, recommended projects) for the State of Arkansas using a crawl/walk/run adoption framework. All content is generated via a Python pipeline from SAP Help Portal data.

## Architecture
```
pipeline/
  sources/        — Data acquisition (scrape_help.js, scrape_joule.py, toc_tree.txt)
  data/           — Generated JSON (scraped_use_cases.json → joule_capabilities_raw.json)
  analysis/       — Analyzers
  generators/     — site_generator.py → site/index.html
site/             — GitHub Pages output (index.html, CNAME)
index.html        — Root copy for GitHub Pages
```

## Key Pipeline Steps
1. `node pipeline/sources/scrape_help.js` — Scrapes SAP Help Portal → scraped_use_cases.json
2. `python3 -m pipeline.enrich_toc` — Enriches TOC tree with scraped data → joule_capabilities_raw.json
3. `python3 -m pipeline.generators.site_generator` — Generates site/index.html
4. `cp site/index.html index.html && git push` — Deploy to GitHub Pages

## Data Quality Rules (enrich_toc.py)
- **Response descriptions**: Text starting with "Joule displays", "Provides", "Recommends", etc. is NOT split into prompts — detected by `_is_response_description()`
- **Prompt preference**: Real prompts from the prompts column are PREFERRED over response-extracted splits
- **Fragment filter**: Prompts < 15 chars rejected unless they start with action verbs (`_looks_like_prompt()`)
- **Empty scrapes**: Pages with many rows but ALL empty prompts/response rejected by `is_good_scraped_data()`
- **Category-column tables**: SuccessFactors-style tables where column 2 has category labels (not prompts) detected by `_is_category_column_table()` — extracts real prompts from response field, groups by subcategory
- **Misaligned tables**: Ariba-style tables where column 2 has capability types detected by `_is_misaligned_table()`
- **Note classification**: `_is_note()` detects instructional text vs prompts
- **Parameter classification**: `_is_parameter()` detects field names vs prompts

## Rendering (site_generator.py)
- Notes shown **inline** alongside use case descriptions (ℹ️ items), not in collapsible drilldowns
- Subcategories rendered with 📂 headers when 2+ categories exist
- Type badges for capability types (Informational, Transactional, Navigational, Analytical)
- Single-product single-capability flattened to avoid unnecessary nesting

## Current Status (2025-03-25)
- **Commit**: b7623bf — Major data quality fix
- **Entries**: 216 total, 171 use cases, 18 products
- **With prompts**: 100 capabilities have sample prompts
- **Data source**: 100 scraped, 116 title-only

## Known Remaining Issues
- Signavio: 59 name-only rows in scrape (empty prompts/response) → falls back to title-only. Needs re-scrape with Puppeteer for JS-rendered content.
- Some products still have limited prompt coverage (title-only entries)
- Rendering could further distinguish between description-only entries and prompt-rich entries