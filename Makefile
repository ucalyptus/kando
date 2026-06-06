.PHONY: setup dev-setup start status trace test eventstore docker-status docker-trace docker-build run run-research run-durable

VENV    := .venv
PYTHON  := python3
PIP     := $(VENV)/bin/pip
KANDO   := $(VENV)/bin/python -m kando.cli.main

# Create venv and install runtime + stream + mcp extras
setup:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --quiet -e ".[stream,mcp]"

# Like setup but also installs dev tools (pytest, hypothesis, etc.)
dev-setup:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --quiet -e ".[dev]"

# Quick smoke test: status demo + trace demo (works without ESDB)
start: setup status trace

status:
	$(KANDO) status demo

trace:
	$(KANDO) trace object.created-2

# Run tests; dev-setup installs pytest automatically
test: dev-setup
	$(VENV)/bin/python -m pytest

# Start EventStoreDB (required for kando run / replay / fork / diff)
eventstore:
	docker compose up -d eventstore

# Run diligence kit (in-memory if EVENTSTORE_URL unset; GOAL required)
run: setup
	$(KANDO) run kits/diligence --goal "$(GOAL)"

# Run research kit (in-memory if EVENTSTORE_URL unset; GOAL required)
run-research: setup
	$(KANDO) run kits/research --goal "$(GOAL)"

# Run against EventStoreDB
run-durable: setup eventstore
	EVENTSTORE_URL=http://localhost:2113 $(KANDO) run kits/diligence --goal "$(GOAL)"

docker-build:
	docker compose build kando

docker-status:
	docker compose run --rm kando python -m kando.cli.main status demo

docker-trace:
	docker compose run --rm kando python -m kando.cli.main trace object.created-2
