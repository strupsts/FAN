.RECIPEPREFIX := >

BACKEND_DIR := backend
PYTHON := $(BACKEND_DIR)/.venv/bin/python
PROFILE ?= dev
PROVISION_YES_ARG := $(if $(filter 1 yes true,$(YES)),--yes,)

.PHONY: help provision doctor provision-test setup api db-up db-down db-logs db-clear health health-db vlm-health vlm-serve vlm-sample process api-e2e api-e2e-clean test smoke status clean-pyc frontend frontend-build frontend-lint android-debug-sync dev dev-down dev-status dev-logs db-upgrade db-downgrade db-current db-check db-revision db-stamp api-schema frontend-api-types api-contracts api-contracts-check

help:
> @echo "F.A.N. dev commands:"
> @echo ""
> @echo "  make provision  Converge the Linux environment (PROFILE=dev|backend|server)"
> @echo "  make doctor     Read-only environment diagnosis"
> @echo "  make provision-test  Run provisioning logic tests"
> @echo "  make dev        Verify and start the provisioned development stack"
> @echo "  make dev-down   Stop the full development stack"
> @echo "  make dev-status Show development stack status"
> @echo "  make dev-logs   Follow API and VLM logs"
> @echo "  make setup      Compatibility alias for backend-only provisioning"
> @echo "  make api        Start FastAPI dev server"
> @echo "  make api-schema Export FastAPI OpenAPI schema"
> @echo "  make frontend-api-types Generate frontend API types"
> @echo "  make api-contracts Regenerate schema and frontend types"
> @echo "  make api-contracts-check Check generated API contract drift"
> @echo "  make frontend   Start Ionic frontend dev server"
> @echo "  make frontend-build Build Ionic frontend"
> @echo "  make frontend-lint  Lint Ionic frontend"
> @echo "  make android-debug-sync Build and sync Android debug web assets"
> @echo "  make db-up      Start Postgres"
> @echo "  make db-down    Stop Postgres"
> @echo "  make db-logs    Show Postgres logs"
> @echo "  make db-upgrade Apply pending database migrations"
> @echo "  make db-downgrade Revert the latest database migration"
> @echo "  make db-current Show the current database revision"
> @echo "  make db-check   Check ORM models for ungenerated changes"
> @echo "  make db-revision MESSAGE=\"...\"  Generate a migration"
> @echo "  make db-stamp   Mark an existing schema as current (bootstrap only)"
> @echo "  make db-clear   Delete dev receipt data from database"
> @echo "  make health     Check /health endpoint"
> @echo "  make health-db  Check /health/db endpoint"
> @echo "  make vlm-health Check whether the receipt VLM is ready"
> @echo "  make vlm-serve   Start the local receipt VLM server"
> @echo "  make vlm-sample  Test the receipt VLM on local samples"
> @echo "  make process    Send sample receipt to /api/receipts/process"
> @echo "  make api-e2e    Run process-confirm-history-summary API check"
> @echo "  make api-e2e-clean  Clear DB, then run API E2E check"
> @echo "  make test       Run backend unit tests"
> @echo "  make smoke      Run core smoke test without HTTP"
> @echo "  make status     Show git status"
> @echo "  make clean-pyc  Remove Python cache files"

dev:
> @bash scripts/doctor.sh --profile dev --quiet
> bash scripts/dev_stack.sh up

provision:
> bash scripts/provision/linux.sh --profile "$(PROFILE)" $(PROVISION_YES_ARG)

doctor:
> @bash scripts/doctor.sh --profile "$(PROFILE)"

provision-test:
> bash scripts/provision/tests/run.sh

dev-down:
> bash scripts/dev_stack.sh down

dev-status:
> bash scripts/dev_stack.sh status

dev-logs:
> @mkdir -p .runtime/logs
> @touch .runtime/logs/api.log .runtime/logs/vlm.log .runtime/logs/frontend.log
> tail -n 100 -F .runtime/logs/vlm.log .runtime/logs/api.log .runtime/logs/frontend.log

setup:
> @echo "make setup now performs backend-only locked provisioning."
> $(MAKE) provision PROFILE=backend YES="$(YES)"

api:
> cd $(BACKEND_DIR) && PYTHONPATH=. .venv/bin/uvicorn app.main:app --reload

api-schema:
> cd $(BACKEND_DIR) && PYTHONPATH=. .venv/bin/python scripts/export_openapi.py

frontend-api-types:
> bash -c 'export NVM_DIR="$$HOME/.nvm"; . "$$NVM_DIR/nvm.sh"; cd frontend; nvm use --silent; npm run api:types'

api-contracts:
> $(MAKE) api-schema
> $(MAKE) frontend-api-types

api-contracts-check:
> $(MAKE) api-contracts
> git diff --exit-code -- frontend/openapi/openapi.json frontend/src/app/core/api/generated/openapi-types.ts

frontend:
> bash -c 'export NVM_DIR="$$HOME/.nvm"; . "$$NVM_DIR/nvm.sh"; cd frontend; nvm use --silent; exec npm run start:mobile'

frontend-build:
> bash -c 'export NVM_DIR="$$HOME/.nvm"; . "$$NVM_DIR/nvm.sh"; cd frontend; nvm use --silent; npm run build'

frontend-lint:
> bash -c 'export NVM_DIR="$$HOME/.nvm"; . "$$NVM_DIR/nvm.sh"; cd frontend; nvm use --silent; npm run lint'

android-debug-sync:
> bash -c 'export NVM_DIR="$$HOME/.nvm"; . "$$NVM_DIR/nvm.sh"; cd frontend; nvm use --silent; export FAN_ANDROID_DEBUG=1; npm run build:android:debug; npx cap sync android'

db-up:
> docker compose up -d db

db-down:
> docker compose down

db-logs:
> docker compose logs -f db

db-upgrade:
> cd $(BACKEND_DIR) && PYTHONPATH=. .venv/bin/alembic upgrade head

db-downgrade:
> cd $(BACKEND_DIR) && PYTHONPATH=. .venv/bin/alembic downgrade -1

db-current:
> cd $(BACKEND_DIR) && PYTHONPATH=. .venv/bin/alembic current

db-check:
> cd $(BACKEND_DIR) && PYTHONPATH=. .venv/bin/alembic check

db-revision:
> @test -n "$(MESSAGE)" || (echo 'Usage: make db-revision MESSAGE="describe change"' && exit 2)
> cd $(BACKEND_DIR) && PYTHONPATH=. .venv/bin/alembic revision --autogenerate -m "$(MESSAGE)"

db-stamp:
> cd $(BACKEND_DIR) && PYTHONPATH=. .venv/bin/alembic stamp head

db-clear:
> cd $(BACKEND_DIR) && PYTHONPATH=. .venv/bin/python scripts/clear_db.py

health:
> curl http://127.0.0.1:8000/health

health-db:
> curl http://127.0.0.1:8000/health/db

vlm-health:
> @curl -fsS -H "Authorization: Bearer local-dev-key" http://127.0.0.1:8002/v1/models >/dev/null
> @echo "VLM is ready."

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

test:
> cd $(BACKEND_DIR) && PYTHONPATH=. .venv/bin/python -m unittest discover -s tests -p "test_*.py"

smoke:
> cd $(BACKEND_DIR) && PYTHONPATH=. .venv/bin/python scripts/smoke.py

status:
> git status

clean-pyc:
> find . -type d -name "__pycache__" -prune -exec rm -rf {} +
> find . -type f -name "*.pyc" -delete
