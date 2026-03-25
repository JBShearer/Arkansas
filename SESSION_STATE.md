# Session State – SAP Business AI / Joule Pipeline

> **Last Updated:** 2026-03-25  
> **Status:** Site LIVE at easyassap.com — 312 capabilities with interactive explorer  
> **Read this file at the start of every new Cline session.**

## Quick Resume
```bash
cd /Users/I530341/Documents/Joule
cat SESSION_STATE.md
```

## Repository
- **Remote:** https://github.com/JBShearer/Arkansas.git
- **Branch:** main
- **GitHub Pages:** easyassap.com — serves from **root** (`/`), path setting = `/`
- **CNAME:** `site/CNAME` contains `easyassap.com`

## Architecture
```
index.html             ← DEPLOYED (copy of site/index.html, served by GitHub Pages)
site/
  index.html           ← generated output
  Arkansas_Joule_Capabilities.html  ← standalone copy
  CNAME                ← custom domain
pipeline/
  sources/
    scrape_joule.py    ← selenium scraper → pipeline/data/joule_capabilities_raw.json
    loader.py          ← loads JSON
    toc_tree.txt       ← 202-page Joule help.sap.com TOC
  analysis/
    analyzer.py        ← enrichment & classification
  generators/
    site_generator.py  ← reads JSON → site/index.html + root index.html
  data/                ← intermediate data (gitignored except .gitkeep)
  main.py              ← orchestrator
config.yaml
Makefile
```

## How to Regenerate
```bash
python3 -m pipeline.sources.scrape_joule        # ~15 min, needs Chrome
python3 -m pipeline.generators.site_generator    # rebuilds HTML → site/ AND root
git add -A && git commit -m "Update capabilities" && git push origin main
```

## Data Snapshot (25 Mar 2026)
| Metric | Value |
|--------|-------|
| Pages scraped | 228 |
| Raw capabilities | 366 |
| After dedup/filtering | 312 |
| S/4 Private Edition | 140 |
| S/4 Public Edition | 47 |
| SuccessFactors | 53 |
| Premium (SAP Business AI) | 68 |
| Base (Standard) | 190 |
| Base (Included) | 47 |

## Site Features
- Interactive card-based explorer with expand/collapse
- Filter by: Type (Nav/Info/Trans), Product, Process Area, Licensing
- Full-text search across use cases, descriptions, prompts
- Licensing badges: Base Standard, Premium (SAP Business AI), Base Included
- Each card shows: description, sample prompts, notes, best practices, mobile support

## Key Decisions
1. **GitHub Pages serves from root** — `index.html` at repo root (not `/site`)
2. Generator writes to both `site/index.html` AND root `index.html`
3. **Crawl-Walk-Run** — Arkansas is in "Crawl" phase
4. **Self-contained HTML** — all entries embedded as JSON (no backend)
5. **Data is gitignored** — regenerate with scraper

## Scraper Notes
- **TOC source:** `pipeline/sources/toc_tree.txt` (manually maintained)
- **Content API:** `https://help.sap.com/docs/content/{DELIVERABLE_ID}/{slug}`
- **Deliverable ID:** `d0750ba6-6e30-455c-a879-af14f1054a14`
- Do NOT use the TOC API — it returns stale 52-page subset
- Deduplicates by (topic_id, use_case, section)

## Next Steps
- [ ] Add Arkansas-specific Crawl/Walk/Run classification
- [ ] Add Embedded AI (non-Joule) features
- [ ] Add recommended projects section
- [ ] Improve mobile responsiveness
- [ ] Add analytics / visitor tracking