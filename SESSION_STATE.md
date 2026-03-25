# Session State – SAP Business AI / Joule Pipeline

> **Last Updated:** 2026-03-25 12:37 MDT  
> **Status:** Site LIVE at easyassap.com — Hierarchical Drilldown Explorer (140KB, 216 capabilities, 175 use cases)  
> **Read this file at the start of every new Cline session.**

## Quick Resume
```bash
cd /Users/I530341/Documents/Joule
cat SESSION_STATE.md
```

## Repository & Deployment

**IMPORTANT:** There are TWO git repos in the workspace:

1. **Site repo** (`/Users/I530341/Documents/Joule/site/`)
   - Remote: `https://github.com/JBShearer/Arkansas.git`
   - Branch: `main`
   - This is what GitHub Pages deploys to **easyassap.com**
   - Contains ONLY: `.github/workflows/static.yml`, `CNAME`, `index.html`
   - **All pushes to deploy the site must happen from this directory**

2. **Pipeline repo** (`/Users/I530341/Documents/Joule/`)
   - NO remote (removed to prevent accidental overwrites)
   - Contains the Python pipeline, config, and source data
   - Local-only; does NOT push to GitHub

## Architecture
```
/Users/I530341/Documents/Joule/          ← Pipeline workspace (NO git remote)
  pipeline/
    sources/
      scrape_joule.py                    ← scraper (SPA blocked; needs headless browser)
      loader.py
      toc_tree.txt                       ← 228-page TOC (indented text tree)
    analysis/
      analyzer.py
    generators/
      site_generator.py                  ← reads enriched JSON → site/index.html
    enrich_toc.py                        ← TOC → enriched JSON with types/hierarchy
    data/                                ← intermediate data (gitignored)
      joule_capabilities_raw.json        ← 216 capabilities (enriched with types)
    main.py
  site/                                  ← SEPARATE GIT REPO → JBShearer/Arkansas
    .github/workflows/static.yml         ← Pages deployment workflow
    index.html                           ← the deployed site (140KB)
    CNAME                                ← easyassap.com
  config.yaml
  Makefile
  SESSION_STATE.md
```

## Pipeline Steps (How to Regenerate & Deploy)
```bash
cd /Users/I530341/Documents/Joule

# 1. Enrich TOC tree into structured JSON with types/hierarchy
python3 -m pipeline.enrich_toc

# 2. Generate HTML site from enriched data
python3 -m pipeline.generators.site_generator

# 3. Verify
wc -c site/index.html   # should be ~140KB

# 4. Deploy (MUST push from site/ directory)
cd site
git add -A && git commit -m "Update capabilities" && git push origin main
```

## Data Model (joule_capabilities_raw.json)
Each capability entry has:
```json
{
  "title": "Display G/L Account Balance",
  "product": "SAP S/4HANA Cloud Private Edition",
  "business_area": "Finance",
  "sub_area": "",
  "capability_type": "Informational",      ← Informational|Navigational|Transactional|Analytical|Generative AI
  "is_leaf": true,
  "depth": 2,
  "hierarchy": "Joule in SAP S/4 ... > Finance > Display G/L Account Balance",
  "slug": "display-g-l-account-balance",
  "sap_help_url": "https://help.sap.com/docs/joule/capabilities-guide/display-g-l-account-balance",
  "children_count": 0
}
```

## Capability Type Classification
Types are inferred from title keywords in `enrich_toc.py`:
- **Informational** (51): Display, Show, View, Search, List, Check, Get
- **Navigational** (7): Navigate to, Go to, Open App
- **Transactional** (53): Create, Manage, Process, Execute, Post, Release, Clearing, Approve
- **Analytical** (5): Analytics, Insights, Anomaly, Forecast
- **Generative AI** (98): Everything else (content gen, audit, custom)
- **Cross-Area** (2): Multi-area capabilities

## SAP Help Portal URLs
URLs follow the pattern:
```
https://help.sap.com/docs/joule/capabilities-guide/{slug}
```
Where `{slug}` is the kebab-cased title. **Verified working** — pages load with Prerequisites, Use Cases, Example Prompts tables.

## Site UI Features
- **Header**: Crawl → Walk → Run phase bar with Arkansas branding
- **Stats bar**: Total entries, use cases, products, type counts
- **Type cards**: 5 clickable cards (Informational, Navigational, Transactional, Analytical, Generative AI) with descriptions and counts — click to filter
- **Filter bar**: Search, Product dropdown, Business Area dropdown, Type dropdown
- **Hierarchical tree**: Product → Business Area → Sub-area → Use Case
  - Click arrows to expand/collapse
  - Each use case shows type badge + "View in SAP Help →" link
- **Responsive**: Mobile-optimized layout

## Data Snapshot (25 Mar 2026 — v3 enriched with types)
| Metric | Value |
|--------|-------|
| TOC pages (toc_tree.txt) | 228 |
| Capabilities after enrichment | 216 |
| Leaf use cases | 175 |
| Branch nodes | 41 |
| S/4 Private Edition | 140 |
| S/4 Public Edition | 42 |
| SuccessFactors | 17 |
| SAP Analytics Cloud | 2 |
| Other products | 15 (1 each) |
| Informational | 51 |
| Transactional | 53 |
| Navigational | 7 |
| Analytical | 5 |
| Generative AI | 98 |
| site/index.html | ~140KB |

## Scraping Status
SAP Help Portal moved to a Vue.js SPA in 2026. All URLs return the same HTML shell; content is loaded client-side via JavaScript.

**To get deep content (descriptions, prompts, tables):**
- Use Puppeteer/Playwright headless browser
- Or intercept the XHR API calls the SPA makes
- Current approach: derive structure from TOC, link out to SAP Help for details

## Key Decisions
1. **Site repo is separate** — `site/` has its own `.git`; parent Joule dir has NO remote
2. **GitHub Pages uses Actions workflow** — `.github/workflows/static.yml` deploys on push
3. **Crawl-Walk-Run** — Arkansas is in "Crawl" phase (Unified Joule + high value/low risk)
4. **Self-contained HTML** — all entries embedded as JSON (no backend)
5. **Data is gitignored** — regenerate with pipeline
6. **TOC-enriched data** — product/area/type derived from hierarchy, deep scrape pending
7. **Capability types** — classified by title keywords, not page content scraping

## Next Steps
- [ ] Add Arkansas-specific Crawl/Walk/Run classification per capability
- [ ] Add Embedded AI (non-Joule) features
- [ ] Add recommended projects section
- [ ] Implement headless browser scraping for descriptions/prompts
- [ ] Improve mobile responsiveness
- [ ] Add analytics / visitor tracking