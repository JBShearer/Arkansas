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
make generate  # Generate site HTML + copy to root
make deploy    # Git add/commit/push
make all       # Full pipeline: enrich → generate → deploy
make scrape    # Re-scrape SAP Help Portal (requires Puppeteer, ~8 min)
make serve     # Local preview on port 4000
```

## Data Pipeline
1. **Scrape**: `node pipeline/sources/scrape_help.js` → scraped_use_cases.json (167 pages)
2. **Enrich**: `python3 -m pipeline.enrich_toc` → joule_capabilities_raw.json (216 entries)
3. **Generate**: `python3 -m pipeline.generators.site_generator` → site/index.html
4. **Deploy**: `git push` → GitHub Pages

## Data Quality Features (Current)
- **No Mixed type** — all capabilities get exactly one type (Informational/Transactional/Navigational/Analytical)
- **Fuzzy title matching** — scraped page titles matched to TOC titles even with suffixes (e.g., "Work Zone, advanced edition")
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
- 108 pages with real scraped data, 108 title-only
- 108 capabilities with sample prompts, 107 with use case details
- 4 capability types: Informational (59), Transactional (123), Navigational (27), Analytical (7)

## Site Features
- Hierarchical tree-based drilldown: Product → Business Area → Sub-Area → Use Cases
- Type filter cards: Informational, Transactional, Analytical, Navigational
- Search bar with text search across titles, hierarchies, and use case names
- Product and Business Area dropdown filters
- Sample prompts shown as pill badges with 💬 prefix
- Collapsible capability groups with child use cases
- Subcategory grouping (e.g., SuccessFactors Feature Areas)
- Notes and parameters displayed inline
- Links to SAP Help Portal for each capability
- "Documentation Pending" badge for title-only entries (no misleading type badges)
- Responsive design for mobile/tablet
- Crawl → Walk → Run adoption framework header

## Key Products & Capability Counts
- SAP S/4HANA Cloud Private Edition: 140 entries (1,067 individual capabilities)
- SAP SuccessFactors: 15 entries (313 capabilities)
- SAP S/4HANA Cloud Public Edition: 43 entries (87 capabilities)
- SAP Logistics Management: 1 entry (62 capabilities)
- SAP Ariba Solutions: 2 entries (40 capabilities)
- SAP Concur Solutions: 1 entry (24 capabilities)
- SAP Batch Release Hub: 1 entry (17 capabilities)
- SAP Analytics Cloud: 3 entries (11 capabilities)

## Recent Changes
- v11: Title-only entries show "📋 Documentation Pending" badge instead of misleading Navigational tag; dimmed styling for placeholder entries
- v10: Data quality audit — fuzzy title matching (fixes Work Zone), Logistics prompts cleanup, Ariba hierarchy, Batch Release/Field Service description swap, "Search X as follows:" and "By X" parameter patterns
- v9: Remove prompt counts, notes always on new line left-aligned, cautions separated from info notes with ⚠️ warning style
- v8: Verified and redeployed with latest enriched data
- v7: Response line rejoining, note suppression, fragment filtering, f-string fix
- v6: Response-option detection, verb exclusions, continuation fragments
- v5: Note/parameter/prompt separation, category-column tables, misaligned tables
- v4: Real scraped data integration, no Mixed type
- v3: Tree-based UI with drilldown

## How to Continue Working in New Sessions
1. Read this file first: `SESSION_STATE.md`
2. Key files to review:
   - `pipeline/enrich_toc.py` — data enrichment logic
   - `pipeline/generators/site_generator.py` — HTML generation
   - `pipeline/sources/toc_tree.txt` — TOC hierarchy
   - `pipeline/data/joule_capabilities_raw.json` — enriched data
3. To regenerate: `make all` (enrich → generate → deploy)
4. To re-scrape from SAP Help: `make scrape` then `make all`