"""Scrape Joule Capabilities Guide from SAP Help Portal.

The Capabilities Guide is the single source of truth for all Joule
capabilities. We maintain the full TOC in toc_tree.txt (indented text)
and fetch each page via the slug-based content API:

    https://help.sap.com/docs/content/{DELIVERABLE_ID}/{slug}

The TOC API (/docs/meta/.../toc) returns a STALE subset, so we derive
slugs from page titles using SAP Help's URL conventions.

Usage:
    python3 -m pipeline.sources.scrape_joule
"""

import json
import re
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
# TOC Tree Parser
# ---------------------------------------------------------------------------

def parse_toc_file(filepath):
    """Parse indented text tree into structured TOC list."""
    lines = Path(filepath).read_text().splitlines()
    root = []
    stack = [(root, -1)]  # (children_list, indent_level)

    for line in lines:
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        title = line.strip()

        node = {"title": title, "children": []}

        # Pop stack to find parent
        while stack and stack[-1][1] >= indent:
            stack.pop()

        parent_children = stack[-1][0]
        parent_children.append(node)
        stack.append((node["children"], indent))

    return root


def title_to_slug(title):
    """Convert a page title to a URL slug matching SAP Help conventions."""
    s = title.strip().lower()
    s = re.sub(r'&', '', s)
    s = re.sub(r'/', ' ', s)
    s = re.sub(r'[^a-z0-9\s-]', '', s)
    s = re.sub(r'\s+', '-', s.strip())
    s = re.sub(r'-+', '-', s)
    return s.strip('-')


def flatten_toc(nodes, parent="", depth=0):
    """Flatten TOC tree into list of page descriptors with slugs."""
    pages = []
    for node in nodes:
        title = node["title"]
        path = f"{parent} > {title}" if parent else title
        children = node.get("children", [])
        pages.append({
            "title": title,
            "slug": title_to_slug(title),
            "path": path,
            "parent": parent,
            "is_leaf": not children,
            "depth": depth,
        })
        if children:
            pages.extend(flatten_toc(children, path, depth + 1))
    return pages


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

HEADERS = {
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/131.0.0.0 Safari/537.36",
    "Referer": "https://help.sap.com/docs/joule/capabilities-guide/",
}


def fetch_json(url, retries=6):
    """Fetch JSON with SSL workaround, browser headers, and retry."""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            resp = urllib.request.urlopen(req, timeout=30, context=SSL_CTX)
            data = resp.read()
            if data[:1] == b"<":
                wait = 5 + attempt * 10
                print(f" ⏳ html({attempt+1},{wait}s)", end="", flush=True)
                time.sleep(wait)
                continue
            return json.loads(data.decode("utf-8"))
        except Exception as e:
            if attempt < retries - 1:
                wait = 5 + attempt * 10
                print(f" ⏳ err({attempt+1},{wait}s)", end="", flush=True)
                time.sleep(wait)
            else:
                raise
    raise RuntimeError(f"Failed after {retries} retries: {url}")


def cell_to_str(cell):
    if isinstance(cell, list):
        return " | ".join(cell)
    return cell


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


