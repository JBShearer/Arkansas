"""Enrich TOC tree with REAL scraped data from SAP Help Portal.

Eliminates 'Mixed' type. Every capability gets exactly one type:
  - Informational: Display, view, search, check, look up, fetch data
  - Navigational:  Open apps, go to screens, find apps
  - Transactional: Create, change, manage, process, update, delete
  - Analytical:    Insights, forecasts, anomaly detection, analytics

Sample prompts come from the ACTUAL SAP Help pages (scraped data).

Usage:
    python3 -m pipeline.enrich_toc
"""

import json
import re
import time
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
TOC_FILE = WORKSPACE / "pipeline" / "sources" / "toc_tree.txt"
SCRAPED_FILE = WORKSPACE / "pipeline" / "data" / "scraped_use_cases.json"
OUT_FILE = WORKSPACE / "pipeline" / "data" / "joule_capabilities_raw.json"

# ── Product mapping ──────────────────────────────────────────────
PRODUCT_MAP = {
    "Joule in SAP SuccessFactors": "SAP SuccessFactors",
    "Joule in SAP S/4HANA Cloud Public Edition": "SAP S/4HANA Cloud Public Edition",
    "Joule in SAP S/4HANA Cloud Private Edition": "SAP S/4HANA Cloud Private Edition",
    "Joule in SAP BTP Cockpit": "SAP BTP Cockpit",
    "Joule in SAP Integrated Product Development": "SAP Integrated Product Development",
    "Joule in SAP Digital Manufacturing": "SAP Digital Manufacturing",
    "Joule in SAP Logistics Management": "SAP Logistics Management",
    "Joule in SAP Integrated Business Planning": "SAP Integrated Business Planning",
    "Joule in SAP Risk and Assurance Management": "SAP Risk and Assurance Management",
    "Joule in SAP Signavio Solutions": "SAP Signavio Solutions",
    "Joule in SAP Concur Solutions": "SAP Concur Solutions",
    "Joule in SAP Ariba Solutions": "SAP Ariba Solutions",
    "Joule in SAP Ariba Intake Management": "SAP Ariba Intake Management",
    "Joule in SAP Field Service Management": "SAP Field Service Management",
    "Joule in SAP Build Work Zone, advanced edition": "SAP Build Work Zone",
    "Joule in SAP Batch Release Hub for Life Sciences": "SAP Batch Release Hub",
    "Joule in SAP Sports One": "SAP Sports One",
    "Joule in SAP Incentive Management": "SAP Incentive Management",
    "Analytical Insights with SAP Analytics Cloud": "SAP Analytics Cloud",
}

# ── Skip list ────────────────────────────────────────────────────
SKIP_TITLES = [
    "What's New", "Archive", "Joule Capabilities", "Activating Business AI",
    "Multi Language", "Glossary", "Important Notes", "Initial Setup",
    "Release-Specific", "Configuring", "Configuration",
]

# ── Capability type classification ───────────────────────────────
# NO "Mixed" — every capability gets exactly one type.
# Priority: Analytical > Navigational > Transactional > Informational

INFORMATIONAL_PATTERNS = [
    r"\bDisplay\b", r"\bShow\b", r"\bView\b", r"\bSearch\b", r"\bList\b",
    r"\bCheck\b", r"\bGet\b", r"\bLook\s?up\b", r"\bFind\b", r"\bRetrieve\b",
    r"\bDisplaying\b", r"\bSearching\b", r"\bViewing\b", r"\bFetch\b",
    r"\bSummariz", r"\bAsk for\b",
    r"\bError Explanation\b", r"\bError Summary\b", r"\bError Explanations\b",
    r"\bSummary\b", r"\bOverview\b", r"\bStatus\b", r"\bBalance\b",
    r"\bLine Items\b", r"\bDocument Flow\b", r"\bPositions?\b",
    r"\bCommitment\b", r"\bAvailability\b",
    r"\bInformational Capability\b",
]

