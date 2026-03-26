# Session State — SAP Business AI / Joule Capabilities Website

> **Last updated:** 2026-03-26
> **Git commit:** v18 — Eliminate Mixed type, add tier badges, fix branch nodes, consistent UI
> **Live site:** https://easyassap.com (via GitHub Pages, CNAME configured)

---

## Project Overview

A Python-based pipeline that scrapes, enriches, cleans, and generates a website cataloging
SAP Business AI (Joule) capabilities across 18 SAP products. Built for the State
of Arkansas's crawl-walk-run AI adoption strategy.

### Architecture

```
pipeline/
├── sources/
│   ├── toc_tree.txt          # TOC hierarchy
│   ├── scrape_help.js         # Puppeteer scraper for SAP Help Portal
│   └── scrape_joule.py        # Python scraper (alternative)
├── data/
│   ├── scraped_use_cases.json # Raw scraped data (167 pages)
│   ├── tier_overrides.json    # Manual tier mapping (slug → base/premium/eac/beta)
│   ├── joule_capabilities_raw.json  # Enriched output (190 entries)
│   └── joule_capabilities_clean.json # Cleaned output (notes/prompts fixed)
├── enrich_toc.py              # Main enrichment pipeline (adds tier field, suppresses depth≤1 branch nodes)
├── clean_data.py              # Data quality cleaner (no Mixed type, resolves via prompt analysis)
├── main.py                    # Pipeline entry point (analyze/clean/generate/build)
├── generators/
│   └── site_generator.py      # HTML site generator (tier badges, consistent template, no Mixed)
└── analysis/
    └── analyzer.py            # Data analysis utilities
site/
├── index.html                 # Generated website
└── CNAME                      # easyassap.com
```

### Pipeline Flow

```
scrape → enrich → clean → generate → deploy
  │         │        │         │         │
  │    toc_tree.txt  │    clean.json    git push
  │    + scraped →   │    (fixed
  │    raw.json      │    prompts/notes/types)
  │                  │         │
  node scraper    enrich_toc  clean_data.py
```

### Key Numbers (v18)

| Metric | Count |
|--------|-------|
| Total entries | 190 |
| Products | 18 |
| Scraped (real data) | 114 |
| Title-only (no scraped data) | 76 |
| With sample prompts | 112 |
| With use case details | 113 |
| Use cases on site | 171 |

### Capability Type Distribution (after cleaning)

| Type | Count |
|------|-------|
| Transactional | 89 |
| Informational | 62 |
| Navigational | 10 |
| Mixed | 6 |
| Analytical | 4 |

### Data Cleaning Stats (v17)

| Metric | Count |
|--------|-------|
| Prompts moved to notes | 165 |
| Notes moved to prompts | 8 |
| Type reclassifications | 31 |

---

## Data Cleaning Pipeline (`clean_data.py`)

### What It Does
Reads `joule_capabilities_raw.json` → writes `joule_capabilities_clean.json`

1. **Prompts → Notes**: Moves descriptive/instructional text out of prompts arrays
   - "Joule displays...", "You must...", "Reading through..." etc.
   - Field labels like "Full Name Business Partner ID"
   - Long multi-sentence descriptions
2. **Notes → Prompts**: Moves actual user commands out of notes arrays
   - "For the BP 17100010, show me industry details"
   - "Show me...", "Display...", "Create..." patterns
3. **Type Reclassification**: Re-evaluates capability_type based on title and use case analysis
   - Infers Informational/Transactional/Navigational/Analytical/Mixed
4. **Rebuilds sample_prompts**: From cleaned use case prompts

### Pattern Lists
- `NOT_A_PROMPT_PATTERNS`: 50+ regex patterns for descriptive text
- `FIELD_LABEL_PATTERNS`: 30+ patterns for column headers/field labels
- `NOTE_IS_PROMPT_PATTERNS`: Patterns for commands that ended up in notes
- `DESCRIPTIVE_PROMPT_PATTERNS`: Long description patterns

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
- SAP Digital Manufacturing → Mixed (4 use cases, 12 prompts: production orders, yield/scrap, goods receipt, components, nonconformances, SOPs)
- SAP Risk and Assurance Management → Informational
- SAP Incentive Management → Transactional

### Skip List
Filters out non-capability pages: What's New, Archive, Glossary, Configuration, etc.

---

## Site Generator (`site_generator.py`)

