# Biome Scope Definition

## Canonical Scope
Biome governs all maintained frontend TypeScript and JavaScript code:
- `src/**/*.ts`
- `src/**/*.tsx`
- `tests/**/*.ts`
- `tests/**/*.tsx`
- `scripts/**/*.mjs`
- `scripts/**/*.js`

## Exclusions
1. `src/api/generated/**`
   - **Reason**: Machine-generated OpenAPI / Orval contract client. Generated code is immutable; modifying it manually violates rule 7 of `00_START_HERE.md`.
2. `node_modules/**`, `.next/**`
   - **Reason**: Dependencies and build artifacts.
