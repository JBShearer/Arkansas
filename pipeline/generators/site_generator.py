"""Generate the Joule Capabilities Explorer site as a hierarchical drilldown.

Reads pipeline/data/joule_capabilities_clean.json → site/index.html
(Falls back to joule_capabilities_raw.json if clean version not found.)
Builds a tree-based UI: Product → Business Area → Use Cases
with capability type filtering and sample prompts.

Usage:
    python3 -m pipeline.generators.site_generator
"""

import json
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent.parent
DATA_FILE_CLEAN = WORKSPACE / "pipeline" / "data" / "joule_capabilities_clean.json"
DATA_FILE_RAW = WORKSPACE / "pipeline" / "data" / "joule_capabilities_raw.json"
OUT_FILE = WORKSPACE / "site" / "index.html"


def generate():
    # Prefer cleaned data; fall back to raw
    data_file = DATA_FILE_CLEAN if DATA_FILE_CLEAN.exists() else DATA_FILE_RAW
    print(f"📂 Reading: {data_file.name}")
    data = json.load(open(data_file))
    caps = data["capabilities"]
    meta = data["metadata"]

    caps_json = json.dumps(caps, ensure_ascii=False)

    products = set(c["product"] for c in caps)
    leaves = [c for c in caps if c["is_leaf"]]
    type_counts = {}
    for c in caps:
        t = c["capability_type"]
        type_counts[t] = type_counts.get(t, 0) + 1

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Joule Capabilities Explorer</title>
<style>
:root {{
  --joule:        #7b2fbe;
  --joule-light:  #b57bee;
  --joule-dim:    rgba(123,47,190,0.18);
  --bg:           #0e0f14;
  --bg-raised:    #16181f;
  --bg-surface:   #1c1f2a;
  --border:       rgba(255,255,255,0.1);
  --text:         #eef1f7;
  --text-muted:   #8b92a8;
  --link:         #c4a6f5;
  --type-info:    #5edfff;
  --type-nav:     #c4a6f5;
  --type-trans:   #6ee89a;
  --type-anal:    #ffab6e;
}}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:var(--bg); color:var(--text); min-height:100vh; }}

/* ── HEADER ── */
.header {{
  position:sticky; top:0; z-index:200;
  background:var(--bg-raised);
  border-bottom:1px solid var(--border);
  display:flex; align-items:center; gap:1rem; padding:0 1.25rem; height:54px;
}}
.hamburger {{ display:none; background:none; border:none; color:var(--text); cursor:pointer; font-size:1.2rem; padding:4px 6px; line-height:1; }}
.header-logo {{ display:flex; align-items:center; gap:0.5rem; flex-shrink:0; }}
.joule-mark {{
  width:26px; height:26px; border-radius:6px;
  background:linear-gradient(135deg,#7b2fbe,#b06be8);
  display:flex; align-items:center; justify-content:center;
  font-size:0.85rem; font-weight:900; color:white; letter-spacing:-0.5px;
}}
.header-title {{ font-size:0.92rem; font-weight:700; white-space:nowrap; }}
.header-title span {{ color:var(--joule-light); }}
.header-search {{ flex:1; max-width:420px; position:relative; }}
.header-search input {{
  width:100%; padding:0.38rem 0.8rem 0.38rem 2rem;
  background:rgba(255,255,255,0.06); border:1px solid var(--border);
  border-radius:6px; color:var(--text); font-size:0.83rem; outline:none;
  transition:border-color .2s;
}}
.header-search input::placeholder {{ color:var(--text-muted); }}
.header-search input:focus {{ border-color:var(--joule-light); }}
.header-search .si {{ position:absolute; left:0.6rem; top:50%; transform:translateY(-50%); color:var(--text-muted); font-size:0.78rem; pointer-events:none; }}

/* ── LAYOUT ── */
.layout {{ display:flex; min-height:calc(100vh - 54px); }}

/* ── SIDEBAR ── */
.sidebar {{
  width:232px; flex-shrink:0; background:var(--bg-raised);
  border-right:1px solid var(--border);
  position:sticky; top:54px; height:calc(100vh - 54px);
  overflow-y:auto; display:flex; flex-direction:column;
}}
.sidebar-inner {{ padding:0.65rem 0 1rem; }}
.sidebar-section-label {{
  font-size:0.62rem; font-weight:700; letter-spacing:0.09em;
  text-transform:uppercase; color:var(--text-muted);
  padding:0.6rem 1rem 0.25rem;
}}
.sidebar-item {{
  display:flex; align-items:center; gap:0.5rem;
  padding:0.38rem 1rem; cursor:pointer; font-size:0.81rem;
  color:var(--text-muted); border-left:3px solid transparent;
  transition:all .15s;
}}
.sidebar-item:hover {{ color:var(--text); background:rgba(255,255,255,0.04); }}
.sidebar-item.active {{
  color:var(--joule-light); font-weight:600;
  background:var(--joule-dim); border-left-color:var(--joule-light);
}}
.sidebar-dot {{ width:7px; height:7px; border-radius:50%; flex-shrink:0; }}
.sidebar-name {{ flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
.sidebar-count {{
  font-size:0.65rem; padding:0.08rem 0.4rem; border-radius:8px;
  background:rgba(255,255,255,0.07); color:var(--text-muted); flex-shrink:0;
}}
.sidebar-item.active .sidebar-count {{ background:var(--joule-dim); color:var(--joule-light); }}

/* mobile overlay */
.sidebar-overlay {{ display:none; position:fixed; inset:0; z-index:149; background:rgba(0,0,0,0.6); }}

/* ── CONTENT ── */
.content {{ flex:1; min-width:0; display:flex; flex-direction:column; }}

/* ── TOOLBAR ── */
.toolbar {{
  position:sticky; top:54px; z-index:100;
  background:rgba(14,15,20,0.95); border-bottom:1px solid var(--border);
  backdrop-filter:blur(8px);
  display:flex; align-items:center; gap:0.5rem; padding:0.55rem 1.25rem; flex-wrap:wrap;
}}
.type-chip {{
  display:inline-flex; align-items:center; gap:0.3rem;
  padding:0.28rem 0.7rem; border-radius:20px; font-size:0.74rem; font-weight:600;
  border:1px solid rgba(255,255,255,0.1); background:rgba(255,255,255,0.05);
  color:var(--text-muted); cursor:pointer; transition:all .15s; user-select:none;
}}
.type-chip:hover {{ color:var(--text); border-color:rgba(255,255,255,0.2); }}
.chip-dot {{ width:6px; height:6px; border-radius:50%; }}
.type-chip.active-info  {{ background:rgba(34,211,238,0.12);  border-color:var(--type-info);  color:var(--type-info); }}
.type-chip.active-trans {{ background:rgba(74,222,128,0.12);  border-color:var(--type-trans); color:var(--type-trans); }}
.type-chip.active-nav   {{ background:rgba(167,139,250,0.12); border-color:var(--type-nav);   color:var(--type-nav); }}
.type-chip.active-anal  {{ background:rgba(251,146,60,0.12);  border-color:var(--type-anal);  color:var(--type-anal); }}
.toolbar-spacer {{ flex:1; }}
.result-meta {{ font-size:0.72rem; color:var(--text-muted); }}
.result-meta strong {{ color:var(--text); }}
.reset-btn {{
  font-size:0.72rem; padding:0.22rem 0.6rem; border-radius:5px;
  background:rgba(255,255,255,0.05); border:1px solid var(--border);
  color:var(--text-muted); cursor:pointer; transition:all .15s;
}}
.reset-btn:hover {{ color:var(--text); background:rgba(255,255,255,0.1); }}

/* ── INNER MAIN ── */
.main {{ padding:1.25rem; flex:1; }}

/* Stats bar */
.stats {{ display:flex; gap:0.75rem; margin-bottom:1.25rem; flex-wrap:wrap; }}
.stat {{ background:var(--bg-raised); border:1px solid var(--border); border-radius:8px; padding:0.85rem 1.25rem; text-align:center; flex:1; min-width:100px; }}
.stat .num {{ font-size:1.7rem; font-weight:700; color:var(--joule-light); }}
.stat .label {{ font-size:0.68rem; color:var(--text-muted); margin-top:2px; text-transform:uppercase; letter-spacing:0.5px; }}

/* Type cards */
.type-cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr)); gap:0.75rem; margin-bottom:1.25rem; }}
.type-card {{
  background:var(--bg-raised); border:1px solid var(--border); border-radius:10px;
  padding:1rem 1.1rem; cursor:pointer; transition:all 0.2s;
}}
.type-card:hover {{ transform:translateY(-2px); box-shadow:0 6px 20px rgba(0,0,0,0.4); }}
.type-card.active {{ border-color:var(--joule-light); box-shadow:0 0 0 1px var(--joule-light); }}
.type-card .icon {{ font-size:1.5rem; margin-bottom:0.35rem; }}
.type-card h3 {{ font-size:0.9rem; margin-bottom:0.25rem; }}
.type-card .desc {{ font-size:0.75rem; color:var(--text-muted); line-height:1.4; margin-bottom:0.4rem; }}
.type-card .count {{ font-size:1.2rem; font-weight:700; color:var(--joule-light); }}
.type-info {{ border-left:3px solid var(--type-info); }}
.type-nav  {{ border-left:3px solid var(--type-nav); }}
.type-trans{{ border-left:3px solid var(--type-trans); }}
.type-anal {{ border-left:3px solid var(--type-anal); }}

