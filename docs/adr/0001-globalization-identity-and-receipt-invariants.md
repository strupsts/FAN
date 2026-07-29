# ADR 0001: Globalization, identity, and receipt invariants

- Status: Accepted
- Date: 2026-07-29

## Context

F.A.N. is moving from a single-user, Canada-first prototype toward a multinational mobile product. The current implementation contains assumptions that would become expensive to remove after History, Summary, Settings, and authentication are built:

- `CAD` is an implicit default in the domain, database, and frontend.
- Monetary values are treated as two-decimal "cents" values.
- The review form recalculates and overwrites the receipt total from item totals and tax.
- The API currently resolves every request to one development user.
- Frontend API models are duplicated manually from backend schemas.
- UI strings and layouts are not yet governed by localization rules.

The goal is to establish stable boundaries now without building a global tax engine, translating every screen, or integrating production authentication prematurely.

## Decision

### 1. Receipt total is authoritative

`receipt.total` represents the amount the user actually paid. It must never be silently overwritten from item totals, subtotal, or tax.

Item totals, printed subtotal, and printed tax are used only for reconciliation and review assistance.

For MVP, a receipt is considered reconciled when at least one expression matches the authoritative total within a currency-aware tolerance:

1. `items_sum ~= total`
2. `items_sum + printed_tax ~= total`
3. `printed_subtotal + printed_tax ~= total`

If none match, saving remains allowed. The UI shows a quiet informational indicator explaining that discounts, fees, tips, deposits, rounding, or missing items may account for the difference.

### 2. Tax remains informational for MVP

`subtotal` and `tax` remain optional receipt fields. F.A.N. may extract, store, display, and allow correction of them, but they do not drive the authoritative total and are not used for tax analytics in MVP.

A jurisdiction-aware tax engine, tax rates, tax lines, and legal tax interpretation are explicitly out of scope for this phase.

### 3. One transaction currency per receipt

A confirmed receipt has exactly one transaction currency. The same currency applies to:

- total;
- subtotal, when present;
- tax, when present;
- every item total;
- every unit price.

Different receipts owned by the same user may use different currencies.

Currency may be absent in an extracted draft, but it is required before confirmation.

Currency resolution is represented explicitly:

- `detected`: supported by explicit receipt evidence;
- `inferred`: assumed from user preferences or contextual evidence;
- `user_selected`: selected or corrected by the user;
- `unknown`: unresolved and not confirmable.

An ambiguous symbol such as `$` is not sufficient by itself to mark a currency as detected.

### 4. Original receipt money is immutable financial evidence

The original amount and transaction currency are never replaced by converted values.

Currency conversion is a separate projection associated with a receipt. A receipt may have multiple conversions for different target currencies or providers.

A future conversion record will contain at least:

- receipt identifier;
- source amount and currency;
- target amount and currency;
- exchange rate;
- requested and actual rate dates;
- provider;
- retrieval timestamp;
- status.

Changing the user's reporting currency creates or selects another conversion projection; it does not mutate the receipt.

Receipt confirmation must not depend on an external FX service. If conversion is unavailable, the receipt is saved and a database-backed conversion job may remain pending for retry.

### 5. Multi-currency reporting is honest by construction

Before FX conversion exists, Summary groups totals by transaction currency and never adds unlike currencies.

After FX support is added, the primary Summary may show one reporting-currency total with an expandable breakdown of original currencies and conversion details.

Historical conversion snapshots are retained so old reports do not change when current exchange rates change.

### 6. User regional preferences are independent values

The following preferences are distinct and must not be collapsed into a single country setting:

- interface language;
- formatting locale;
- home country;
- default receipt currency;
- reporting currency;
- time zone;
- onboarding completion state.

The first onboarding flow may present a simplified "primary currency" choice that initially sets both default receipt currency and reporting currency. They remain separate fields internally and can be separated in Settings later.

User preferences are available locally before authentication and synchronized with server-side preferences after authentication.

### 7. Identity is a boundary, not a hard-coded UUID

