# Session State — SAP Business AI / Joule Capabilities Website

> **Last updated:** 2025-03-25T18:33 MDT  
> **Git commit:** v14 (d4d2020) — Clean up Signavio prompts  
> **Live site:** https://easyassap.com (via GitHub Pages, CNAME configured)

---

## Project Overview

A Python-based pipeline that scrapes, enriches, and generates a website cataloging
SAP Business AI (Joule) capabilities across 18 SAP products. Built for the State
of Arkansas's crawl-walk-run AI adoption strategy.

### Architecture

```
pipeline/
├── sources/
│   ├── toc_tree.txt          # TOC hierarchy (216 entries after skip filtering)
│   ├── scrape_help.js         # Puppeteer scraper for SAP Help Portal
│   └── scrape_joule.py        # Python scraper (alternative)
├── data/
│   ├── scraped_use_cases.json # Raw scraped data (167 pages)
│   └── joule_capabilities_raw.json  # Enriched output (216 entries)
├── enrich_toc.py              # Main enrichment pipeline
├── generators/
│   └── site_generator.py      # HTML site generator
└── analysis/
    └── analyzer.py            # Data analysis utilities
site/
├── index.html                 # Generated website
└── CNAME                      # easyassap.com
```

### Key Numbers (v14)

| Metric | Count |
|--------|-------|
| Total entries | 216 |
| Products | 18 |
| Scraped (real data) | 114 |
| Title-only (no scraped data) | 102 |
| With sample prompts | 111 |
| With use case details | 113 |
| Use cases on site | 171 |

### Capability Type Distribution

| Type | Count |
|------|-------|
| Transactional | 124 |
| Informational | 61 |
| Navigational | 24 |
| Analytical | 7 |

---

## Enrichment Pipeline (`enrich_toc.py`)

### What It Does
1. Parses `toc_tree.txt` hierarchy
2. Matches each entry to scraped page data (fuzzy title matching)
3. Validates scraped data quality (filters sidebar nav false positives)
4. Extracts use cases with smart table layout detection:
   - Standard tables (most S/4HANA pages)
   - Category-column tables (SuccessFactors style)
   - Misaligned tables (Ariba style)
   - Text-only pages (Digital Manufacturing, Risk & Assurance, Incentive Mgmt)
5. Classifies prompts vs notes vs parameters vs descriptions
6. Merges duplicate use cases
7. Assigns capability types (Informational/Transactional/Navigational/Analytical)

### Data Quality Features
- **`is_good_scraped_data()`**: Filters sidebar navigation (233 use cases, "What's New" patterns, >30 prompts)
- **`_fuzzy_match_scraped_page()`**: Handles title mismatches (e.g., "Work Zone" vs "Work Zone, advanced edition")
- **`_is_note()`**: Classifies instructional text, response-option descriptions, description-style text
- **`_is_parameter()`**: Identifies parameter names vs prompts
- **`_is_response_description()`**: Detects "Joule displays..." descriptions vs actual prompts
- **`_split_response_into_prompts()`**: Handles concatenated prompts, rejoins broken lines
- **`_DESCRIPTION_STARTS`**: Regex matching description patterns (also used in `_is_note`)
- **Fragment filtering**: Removes lowercase continuations, preposition-starting fragments, quoted refs

### Text-Only Page Fallback (`TEXT_ONLY_PAGE_FALLBACK`)
For pages without tables where the scraper captured sidebar nav:
- SAP Digital Manufacturing → Informational (doc search)
- SAP Risk and Assurance Management → Informational
- SAP Incentive Management → Transactional

### Skip List
Filters out non-capability pages: What's New, Archive, Glossary, Configuration, etc.

---

## Site Generator (`site_generator.py`)

### Features
- Responsive single-page HTML with embedded CSS/JS
- Product filter sidebar with capability counts
- Capability type filter (color-coded badges)
- Search across titles, prompts, descriptions
- Expandable use case cards with prompts, notes, parameters
- SAP Help Portal deep links
- Arkansas "crawl-walk-run" framing
- Mobile-friendly layout

---

## Scraper (`scrape_help.js`)

### How It Works
- Puppeteer-based, navigates SAP Help Portal TOC
- Extracts tables from each capability page
- Maps columns: name | prompts/samplePrompts | response/description
- Saves to `scraped_use_cases.json`

### Known Limitations
- Text-only pages (no tables) → captures sidebar nav instead
  - **Workaround**: `TEXT_ONLY_PAGE_FALLBACK` in `enrich_toc.py`
- Some Signavio prompts still have description fragments starting uppercase
  - Minor issue, prompts are still usable

---

## Completed Work (This Session)

### Data Quality Fixes
1. ✅ Fixed "0 prompts" display — extracted prompts from response column
2. ✅ Fixed note formatting — separated notes from prompts
3. ✅ Separated cautions/warnings from notes
4. ✅ Fixed misclassified prompts (response descriptions, instructional text)
5. ✅ Full data quality audit across all 18 products
6. ✅ Added fuzzy page title matching (fixed Work Zone)
7. ✅ Fixed Logistics, Ariba, Batch Release, Concur, Sports One data
8. ✅ Fixed `is_good_scraped_data` to check samplePrompts + description keys
9. ✅ Re-enriched and unlocked Signavio, IPD, IBP data
10. ✅ Added fallback data for text-only pages (Digital Mfg, Risk & Assurance, Incentive Mgmt)
11. ✅ Cleaned up Signavio prompts (descriptions filtered from samplePrompts)

### Commits
- v13: Add fallback data for text-only pages
- v14: Clean up Signavio prompts - filter descriptions/fragments

---

## Remaining Work / Known Issues

### Minor
- A few Signavio prompts still have uppercase description fragments (e.g., "Process Intelligence based on..." in Performance Indicator Recommender)
- 102 entries still "title-only" — these are branch/category nodes without their own capability pages

### Future Enhancements
- Improve scraper to handle text-only pages natively
- Add crawl/walk/run phase recommendations per capability
- Add embedded AI features catalog (non-Joule)
- Add recommended projects section
- Add risk/complexity scoring for implementation planning
- Consider breaking large product pages into sub-tabs

---

## How to Continue

```bash
# Re-run enrichment pipeline
python3 -m pipeline.enrich_toc

# Regenerate site
python3 -m pipeline.generators.site_generator

# Deploy
cp site/index.html index.html
git add -A && git commit -m "description" && git push

# Full pipeline
make all  # or: python3 -m pipeline.main

# Re-scrape (takes ~8 min)
node pipeline/sources/scrape_help.js
```

### Key Files to Edit
- **Add products**: `PRODUCT_MAP` in `enrich_toc.py`
- **Fix data quality**: `_is_note()`, `_is_parameter()`, `_DESCRIPTION_STARTS` in `enrich_toc.py`
- **Add fallback data**: `TEXT_ONLY_PAGE_FALLBACK` in `enrich_toc.py`
- **Change site design**: `site_generator.py`
- **Update TOC**: `pipeline/sources/toc_tree.txt`