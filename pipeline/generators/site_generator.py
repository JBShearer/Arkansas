"""Generate the interactive Joule Capabilities Explorer HTML page.

Reads the scraped data and embeds it as JSON inside a self-contained
HTML file with client-side filtering by:
  - Capability Type (Navigational, Informational, Transactional, Analytical)
  - Product
  - Process Area (for S/4)
  - Commercial Model (base vs premium)

Usage:
    python3 -m pipeline.generators.site_generator
"""

import json
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent.parent
DATA_FILE = WORKSPACE / "pipeline" / "data" / "joule_capabilities_raw.json"
SITE_DIR = WORKSPACE / "site"


def normalize_product(path):
    """Extract clean product name from source_path."""
    parts = path.split(" > ")
    top = parts[0]
    # Clean up product names
    if "S/4HANA Cloud Public" in top:
        return "SAP S/4HANA Cloud Public Edition"
    elif "S/4HANA Cloud Private" in top:
        return "SAP S/4HANA Cloud Private Edition"
    elif "SuccessFactors" in top:
        return "SAP SuccessFactors"
    elif "Concur" in top:
        return "SAP Concur"
    elif "Ariba Solutions" in top:
        return "SAP Ariba"
    elif "Ariba Intake" in top:
        return "SAP Ariba Intake Management"
    elif "Signavio" in top:
        return "SAP Signavio"
    elif "BTP Cockpit" in top:
        return "SAP BTP Cockpit"
    elif "Build Work Zone" in top:
        return "SAP Build Work Zone"
    elif "Integrated Business Planning" in top:
        return "SAP IBP"
    elif "Digital Manufacturing" in top:
        return "SAP Digital Manufacturing"
    elif "Logistics Management" in top:
        return "SAP Logistics Management"
    elif "Risk and Assurance" in top:
        return "SAP Risk and Assurance Management"
    elif "Integrated Product Development" in top:
        return "SAP Integrated Product Development"
    elif "Field Service" in top:
        return "SAP Field Service Management"
    elif "Batch Release" in top:
        return "SAP Batch Release Hub"
    elif "Sports One" in top:
        return "SAP Sports One"
    elif "Incentive" in top:
        return "SAP Incentive Management"
    elif "Analytical Insights" in top:
        return "SAP Analytics Cloud"
    elif "What's New" in top:
        return "What's New"
    return top


def get_process_area(path):
    """Extract process area from source_path (level 2 for S/4, level 1 for others)."""
    parts = path.split(" > ")
    if "S/4HANA" in path and len(parts) > 1:
        return parts[1]
    elif "SuccessFactors" in path and len(parts) > 1:
        return parts[1]
    return parts[0] if parts else ""


def classify_commercial(model):
    """Classify into Base / Premium / Included."""
    if not model:
        return "Unknown"
    m = model.lower()
    if "standard" in m or "not applicable" in m:
        return "Base (Standard)"
    elif "sap business ai" in m:
        return "Premium (SAP Business AI)"
    elif "included" in m:
        return "Base (Included)"
    return model


def build_entries(caps):
    """Transform raw capabilities into display-ready entries."""
    entries = []
    for c in caps:
        # Skip What's New entries (they're change log, not use cases)
        path = c.get("source_path", "")
        if "What's New" in path:
            continue

        use_case = c.get("use_case", "")
        if not use_case:
            continue

        cap_type = c.get("capability_type", "Unknown")
        if not cap_type or cap_type == "?":
            cap_type = "Unknown"

        product = normalize_product(path)
        area = get_process_area(path)
        model = classify_commercial(c.get("commercial_model", ""))

        # Handle prompts
        prompts = c.get("sample_prompts", "")
        if isinstance(prompts, list):
            prompts = "\n".join(prompts)

        # Handle notes
        notes = c.get("important_notes", "")
        if isinstance(notes, list):
            notes = "\n".join(notes)

        # Handle description
        desc = c.get("description", "")
        if isinstance(desc, list):
            desc = "\n".join(desc)

        # Best practices
        bp = c.get("best_practices", "")
        if isinstance(bp, list):
            bp = "\n".join(bp)

        entry = {
            "use_case": use_case,
            "description": desc,
            "type": cap_type,
            "product": product,
            "area": area,
            "commercial": model,
            "prompts": prompts,
            "notes": notes,
            "best_practices": bp,
            "mobile": c.get("on_mobile", ""),
            "source_page": c.get("source_page", ""),
        }
        entries.append(entry)

    return entries


