.RECIPEPREFIX := >

BACKEND_DIR := backend
PYTHON := $(BACKEND_DIR)/.venv/bin/python
PIP := $(PYTHON) -m pip

.PHONY: help setup api db-up db-down db-logs health process smoke status clean-pyc

help:
> @echo "F.A.N. dev commands:"
> @echo ""
> @echo "  make setup      Create/update WSL backend venv and install dependencies"
> @echo "  make api        Start FastAPI dev server"
> @echo "  make db-up      Start Postgres"
> @echo "  make db-down    Stop Postgres"
> @echo "  make db-logs    Show Postgres logs"
> @echo "  make health     Check /health endpoint"
> @echo "  make process    Send sample receipt to /api/receipts/process"
> @echo "  make smoke      Run core smoke test without HTTP"
> @echo "  make status     Show git status"
> @echo "  make clean-pyc  Remove Python cache files"

setup:
> python3 -m venv $(BACKEND_DIR)/.venv
> $(PIP) install -U pip
> $(PIP) install -e $(BACKEND_DIR)

api:
> cd $(BACKEND_DIR) && PYTHONPATH=. .venv/bin/uvicorn app.main:app --reload

db-up:
> docker compose up -d db

db-down:
> docker compose down

db-logs:
> docker compose logs -f db

health:
> curl http://127.0.0.1:8000/health

process:
> curl -X POST "http://127.0.0.1:8000/api/receipts/process" \
>   -F "file=@data/test_receipt.jpg"

smoke:
> cd $(BACKEND_DIR) && PYTHONPATH=. .venv/bin/python scripts/smoke.py

status:
> git status

clean-pyc:
> find . -type d -name "__pycache__" -prune -exec rm -rf {} +
> find . -type f -name "*.pyc" -delete
