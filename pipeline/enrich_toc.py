"""Enrich TOC tree into structured Joule capabilities with proper typing.

ALL capabilities here are Joule (Generative AI) — the 'capability_type' describes
the INTERACTION PATTERN: what the user does with it.

Types:
  - Informational: Display, view, search, check, look up data
  - Navigational:  Open apps, go to screens
  - Transactional: Create, change, manage, process business documents
  - Analytical:    Insights, forecasts, anomaly detection, analytics
  - Mixed:         Capabilities with both informational and transactional use cases

Usage:
    python3 -m pipeline.enrich_toc
"""

import json
import re
import time
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
TOC_FILE = WORKSPACE / "pipeline" / "sources" / "toc_tree.txt"
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
# Order matters — first match wins for single-type classification
INFORMATIONAL_PATTERNS = [
    r"\bDisplay\b", r"\bShow\b", r"\bView\b", r"\bSearch\b", r"\bList\b",
    r"\bCheck\b", r"\bGet\b", r"\bLook\s?up\b", r"\bFind\b", r"\bRetrieve\b",
    r"\bDisplaying\b", r"\bSearching\b", r"\bAvailability\b",
    r"\bError Explanation\b", r"\bError Summary\b", r"\bError Explanations\b",
    r"\bSummary\b", r"\bOverview\b", r"\bStatus\b", r"\bBalance\b",
    r"\bLine Items\b", r"\bDocument Flow\b", r"\bPositions?\b",
    r"\bCommitment\b",
]

TRANSACTIONAL_PATTERNS = [
    r"\bCreate\b", r"\bManage\b", r"\bProcess\b", r"\bExecute\b", r"\bPost\b",
    r"\bRelease\b", r"\bClearing\b", r"\bApprove\b", r"\bChange\b", r"\bEdit\b",
    r"\bUpdate\b", r"\bDelete\b", r"\bCancel\b", r"\bReverse\b", r"\bAssign\b",
    r"\bReassign\b", r"\bTransfer\b", r"\bConvert\b", r"\bClose\b",
    r"\bCreation\b", r"\bBudgeting\b", r"\bReminders?\b",
    r"\bRecurring\b", r"\bTemplates?\b",
]

NAVIGATIONAL_PATTERNS = [
    r"\bNavigate\b", r"\bGo to\b", r"\bOpen App\b", r"\bLaunch\b",
    r"\bUsing Siri\b",
]

ANALYTICAL_PATTERNS = [
    r"\bAnalytic", r"\bInsight", r"\bAnomal", r"\bForecast",
    r"\bTrend", r"\bPredict", r"\bOptimiz",
]

# ── Items that have BOTH informational and transactional use cases ──
# These are capability pages where Joule can both display AND create/change
MIXED_CAPABILITIES = {
    "Billing Request",
    "Invoicing Document",
    "Contract Accounting",
    "Clarification Case",
    "Convergent Invoicing",
    "Dispute Resolution",
    "Payment Resolution",
    "Billing Plan",
    "Cash Management",
    "Subscription Order",
    "Subscription Contract",
    "Master Agreement",
    "Production Order",
    "Manufacturing Supervisor",
    "Enterprise Portfolio and Project Management",
    "Products, Resources, and Receipts in Production Planning and Detailed Scheduling",
    "Audit Journal",
}

