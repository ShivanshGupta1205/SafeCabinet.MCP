# CHANGELOG.md

One line per meaningful change, per docs/CLAUDE.md convention.

## 2026-11-01
- Recorded D20 (proposed): managed OAuth provider (WorkOS AuthKit or Auth0, decided in Phase 5) + privacy-safe access logging; added auth to the brief.
- Added `plan.md`: 15-step, 3-day build plan plus a scale & ops backlog.

## 2026-10-29
- Re-scoped to a consumer product-safety MCP server with five tools: drug recalls, food recalls, side-effect reports, drug shortages (+ FDA-rated equivalents), cosmetic reports (D15).
- Dropped Postgres/pgvector, embeddings and the ingestion pipeline; tools query openFDA live (D14).
- Recorded D14–D19 (no database, consumer tools, facts-and-limits output, scale design, recorded fixtures, cosmetic search by brand only); marked D2, D3, D5, D6, D7, D10, D11 superseded and noted D12/D13's new role.
- Rewrote `docs/PROJECT_BRIEF.md` around the five tools, shared output envelope, scale architecture and new phases.
- Updated `docs/CLAUDE.md` conventions; repurposed `docs/CORPUS.md` as the eval/fixture drug set; added a learning-log entry.

## 2026-08-30
- Pivoted subject from CDC clinical-guideline scraping to FDA drug information via the openFDA JSON API (see `docs/DECISIONS.md` D1).
- Switched to a code-first, learn-by-doing workflow; retired the teaching-project gate (D9).
- Repo hygiene: added `.gitignore`; untracked `.idea/` and `.DS_Store`.
- Trimmed `requirements.txt` (removed `pdfplumber`).
- Rewrote `docs/PROJECT_BRIEF.md` for the openFDA design (new schema, exact-lookup-first tools, elicitation core).
- Slimmed `docs/CLAUDE.md` to code-first operating rules.
- Repurposed `docs/LEARNING_LOG.md` from a gate table into a build/learning journal.
- Added `docs/DECISIONS.md` (decision log), seeded D1–D9.
- Recorded D10: ingest via API with local snapshot caching (`data/raw/`), not bulk downloads.
- Recorded D11: corpus unit is the product; keep several meaningful formulations per brand, dedupe versions to latest.
- Recorded D12: canonical record selection — prefer original packager, collapse repackagers, then newest `effective_time`.
- Recorded D13: label text needs a structural cleaning pass (strip HTML/bullets, drop `*_table`) before semantic indexing; no spell-correction.
- Added `docs/CORPUS.md`: curated 15-brand drug list (OTC + prescription); widened corpus target to ~15 brands / ~50–90 products (D11 updated).

## 2026-08-15
- Scaffolded empty repo structure (`ingestion/`, `db/`, `mcp_server/`, `eval/`, `tests/`) + pinned `requirements.txt`. No implementation — Phase 1 gate (M1–M3 in `docs/LEARNING_LOG.md`) not yet cleared.
- Restructured module folders under `src/clinical_guidelines_mcp/` (src layout) with `pyproject.toml` for package discovery; `tests/` kept at top level per convention.
- Added this `CHANGELOG.md`.