### Features
- Reads `joule_capabilities_clean.json` (falls back to raw if clean not found)
- Responsive single-page HTML with embedded CSS/JS
- Product filter sidebar with capability counts
- Capability type filter (color-coded badges)
- Search across titles, prompts, descriptions
- Expandable use case cards with prompts, notes, parameters
- SAP Help Portal deep links
- Arkansas "crawl-walk-run" framing
- Mobile-friendly layout
- JS-level `isExplanatoryText()` as safety net (data is pre-cleaned)

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

---

## Completed Work

### Session 1 (v1–v14): Data Quality & Pipeline Build
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

### Session 2 (v15): Git Cleanup
1. ✅ Removed broken site/ gitlink (was tracked as submodule without .gitmodules)
2. ✅ Removed site/.git (separate repo with diverged v6 history)
3. ✅ Re-added site/ as regular tracked directory (CNAME + index.html)
4. ✅ Removed duplicate files from old site/ repo (.github/workflows, old HTML)

### Session 3 (v16): Data Quality Cleaning Pipeline
1. ✅ Identified 50+ data quality issues (notes as prompts, wrong types)
2. ✅ Created `pipeline/clean_data.py` — systematic data cleaner
3. ✅ Moved 165 descriptive texts from prompts → notes
4. ✅ Moved 8 actual commands from notes → prompts
5. ✅ Reclassified 31 capability types (better Informational/Transactional/Mixed split)
6. ✅ Updated site generator to read clean data (with raw fallback)
7. ✅ Integrated clean step into `main.py` pipeline and `Makefile`
8. ✅ Fixed Python SyntaxWarning (escaped regex in JS template)
9. ✅ Regenerated site from clean data — no warnings

### Session 4 (v17): Inline Styles → CSS Classes + Digital Manufacturing Fix
1. ✅ Converted all inline `style=` attributes in site_generator.py to CSS classes
   - `.subcat-header`, `.subcat-list`, `.subcat-item` — subcategory headers/lists
   - `.uc-inline-desc` — inline description next to use case name
   - `.cap-desc` — capability-level description block
   - `.cap-single-uc` — single use case name display
   - `.flat-badge-row` — flattened product badge/link row
2. ✅ Fixed Digital Manufacturing fallback — added 4 real use cases with 12 sample prompts
   - Production Order Information (4 prompts)
   - Yield, Scrap, and Goods Receipt (3 prompts)
   - Component Availability and Order Priorities (3 prompts)
   - Process Parameters and SOPs (2 prompts)
3. ✅ Fixed `TEXT_ONLY_PAGE_FALLBACK` branch to extract `sample_prompts` from fallback use cases
4. ✅ Verified zero inline `style=` attributes in generated HTML
5. ✅ Regenerated site from clean data (502KB, 216 entries, 171 use cases)

### Commits
- v13: Add fallback data for text-only pages
- v14: Clean up Signavio prompts - filter descriptions/fragments
- v15: Fix site/ broken submodule — convert to regular tracked directory
- v16: Data quality cleaning pipeline — fix prompts/notes/types
- v17: Inline styles → CSS classes + Digital Manufacturing fix

---

## Remaining Work / Known Issues

### Minor
- 102 entries still "title-only" — these are branch/category nodes without their own capability pages
- JS `isExplanatoryText()` still runs as safety net — could be removed now that data is pre-cleaned

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
# Full pipeline (enrich → clean → generate → deploy)
make all

# Individual steps
make enrich      # Re-enrich from TOC + scraped data
make cleandata   # Clean data quality (prompts↔notes, fix types)
make generate    # Regenerate site from clean data
make deploy      # Git commit + push

# Or via Python
python3 -m pipeline.main build    # analyze + clean + generate
python3 -m pipeline.main clean    # just clean data

# Re-scrape (takes ~8 min)
node pipeline/sources/scrape_help.js

# Local preview
make serve  # → http://localhost:4000
```

### Key Files to Edit
- **Add products**: `PRODUCT_MAP` in `enrich_toc.py`
- **Fix data quality**: `clean_data.py` (add patterns to NOT_A_PROMPT_PATTERNS etc.)
- **Fix enrichment**: `_is_note()`, `_is_parameter()`, `_DESCRIPTION_STARTS` in `enrich_toc.py`
- **Add fallback data**: `TEXT_ONLY_PAGE_FALLBACK` in `enrich_toc.py`
- **Change site design**: `site_generator.py`
- **Update TOC**: `pipeline/sources/toc_tree.txt`