/* Filter bar */
.filter-bar {{
  background:var(--bg-raised); border:1px solid var(--border); border-radius:8px;
  padding:0.85rem 1.25rem; margin-bottom:1.25rem;
  display:flex; gap:0.75rem; align-items:center; flex-wrap:wrap;
}}
.filter-bar input {{
  flex:1; min-width:200px; padding:0.45rem 0.8rem;
  border:1px solid var(--border); border-radius:6px;
  font-size:0.88rem; background:var(--bg); color:var(--text); outline:none;
  transition:border-color .2s;
}}
.filter-bar input::placeholder {{ color:var(--text-muted); }}
.filter-bar input:focus {{ border-color:var(--joule-light); }}
.filter-bar select {{
  padding:0.45rem 0.6rem; border:1px solid var(--border); border-radius:6px;
  font-size:0.83rem; background:var(--bg); color:var(--text);
}}
.filter-bar select option {{ background:var(--bg-surface); }}

/* Tree */
.tree-section {{ background:var(--bg-raised); border:1px solid var(--border); border-radius:10px; overflow:hidden; }}
.product-section {{ margin-bottom:0; border-bottom:1px solid var(--border); }}
.product-section:last-child {{ border-bottom:none; }}
.product-header {{ display:flex; align-items:center; padding:0.75rem 1.25rem; background:var(--bg-surface); cursor:pointer; gap:0.75rem; }}
.product-header:hover {{ background:rgba(123,47,190,0.1); }}
.product-header h3 {{ flex:1; font-size:0.93rem; }}
.product-header .count {{ font-size:0.82rem; color:var(--text-muted); }}
.product-body {{ display:none; }}
.product-body.open {{ display:block; }}
.tree-expand {{ width:18px; font-size:0.65rem; color:var(--text-muted); flex-shrink:0; text-align:center; }}

.ba-section {{ border-bottom:1px solid var(--border); }}
.ba-section:last-child {{ border-bottom:none; }}
.ba-header {{ display:flex; align-items:center; padding:0.6rem 1.25rem 0.6rem 2.5rem; cursor:pointer; gap:0.75rem; background:rgba(255,255,255,0.02); }}
.ba-header:hover {{ background:rgba(123,47,190,0.07); }}
.ba-header h4 {{ flex:1; font-size:0.87rem; font-weight:600; }}
.ba-header .count {{ font-size:0.78rem; color:var(--text-muted); }}
.ba-body {{ display:none; }}
.ba-body.open {{ display:block; }}

/* Use case row */
.use-case {{ display:flex; align-items:flex-start; padding:0.55rem 1.25rem 0.55rem 3.25rem; border-bottom:1px solid rgba(255,255,255,0.04); gap:0.75rem; flex-wrap:wrap; }}
.use-case:last-child {{ border-bottom:none; }}
.use-case:hover {{ background:rgba(123,47,190,0.06); }}
.use-case .uc-main {{ display:flex; align-items:center; gap:0.75rem; flex:1; min-width:200px; }}
.use-case .uc-title {{ flex:1; font-size:0.84rem; }}
.use-case .uc-title a {{ color:var(--text); text-decoration:none; }}
.use-case .uc-title a:hover {{ color:var(--link); text-decoration:underline; }}

/* Badges */
.badge {{ font-size:0.68rem; padding:0.12rem 0.48rem; border-radius:4px; font-weight:600; white-space:nowrap; }}
.badge-info  {{ background:rgba(34,211,238,0.12);  color:var(--type-info); }}
.badge-nav   {{ background:rgba(167,139,250,0.12); color:var(--type-nav); }}
.badge-trans {{ background:rgba(74,222,128,0.12);  color:var(--type-trans); }}
.badge-anal  {{ background:rgba(251,146,60,0.12);  color:var(--type-anal); }}
.badge-pending {{ font-size:0.68rem; padding:0.12rem 0.48rem; border-radius:4px; font-weight:600; white-space:nowrap; background:rgba(255,255,255,0.07); color:var(--text-muted); font-style:italic; }}
.title-only-entry {{ opacity:0.65; }}
.help-link {{ font-size:0.74rem; color:var(--link); text-decoration:none; white-space:nowrap; }}
.help-link:hover {{ text-decoration:underline; }}

