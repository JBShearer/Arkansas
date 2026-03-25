"""Load source documents from sources/ directory."""

import json
from pathlib import Path


def load_sources(workspace: Path) -> list[dict]:
    """Load all source docs. Returns list of dicts with path, type, content."""
    sources_dir = workspace / "sources"
    docs = []
    if not sources_dir.exists():
        return docs
    for f in sources_dir.rglob("*"):
        if f.is_file() and not f.name.startswith("."):
            docs.append({
                "path": str(f.relative_to(workspace)),
                "name": f.stem,
                "content": f.read_text(encoding="utf-8") if f.suffix in (".md", ".json", ".txt") else None,
            })
    return docs