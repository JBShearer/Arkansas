#!/usr/bin/env python3
"""
Data quality cleaner for Joule capabilities data.
Fixes:
1. Notes/descriptions that ended up in prompts arrays
2. Prompts that are actually notes (move to notes)
3. Notes that are actually prompts (move to prompts)
4. Capability type corrections based on heuristics
5. Sports One / Concur descriptive text in prompts
6. Technical-ID UC names and SAP_TC_ prompts (drop entire UC rows)
7. Garbled multi-line UC names (strip at first newline, extract embedded notes)
8. App names misclassified as prompts in Navigational capabilities
9. Fiori intent strings and OData service names in parameters (drop)
10. Siri phrases misplaced in parameters for SuccessFactors Siri UCs
11. Signavio fragment prompts (rejoin consecutive fragments)
12. Cap-level type correction by UC consensus and title heuristics
"""

import json
import re
import sys
from pathlib import Path

# --- Patterns that indicate a "prompt" is actually a note/description ---
NOT_A_PROMPT_PATTERNS = [
    r'^Joule displays',
    r'^Joule checks',
    r'^Joule prompts',
    r'^Joule provides',
    r'^Joule creates',
    r'^Joule retrieves',
    r'^Joule informs',
    r'^Joule can ',
    r'^Joule guides',
    r'^Joule uses',
    r'^Joule automatically',
    r'^Joule enables',
    r'^Joule triggers',
    r'^You can ',
    r'^You must ',
    r'^You will ',
    r'^You are required',
    r'^You need to',
    r'^You use ',
    r'^Reading through',
    r'^The system performs',
    r'^The search results',
    r'^The display results',
    r'^The processing of',
    r'^Currently,',
    r'^Provide all the required',
    r'^Provide the following',
    r'^If you ',
    r'^If the ',
    r'^If no ',
    r'^If decision table',
    r'^When you ',
    r'^Once you ',
    r'^Specify if',
    r'^Please note',
    r'^For each ',
    r'^For posting',
    r'^For this request',
    r'^Additionally,',
    r'^Ensure that',
    r'^We recommend',
    r'^Clicking on this option',
    r'^This can be done',
    r'^This will navigate',
    r'^This feature will',
    r'^Use the format',
    r'^Use of this AI',
    r'^Reselect:',
    r'^Confirm ',
    r'^Recommendation$',
    r'^Creation of ',
    r'^Start a new chat',
    r'^Before proceeding',
    r'^In some cases',
    r'^SAP delivers',
    r'^Open the \w',           # UI navigation step: "Open the Asset Overview app"
    r'^Open Joule',            # Meta-instruction
    r'^Choose \w',             # UI action: "Choose Confirm to..."
    r'^Enter the ',            # Form field instruction
    r'^As a result',           # System response description
    r'^User views ',           # Concur-style "User X" descriptions
    r'^User searches',
    r'^User recalls',
    r'^User can ',
    r'^User selects',
    r'^User adds',
    r'^User filters',
    r'Navigates to \w+ app',   # Button label + nav description (DSO)
    r'Provides a multilevel',  # Feature label + description (DSO)
    r'^Order Details:',        # Feature label (DSO)
    r'^Explain:',              # Feature label (DSO)
    r'^Process Order: Navigates',  # Button label (DSO)
    r'^InHouseRepair-',        # Technical Fiori intent string in prompts
    r'^RepairObject-',
    r'^Ask Joule which',       # Meta-instruction
    r'^Ask for example\s*:?\s*$',
    r'^For example\s*:?\s*$',
]