/* Tier badges */
.tier-badge {{ font-size:0.63rem; padding:0.08rem 0.42rem; border-radius:10px; font-weight:700; white-space:nowrap; text-transform:uppercase; letter-spacing:0.3px; }}
.tier-base    {{ background:rgba(74,222,128,0.1);  color:#4ade80; border:1px solid rgba(74,222,128,0.25); }}
.tier-premium {{ background:rgba(251,191,36,0.12); color:#fbbf24; border:1px solid rgba(251,191,36,0.3); }}
.tier-eac     {{ background:rgba(56,189,248,0.1);  color:#38bdf8; border:1px solid rgba(56,189,248,0.25); }}
.tier-beta    {{ background:rgba(251,113,133,0.1); color:#fb7185; border:1px solid rgba(251,113,133,0.25); }}

/* Sample prompts */
.sample-prompts {{ width:100%; padding:0.25rem 0 0.35rem 3.25rem; }}
.sample-prompts ul {{ list-style:none; display:flex; flex-wrap:wrap; gap:0.35rem; }}
.sample-prompts li {{ font-size:0.76rem; color:var(--joule-light); background:var(--joule-dim); padding:0.22rem 0.65rem; border-radius:14px; font-style:italic; cursor:default; border:1px solid rgba(123,47,190,0.3); }}
.sample-prompts li::before {{ content:'💬 '; }}

/* Notes & Parameters */
.uc-notes {{ width:100%; padding:0.25rem 0 0.2rem 4.25rem; }}
.uc-notes .note-item {{ display:flex; align-items:flex-start; gap:0.4rem; padding:0.2rem 0; font-size:0.76rem; color:var(--text-muted); line-height:1.4; }}

/* Caution boxes */
.uc-caution {{ width:100%; padding:0.25rem 0 0.25rem 4.25rem; }}
.caution-box {{ background:rgba(249,168,37,0.12); border-left:3px solid #f9a825; border-radius:4px; padding:0.38rem 0.65rem; font-size:0.74rem; color:#fcd57a; line-height:1.4; }}
.caution-box::before {{ content:'⚠️ '; }}

/* Info notes */
.uc-info-note {{ width:100%; padding:0.18rem 0 0.18rem 4.25rem; }}
.info-note-text {{ font-size:0.76rem; color:#b0b8cc; line-height:1.5; padding:0.18rem 0; }}
.uc-params {{ width:100%; padding:0.12rem 0 0.25rem 4.25rem; }}
.uc-params .param-list {{ display:flex; flex-wrap:wrap; gap:0.3rem; }}
.uc-params .param-tag {{ font-size:0.7rem; background:rgba(251,191,36,0.1); color:#e8c96a; padding:0.12rem 0.5rem; border-radius:10px; border:1px solid rgba(251,191,36,0.25); }}
.uc-params .param-tag::before {{ content:'⚙️ '; font-size:0.63rem; }}

/* Special note */
.special-note {{ width:100%; padding:0.45rem 1rem 0.45rem 3.25rem; }}
.note-box {{ background:var(--joule-dim); border-radius:8px; padding:0.85rem; border-left:4px solid var(--joule-light); font-size:0.8rem; color:var(--text); line-height:1.5; }}
.note-box strong {{ color:var(--joule-light); }}

/* Sub-area */
.sub-area-header {{ display:flex; align-items:center; padding:0.55rem 1.25rem 0.55rem 3.25rem; cursor:pointer; gap:0.75rem; }}
.sub-area-header:hover {{ background:rgba(123,47,190,0.06); }}
.sub-area-header h5 {{ flex:1; font-size:0.83rem; font-weight:600; }}
.sub-area-body {{ display:none; }}
.sub-area-body.open {{ display:block; }}
.sub-area-body .use-case {{ padding-left:4.25rem; }}
.sub-area-body .sample-prompts {{ padding-left:4.25rem; }}

/* Capability group */
.cap-group-header {{ display:flex; align-items:center; padding:0.55rem 1.25rem 0.55rem 3.25rem; cursor:pointer; gap:0.75rem; border-bottom:1px solid rgba(255,255,255,0.04); }}
.cap-group-header:hover {{ background:rgba(123,47,190,0.06); }}
.cap-group-header .cg-title {{ flex:1; font-size:0.83rem; font-weight:600; }}
.cap-group-header .cg-title a {{ color:var(--text); text-decoration:none; }}
.cap-group-header .cg-title a:hover {{ color:var(--link); text-decoration:underline; }}
.cap-group-body {{ display:none; }}
.cap-group-body.open {{ display:block; }}
.cap-group-body .use-case {{ padding-left:4.25rem; border-left:2px solid rgba(123,47,190,0.3); margin-left:3.25rem; padding-left:1rem; }}
.cap-group-body .sample-prompts {{ padding-left:4.25rem; }}
.uc-child {{ display:flex; align-items:flex-start; padding:0.45rem 1.25rem 0.45rem 4.25rem; border-bottom:1px solid rgba(255,255,255,0.03); gap:0.55rem; flex-wrap:wrap; }}
.uc-child:hover {{ background:rgba(123,47,190,0.05); }}
.uc-child .uc-main {{ display:flex; align-items:center; gap:0.55rem; flex:1; min-width:200px; }}
.uc-child .uc-name {{ font-size:0.8rem; flex:1; }}
.uc-child .uc-desc {{ width:100%; font-size:0.76rem; color:#b0b8cc; line-height:1.4; margin-top:0.18rem; }}
.uc-child-prompts {{ width:100%; padding:0.18rem 0 0.28rem 0; }}
.uc-child-prompts ul {{ list-style:none; display:flex; flex-wrap:wrap; gap:0.3rem; }}
.uc-child-prompts li {{ font-size:0.73rem; color:var(--joule-light); background:var(--joule-dim); padding:0.18rem 0.55rem; border-radius:12px; font-style:italic; cursor:default; border:1px solid rgba(123,47,190,0.25); }}
.uc-child-prompts li::before {{ content:'💬 '; }}

/* Subcategory headers */
.subcat-header {{ margin:0.45rem 0 0.18rem 0; font-size:0.78rem; font-weight:600; color:#b0b8cc; border-bottom:1px solid var(--border); padding-bottom:0.18rem; }}
.subcat-list {{ list-style:none; display:flex; flex-wrap:wrap; gap:0.3rem; }}
.subcat-item {{ font-size:0.76rem; color:var(--text); background:rgba(255,255,255,0.07); padding:0.22rem 0.65rem; border-radius:6px; border:1px solid var(--border); }}

.uc-inline-desc {{ font-size:0.76rem; color:#b0b8cc; margin-left:0.45rem; }}
.cap-desc {{ width:100%; padding:0.25rem 0 0.18rem 3.25rem; font-size:0.8rem; color:#b0b8cc; }}
.cap-single-uc {{ width:100%; padding:0.12rem 0 0.12rem 3.25rem; font-size:0.76rem; color:#b0b8cc; }}
.flat-badge-row {{ padding:0.45rem 1.25rem 0.25rem; display:flex; gap:0.55rem; align-items:center; flex-wrap:wrap; }}

/* ── CONFIGURE PANEL ── */
.config-btn {{
  display:inline-flex; align-items:center; gap:0.35rem;
  padding:0.28rem 0.65rem; border-radius:20px; font-size:0.74rem; font-weight:600;
  border:1px solid rgba(255,255,255,0.1); background:rgba(255,255,255,0.05);
  color:var(--text-muted); cursor:pointer; transition:all .15s; user-select:none;
}}
.config-btn:hover {{ color:var(--text); border-color:rgba(255,255,255,0.2); }}
.config-btn.active {{ background:var(--joule-dim); border-color:var(--joule-light); color:var(--joule-light); }}
.config-panel {{
  display:none; background:var(--bg-surface); border-bottom:1px solid var(--border);
  padding:0.85rem 1.25rem; gap:1.5rem; flex-wrap:wrap; align-items:flex-start;
}}
.config-panel.open {{ display:flex; }}
.config-group {{ display:flex; flex-direction:column; gap:0.4rem; min-width:200px; flex:1; }}
.config-group-label {{
  font-size:0.65rem; font-weight:700; letter-spacing:0.08em; text-transform:uppercase;
  color:var(--text-muted); margin-bottom:0.15rem;
}}
.config-checkboxes {{ display:flex; flex-wrap:wrap; gap:0.35rem; }}
.config-check {{
  display:inline-flex; align-items:center; gap:0.35rem;
  padding:0.25rem 0.6rem; border-radius:6px; font-size:0.75rem;
  border:1px solid var(--border); background:rgba(255,255,255,0.04);
  color:var(--text-muted); cursor:pointer; transition:all .15s; user-select:none;
}}
.config-check input {{ display:none; }}
.config-check.checked {{
  background:var(--joule-dim); border-color:var(--joule-light); color:var(--text);
}}
.config-check .check-dot {{ width:6px; height:6px; border-radius:50%; background:var(--text-muted); flex-shrink:0; }}
.config-check.checked .check-dot {{ background:var(--joule-light); }}
.config-actions {{ display:flex; gap:0.5rem; align-items:center; margin-top:0.25rem; }}
.config-link {{ font-size:0.72rem; color:var(--text-muted); cursor:pointer; transition:color .15s; }}
.config-link:hover {{ color:var(--joule-light); }}

/* ── ROLE CHIPS ── */
.role-chip {{
  display:inline-flex; align-items:center; gap:0.3rem;
  padding:0.28rem 0.7rem; border-radius:20px; font-size:0.74rem; font-weight:600;
  border:1px solid rgba(255,255,255,0.1); background:rgba(255,255,255,0.05);
  color:var(--text-muted); cursor:pointer; transition:all .15s; user-select:none;
}}
.role-chip:hover {{ color:var(--text); border-color:rgba(255,255,255,0.2); }}
.role-chip.active {{
  background:rgba(181,123,238,0.15); border-color:var(--joule-light); color:var(--joule-light);
}}
.toolbar-divider {{ width:1px; height:18px; background:var(--border); flex-shrink:0; margin:0 0.15rem; }}
.footer {{ text-align:center; padding:1.5rem; color:var(--text-muted); font-size:0.78rem; border-top:1px solid var(--border); }}
.footer strong {{ color:var(--text); }}

@media (max-width:768px) {{
  .hamburger {{ display:block; }}
  .header-search {{ max-width:none; flex:1; }}
  .sidebar {{ position:fixed; top:0; left:-240px; width:240px; height:100vh; z-index:150; transition:left .25s; }}
  .sidebar.open {{ left:0; }}
  .sidebar-overlay.open {{ display:block; }}
  .layout {{ display:block; }}
  .toolbar {{ top:54px; }}
  .stats {{ gap:0.5rem; }}
  .stat {{ padding:0.6rem; min-width:70px; }}
  .stat .num {{ font-size:1.2rem; }}
  .type-cards {{ grid-template-columns:repeat(2,1fr); }}
  .filter-bar {{ flex-direction:column; }}
  .filter-bar input {{ min-width:auto; }}
  .use-case {{ padding-left:2.5rem; }}
  .sample-prompts {{ padding-left:2.5rem; }}
  .sub-area-body .use-case {{ padding-left:3rem; }}
}}
</style>
</head>
<body>

<!-- HEADER -->
<header class="header">
  <button class="hamburger" id="hamburgerBtn" aria-label="Toggle menu">&#9776;</button>
  <div class="header-logo">
    <div class="joule-mark">J</div>
    <span class="header-title">Joule <span>Capabilities Explorer</span></span>
  </div>
  <div class="header-search">
    <span class="si">&#128269;</span>
    <input type="text" id="search" placeholder="Search capabilities, prompts..." oninput="applyFilters()" autocomplete="off">
  </div>
</header>

<!-- LAYOUT -->
<div class="layout">

  <!-- Sidebar overlay (mobile) -->
  <div class="sidebar-overlay" id="sidebarOverlay"></div>

  <!-- SIDEBAR -->
  <nav class="sidebar" id="sidebar">
    <div class="sidebar-inner">
      <div class="sidebar-section-label">Products</div>
      <div id="sidebarItems"></div>
    </div>
  </nav>

  <!-- CONTENT -->
  <div class="content">

    <!-- TOOLBAR: type filter chips + role chips -->
    <div class="toolbar" id="toolbar">
      <span class="toolbar-label">Type:</span>
      <button class="type-chip" data-type="Informational" onclick="setTypeChip(this)">
        <span class="chip-dot" style="background:var(--type-info)"></span>Informational
        <span id="chip-cnt-Informational"></span>
      </button>
      <button class="type-chip" data-type="Transactional" onclick="setTypeChip(this)">
        <span class="chip-dot" style="background:var(--type-trans)"></span>Transactional
        <span id="chip-cnt-Transactional"></span>
      </button>
      <button class="type-chip" data-type="Navigational" onclick="setTypeChip(this)">
        <span class="chip-dot" style="background:var(--type-nav)"></span>Navigational
        <span id="chip-cnt-Navigational"></span>
      </button>
      <button class="type-chip" data-type="Analytical" onclick="setTypeChip(this)">
        <span class="chip-dot" style="background:var(--type-anal)"></span>Analytical
        <span id="chip-cnt-Analytical"></span>
      </button>
      <div class="toolbar-divider"></div>
      <span class="toolbar-label">Role:</span>
      <div id="roleChips"></div>
      <div class="toolbar-spacer"></div>
      <span class="result-meta" id="resultMeta"></span>
      <button class="config-btn" id="configBtn" onclick="toggleConfigPanel()">&#9881; Products</button>
      <button class="reset-btn" onclick="resetAll()">&#215; Reset</button>
    </div>

    <!-- CONFIGURE PANEL: product multiselect -->
    <div class="config-panel" id="configPanel">
      <div class="config-group">
        <div class="config-group-label">Show only these products</div>
        <div class="config-checkboxes" id="productCheckboxes"></div>
        <div class="config-actions">
          <span class="config-link" onclick="selectAllProducts()">Select all</span>
          <span style="color:var(--border)">·</span>
          <span class="config-link" onclick="deselectAllProducts()">Deselect all</span>
        </div>
      </div>
    </div>

    <!-- MAIN CONTENT -->
    <div class="main">
      <div id="stats" style="display:none"></div>
      <div id="typeCards" style="display:none"></div>
      <div class="filter-bar" style="display:none">
        <select id="productFilter"><option value="">All Products</option></select>
        <select id="areaFilter"><option value="">All Business Areas</option></select>
        <select id="typeFilter"><option value="">All Types</option></select>
      </div>
      <div class="tree-section" id="treeContent"></div>
    </div>

    <div class="footer">
      <strong>{meta['total_entries']}</strong> entries &middot; <strong>{meta['total_leaves']}</strong> use cases &middot; <strong>{meta['products']}</strong> products &middot; Updated {meta['enriched_at'][:10]}
    </div>

  </div><!-- /content -->
</div><!-- /layout -->

<script>
const ALL_CAPS = {caps_json};

const TYPE_INFO = {{
  'Informational': {{
    icon: 'ℹ️', badgeClass: 'badge-info', borderClass: 'type-info',
    desc: 'Display and retrieve data — view business partners, account balances, order details, search records.'
  }},
  'Navigational': {{
    icon: '🧭', badgeClass: 'badge-nav', borderClass: 'type-nav',
    desc: 'Navigate to SAP Fiori apps — ask Joule to open the right application screen directly.'
  }},
  'Transactional': {{
    icon: '⚡', badgeClass: 'badge-trans', borderClass: 'type-trans',
    desc: 'Create, change, and process business documents — manage orders, post journals, execute workflows.'
  }},
  'Analytical': {{
    icon: '📊', badgeClass: 'badge-anal', borderClass: 'type-anal',
    desc: 'AI-assisted analysis and insights — anomaly detection, forecasting, and data-driven decisions.'
  }}
}};

let activeType = null;

function getTierBadge(tier) {{
  if (!tier || tier === 'base') return '';
  const labels = {{ premium: 'Premium', eac: 'EAC', beta: 'Beta' }};
  const label = labels[tier] || tier;
  return '<span class="tier-badge tier-' + tier + '">' + label + '</span>';
}}

function ucCount(c) {{
  // If a capability has use_cases, count total individual capabilities
  if (c.use_cases && c.use_cases.length > 0) {{
    let total = 0;
    c.use_cases.forEach(uc => {{
      // Each prompt is an individual capability; at minimum count the use case itself
      total += (uc.prompts && uc.prompts.length > 0) ? uc.prompts.length : 1;
    }});
    return total > 1 ? total : 1;
  }}
  return 1;
}}

function buildTree(caps) {{
  const tree = {{}};
  caps.forEach(c => {{
    // Skip pure branch category nodes — they are TOC structural nodes, not capabilities
    if (c.is_branch && !c.use_cases?.length && !c.sample_prompts?.length) return;
    const prod = c.product;
    if (!tree[prod]) tree[prod] = {{ areas: {{}}, count: 0 }};
    const ba = c.business_area || '(General)';
    if (c.is_leaf) {{
      if (!tree[prod].areas[ba]) tree[prod].areas[ba] = {{ subareas: {{}}, items: [] }};
      const sa = c.sub_area;
      if (sa) {{
        if (!tree[prod].areas[ba].subareas[sa]) tree[prod].areas[ba].subareas[sa] = [];
        tree[prod].areas[ba].subareas[sa].push(c);
      }} else {{
        tree[prod].areas[ba].items.push(c);
      }}
      tree[prod].count += ucCount(c);
    }}
  }});
  return tree;
}}

function getTypeBadge(type) {{
  const ti = TYPE_INFO[type] || TYPE_INFO['Informational'];
  return '<span class="badge ' + ti.badgeClass + '">' + type + '</span>';
}}

function renderStats(caps) {{
  const leaves = caps.filter(c => c.is_leaf).length;
  const products = new Set(caps.map(c => c.product)).size;
  const types = {{}};
  caps.forEach(c => {{ types[c.capability_type] = (types[c.capability_type] || 0) + 1; }});
  
  let html = '<div class="stat"><div class="num">' + caps.length + '</div><div class="label">Total Entries</div></div>';
  html += '<div class="stat"><div class="num">' + leaves + '</div><div class="label">Use Cases</div></div>';
  html += '<div class="stat"><div class="num">' + products + '</div><div class="label">SAP Products</div></div>';
  const withPrompts = caps.filter(c => c.sample_prompts && c.sample_prompts.length > 0).length;
  html += '<div class="stat"><div class="num">' + withPrompts + '</div><div class="label">With Sample Prompts</div></div>';
  document.getElementById('stats').innerHTML = html;
}}

function getUCTypes(c) {{
  // Get all unique capability types present in a capability's use cases
  if (c.use_cases && c.use_cases.length > 0) {{
    return [...new Set(c.use_cases.map(uc => uc.capability_type).filter(Boolean))];
  }}
  return [c.capability_type].filter(Boolean);
}}

function renderTypeCards(caps) {{
  const types = {{}};
  caps.forEach(c => {{
    getUCTypes(c).forEach(t => {{ types[t] = (types[t] || 0) + 1; }});
  }});
  
  const order = ['Informational', 'Transactional', 'Analytical', 'Navigational'];
  let html = '';
  order.forEach(t => {{
    if (!types[t]) return;
    const ti = TYPE_INFO[t];
    const activeClass = activeType === t ? 'active' : '';
    html += '<div class="type-card ' + ti.borderClass + ' ' + activeClass + '" onclick="toggleType(\\'' + t + '\\')">';
    html += '<div class="icon">' + ti.icon + '</div>';
    html += '<h3>' + t + '</h3>';
    html += '<div class="desc">' + ti.desc + '</div>';
    html += '<div class="count">' + types[t] + '</div>';
    html += '</div>';
  }});
  document.getElementById('typeCards').innerHTML = html;
}}

/* ── ROLE GROUPS ── */
const ROLE_GROUPS = [
  {{ id:'finance',    label:'Finance',                     areas: new Set(['Finance']) }},
  {{ id:'sales',      label:'Sales',                       areas: new Set(['Sales']) }},
  {{ id:'procure',    label:'Procurement & Supply Chain',  areas: new Set(['Procurement','Sourcing and Procurement','Supply Chain','Warehouse Management','Transportation Management','Core Logistics','Field Logistics']) }},
  {{ id:'mfg',        label:'Manufacturing & Engineering', areas: new Set(['Manufacturing','R&D/ Engineering','Production Planning and Detailed Scheduling','Asset Management']) }},
  {{ id:'service',    label:'Service',                     areas: new Set(['Service']) }},
  {{ id:'masterdata', label:'Master Data & Governance',    areas: new Set(['Business Partners','Master Data Governance','Business Rules Framework Plus','ILM Data Destruction']) }},
  {{ id:'crossarea',  label:'Cross-Area',                  areas: new Set(['Cross-Area Capabilities','Country/Region-Specific Capabilities']) }},
];

let activeRole = null;

function buildRoleChips() {{
  const container = document.getElementById('roleChips');
  container.innerHTML = ROLE_GROUPS.map(rg => {{
    const active = activeRole === rg.id ? 'active' : '';
    return `<button class="role-chip ${{active}}" data-role="${{rg.id}}" onclick="toggleRole(this)">${{rg.label}}</button>`;
  }}).join('');
}}

function toggleRole(btn) {{
  const role = btn.dataset.role;
  activeRole = (activeRole === role) ? null : role;
  render();
}}

/* ── PRODUCT EXCLUSION (multiselect panel) ── */
let excludedProducts = new Set();

const ALL_PRODUCTS = (function() {{
  const counts = {{}};
  ALL_CAPS.forEach(c => {{
    if (!c.is_leaf && !(c.is_branch && c.use_cases && c.use_cases.length)) return;
    const n = (c.use_cases && c.use_cases.length) ? c.use_cases.length : 1;
    counts[c.product] = (counts[c.product] || 0) + n;
  }});
  return Object.entries(counts).sort((a,b) => b[1]-a[1]).map(e => e[0]);
}})();

function buildProductCheckboxes() {{
  const container = document.getElementById('productCheckboxes');
  container.innerHTML = ALL_PRODUCTS.map(p => {{
    const checked = !excludedProducts.has(p);
    const shortName = p.replace(/^SAP\\s+/, '');
    return `<label class="config-check ${{checked ? 'checked' : ''}}" data-product="${{p.replace(/"/g,'&quot;')}}">
      <input type="checkbox" ${{checked ? 'checked' : ''}} onchange="toggleProductExclusion(this)">
      <span class="check-dot"></span>${{shortName}}
    </label>`;
  }}).join('');
}}

function toggleProductExclusion(input) {{
  const label = input.closest('.config-check');
  const prod = label.dataset.product;
  if (input.checked) {{
    excludedProducts.delete(prod);
    label.classList.add('checked');
  }} else {{
    excludedProducts.add(prod);
    label.classList.remove('checked');
  }}
  updateConfigBtn();
  render();
}}

function selectAllProducts() {{
  excludedProducts.clear();
  buildProductCheckboxes();
  updateConfigBtn();
  render();
}}

function deselectAllProducts() {{
  ALL_PRODUCTS.forEach(p => excludedProducts.add(p));
  buildProductCheckboxes();
  updateConfigBtn();
  render();
}}

function updateConfigBtn() {{
  const btn = document.getElementById('configBtn');
  const excluded = excludedProducts.size;
  if (excluded > 0) {{
    btn.textContent = '⚙ Products (' + (ALL_PRODUCTS.length - excluded) + '/' + ALL_PRODUCTS.length + ')';
    btn.classList.add('active');
  }} else {{
    btn.textContent = '⚙ Products';
    btn.classList.remove('active');
  }}
}}

function toggleConfigPanel() {{
  const panel = document.getElementById('configPanel');
  const btn = document.getElementById('configBtn');
  const open = panel.classList.toggle('open');
  // Keep active class if products are filtered, regardless of panel state
  btn.classList.toggle('active', open || excludedProducts.size > 0);
}}

function populateFilters(caps) {{
  const products = [...new Set(caps.map(c => c.product))].sort();
  const areas = [...new Set(caps.map(c => c.business_area).filter(Boolean))].sort();
  const types = [...new Set(caps.flatMap(c => getUCTypes(c)))].sort();
  const pSel = document.getElementById('productFilter');
  pSel.innerHTML = '<option value="">All Products</option>' + products.map(p => '<option value="' + p + '">' + p + '</option>').join('');
  const aSel = document.getElementById('areaFilter');
  aSel.innerHTML = '<option value="">All Business Areas</option>' + areas.map(a => '<option value="' + a + '">' + a + '</option>').join('');
  const tSel = document.getElementById('typeFilter');
  tSel.innerHTML = '<option value="">All Types</option>' + types.map(t => '<option value="' + t + '">' + t + '</option>').join('');
}}

function getFilteredCaps() {{
  let caps = ALL_CAPS;
  const search  = document.getElementById('search').value.toLowerCase();
  const product = activeSidebarProduct || '';

  // 1. Product exclusion (independent of all other filters)
  if (excludedProducts.size > 0) {{
    caps = caps.filter(c => !excludedProducts.has(c.product));
  }}
  // 2. Sidebar product drill-down
  if (product) caps = caps.filter(c => c.product === product);
  // 3. Type chip
  if (activeType) caps = caps.filter(c => getUCTypes(c).includes(activeType));
  // 4. Role group
  if (activeRole) {{
    const rg = ROLE_GROUPS.find(r => r.id === activeRole);
    if (rg) caps = caps.filter(c => rg.areas.has((c.business_area || '').trim()));
  }}
  // 5. Search
  if (search) caps = caps.filter(c => {{
    if (c.title.toLowerCase().includes(search)) return true;
    if ((c.hierarchy || '').toLowerCase().includes(search)) return true;
    if ((c.description || '').toLowerCase().includes(search)) return true;
    if (c.use_cases) return c.use_cases.some(uc =>
      (uc.name || '').toLowerCase().includes(search) ||
      (uc.description || '').toLowerCase().includes(search) ||
      (uc.prompts || []).some(p => p.toLowerCase().includes(search))
    );
    return false;
  }});
  return caps;
}}

let promptCounter = 0;

function isExplanatoryText(text) {{
  // Detect explanatory/instructional text that was misclassified as a prompt
  const t = text.trim();
  const tl = t.toLowerCase();
  // Explanatory starters — sentences describing behavior, not commands
  if (/^(?:You need to|You can |You must |If you |If no |If the |If a |If several |When Joule|When you |Joule (?:automatically|checks|creates|displays|supports|adjusts|uses|shows|will)|Note that |Please note|This (?:feature|function|capability)|The (?:system|app)|In (?:this|the) )/i.test(t)) return true;
  // Long multi-sentence explanations (>120 chars with at least one period mid-text)
  if (t.length > 120 && /\\.\\s+[A-Z]/.test(t)) return true;
  return false;
}}

function renderChildUseCase(uc) {{
  const name = uc.name || 'Use Case';
  const desc = uc.description || '';
  const rawPrompts = uc.prompts || [];
  
  // Separate real prompts from explanatory text misclassified as prompts
  const prompts = [];
  const promptNotes = [];
  rawPrompts.forEach(p => {{
    if (isExplanatoryText(p)) {{
      promptNotes.push(p);
    }} else {{
      prompts.push(p);
    }}
  }});
  
  const notes = (uc.notes || []).concat(promptNotes).filter(n => {{
    const nl = n.toLowerCase();
    if (nl.includes('you can choose one of the following')) return false;
    if (nl.includes('you can choose') && nl.endsWith(':')) return false;
    if (/^(?:Submit|Cancel|Retype|Save Draft|Reject|Approve|Confirm|Discard|Close|Accept|Decline|Go Back|Try Again|Submit with Governance|Save Draft Governance Process)\\s*[:–—]/i.test(n)) return false;
    if (/^(?:Show|Perform|Do) the following\\s*:?\\s*$/i.test(n)) return false;
    if (/^(?:Ask for example|For example)\\s*:?\\s*$/i.test(n)) return false;
    return true;
  }});
  const params = uc.parameters || [];
  const subcategories = uc.subcategories || {{}};
  const resp = uc.response_summary || '';
  const hasSubs = Object.keys(subcategories).length > 0;
  
  // Classify notes into info notes vs cautions
  const infoNotes = [];
  const cautions = [];
  notes.forEach(n => {{
    const nl = n.toLowerCase();
    if (nl.startsWith('currently') || nl.startsWith('note:') || nl.startsWith('note that') ||
        nl.startsWith('only ') || nl.startsWith('please note') || nl.startsWith('this feature') ||
        nl.includes('not supported') || nl.includes('not available') || nl.includes('limitation') ||
        nl.includes('currently') || nl.includes('restricted to') || nl.includes('does not') ||
        nl.includes('cannot') || nl.includes('only available') || nl.includes('only supported') ||
        nl.includes('make sure') || nl.includes('ensure that') || nl.includes('be aware')) {{
      cautions.push(n);
    }} else {{
      infoNotes.push(n);
    }}
  }});

  let html = '<div class="uc-child">';
  html += '<div class="uc-main">';
  html += '<span class="uc-name"><strong>' + name + '</strong></span>';
  // Render per-use-case type badge
  if (uc.capability_type) {{
    html += ' ' + getTypeBadge(uc.capability_type);
  }}
  if (desc) {{
    html += '<span class="uc-inline-desc">' + desc.substring(0, 200) + '</span>';
  }}
  html += '</div>';
  // Info notes — always on new line, left-aligned, full width
  if (infoNotes.length > 0) {{
    html += '<div class="uc-info-note">';
    infoNotes.forEach(n => {{
      html += '<div class="info-note-text">' + n + '</div>';
    }});
    html += '</div>';
  }}

  // Parameters as compact tags
  if (params.length > 0) {{
    html += '<div class="uc-params"><div class="param-list">';
    params.forEach(p => {{
      html += '<span class="param-tag">' + p + '</span>';
    }});
    html += '</div></div>';
  }}

  // If subcategories exist, group prompts under category headers
  if (hasSubs) {{
    html += '<div class="uc-child-prompts">';
    Object.keys(subcategories).forEach(cat => {{
      html += '<div class="subcat-header">' + cat + '</div>';
      html += '<ul class="subcat-list">';
      subcategories[cat].forEach(p => {{
        html += '<li class="subcat-item">' + p + '</li>';
      }});
      html += '</ul>';
    }});
    html += '</div>';
  }} else if (prompts.length > 0) {{
    // Flat prompt list
    html += '<div class="uc-child-prompts"><ul>';
    prompts.forEach(p => {{
      html += '<li>' + p + '</li>';
    }});
    html += '</ul></div>';
  }}

  // Cautions — rendered below prompts with warning style
  if (cautions.length > 0) {{
    html += '<div class="uc-caution">';
    cautions.forEach(n => {{
      html += '<div class="caution-box">' + n + '</div>';
    }});
    html += '</div>';
  }}

  html += '</div>'; // close uc-child
  return html;
}}

function renderUseCase(c) {{
  const badge = getTypeBadge(c.capability_type);
  const tierBadge = getTierBadge(c.tier);
  const link = c.sap_help_url ? '<a href="' + c.sap_help_url + '" target="_blank" rel="noopener" class="help-link">View in SAP Help \\u2192</a>' : '';
  const titleText = c.sap_help_url
    ? '<a href="' + c.sap_help_url + '" target="_blank" rel="noopener">' + c.title + '</a>'
    : c.title;

  const hasChildUCs = c.use_cases && (c.use_cases.length > 1 || (c.use_cases.length === 1 && c.use_cases[0].subcategories && Object.keys(c.use_cases[0].subcategories).length > 0));
  const hasUCs = c.use_cases && c.use_cases.length > 0;
  const hasPrompts = c.sample_prompts && c.sample_prompts.length > 0;
  const hasNote = c.special_note;
  const isTitleOnly = c.data_source === 'title-only';

  let html = '';

  // Suppress pure branch/category nodes with no real content
  if (c.is_branch && !hasUCs && !hasPrompts) {{
    return '';
  }}

  if (isTitleOnly && !hasChildUCs && !hasPrompts && !hasUCs) {{
    // Title-only entry with no real content — still show with pending badge
    html += '<div class="use-case title-only-entry">';
    html += '<div class="uc-main">';
    html += '<span class="uc-title">' + titleText + '</span>';
    html += badge + ' ' + tierBadge;
    html += '<span class="badge-pending">📋 Documentation Pending</span>';
    html += link;
    html += '</div>';
    html += '</div>';
    return html;
  }}

  const isDescOnly = c.data_source === 'description-only';
  if (isDescOnly && !hasChildUCs && !hasPrompts && !hasUCs) {{
    // Scraped page with description prose but no examples table yet
    html += '<div class="use-case">';
    html += '<div class="uc-main">';
    html += '<span class="uc-title">' + titleText + '</span>';
    html += badge + ' ' + tierBadge;
    html += '<span class="badge-pending">🔜 Examples Coming Soon</span>';
    html += link;
    html += '</div>';
    if (c.description) {{
      html += '<div class="cap-desc">' + c.description + '</div>';
    }}
    html += '</div>';
    return html;
  }}

  if (hasChildUCs) {{
    // Render as collapsible group with child use cases
    const gid = 'capgroup-' + (promptCounter++);
    html += '<div class="cap-group-header" onclick="toggleSection(this)">';
    html += '<span class="tree-expand">\\u25B6</span>';
    html += '<span class="cg-title">' + titleText + '</span>';
    html += tierBadge;
    html += '<span class="count">' + c.use_cases.length + ' use cases</span>';
    html += link;
    html += '</div>';
    html += '<div class="cap-group-body">';
    if (c.description) {{
      html += '<div class="cap-desc">' + c.description + '</div>';
    }}
    c.use_cases.forEach(uc => {{
      html += renderChildUseCase(uc);
    }});
    html += '</div>';
  }} else {{
    // Render as simple row
    html += '<div class="use-case">';
    html += '<div class="uc-main">';
    html += '<span class="uc-title">' + titleText + '</span>';
    html += badge + ' ' + tierBadge;
    html += link;
    html += '</div>';
    // Show description if available (capability-level or from single use case)
    const desc = c.description || (hasUCs && c.use_cases[0].description ? c.use_cases[0].description : '');
    if (desc) {{
      html += '<div class="cap-desc">' + desc + '</div>';
    }}
    // Show single use case name + description even when no prompts
    if (hasUCs && c.use_cases.length === 1) {{
      const uc = c.use_cases[0];
      if (uc.name && uc.name !== c.title) {{
        html += '<div class="cap-single-uc"><strong>Use Case:</strong> ' + uc.name + '</div>';
      }}
      // Show use case description if different from cap description
      if (uc.description && uc.description !== desc) {{
        html += '<div class="cap-desc" style="padding-top:0">' + uc.description + '</div>';
      }}
      // Show notes even when no prompts
      if (uc.notes && uc.notes.length > 0) {{
        html += '<div class="uc-info-note">';
        uc.notes.forEach(n => {{ html += '<div class="info-note-text">' + n + '</div>'; }});
        html += '</div>';
      }}
      // Show parameters
      if (uc.parameters && uc.parameters.length > 0) {{
        html += '<div class="uc-params"><div class="param-list">';
        uc.parameters.forEach(p => {{ html += '<span class="param-tag">' + p + '</span>'; }});
        html += '</div></div>';
      }}
    }}
    if (hasPrompts) {{
      html += '<div class="sample-prompts">';
      html += '<ul>';
      c.sample_prompts.forEach(p => {{
        html += '<li>' + p + '</li>';
      }});
      html += '</ul></div>';
    }}
    html += '</div>';
  }}

  if (hasNote) {{
    html += '<div class="special-note"><div class="note-box">';
    html += '<strong>🔮 Coming Soon:</strong> ' + c.special_note;
    html += '</div></div>';
  }}

  return html;
}}

function renderTree(caps) {{
  const tree = buildTree(caps);
  const productNames = Object.keys(tree).sort((a, b) => tree[b].count - tree[a].count);
  
  if (productNames.length === 0) {{
    document.getElementById('treeContent').innerHTML = '<div class="empty">No capabilities match your filters.</div>';
    return;
  }}
  
  promptCounter = 0;
  let html = '';
  productNames.forEach(prod => {{
    const pt = tree[prod];
    const areaNames = Object.keys(pt.areas).sort();
    const isOpen = productNames.length === 1 || !!activeType;
    
    html += '<div class="product-section">';
    html += '<div class="product-header" onclick="toggleSection(this)">';
    html += '<span class="tree-expand">' + (isOpen ? '\\u25BC' : '\\u25B6') + '</span>';
    html += '<h3>' + prod + '</h3>';
    html += '<span class="count">' + pt.count + ' capabilities</span>';
    html += '</div>';
    html += '<div class="product-body' + (isOpen ? ' open' : '') + '">';
    
    /* Helper: render area contents (items + subareas) without wrapper */
    function renderAreaContents(areaData) {{
      let h = '';
      areaData.items.forEach(c => {{ h += renderUseCase(c); }});
      Object.keys(areaData.subareas).sort().forEach(sa => {{
        const saItems = areaData.subareas[sa];
        h += '<div class="sub-area-header" onclick="toggleSection(this)">';
        h += '<span class="tree-expand">\\u25B6</span>';
        h += '<h5>' + sa + '</h5>';
        h += '<span class="count">' + saItems.length + '</span>';
        h += '</div>';
        h += '<div class="sub-area-body">';
        saItems.forEach(c => {{ h += renderUseCase(c); }});
        h += '</div>';
      }});
      return h;
    }}

    /* Skip the BA level when there's only a single area */
    const skipBA = areaNames.length === 1;

    /* Also: if single area has exactly 1 item with use_cases, flatten completely —
       render child use cases directly under the product header */
    let flattenedToProduct = false;
    if (skipBA) {{
      const areaData = pt.areas[areaNames[0]];
      const totalItems = areaData.items.length + Object.values(areaData.subareas).reduce((s, a) => s + a.length, 0);
      if (totalItems === 1 && areaData.items.length === 1) {{
        const singleCap = areaData.items[0];
        if (singleCap.use_cases && singleCap.use_cases.length > 1) {{
          /* Render use cases directly — skip the capability header */
          flattenedToProduct = true;
          const link = singleCap.sap_help_url ? '<a href="' + singleCap.sap_help_url + '" target="_blank" rel="noopener" class="help-link">View in SAP Help \\u2192</a>' : '';
          const badge = getTypeBadge(singleCap.capability_type);
          const tierBadge = getTierBadge(singleCap.tier);
          html += '<div class="flat-badge-row">' + badge + ' ' + tierBadge + link + '</div>';
          if (singleCap.description) {{
            html += '<div class="cap-desc">' + singleCap.description + '</div>';
          }}
          singleCap.use_cases.forEach(uc => {{
            html += renderChildUseCase(uc);
          }});
          if (singleCap.special_note) {{
            html += '<div class="special-note"><div class="note-box"><strong>🔮 Coming Soon:</strong> ' + singleCap.special_note + '</div></div>';
          }}
        }}
      }}
    }}

    if (!flattenedToProduct) {{
    areaNames.forEach(area => {{
      const areaData = pt.areas[area];
      const areaTotal = areaData.items.length + Object.values(areaData.subareas).reduce((s, a) => s + a.length, 0);
      if (areaTotal === 0) return;
      
      if (skipBA) {{
        /* Render items directly under the product — no BA header */
        html += renderAreaContents(areaData);
      }} else {{
        const areaOpen = areaNames.length <= 3 || !!activeType;
        html += '<div class="ba-section">';
        html += '<div class="ba-header" onclick="toggleSection(this)">';
        html += '<span class="tree-expand">' + (areaOpen ? '\\u25BC' : '\\u25B6') + '</span>';
        html += '<h4>' + area + '</h4>';
        html += '<span class="count">' + areaTotal + '</span>';
        html += '</div>';
        html += '<div class="ba-body' + (areaOpen ? ' open' : '') + '">';
        html += renderAreaContents(areaData);
        html += '</div></div>';
      }}
    }});
    }} /* end if !flattenedToProduct */
    
    html += '</div></div>';
  }});
  
  document.getElementById('treeContent').innerHTML = html;
}}

function toggleSection(el) {{
  const body = el.nextElementSibling;
  const expand = el.querySelector('.tree-expand');
  body.classList.toggle('open');
  expand.textContent = body.classList.contains('open') ? '\\u25BC' : '\\u25B6';
}}

function togglePrompts(id) {{
  const el = document.getElementById(id);
  if (el) el.classList.toggle('open');
}}

function toggleType(type) {{
  activeType = activeType === type ? null : type;
  render();
}}

function applyFilters() {{
  render();
}}

function navigateTo() {{
  activeType = null;
  activeSidebarProduct = null;
  activeRole = null;
  document.getElementById('search').value = '';
  document.getElementById('productFilter').value = '';
  document.getElementById('areaFilter').value = '';
  document.getElementById('typeFilter').value = '';
  render();
}}

function resetAll() {{
  activeType = null;
  activeSidebarProduct = null;
  activeRole = null;
  document.getElementById('search').value = '';
  document.getElementById('productFilter').value = '';
  document.getElementById('areaFilter').value = '';
  document.getElementById('typeFilter').value = '';
  // Do NOT reset product exclusions — those are a customer config choice
  render();
}}

/* ── SIDEBAR ── */
let activeSidebarProduct = null;

const PROD_COLORS = ['#9b4fd8','#22d3ee','#4ade80','#a78bfa','#fb923c','#f472b6','#38bdf8','#34d399','#fbbf24','#e879f9','#60a5fa','#a3e635','#f87171','#2dd4bf','#facc15','#818cf8','#fb7185','#67e8f9'];

function buildSidebarCounts() {{
  const counts = {{}};
  ALL_CAPS.forEach(c => {{
    if (!c.is_leaf && !(c.is_branch && c.use_cases && c.use_cases.length)) return;
    const ucCount = (c.use_cases && c.use_cases.length) ? c.use_cases.length : 1;
    counts[c.product] = (counts[c.product] || 0) + ucCount;
  }});
  return counts;
}}

function renderSidebar() {{
  const counts = buildSidebarCounts();
  const total = Object.values(counts).reduce((a,b)=>a+b,0);
  const sorted = Object.entries(counts).sort((a,b)=>b[1]-a[1]);
  let h = '';
  const allActive = activeSidebarProduct === null ? 'active' : '';
  h += `<div class="sidebar-item ${{allActive}}" onclick="selectSidebarProduct(null)"><span class="sidebar-dot" style="background:#9b4fd8"></span><span class="sidebar-name">All Products</span><span class="sidebar-count">${{total}}</span></div>`;
  sorted.forEach(([prod, cnt], i) => {{
    const color = PROD_COLORS[i % PROD_COLORS.length];
    const active = activeSidebarProduct === prod ? 'active' : '';
    const name = prod.replace(/^SAP\\s+/, '');
    h += `<div class="sidebar-item ${{active}}" data-product="${{prod.replace(/"/g,'&quot;')}}" onclick="selectSidebarProduct(this.dataset.product)"><span class="sidebar-dot" style="background:${{color}}"></span><span class="sidebar-name" title="${{prod.replace(/"/g,'&quot;')}}">${{name}}</span><span class="sidebar-count">${{cnt}}</span></div>`;
  }});
  document.getElementById('sidebarItems').innerHTML = h;
}}

function selectSidebarProduct(prod) {{
  activeSidebarProduct = prod || null;
  // sync the select dropdown
  const sel = document.getElementById('productFilter');
  if (sel) sel.value = activeSidebarProduct || '';
  // close mobile sidebar
  document.getElementById('sidebar').classList.remove('open');
  document.getElementById('sidebarOverlay').classList.remove('open');
  render();
}}

/* ── TYPE CHIPS (toolbar) ── */
const TYPE_CHIP_ACTIVE_CLASS = {{
  'Informational':'active-info','Transactional':'active-trans',
  'Navigational':'active-nav','Analytical':'active-anal'
}};

function setTypeChip(btn) {{
  const t = btn.dataset.type;
  toggleType(t);
}}

function updateChips() {{
  document.querySelectorAll('.type-chip').forEach(chip => {{
    const t = chip.dataset.type;
    chip.className = 'type-chip';
    if (activeType === t) chip.classList.add(TYPE_CHIP_ACTIVE_CLASS[t]);
  }});
  // update chip counts
  const types = ['Informational','Transactional','Navigational','Analytical'];
  types.forEach(t => {{
    const el = document.getElementById('chip-cnt-' + t);
    if (!el) return;
    const n = ALL_CAPS.filter(c => getUCTypes(c).includes(t)).length;
    el.textContent = n ? ' ' + n : '';
  }});
}}

function updateResultMeta() {{
  const total = ALL_CAPS.filter(c => c.is_leaf || (c.is_branch && c.use_cases && c.use_cases.length))
    .filter(c => !excludedProducts.has(c.product))
    .reduce((sum, c) => sum + ((c.use_cases && c.use_cases.length) ? c.use_cases.length : 1), 0);
  const filtered = getFilteredCaps()
    .filter(c => c.is_leaf || (c.is_branch && c.use_cases && c.use_cases.length))
    .reduce((sum, c) => sum + ((c.use_cases && c.use_cases.length) ? c.use_cases.length : 1), 0);
  const el = document.getElementById('resultMeta');
  if (!el) return;
  const isFiltered = activeSidebarProduct || activeType || activeRole || document.getElementById('search').value;
  el.innerHTML = isFiltered
    ? `<strong>${{filtered}}</strong> of ${{total}} use cases`
    : `${{total}} use cases`;
}}

/* ── HAMBURGER ── */
document.addEventListener('DOMContentLoaded', function() {{
  const btn = document.getElementById('hamburgerBtn');
  const overlay = document.getElementById('sidebarOverlay');
  if (btn) btn.addEventListener('click', function() {{
    document.getElementById('sidebar').classList.toggle('open');
    overlay.classList.toggle('open');
  }});
  if (overlay) overlay.addEventListener('click', function() {{
    document.getElementById('sidebar').classList.remove('open');
    overlay.classList.remove('open');
  }});
}});

function render() {{
  const caps = getFilteredCaps();
  renderStats(caps);
  renderTypeCards(caps);
  renderTree(caps);
  renderSidebar();
  updateChips();
  buildRoleChips();
  updateResultMeta();
}}

populateFilters(ALL_CAPS);
buildProductCheckboxes();
render();
</script>
</body>
</html>"""

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(html, encoding="utf-8")
    size = OUT_FILE.stat().st_size
    print(f"✅ Generated {OUT_FILE} ({size:,} bytes)")
    print(f"   {len(caps)} entries, {len(leaves)} use cases, {len(products)} products")


if __name__ == "__main__":
    generate()