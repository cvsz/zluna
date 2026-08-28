SHELL := /bin/sh
PYTHON := python3

.PHONY: help check test run

help:
	@printf '%s\n' 'Targets: check test run'

check: test

test:
	PYTHONPATH=src $(PYTHON) -m pytest tests/ -v

run:
	PYTHONPATH=src $(PYTHON) src/app.py