# Patterns that indicate it's a field/column label, not a prompt
FIELD_LABEL_PATTERNS = [
    r'^Full Name Business Partner ID$',
    r'^Address \(country',
    r'^(Header|Main View|Detailed View|Standard Card)$',
    r'^(Ledger GL Line Item)$',
    r'^(Sales Order (Header|Item))$',
    r'^(Billing Document (Header|Item))$',
    r'^(Process order|Production order) (planned )?start date$',
    r'^(Process order|Production order) sub operation$',
    r'^(Process order|Production order) (planned start date|item planned)',
    r'^Amount in (Display|Transaction) Currency$',
    r'^Open Amount$',
    r'^(Payment Card ID and Type)$',
    r'^(Contact Person Business Partner)$',
    r'^(Contact Person Full Name)$',
    r'^(Business Partner Name and ID)$',
    r'^(International Bank Account Number)$',
    r'^(Post Office Postal Code)$',
    r'^(Ship-to Party Partner Function)$',
    r'^(Item earliest requested delivery date)$',
    r'^(Billing Request Total Amount)$',
    r'^Open in App button\.$',
    r'^(Bank ID for Incoming Payments)$',
    r'^(Payment Method for Incoming Payment)$',
    r'^(Payment Card ID for Incoming Payment)$',
    r'^Goods\.$',
    r'^(Partially confirmed, in process, running or started)$',
    r'^(Quantity deviations such as)',
    r'^(Calculation Schema Group Code)$',
    r'^(Supplier posting status information)$',
    r'^(Posting block status details)$',
    r'^(Customer posting status information)$',
]

# Notes that are actually prompts
NOTE_IS_PROMPT_PATTERNS = [
    r'^For the BP \d+',
    r'^Show me ',
    r'^Display ',
    r'^Search ',
    r'^Create ',
    r'^Change ',
    r'^Update ',
]

# Descriptive text in Sports One and similar
DESCRIPTIVE_PROMPT_PATTERNS = [
    r'can be time-consuming\. Let Joule help',
    r'key details can be time-consuming',
]

# Technical ID patterns: OData service names, Fiori intent strings, SAP_TC_ auth codes,
# ABAP program names, internal AI IDs — none of these are user-facing prompts or parameters.
TECHNICAL_ID_RE = re.compile(
    r'^SAP_TC_[A-Z_]+$'           # Auth scope codes
    r'|^SD_INT_AI'                 # AI integration IDs
    r'|^SAP_INT_'                  # SAP internal integration IDs
    r'|^[A-Z][A-Z0-9_]{4,}/[A-Z]' # OData service paths
    r'|^API_[A-Z0-9_]+_SRV$'      # OData service names (API_*)
    r'|^[A-Z]{2,}_[A-Z0-9_]{4,}$' # ABAP/Fiori tech IDs (all-caps with underscore)
    r'|^[a-z][a-z0-9_]+_[a-z0-9_]+$'  # lowercase OData service names
    r'|^ui_[a-z]'                  # lowercase Fiori app IDs
    r'|^\d{4}(\s+SP\d+)*$'        # Release year / SP version rows
    r'|^SD_INT_AI_GEMINI'
    r'|^SD_INT_AI_GPT'
)

# Fiori intent strings in parameters: "SomeObject-someAction" pattern
FIORI_INTENT_RE = re.compile(r'^[A-Za-z][A-Za-z0-9]+(-[A-Za-z][A-Za-z0-9]+)+$')


def is_technical_id(text: str) -> bool:
    """Return True if text is an internal technical identifier, not user-facing content."""
    return bool(TECHNICAL_ID_RE.match(text.strip()))


def is_fiori_intent(text: str) -> bool:
    """Return True if text looks like a Fiori semantic object-action intent string."""
    return bool(FIORI_INTENT_RE.match(text.strip()))


def is_technical_uc(uc: dict) -> bool:
    """Return True if this entire UC is a metadata/technical row, not a real use case.

    Indicators: name is a technical ID, OR the only prompt is a SAP_TC_ code.
    These rows come from SAP Help prerequisite tables scraped into use_cases.
    """
    name = uc.get('name', '').strip()
    if is_technical_id(name):
        return True
    prompts = uc.get('prompts', [])
    if len(prompts) == 1 and is_technical_id(prompts[0]):
        return True
    return False


