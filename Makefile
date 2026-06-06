.PHONY: setup start status trace test eventstore docker-status docker-trace

VENV := .venv
PYTHON := python3
KANDO := $(VENV)/bin/python -m kando.cli.main

setup:
	$(PYTHON) -m venv $(VENV)

start: setup status trace

status:
	$(KANDO) status demo

trace:
	$(KANDO) trace object.created-2

test:
	$(VENV)/bin/python -m pytest

eventstore:
	docker compose up -d eventstore

docker-status:
	docker compose run --rm kando python -m kando.cli.main status demo

docker-trace:
	docker compose run --rm kando python -m kando.cli.main trace object.created-2