Application use cases continue to receive a resolved user identifier and remain unaware of Google, Apple, JWTs, or other authentication details.

The current development user becomes one implementation of the current-user boundary. Production authentication adapters are added later without changing receipt use cases.

All user-owned queries and mutations must be covered by two-user isolation tests.

### 8. Date semantics are explicit

The purchase timestamp represents the local merchant time printed on the receipt unless stronger evidence is available. It must not be presented as invented UTC.

Purchase date is required before confirmation because History ordering and historical FX conversion depend on it.

API and persistence use canonical ISO-compatible values. User-facing dates use locale-aware month names, for example `10 June 2026`, and avoid ambiguous all-numeric formats.

### 9. Money and quantity use decimal semantics

Backend monetary amounts and quantities use decimal representations, never binary floating point.

Currency must be explicit when constructing confirmed money values. Implicit `CAD` defaults are removed.

Persistence precision is widened to support international currencies and exchange-rate calculations. API decimal values remain strings to avoid precision loss across JSON and JavaScript.

### 10. Localization is runtime-configurable

User-facing strings are referenced through translation keys rather than hard-coded in components.

The application supports runtime language switching, English fallback, lazy-loaded translation packs, and locale-aware formatting for dates, numbers, and currencies.

English and Russian are the first complete language packs. Additional languages are enabled only after required translation keys are complete and the relevant layouts are tested.

Merchant names and item names are preserved in their original receipt language. The VLM must not silently translate source evidence. Universal category identifiers remain language-independent.

A multilingual receipt evaluation set is required before claiming support for additional receipt languages or countries.

### 11. Layouts are internationalization-ready

New layout code uses logical directions such as `inline-start` and `inline-end` instead of assuming left-to-right placement.

The application can switch the document `lang` and `dir` attributes. RTL test mode is supported before Arabic, Hebrew, Persian, or Urdu language packs are publicly enabled.

Receipt images are never mirrored.

Icons may reduce translation pressure only when their meaning is widely understood. Financially significant, destructive, or ambiguous actions must not rely on an unlabeled icon. Icon-only controls require an accessible name and, where useful, a tooltip or contextual explanation.

### 12. Backend schemas are the API contract source of truth

FastAPI OpenAPI output is used to generate frontend TypeScript request and response types.

The Angular API service may remain handwritten initially, but duplicated handwritten interface definitions are phased out. Generated files are reproducible and checked for drift in development or CI.

## Project workflow agreement

The assistant may read and analyze the repository through GitHub but does not write directly to active GitHub branches.

All repository changes are performed locally by the user from explicit instructions, including ADR updates. The assistant supplies the ADR patch or command together with the related implementation instructions so that documentation and code can be committed atomically.

This includes:

- creating or deleting branches;
- creating or editing source files;
- updating this ADR;
- generating migrations;
- installing dependencies;
- staging changes;
- committing;
- pushing;
- merging.

This prevents the remote branch from moving ahead while the user has local work and avoids unnecessary pulls or merge conflicts.

Unapproved proposals and unverified assumptions must not be recorded as completed work. The implementation journal records meaningful decisions and verified milestones rather than every terminal command.

## Out of scope for this decision

- country-by-country tax rates or legal tax advice;
- production Google or Apple authentication;
- a full set of translated language packs;
- production FX provider integration;
- bank-statement reconciliation;
- tax analytics;
- a message broker such as RabbitMQ or a distributed task system.

## Implementation order

1. Add reproducible OpenAPI-to-TypeScript type generation.
2. Add users, user preferences, and the current-user boundary.
3. Add runtime localization, locale formatting, and RTL test foundations.
4. Remove implicit currency defaults and enforce one currency per confirmed receipt.
5. Preserve authoritative totals and implement tax-neutral reconciliation.
6. Add regional onboarding.
7. Build History and receipt details on the new contracts.
8. Build Summary grouped by original currency.
9. Add FX ports, conversion snapshots, retries, and reporting-currency Summary.
10. Add production authentication before external beta.

