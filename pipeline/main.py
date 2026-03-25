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
        from pipeline.generators.site_generator import run
        run(config, WORKSPACE)
    elif cmd == "build":
        from pipeline.analysis.analyzer import run as analyze
        from pipeline.generators.site_generator import run as generate
        analyze(config, WORKSPACE)
        generate(config, WORKSPACE)
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()