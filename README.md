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

## Development environment

The supported development host is Windows 11 with WSL2 and Ubuntu 24.04 LTS.
Native Ubuntu 24.04 LTS is also supported as a Linux foundation. From Ubuntu:

```bash
make provision
make doctor
make dev
```

Provisioning asks for confirmation and defaults to **No**. For automation, use
`make provision YES=1` with non-interactive sudo already configured. See
[docs/provisioning.md](docs/provisioning.md) for the clean Windows bootstrap,
profiles, external cache placement, GPU prerequisites, Android, and recovery.

## Architecture

The backend is organized around:

- `domain` — product entities and business rules.
- `application` — use cases / scenarios.
- `ports` — contracts required by the application.
- `adapters` — concrete implementations such as FastAPI, Surya OCR, Qwen, Postgres.
- `infrastructure` — configuration and dependency wiring.