# ── Curated sample prompts ───────────────────────────────────────
SAMPLE_PROMPTS = {
    # Business Partners
    "Display Business Partners": [
        "Show me Business Partner 17100010",
        "Display overview of Business Partner 17100010",
        "Show me the addresses for Business Partner 17100010",
    ],
    "Edit Business Partners": [
        "Change the phone number for Business Partner 17100010",
        "Update the address for Business Partner 17100010",
    ],
    # Finance
    "Display G/L Account Balance": [
        "Show me the balance for G/L account 100000",
        "Display G/L account balance for company code 1000",
    ],
    "Display G/L Account Line Items - General Ledger View": [
        "Show me G/L account line items for account 100000",
    ],
    "Display Journal Entries in T-Accounting View": [
        "Show journal entry 100000001 in T-account view",
    ],
    "Manage Journal Entries": [
        "Create a journal entry for company code 1000",
        "Post a journal entry to G/L account 400000",
    ],
    "Manage Cost Center": [
        "Create a new cost center in controlling area 0001",
        "Update cost center 10001",
    ],
    "Clearing Single G/L Open Item": [
        "Clear open items for G/L account 113100",
    ],
    "Manage Accounts Receivable": [
        "Show open receivables for customer 17100001",
    ],
    "Audit Journal": [
        "Show me the audit journal for today",
        "Display audit trail for user SMITH",
    ],
    "Cost Center Budgeting": [
        "Set budget for cost center 10001 to $500,000",
        "Display budget for cost center 10001",
    ],
    # Sales
    "Display Sales Order": [
        "Show me sales order 1000001",
        "Display details of sales order 1000001",
    ],
    "Create Sales Order": [
        "Create a sales order for customer 17100001",
        "Create a standard sales order with material M-01",
    ],
    "Display Sales Quotation": [
        "Show me quotation 20000001",
    ],
    "Create Sales Quotation": [
        "Create a quotation for customer 17100001",
    ],
    "Display Billing Document": [
        "Show billing document 90000001",
    ],
    # Billing & Revenue
    "Billing Request": [
        "Show me billing request 700000001",
        "Create a new billing request",
        "Display billing requests for account 100001",
    ],
    "Invoicing Document": [
        "Display invoicing document 800000001",
        "Create an invoicing document",
    ],
    "Clarification Case": [
        "Show clarification case 300000001",
        "Create a clarification case for account 100001",
    ],
    "Dispute Resolution": [
        "Display dispute case 400000001",
        "Create a dispute case",
    ],
    # Warehouse
    "Searching for Outbound Delivery Orders": [
        "Search for outbound delivery orders for warehouse 1000",
        "Find delivery orders shipped today",
    ],
    # Cash
    "Displaying Cash Positions": [
        "Show me cash positions for company code 1000",
        "Display today's cash position",
    ],
    "Cash Management": [
        "Show cash management overview for company code 1000",
        "Display liquidity forecast",
    ],
    # Service
    "Display Service Order": [
        "Show me service order 4000001",
    ],
    "Create Service Order": [
        "Create a service order for equipment 10000001",
    ],
    # Procurement
    "Display Purchase Order": [
        "Show purchase order 4500000001",
    ],
    "Create Purchase Order": [
        "Create a purchase order for vendor 1000001",
    ],
    # Asset Management
    "Display Fixed Asset": [
        "Show me fixed asset 100000-0",
    ],
    "Create Fixed Asset": [
        "Create a fixed asset in company code 1000",
    ],
    # SuccessFactors
    "Compensation Use Cases": [
        "What is my current salary?",
        "Show me my compensation history",
    ],
    "Employee Central Use Cases": [
        "Show me my team members",
        "Who is my manager?",
        "What are my direct reports?",
    ],
    "Learning Use Cases": [
        "Find training courses on leadership",
        "Show my learning assignments",
    ],
    "Recruiting Use Cases": [
        "Show open positions in my department",
        "What's the status of requisition 12345?",
    ],
    "Time Tracking Use Cases": [
        "Clock in for today",
        "Show my time sheet for this week",
    ],
    "Performance & Goals Use Cases": [
        "Show my performance goals",
        "What are my objectives for this quarter?",
    ],
    # SAC
    "Analytical Insights with SAP Analytics Cloud": [
        "Show me revenue trends for Q1",
        "Analyze cost center spending anomalies",
    ],
    # EWM
    "Display Warehouse Task": [
        "Show warehouse task 100000001",
    ],
    "Display Physical Inventory Document": [
        "Show physical inventory document 100000001",
    ],
}


def classify_capability(title, is_leaf, children_types=None):
    """Classify a capability by its interaction pattern.
    
    Returns one of: Informational, Navigational, Transactional, Analytical, Mixed
    """
    # Check mixed list first
    if title in MIXED_CAPABILITIES:
        return "Mixed"
    
    # Check patterns
    for pattern in NAVIGATIONAL_PATTERNS:
        if re.search(pattern, title, re.IGNORECASE):
            return "Navigational"
    
    for pattern in ANALYTICAL_PATTERNS:
        if re.search(pattern, title, re.IGNORECASE):
            return "Analytical"
    
    for pattern in INFORMATIONAL_PATTERNS:
        if re.search(pattern, title, re.IGNORECASE):
            return "Informational"
    
    for pattern in TRANSACTIONAL_PATTERNS:
        if re.search(pattern, title, re.IGNORECASE):
            return "Transactional"
    
    # For branch nodes, aggregate children types
    if children_types:
        unique = set(children_types)
        if len(unique) == 1:
            return list(unique)[0]
        elif "Informational" in unique and "Transactional" in unique:
            return "Mixed"
        elif unique:
            return list(unique)[0]
    
    # SuccessFactors "Use Cases" pages → Mixed (they contain both info + transactional)
    if "Use Cases" in title:
        return "Mixed"
    
    # Product overview pages like "Joule in SAP X" → Mixed
    if title.startswith("Joule in SAP"):
        return "Mixed"
    
    # Default for remaining unclassified leaves → Mixed
    if is_leaf:
        return "Mixed"
    
    return "Mixed"


