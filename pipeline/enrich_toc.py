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
    "Joule in SAP Ariba Intake Management": "SAP Ariba Solutions",
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
    # False positive: many rows but ALL have empty prompts AND empty response
    # (e.g., Signavio with 59 name-only rows from failed scrape)
    non_empty = sum(
        1 for uc in ucs
        if (uc.get("prompts") or uc.get("response", "").strip())
    )
    if non_empty == 0:
        return False
    return True


def extract_prompts_from_scraped(page_data):
    """Extract clean prompts from scraped data."""
    prompts = []
    if not page_data:
        return prompts
    for uc in page_data.get("useCases", []):
        # Support both 'prompts' and 'samplePrompts' keys
        raw_prompts = uc.get("prompts", []) or uc.get("samplePrompts", [])
        for p in raw_prompts:
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


CAPABILITY_TYPES_SET = {"Informational", "Transactional", "Navigational", "Analytical"}


def _is_misaligned_table(use_cases_raw):
    """Detect pages where column 2 contains capability types instead of prompts.

    Ariba-style tables have columns: Solution | Capability Type | Description
    but the scraper maps them as:       name   | prompts         | response
    """
    if not use_cases_raw:
        return False
    type_count = 0
    name_is_type = 0
    for uc in use_cases_raw:
        prompts = uc.get("prompts", [])
        if prompts and len(prompts) == 1 and prompts[0].strip() in CAPABILITY_TYPES_SET:
            type_count += 1
        name = uc.get("name", "").strip()
        if name in CAPABILITY_TYPES_SET:
            name_is_type += 1
    # If >80% of rows have a single-value prompts that is a type string → misaligned
    if type_count > len(use_cases_raw) * 0.8:
        return True
    # Or if any row's name is literally a capability type → misaligned
    if name_is_type > 0:
        return True
    return False


def _is_category_column_table(use_cases_raw):
    """Detect pages where column 2 has category labels instead of sample prompts.

    SuccessFactors-style tables have columns:
        Use Case | Feature Area | Sample Prompt
    but the scraper maps them as:
        name     | prompts      | response

    Pattern: most rows have prompts that form a short category label
    (1-4 words, no action verb), and the response contains the real prompt.
    Note: the scraper may split multi-word labels like "Rewards and Recognition"
    into multiple array elements ['Rewards and', 'Recognition'].
    """
    if not use_cases_raw or len(use_cases_raw) < 3:
        return False

    category_rows = 0
    prompt_verbs = {
        "show", "display", "create", "get", "search", "find", "list",
        "check", "manage", "open", "delete", "update", "view", "go",
        "approve", "add", "assign", "start", "complete", "navigate",
        "what", "how", "where", "which", "who", "set", "run", "close",
        "cancel", "reverse", "post", "release", "pick", "select",
    }

    for uc in use_cases_raw:
        prompts = uc.get("prompts", [])
        response = (uc.get("response", "") or "").strip()
        if not prompts:
            continue
        # Join all prompt fragments into one label (scraper may split on whitespace)
        label = " ".join(p.strip() for p in prompts).strip()
        words = label.split()
        # Category label: 1-5 words, no action verb, has a response
        if (1 <= len(words) <= 5
                and not any(w.lower() in prompt_verbs for w in words)
                and len(response) > 3):
            category_rows += 1

    # If >70% of rows match the category pattern → category column table
    return category_rows > len(use_cases_raw) * 0.7


# ── Note / Parameter / Prompt classification ─────────────────────

NOTE_STARTS = [
    "You can ", "When the ", "Currently", "Ensure ", "The current ",
    "The date ", "Use the ", "The job ", "New status ", "The confirmation ",
    "Action on ", "Requested data", "Note:", "Important:", "As a workaround",
    "The ", "If the ", "Only ", "This ", "After ", "Before ", "Once ",
    "In case ", "For more ", "Please ", "Make sure ",
]

NOTE_CONTAINS = [
    "is validated", "can only be", "not supported", "as a workaround",
    "is posted after", "are not provided", "should be between",
    "is activated after", "cannot be", "is not available",
]