def clean_uc_name(name: str) -> tuple[str, list[str]]:
    """Clean a garbled UC name, returning (clean_name, extracted_notes).

    Handles:
    - Multi-line names: strip at first blank line (keep only first paragraph)
    - Embedded "Note\\n\\nAlways start from here." patterns: extract to notes
    - Trailing colon-separated lists (service order filter values): strip list
    - Step-by-step instructions after colon: strip, keep only the action phrase
    """
    extracted_notes = []

    # Split on double newline (paragraph break) — keep only first paragraph as name
    paragraphs = re.split(r'\n\s*\n', name)
    clean = paragraphs[0].strip()

    # If there are more paragraphs, check if they look like embedded notes
    for para in paragraphs[1:]:
        para = para.strip()
        if not para:
            continue
        # "Note\n\nAlways start from here." pattern
        if re.match(r'^Note\s*$', para, re.IGNORECASE):
            continue  # The next para will be the actual note text
        # Looks like a note/instruction
        if re.match(r'^(Note:|Always |Ensure |If |You |The )', para, re.IGNORECASE):
            extracted_notes.append(para)
        # Otherwise just discard (it's structural text)

    # Strip trailing colon-list (filter values lists like "Status:\n\nOpen\n\nIn Process")
    # — these become the name itself if on one line, e.g. "Status:\nOpen\nIn Process"
    clean = re.sub(r'\n.+', '', clean).strip()

    # Strip trailing colon (e.g. "Renew expiring prices:")
    clean = clean.rstrip(':').strip()

    # If the name after cleaning is empty, use the original first non-empty line
    if not clean:
        clean = name.split('\n')[0].strip().rstrip(':')

    return clean, extracted_notes


def is_not_a_prompt(text: str) -> bool:
    """Check if text looks like a note/description rather than a prompt."""
    for pattern in NOT_A_PROMPT_PATTERNS:
        if re.match(pattern, text, re.IGNORECASE):
            return True
    for pattern in FIELD_LABEL_PATTERNS:
        if re.match(pattern, text, re.IGNORECASE):
            return True
    for pattern in DESCRIPTIVE_PROMPT_PATTERNS:
        if re.search(pattern, text):
            return True
    return False


def is_note_actually_prompt(text: str) -> bool:
    """Check if a note looks like it should be a prompt."""
    for pattern in NOTE_IS_PROMPT_PATTERNS:
        if re.match(pattern, text.strip()):
            return True
    return False


def is_app_name(text: str) -> bool:
    """Return True if text looks like a Fiori app name rather than a user prompt.

    App names are short, title-cased, contain no question mark, and start with
    a capitalised noun or verb-as-noun (e.g. "Manage Purchase Orders").
    They never start with a lowercase word or a pronoun like "Show", "Where", "Which".
    """
    t = text.strip()
    if not t or '?' in t or len(t) > 80:
        return False
    if not t[0].isupper():
        return False
    prompt_starters = {
        'show', 'display', 'find', 'search', 'get', 'list', 'fetch',
        'create', 'change', 'update', 'delete', 'post', 'cancel',
        'where', 'which', 'what', 'how', 'who', 'when', 'why',
        'i', 'help', 'open', 'navigate', 'go',
    }
    first_word = re.split(r'\s+', t)[0].rstrip('.,').lower()
    if first_word in prompt_starters:
        return False
    words = re.split(r'\s+', t)
    short_words = {'a', 'an', 'the', 'of', 'for', 'in', 'to', 'and', 'or', 'by', 'with', 'on', 'at'}
    cap_words = [w for w in words if w not in short_words]
    if not cap_words:
        return False
    frac = sum(1 for w in cap_words if w and w[0].isupper()) / len(cap_words)
    return frac >= 0.75


def rejoin_signavio_fragments(prompts: list) -> list:
    """Rejoin Signavio prompt fragments split across list entries by the scraper.

    A fragment is detected when an entry starts with a lowercase letter, a
    closing quote, or is very short (≤3 words) and the previous entry doesn't
    end with sentence-terminating punctuation.
    """
    if not prompts:
        return prompts
    result = [prompts[0]]
    for p in prompts[1:]:
        prev = result[-1]
        # Join if this entry starts lowercase, or starts with a quote fragment,
        # or is very short and prev doesn't end with sentence punctuation
        starts_lower = p and p[0].islower()
        starts_quote_frag = p.startswith('"') and not p.endswith('"')
        is_short_fragment = len(p.split()) <= 2 and not re.search(r'[.?!]$', prev)
        if starts_lower or starts_quote_frag or is_short_fragment:
            result[-1] = prev.rstrip() + ' ' + p.lstrip()
        else:
            result.append(p)
    return result


