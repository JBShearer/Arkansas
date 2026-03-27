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
<title>SAP Business AI — Joule Capabilities Explorer</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f0f2f5; color: #1a1a2e; }}

/* Header */
.header {{ background: linear-gradient(135deg, #0a1628 0%, #1a3a5c 50%, #2d6a9f 100%); color: white; padding: 2rem 1.5rem 1.5rem; text-align: center; }}
.header h1 {{ font-size: 2rem; margin-bottom: 0.3rem; }}
.header .subtitle {{ opacity: 0.85; font-size: 0.95rem; }}
.phase-bar {{ display: flex; justify-content: center; gap: 0; margin-top: 1rem; }}
.phase {{ padding: 0.5rem 1.5rem; font-size: 0.8rem; font-weight: 600; border: 1px solid rgba(255,255,255,0.3); }}
.phase:first-child {{ border-radius: 6px 0 0 6px; }}
.phase:last-child {{ border-radius: 0 6px 6px 0; }}
.phase.active {{ background: #0a6ed1; border-color: #0a6ed1; }}
.phase.next {{ background: rgba(255,255,255,0.1); }}
.phase.future {{ background: rgba(255,255,255,0.05); }}

/* AI banner */
.ai-banner {{ background: linear-gradient(90deg, #e3f2fd, #f3e5f5, #e8f5e9); padding: 0.7rem 1.5rem; text-align: center; font-size: 0.85rem; border-bottom: 1px solid #e0e0e0; }}
.ai-banner strong {{ color: #0a6ed1; }}

/* Breadcrumb */
.breadcrumb {{ background: white; padding: 0.8rem 1.5rem; border-bottom: 1px solid #e0e0e0; font-size: 0.85rem; }}
.breadcrumb a {{ color: #0a6ed1; text-decoration: none; cursor: pointer; }}
.breadcrumb a:hover {{ text-decoration: underline; }}
.breadcrumb span {{ color: #666; }}

/* Main */
.main {{ max-width: 1200px; margin: 0 auto; padding: 1.5rem; }}

/* Stats bar */
.stats {{ display: flex; gap: 1rem; margin-bottom: 1.5rem; flex-wrap: wrap; }}
.stat {{ background: white; border-radius: 8px; padding: 1rem 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.08); text-align: center; flex: 1; min-width: 100px; }}
.stat .num {{ font-size: 1.8rem; font-weight: 700; color: #0a6ed1; }}
.stat .label {{ font-size: 0.7rem; color: #666; margin-top: 2px; text-transform: uppercase; letter-spacing: 0.5px; }}

/* Type cards */
.type-cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }}
.type-card {{ background: white; border-radius: 10px; padding: 1.2rem; cursor: pointer; border: 2px solid transparent; box-shadow: 0 1px 4px rgba(0,0,0,0.08); transition: all 0.2s; }}
.type-card:hover {{ box-shadow: 0 4px 12px rgba(0,0,0,0.12); transform: translateY(-2px); }}
.type-card.active {{ border-color: #0a6ed1; box-shadow: 0 4px 12px rgba(10,110,209,0.2); }}
.type-card .icon {{ font-size: 1.8rem; margin-bottom: 0.4rem; }}
.type-card h3 {{ font-size: 0.95rem; margin-bottom: 0.3rem; }}
.type-card .desc {{ font-size: 0.78rem; color: #666; line-height: 1.4; margin-bottom: 0.5rem; }}
.type-card .count {{ font-size: 1.3rem; font-weight: 700; color: #0a6ed1; }}
.type-info {{ border-left: 3px solid #17a2b8; }}
.type-nav {{ border-left: 3px solid #6f42c1; }}
.type-trans {{ border-left: 3px solid #28a745; }}
.type-anal {{ border-left: 3px solid #fd7e14; }}

/* Filter bar */
.filter-bar {{ background: white; border-radius: 8px; padding: 1rem 1.5rem; margin-bottom: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.08); display: flex; gap: 1rem; align-items: center; flex-wrap: wrap; }}
.filter-bar input {{ flex: 1; min-width: 200px; padding: 0.5rem 0.8rem; border: 1px solid #d0d0d0; border-radius: 6px; font-size: 0.9rem; }}
.filter-bar input:focus {{ outline: none; border-color: #0a6ed1; box-shadow: 0 0 0 2px rgba(10,110,209,0.15); }}
.filter-bar select {{ padding: 0.5rem; border: 1px solid #d0d0d0; border-radius: 6px; font-size: 0.85rem; background: white; }}

/* Tree/product/BA/use-case */
.tree-section {{ background: white; border-radius: 10px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); overflow: hidden; }}
.product-section {{ margin-bottom: 0.5rem; }}
.product-header {{ display: flex; align-items: center; padding: 0.8rem 1.5rem; background: #f8f9fa; cursor: pointer; border-bottom: 1px solid #e8e8e8; gap: 0.8rem; }}
.product-header:hover {{ background: #eef2f7; }}
.product-header h3 {{ flex: 1; font-size: 0.95rem; }}
.product-header .count {{ font-size: 0.85rem; color: #666; }}
.product-body {{ display: none; }}
.product-body.open {{ display: block; }}
.tree-expand {{ width: 20px; font-size: 0.7rem; color: #999; flex-shrink: 0; text-align: center; }}

.ba-section {{ border-bottom: 1px solid #f0f0f0; }}
.ba-header {{ display: flex; align-items: center; padding: 0.7rem 1.5rem 0.7rem 2.5rem; cursor: pointer; gap: 0.8rem; background: #fafbfc; }}
.ba-header:hover {{ background: #f0f4f8; }}
.ba-header h4 {{ flex: 1; font-size: 0.9rem; font-weight: 600; }}
.ba-header .count {{ font-size: 0.8rem; color: #888; }}
.ba-body {{ display: none; }}
.ba-body.open {{ display: block; }}

/* Use case row */
.use-case {{ display: flex; align-items: flex-start; padding: 0.6rem 1.5rem 0.6rem 3.5rem; border-bottom: 1px solid #f5f5f5; gap: 0.8rem; flex-wrap: wrap; }}
.use-case:last-child {{ border-bottom: none; }}
.use-case:hover {{ background: #fafcff; }}
.use-case .uc-main {{ display: flex; align-items: center; gap: 0.8rem; flex: 1; min-width: 200px; }}
.use-case .uc-title {{ flex: 1; font-size: 0.85rem; }}
.use-case .uc-title a {{ color: #1a1a2e; text-decoration: none; }}
.use-case .uc-title a:hover {{ color: #0a6ed1; text-decoration: underline; }}

/* Badges */
.badge {{ font-size: 0.7rem; padding: 0.15rem 0.5rem; border-radius: 3px; font-weight: 600; white-space: nowrap; }}
.badge-info {{ background: #e8f4f8; color: #0c7c9e; }}
.badge-nav {{ background: #f0e6f6; color: #6f42c1; }}
.badge-trans {{ background: #e6f4ea; color: #1e7e34; }}
.badge-anal {{ background: #fff3e0; color: #e65100; }}
.badge-pending {{ font-size: 0.7rem; padding: 0.15rem 0.5rem; border-radius: 3px; font-weight: 600; white-space: nowrap; background: #f0f0f0; color: #999; font-style: italic; }}
.title-only-entry {{ opacity: 0.7; }}
.help-link {{ font-size: 0.75rem; color: #0a6ed1; text-decoration: none; white-space: nowrap; }}
.help-link:hover {{ text-decoration: underline; }}

/* Tier badges */
.tier-badge {{ font-size: 0.65rem; padding: 0.1rem 0.45rem; border-radius: 10px; font-weight: 700; white-space: nowrap; text-transform: uppercase; letter-spacing: 0.3px; }}
.tier-base {{ background: #e8f5e9; color: #2e7d32; border: 1px solid #c8e6c9; }}
.tier-premium {{ background: #fff8e1; color: #f57f17; border: 1px solid #ffe082; }}
.tier-eac {{ background: #e3f2fd; color: #1565c0; border: 1px solid #90caf9; }}
.tier-beta {{ background: #fce4ec; color: #c62828; border: 1px solid #f48fb1; }}

/* Sample prompts — always visible */
.sample-prompts {{ width: 100%; padding: 0.3rem 0 0.4rem 3.5rem; }}
.sample-prompts ul {{ list-style: none; display: flex; flex-wrap: wrap; gap: 0.4rem; }}
.sample-prompts li {{ font-size: 0.78rem; color: #0a6ed1; background: #e8f4f8; padding: 0.25rem 0.7rem; border-radius: 14px; font-style: italic; cursor: default; border: 1px solid #d0e8f0; }}
.sample-prompts li::before {{ content: '💬 '; }}

/* Notes & Parameters */
.uc-notes {{ width: 100%; padding: 0.3rem 0 0.2rem 4.5rem; }}
.uc-notes details {{ font-size: 0.78rem; }}
.uc-notes summary {{ cursor: pointer; color: #7b6d00; font-weight: 600; font-size: 0.78rem; }}
.uc-notes summary:hover {{ color: #5a4f00; }}
.uc-notes .note-item {{ display: flex; align-items: flex-start; gap: 0.4rem; padding: 0.2rem 0; font-size: 0.78rem; color: #555; line-height: 1.4; }}
.uc-notes .note-item::before {{ content: ''; }}

/* Caution boxes — limitations/warnings rendered below prompts */
.uc-caution {{ width: 100%; padding: 0.3rem 0 0.3rem 4.5rem; }}
.caution-box {{ background: #fff8e1; border-left: 3px solid #f9a825; border-radius: 4px; padding: 0.4rem 0.7rem; font-size: 0.76rem; color: #5d4037; line-height: 1.4; }}
.caution-box::before {{ content: '⚠️ '; }}

/* Info notes — descriptive text rendered above prompts */
.uc-info-note {{ width: 100%; padding: 0.2rem 0 0.2rem 4.5rem; }}
.info-note-text {{ font-size: 0.78rem; color: #555; line-height: 1.5; padding: 0.2rem 0; }}
.uc-params {{ width: 100%; padding: 0.15rem 0 0.3rem 4.5rem; }}
.uc-params .param-list {{ display: flex; flex-wrap: wrap; gap: 0.3rem; }}
.uc-params .param-tag {{ font-size: 0.72rem; background: #f5f0e0; color: #7b6d00; padding: 0.15rem 0.55rem; border-radius: 10px; border: 1px solid #e8e0c0; }}
.uc-params .param-tag::before {{ content: '⚙️ '; font-size: 0.65rem; }}

/* Special note */
.special-note {{ width: 100%; padding: 0.5rem 1rem 0.5rem 3.5rem; }}
.note-box {{ background: linear-gradient(135deg, #e3f2fd, #f3e5f5); border-radius: 8px; padding: 1rem; border-left: 4px solid #0a6ed1; font-size: 0.82rem; color: #333; line-height: 1.5; }}
.note-box strong {{ color: #0a6ed1; }}

/* Sub-area */
.sub-area-header {{ display: flex; align-items: center; padding: 0.6rem 1.5rem 0.6rem 3.5rem; cursor: pointer; gap: 0.8rem; }}
.sub-area-header:hover {{ background: #f5f8ff; }}
.sub-area-header h5 {{ flex: 1; font-size: 0.85rem; font-weight: 600; }}
.sub-area-body {{ display: none; }}
.sub-area-body.open {{ display: block; }}
.sub-area-body .use-case {{ padding-left: 4.5rem; }}
.sub-area-body .sample-prompts {{ padding-left: 4.5rem; }}

/* Capability group (parent with multiple use cases) */
.cap-group-header {{ display: flex; align-items: center; padding: 0.6rem 1.5rem 0.6rem 3.5rem; cursor: pointer; gap: 0.8rem; border-bottom: 1px solid #f5f5f5; }}
.cap-group-header:hover {{ background: #f5f8ff; }}
.cap-group-header .cg-title {{ flex: 1; font-size: 0.85rem; font-weight: 600; }}
.cap-group-header .cg-title a {{ color: #1a1a2e; text-decoration: none; }}
.cap-group-header .cg-title a:hover {{ color: #0a6ed1; text-decoration: underline; }}
.cap-group-body {{ display: none; }}
.cap-group-body.open {{ display: block; }}
.cap-group-body .use-case {{ padding-left: 4.5rem; border-left: 2px solid #e0e8f0; margin-left: 3.5rem; padding-left: 1rem; }}
.cap-group-body .sample-prompts {{ padding-left: 4.5rem; }}
.uc-child {{ display: flex; align-items: flex-start; padding: 0.5rem 1.5rem 0.5rem 4.5rem; border-bottom: 1px solid #f8f8f8; gap: 0.6rem; flex-wrap: wrap; }}
.uc-child:hover {{ background: #fafcff; }}
.uc-child .uc-main {{ display: flex; align-items: center; gap: 0.6rem; flex: 1; min-width: 200px; }}
.uc-child .uc-name {{ font-size: 0.82rem; flex: 1; }}
.uc-child .uc-desc {{ width: 100%; font-size: 0.78rem; color: #666; padding-left: 0; line-height: 1.4; margin-top: 0.2rem; }}
.uc-child-prompts {{ width: 100%; padding: 0.2rem 0 0.3rem 4.5rem; }}
.uc-child-prompts ul {{ list-style: none; display: flex; flex-wrap: wrap; gap: 0.3rem; }}
.uc-child-prompts li {{ font-size: 0.75rem; color: #0a6ed1; background: #e8f4f8; padding: 0.2rem 0.6rem; border-radius: 12px; font-style: italic; cursor: default; border: 1px solid #d0e8f0; }}
.uc-child-prompts li::before {{ content: '💬 '; }}

/* Subcategory headers inside child use cases */
.subcat-header {{ margin: 0.5rem 0 0.2rem 0; font-size: 0.8rem; font-weight: 600; color: #444; border-bottom: 1px solid #e8e8e8; padding-bottom: 0.2rem; }}
.subcat-list {{ list-style: none; display: flex; flex-wrap: wrap; gap: 0.35rem; }}
.subcat-item {{ font-size: 0.78rem; color: #333; background: #f4f6f8; padding: 0.25rem 0.7rem; border-radius: 6px; border: 1px solid #dde2e8; }}

/* Inline description next to use case name */
.uc-inline-desc {{ font-size: 0.78rem; color: #666; margin-left: 0.5rem; }}

/* Capability-level description */
.cap-desc {{ width: 100%; padding: 0.3rem 0 0.2rem 3.5rem; font-size: 0.82rem; color: #444; }}

/* Single use case name shown under title */
.cap-single-uc {{ width: 100%; padding: 0.15rem 0 0.15rem 3.5rem; font-size: 0.78rem; color: #555; }}

/* Flattened product badge/link row */
.flat-badge-row {{ padding: 0.5rem 1.5rem 0.3rem; display: flex; gap: 0.6rem; align-items: center; flex-wrap: wrap; }}

.empty {{ padding: 3rem; text-align: center; color: #999; }}
.footer {{ text-align: center; padding: 2rem; color: #999; font-size: 0.8rem; }}

@media (max-width: 768px) {{
  .header h1 {{ font-size: 1.4rem; }}
  .stats {{ gap: 0.5rem; }}
  .stat {{ padding: 0.7rem; min-width: 70px; }}
  .stat .num {{ font-size: 1.2rem; }}
  .type-cards {{ grid-template-columns: repeat(2, 1fr); }}
  .filter-bar {{ flex-direction: column; }}
  .filter-bar input {{ min-width: auto; }}
  .use-case {{ padding-left: 2.5rem; }}
  .sample-prompts {{ padding-left: 2.5rem; }}
  .sub-area-body .use-case {{ padding-left: 3rem; }}
}}
</style>
</head>
<body>

<div class="header">
  <h1>🤖 SAP Business AI — Joule Capabilities Explorer</h1>
  <div class="subtitle">State of Arkansas · Crawl → Walk → Run Adoption Framework</div>
  <div class="phase-bar">
    <div class="phase active">🐣 Crawl — Unified Joule<br><small>✓ Current</small></div>
    <div class="phase next">🚶 Walk — Embedded AI<br><small>Next</small></div>
    <div class="phase future">🏃 Run — Custom AI Projects<br><small>Future</small></div>
  </div>
</div>

<div class="ai-banner">
  🤖 <strong>All capabilities below are powered by Joule</strong> — SAP's generative AI copilot. Ask in natural language and Joule handles the rest.
</div>

<div class="breadcrumb" id="breadcrumb">
  <a onclick="navigateTo('home')">Home</a>
</div>

<div class="main">
  <div class="stats" id="stats"></div>
  <div class="type-cards" id="typeCards"></div>
  <div class="filter-bar">
    <input type="text" id="search" placeholder="Search capabilities..." oninput="applyFilters()">
    <select id="productFilter" onchange="applyFilters()"><option value="">All Products</option></select>
    <select id="areaFilter" onchange="applyFilters()"><option value="">All Business Areas</option></select>
    <select id="typeFilter" onchange="applyFilters()"><option value="">All Types</option></select>
  </div>
  <div class="tree-section" id="treeContent"></div>
</div>

<div class="footer">
  Generated by SAP Business AI Pipeline · Data from SAP Help Portal Joule Capabilities Guide<br>
  {meta['total_entries']} entries · {meta['total_leaves']} use cases · {meta['products']} products · Updated {meta['enriched_at'][:10]}
</div>

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

function renderTypeCards(caps) {{
  const types = {{}};
  caps.forEach(c => {{ types[c.capability_type] = (types[c.capability_type] || 0) + 1; }});
  
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

function populateFilters(caps) {{
  const products = [...new Set(caps.map(c => c.product))].sort();
  const areas = [...new Set(caps.map(c => c.business_area).filter(Boolean))].sort();
  const types = [...new Set(caps.map(c => c.capability_type))].sort();
  
  const pSel = document.getElementById('productFilter');
  pSel.innerHTML = '<option value="">All Products</option>' + products.map(p => '<option value="' + p + '">' + p + '</option>').join('');
  
  const aSel = document.getElementById('areaFilter');
  aSel.innerHTML = '<option value="">All Business Areas</option>' + areas.map(a => '<option value="' + a + '">' + a + '</option>').join('');
  
  const tSel = document.getElementById('typeFilter');
  tSel.innerHTML = '<option value="">All Types</option>' + types.map(t => '<option value="' + t + '">' + t + '</option>').join('');
}}

function getFilteredCaps() {{
  let caps = ALL_CAPS;
  const search = document.getElementById('search').value.toLowerCase();
  const product = document.getElementById('productFilter').value;
  const area = document.getElementById('areaFilter').value;
  const type = document.getElementById('typeFilter').value;
  
  if (activeType) caps = caps.filter(c => c.capability_type === activeType);
  if (search) caps = caps.filter(c => {{
    if (c.title.toLowerCase().includes(search) || c.hierarchy.toLowerCase().includes(search)) return true;
    if ((c.description || '').toLowerCase().includes(search)) return true;
    if (c.use_cases) return c.use_cases.some(uc => (uc.name || '').toLowerCase().includes(search) || (uc.description || '').toLowerCase().includes(search));
    return false;
  }});
  if (product) caps = caps.filter(c => c.product === product);
  if (area) caps = caps.filter(c => c.business_area === area);
  if (type) caps = caps.filter(c => c.capability_type === type);
  
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
  const CAP_TYPES = ['Informational','Transactional','Navigational','Analytical'];
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
  // Render description as type badges if it contains capability type names
  if (desc) {{
    const parts = desc.split(',').map(s => s.trim()).filter(Boolean);
    const allTypes = parts.every(p => CAP_TYPES.includes(p));
    if (allTypes) {{
      parts.forEach(t => {{ html += ' ' + getTypeBadge(t); }});
    }} else {{
      html += '<span class="uc-inline-desc">' + desc.substring(0, 200) + '</span>';
    }}
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
    html += badge + ' ' + tierBadge;
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
  document.getElementById('search').value = '';
  document.getElementById('productFilter').value = '';
  document.getElementById('areaFilter').value = '';
  document.getElementById('typeFilter').value = '';
  render();
}}

function render() {{
  const caps = getFilteredCaps();
  renderStats(caps);
  renderTypeCards(caps);
  renderTree(caps);
  
  let bc = '<a onclick="navigateTo()">Home</a>';
  if (activeType) bc += ' <span>\\u203A</span> <span>' + activeType + ' Capabilities</span>';
  document.getElementById('breadcrumb').innerHTML = bc;
}}

populateFilters(ALL_CAPS);
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