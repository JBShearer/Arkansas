.PHONY: build analyze generate deploy serve clean

build: analyze generate

analyze:
	python -m pipeline.main analyze

generate:
	python -m pipeline.main generate

deploy:
	cd site && git add -A && git commit -m "Update site — $$(date '+%Y-%m-%d %H:%M')" && git push origin main

serve:
	cd site && bundle exec jekyll serve --port 4000

clean:
	rm -rf output/* pipeline/data/*.json