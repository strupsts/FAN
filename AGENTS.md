# F.A.N. coding-agent instructions

## Project overview

F.A.N. is a receipt-to-personal-finance application. The backend is a FastAPI modular monolith organized with light hexagonal architecture, using SQLAlchemy and PostgreSQL. The frontend is an Ionic Angular application packaged with Capacitor. Backend OpenAPI schemas generate frontend TypeScript types, and runtime interface localization uses Transloco.

Implement only the behavior in scope. Check the current code and tests before treating roadmap or historical documentation as implemented.

## Architecture boundaries

- `backend/app/domain` and `backend/app/application` are the core. Keep framework and persistence concerns out of them.
- Application use cases depend on contracts in `backend/app/ports`, not FastAPI, SQLAlchemy, or concrete external services.
- Inbound FastAPI routes in `backend/app/adapters/inbound` translate HTTP input/output and delegate to use cases; keep them thin.
- Outbound adapters in `backend/app/adapters/outbound` implement ports.
- `AppContainer` in `backend/app/infrastructure/container.py` is the composition root for adapters and use cases.
- Treat generated OpenAPI types as authoritative for frontend API contracts. Do not add duplicate handwritten response interfaces for new or changed API boundaries.
- Server-owned values, including the current user ID and system-created or system-updated timestamps, must not be accepted from request bodies.

## Current-user boundary

- Authentication is not implemented. The shared FastAPI dependency in `backend/app/adapters/inbound/api/dependencies.py` currently resolves the configured development user ID.
- User-owned routes must obtain identity through `get_current_user_id`; do not hardcode IDs in routes or accept a user ID from a request body.
- Keep application and domain code independent of authentication providers.
- Production Google OAuth is still required before an external beta.

## Localization rules

- English (`en`) and Russian (`ru`) are the initial supported interface languages; English is the fallback.
- `interface_language` and `formatting_locale` are independent preferences. Do not infer one from the other.
- Preserve merchant and item names in their source language and script. Extraction must not translate source receipt evidence.
- Keep translation-key parity between `frontend/src/assets/i18n/en.json` and `ru.json`.
- Use Transloco keys for visible UI strings instead of adding new hardcoded text in components or templates.
- Preserve document `lang` and `dir` handling and RTL-safe layout foundations even though the currently enabled languages are LTR. Never mirror receipt images.

## Money and date rules

- Use `Decimal` in backend money calculations and string amounts in JSON API contracts. Never use binary floating point for money.
- Preserve the original receipt amount and currency; display localization or future conversion must not mutate stored source values.
- Do not nominally add or compare amounts in different currencies. Until FX projections exist, totals must remain separated by original currency.
- Use canonical ISO-compatible forms for purchase dates and API timestamps. Locale-aware display formatting must not alter persisted values.
- The migration toward these rules is not complete: legacy CAD defaults, two-decimal assumptions, and related older models still exist. Change them only in a focused task with corresponding contract, persistence, and test updates.

## Development workflow

- Make one focused task per commit and include only task-related files.
- Inspect current implementations, tests, and every call site before changing a shared signature or contract.
- Prefer focused edits over replacing an existing file wholesale.
- Inspect `git status` and relevant diffs before work, preserve all pre-existing uncommitted changes, and leave the tree clean between completed tasks.
- Review generated output, but regenerate it through project commands rather than editing it manually.
- Current code and tests are the implementation truth. Documentation may describe desired or historical states.
- ADRs record architectural reasoning and history. They may be superseded; do not use them as an implementation journal or treat them as infallible descriptions of current code.

## Required verification

Run checks relevant to the touched areas, and run the full required set before pushing a cross-layer change. Make targets assume WSL, `backend/.venv`, and the repository's configured Node environment.

```bash
# Backend unit tests
make test

# SQLAlchemy/Alembic migration drift
make db-check

# Regenerate OpenAPI artifacts and fail on contract drift
make api-contracts-check

# Frontend production build and lint
make frontend-build
make frontend-lint

# Frontend Jasmine/Karma tests
cd frontend
npm test -- --watch=false --browsers=ChromeHeadless
```

When WSL has no Linux Chrome binary, this environment-specific fallback has worked with an existing Windows Edge installation; it is not a universal requirement:

```bash
cd frontend
CHROME_BIN=/mnt/c/PROGRA~2/Microsoft/Edge/Application/msedge.exe npm test -- --watch=false --browsers=ChromeHeadless
```

Also run `git diff --check` before committing.

## Git safety

- Never discard pre-existing uncommitted work.
- Unless the user explicitly authorizes the exact destructive operation, do not use `git reset --hard`, `git clean`, `git restore` or `git checkout` in a way that discards work, force push, rewrite published history, or amend an earlier commit.
- Inspect status and diffs first. Commit only task-related files.
- Push only after all required checks pass.
- Do not write to GitHub directly through APIs. Work through the local repository and normal Git commands.

## Generated files

These files are generated from the backend FastAPI OpenAPI schema and must not be hand-edited:

- `frontend/openapi/openapi.json`
- `frontend/src/app/core/api/generated/openapi-types.ts`

Use `make api-schema` and `make frontend-api-types` to regenerate them together as needed, preferably through `make api-contracts`. Use `make api-contracts-check` to regenerate and verify drift.

## Completion report

For every coding task, report:

- files changed;
- architectural decisions made;
- verification commands run and exact test results;
- commit SHA and push result;
- final Git status;
- remaining risks or assumptions.
