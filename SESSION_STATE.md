# Session State — SAP Business AI / Joule Capabilities Website

## Project Overview
Website at **easyassap.com** (Arkansas folder) explaining SAP Business AI features including Joule, Embedded AI, and recommended projects for the State of Arkansas. Crawl/Walk/Run approach.

## Repository
- **GitHub**: https://github.com/JBShearer/Arkansas
- **Branch**: main
- **Remote**: origin → Arkansas repo
- **Site URL**: https://easyassap.com (GitHub Pages via `site/` folder + root `index.html`)
- **Latest Commit**: `d36ff23` — Fix Ariba rendering: show grouped sub-products with type badges, count total prompts

## Architecture

### Pipeline (Python + Node.js)
```
pipeline/
├── sources/
│   ├── toc_tree.txt          # TOC from SAP Help Portal (raw hierarchy)
│   ├── scrape_help.js        # Puppeteer scraper for SAP Help use case tables
│   ├── scrape_joule.py       # Python scraper (alternative)
│   ├── loader.py             # Data loading utilities
│   └── __init__.py
├── data/
│   ├── scraped_use_cases.json # Raw scraped data (172 pages, 170 with tables)
│   └── joule_capabilities_raw.json  # Enriched output (216 capabilities)
├── analysis/
│   ├── analyzer.py           # Analysis utilities
│   └── __init__.py
├── generators/
│   ├── site_generator.py     # HTML site generator (hierarchical drilldown)
│   └── __init__.py
├── enrich_toc.py             # Main enrichment pipeline (TOC → JSON with scraped data)
├── main.py                   # Pipeline orchestrator
└── __init__.py
```

### Site Output
```
site/
├── index.html                # Generated single-page app (~492KB)
└── CNAME                     # easyassap.com
index.html                    # Copy of site/index.html for GitHub Pages root
```

### Key Commands
```bash
# Full pipeline (enrich → generate → deploy)
make all

# Individual steps
node pipeline/sources/scrape_help.js          # Scrape SAP Help (172 pages, ~8 min)
python3 -m pipeline.enrich_toc                # Enrich with scraped data
python3 -m pipeline.generators.site_generator # Generate HTML
cp site/index.html index.html                 # Copy to root for GitHub Pages
git add -A && git commit -m "msg" && git push # Deploy

# Local preview
make serve   # → http://localhost:4000
```

## Data Quality (v7)
- **216 total capabilities** (no "Mixed" type)
- **4 capability types**: Informational (59), Transactional (123), Navigational (27), Analytical (7)
- **19 SAP products** covered
- **103 pages with verified real scraped data** (out of 167 scraped)
- **100 capabilities with actual SAP-provided sample prompts**
- **102 capabilities with use case details**
- False positives filtered: sidebar nav captures, sidebar link captures

## Scraper Details
- Uses Puppeteer (headless Chrome) to render JavaScript-heavy SAP Help pages
- Targets `<table>` elements with use case rows
- Extracts: use case name, sample prompts, expected response
- False positive detection:
  - 233 use cases = sidebar navigation (skip)
  - 1 use case + "What's New" in prompts = sidebar links (skip)
  - 1 use case + 30+ prompts = sidebar content (skip)

## Ariba Misaligned Table Handling
SAP Ariba pages have a different table structure than other products:
- Standard: `Name | Sample Prompts | Response` 
- Ariba: `Sub-Product | Capability Type | Description`

The scraper maps columns as: `name → Sub-Product`, `prompts → [Capability Type]`, `response → Description`

**Detection** (`_is_misaligned_table` in `enrich_toc.py`):
- If >80% of rows have a single prompt value that's a capability type string → misaligned
- If any row's `name` is literally a capability type (e.g., "Transactional") → misaligned

**Restructuring**:
- Groups rows by sub-product name
- Aggregates capability types as badges
- Uses description text as actual prompts/capabilities
- For Intake Management edge case: if `name` is a type, `prompts[0]` becomes the use case name

**Result**: SAP Ariba Solutions → 6 grouped sub-products, 39 total capabilities with real prompts

## URL Handling
- **Scraped URLs**: Real URLs from SAP Help Portal are captured during scraping and carried through enrichment via `page_data.get("url", "")`
- **Fallback URLs**: For pages without scraped data, generated from slug: `https://help.sap.com/docs/joule/capabilities-guide/{slug}`

## Site Generator Features
- **ucCount**: Counts total individual capabilities (sum of prompts across use_cases)
- **Flattened products**: Single-capability products skip intermediate hierarchy levels
- **renderChildUseCase**: Shows sub-product name (bold), type badges (Navigational/Transactional), and all prompts as pills
- **Type badges**: Description field parsed — if all comma-separated values are capability types, rendered as colored badges

## Classification Rules (No Mixed)
Priority order: Analytical > Navigational > Transactional > Informational
- **Analytical**: Insights, forecasts, anomaly detection, AI-assisted, optimization
- **Navigational**: Find apps, launch, navigate, open, Siri, requesting access
- **Transactional**: Create, change, manage, process, execute, update, delete, transfer
- **Informational**: Display, show, view, search, list, check, fetch, summarize

## Crawl/Walk/Run Strategy (Arkansas)
- **Crawl**: Unified Joule + high-value, low-risk features
- **Walk**: Embedded AI features, broader adoption
- **Run**: Advanced AI projects, custom implementations

## Dependencies
- Python 3.x (no pip packages needed for core pipeline)
- Node.js + Puppeteer (`npm install` in project root)
- Git + GitHub CLI (gh)

## Key Design Decisions
1. **Single-page app**: All data embedded in `index.html` as JSON — no server needed
2. **Hierarchical drilldown**: Product → Business Area → Sub-Area → Use Cases with collapsible tree
3. **Sample prompts always visible**: Shown as blue pills below each use case (no toggle needed)
4. **Type filtering**: Click type cards or use dropdown to filter by Informational/Transactional/Navigational/Analytical
5. **Scraped URLs preferred**: `enrich_toc.py` carries through actual SAP Help URLs from scrape data
6. **Grouped sub-products**: Ariba-style tables auto-detected and restructured into grouped display

## What's Next
- Add Embedded AI features (non-Joule AI capabilities)
- Add recommended projects section with crawl/walk/run classification
- Enhance site design with better filtering and navigation
- Add data freshness indicators and auto-update workflow
- Consider splitting large products into sub-pages for performance