def parse_toc():
    """Parse toc_tree.txt into a flat list with hierarchy."""
    lines = TOC_FILE.read_text().splitlines()
    entries = []
    path_stack = []
    
    for line in lines:
        if not line.strip():
            continue
        # Count indentation (2 spaces per level)
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        depth = indent // 2
        title = stripped.strip()
        
        # Maintain path stack
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
    """Main enrichment pipeline."""
    print("📊 Enriching TOC tree with proper capability types...")
    entries = parse_toc()
    
    # Build parent-children relationships
    children_map = {}  # index → list of child indices
    parent_map = {}    # index → parent index
    
    for i, entry in enumerate(entries):
        children_map[i] = []
    
    for i, entry in enumerate(entries):
        # Find parent: nearest previous entry at depth-1
        for j in range(i - 1, -1, -1):
            if entries[j]["depth"] == entry["depth"] - 1:
                parent_map[i] = j
                children_map[j].append(i)
                break
    
    # Determine which entries are leaves
    leaf_set = set()
    for i, entry in enumerate(entries):
        if not children_map[i]:
            leaf_set.add(i)
    
    # Skip filtered entries
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
        cap_types[i] = classify_capability(entries[i]["title"], False, child_types)
    
    # Build output capabilities
    capabilities = []
    for i, entry in enumerate(entries):
        if i in skip_indices:
            continue
        
        title = entry["title"]
        path = entry["path"]
        path_str = entry["path_str"]
        depth = entry["depth"]
        is_leaf = i in leaf_set
        product = get_product(path_str)
        
        # Extract business area and sub-area
        # Path: [Product, BusinessArea, SubArea?, ..., Title]
        # For product-level entries, business_area might be the title itself
        product_depth = None
        for pi, part in enumerate(path):
            if part in PRODUCT_MAP or part.startswith("Joule in SAP") or part.startswith("Analytical Insights"):
                product_depth = pi
                break
        
        if product_depth is not None:
            remaining = path[product_depth + 1:]
        else:
            remaining = path[1:]  # Skip root
        
        business_area = ""
        sub_area = ""
        if len(remaining) >= 2:
            business_area = remaining[0]
            if len(remaining) >= 3:
                sub_area = remaining[1]
        elif len(remaining) == 1 and not is_leaf:
            business_area = remaining[0]
        
        slug = title_to_slug(title)
        cap_type = cap_types.get(i, "Mixed")
        
        # Get sample prompts if available
        prompts = SAMPLE_PROMPTS.get(title, [])
        
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
            "sample_prompts": prompts,
        }
        capabilities.append(cap)
    
    # Add SAC integration note as a special capability
    capabilities.append({
        "title": "Joule + SAP Analytics Cloud Integration",
        "product": "SAP Analytics Cloud",
        "business_area": "Analytics",
        "sub_area": "",
        "capability_type": "Analytical",
        "is_leaf": True,
        "is_branch": False,
        "depth": 1,
        "hierarchy": "Analytical Insights with SAP Analytics Cloud > Joule + SAC Integration",
        "slug": "joule-sac-integration",
        "sap_help_url": "",
        "children_count": 0,
        "sample_prompts": [
            "Show me revenue trends for Q1",
            "Analyze cost center spending anomalies",
            "What are the top performing products this quarter?",
        ],
        "special_note": "Coming soon: Enhanced analytics capabilities when Joule is connected to SAP Analytics Cloud. This integration will unlock conversational data exploration, natural language queries on your live data, and AI-generated insights across all SAP data sources.",
    })
    
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
            "source": "TOC-enriched-v4",
            "enriched_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "total_entries": len(capabilities),
            "total_leaves": len(leaves),
            "products": len(product_counts),
        },
        "capabilities": capabilities,
    }
    
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"   Total entries: {len(capabilities)}")
    print()
    print("   By capability type:")
    for t in ["Informational", "Transactional", "Navigational", "Analytical", "Mixed"]:
        if t in type_counts:
            print(f"     {t}: {type_counts[t]}")
    print()
    print("   By product:")
    for p, count in sorted(product_counts.items(), key=lambda x: -x[1]):
        print(f"     {p}: {count}")
    print()
    print(f"   Leaves: {len(leaves)}, Branches: {len(capabilities) - len(leaves)}")
    print(f"   Capabilities with sample prompts: {sum(1 for c in capabilities if c.get('sample_prompts'))}")
    print()
    print(f"   💾 Saved to {OUT_FILE}")


if __name__ == "__main__":
    enrich()