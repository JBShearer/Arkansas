"""Scrape Joule Capabilities Guide from SAP Help Portal.

The Capabilities Guide (d0750ba6...) is the single source of truth for all
Joule capabilities across products. Each leaf page has a rich table with:
  Use Case, Description, Important Notes, Capability Type,
  Sample Prompts, Commercial Model, On Mobile App?, Best Practices

The root page has What's New and Changes to Existing Capabilities.

Usage:
    python3 -m pipeline.sources.scrape_joule
"""

import json
import ssl
import time
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

DELIVERABLE_ID = "d0750ba6-6e30-455c-a879-af14f1054a14"
BASE = "https://help.sap.com"
WORKSPACE = Path(__file__).resolve().parent.parent.parent
DATA_DIR = WORKSPACE / "pipeline" / "data"
SSL_CTX = ssl._create_unverified_context()


# ---------------------------------------------------------------------------
# HTML Parser
# ---------------------------------------------------------------------------

class TableExtractor(HTMLParser):
    """Extract tables preserving paragraph-level detail within cells."""

    def __init__(self):
        super().__init__()
        self.tables = []
        self.in_table = False
        self.current_table = []
        self.current_row = []
        self.current_cell_parts = []
        self.current_part = ""
        self.in_cell = False
        self.section_title = ""
        self.sections = []
        self.in_heading = False
        self.heading_text = ""
        self.skip_tags = set()

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip_tags.add(tag)
            return
        if tag == "table":
            self.in_table = True
            self.current_table = []
        elif tag == "tr":
            self.current_row = []
        elif tag in ("td", "th"):
            self.in_cell = True
            self.current_cell_parts = []
            self.current_part = ""
        elif tag == "p" and self.in_cell:
            if self.current_part.strip():
                self.current_cell_parts.append(self.current_part.strip())
            self.current_part = ""
        elif tag in ("h1", "h2", "h3", "h4"):
            self.in_heading = True
            self.heading_text = ""

    def handle_endtag(self, tag):
        if tag in self.skip_tags:
            self.skip_tags.discard(tag)
            return
        if self.skip_tags:
            return
        if tag == "p" and self.in_cell:
            if self.current_part.strip():
                self.current_cell_parts.append(self.current_part.strip())
            self.current_part = ""
        elif tag in ("td", "th"):
            if self.current_part.strip():
                self.current_cell_parts.append(self.current_part.strip())
            if len(self.current_cell_parts) == 1:
                self.current_row.append(self.current_cell_parts[0])
            elif len(self.current_cell_parts) > 1:
                self.current_row.append(self.current_cell_parts)
            else:
                self.current_row.append("")
            self.in_cell = False
            self.current_cell_parts = []
            self.current_part = ""
        elif tag == "tr":
            if self.current_row:
                self.current_table.append(self.current_row)
        elif tag == "table":
            if self.current_table:
                self.tables.append({"section": self.section_title, "rows": self.current_table})
            self.current_table = []
            self.in_table = False
        elif tag in ("h1", "h2", "h3", "h4"):
            self.in_heading = False
            self.section_title = self.heading_text.strip()
            self.sections.append(self.section_title)

    def handle_data(self, data):
        if self.skip_tags:
            return
        if self.in_cell:
            self.current_part += data
        if self.in_heading:
            self.heading_text += data


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fetch_json(url, retries=5):
    """Fetch JSON with SSL workaround and retry."""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            resp = urllib.request.urlopen(req, timeout=30, context=SSL_CTX)
            data = resp.read()
            if data[:1] == b"<":
                wait = 3 + attempt * 5
                print(f"    ⏳ Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            return json.loads(data.decode("utf-8"))
        except Exception as e:
            if attempt < retries - 1:
                wait = 3 + attempt * 5
                print(f"    ⏳ Error ({e}), retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError(f"Failed after {retries} retries: {url}")


def cell_to_str(cell):
    if isinstance(cell, list):
        return " | ".join(cell)
    return cell


def collect_leaves(nodes, parent_title=""):
    """Recursively collect all leaf pages from TOC."""
    leaves = []
    for node in nodes:
        title = node["title"].strip()
        full_path = f"{parent_title} > {title}" if parent_title else title
        children = node.get("children", [])
        if children:
            leaves.extend(collect_leaves(children, full_path))
        else:
            leaves.append({
                "id": node["id"], "title": title,
                "path": full_path, "parent": parent_title,
            })
    return leaves


# Column-name mapping for the use-case tables
COLUMN_KEYWORDS = {
    "use_case":         ["use case", "capability", "feature", "task", "function"],
    "description":      ["description", "detail"],
    "important_notes":  ["important", "note"],
    "capability_type":  ["capability type", "type", "category"],
    "sample_prompts":   ["sample prompt", "example prompt", "prompt", "example", "how to use"],
    "commercial_model": ["commercial model", "commercial", "license", "edition"],
    "on_mobile":        ["mobile"],
    "best_practices":   ["best practice"],
    "lifecycle":        ["lifecycle", "status", "availability"],
    "product":          ["product"],
    "latest_revision":  ["revision", "date", "release"],
}


def map_columns(header_row):
    """Map header columns to canonical field names."""
    header = [cell_to_str(h).lower().strip().replace("\n", " ") for h in header_row]
    col_map = {}
    for i, h in enumerate(header):
        for field, keywords in COLUMN_KEYWORDS.items():
            if field in col_map:
                continue
            for kw in keywords:
                if kw in h:
                    col_map[field] = i
                    break
    if "use_case" not in col_map and len(header) >= 2:
        col_map["use_case"] = 0
    return col_map


def extract_entries(html, page_title, parent_product):
    """Parse HTML and extract all table entries."""
    parser = TableExtractor()
    parser.feed(html)

    entries = []
    for table_info in parser.tables:
        rows = table_info["rows"]
        section = table_info.get("section", "")
        if len(rows) < 2:
            continue

        col_map = map_columns(rows[0])

        for row in rows[1:]:
            entry = {
                "source_page": page_title,
                "source_product": parent_product,
                "section": section,
            }
            for field, idx in col_map.items():
                if idx < len(row):
                    raw = row[idx]
                    if field in ("description", "sample_prompts", "important_notes",
                                 "best_practices") and isinstance(raw, list):
                        entry[field] = raw
                    else:
                        entry[field] = cell_to_str(raw).strip().replace("\n", " ").replace("  ", " ")

            # Skip noise rows (Supported Languages table)
            uc = entry.get("use_case", "")
            if isinstance(uc, str) and uc.lower() in ("language", "english", "status", "supported", ""):
                continue
            if entry.get("use_case") or entry.get("description"):
                entries.append(entry)

    return entries, parser.sections


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("🔍 Scraping Joule Capabilities Guide")
    print(f"   {BASE}/docs/joule/capabilities-guide/")
    print(f"   Deliverable: {DELIVERABLE_ID}\n")

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Fetch TOC
    print("📋 Fetching table of contents...")
    toc = fetch_json(f"{BASE}/docs/meta/{DELIVERABLE_ID}/toc")
    root = toc[0] if isinstance(toc, list) else toc
    root_id = root["id"]
    leaves = collect_leaves(root.get("children", []))
    print(f"   {len(leaves)} leaf pages + 1 root\n")

    # 2. Scrape root page (What's New + Changes)
    print("📰 Root page (What's New)...")
    root_data = fetch_json(f"{BASE}/docs/content/{DELIVERABLE_ID}/{root_id}")
    root_html = root_data.get("topicContent", "")
    whats_new, root_sections = extract_entries(root_html, "What's New", "Overview")
    print(f"   → {len(whats_new)} entries\n")

    # 3. Scrape all leaf pages
    all_entries = []
    pages_info = []

    for i, leaf in enumerate(leaves):
        print(f"   [{i+1}/{len(leaves)}] {leaf['title']}", end="", flush=True)
        try:
            entries = []
            sections = []
            page_url = f"{BASE}/docs/content/{DELIVERABLE_ID}/{leaf['id']}"

            # Try up to 3 times — rate limiting can return empty/truncated content
            for attempt in range(3):
                data = fetch_json(page_url)
                html = data.get("topicContent", "")
                if not html:
                    wait = 5 + attempt * 5
                    print(f" ⏳ empty({attempt+1})", end="", flush=True)
                    time.sleep(wait)
                    continue
                entries, sections = extract_entries(html, leaf["title"], leaf["parent"])
                if entries:
                    break
                # Got HTML but 0 entries — may be truncated
                wait = 5 + attempt * 5
                print(f" ⏳ retry({attempt+1})", end="", flush=True)
                time.sleep(wait)

            pages_info.append({
                "id": leaf["id"], "title": leaf["title"],
                "path": leaf["path"], "parent": leaf["parent"],
                "entries_count": len(entries),
                "sections": sections,
            })

            for e in entries:
                e["page_id"] = leaf["id"]
            all_entries.extend(entries)

            print(f" → {len(entries)} entries")
        except Exception as e:
            print(f" ⚠️ {e}")
            pages_info.append({
                "id": leaf["id"], "title": leaf["title"],
                "path": leaf["path"], "error": str(e),
            })
        time.sleep(0.5)

    # 4. Save
    output = {
        "metadata": {
            "source": "SAP Help Portal — Joule Capabilities Guide",
            "deliverable_id": DELIVERABLE_ID,
            "url": f"{BASE}/docs/joule/capabilities-guide/",
            "scraped_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "total_leaf_pages": len(leaves),
            "total_whats_new": len(whats_new),
            "total_capabilities": len(all_entries),
        },
        "whats_new": whats_new,
        "pages": pages_info,
        "capabilities": all_entries,
    }

    out_path = DATA_DIR / "joule_capabilities_raw.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Saved to {out_path}")

    # 5. Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"What's New entries: {len(whats_new)}")
    print(f"Leaf capabilities:  {len(all_entries)}")
    print(f"Total combined:     {len(whats_new) + len(all_entries)}\n")

    by_page = {}
    for e in all_entries:
        by_page.setdefault(e["source_page"], []).append(e)

    for page in sorted(by_page.keys()):
        items = by_page[page]
        types = {}
        models = {}
        for item in items:
            t = item.get("capability_type", "?")
            types[t] = types.get(t, 0) + 1
            m = item.get("commercial_model", "—")
            models[m] = models.get(m, 0) + 1
        type_str = ", ".join(f"{t}:{n}" for t, n in sorted(types.items()))
        model_str = ", ".join(f"{m}:{n}" for m, n in sorted(models.items()))
        print(f"  {page}: {len(items)} | {type_str} | {model_str}")


if __name__ == "__main__":
    main()