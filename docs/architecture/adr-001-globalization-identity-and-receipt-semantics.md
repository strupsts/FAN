# ADR-001: Globalization, identity, and receipt semantics

- Status: Accepted
- Date: 2026-07-29
- Branch: `feat/globalization-foundation`

## Context

F.A.N. must support multiple users, languages, countries, currencies, receipt formats, and tax presentation styles without rewriting confirmed receipt history or the core use cases.

The current MVP is functional, but several temporary assumptions are unsafe for international use:

- one development user is used for every request;
- `CAD` is an implicit default in the domain, API, database, and frontend;
- money is treated as always having two decimal places;
- receipt totals are recalculated as item totals plus tax;
- frontend API models are duplicated manually from backend schemas;
- visible UI strings are currently written directly in components and templates.

This ADR defines stable product and architecture invariants. It intentionally does not implement a worldwide tax engine, authentication provider, exchange-rate provider, or every translation.

## Decisions

### 1. A confirmed receipt is the original financial fact

A confirmed receipt stores the purchase in its original transaction currency.

The receipt total is authoritative:

```text
receipt.total = the amount the user actually paid
```

The application must not silently overwrite `total` with a calculated value such as `items_total + tax`.

Calculated amounts are used only for reconciliation and review hints.

### 2. Tax is informational in the MVP

The MVP keeps optional printed `subtotal` and `tax` values but does not implement country-specific tax legislation or tax analytics.

No warning is shown when at least one supported reconciliation scenario matches within a currency-aware tolerance:

```text
items_total ≈ receipt_total
items_total + printed_tax ≈ receipt_total
printed_subtotal + printed_tax ≈ receipt_total
```

If none matches, saving remains allowed. The UI shows a quiet informational indicator explaining that the difference may come from discounts, fees, tips, deposits, rounding, missing items, or extraction errors.

Tax never controls the authoritative receipt total.

### 3. One transaction currency per receipt

A confirmed receipt has exactly one transaction currency. The following values must use the same currency:

- receipt total;
- optional subtotal;
- optional tax;
- every item total;
- every unit price.

Different receipts belonging to the same user may use different currencies.

Dual-currency information printed on a receipt is not represented by mixing item currencies. It may later be stored as separate reference or conversion information.

### 4. Currency may be unresolved in a draft, but not in a confirmed receipt

A receipt draft may have no resolved currency.

Currency resolution states are:

- `detected`: explicit and sufficiently unambiguous evidence was found on the receipt;
- `inferred`: currency was inferred from user preferences, country context, merchant context, or ambiguous symbols;
- `user_selected`: the user selected or corrected the currency;
- `unknown`: currency could not be resolved.

A symbol such as `$` alone is not sufficient evidence for `detected`.

When the receipt currency is missing, the user's default receipt currency may be applied as `inferred`. The UI must communicate this quietly and allow correction.

Confirmation is blocked only when the transaction currency remains `unknown`.

### 5. User regional preferences are independent values

The application must not collapse language, locale, country, and currency into one setting.

Each user has independent preferences:

- interface language;
- formatting locale;
- home country;
- default receipt currency;
- reporting currency;
- time zone;
- onboarding completion state.

During the first MVP onboarding, a single "Primary currency" choice may initialize both `default_receipt_currency` and `reporting_currency`. They remain separate fields and may later be changed independently.

Device-local preferences are available before authentication and offline. Server-side user preferences become canonical after authentication and synchronization.

### 6. Identity is a boundary, not a hard-coded provider

All user-owned data and use cases remain scoped by `user_id`.

The API obtains the current user through an identity boundary. Development may use a deterministic dev user adapter. Google authentication will later replace the inbound identity adapter without changing receipt use cases or domain entities.

Before external beta, user isolation must be covered by tests using at least two distinct users.

### 7. Currency conversion is a separate projection

The original receipt amount and currency are never replaced by a converted amount.

Exchange-rate results are stored separately as immutable conversion snapshots associated with a receipt and target reporting currency. A receipt may have multiple conversion snapshots for different target currencies.

A conversion snapshot may include:

- source amount and currency;
- target amount and currency;
- exchange rate;
- requested rate date;
- actual rate date;
- provider;
- retrieval timestamp;
- status.

Changing a user's reporting currency does not rewrite receipts. It may create or reuse another conversion snapshot.

An unavailable exchange-rate provider must not block receipt confirmation. The receipt is saved first, and conversion work may remain pending and retry later.

Before FX support is implemented, summaries must group totals by original currency rather than add unlike currencies.

### 8. Dates are canonical in storage and unambiguous in the UI

The purchase date and time extracted from a receipt represent the merchant-local value printed on the receipt unless stronger timezone evidence exists.

The API uses canonical ISO-compatible values.

User-facing dates must be locale-aware and use a textual month form where practical, for example:

```text
10 June 2026
10 июня 2026 г.
10 juin 2026
```