def clean_parameters(params: list, parent_type: str = None) -> list:
    """Remove technical IDs, Fiori intent strings, and type labels from parameters."""
    clean = []
    for p in params:
        p = p.strip()
        if not p:
            continue
        # Drop internal technical IDs
        if is_technical_id(p):
            continue
        # Drop Fiori semantic object-action intent strings
        if is_fiori_intent(p):
            continue
        # Drop the word "Transactional" / "Informational" etc. appearing as a param value
        if p in {'Transactional', 'Informational', 'Navigational', 'Analytical'}:
            continue
        # Drop sentence fragments ending with a stray quote
        if p.endswith('"') and p.count('"') == 1:
            continue
        clean.append(p)
    return clean


def infer_uc_type(uc: dict, parent_type: str = None) -> str:
    """Infer capability_type for a single use case based on its name and prompts.

    If the parent capability is Navigational, the UC inherits that type directly —
    the heuristics should not override a known-good parent classification.
    """
    if parent_type == 'Navigational':
        return 'Navigational'

    name = uc.get('name', '').lower()
    prompts = uc.get('prompts', [])
    prompt_text = ' '.join(prompts).lower()
    name_words = set(re.split(r'[\s\-/,.()\[\]]+', name))

    nav_keywords = {'navigate', 'launch', 'open'}
    nav_phrases = ['finding apps', 'go to']
    if name_words & nav_keywords or any(k in name for k in nav_phrases):
        return 'Navigational'

    anal_keywords = {'analytical', 'insights', 'analytics', 'analysis'}
    if name_words & anal_keywords or 'report' in name:
        return 'Analytical'

    info_words = {'display', 'view', 'show', 'fetch', 'search', 'list', 'get', 'find',
                  'summarize', 'summarise', 'read', 'check', 'query', 'retrieve', 'summarizing'}
    trans_words = {'create', 'change', 'edit', 'update', 'delete', 'manage', 'post', 'clear',
                   'assign', 'complete', 'cancel', 'reject', 'release', 'approve', 'perform',
                   'process', 'submit', 'resubmit', 'execute', 'add', 'remove', 'set', 'send', 'generate',
                   'schedule', 'confirm', 'activate', 'deploy', 'transfer', 'modify', 'close',
                   'open', 'resolve', 'handle', 'apply', 'save', 'publish', 'lock', 'unlock',
                   'renew', 'reopen', 'release', 'attach', 'detach', 'promote', 'run'}

    name_is_info = bool(name_words & info_words)
    name_is_trans = bool(name_words & trans_words)

    if name_is_info and not name_is_trans:
        return 'Informational'
    if name_is_trans and not name_is_info:
        return 'Transactional'

    trans_prompt_verbs = {'create', 'submit', 'change', 'update', 'delete', 'approve', 'reject',
                          'process', 'post', 'log', 'assign', 'complete', 'release', 'cancel',
                          'close', 'add', 'remove', 'set', 'send', 'generate', 'schedule', 'save'}
    info_prompt_verbs = {'show', 'display', 'list', 'get', 'find', 'search', 'view', 'fetch',
                         'what', 'how', 'give', 'tell', 'summarize', 'summarise', 'explain',
                         'retrieve', 'where', 'which'}
    first_word = prompt_text.split()[0].rstrip('?.,') if prompt_text.strip() else ''
    if first_word in trans_prompt_verbs:
        return 'Transactional'
    if first_word in info_prompt_verbs:
        return 'Informational'

    return 'Informational'  # safe default


