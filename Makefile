# Course Video Generator - developer commands
#
# Defaults work on macOS, Linux, and most Windows setups.
# Commands can be overridden when needed, for example:
#
#   make PYTHON=py
#   make NPM=npm.cmd NPX=npx.cmd remotion-install

PYTHON ?= python
PIP ?= $(PYTHON) -m pip
NPM ?= npm
NPX ?= npx

.PHONY: \
	setup \
	fixture \
	preview \
	render \
	test \
	test-unit \
	test-integration \
	remotion-install \
	remotion-typecheck \
	remotion-smoke \
	remotion-preview \
	clean

setup:
	$(PIP) install -r requirements.txt

fixture:
	$(PYTHON) tests/fixtures/generate_course_docx.py --out input/course.docx

preview:
	$(PYTHON) pipeline/main.py input/course.docx --preview

render:
	$(PYTHON) pipeline/main.py input/course.docx

test: test-unit test-integration

test-unit:
	$(PYTHON) -m pytest tests -m "not integration" -q

test-integration:
	$(PYTHON) -m pytest tests -m integration -q

remotion-install:
	cd remotion && $(NPM) ci --cache .npm-cache --no-audit --no-fund

remotion-typecheck:
	cd remotion && $(NPX) tsc --noEmit

remotion-smoke:
	cd remotion && $(NPX) remotion render src/index.ts TestSuite ../output/test-suite.mp4 --frames=0-30 --codec=h264

remotion-preview:
	cd remotion && $(NPX) remotion studio

clean:
	$(PYTHON) -c "import shutil; from pathlib import Path; [shutil.rmtree(Path(p), ignore_errors=True) for p in ('generated', 'output', 'cache', 'logs', '.tmp')]"
	@echo "Generated files, output, cache, logs, and temporary files removed."