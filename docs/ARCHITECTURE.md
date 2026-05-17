# Architecture

F.A.N. uses a light hexagonal architecture.

## Core

### Domain

Domain contains product concepts and rules:

- Receipt
- ReceiptItem
- Category
- Money
- Correction
- Summary

Domain must not import FastAPI, database libraries, OCR libraries, LLM clients, or external services.

### Application

Application contains use cases:

- ProcessReceiptUseCase
- ConfirmReceiptUseCase
- GetReceiptHistoryUseCase
- GetSpendingSummaryUseCase

Use cases orchestrate the flow and depend on ports, not concrete tools.

## Ports

Ports define what the application needs from the outside world:

- OCRPort
- ReceiptParserPort
- ReceiptRepositoryPort
- ImageStoragePort
- AnalyticsPort
- PrivacyRedactorPort

Ports are contracts. They do not contain external service logic.

## Adapters

Adapters implement ports or bring requests into the application.

Inbound adapters:

- FastAPI routes

Outbound adapters:

- OCR
- LLM receipt parser
- Postgres repositories
- Local image storage
- Analytics storage
- Privacy redaction

## Infrastructure

Infrastructure wires the application together:

- config
- dependency container
- logging
