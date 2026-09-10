# Course Video Generator - developer commands
# On Windows use: make PYTHON=<path-to-python> <target>

PYTHON ?= python
PIP ?= $(PYTHON) -m pip

.PHONY: setup fixture preview render test test-unit test-integration \
	remotion-install remotion-preview clean

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
	cd remotion && npm.cmd install --cache .npm-cache --no-audit --no-fund

remotion-typecheck:
	cd remotion && npx.cmd tsc --noEmit

remotion-smoke:
	cd remotion && npx.cmd remotion render src/index.ts TestSuite ../output/test-suite.mp4 --frames=0-30 --codec=h264

remotion-preview:
	cd remotion && npx.cmd remotion studio

clean:
	$(PYTHON) pipeline/main.py --help > /dev/null
	@echo "Remove generated/, output/, cache/, logs/ manually to force a full rebuild."