def _is_note(text):
    """Check if text is a note/instruction rather than an example prompt."""
    t = text.strip()
    # Starts with note patterns
    for start in NOTE_STARTS:
        if t.startswith(start) and len(t) > 40:
            return True
    # Contains explanation language
    t_lower = t.lower()
    for phrase in NOTE_CONTAINS:
        if phrase in t_lower:
            return True
    # Ends with colon → intro sentence
    if t.endswith(":") or t.endswith("attributes:") or t.endswith("attributes."):
        return True
    return False


def _is_parameter(text):
    """Check if text is a parameter/attribute name rather than an example prompt."""
    t = text.strip()
    if not t or len(t) > 80:
        return False
    # Has parenthetical options like "JobSelection (all/my/team/open)"
    if re.match(r'^[A-Z][\w\s]*\(.*\)$', t):
        return True
    # Short text (≤ 3 words) that doesn't start with a prompt verb
    words = t.split()
    if len(words) <= 3 and t[0].isupper():
        prompt_verbs = (
            "Show", "Display", "Create", "Get", "Search", "Find", "List",
            "Check", "Manage", "Open", "Delete", "Update", "Copy", "Recall",
            "Add", "Assign", "Start", "Pause", "Resume", "Complete", "Record",
            "Pick", "Select", "Book", "Filter", "Navigate", "Go", "What",
            "How", "Where", "Which", "Who", "Set", "Run", "View", "Close",
            "Cancel", "Reverse", "Post", "Release", "Approve",
        )
        if not any(t.startswith(v) for v in prompt_verbs):
            return True
    return False


# Regex for splitting concatenated response text into individual prompts
_PROMPT_VERBS_RE = (
    r"(?:Show|Display|Get|Search|Find|List|Check|Create|Manage|Open|Delete|"
    r"Update|Copy|Recall|Add|Assign|Start|Pause|Resume|Complete|Record|"
    r"Pick|Select|Book|Filter|Navigate|Go to|What|How|Where|Which|Who|"
    r"Set |Run |View|Close|Cancel|Reverse|Post|Release|Approve|"
    r"Quick confirm|Retrieve|Send|Make)"
)


# Patterns that indicate a response is a DESCRIPTION of what Joule does,
# not a list of example prompts a user would type
_DESCRIPTION_STARTS = re.compile(
    r'^(?:Joule (?:displays?|shows?|provides?|returns?|lists?|creates?|opens?)|'
    r'Delivers |Provides |Recommends |Available |Supports |Enables |'
    r'Allows |Returns |Generates |Retrieves |Processes |'
    r'This (?:scenario|feature|capability|function)|'
    r'The (?:system|assistant|AI|bot)|'
    r'Based on |Reads? |Uses? |Analyzes? |'
    r'You (?:can|will|may|should)|'
    r'(?:For|In) (?:each|every|all|the) )',
    re.IGNORECASE
)


def _is_response_description(response_text):
    """Check if response text is a description of what Joule does vs example prompts."""
    if not response_text:
        return False
    text = response_text.strip()
    # Check first line
    first_line = text.split("\n")[0].strip()
    if _DESCRIPTION_STARTS.match(first_line):
        return True
    return False


def _split_response_into_prompts(response_text):
    """Split concatenated response text into individual example prompts.

    SAP Help response columns often concatenate example prompts without
    delimiters: "Show my jobsShow team jobs" → ["Show my jobs", "Show team jobs"]

    Returns empty list if the response is a description (not prompts).
    """
    if not response_text or len(response_text.strip()) < 5:
        return []

    text = response_text.strip()

    # Skip description responses — these describe what Joule does, not user prompts
    if _is_response_description(text):
        return []

    # First split on newlines
    parts = text.split("\n")

    prompts = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        # Split on verb boundaries: lowercase/digit followed by uppercase verb
        splits = re.split(
            rf'(?<=[a-z\d\)\.])\s*(?={_PROMPT_VERBS_RE})',
            part
        )
        for s in splits:
            s = s.strip()
            if s and 3 < len(s) < 200:
                prompts.append(s)

    return prompts


