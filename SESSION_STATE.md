# Session State

> **Last Updated:** 2026-03-25  
> **Status:** Scraper complete, all data verified. Ready for analysis & site build.  
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

Scrapes the **Joule Capabilities Guide** from SAP Help Portal.

- **Deliverable ID:** `d0750ba6-6e30-455c-a879-af14f1054a14`
- **Source URL:** https://help.sap.com/docs/joule/capabilities-guide/
- **39 leaf pages + 1 root page**
- **214 leaf capabilities + 54 What's New entries = 268 total**
- **All Commercial Model = Base**

### Data fields (per capability)
- `use_case` — capability name
- `description` — full detail (may be list for multi-paragraph)
- `important_notes` — caveats and limitations
- `capability_type` — Navigational, Informational, Transactional, Analytical
- `sample_prompts` — example prompts (may be list)
- `commercial_model` — **Base** (all current entries)
- `on_mobile` — Yes/No
- `best_practices` — usage tips
- `source_page` — which leaf page
- `source_product` — parent product group
- `section` — section heading on the page (e.g., "Operational Purchaser")

### Key Counts by Page (verified)
| Page | Count | Sections / Types |
|------|-------|-----------------|
| SAP SuccessFactors Employee Central | 21 | Info:9, Nav:8, Trans:4 |
| Finance | 21 | Financial Planning, Financial Close, AP, AR, Fixed Asset, Treasury, Manage Internal Orders |
| Perform Maintenance Jobs | 17 | Info:4, Nav:4, Trans:9 |
| Sales | 14 | Info:5, Nav:5, Trans:4 |
| Procurement | 13 | Operational Purchaser:3, Central Purchaser:7, Business Network:2, Supplier Self Service:1 |
| SAP Analytics Cloud | 11 | Analytical:3, Info:5, Nav:3 |
| SAP Sales and Service Cloud | 10 | Info:2, Nav:1, Trans:7 |
| Manufacturing | 9 | Info:2, Nav:2, Trans:5 |
| Lifecycle and Performance (Ariba) | 9 | Nav:3, Trans:6 |
| Joule AI Assistant | 8 | Info:4, Nav:2, Trans:2 |
| SAP SuccessFactors Learning | 7 | Info:1, Trans:6 |
| Concur Expense | 5 | Info:2, Nav:1, Trans:2 |
| SAP Datasphere | 5 | Info:3, Nav:2 |
| Build Apps | 4 | Nav:2, Trans:2 |
| SAP Business Application Studio | 4 | Nav:2, Trans:2 |
| SAP Emarsys Customer Engagement | 4 | Info:1, Nav:1, Trans:2 |
| SAP SuccessFactors Compensation | 4 | Info:2, Trans:2 |
| SAP SuccessFactors Recruiting | 4 | Info:4 |
| SAP SuccessFactors Time Tracking | 4 | Info:1, Nav:1, Trans:2 |
| Supply Chain | 4 | Info:1, Nav:1, Trans:2 |
| Joule Studio | 4 | Trans:4 |
| Asset Management | 3 | Info:1, Nav:1, Trans:1 |
| SAP Commerce Cloud | 3 | Info:2, Trans:1 |
| SAP Integration Suite | 3 | Info:1, Trans:2 |
| Technology | 3 | Nav:3 |
| Warehouse Management | 3 | Info:1, Nav:1, Trans:1 |
| SAP SuccessFactors EC Payroll | 3 | Info:2, Nav:1 |
| Concur Travel | 2 | Nav:2 |
| Guided Buying | 2 | Nav:2 |
| Joule for SAP Business AI | 2 | Info:1, Trans:1 |
| SAP Fieldglass | 2 | Info:1, Nav:1 |
| SAP SuccessFactors Succession | 2 | Info:2 |
| SAP SuccessFactors Work Zone | 2 | Info:1, Nav:1 |
| Build Process Automation | 1 | Trans:1 |
| Guided Sourcing | 1 | Nav:1 |
| Human Resources | 1 | Nav:1 |
| SAP Customer Data Platform | 1 | Info:1 |
| Sourcing and Contract Mgmt | 1 | Nav:1 |
| Sustainability | 1 | Nav:1 |

## Technical Notes

- SAP Help content API: `https://help.sap.com/docs/content/{deliverable_id}/{page_id}`
- TOC API: `https://help.sap.com/docs/meta/{deliverable_id}/toc`
- SSL workaround needed: `ssl._create_unverified_context()` (macOS Python)
- Rate limiting: API sometimes returns empty/truncated content; scraper retries up to 3x
- "Perform Maintenance Jobs" page (80KB) is most rate-limit-prone
- TOC is live — SAP adds pages (e.g., "Lifecycle and Performance" added recently)

## Arkansas Approach

- **Crawl → Walk → Run** adoption strategy
- **Crawl phase** = Unified Joule + high-value, low-risk features
- All 214 capabilities are Commercial Model: **Base** (included in standard license)
- Website: **easyassap.com** (GitHub Pages from `JBShearer/Arkansas`)

## Next Steps

1. Build analysis pipeline for Arkansas crawl-phase recommendations
2. Build site pages from scraped data
3. Deploy to easyassap.com