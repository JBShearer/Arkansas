# Session State — SAP Business AI Joule Capabilities Explorer

## Project Status: PRODUCTION ✅
- **Live at**: https://easyassap.com (GitHub Pages)
- **Repository**: https://github.com/JBShearer/Arkansas

## Architecture
```
pipeline/
  sources/         # Data acquisition
    toc_tree.txt   # TOC from SAP Help (216 entries)
    scrape_help.js # Puppeteer scraper for SAP Help Portal
    scrape_joule.py # Python-based scraper (alternative)
  data/            # Generated data
    scraped_use_cases.json  # Raw scraped data (167 pages)
    joule_capabilities_raw.json  # Enriched capabilities
  enrich_toc.py    # TOC enrichment pipeline
  analysis/        # Analysis modules  
  generators/
    site_generator.py  # HTML site generation
site/
  index.html       # Generated site (served by GitHub Pages)
  CNAME            # Custom domain config
```

## Key Commands
```bash
make enrich    # Enrich TOC with scraped data
make site      # Generate site HTML
make deploy    # Git add/commit/push
make all       # Full pipeline: enrich → site → deploy
```

## Data Pipeline
1. **Scrape**: `node pipeline/sources/scrape_help.js` → scraped_use_cases.json (167 pages)
2. **Enrich**: `python3 -m pipeline.enrich_toc` → joule_capabilities_raw.json (216 entries)
3. **Generate**: `python3 -m pipeline.generators.site_generator` → site/index.html
4. **Deploy**: `git push` → GitHub Pages

## Data Quality Features (Current)
- **No Mixed type** — all capabilities get exactly one type (Informational/Transactional/Navigational/Analytical)
- **Category-column detection** — SuccessFactors tables with Feature Area column handled correctly
- **Misaligned table detection** — Ariba tables with swapped columns handled correctly
- **Note/Parameter/Prompt separation** — intelligent classification of scraped text
- **Response-option filtering** — Submit:/Cancel:/Retype: button descriptions → notes (suppressed in renderer)
- **Line rejoining** — mid-sentence line breaks in response text properly reassembled
- **Instructional prefix stripping** — "Ask for example:", "Show the following:" detected and handled
- **Continuation fragment filtering** — lowercase starts, "to ..." fragments excluded
- **Duplicate merging** — use cases with same name grouped with all prompts collected

## Stats (Current)
- 216 total entries, 171 use cases, 18 products
- 100 pages with real scraped data, 116 title-only
- 1,564 total prompts across all use cases
- 4 capability types: Informational (59), Transactional (123), Navigational (27), Analytical (7)

## Recent Changes
- v7: Response line rejoining, note suppression, fragment filtering, f-string fix
- v6: Response-option detection, verb exclusions, continuation fragments
- v5: Note/parameter/prompt separation, category-column tables, misaligned tables
- v4: Real scraped data integration, no Mixed type
- v3: Tree-based UI with drilldown