def _looks_like_prompt(text):
    """Check if a short text (<15 chars) still looks like a valid prompt."""
    t = text.strip()
    if not t:
        return False
    # Must start with a prompt-style verb or question word
    prompt_starts = (
        "Show", "Display", "Create", "Get", "Search", "Find", "List",
        "Check", "Manage", "Open", "Delete", "Update", "View", "Go",
        "What", "How", "Where", "Which", "Who", "Set", "Run",
    )
    return any(t.startswith(v) for v in prompt_starts)


def _merge_duplicate_use_cases(use_cases):
    """Merge use cases that share the same name into a single grouped entry.

    When scraped tables have one row per prompt (e.g., Concur Expense × 11,
    SuccessFactors Employee Central × 63), this groups them into a single
    use case with all prompts collected together.
    """
    from collections import OrderedDict
    groups = OrderedDict()
    for uc in use_cases:
        name = uc["name"]
        if name not in groups:
            groups[name] = {
                "name": name,
                "description": uc.get("description", ""),
                "notes": list(uc.get("notes", [])),
                "parameters": list(uc.get("parameters", [])),
                "prompts": [],
                "response_summary": uc.get("response_summary", ""),
            }
        # Merge prompts — avoid duplicates
        for p in uc.get("prompts", []):
            if p and p not in groups[name]["prompts"]:
                groups[name]["prompts"].append(p)
        # Merge notes
        for n in uc.get("notes", []):
            if n and n not in groups[name]["notes"]:
                groups[name]["notes"].append(n)
        # Merge parameters
        for p in uc.get("parameters", []):
            if p and p not in groups[name]["parameters"]:
                groups[name]["parameters"].append(p)
        # Keep first non-empty description
        if not groups[name]["description"] and uc.get("description"):
            groups[name]["description"] = uc["description"]

    return list(groups.values())


