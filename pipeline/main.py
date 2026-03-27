"""Pipeline entry point.

Usage:
    python -m pipeline.main analyze
    python -m pipeline.main generate
    python -m pipeline.main build
"""

import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent


def load_config():
    import yaml
    with open(WORKSPACE / "config.yaml") as f:
        return yaml.safe_load(f)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    config = load_config()

    if cmd == "analyze":
        from pipeline.analysis.analyzer import run
        run(config, WORKSPACE)
    elif cmd == "generate":
        from pipeline.generators.site_generator import generate
        generate()
    elif cmd == "clean":
        from pipeline.clean_data import clean_data
        raw = str(WORKSPACE / "pipeline" / "data" / "joule_capabilities_raw.json")
        clean = str(WORKSPACE / "pipeline" / "data" / "joule_capabilities_clean.json")
        clean_data(raw, clean)
    elif cmd == "build":
        from pipeline.analysis.analyzer import run as analyze
        from pipeline.clean_data import clean_data
        from pipeline.generators.site_generator import generate
        analyze(config, WORKSPACE)
        raw = str(WORKSPACE / "pipeline" / "data" / "joule_capabilities_raw.json")
        clean = str(WORKSPACE / "pipeline" / "data" / "joule_capabilities_clean.json")
        clean_data(raw, clean)
        generate()
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()