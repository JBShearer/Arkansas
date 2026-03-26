.PHONY: all scrape enrich cleandata generate deploy serve clean

# Full pipeline: scrape → enrich → clean → generate → deploy
all: enrich cleandata generate deploy

# Scrape SAP Help Portal (requires Node.js + Puppeteer, ~8 min)
scrape:
	node pipeline/sources/scrape_help.js

# Enrich TOC with scraped data (no Mixed type)
enrich:
	python3 -m pipeline.enrich_toc

# Clean data quality (move notes↔prompts, fix types)
cleandata:
	python3 pipeline/clean_data.py

# Generate HTML site (uses clean data if available)
generate:
	python3 -m pipeline.generators.site_generator
	cp site/index.html index.html

# Deploy to GitHub Pages
deploy:
	git add -A && git commit -m "Update site — $$(date '+%Y-%m-%d %H:%M')" && git push

# Local preview
serve:
	python3 -m http.server 4000 --directory site

# Clean generated data
clean:
	rm -rf pipeline/data/*.json site/index.html index.html