def infer_capability_type(cap: dict) -> str:
    """Improve capability_type based on title, UC consensus, and content heuristics."""
    title = cap.get('title', '').lower()
    use_cases = cap.get('use_cases', [])

    # Hard title-based overrides
    nav_title_kw = ['finding apps', 'go to', 'navigate', 'launch', 'navigating to']
    if any(k in title for k in nav_title_kw):
        return 'Navigational'

    anal_title_kw = ['analytical', 'insights', 'analytics', 'analysis', 'detailed scheduling']
    if any(k in title for k in anal_title_kw):
        return 'Analytical'

    # Informational title indicators (display/view/show/search/retrieve — no write verbs)
    info_title_kw = ['display', 'view', 'show', 'fetch', 'search', 'informational',
                     'retrieval of', 'summarizing']
    trans_title_kw = ['create', 'change', 'edit', 'update', 'delete', 'manage', 'mass change',
                      'post', 'clear', 'assign', 'complete', 'cancel', 'reject', 'release',
                      'renew', 'perform', 'processing', 'executing']

    title_is_info = any(k in title for k in info_title_kw)
    title_is_trans = any(k in title for k in trans_title_kw)

    if title_is_info and not title_is_trans:
        return 'Informational'

    # UC consensus: if ALL UCs agree on a type, trust that over the title
    if use_cases:
        uc_types = [uc.get('capability_type') for uc in use_cases if uc.get('capability_type')]
        if uc_types:
            type_counts = {}
            for t in uc_types:
                type_counts[t] = type_counts.get(t, 0) + 1
            dominant = max(type_counts, key=type_counts.get)
            dominant_frac = type_counts[dominant] / len(uc_types)
            # If ≥80% of UCs agree, override the cap type with the consensus
            if dominant_frac >= 0.80:
                return dominant

    if title_is_trans:
        return 'Transactional'

    all_prompts = []
    for uc in use_cases:
        all_prompts.extend(uc.get('prompts', []))
    uc_names = ' '.join(uc.get('name', '') for uc in use_cases).lower()

    has_info = any(k in uc_names for k in ['display', 'view', 'show', 'fetch', 'search', 'retrieve'])
    has_trans = any(k in uc_names for k in ['create', 'change', 'edit', 'update', 'delete',
                                              'complete', 'cancel', 'reject', 'renew', 'release'])
    trans_prompt_verbs = ['create', 'submit', 'change', 'update', 'delete', 'approve', 'reject',
                          'process', 'post', 'log', 'assign', 'complete', 'release', 'cancel', 'close']
    has_trans_prompts = any(any(v in p.lower() for v in trans_prompt_verbs) for p in all_prompts)

    if has_info and has_trans:
        return 'Transactional' if has_trans_prompts else 'Informational'
    if has_info and not has_trans:
        return 'Informational'
    if has_trans:
        return 'Transactional'

    existing = cap.get('capability_type', 'Informational')
    if existing == 'Mixed':
        return 'Transactional' if has_trans_prompts else 'Informational'
    return existing


