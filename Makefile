.PHONY: test check build preview web-build audit clean

# Li&Blog 常用开发入口（容器内构建仍走 scripts/build.py）

PY ?= .venv/bin/python

test:
	$(PY) -m unittest discover -s tests -q

check:
	$(PY) scripts/check_hardcoded.py
	$(PY) scripts/check_contrast.py

build:
	$(PY) scripts/build.py --full

preview:
	$(PY) scripts/build.py --preview

web-build:
	cd web && npm run build

audit:
	$(PY) scripts/check_hardcoded.py
	$(PY) scripts/check_contrast.py
	$(PY) scripts/build.py --full

clean:
	rm -rf .build-tmp .preview-out resources/_gen