def extract_use_cases_from_scraped(page_data):
    """Extract use case names from scraped data."""
    use_cases = []
    if not page_data:
        return use_cases

    raw_ucs = page_data.get("useCases", [])

    # ── Handle category-column tables (SuccessFactors style) ─────
    if _is_category_column_table(raw_ucs):
        # Column 2 has category labels, Column 3 has actual prompts
        from collections import OrderedDict
        groups = OrderedDict()  # name → { categories: { label: [prompts] } }
        for uc in raw_ucs:
            name = uc.get("name", "").strip()
            raw_p = uc.get("prompts", [])
            # Join split fragments: ['Rewards and', 'Recognition'] → 'Rewards and Recognition'
            category = " ".join(p.strip() for p in raw_p).strip() if raw_p else ""
            prompt = (uc.get("response", "") or "").strip()
            if not name or not prompt:
                continue
            if name not in groups:
                groups[name] = OrderedDict()
            if category not in groups[name]:
                groups[name][category] = []
            if prompt not in groups[name][category]:
                groups[name][category].append(prompt)

        for name, categories in groups.items():
            all_prompts = []
            subcategories = {}
            for cat, prompts in categories.items():
                if cat:
                    subcategories[cat] = prompts
                all_prompts.extend(prompts)
            use_cases.append({
                "name": name,
                "description": "",
                "notes": [],
                "parameters": [],
                "prompts": all_prompts,
                "subcategories": subcategories if len(subcategories) > 1 else {},
                "response_summary": "",
            })
        return use_cases

    # ── Handle misaligned Ariba-style tables ─────────────────────
    if _is_misaligned_table(raw_ucs):
        # Group rows by sub-product name; response field is the actual use case
        from collections import OrderedDict
        groups = OrderedDict()
        for uc in raw_ucs:
            sub_product = uc.get("name", "").strip().replace("\n", " ")
            # Clean up multi-line names
            sub_product = " ".join(sub_product.split())
            cap_type = (uc.get("prompts", [""])[0] or "").strip()
            description = (uc.get("response", "") or "").strip().replace("\n", " ")
            description = " ".join(description.split())

            if not sub_product or not description:
                continue
            # If "name" is actually a capability type (Intake Management pattern)
            if sub_product in CAPABILITY_TYPES_SET:
                # prompts[0] is the actual use case name, response is description
                actual_name = cap_type  # cap_type here is actually the use case name
                if actual_name and len(actual_name) > 3:
                    use_cases.append({
                        "name": actual_name,
                        "description": description,
                        "prompts": [],
                        "response_summary": description[:200],
                    })
                continue

            if sub_product not in groups:
                groups[sub_product] = {"items": [], "types": set()}
            groups[sub_product]["items"].append(description)
            if cap_type in CAPABILITY_TYPES_SET:
                groups[sub_product]["types"].add(cap_type)

        for sub_product, data in groups.items():
            # Each sub-product becomes a use case with child descriptions
            unique_items = list(dict.fromkeys(data["items"]))  # deduplicate, keep order
            type_str = ", ".join(sorted(data["types"])) if data["types"] else ""
            use_cases.append({
                "name": sub_product,
                "description": type_str,
                "prompts": unique_items,  # actual use case descriptions as "prompts"
                "response_summary": f"{len(unique_items)} capabilities",
            })
        return use_cases

    # ── Standard table parsing with note/parameter separation ────
    for uc in raw_ucs:
        name = uc.get("name", "").strip()
        raw_prompts = uc.get("prompts", []) or uc.get("samplePrompts", [])
        response_text = uc.get("response", "") or ""

        if not name or len(name) <= 3 or "What's New" in name:
            continue

        # Classify each "prompt" item as note, parameter, or real prompt
        notes = []
        parameters = []
        real_prompts = []

        for p in raw_prompts:
            p = p.strip()
            if not p or len(p) <= 5 or "What's New" in p:
                continue
            if _is_note(p):
                notes.append(p)
            elif _is_parameter(p):
                parameters.append(p)
            else:
                real_prompts.append(p)

        # Extract example prompts from response field (often concatenated)
        response_prompts = _split_response_into_prompts(response_text)

        # Decide which prompts to show:
        # Prefer real prompts from the prompts column when they exist;
        # only fall back to response-extracted prompts when there are none
        if real_prompts:
            final_prompts = real_prompts
            # Also add response prompts that aren't duplicates
            for rp in response_prompts:
                if rp not in final_prompts:
                    final_prompts.append(rp)
        elif response_prompts:
            final_prompts = response_prompts
        else:
            final_prompts = []

        # Filter out fragment prompts (too short to be useful)
        final_prompts = [p for p in final_prompts if len(p) >= 15 or _looks_like_prompt(p)]

        use_cases.append({
            "name": name,
            "description": uc.get("description", ""),
            "notes": notes,
            "parameters": parameters,
            "prompts": final_prompts,
            "response_summary": response_text[:200] if not response_prompts else "",
        })

    # ── Global dedup: merge use cases with the same name ─────────
    use_cases = _merge_duplicate_use_cases(use_cases)

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

        # Use actual scraped URL if available, otherwise generate from slug
        scraped_url = page_data.get("url", "") if page_data else ""

        use_cases = []
        sample_prompts = []
        description = ""

        if has_good_data:
            good_scraped += 1
            use_cases = extract_use_cases_from_scraped(page_data)
            description = (page_data.get("description") or "").strip()

            # Prefer prompts from structured use_cases (handles category-column
            # tables and other cases where raw extraction gives bad labels)
            uc_prompts = []
            for uc in use_cases:
                uc_prompts.extend(uc.get("prompts", []))
            if uc_prompts:
                sample_prompts = uc_prompts
            else:
                sample_prompts = extract_prompts_from_scraped(page_data)

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
            "sap_help_url": scraped_url if scraped_url else f"https://help.sap.com/docs/joule/capabilities-guide/{slug}",
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