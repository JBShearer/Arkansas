# SAP Business AI — Arkansas

**Website:** [easyassap.com](https://easyassap.com)  
**Repo:** [github.com/mhackersu/easyassap](https://github.com/mhackersu/easyassap)

## Overview

Python pipeline for analyzing SAP Business AI features and generating the easyassap.com website content. Arkansas is using a **Crawl → Walk → Run** approach to AI adoption.

## Structure

```
Joule/                      # Workspace
├── config.yaml             # Pipeline configuration
├── Makefile                # Build commands
├── requirements.txt        # Python deps
├── pipeline/               # Python pipeline
│   ├── main.py             # Entry point
│   ├── sources/loader.py   # Document loading
│   ├── analysis/analyzer.py # Feature analysis
│   ├── generators/         # Site content generation
│   └── data/               # Intermediate JSON data
├── sources/                # Raw SAP documents
├── output/                 # Analysis outputs
├── site/                   # easyassap repo (cloned)
└── SESSION_STATE.md        # Read this in new sessions
```

## Commands

```bash
make build       # analyze + generate
make deploy      # push site/ to GitHub
make analyze     # run analysis only
make generate    # generate site content only