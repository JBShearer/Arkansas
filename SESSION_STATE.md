# SESSION STATE — SAP Business AI Pipeline

> Last updated: 2025-03-25T13:07:00
> Use this file to resume work in new sessions.

## Architecture

```
/Users/I530341/Documents/Joule/
├── pipeline/                    # Python analysis pipeline
│   ├── enrich_toc.py           # TOC → enriched JSON (types, prompts, SAC)
│   ├── generators/
│   │   └── site_generator.py   # JSON → static HTML site
│   ├── sources/
│   │   ├── toc_tree.txt        # 228-page TOC from SAP Help
│   │   └── scrape_joule.py     # Headless scraper (future)
│   └── data/
│       └── joule_capabilities_raw.json  # Enriched data (217 entries)
├── site/                        # GitHub Pages (separate git repo)
│   ├── index.html              # Generated site
│   └── CNAME                   # easyassap.com
├── config.yaml                 # Pipeline configuration
├── requirements.txt            # Python dependencies
├── Makefile                    # Build commands
└── SESSION_STATE.md            # This file
```

## Key Design Decisions

### Capability Types (v6)
ALL capabilities are Joule GenAI. The type describes the INTERACTION PATTERN:
- **Informational** (45): Display, view, search, check data
- **Transactional** (42): Create, change, manage, process documents
- **Navigational** (15): Launch apps, navigate to screens, "Joule in SAP X" product availability
- **Analytical** (9): Insights, forecasting, anomaly detection (includes SAC entries)
- **Mixed** (106): Both informational + transactional in one capability

Key classification rules:
- "Joule in SAP X" **leaf** entries (no children) → **Navigational** (product availability pages)
- "Joule in SAP X" **branch** entries (with children) → aggregated from children types
- "Using Siri to Launch Joule" → **Navigational**
- Explicit `MIXED_CAPABILITIES` set for items that span display + create (e.g., Billing Request, Audit Journal)

### Sample Prompts (v6)
**173 capabilities** have sample prompts (all leaves + SAC integration):
- ~40 curated prompts in `SAMPLE_PROMPTS` dict
- Auto-generated prompts via `auto_generate_prompts()` for remaining capabilities
- Pattern matching: "Display X" → "Show me X", "Create X" → "Create a new X", etc.
- Navigational: "Joule in SAP X" → "Open X", "Take me to X"
- Displayed as always-visible 💬 pill badges (not hidden toggles)

### SAP Analytics Cloud
Special "Joule + SAC Integration" entry with:
- Analytical type badge
- Sample prompts for analytics queries
- "Coming Soon" note about conversational data exploration

## Git Repos
- **Pipeline**: `/Users/I530341/Documents/Joule/` (local git, no remote)
- **Site**: `/Users/I530341/Documents/Joule/site/` → `github.com/JBShearer/Arkansas` (main branch)
- **Live URL**: https://easyassap.com

## Regeneration
```bash
cd /Users/I530341/Documents/Joule
python3 -m pipeline.enrich_toc          # Enrich TOC → JSON
python3 -m pipeline.generators.site_generator  # JSON → HTML
cd site && git add -A && git commit -m "Update" && git push origin main
```

## Data Model (joule_capabilities_raw.json)
```json
{
  "title": "Display G/L Account Balance",
  "product": "SAP S/4HANA Cloud Private Edition",
  "business_area": "Finance",
  "sub_area": "",
  "capability_type": "Informational",
  "is_leaf": true,
  "is_branch": false,
  "slug": "display-gl-account-balance",
  "sap_help_url": "https://help.sap.com/docs/joule/capabilities-guide/display-gl-account-balance",
  "sample_prompts": ["Show me the balance for G/L account 100000"],
  "special_note": null
}
```

## Version History
- **v1**: Initial TOC parsing, basic site
- **v2**: Added capability types (Generative AI, Informational, etc.)
- **v3**: Refined types, added sample prompts
- **v4**: Removed "Generative AI" type (redundant), fixed Mixed classification
- **v5**: Auto-generated prompts for ALL 173 leaves, always-visible pill badges
- **v6**: Fixed Navigational classification — 15 "Joule in SAP X" products now correctly Navigational

## Next Steps
- [ ] Scrape actual SAP Help pages for richer sample prompts
- [ ] Add embedded AI features (Walk phase)
- [ ] Add recommended projects (Run phase)
- [ ] Add Arkansas-specific project recommendations
- [ ] Connect pipeline to auto-update when SAP docs change