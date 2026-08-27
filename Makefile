SHELL := /bin/sh
PYTHON := python3

.PHONY: help check test lint run

help:
	@printf '%s\n' 'Targets: check test lint run'

check: test lint

test:
	$(PYTHON) -m unittest discover -s tests -v

lint:
	@echo 'Add project-specific linting here.'

run:
	$(PYTHON) app.py