TRANSACTIONAL_PATTERNS = [
    r"\bCreate\b", r"\bCreating\b", r"\bManage\b", r"\bManaging\b",
    r"\bProcess\b", r"\bProcessing\b", r"\bExecut", r"\bPost\b",
    r"\bRelease\b", r"\bClearing\b", r"\bApprove\b", r"\bChange\b",
    r"\bChanging\b", r"\bEdit\b", r"\bUpdate\b", r"\bUpdating\b",
    r"\bDelete\b", r"\bCancel\b", r"\bReverse\b", r"\bAssign\b",
    r"\bReassign\b", r"\bTransfer\b", r"\bConvert\b", r"\bClose\b",
    r"\bMaking\b", r"\bGenerating\b", r"\bRenewing\b", r"\bDestroying\b",
    r"\bPerform\b", r"\bComplete\b",
    r"\bBudgeting\b", r"\bReminders?\b", r"\bRecurring\b",
    r"\bTemplates?\b", r"\bAccrual\b",
    r"\bTransactional Capabilit",
    r"\bBilling Request\b", r"\bInvoicing Document\b",
    r"\bClarification Case\b", r"\bDispute Resolution\b",
    r"\bPayment Resolution\b", r"\bBilling Plan\b",
    r"\bContract Accounting\b", r"\bConvergent Invoicing\b",
    r"\bCash Management\b", r"\bSubscription\b",
    r"\bMaster Agreement\b", r"\bMaintenance\b",
    r"\bProduction Order\b", r"\bProcess Order\b",
    r"\bManufacturing Supervisor\b",
    r"\bDecision Table\b",
    r"\bAudit Journal\b",
    r"\bCost Center\b",
    r"\bInternal Order\b", r"\bJournal Entr",
    r"\bProfit Center\b", r"\bActivity Type\b",
    r"\bStatistical Key\b", r"\bDirect Activity\b",
    r"\bPurchase Requisition\b", r"\bPurchase Order\b",
    r"\bService Confirm", r"\bService Contract\b",
    r"\bService Order\b", r"\bIn-House Service\b",
    r"\bEquipment\b",
]

NAVIGATIONAL_PATTERNS = [
    r"\bNavigat", r"\bGo to\b", r"\bOpen App\b", r"\bLaunch\b",
    r"\bUsing Siri\b", r"\bFinding Apps\b",
    r"\bNavigational Capability\b",
    r"\bRequesting Access\b",
]

ANALYTICAL_PATTERNS = [
    r"\bAnalytic", r"\bInsight", r"\bAnomal", r"\bForecast",
    r"\bTrend", r"\bPredict", r"\bOptimiz",
    r"\bAI-Assisted\b", r"\bDetailed Scheduling Optimization\b",
]


def is_good_scraped_data(page_data):
    """Check if scraped data is real content vs sidebar navigation."""
    if not page_data:
        return False
    ucs = page_data.get("useCases", [])
    if not ucs:
        return False
    # False positive: exactly 233 use cases = sidebar nav
    if len(ucs) == 233:
        return False
    # False positive: single use case where prompts start with "What's New"
    if len(ucs) == 1:
        prompts = ucs[0].get("prompts", [])
        if prompts and any("What's New" in p for p in prompts[:3]):
            return False
        # Also check for very high prompt count (likely sidebar)
        if len(prompts) > 30:
            return False
    return True


def extract_prompts_from_scraped(page_data):
    """Extract clean prompts from scraped data."""
    prompts = []
    if not page_data:
        return prompts
    for uc in page_data.get("useCases", []):
        for p in uc.get("prompts", []):
            # Clean up prompt text
            clean = p.strip()
            # Skip sidebar items
            if "What's New" in clean:
                continue
            if len(clean) < 5 or len(clean) > 300:
                continue
            # Skip if it looks like a heading or nav item
            if clean.startswith("20") and "What's New" in clean:
                continue
            prompts.append(clean)
    return prompts


def extract_use_cases_from_scraped(page_data):
    """Extract use case names from scraped data."""
    use_cases = []
    if not page_data:
        return use_cases
    for uc in page_data.get("useCases", []):
        name = uc.get("name", "").strip()
        if name and len(name) > 3 and "What's New" not in name:
            use_cases.append({
                "name": name,
                "prompts": [p.strip() for p in uc.get("prompts", [])
                           if p.strip() and "What's New" not in p and len(p.strip()) > 5],
                "response_summary": uc.get("response", "")[:200],
            })
    return use_cases


