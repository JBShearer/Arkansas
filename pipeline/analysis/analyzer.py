"""Analyze SAP Business AI features and categorize by adoption phase."""

import json
from pathlib import Path


def run(config: dict, workspace: Path):
    """Run analysis. Populate pipeline/data/features.json."""
    data_dir = workspace / "pipeline" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    features_path = data_dir / "features.json"

    if features_path.exists():
        print(f"Features data already exists at {features_path}")
        return

    # Placeholder — will be populated with real feature data
    data = {"features": [], "metadata": {"customer": config.get("customer", {}).get("name", "")}}
    with open(features_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Initialized empty features file at {features_path}")