"""Generate site content from analyzed feature data."""

import json
from pathlib import Path


def run(config: dict, workspace: Path):
    """Generate Markdown pages into the site directory."""
    site_dir = workspace / "site"
    data_path = workspace / "pipeline" / "data" / "features.json"

    if not data_path.exists():
        print("No features.json found. Run 'python -m pipeline.main analyze' first.")
        return

    with open(data_path) as f:
        data = json.load(f)

    # Placeholder — will generate pages from feature data
    print(f"Generator ready. {len(data.get('features', []))} features available.")
    print(f"Site directory: {site_dir}")