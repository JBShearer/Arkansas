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


def clean_use_case(uc: dict) -> dict:
    """Clean a single use case: fix prompts vs notes."""
    prompts = uc.get('prompts', [])
    notes = uc.get('notes', [])
    
    clean_prompts = []
    new_notes = list(notes)
    
    for p in prompts:
        p = p.strip()
        if not p:
            continue
        if is_not_a_prompt(p):
            new_notes.append(p)
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
        
        for uc in cap.get('use_cases', []):
            old_prompts = len(uc.get('prompts', []))
            old_notes = len(uc.get('notes', []))
            
            clean_use_case(uc)
            
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