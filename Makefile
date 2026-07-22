.RECIPEPREFIX := >

BACKEND_DIR := backend
PYTHON := $(BACKEND_DIR)/.venv/bin/python
PIP := $(PYTHON) -m pip

.PHONY: help setup api db-up db-down db-logs db-init db-clear health health-db llm-health llm-serve llm-parse ocr-surya-v1-setup ocr-surya-v1-sample ocr-surya-v2-setup ocr-surya-v2-sample vlm-qwen25vl7b-serve vlm-qwen25vl7b-sample vlm-minicpmv45-serve vlm-minicpmv45-sample process api-e2e api-e2e-clean smoke status clean-pyc

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
> @echo "  make llm-health Check vLLM /v1/models endpoint"
> @echo "  make llm-serve  Start local vLLM Qwen3-8B-AWQ server"
> @echo "  make llm-parse  Test vLLM receipt parser adapter"
> @echo "  make ocr-surya-v1-setup   Create/update local Surya v1 OCR venv"
> @echo "  make ocr-surya-v1-sample  Run Surya v1 OCR on data/test_receipt.jpg"
> @echo "  make ocr-surya-v2-setup   Create/update local Surya v2 OCR venv"
> @echo "  make ocr-surya-v2-sample  Run Surya v2 OCR on data/test_receipt.jpg"
> @echo "  make vlm-qwen25vl7b-serve   Start Qwen2.5-VL-7B-AWQ vLLM server"
> @echo "  make vlm-qwen25vl7b-sample  Test Qwen2.5-VL on local receipt folder"
> @echo "  make vlm-minicpmv45-serve   Start MiniCPM-V 4.5 AWQ vLLM server"
> @echo "  make vlm-minicpmv45-sample  Test MiniCPM-V 4.5 on local receipt folder"
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

llm-health:
> cd $(BACKEND_DIR) && PYTHONPATH=. .venv/bin/python scripts/check_vllm.py

llm-serve:
> bash scripts/serve_vllm_awq.sh

llm-parse:
> cd $(BACKEND_DIR) && PYTHONPATH=. .venv/bin/python scripts/test_vllm_parser.py

ocr-surya-v1-setup:
> bash scripts/setup_surya_v1.sh

ocr-surya-v1-sample:
> bash scripts/run_surya_v1_ocr_sample.sh

ocr-surya-v2-setup:
> bash scripts/setup_surya_v2.sh

ocr-surya-v2-sample:
> bash scripts/run_surya_v2_ocr_sample.sh

vlm-qwen25vl7b-serve:
> bash scripts/serve_vlm_qwen25vl7b_awq.sh

vlm-qwen25vl7b-sample:
> VLM_BASE_URL=http://127.0.0.1:8002/v1 VLM_MODEL=local-vlm-receipt-parser VLM_START_COMMAND='make vlm-qwen25vl7b-serve' OUTPUT_ROOT=/tmp/fan_vlm_qwen25vl7b_awq python3 scripts/test_vlm_receipt_batch.py

vlm-minicpmv45-serve:
> bash scripts/serve_vlm_minicpmv45_awq.sh

vlm-minicpmv45-sample:
> VLM_BASE_URL=http://127.0.0.1:8003/v1 VLM_MODEL=local-vlm-minicpm-receipt-parser VLM_START_COMMAND='make vlm-minicpmv45-serve' OUTPUT_ROOT=/tmp/fan_vlm_minicpmv45_awq python3 scripts/test_vlm_receipt_batch.py

process:
> curl -X POST "http://127.0.0.1:8000/api/receipts/process" \
>   -F "file=@data/test_receipt.jpg"

api-e2e:
> bash $(BACKEND_DIR)/scripts/api_e2e.sh

api-e2e-clean:
> $(MAKE) db-clear
> $(MAKE) api-e2e

smoke:
> cd $(BACKEND_DIR) && PYTHONPATH=. .venv/bin/python scripts/smoke.py

status:
> git status

clean-pyc:
> find . -type d -name "__pycache__" -prune -exec rm -rf {} +
> find . -type f -name "*.pyc" -delete
