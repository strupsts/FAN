.RECIPEPREFIX := >

BACKEND_DIR := backend
PYTHON := $(BACKEND_DIR)/.venv/bin/python
PIP := $(PYTHON) -m pip
UVICORN := $(BACKEND_DIR)/.venv/bin/uvicorn

.PHONY: help setup api health process smoke status clean-pyc

help:
> @echo "F.A.N. dev commands:"
> @echo ""
> @echo "  make setup      Create/update WSL backend venv and install dependencies"
> @echo "  make api        Start FastAPI dev server"
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
