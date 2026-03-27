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
    leaves = [c for c in caps if c.get("is_leaf")]
    updated_date = meta.get("enriched_at", "")[:10]
    total_entries = meta.get("total_entries", len(caps))
    total_leaves  = meta.get("total_leaves", len(leaves))
    num_products  = meta.get("products", len(set(c["product"] for c in caps)))

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Joule Capabilities Explorer</title>
<style>
:root {{
  --bg-base:      #080c18;
  --bg-surface:   #0d1224;
  --bg-card:      rgba(255,255,255,0.055);
  --bg-card-hover:rgba(255,255,255,0.09);
  --accent:       #4a9eff;
  --type-info:    #22d3ee;
  --type-trans:   #4ade80;
  --type-nav:     #c084fc;
  --type-anal:    #fb923c;
  --type-info-bg: rgba(34,211,238,0.12);
  --type-trans-bg:rgba(74,222,128,0.12);
  --type-nav-bg:  rgba(192,132,252,0.12);
  --type-anal-bg: rgba(251,146,60,0.12);
  --text-primary: #e8edf5;
  --text-muted:   rgba(232,237,245,0.38);
  --border:       rgba(255,255,255,0.07);
}}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:var(--bg-base); color:var(--text-primary); min-height:100vh; }}

/* ── HEADER ── */
.header {{
  position:sticky; top:0; z-index:200;
  background:linear-gradient(90deg,var(--bg-surface) 0%,#0f1a30 100%);
  border-bottom:1px solid var(--border);
  display:flex; align-items:center; gap:1rem; padding:0 1.25rem; height:52px;
  backdrop-filter:blur(10px);
}}
.header-logo {{ display:flex; align-items:center; gap:0.55rem; flex-shrink:0; }}
.hamburger {{ display:none; background:none; border:none; color:var(--text-primary); cursor:pointer; padding:4px; font-size:1.1rem; line-height:1; }}
.logo-mark {{ font-size:1.15rem; }}
.logo-title {{ font-size:0.92rem; font-weight:700; letter-spacing:0.01em; white-space:nowrap; }}
.logo-title span {{ color:var(--accent); }}
.header-search {{ flex:1; max-width:380px; position:relative; }}
.header-search input {{
  width:100%; padding:0.38rem 0.75rem 0.38rem 2.1rem;
  background:rgba(255,255,255,0.07); border:1px solid var(--border);
  border-radius:6px; color:var(--text-primary); font-size:0.82rem;
  outline:none; transition:border-color .2s, background .2s;
}}
.header-search input::placeholder {{ color:var(--text-muted); }}
.header-search input:focus {{ border-color:var(--accent); background:rgba(74,158,255,0.08); }}
.header-search .search-icon {{ position:absolute; left:0.6rem; top:50%; transform:translateY(-50%); color:var(--text-muted); font-size:0.8rem; pointer-events:none; }}
.header-count {{ margin-left:auto; flex-shrink:0; font-size:0.78rem; color:var(--text-muted); white-space:nowrap; }}
.header-count strong {{ color:var(--accent); }}

/* ── LAYOUT ── */
.layout {{ display:flex; min-height:calc(100vh - 52px); }}

/* ── SIDEBAR ── */
.sidebar {{
  width:236px; flex-shrink:0;
  background:var(--bg-surface);
  border-right:1px solid var(--border);
  display:flex; flex-direction:column;
  overflow-y:auto; position:sticky; top:52px; height:calc(100vh - 52px);
}}
.sidebar-inner {{ padding:0.75rem 0; }}
.sidebar-label {{ font-size:0.65rem; font-weight:700; letter-spacing:0.08em; text-transform:uppercase; color:var(--text-muted); padding:0.5rem 1rem 0.3rem; }}
.sidebar-item {{
  display:flex; align-items:center; gap:0.55rem;
  padding:0.42rem 1rem; cursor:pointer; font-size:0.82rem;
  border-left:3px solid transparent; transition:all .15s;
  color:var(--text-muted);
}}
.sidebar-item:hover {{ background:rgba(74,158,255,0.07); color:var(--text-primary); }}
.sidebar-item.active {{
  background:rgba(34,211,238,0.1);
  border-left-color:var(--accent);
  color:var(--accent); font-weight:600;
}}
.sidebar-dot {{ width:7px; height:7px; border-radius:50%; flex-shrink:0; }}
.sidebar-name {{ flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
.sidebar-badge {{
  font-size:0.65rem; padding:0.1rem 0.4rem; border-radius:10px;
  background:rgba(255,255,255,0.08); color:var(--text-muted);
  font-weight:600; flex-shrink:0;
}}
.sidebar-item.active .sidebar-badge {{ background:rgba(74,158,255,0.2); color:var(--accent); }}

/* Sidebar overlay (mobile) */
.sidebar-overlay {{ display:none; position:fixed; inset:0; z-index:149; background:rgba(0,0,0,0.55); }}

/* ── MAIN ── */
.main {{ flex:1; min-width:0; display:flex; flex-direction:column; }}

/* ── TOOLBAR ── */
.toolbar {{
  position:sticky; top:52px; z-index:100;
  background:rgba(13,18,36,0.92); border-bottom:1px solid var(--border);
  backdrop-filter:blur(10px);
  display:flex; align-items:center; gap:0.5rem; padding:0.6rem 1.25rem; flex-wrap:wrap;
}}
.toolbar-label {{ font-size:0.7rem; color:var(--text-muted); margin-right:0.2rem; }}
.type-chip {{
  display:inline-flex; align-items:center; gap:0.35rem;
  padding:0.3rem 0.75rem; border-radius:20px; font-size:0.75rem; font-weight:600;
  border:1px solid rgba(255,255,255,0.1); background:rgba(255,255,255,0.05);
  color:var(--text-muted); cursor:pointer; transition:all .15s; user-select:none;
}}
.type-chip:hover {{ color:var(--text-primary); border-color:rgba(255,255,255,0.2); }}
.type-chip .chip-dot {{ width:6px; height:6px; border-radius:50%; }}
.type-chip.active-info  {{ background:var(--type-info-bg);  border-color:var(--type-info);  color:var(--type-info); }}
.type-chip.active-trans {{ background:var(--type-trans-bg); border-color:var(--type-trans); color:var(--type-trans); }}
.type-chip.active-nav   {{ background:var(--type-nav-bg);   border-color:var(--type-nav);   color:var(--type-nav); }}
.type-chip.active-anal  {{ background:var(--type-anal-bg);  border-color:var(--type-anal);  color:var(--type-anal); }}
.toolbar-spacer {{ flex:1; }}
.result-meta {{ font-size:0.72rem; color:var(--text-muted); white-space:nowrap; }}
.result-meta strong {{ color:var(--text-primary); }}
.reset-btn {{
  font-size:0.72rem; padding:0.25rem 0.6rem; border-radius:5px;
  background:rgba(255,255,255,0.06); border:1px solid var(--border);
  color:var(--text-muted); cursor:pointer; transition:all .15s;
}}
.reset-btn:hover {{ background:rgba(255,255,255,0.12); color:var(--text-primary); }}

/* ── CARD GRID ── */
.card-grid-wrap {{ padding:1.1rem 1.25rem 2rem; flex:1; }}
.card-grid {{
  display:grid;
  grid-template-columns:repeat(auto-fill, minmax(320px, 1fr));
  gap:0.85rem;
}}
.empty-state {{
  grid-column:1/-1; text-align:center; padding:4rem 1rem; color:var(--text-muted);
}}
.empty-state .empty-icon {{ font-size:2.5rem; margin-bottom:0.75rem; }}
.empty-state p {{ font-size:0.9rem; }}

/* ── CAPABILITY CARD ── */
.cap-card {{
  background:var(--bg-card);
  backdrop-filter:blur(12px);
  border:1px solid var(--border);
  border-radius:10px;
  border-left:3px solid var(--card-accent, var(--accent));
  display:flex; flex-direction:column;
  transition:transform .18s, box-shadow .18s, background .18s;
  overflow:hidden;
}}
.cap-card:hover {{
  transform:translateY(-2px);
  background:var(--bg-card-hover);
  box-shadow:0 8px 32px rgba(0,0,0,0.35);
}}
.card-head {{ padding:0.75rem 0.85rem 0.5rem; }}
.card-title-row {{ display:flex; align-items:flex-start; gap:0.5rem; margin-bottom:0.3rem; }}
.card-title {{
  font-size:0.88rem; font-weight:700; line-height:1.35;
  display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden;
  flex:1;
}}
.card-title a {{ color:var(--text-primary); text-decoration:none; }}
.card-title a:hover {{ color:var(--accent); }}
.card-help-link {{
  flex-shrink:0; font-size:0.75rem; color:var(--text-muted);
  text-decoration:none; transition:color .15s; padding-top:0.05rem;
  line-height:1;
}}
.card-help-link:hover {{ color:var(--accent); }}
.card-breadcrumb {{ font-size:0.7rem; color:var(--text-muted); margin-bottom:0.45rem; }}
.card-badges {{ display:flex; gap:0.35rem; flex-wrap:wrap; margin-bottom:0.45rem; }}
.badge {{
  font-size:0.65rem; font-weight:700; padding:0.15rem 0.5rem;
  border-radius:10px; white-space:nowrap; letter-spacing:0.01em;
}}
.badge-info  {{ background:var(--type-info-bg);  color:var(--type-info);  border:1px solid rgba(34,211,238,0.3); }}
.badge-trans {{ background:var(--type-trans-bg); color:var(--type-trans); border:1px solid rgba(74,222,128,0.3); }}
.badge-nav   {{ background:var(--type-nav-bg);   color:var(--type-nav);   border:1px solid rgba(192,132,252,0.3); }}
.badge-anal  {{ background:var(--type-anal-bg);  color:var(--type-anal);  border:1px solid rgba(251,146,60,0.3); }}
.badge-premium {{ background:rgba(251,191,36,0.15); color:#fbbf24; border:1px solid rgba(251,191,36,0.35); }}
.badge-pending {{ background:rgba(255,255,255,0.07); color:var(--text-muted); border:1px solid var(--border); font-style:italic; }}
.badge-soon    {{ background:rgba(74,158,255,0.1);   color:var(--accent);       border:1px solid rgba(74,158,255,0.3); }}

/* Prompt chips */
.card-prompts {{ padding:0 0.85rem 0.5rem; display:flex; flex-direction:column; gap:0.3rem; flex:1; }}
.prompt-chip {{
  font-size:0.72rem; color:var(--accent); background:rgba(74,158,255,0.08);
  border:1px solid rgba(74,158,255,0.18); border-radius:6px;
  padding:0.28rem 0.6rem; line-height:1.35;
  display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden;
}}
.card-desc {{ padding:0 0.85rem 0.5rem; font-size:0.74rem; color:var(--text-muted); line-height:1.5; }}

/* Expand button */
.card-footer {{ padding:0.45rem 0.85rem 0.6rem; border-top:1px solid var(--border); margin-top:auto; }}
.expand-btn {{
  width:100%; background:none; border:none; color:var(--text-muted);
  font-size:0.74rem; cursor:pointer; text-align:left; padding:0;
  display:flex; align-items:center; gap:0.3rem; transition:color .15s;
}}
.expand-btn:hover {{ color:var(--accent); }}
.expand-arrow {{ display:inline-block; transition:transform .2s; }}
.expand-btn.open .expand-arrow {{ transform:rotate(180deg); }}

/* Expanded panel */
.card-expanded {{
  display:none; border-top:1px solid var(--border);
  padding:0.6rem 0.85rem 0.75rem; background:rgba(0,0,0,0.15);
}}
.card-expanded.open {{ display:block; }}
.uc-block {{ margin-bottom:0.85rem; }}
.uc-block:last-child {{ margin-bottom:0; }}
.uc-name {{
  font-size:0.75rem; font-weight:700; color:var(--text-primary);
  margin-bottom:0.35rem; display:flex; align-items:center; gap:0.4rem; flex-wrap:wrap;
}}
.uc-prompts {{ display:flex; flex-direction:column; gap:0.25rem; margin-bottom:0.3rem; }}
.uc-prompt {{
  font-size:0.71rem; color:var(--accent); background:rgba(74,158,255,0.07);
  border:1px solid rgba(74,158,255,0.15); border-radius:5px;
  padding:0.22rem 0.55rem; line-height:1.35;
}}
.uc-prompt::before {{ content:'💬 '; }}
.uc-desc {{ font-size:0.71rem; color:var(--text-muted); line-height:1.45; margin-bottom:0.25rem; }}
.uc-caution {{
  font-size:0.7rem; color:#fbbf24; background:rgba(251,191,36,0.07);
  border-left:2px solid rgba(251,191,36,0.4); border-radius:0 4px 4px 0;
  padding:0.25rem 0.55rem; margin-top:0.25rem; line-height:1.4;
}}
.uc-caution::before {{ content:'⚠ '; }}
.uc-note {{ font-size:0.7rem; color:var(--text-muted); line-height:1.4; padding:0.2rem 0; }}

/* ── FOOTER ── */
.footer {{
  text-align:center; padding:1.25rem 1rem;
  font-size:0.74rem; color:var(--text-muted);
  border-top:1px solid var(--border);
}}
.footer strong {{ color:var(--text-primary); }}

/* ── MOBILE ── */
@media (max-width:768px) {{
  .hamburger {{ display:flex; align-items:center; justify-content:center; }}
  .header-search {{ max-width:none; flex:1; }}
  .sidebar {{
    position:fixed; top:0; left:-260px; width:260px; height:100vh;
    z-index:150; transition:left .25s; top:0;
  }}
  .sidebar.open {{ left:0; }}
  .sidebar-overlay.open {{ display:block; }}
  .layout {{ display:block; }}
  .main {{ min-height:calc(100vh - 52px); }}
  .toolbar {{ top:52px; }}
  .card-grid {{ grid-template-columns:1fr; }}
  .card-grid-wrap {{ padding:0.75rem; }}
}}
</style>
</head>
<body>

<!-- HEADER -->
<header class="header">
  <div class="header-logo">
    <button class="hamburger" id="hamburgerBtn" aria-label="Toggle sidebar">&#9776;</button>
    <span class="logo-mark">✦</span>
    <span class="logo-title">Joule <span>Capabilities Explorer</span></span>
  </div>
  <div class="header-search">
    <span class="search-icon">&#128269;</span>
    <input type="text" id="searchInput" placeholder="Search capabilities, prompts..." autocomplete="off">
  </div>
  <div class="header-count" id="headerCount"><strong>171</strong> capabilities</div>
</header>

<!-- LAYOUT -->
<div class="layout">

  <!-- SIDEBAR OVERLAY (mobile) -->
  <div class="sidebar-overlay" id="sidebarOverlay"></div>

  <!-- SIDEBAR -->
  <nav class="sidebar" id="sidebar">
    <div class="sidebar-inner">
      <div class="sidebar-label">Products</div>
      <div id="sidebarItems"></div>
    </div>
  </nav>

  <!-- MAIN -->
  <div class="main">

    <!-- TOOLBAR -->
    <div class="toolbar" id="toolbar">
      <span class="toolbar-label">Type:</span>
      <button class="type-chip" data-type="Informational" onclick="toggleType(this)">
        <span class="chip-dot" style="background:var(--type-info)"></span>Informational
        <span class="chip-count" id="cnt-Informational"></span>
      </button>
      <button class="type-chip" data-type="Transactional" onclick="toggleType(this)">
        <span class="chip-dot" style="background:var(--type-trans)"></span>Transactional
        <span class="chip-count" id="cnt-Transactional"></span>
      </button>
      <button class="type-chip" data-type="Navigational" onclick="toggleType(this)">
        <span class="chip-dot" style="background:var(--type-nav)"></span>Navigational
        <span class="chip-count" id="cnt-Navigational"></span>
      </button>
      <button class="type-chip" data-type="Analytical" onclick="toggleType(this)">
        <span class="chip-dot" style="background:var(--type-anal)"></span>Analytical
        <span class="chip-count" id="cnt-Analytical"></span>
      </button>
      <div class="toolbar-spacer"></div>
      <span class="result-meta" id="resultMeta"></span>
      <button class="reset-btn" onclick="resetFilters()">&#x2715; Reset</button>
    </div>

    <!-- CARD GRID -->
    <div class="card-grid-wrap">
      <div class="card-grid" id="cardGrid"></div>
    </div>

    <!-- FOOTER -->
    <footer class="footer">
      <strong>{total_entries}</strong> entries &middot; <strong>{total_leaves}</strong> use cases &middot; <strong>{num_products}</strong> products &middot; Updated {updated_date}
    </footer>
  </div>
</div>

<script>
const ALL_CAPS = {caps_json};

/* ── STATE ── */
const state = {{
  activeProduct: null,
  activeTypes: new Set(),
  searchQuery: '',
}};

let searchTimer = null;

/* ── HELPERS ── */
function escHtml(s) {{
  if (!s) return '';
  return String(s)
    .replace(/&/g,'&amp;')
    .replace(/</g,'&lt;')
    .replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;');
}}

const TYPE_COLOR = {{
  'Informational': 'var(--type-info)',
  'Transactional':  'var(--type-trans)',
  'Navigational':   'var(--type-nav)',
  'Analytical':     'var(--type-anal)',
}};
const TYPE_BADGE_CLASS = {{
  'Informational': 'badge-info',
  'Transactional':  'badge-trans',
  'Navigational':   'badge-nav',
  'Analytical':     'badge-anal',
}};
const TYPE_CHIP_ACTIVE = {{
  'Informational': 'active-info',
  'Transactional':  'active-trans',
  'Navigational':   'active-nav',
  'Analytical':     'active-anal',
}};

/* product display name: strip "SAP " prefix, shorten long names */
function shortProduct(p) {{
  return p.replace(/^SAP\\s+/, '');
}}

/* unique color per product index */
const PROD_COLORS = ['#4a9eff','#22d3ee','#4ade80','#c084fc','#fb923c','#f472b6','#a3e635','#38bdf8','#e879f9','#34d399','#fbbf24','#60a5fa','#f87171','#a78bfa','#2dd4bf','#facc15','#fb7185','#818cf8'];

/* collect all use case types for a capability */
function getUCTypes(c) {{
  if (c.use_cases && c.use_cases.length > 0) {{
    return [...new Set(c.use_cases.map(uc => uc.capability_type).filter(Boolean))];
  }}
  return c.capability_type ? [c.capability_type] : [];
}}

/* is this cap a "leaf" we should show in grid? */
function isShowable(c) {{
  if (c.is_leaf) return true;
  if (c.is_branch && c.use_cases && c.use_cases.length > 0) return true;
  return false;
}}

/* ── FILTER LOGIC ── */
function getFilteredCaps() {{
  const q = state.searchQuery;
  return ALL_CAPS.filter(c => {{
    if (!isShowable(c)) return false;
    // product filter
    if (state.activeProduct && c.product !== state.activeProduct) return false;
    // type filter (multi-select: empty = show all)
    if (state.activeTypes.size > 0) {{
      const capTypes = getUCTypes(c);
      if (c.capability_type) capTypes.push(c.capability_type);
      const unique = [...new Set(capTypes)];
      if (!unique.some(t => state.activeTypes.has(t))) return false;
    }}
    // search
    if (q) {{
      const ql = q.toLowerCase();
      if (c.title.toLowerCase().includes(ql)) return true;
      if ((c.business_area || '').toLowerCase().includes(ql)) return true;
      if ((c.description || '').toLowerCase().includes(ql)) return true;
      if ((c.sample_prompts || []).some(p => p.toLowerCase().includes(ql))) return true;
      if (c.use_cases && c.use_cases.some(uc =>
        (uc.name || '').toLowerCase().includes(ql) ||
        (uc.prompts || []).some(p => p.toLowerCase().includes(ql))
      )) return true;
      return false;
    }}
    return true;
  }});
}}

/* ── BUILD PRODUCT SIDEBAR ── */
function buildSidebarData() {{
  // Count leaf caps per product
  const counts = {{}};
  ALL_CAPS.forEach(c => {{
    if (!isShowable(c)) return;
    counts[c.product] = (counts[c.product] || 0) + 1;
  }});
  const total = Object.values(counts).reduce((a, b) => a + b, 0);
  const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  return {{ total, sorted }};
}}

function renderSidebar() {{
  const {{ total, sorted }} = buildSidebarData();
  const container = document.getElementById('sidebarItems');
  let html = '';
  // All row
  const allActive = state.activeProduct === null ? 'active' : '';
  html += `<div class="sidebar-item ${{allActive}}" onclick="selectProduct(null)">
    <span class="sidebar-dot" style="background:var(--accent)"></span>
    <span class="sidebar-name">All Products</span>
    <span class="sidebar-badge">${{total}}</span>
  </div>`;
  sorted.forEach(([prod, cnt], idx) => {{
    const active = state.activeProduct === prod ? 'active' : '';
    const color = PROD_COLORS[idx % PROD_COLORS.length];
    const name = escHtml(shortProduct(prod));
    html += `<div class="sidebar-item ${{active}}" data-product="${{escHtml(prod)}}" onclick="selectProduct(this.dataset.product)">
      <span class="sidebar-dot" style="background:${{color}}"></span>
      <span class="sidebar-name" title="${{escHtml(prod)}}">${{name}}</span>
      <span class="sidebar-badge">${{cnt}}</span>
    </div>`;
  }});
  container.innerHTML = html;
}}

/* ── RENDER TYPE CHIP COUNTS ── */
function updateChipCounts(caps) {{
  const types = ['Informational','Transactional','Navigational','Analytical'];
  types.forEach(t => {{
    const cnt = caps.filter(c => {{
      const ts = getUCTypes(c);
      if (c.capability_type) ts.push(c.capability_type);
      return [...new Set(ts)].includes(t);
    }}).length;
    const el = document.getElementById('cnt-' + t);
    if (el) el.textContent = cnt ? ' ' + cnt : '';
  }});
  // update active state on chips
  document.querySelectorAll('.type-chip').forEach(chip => {{
    const t = chip.dataset.type;
    chip.className = 'type-chip';
    if (state.activeTypes.has(t)) chip.classList.add(TYPE_CHIP_ACTIVE[t]);
  }});
}}

/* ── RENDER A SINGLE CARD ── */
let cardIdCounter = 0;

function isExplanatoryText(text) {{
  const t = text.trim();
  if (/^(?:You need to|You can |You must |If you |If no |If the |If a |If several |When Joule|When you |Joule (?:automatically|checks|creates|displays|supports|adjusts|uses|shows|will)|Note that |Please note|This (?:feature|function|capability)|The (?:system|app)|In (?:this|the) )/i.test(t)) return true;
  if (t.length > 120 && /\\.\\s+[A-Z]/.test(t)) return true;
  return false;
}}

function classifyNotes(notes) {{
  const info = [], caution = [];
  notes.forEach(n => {{
    const nl = n.toLowerCase();
    if (nl.startsWith('currently') || nl.startsWith('note:') || nl.startsWith('note that') ||
        nl.startsWith('only ') || nl.startsWith('please note') || nl.startsWith('this feature') ||
        nl.includes('not supported') || nl.includes('not available') || nl.includes('limitation') ||
        nl.includes('currently') || nl.includes('restricted to') || nl.includes('does not') ||
        nl.includes('cannot') || nl.includes('only available') || nl.includes('only supported') ||
        nl.includes('make sure') || nl.includes('ensure that') || nl.includes('be aware')) {{
      caution.push(n);
    }} else {{
      info.push(n);
    }}
  }});
  return {{ info, caution }};
}}

function renderExpandedUC(uc) {{
  const rawPrompts = uc.prompts || [];
  const prompts = rawPrompts.filter(p => !isExplanatoryText(p));
  const explanatory = rawPrompts.filter(p => isExplanatoryText(p));
  const allNotes = (uc.notes || []).concat(explanatory);
  const {{ info: infoNotes, caution: cautions }} = classifyNotes(allNotes);
  let h = '<div class="uc-block">';
  h += '<div class="uc-name">' + escHtml(uc.name || '');
  if (uc.capability_type && TYPE_BADGE_CLASS[uc.capability_type]) {{
    h += ' <span class="badge ' + TYPE_BADGE_CLASS[uc.capability_type] + '">' + escHtml(uc.capability_type) + '</span>';
  }}
  h += '</div>';
  if (uc.description) h += '<div class="uc-desc">' + escHtml(uc.description) + '</div>';
  infoNotes.forEach(n => {{ h += '<div class="uc-note">' + escHtml(n) + '</div>'; }});
  if (prompts.length > 0) {{
    h += '<div class="uc-prompts">';
    prompts.forEach(p => {{ h += '<div class="uc-prompt">' + escHtml(p) + '</div>'; }});
    h += '</div>';
  }}
  cautions.forEach(n => {{ h += '<div class="uc-caution">' + escHtml(n) + '</div>'; }});
  h += '</div>';
  return h;
}}

function renderCard(c) {{
  const isTitleOnly = c.data_source === 'title-only';
  const isDescOnly  = c.data_source === 'description-only';
  const isPremium   = c.tier === 'premium';
  const hasUCs      = c.use_cases && c.use_cases.length > 0;
  const hasPrompts  = c.sample_prompts && c.sample_prompts.length > 0;

  // Card accent color
  const types = getUCTypes(c);
  if (c.capability_type) types.push(c.capability_type);
  const primaryType = [...new Set(types)][0] || 'Informational';
  const accentColor = TYPE_COLOR[primaryType] || 'var(--accent)';

  const cardId = 'card-' + (cardIdCounter++);

  // Title
  const titleHtml = c.sap_help_url
    ? `<a href="${{escHtml(c.sap_help_url)}}" target="_blank" rel="noopener">${{escHtml(c.title)}}</a>`
    : escHtml(c.title);
  const helpLink = c.sap_help_url
    ? `<a href="${{escHtml(c.sap_help_url)}}" target="_blank" rel="noopener" class="card-help-link" title="Open in SAP Help">&#8599;</a>`
    : '';

  // Badges
  let badges = '';
  const badgeClass = TYPE_BADGE_CLASS[primaryType] || 'badge-info';
  badges += `<span class="badge ${{badgeClass}}">${{escHtml(primaryType)}}</span>`;
  if (isPremium) badges += '<span class="badge badge-premium">&#9733; Premium</span>';
  if (isTitleOnly) badges += '<span class="badge badge-pending">&#128203; Documentation Pending</span>';
  else if (isDescOnly) badges += '<span class="badge badge-soon">&#128282; Examples Coming Soon</span>';

  // Prompt chips (up to 3, shown on card face)
  let promptChips = '';
  if (!isTitleOnly) {{
    const facePrompts = hasPrompts
      ? c.sample_prompts.slice(0, 3)
      : (hasUCs ? (c.use_cases[0].prompts || []).filter(p => !isExplanatoryText(p)).slice(0, 3) : []);
    facePrompts.forEach(p => {{
      promptChips += `<div class="prompt-chip">&#128172; ${{escHtml(p)}}</div>`;
    }});
    if (isDescOnly && c.description) {{
      promptChips += `<div class="card-desc">${{escHtml(c.description.substring(0,200))}}</div>`;
    }}
  }}

  // Expanded use case panel
  let expandedHtml = '';
  let expandBtn = '';
  const expandableUCs = hasUCs
    ? c.use_cases.filter(uc => (uc.prompts && uc.prompts.length > 0) || uc.description || (uc.notes && uc.notes.length > 0))
    : [];
  if (!isTitleOnly && expandableUCs.length > 0) {{
    expandedHtml = '<div class="card-expanded" id="exp-' + cardId + '">';
    expandableUCs.forEach(uc => {{ expandedHtml += renderExpandedUC(uc); }});
    expandedHtml += '</div>';
    expandBtn = `<div class="card-footer">
      <button class="expand-btn" onclick="toggleCard(this, 'exp-${{cardId}}')" data-count="${{expandableUCs.length}}">
        <span class="expand-arrow">&#9660;</span> Show ${{expandableUCs.length}} use case${{expandableUCs.length !== 1 ? 's' : ''}}
      </button>
    </div>`;
  }}

  // Breadcrumb
  const breadcrumb = c.business_area
    ? `<div class="card-breadcrumb">${{escHtml(c.business_area)}}</div>`
    : '';

  return `<div class="cap-card" style="--card-accent:${{accentColor}}">
    <div class="card-head">
      <div class="card-title-row">
        <div class="card-title">${{titleHtml}}</div>
        ${{helpLink}}
      </div>
      ${{breadcrumb}}
      <div class="card-badges">${{badges}}</div>
    </div>
    <div class="card-prompts">${{promptChips}}</div>
    ${{expandBtn}}
    ${{expandedHtml}}
  </div>`;
}}

/* ── RENDER ALL CARDS ── */
function renderCards(caps) {{
  cardIdCounter = 0;
  const grid = document.getElementById('cardGrid');
  if (caps.length === 0) {{
    grid.innerHTML = '<div class="empty-state"><div class="empty-icon">&#128269;</div><p>No capabilities match your filters.</p></div>';
    return;
  }}
  grid.innerHTML = caps.map(renderCard).join('');
}}

/* ── UPDATE HEADER COUNT ── */
function updateHeaderCount(caps) {{
  const el = document.getElementById('headerCount');
  el.innerHTML = `<strong>${{caps.length}}</strong> capabilit${{caps.length === 1 ? 'y' : 'ies'}}`;
}}

/* ── UPDATE RESULT META ── */
function updateResultMeta(caps) {{
  const el = document.getElementById('resultMeta');
  const total = ALL_CAPS.filter(isShowable).length;
  if (caps.length === total && state.activeTypes.size === 0 && !state.searchQuery) {{
    el.textContent = '';
  }} else {{
    el.innerHTML = `<strong>${{caps.length}}</strong> of ${{total}} shown`;
  }}
}}

/* ── MAIN RENDER ── */
function render() {{
  const caps = getFilteredCaps();
  renderSidebar();
  updateChipCounts(caps);
  renderCards(caps);
  updateHeaderCount(caps);
  updateResultMeta(caps);
}}

/* ── ACTIONS ── */
function selectProduct(p) {{
  state.activeProduct = p || null;
  // close mobile sidebar
  document.getElementById('sidebar').classList.remove('open');
  document.getElementById('sidebarOverlay').classList.remove('open');
  render();
}}

function toggleType(btn) {{
  const t = btn.dataset.type;
  if (state.activeTypes.has(t)) {{
    state.activeTypes.delete(t);
  }} else {{
    state.activeTypes.add(t);
  }}
  render();
}}

function resetFilters() {{
  state.activeProduct = null;
  state.activeTypes.clear();
  state.searchQuery = '';
  document.getElementById('searchInput').value = '';
  render();
}}

function toggleCard(btn, expId) {{
  const panel = document.getElementById(expId);
  const isOpen = panel.classList.toggle('open');
  btn.classList.toggle('open', isOpen);
  const count = btn.dataset.count;
  const arrow = btn.querySelector('.expand-arrow');
  if (isOpen) {{
    btn.childNodes[btn.childNodes.length - 1].textContent = ` Hide use case${{count !== '1' ? 's' : ''}}`;
  }} else {{
    btn.childNodes[btn.childNodes.length - 1].textContent = ` Show ${{count}} use case${{count !== '1' ? 's' : ''}}`;
  }}
}}

/* ── SEARCH (debounced) ── */
document.getElementById('searchInput').addEventListener('input', function(e) {{
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {{
    state.searchQuery = e.target.value.trim();
    render();
  }}, 120);
}});

/* ── HAMBURGER ── */
document.getElementById('hamburgerBtn').addEventListener('click', function() {{
  document.getElementById('sidebar').classList.toggle('open');
  document.getElementById('sidebarOverlay').classList.toggle('open');
}});
document.getElementById('sidebarOverlay').addEventListener('click', function() {{
  document.getElementById('sidebar').classList.remove('open');
  this.classList.remove('open');
}});

/* ── INIT ── */
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