# Thin wrapper for Mac/Linux. On Windows run the same commands with `py -m pipeline ...`.
PY ?= python3

.PHONY: setup validate test film

setup:
	$(PY) -m venv .venv
	.venv/bin/pip install -r requirements.txt

validate:
	$(PY) -m pipeline validate

test:
	$(PY) -m pytest

film:
	$(PY) -m pipeline film