def classify_capability(title, is_leaf):
    """Classify a capability by its interaction pattern.

    Returns one of: Informational, Navigational, Transactional, Analytical
    NO Mixed type.
    """
    # "Joule in SAP X" leaf entries → Navigational (product availability)
    if title.startswith("Joule in SAP") and is_leaf:
        return "Navigational"

    # Check patterns in priority order: Analytical > Navigational > Transactional > Informational
    for pattern in ANALYTICAL_PATTERNS:
        if re.search(pattern, title, re.IGNORECASE):
            return "Analytical"

    for pattern in NAVIGATIONAL_PATTERNS:
        if re.search(pattern, title, re.IGNORECASE):
            return "Navigational"

    for pattern in TRANSACTIONAL_PATTERNS:
        if re.search(pattern, title, re.IGNORECASE):
            return "Transactional"

    for pattern in INFORMATIONAL_PATTERNS:
        if re.search(pattern, title, re.IGNORECASE):
            return "Informational"

    # SuccessFactors "Use Cases" pages — determine from title prefix
    if "Use Cases" in title:
        return "Transactional"

    # Remaining unclassified → Transactional (default for business capabilities)
    return "Transactional"


def classify_branch(title, children_types):
    """Classify a branch node based on children.
    Returns the majority type of children.
    """
    # First check if the branch title itself is clearly one type
    if title.startswith("Joule in SAP"):
        pass  # Aggregate from children
    else:
        for pattern in ANALYTICAL_PATTERNS:
            if re.search(pattern, title, re.IGNORECASE):
                return "Analytical"
        for pattern in NAVIGATIONAL_PATTERNS:
            if re.search(pattern, title, re.IGNORECASE):
                return "Navigational"

    if not children_types:
        return classify_capability(title, False)

    # Count types and return majority
    counts = {}
    for t in children_types:
        counts[t] = counts.get(t, 0) + 1

    # If all same type, use that
    if len(counts) == 1:
        return list(counts.keys())[0]

    # Return the most common type
    return max(counts, key=counts.get)


def parse_toc():
    """Parse toc_tree.txt into a flat list with hierarchy."""
    lines = TOC_FILE.read_text().splitlines()
    entries = []
    path_stack = []

    for line in lines:
        if not line.strip():
            continue
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        depth = indent // 2
        title = stripped.strip()

        while len(path_stack) > depth:
            path_stack.pop()
        path_stack.append(title)

        entries.append({
            "title": title,
            "depth": depth,
            "path": list(path_stack),
            "path_str": " > ".join(path_stack),
        })

    return entries


def title_to_slug(title):
    """Convert title to URL slug."""
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug.strip())
    slug = re.sub(r"-+", "-", slug)
    return slug


def get_product(path_str):
    """Determine product from hierarchy path."""
    for key, prod in PRODUCT_MAP.items():
        if key in path_str:
            return prod
    return "Cross-Product"


