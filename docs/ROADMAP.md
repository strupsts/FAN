# Roadmap

## Phase 1: Clean backend skeleton

- Create backend structure.
- Add architecture docs.
- Add minimal FastAPI health route.
- Keep old prototype code untouched.

## Phase 2: Domain and ports

- Add receipt domain models.
- Add OCR, parser, storage, repository, analytics, and privacy ports.

## Phase 3: Use cases

- Add ProcessReceiptUseCase.
- Add ConfirmReceiptUseCase.
- Add receipt history use case.
- Add spending summary use case.

## Phase 4: Adapters

- Add LocalImageStorageAdapter.
- Add SuryaOCRAdapter.
- Add QwenReceiptParserAdapter.
- Add Postgres repositories.

## Phase 5: API routes

- Add receipt processing route.
- Add receipt confirmation route.
- Add history route.
- Add summary route.

## Phase 6: Legacy cleanup

- Move useful old code into new adapters/use cases.
- Delete obsolete prototype files.
- Remove hardcoded credentials and user_id.
