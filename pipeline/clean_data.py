#!/usr/bin/env python3
"""
Data quality cleaner for Joule capabilities data.
Fixes:
1. Notes/descriptions that ended up in prompts arrays
2. Prompts that are actually notes (move to notes)
3. Notes that are actually prompts (move to prompts)
4. Capability type corrections based on heuristics
5. Sports One descriptive text in prompts
6. Work Zone missing type info
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
    r'^You can ',
    r'^You must ',
    r'^You will ',
    r'^You are required',
    r'^You need to',
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
    r'^(Posting block status details)$',
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
    # Must start with an uppercase letter
    if not t[0].isupper():
        return False
    # Prompt-starter words that indicate a user sentence, not an app name
    prompt_starters = {
        'show', 'display', 'find', 'search', 'get', 'list', 'fetch',
        'create', 'change', 'update', 'delete', 'post', 'cancel',
        'where', 'which', 'what', 'how', 'who', 'when', 'why',
        'i', 'help', 'open', 'navigate', 'go',
    }
    first_word = re.split(r'\s+', t)[0].rstrip('.,').lower()
    if first_word in prompt_starters:
        return False
    # Must look like title case (most words capitalised)
    words = re.split(r'\s+', t)
    short_words = {'a', 'an', 'the', 'of', 'for', 'in', 'to', 'and', 'or', 'by', 'with', 'on', 'at'}
    cap_words = [w for w in words if w not in short_words]
    if not cap_words:
        return False
    frac = sum(1 for w in cap_words if w and w[0].isupper()) / len(cap_words)
    return frac >= 0.75


def infer_uc_type(uc: dict, parent_type: str = None) -> str:
    """Infer capability_type for a single use case based on its name and prompts.

    If the parent capability is Navigational, the UC inherits that type directly —
    the heuristics should not override a known-good parent classification.
    """
    # Navigational parent always wins — don't second-guess it with word heuristics
    if parent_type == 'Navigational':
        return 'Navigational'

    name = uc.get('name', '').lower()
    prompts = uc.get('prompts', [])
    prompt_text = ' '.join(prompts).lower()
    # Use word-level matching to avoid substring false positives (e.g. "approver" matching "approve")
    name_words = set(re.split(r'[\s\-/,.()\[\]]+', name))

    nav_keywords = {'navigate', 'launch', 'open'}
    nav_phrases = ['finding apps', 'go to']
    if name_words & nav_keywords or any(k in name for k in nav_phrases):
        return 'Navigational'

    anal_keywords = {'analytical', 'insights', 'analytics', 'analysis'}
    if name_words & anal_keywords or 'report' in name:
        return 'Analytical'

    info_words = {'display', 'view', 'show', 'fetch', 'search', 'list', 'get', 'find',
                  'summarize', 'summarise', 'read', 'check', 'query'}
    trans_words = {'create', 'change', 'edit', 'update', 'delete', 'manage', 'post', 'clear',
                   'assign', 'complete', 'cancel', 'reject', 'release', 'approve', 'perform',
                   'process', 'submit', 'resubmit', 'execute', 'add', 'remove', 'set', 'send', 'generate',
                   'schedule', 'confirm', 'activate', 'deploy', 'transfer', 'modify', 'close',
                   'open', 'resolve', 'handle', 'apply', 'save', 'publish', 'lock', 'unlock'}

    name_is_info = bool(name_words & info_words)
    name_is_trans = bool(name_words & trans_words)

    if name_is_info and not name_is_trans:
        return 'Informational'
    if name_is_trans and not name_is_info:
        return 'Transactional'

    # Fall back to checking first word of first prompt
    trans_prompt_verbs = {'create', 'submit', 'change', 'update', 'delete', 'approve', 'reject',
                          'process', 'post', 'log', 'assign', 'complete', 'release', 'cancel',
                          'close', 'add', 'remove', 'set', 'send', 'generate', 'schedule', 'save'}
    info_prompt_verbs = {'show', 'display', 'list', 'get', 'find', 'search', 'view', 'fetch',
                         'what', 'how', 'give', 'tell', 'summarize', 'summarise', 'explain'}
    first_word = prompt_text.split()[0].rstrip('?.,') if prompt_text.strip() else ''
    if first_word in trans_prompt_verbs:
        return 'Transactional'
    if first_word in info_prompt_verbs:
        return 'Informational'

    return 'Informational'  # safe default


def infer_capability_type(cap: dict) -> str:
    """Improve capability_type based on title and use case content."""
    title = cap.get('title', '').lower()
    all_prompts = []
    for uc in cap.get('use_cases', []):
        all_prompts.extend(uc.get('prompts', []))
    prompt_text = ' '.join(all_prompts).lower()
    uc_names = ' '.join(uc.get('name', '') for uc in cap.get('use_cases', [])).lower()

    # Navigational indicators
    nav_keywords = ['finding apps', 'go to', 'navigate', 'open ', 'launch']
    if any(k in title for k in nav_keywords):
        return 'Navigational'

    # Analytical indicators
    anal_keywords = ['analytical', 'insights', 'analytics', 'report', 'analysis']
    if any(k in title for k in anal_keywords):
        return 'Analytical'

    # Informational - display/view/show only, no create/change/delete
    info_keywords = ['display', 'view', 'show', 'fetch', 'search', 'informational']
    trans_keywords = ['create', 'change', 'edit', 'update', 'delete', 'manage', 'mass change', 'post', 'clear', 'assign', 'complete', 'cancel', 'reject', 'release']
    
    title_is_info = any(k in title for k in info_keywords)
    title_is_trans = any(k in title for k in trans_keywords)
    
    if title_is_info and not title_is_trans:
        return 'Informational'
    if title_is_trans:
        return 'Transactional'
    
    # Check use case names
    has_info = any(k in uc_names for k in ['display', 'view', 'show', 'fetch', 'search'])
    has_trans = any(k in uc_names for k in ['create', 'change', 'edit', 'update', 'delete', 'complete', 'cancel', 'reject'])

    # Check prompts for transactional verbs (used both here and in fallback)
    trans_prompt_verbs = ['create', 'submit', 'change', 'update', 'delete', 'approve', 'reject', 'process',
                          'post', 'log', 'report', 'assign', 'complete', 'release', 'cancel', 'close']
    has_trans_prompts = any(any(v in p.lower() for v in trans_prompt_verbs) for p in all_prompts)

    if has_info and has_trans:
        # Transactional wins if there are actual transactional prompts; otherwise Informational
        return 'Transactional' if has_trans_prompts else 'Informational'
    if has_info and not has_trans:
        return 'Informational'
    if has_trans:
        return 'Transactional'
    
    existing = cap.get('capability_type', 'Informational')
    if existing == 'Mixed':
        # Resolve Mixed: Transactional if any transactional prompts exist, else Informational
        return 'Transactional' if has_trans_prompts else 'Informational'
    return existing


def clean_use_case(uc: dict, parent_type: str = None) -> dict:
    """Clean a single use case: fix prompts vs notes.

    For Navigational use cases, items in the prompts array that look like
    Fiori app names are moved to parameters (they are navigation targets,
    not things the user types).
    """
    prompts = uc.get('prompts', [])
    notes = uc.get('notes', [])

    clean_prompts = []
    new_notes = list(notes)

    for p in prompts:
        p = p.strip()
        if not p:
            continue
        # Strip " Joule provides/explains/compares/..." appended after the user question.
        # SAP Help "Informational Capability" page uses format: "What is X? Joule provides Y."
        # The real user prompt is everything up to and including the first "?".
        m = re.match(r'^(.+?\?)\s+Joule\b.+', p, re.DOTALL)
        if m:
            p = m.group(1).strip()
        if is_not_a_prompt(p):
            new_notes.append(p)
        elif parent_type == 'Navigational' and is_app_name(p):
            # This is a Fiori app name (navigation target), not a user-typed prompt
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
        if is_note_actually_prompt(n):
            clean_prompts.append(n)
        else:
            remaining_notes.append(n)

    uc['prompts'] = clean_prompts
    uc['notes'] = remaining_notes
    # Infer use-case-level capability type
    uc['capability_type'] = infer_uc_type(uc, parent_type=parent_type)
    return uc


def clean_capability(cap: dict) -> dict:
    """Clean a single capability entry."""
    # Clean use cases
    for uc in cap.get('use_cases', []):
        clean_use_case(uc)

    # Rebuild sample_prompts from cleaned use case prompts
    all_prompts = []
    for uc in cap.get('use_cases', []):
        all_prompts.extend(uc.get('prompts', []))
    cap['sample_prompts'] = all_prompts[:10]  # Keep top 10

    # Re-evaluate capability type for leaf nodes with use cases
    if cap.get('is_leaf') and cap.get('use_cases'):
        new_type = infer_capability_type(cap)
        if new_type != cap.get('capability_type'):
            cap['capability_type'] = new_type

    # Downgrade data_source for scraped pages where all UCs are empty after cleaning.
    # Also remove the empty UC shells so the renderer uses the description-only path.
    if cap.get('data_source') == 'scraped' and not cap.get('sample_prompts'):
        ucs = cap.get('use_cases', [])
        all_empty = all(
            not uc.get('prompts') and not uc.get('notes') and not uc.get('description', '').strip()
            for uc in ucs
        ) if ucs else True
        if all_empty:
            cap['data_source'] = 'description-only' if cap.get('description') else 'title-only'
            cap['use_cases'] = []  # Remove empty shells so renderer picks the right path

    return cap


def clean_data(input_path: str, output_path: str):
    """Main cleaning function."""
    with open(input_path) as f:
        data = json.load(f)
    
    stats = {
        'prompts_moved_to_notes': 0,
        'notes_moved_to_prompts': 0,
        'type_changes': 0,
        'total_caps': len(data['capabilities']),
    }
    
    for cap in data['capabilities']:
        old_type = cap.get('capability_type')
        parent_type = cap.get('capability_type')

        for uc in cap.get('use_cases', []):
            old_prompts = len(uc.get('prompts', []))
            old_notes = len(uc.get('notes', []))

            clean_use_case(uc, parent_type=parent_type)

            new_prompts = len(uc.get('prompts', []))
            new_notes = len(uc.get('notes', []))
            
            moved_to_notes = old_prompts - new_prompts + (new_notes - old_notes - (old_prompts - new_prompts))
            if old_prompts > new_prompts:
                stats['prompts_moved_to_notes'] += old_prompts - new_prompts
            if new_prompts > old_prompts:
                stats['notes_moved_to_prompts'] += new_prompts - old_prompts
        
        # Rebuild sample_prompts
        all_prompts = []
        for uc in cap.get('use_cases', []):
            all_prompts.extend(uc.get('prompts', []))
        cap['sample_prompts'] = all_prompts[:10]

        # Re-evaluate capability type
        if cap.get('is_leaf') and cap.get('use_cases'):
            new_type = infer_capability_type(cap)
            if new_type != old_type:
                stats['type_changes'] += 1
                cap['capability_type'] = new_type

        # Downgrade data_source for scraped pages where all UCs are empty after cleaning.
        # Also remove the empty UC shells so the renderer uses the description-only path.
        if cap.get('data_source') == 'scraped' and not cap.get('sample_prompts'):
            ucs = cap.get('use_cases', [])
            all_empty = all(
                not uc.get('prompts') and not uc.get('notes') and not uc.get('description', '').strip()
                for uc in ucs
            ) if ucs else True
            if all_empty:
                cap['data_source'] = 'description-only' if cap.get('description') else 'title-only'
                cap['use_cases'] = []  # Remove empty shells so renderer picks the right path
    
    # Write cleaned data
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Cleaning complete:")
    print(f"  Total capabilities: {stats['total_caps']}")
    print(f"  Prompts moved to notes: {stats['prompts_moved_to_notes']}")
    print(f"  Notes moved to prompts: {stats['notes_moved_to_prompts']}")
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