## Implementation journal

### 2026-07-29: Globalization branch and ADR

- Working branch: `feat/globalization-foundation`.
- Globalization, identity, currency, tax-reconciliation, localization, and API-contract invariants were accepted in this ADR.

### 2026-07-29: OpenAPI export foundation verified locally

The user created `backend/scripts/export_openapi.py`. It imports `create_app()`, calls `app.openapi()`, and writes deterministic formatted JSON to `frontend/openapi/openapi.json`.

Verified generated schema:

- OpenAPI version: `3.1.0`;
- API title: `F.A.N. API`;
- exported paths: 6;
- `/api/receipts/confirm`;
- `/api/receipts/history`;
- `/api/receipts/process`;
- `/api/receipts/summary`;
- `/health`;
- `/health/db`.

Verification results:

- generated JSON parsed successfully;
- backend test suite: 15 tests passed;
- Ionic/Angular production build succeeded;
- only `backend/scripts/export_openapi.py` and `frontend/openapi/` were untracked at this checkpoint;
- the implementation files had not yet been committed.

### 2026-07-29: OpenAPI-to-TypeScript generation verified locally

The user installed `openapi-typescript` `7.13.0` as a frontend development dependency and generated `frontend/src/app/core/api/generated/openapi-types.ts` from the exported OpenAPI document.

Verified results:

- generated TypeScript file: 465 lines;
- receipt, money, summary, validation, path, and operation types were present;
- Angular production build succeeded;
- Angular lint succeeded;
- backend test suite: 15 tests passed;
- implementation changes were still uncommitted at this checkpoint.

The generated file is treated as derived output. It must not be edited manually because regeneration replaces its contents. Uncomfortable generated types are corrected at the authoritative backend schema or adapted through a handwritten frontend alias/facade layer.

Dependency-install output also reported 36 npm audit findings and pending install-script approvals. Their production impact has not yet been classified; audit review is required before this implementation block is committed.

### 2026-07-29: OpenAPI-to-TypeScript generation completed

The API contract generation pipeline was implemented locally:

- `backend/scripts/export_openapi.py` exports deterministic FastAPI OpenAPI JSON;
- `frontend/openapi/openapi.json` stores the generated schema;
- `openapi-typescript` version `7.13.0` generates frontend TypeScript definitions;
- `frontend/package.json` provides the `api:types` command;
- the Makefile provides `api-schema`, `frontend-api-types`, `api-contracts`, and `api-contracts-check`;
- the generated TypeScript file contains 465 lines at this checkpoint.

Verification results:

- two consecutive generations produced identical SHA-256 hashes;
- production dependency audit reported zero vulnerabilities;
- the full development dependency audit reported 36 issues;
- no forced dependency upgrade was applied because it could introduce breaking changes;
- backend test suite: 15 tests passed;
- Ionic/Angular production build succeeded;
- frontend lint succeeded.

The implementation was ready for its first source commit at this checkpoint.

### 2026-07-29: User domain foundation completed

The initial user domain foundation was added:

- `User` represents the provider-independent FAN user;
- `UserPreferences` stores interface language, formatting locale, home country, default receipt currency, reporting currency, time zone, onboarding state, and update timestamp;
- Google, Apple, OAuth tokens, and provider-specific identities remain outside the core user model;
- country codes are normalized to two uppercase ASCII letters;
- currency codes are normalized to three uppercase ASCII letters;
- user and preference timestamps must be timezone-aware;
- no implicit Canadian or CAD defaults were introduced into the domain model.

Verification results:

- user preference normalization tests passed;
- invalid country and currency tests passed;
- non-ASCII lookalike codes were rejected;
- naive user timestamps were rejected;
- backend test suite: 21 tests passed;
- generated API contracts remained unchanged.

## Consequences

This decision adds a small amount of schema and contract work before more product screens are built. In exchange, receipts remain stable financial facts while identity, display language, reporting currency, FX providers, and future tax features can evolve independently.