def clean_use_case(uc: dict, parent_type: str = None, is_signavio: bool = False) -> dict:
    """Clean a single use case: fix prompts vs notes, clean parameters."""
    prompts = uc.get('prompts', [])
    notes = uc.get('notes', [])

    # Rejoin Signavio fragment prompts before other processing
    if is_signavio:
        prompts = rejoin_signavio_fragments(prompts)

    clean_prompts = []
    new_notes = list(notes)

    for p in prompts:
        p = p.strip()
        if not p:
            continue
        # Drop SAP internal technical codes entirely
        if is_technical_id(p):
            continue
        # Strip " Joule provides/explains/..." appended after the user question
        m = re.match(r'^(.+?\?)\s+Joule\b.+', p, re.DOTALL)
        if m:
            p = m.group(1).strip()
        if is_not_a_prompt(p):
            new_notes.append(p)
        elif parent_type == 'Navigational' and is_app_name(p):
            existing_params = uc.setdefault('parameters', [])
            if p not in existing_params:
                existing_params.append(p)
        else:
            clean_prompts.append(p)

    # Check if any notes are actually prompts
    remaining_notes = []
    for n in new_notes:
        n = n.strip()
        if not n:
            continue
        # Drop field labels that ended up in notes
        if is_not_a_prompt(n) and any(re.match(pat, n, re.IGNORECASE) for pat in FIELD_LABEL_PATTERNS):
            continue
        if is_note_actually_prompt(n):
            clean_prompts.append(n)
        else:
            remaining_notes.append(n)

    uc['prompts'] = clean_prompts
    uc['notes'] = remaining_notes

    # Clean parameters
    uc['parameters'] = clean_parameters(uc.get('parameters', []), parent_type)

    # For "Using Siri to Launch Joule" UCs: Siri phrases belong in prompts not parameters
    uc_name = uc.get('name', '')
    if not clean_prompts and uc.get('parameters'):
        # If there are no prompts but parameters look like voice phrases (contain spaces, not tech IDs)
        # and the UC name is a language name, move them to prompts
        lang_name_re = re.compile(
            r'^(English|German|French|Spanish|Bulgarian|Catalan|Estonian|Finnish|'
            r'Welsh|Montenegrin|Arabic|Chinese|Japanese|Korean|Portuguese|Dutch|'
            r'Italian|Norwegian|Swedish|Danish|Polish|Czech|Hungarian|Romanian|'
            r'Croatian|Slovak|Slovenian|Turkish|Hebrew|Thai|Vietnamese|Indonesian|'
            r'Malay|Greek|Ukrainian|Russian|Serbian)\b',
            re.IGNORECASE
        )
        if lang_name_re.match(uc_name):
            voice_phrases = [p for p in uc['parameters'] if ' ' in p and not is_technical_id(p)]
            if voice_phrases:
                uc['prompts'] = voice_phrases
                uc['parameters'] = [p for p in uc['parameters'] if p not in voice_phrases]

    uc['capability_type'] = infer_uc_type(uc, parent_type=parent_type)
    return uc


def clean_capability(cap: dict) -> dict:
    """Clean a single capability entry."""
    parent_type = cap.get('capability_type')
    is_signavio = 'signavio' in cap.get('product', '').lower()

    # Clean UC names and filter out technical-ID rows
    clean_ucs = []
    for uc in cap.get('use_cases', []):
        if is_technical_uc(uc):
            continue
        # Clean the UC name
        raw_name = uc.get('name', '')
        if '\n' in raw_name:
            clean_name, extracted_notes = clean_uc_name(raw_name)
            uc['name'] = clean_name
            uc['notes'] = list(uc.get('notes', [])) + extracted_notes
        clean_use_case(uc, parent_type=parent_type, is_signavio=is_signavio)
        clean_ucs.append(uc)

    cap['use_cases'] = clean_ucs

    # Rebuild sample_prompts
    all_prompts = []
    for uc in cap['use_cases']:
        all_prompts.extend(uc.get('prompts', []))
    cap['sample_prompts'] = all_prompts[:10]

    # Re-evaluate capability type for leaf nodes with use cases
    if cap.get('is_leaf') and cap.get('use_cases'):
        new_type = infer_capability_type(cap)
        if new_type != cap.get('capability_type'):
            cap['capability_type'] = new_type

    # Downgrade data_source for scraped pages where all UCs are empty after cleaning
    if cap.get('data_source') == 'scraped' and not cap.get('sample_prompts'):
        ucs = cap.get('use_cases', [])
        all_empty = all(
            not uc.get('prompts') and not uc.get('notes') and not uc.get('description', '').strip()
            for uc in ucs
        ) if ucs else True
        if all_empty:
            cap['data_source'] = 'description-only' if cap.get('description') else 'title-only'
            cap['use_cases'] = []

    return cap