def enrich():
    """Main enrichment pipeline using scraped data."""
    print("📊 Enriching TOC tree with REAL scraped data (no Mixed type)...")

    # Load scraped data
    scraped = {}
    if SCRAPED_FILE.exists():
        raw = json.loads(SCRAPED_FILE.read_text())
        scraped = raw.get("pages", {})
        print(f"   Loaded scraped data: {len(scraped)} pages")
    else:
        print("   ⚠️  No scraped data found. Run: node pipeline/sources/scrape_help.js")

    entries = parse_toc()

    # Build parent-children relationships
    children_map = {}
    parent_map = {}

    for i, entry in enumerate(entries):
        children_map[i] = []

    for i, entry in enumerate(entries):
        for j in range(i - 1, -1, -1):
            if entries[j]["depth"] == entry["depth"] - 1:
                parent_map[i] = j
                children_map[j].append(i)
                break

    leaf_set = set()
    for i, entry in enumerate(entries):
        if not children_map[i]:
            leaf_set.add(i)

    skip_indices = set()
    for i, entry in enumerate(entries):
        if any(s.lower() in entry["title"].lower() for s in SKIP_TITLES):
            skip_indices.add(i)

    # First pass: classify leaves
    cap_types = {}
    for i in leaf_set:
        if i in skip_indices:
            continue
        cap_types[i] = classify_capability(entries[i]["title"], True)

    # Second pass: classify branches based on children
    for i in sorted(set(range(len(entries))) - leaf_set - skip_indices, reverse=True):
        child_types = [cap_types[c] for c in children_map[i] if c in cap_types]
        cap_types[i] = classify_branch(entries[i]["title"], child_types)

    # Build output
    capabilities = []
    good_scraped = 0
    fallback_count = 0

    for i, entry in enumerate(entries):
        if i in skip_indices:
            continue

        title = entry["title"]
        path = entry["path"]
        path_str = entry["path_str"]
        depth = entry["depth"]
        is_leaf = i in leaf_set
        product = get_product(path_str)

        # Extract business area
        product_depth = None
        for pi, part in enumerate(path):
            if part in PRODUCT_MAP or part.startswith("Joule in SAP") or part.startswith("Analytical Insights"):
                product_depth = pi
                break

        if product_depth is not None:
            remaining = path[product_depth + 1:]
        else:
            remaining = path[1:]

        business_area = ""
        sub_area = ""
        if len(remaining) >= 2:
            business_area = remaining[0]
            if len(remaining) >= 3:
                sub_area = remaining[1]
        elif len(remaining) == 1 and not is_leaf:
            business_area = remaining[0]

        slug = title_to_slug(title)
        cap_type = cap_types.get(i, "Transactional")

        # Get data from scraped content
        page_data = scraped.get(title)
        has_good_data = is_good_scraped_data(page_data)

        use_cases = []
        sample_prompts = []
        description = ""

        if has_good_data:
            good_scraped += 1
            use_cases = extract_use_cases_from_scraped(page_data)
            sample_prompts = extract_prompts_from_scraped(page_data)
            description = (page_data.get("description") or "").strip()
            # Limit to reasonable number of prompts for display
            if len(sample_prompts) > 10:
                sample_prompts = sample_prompts[:10]
        else:
            fallback_count += 1

        cap = {
            "title": title,
            "product": product,
            "business_area": business_area,
            "sub_area": sub_area,
            "capability_type": cap_type,
            "is_leaf": is_leaf,
            "is_branch": not is_leaf and bool(children_map[i]),
            "depth": depth,
            "hierarchy": path_str,
            "slug": slug,
            "sap_help_url": f"https://help.sap.com/docs/joule/capabilities-guide/{slug}",
            "children_count": len(children_map[i]),
            "description": description,
            "use_cases": use_cases,
            "sample_prompts": sample_prompts,
            "data_source": "scraped" if has_good_data else "title-only",
        }
        capabilities.append(cap)

    # Stats
    leaves = [c for c in capabilities if c["is_leaf"]]
    type_counts = {}
    for c in capabilities:
        t = c["capability_type"]
        type_counts[t] = type_counts.get(t, 0) + 1

    product_counts = {}
    for c in capabilities:
        p = c["product"]
        product_counts[p] = product_counts.get(p, 0) + 1

    output = {
        "metadata": {
            "source": "TOC-enriched-v7-scraped",
            "enriched_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "total_entries": len(capabilities),
            "total_leaves": len(leaves),
            "products": len(product_counts),
            "scraped_pages": good_scraped,
            "fallback_pages": fallback_count,
        },
        "capabilities": capabilities,
    }

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"   Total entries: {len(capabilities)}")
    print()
    print("   By capability type (NO Mixed):")
    for t in ["Informational", "Transactional", "Navigational", "Analytical"]:
        if t in type_counts:
            print(f"     {t}: {type_counts[t]}")
    print()
    print("   By product:")
    for p, count in sorted(product_counts.items(), key=lambda x: -x[1]):
        print(f"     {p}: {count}")
    print()
    print(f"   Data sources:")
    print(f"     Scraped (real data): {good_scraped}")
    print(f"     Title-only (no scraped data): {fallback_count}")
    with_prompts = sum(1 for c in capabilities if c.get("sample_prompts"))
    with_use_cases = sum(1 for c in capabilities if c.get("use_cases"))
    print(f"     With sample prompts: {with_prompts}")
    print(f"     With use case details: {with_use_cases}")
    print()
    print(f"   💾 Saved to {OUT_FILE}")


if __name__ == "__main__":
    enrich()