# F.A.N.

F.A.N. is a receipt-to-spending clarity app.

Current goal: rebuild the backend as a clean modular monolith using light hexagonal architecture.

## MVP flow

1. User uploads a receipt image.
2. Backend stores the image.
3. OCR extracts text from the image.
4. LLM parses receipt text into structured data.
5. User reviews and corrects the draft.
6. System saves confirmed receipt data.
7. System stores prediction/correction pairs for future evaluation and training.
8. User can view transaction history and spending summary.

## Architecture

The backend is organized around:

- `domain` — product entities and business rules.
- `application` — use cases / scenarios.
- `ports` — contracts required by the application.
- `adapters` — concrete implementations such as FastAPI, Surya OCR, Qwen, Postgres.
- `infrastructure` — configuration and dependency wiring.