def clean_data(input_path: str, output_path: str):
    """Main cleaning function."""
    with open(input_path) as f:
        data = json.load(f)

    stats = {
        'total_caps': len(data['capabilities']),
        'ucs_dropped': 0,
        'uc_names_cleaned': 0,
        'prompts_moved_to_notes': 0,
        'notes_moved_to_prompts': 0,
        'prompts_dropped': 0,
        'params_cleaned': 0,
        'type_changes': 0,
    }

    for cap in data['capabilities']:
        old_type = cap.get('capability_type')
        parent_type = cap.get('capability_type')
        is_signavio = 'signavio' in cap.get('product', '').lower()

        # Count original totals before cleaning
        orig_uc_count = len(cap.get('use_cases', []))
        orig_prompt_count = sum(len(uc.get('prompts', [])) for uc in cap.get('use_cases', []))
        orig_note_count = sum(len(uc.get('notes', [])) for uc in cap.get('use_cases', []))
        orig_param_count = sum(len(uc.get('parameters', [])) for uc in cap.get('use_cases', []))

        # Drop technical-ID UC rows
        cap['use_cases'] = [uc for uc in cap.get('use_cases', []) if not is_technical_uc(uc)]
        stats['ucs_dropped'] += orig_uc_count - len(cap['use_cases'])

        # Clean UC names
        for uc in cap['use_cases']:
            raw_name = uc.get('name', '')
            if '\n' in raw_name:
                clean_name, extracted_notes = clean_uc_name(raw_name)
                if clean_name != raw_name:
                    stats['uc_names_cleaned'] += 1
                uc['name'] = clean_name
                uc['notes'] = list(uc.get('notes', [])) + extracted_notes

        # Clean each UC
        for uc in cap['use_cases']:
            if is_signavio:
                uc['prompts'] = rejoin_signavio_fragments(uc.get('prompts', []))

            old_prompts = list(uc.get('prompts', []))
            old_notes = list(uc.get('notes', []))

            clean_use_case(uc, parent_type=parent_type, is_signavio=is_signavio)

            new_prompts = uc.get('prompts', [])
            new_notes = uc.get('notes', [])

            if len(old_prompts) > len(new_prompts):
                stats['prompts_moved_to_notes'] += len(old_prompts) - len(new_prompts)
            if len(new_prompts) > len(old_prompts):
                stats['notes_moved_to_prompts'] += len(new_prompts) - len(old_prompts)

        # Count cleaned params
        new_param_count = sum(len(uc.get('parameters', [])) for uc in cap['use_cases'])
        stats['params_cleaned'] += max(0, orig_param_count - new_param_count)

        # Rebuild sample_prompts
        all_prompts = []
        for uc in cap['use_cases']:
            all_prompts.extend(uc.get('prompts', []))
        cap['sample_prompts'] = all_prompts[:10]

        # Re-evaluate capability type
        if cap.get('is_leaf') and cap.get('use_cases'):
            new_type = infer_capability_type(cap)
            if new_type != old_type:
                stats['type_changes'] += 1
                cap['capability_type'] = new_type

        # Downgrade data_source for scraped pages where all UCs are empty after cleaning
        if cap.get('data_source') == 'scraped' and not cap.get('sample_prompts'):
            ucs = cap.get('use_cases', [])
            all_empty = all(
                not uc.get('prompts') and not uc.get('notes') and not uc.get('description', '').strip()
                for uc in ucs
            ) if ucs else True
            if all_empty:
                cap['data_source'] = 'description-only' if cap.get('description') else 'title-only'
                cap['use_cases'] = []

    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"Cleaning complete:")
    print(f"  Total capabilities: {stats['total_caps']}")
    print(f"  Technical UC rows dropped: {stats['ucs_dropped']}")
    print(f"  UC names cleaned (multi-line): {stats['uc_names_cleaned']}")
    print(f"  Prompts moved to notes: {stats['prompts_moved_to_notes']}")
    print(f"  Notes moved to prompts: {stats['notes_moved_to_prompts']}")
    print(f"  Parameters cleaned (tech IDs removed): {stats['params_cleaned']}")
    print(f"  Type reclassifications: {stats['type_changes']}")
    print(f"  Output: {output_path}")


if __name__ == '__main__':
    base = Path(__file__).parent.parent
    input_file = base / 'pipeline' / 'data' / 'joule_capabilities_raw.json'
    output_file = base / 'pipeline' / 'data' / 'joule_capabilities_clean.json'

    if len(sys.argv) > 1:
        input_file = Path(sys.argv[1])
    if len(sys.argv) > 2:
        output_file = Path(sys.argv[2])

    clean_data(str(input_file), str(output_file))
