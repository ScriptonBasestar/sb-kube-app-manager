# Installation targets

.PHONY: install install-global install-system install-dev install-test install-all

install:
	uv pip install -e .

install-global:
	uv tool install . --force

install-system:
	uv pip install -e . --system

install-dev:
	uv pip install -e . --group dev

install-test:
	uv pip install -e . --group test

install-all:
	uv pip install -e . --group dev --group test