Ambiguous numeric-only dates are not used for normal user-facing history and details views.

A confirmed receipt requires a purchase date. If extraction cannot resolve it, the review UI asks the user to provide it.

### 9. Original receipt text is preserved

Merchant and item names are preserved in the source language and script.

The extraction model must not translate receipt text as part of extraction. Universal product categories and budget buckets remain language-independent identifiers.

Future normalized or translated names, if added, are separate fields and never replace the original text.

### 10. Localization is runtime-capable and RTL-ready

The mobile application uses one build capable of switching interface language at runtime.

The localization foundation must support:

- lazy-loaded translation packs;
- English fallback;
- translation-key completeness checks;
- locale-aware dates, numbers, and currencies;
- dynamic document `lang` and `dir`;
- left-to-right and right-to-left layouts;
- long translated labels;
- scripts with different line-height and wrapping requirements.

English and Russian are the first complete translation packs. Other languages are added incrementally without changing component architecture.

RTL readiness is implemented before enabling Arabic, Hebrew, Persian, or Urdu in production. Receipt images are never mirrored.

### 11. Icons reduce language load but do not replace meaning blindly

The UI should prefer familiar, intuitive icons where they reduce repeated text, especially for navigation and common actions.

However:

- critical financial actions and validation states must not rely on an icon alone;
- icon-only controls require accessible names;
- unfamiliar icons require a tooltip, popover, or nearby explanation;
- icons must remain understandable in both LTR and RTL layouts;
- directional icons use semantic start/end behavior where appropriate;
- destructive actions require explicit confirmation.

Icons supplement localization; they are not a substitute for accessibility or clear financial meaning.

### 12. Backend schemas are the API contract source of truth

FastAPI/Pydantic schemas are the source of truth for HTTP request and response contracts.

TypeScript API types are generated from the OpenAPI schema rather than maintained as a second manual copy.

The first implementation generates types only. API service methods may remain handwritten.

Generated files must be reproducible through repository commands and checked for drift in development or CI.

### 13. Money and quantity use decimal-safe representations

Money arithmetic uses decimal values, never binary floating-point.

The domain does not provide an implicit `CAD` default.

Database precision must support currencies and intermediate calculations without forcing every value to two decimal places. User-facing precision is determined by currency metadata and locale formatting.

Receipt quantities use a decimal-safe representation because weighted and measured items may contain fractional quantities.

### 14. Country configuration is versioned and non-authoritative

The application ships with a bundled baseline country and currency catalog so first launch works offline.

A newer version may later be downloaded from the backend, validated by schema and version, and cached.

Country configuration may provide defaults and hints such as:

- default currency;
- suggested locales;
- suggested languages;
- time zones;
- common receipt tax labels.

Country configuration is not treated as authoritative tax legislation and must not silently determine receipt totals.

### 15. Multilingual evaluation is a product requirement

Receipt extraction quality must be measured across countries, languages, currencies, scripts, and receipt layouts.

The evaluation set will include at least:

- explicit, inferred, ambiguous, and missing currency cases;
- tax-inclusive and tax-exclusive presentation;
- multiple scripts and mixed-language receipts;
- poor image quality, rotation, shadows, folds, and long receipts;
- weighted items, discounts, deposits, tips, fees, and rounding;
- merchant, date, total, subtotal, tax, item, currency, JSON validity, and latency metrics.

Model or prompt changes must be evaluated against this set before release.

## Initial implementation order

1. Generate TypeScript API types from FastAPI OpenAPI.
2. Add users and user regional preferences.
3. Introduce the current-user boundary and two-user isolation tests.
4. Add runtime localization, locale formatting, and RTL test mode.
5. Remove implicit `CAD` assumptions and make receipt currency explicit.
6. Preserve authoritative totals and implement tax-neutral reconciliation hints.
7. Add regional onboarding.
8. Build History and Receipt Details on the new contracts.
9. Add per-currency Summary.
10. Add FX provider, conversion snapshots, and pending conversion jobs.
11. Add unified reporting-currency Summary.
12. Add production authentication before external beta.

## Consequences

### Positive

- Historical receipts remain stable when reporting preferences or exchange rates change.
- Different currencies are never added dishonestly.
- Localization and identity changes remain outside receipt business rules.
- The MVP avoids a worldwide tax engine while preserving future tax data.
- New languages and authentication providers can be added through adapters and configuration.
- OpenAPI type generation reduces backend/frontend contract drift.

### Costs

- Several existing `CAD` defaults and two-decimal assumptions require migration.
- The receipt review UI needs explicit currency and date validation.
- Summaries remain grouped by currency until FX support is implemented.
- RTL and long-text testing add frontend test cases even before every language is enabled.

## Explicitly deferred

- worldwide tax rates and legal tax rules;
- tax analytics;
- multiple detailed tax lines;
- production Google or Apple authentication;
- live FX conversion during receipt confirmation;
- every planned translation pack;
- automatic translation of merchant or item text.
