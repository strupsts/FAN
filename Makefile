.RECIPEPREFIX := >

BACKEND_DIR := backend
PYTHON := $(BACKEND_DIR)/.venv/bin/python
PIP := $(PYTHON) -m pip

.PHONY: help setup api db-up db-down db-logs db-init db-clear health health-db vlm-serve vlm-sample process api-e2e api-e2e-clean smoke status clean-pyc

help:
> @echo "F.A.N. dev commands:"
> @echo ""
> @echo "  make setup      Create/update WSL backend venv and install dependencies"
> @echo "  make api        Start FastAPI dev server"
> @echo "  make db-up      Start Postgres"
> @echo "  make db-down    Stop Postgres"
> @echo "  make db-logs    Show Postgres logs"
> @echo "  make db-init    Create database tables"
> @echo "  make db-clear   Delete dev receipt data from database"
> @echo "  make health     Check /health endpoint"
> @echo "  make health-db  Check /health/db endpoint"
> @echo "  make vlm-serve   Start the local receipt VLM server"
> @echo "  make vlm-sample  Test the receipt VLM on local samples"
> @echo "  make process    Send sample receipt to /api/receipts/process"
> @echo "  make api-e2e    Run process-confirm-history-summary API check"
> @echo "  make api-e2e-clean  Clear DB, then run API E2E check"
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

db-init:
> cd $(BACKEND_DIR) && PYTHONPATH=. .venv/bin/python scripts/init_db.py

db-clear:
> cd $(BACKEND_DIR) && PYTHONPATH=. .venv/bin/python scripts/clear_db.py

health:
> curl http://127.0.0.1:8000/health

health-db:
> curl http://127.0.0.1:8000/health/db

vlm-serve:
> bash scripts/serve_vlm.sh

vlm-sample:
> VLM_BASE_URL=http://127.0.0.1:8002/v1 VLM_MODEL=local-vlm-receipt-parser VLM_START_COMMAND='make vlm-serve' OUTPUT_ROOT=/tmp/fan_vlm_receipts python3 scripts/test_vlm_receipt_batch.py

process:
> curl -X POST "http://127.0.0.1:8000/api/receipts/process" \
>   -F "file=@data/test_receipt.jpg"

api-e2e:
> bash $(BACKEND_DIR)/scripts/api_e2e.sh

api-e2e-clean:
> $(MAKE) db-clear
> $(MAKE) api-e2e

smoke:
> cd $(BACKEND_DIR) && RECEIPT_EXTRACTION_PROVIDER=fake PYTHONPATH=. .venv/bin/python scripts/smoke.py

status:
> git status

clean-pyc:
> find . -type d -name "__pycache__" -prune -exec rm -rf {} +
> find . -type f -name "*.pyc" -delete