def generate_html(entries):
    """Generate the full HTML page."""
    # Collect filter values
    types = sorted(set(e["type"] for e in entries))
    products = sorted(set(e["product"] for e in entries))
    areas = sorted(set(e["area"] for e in entries if e["area"]))
    commercials = sorted(set(e["commercial"] for e in entries))

    data_json = json.dumps(entries, ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SAP Business AI — Joule Capabilities Explorer</title>
<style>
:root {{
  --sap-blue: #0070F2;
  --sap-dark: #1B2B3A;
  --sap-light: #F5F6F7;
  --sap-green: #107E3E;
  --sap-orange: #E76500;
  --sap-red: #BB0000;
  --sap-purple: #7B3B99;
  --radius: 8px;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: var(--sap-light);
  color: var(--sap-dark);
  line-height: 1.5;
}}
header {{
  background: linear-gradient(135deg, var(--sap-dark) 0%, #2C4A62 100%);
  color: white;
  padding: 2rem 1.5rem;
  text-align: center;
}}
header h1 {{
  font-size: 1.8rem;
  font-weight: 700;
  margin-bottom: 0.3rem;
}}
header p {{
  opacity: 0.85;
  font-size: 1rem;
}}
.toolbar {{
  background: white;
  border-bottom: 1px solid #ddd;
  padding: 1rem 1.5rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  align-items: center;
  position: sticky;
  top: 0;
  z-index: 100;
  box-shadow: 0 2px 4px rgba(0,0,0,0.08);
}}
.toolbar label {{
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  color: #666;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}}
.toolbar select, .toolbar input {{
  padding: 0.5rem 0.75rem;
  border: 1px solid #ccc;
  border-radius: var(--radius);
  font-size: 0.9rem;
  min-width: 180px;
  background: white;
}}
.toolbar select:focus, .toolbar input:focus {{
  outline: none;
  border-color: var(--sap-blue);
  box-shadow: 0 0 0 2px rgba(0,112,242,0.2);
}}
.stats {{
  margin-left: auto;
  font-size: 0.9rem;
  color: #666;
  white-space: nowrap;
}}
.stats strong {{
  color: var(--sap-blue);
  font-size: 1.1rem;
}}
main {{
  max-width: 1400px;
  margin: 0 auto;
  padding: 1.5rem;
}}
.card {{
  background: white;
  border-radius: var(--radius);
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  margin-bottom: 0.75rem;
  overflow: hidden;
  transition: box-shadow 0.2s;
}}
.card:hover {{
  box-shadow: 0 3px 12px rgba(0,0,0,0.15);
}}
.card-header {{
  padding: 1rem 1.25rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  cursor: pointer;
  user-select: none;
}}
.card-header:hover {{
  background: #FAFBFC;
}}
.card-header .expand {{
  color: #aaa;
  font-size: 0.8rem;
  transition: transform 0.2s;
  flex-shrink: 0;
}}
.card.open .card-header .expand {{
  transform: rotate(90deg);
}}
.card-header .title {{
  font-weight: 600;
  font-size: 1rem;
  flex: 1;
}}
.badge {{
  display: inline-block;
  padding: 0.15rem 0.6rem;
  border-radius: 12px;
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  white-space: nowrap;
}}
.badge-nav {{ background: #E8F4FD; color: #0854A0; }}
.badge-info {{ background: #E8FDF0; color: #107E3E; }}
.badge-trans {{ background: #FFF3E0; color: #E76500; }}
.badge-unknown {{ background: #F0F0F0; color: #666; }}
.badge-base {{ background: #E8FDF0; color: #107E3E; }}
.badge-premium {{ background: #FFF3E0; color: #E76500; }}
.badge-included {{ background: #E8F4FD; color: #0854A0; }}
.badge-product {{
  background: #F0E8FD;
  color: var(--sap-purple);
}}
.card-body {{
  display: none;
  padding: 0 1.25rem 1.25rem 1.25rem;
  border-top: 1px solid #eee;
}}
.card.open .card-body {{
  display: block;
}}
.detail-grid {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  margin-top: 0.75rem;
}}
@media (max-width: 768px) {{
  .detail-grid {{ grid-template-columns: 1fr; }}
  .toolbar {{ flex-direction: column; }}
  .toolbar label {{ width: 100%; }}
  .toolbar select, .toolbar input {{ width: 100%; min-width: 0; }}
  .stats {{ margin-left: 0; }}
}}
.detail-section {{
  background: #FAFBFC;
  padding: 0.75rem 1rem;
  border-radius: var(--radius);
  border-left: 3px solid var(--sap-blue);
}}
.detail-section h4 {{
  font-size: 0.75rem;
  text-transform: uppercase;
  color: #666;
  margin-bottom: 0.4rem;
}}
.detail-section p, .detail-section ul {{
  font-size: 0.9rem;
  color: #333;
}}
.detail-section.prompts {{
  border-left-color: var(--sap-green);
  grid-column: 1 / -1;
}}
.detail-section.notes {{
  border-left-color: var(--sap-orange);
  grid-column: 1 / -1;
}}
.detail-section.bp {{
  border-left-color: var(--sap-purple);
  grid-column: 1 / -1;
}}
.prompt-item {{
  background: white;
  padding: 0.5rem 0.75rem;
  border-radius: 6px;
  margin: 0.4rem 0;
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 0.85rem;
  border: 1px solid #e0e0e0;
}}
.meta {{
  display: flex;
  gap: 0.5rem;
  align-items: center;
  flex-wrap: wrap;
  font-size: 0.8rem;
  color: #777;
  margin-top: 0.25rem;
}}
footer {{
  text-align: center;
  padding: 2rem;
  color: #888;
  font-size: 0.8rem;
}}
footer a {{ color: var(--sap-blue); text-decoration: none; }}
.no-results {{
  text-align: center;
  padding: 3rem;
  color: #888;
  font-size: 1.1rem;
}}
</style>
</head>
<body>

<header>
  <h1>🤖 SAP Business AI — Joule Capabilities Explorer</h1>
  <p>State of Arkansas • Crawl → Walk → Run Adoption</p>
</header>

<div class="toolbar">
  <label>
    Search
    <input type="text" id="searchBox" placeholder="Search use cases, prompts…">
  </label>
  <label>
    Type
    <select id="filterType">
      <option value="">All Types</option>
    </select>
  </label>
  <label>
    Product
    <select id="filterProduct">
      <option value="">All Products</option>
    </select>
  </label>
  <label>
    Process Area
    <select id="filterArea">
      <option value="">All Areas</option>
    </select>
  </label>
  <label>
    Licensing
    <select id="filterCommercial">
      <option value="">All</option>
    </select>
  </label>
  <div class="stats">
    Showing <strong id="countShowing">0</strong> of <strong id="countTotal">0</strong> capabilities
  </div>
</div>

<main id="cardContainer"></main>

<footer>
  Data sourced from <a href="https://help.sap.com/docs/joule/capabilities-guide/" target="_blank">SAP Help — Joule Capabilities Guide</a>.
  Last scraped: {json.loads(open(DATA_FILE).read())["metadata"]["scraped_at"][:10]}.
  Built with the Arkansas SAP Business AI Pipeline.
</footer>

<script>
const DATA = {data_json};

// Populate filters
function populateSelect(id, values) {{
  const sel = document.getElementById(id);
  values.forEach(v => {{
    const opt = document.createElement('option');
    opt.value = v;
    opt.textContent = v;
    sel.appendChild(opt);
  }});
}}

const types = [...new Set(DATA.map(d => d.type))].sort();
const products = [...new Set(DATA.map(d => d.product))].sort();
const areas = [...new Set(DATA.map(d => d.area).filter(Boolean))].sort();
const commercials = [...new Set(DATA.map(d => d.commercial))].sort();

populateSelect('filterType', types);
populateSelect('filterProduct', products);
populateSelect('filterArea', areas);
populateSelect('filterCommercial', commercials);

document.getElementById('countTotal').textContent = DATA.length;

function typeBadge(t) {{
  const cls = t === 'Navigational' ? 'badge-nav'
    : t === 'Informational' ? 'badge-info'
    : t === 'Transactional' ? 'badge-trans'
    : 'badge-unknown';
  return `<span class="badge ${{cls}}">${{t}}</span>`;
}}

function commercialBadge(c) {{
  const cls = c.includes('Premium') ? 'badge-premium'
    : c.includes('Base') ? 'badge-base'
    : 'badge-included';
  return `<span class="badge ${{cls}}">${{c}}</span>`;
}}

function escHtml(s) {{
  if (!s) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}}

function formatPrompts(prompts) {{
  if (!prompts) return '';
  return prompts.split('\\n').filter(Boolean).map(p =>
    `<div class="prompt-item">${{escHtml(p.replace(/^"|"$/g, ''))}}</div>`
  ).join('');
}}

function formatText(text) {{
  if (!text) return '';
  return text.split('\\n').filter(Boolean).map(p => `<p>${{escHtml(p)}}</p>`).join('');
}}

function renderCards(filtered) {{
  const container = document.getElementById('cardContainer');
  document.getElementById('countShowing').textContent = filtered.length;

  if (filtered.length === 0) {{
    container.innerHTML = '<div class="no-results">No capabilities match your filters.</div>';
    return;
  }}

  // Limit rendering for performance
  const toRender = filtered.slice(0, 500);
  let html = '';

  toRender.forEach((e, i) => {{
    const hasPrompts = e.prompts && e.prompts.trim();
    const hasNotes = e.notes && e.notes.trim();
    const hasDesc = e.description && e.description.trim();
    const hasBP = e.best_practices && e.best_practices.trim();

    html += `<div class="card" id="card-${{i}}">
      <div class="card-header" onclick="toggleCard(${{i}})">
        <span class="expand">▶</span>
        <span class="title">${{escHtml(e.use_case)}}</span>
        ${{typeBadge(e.type)}}
        ${{commercialBadge(e.commercial)}}
        <span class="badge badge-product">${{escHtml(e.product)}}</span>
      </div>
      <div class="card-body">
        <div class="meta">
          <span>📂 ${{escHtml(e.area)}}</span>
          <span>📄 ${{escHtml(e.source_page)}}</span>
          ${{e.mobile ? '<span>📱 Mobile: ' + escHtml(e.mobile) + '</span>' : ''}}
        </div>
        <div class="detail-grid">
          ${{hasDesc ? `<div class="detail-section"><h4>Description</h4>${{formatText(e.description)}}</div>` : ''}}
          ${{hasPrompts ? `<div class="detail-section prompts"><h4>💬 Sample Prompts</h4>${{formatPrompts(e.prompts)}}</div>` : ''}}
          ${{hasNotes ? `<div class="detail-section notes"><h4>⚠️ Important Notes</h4>${{formatText(e.notes)}}</div>` : ''}}
          ${{hasBP ? `<div class="detail-section bp"><h4>✅ Best Practices</h4>${{formatText(e.notes)}}</div>` : ''}}
        </div>
      </div>
    </div>`;
  }});

  if (filtered.length > 500) {{
    html += `<div class="no-results">Showing first 500 of ${{filtered.length}} results. Narrow your filters to see more.</div>`;
  }}

  container.innerHTML = html;
}}

function toggleCard(i) {{
  document.getElementById('card-' + i).classList.toggle('open');
}}

function applyFilters() {{
  const search = document.getElementById('searchBox').value.toLowerCase();
  const type = document.getElementById('filterType').value;
  const product = document.getElementById('filterProduct').value;
  const area = document.getElementById('filterArea').value;
  const commercial = document.getElementById('filterCommercial').value;

  const filtered = DATA.filter(e => {{
    if (type && e.type !== type) return false;
    if (product && e.product !== product) return false;
    if (area && e.area !== area) return false;
    if (commercial && e.commercial !== commercial) return false;
    if (search) {{
      const blob = (e.use_case + ' ' + e.description + ' ' + e.prompts + ' ' + e.area + ' ' + e.product).toLowerCase();
      if (!blob.includes(search)) return false;
    }}
    return true;
  }});

  renderCards(filtered);
}}

// Dynamic area filter based on selected product
document.getElementById('filterProduct').addEventListener('change', function() {{
  const product = this.value;
  const areaSelect = document.getElementById('filterArea');
  const currentArea = areaSelect.value;
  
  // Get areas for selected product (or all)
  let relevantAreas;
  if (product) {{
    relevantAreas = [...new Set(DATA.filter(d => d.product === product).map(d => d.area).filter(Boolean))].sort();
  }} else {{
    relevantAreas = areas;
  }}
  
  // Rebuild area select
  areaSelect.innerHTML = '<option value="">All Areas</option>';
  relevantAreas.forEach(a => {{
    const opt = document.createElement('option');
    opt.value = a;
    opt.textContent = a;
    if (a === currentArea) opt.selected = true;
    areaSelect.appendChild(opt);
  }});
  
  applyFilters();
}});

document.getElementById('searchBox').addEventListener('input', applyFilters);
document.getElementById('filterType').addEventListener('change', applyFilters);
document.getElementById('filterArea').addEventListener('change', applyFilters);
document.getElementById('filterCommercial').addEventListener('change', applyFilters);

// Initial render
applyFilters();
</script>
</body>
</html>"""

    return html


def main():
    print("📊 Generating Joule Capabilities Explorer...")

    with open(DATA_FILE) as f:
        data = json.load(f)

    caps = data["capabilities"]
    print(f"   Loaded {len(caps)} raw capabilities")

    entries = build_entries(caps)
    print(f"   Prepared {len(entries)} display entries")

    html = generate_html(entries)

    SITE_DIR.mkdir(parents=True, exist_ok=True)
    out_path = SITE_DIR / "index.html"
    with open(out_path, "w") as f:
        f.write(html)
    print(f"   💾 Saved to {out_path} ({len(html):,} bytes)")

    # Capability counts
    by_type = {}
    by_product = {}
    by_commercial = {}
    for e in entries:
        by_type[e["type"]] = by_type.get(e["type"], 0) + 1
        by_product[e["product"]] = by_product.get(e["product"], 0) + 1
        by_commercial[e["commercial"]] = by_commercial.get(e["commercial"], 0) + 1

    print(f"\n   By type: {by_type}")
    print(f"   By licensing: {by_commercial}")
    print(f"   By product: {dict(sorted(by_product.items(), key=lambda x: -x[1]))}")


if __name__ == "__main__":
    main()