def extract_entries(html, page_title, parent_path):
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
                "source_path": parent_path,
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
    print("🔍 Scraping Joule Capabilities Guide — FULL TREE (slug-based)")
    print(f"   {BASE}/docs/joule/capabilities-guide/")
    print(f"   Deliverable: {DELIVERABLE_ID}\n")

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Parse TOC
    toc_path = Path(__file__).parent / "toc_tree.txt"
    print(f"📋 Loading TOC from {toc_path.name}...")
    tree = parse_toc_file(toc_path)
    all_pages = flatten_toc(tree)
    leaves = [p for p in all_pages if p["is_leaf"]]
    branches = [p for p in all_pages if not p["is_leaf"]]
    print(f"   {len(all_pages)} total pages ({len(leaves)} leaves, {len(branches)} branches)\n")

    # Check for slug collisions
    slug_counts = {}
    for p in all_pages:
        slug_counts[p["slug"]] = slug_counts.get(p["slug"], 0) + 1
    collisions = {s: c for s, c in slug_counts.items() if c > 1}
    if collisions:
        print(f"⚠️  {len(collisions)} slug collisions (SAP disambiguates these):")
        for s, c in collisions.items():
            pages_with_slug = [p["path"] for p in all_pages if p["slug"] == s]
            print(f"   '{s}' ({c}x): {pages_with_slug}")
        print()

    # 2. Scrape every page
    all_entries = []
    pages_info = []
    failed = []

    for i, page in enumerate(all_pages):
        kind = "leaf" if page["is_leaf"] else "BRANCH"
        print(f"   [{i+1}/{len(all_pages)}] {page['title']} ({kind})", end="", flush=True)

        page_url = f"{BASE}/docs/content/{DELIVERABLE_ID}/{page['slug']}"
        try:
            entries = []
            sections = []
            topic_id = None
            content_len = 0

            for attempt in range(5):
                data = fetch_json(page_url)
                html = data.get("topicContent", "")
                topic_id = data.get("topicId")
                content_len = len(html) if html else 0

                if not html:
                    wait = 8 + attempt * 8
                    print(f" ⏳ empty({attempt+1})", end="", flush=True)
                    time.sleep(wait)
                    continue

                entries, sections = extract_entries(html, page["title"], page["path"])
                if entries:
                    break
                # Pages without tables are valid (text-only content)
                if "<table" not in html:
                    break
                # Has table but 0 entries — might be truncated
                wait = 8 + attempt * 8
                print(f" ⏳ retry({attempt+1})", end="", flush=True)
                time.sleep(wait)

            info = {
                "title": page["title"],
                "slug": page["slug"],
                "topic_id": topic_id,
                "path": page["path"],
                "parent": page["parent"],
                "is_leaf": page["is_leaf"],
                "depth": page["depth"],
                "content_bytes": content_len,
                "entries_count": len(entries),
                "sections": sections,
            }
            pages_info.append(info)

            for e in entries:
                e["slug"] = page["slug"]
                e["topic_id"] = topic_id
            all_entries.extend(entries)

            if entries:
                print(f" → {len(entries)} entries")
            else:
                print(f" → 0 ({content_len}b)")
                if content_len == 0:
                    failed.append(page)

        except Exception as e:
            print(f" ⚠️ {e}")
            failed.append(page)
            pages_info.append({
                "title": page["title"],
                "slug": page["slug"],
                "path": page["path"],
                "error": str(e),
            })

        time.sleep(0.5)

    # 3. Retry failed pages
    if failed:
        print(f"\n🔄 Retry pass for {len(failed)} failed/empty pages...")
        time.sleep(10)
        for page in failed:
            print(f"   Retrying: {page['title']}", end="", flush=True)
            try:
                page_url = f"{BASE}/docs/content/{DELIVERABLE_ID}/{page['slug']}"
                for attempt in range(5):
                    data = fetch_json(page_url)
                    html = data.get("topicContent", "")
                    if not html:
                        wait = 10 + attempt * 10
                        print(f" ⏳ ({attempt+1})", end="", flush=True)
                        time.sleep(wait)
                        continue
                    entries, sections = extract_entries(html, page["title"], page["path"])
                    # Update page info
                    for pi in pages_info:
                        if pi.get("slug") == page["slug"] and pi.get("title") == page["title"]:
                            pi["entries_count"] = len(entries)
                            pi["sections"] = sections
                            pi["content_bytes"] = len(html)
                            pi["topic_id"] = data.get("topicId")
                            if "error" in pi:
                                del pi["error"]
                    for e in entries:
                        e["slug"] = page["slug"]
                        e["topic_id"] = data.get("topicId")
                    all_entries.extend(entries)
                    print(f" → {len(entries)} entries")
                    break
                else:
                    print(f" → still empty")
            except Exception as e:
                print(f" ⚠️ {e}")
            time.sleep(3)

    # 4. Deduplicate entries by (topic_id, use_case) — slug collisions
    #    cause the same page to be fetched twice for Public/Private editions
    seen = set()
    deduped = []
    for e in all_entries:
        key = (e.get("topic_id", ""), e.get("use_case", ""), e.get("section", ""))
        if key not in seen:
            seen.add(key)
            deduped.append(e)
    if len(deduped) < len(all_entries):
        print(f"\n🔄 Deduplicated: {len(all_entries)} → {len(deduped)} entries")
    all_entries = deduped

    # 5. Save
    output = {
        "metadata": {
            "source": "SAP Help Portal — Joule Capabilities Guide",
            "deliverable_id": DELIVERABLE_ID,
            "url": f"{BASE}/docs/joule/capabilities-guide/",
            "scraped_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "total_pages": len(all_pages),
            "total_leaves": len(leaves),
            "total_branches": len(branches),
            "total_capabilities": len(all_entries),
        },
        "pages": pages_info,
        "capabilities": all_entries,
    }

    out_path = DATA_DIR / "joule_capabilities_raw.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Saved to {out_path}")

    # 6. Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Total capabilities: {len(all_entries)}\n")

    by_page = {}
    for e in all_entries:
        by_page.setdefault(e["source_page"], []).append(e)

    for page in sorted(by_page.keys()):
        items = by_page[page]
        types = {}
        for item in items:
            t = item.get("capability_type", "?")
            types[t] = types.get(t, 0) + 1
        type_str = ", ".join(f"{t}:{n}" for t, n in sorted(types.items()))
        print(f"  {page}: {len(items)} | {type_str}")

    # Pages with 0 entries
    zero = [p for p in pages_info if p.get("entries_count", 0) == 0 and p.get("content_bytes", 0) > 0]
    if zero:
        print(f"\n  ({len(zero)} pages with content but no table entries — text-only)")


if __name__ == "__main__":
    main()