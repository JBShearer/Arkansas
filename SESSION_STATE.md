# Session State

> **Last Updated:** 2026-03-25  
> **Status:** Full tree scraper complete — 202 pages, 366 capabilities.  
> **Read this file at the start of every new Cline session.**

## What Exists

| Item | Path / Detail |
|------|--------------|
| Workspace | `/Users/I530341/Documents/Joule/` |
| GitHub repo | `JBShearer/Arkansas` (origin, main branch) |
| Site folder | `site/` — deployed to **easyassap.com** via GitHub Pages |
| Pipeline | `pipeline/` — Python scraper + analysis + site generator |
| Data | `pipeline/data/joule_capabilities_raw.json` (gitignored, regenerate with scraper) |

## Scraper

**Run:** `python3 -m pipeline.sources.scrape_joule`

### Architecture
- **TOC source:** `pipeline/sources/toc_tree.txt` (indented text tree, easy to update)
- **Slug-based fetching:** auto-generates URL slugs from page titles
- **Content API:** `https://help.sap.com/docs/content/{DELIVERABLE_ID}/{slug}`
- The TOC API (`/docs/meta/.../toc`) returns a STALE 52-page subset — do NOT use it
- Deduplicates entries by (topic_id, use_case, section)

### Stats
- **Deliverable ID:** `d0750ba6-6e30-455c-a879-af14f1054a14`
- **228 pages** (183 leaves, 45 branches), **~95 with table entries**
- **366 deduplicated capabilities** (418 raw, 52 removed as duplicates from slug collisions)
- **S/4HANA = 267 capabilities (73% of total)**
  - S/4 Public Edition: 70 (Finance 21, Sales 14, Finding Apps 17, etc.)
  - S/4 Private Edition: 197 (Sales 30, Finance 43, Supply Chain 20, Service 18, Procurement 17, BRIM 16, Manufacturing 15, etc.)
- **Other products: 99** (SuccessFactors 57, Concur 10, Ariba 9, Analytics 11, etc.)

### Data fields (per capability)
- `use_case`, `description`, `important_notes`, `capability_type`
- `sample_prompts`, `commercial_model`, `on_mobile`, `best_practices`
- `source_page`, `source_path`, `section`, `slug`, `topic_id`

### Verified Spot Checks (all pass)
| Check | Count |
|-------|-------|
| Perform Maintenance Jobs | 17 |
| Finance (Public Edition) | 21 |
| Employee Central Use Cases | 21 |
| What's New | 54 |
| Concur Solutions (total) | 10 |
| Work Zone Advanced | 5 |
| BTP Cockpit | 4 |
| Risk and Assurance Management | 2 |
| Digital Manufacturing | 1 |
| Create Billing Documents | 2 |
| Manufacturing Supervisor | 2 |
| Audit Journal | 1 |

### Adding New Pages
When SAP adds pages to the Capabilities Guide:
1. Edit `pipeline/sources/toc_tree.txt` — add the page title with proper indentation
2. Re-run `python3 -m pipeline.sources.scrape_joule`
3. Slugs are auto-generated from titles

## Technical Notes
- **ONLY use Capabilities Guide** — do NOT scrape other SAP Help deliverables
- Slug collisions: pages with same name in Public/Private Edition resolve to same content
  (unique child pages capture all distinct PE content)
- Rate limiting: scraper retries up to 5x per page + dedicated retry pass
- SSL workaround: `ssl._create_unverified_context()` (macOS Python)

## Arkansas Approach
- **Crawl → Walk → Run** adoption strategy
- **Crawl phase** = Unified Joule + high-value, low-risk features
- Website: **easyassap.com** (GitHub Pages from `JBShearer/Arkansas`)

## Next Steps
1. Build analysis pipeline for Arkansas crawl-phase recommendations
2. Build site pages from scraped data
3. Deploy to easyassap.com