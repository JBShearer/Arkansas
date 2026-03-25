# Session State

> **Last Updated:** 2026-03-25  
> **Status:** Scraper complete, ALL pages scraped, all spot checks pass.  
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

Scrapes **EVERY page** (branch + leaf) in the **Joule Capabilities Guide** TOC tree.

- **Deliverable ID:** `d0750ba6-6e30-455c-a879-af14f1054a14`
- **Source URL:** https://help.sap.com/docs/joule/capabilities-guide/
- **52 pages total** (39 leaves + 13 branches), **44 with content**
- **253 capabilities + 54 What's New = 307 total**
- **All Commercial Model = Base**
- Retry pass handles rate-limited pages (especially Perform Maintenance Jobs, 80KB)

### Data fields (per capability)
- `use_case`, `description`, `important_notes`, `capability_type`
- `sample_prompts`, `commercial_model`, `on_mobile`, `best_practices`
- `source_page`, `source_product`, `section`, `page_id`

### Verified Counts
| Page | Count | Key Detail |
|------|-------|------------|
| SF Employee Central | 21 | |
| Finance | 21 | 7 sections incl Manage Internal Orders |
| Perform Maintenance Jobs | 17 | 80KB page, rate-limit-prone |
| Sales | 14 | |
| S/4HANA Cloud (branch) | 14 | 4 journal entries, manufacturing, procurement |
| Procurement | 13 | Op Purchaser:3, Central:7, BizNet:2, Supplier:1 |
| SAP Analytics Cloud | 11 | |
| SAP Sales and Service Cloud | 10 | |
| Concur total | 10 | Branch:3 + Expense:5 + Travel:2 |
| Manufacturing | 9 | |
| Ariba Lifecycle & Performance | 9 | |
| Joule AI Assistant | 8 | |
| SF Learning | 7 | |
| Work Zone Advanced Edition | 5 | Branch page |
| BTP Cockpit (branch) | 4 | General, Subscriptions, Services, Security |
| SAP Cloud ALM (branch) | 4 | Analytics, Projects, Operations, Config |
| SF Compensation | 4 | |

## Technical Notes

- SAP Help content API: `https://help.sap.com/docs/content/{deliverable_id}/{page_id}`
- TOC API: `https://help.sap.com/docs/meta/{deliverable_id}/toc`
- SSL workaround: `ssl._create_unverified_context()` (macOS Python)
- Rate limiting: scraper retries up to 5x per page + dedicated retry pass at end
- TOC is live — SAP adds pages over time
- **ONLY use Capabilities Guide** — do NOT scrape other deliverables

## Arkansas Approach

- **Crawl → Walk → Run** adoption strategy
- **Crawl phase** = Unified Joule + high-value, low-risk features
- All 253 capabilities are Commercial Model: **Base**
- Website: **easyassap.com** (GitHub Pages from `JBShearer/Arkansas`)

## Next Steps

1. Build analysis pipeline for Arkansas crawl-phase recommendations
2. Build site pages from scraped data
3. Deploy to easyassap.com