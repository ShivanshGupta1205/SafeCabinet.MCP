# DECISIONS.md — decision log

Short records of *why* the major choices were made. Format per entry: **context → decision → why**. These exist so the reasoning survives, and so it can be explained in an interview instead of shrugged at.

Status values: `accepted` (in force), `superseded` (replaced by a later entry), `proposed` (not yet committed).

---

### D1 — Data source: openFDA, not CDC scraping — `accepted`
- **Context:** Original plan scraped CDC/WHO/NIH web pages and PDFs. CDC has no clean data feed; a week was lost fighting the website structure.
- **Decision:** Use the openFDA JSON API as the data source.
- **Why:** Clean, structured JSON over HTTP; no scraping or PDF parsing; reliable and reproducible. The MCP/retrieval skills are identical; only the source changes.

### D2 — Curated/pinned corpus, not a crawler — `superseded by D14, D15`
- **Context:** Could auto-discover drugs, or hand-pick a set.
- **Decision:** Pin a deliberately chosen set of ~15–30 drugs across a few therapeutic areas.
- **Why:** The eval harness needs a fixed, reproducible corpus. Production systems pin clinical sources too. Framed as "deliberately scoped," never "comprehensive."

### D3 — Exact-lookup tools are core; semantic search is secondary — `superseded by D15` (exact-first still holds; the semantic leg is dropped)
- **Context:** Leading with semantic search makes the project look like plain RAG.
- **Decision:** Build the exact-lookup tools (structured facts, adverse-event counts, recalls) first; treat semantic search over label text as the secondary leg.
- **Why:** Exact lookups from structured data are what make this MCP-and-not-RAG, and they're safer for facts like dosages (no fuzzy guessing).

### D4 — Elicitation promoted from stretch to core — `accepted`
- **Context:** Elicitation (server asks the client a clarifying question) was originally a stretch goal.
- **Decision:** Make it a core feature (drug/product/population disambiguation).
- **Why:** It's an MCP capability with no RAG equivalent — the clearest proof the project is genuinely MCP.

### D5 — Structured facts are extracted from JSON, never hand-typed — `superseded by D14` (still never hand-typed; now read live per request instead of ingested)
- **Context:** A human hand-entering a dosage table is data entry, not engineering, and it would undercut the "not just RAG" claim.
- **Decision:** Ingest structured facts programmatically from openFDA JSON (`/drug/ndc`, `/drug/event`). Humans only QA a sample.
- **Why:** Demonstrates a real extraction pipeline; scales; keeps the structured leg honest.

### D6 — Local embeddings, not a paid API — `superseded by D14` (no semantic search, so no embeddings)
- **Context:** Semantic search needs an embedding model.
- **Decision:** Use a local sentence-transformers model (small BGE variant).
- **Why:** No paid API, deliberate cost/tradeoff choice; keeps the project self-contained.

### D7 — Postgres + pgvector for storage — `superseded by D14`
- **Context:** Need to store structured facts and vector embeddings together.
- **Decision:** Single Postgres database with the pgvector extension.
- **Why:** One store for both structured (exact) and vector (semantic) data; production-standard; avoids running a separate vector DB.

### D8 — Keep the repo/package name for now — `superseded by D21`
- **Context:** Subject changed from clinical guidelines to FDA drug info; repo is `Clinical-Guidelines-MCP`.
- **Decision:** Keep `Clinical-Guidelines-MCP` / `clinical_guidelines_mcp` for now.
- **Why:** Drug labels are clinical information (defensible), and renaming later is cheap enough. Revisit before public launch.

### D9 — Code-first process; teaching-project gate retired — `accepted`
- **Context:** The strict "learn fully in a teaching project, prove it, then build" gate produced deep theory but zero code in a week.
- **Decision:** Switch to code-first / learn-by-doing. User implements first; Claude refines and teaches from the real code.
- **Why:** Building-then-learning is faster and sustains motivation; the old gate optimized understanding at the cost of ever shipping.

### D10 — Ingest via the API with local snapshot caching, not bulk downloads — `superseded by D14, D18` (API-not-bulk still holds; snapshots become recorded test fixtures, not the source of truth)
- **Context:** openFDA offers both a live query API and full bulk dataset downloads. The corpus is small and curated (~15–30 drugs), and the eval harness needs reproducible data.
- **Decision:** Fetch each curated drug from the API and save ("snapshot") the raw JSON responses to `data/raw/` (gitignored). Everything downstream reads from those snapshots, not the network. Bulk downloads are not used.
- **Why:** Targeted (fetch only our drugs, not GBs of data), reproducible (snapshots don't change under us, so the eval harness sees identical data every run), keeps the API-only `count=` aggregation for adverse events, and makes ingestion testable offline against saved fixtures. Bulk download would only win for a whole-dataset or very large corpus, which this isn't — revisit if the corpus grows to that scale. Implemented as a fetch-and-cache boundary in `client.py`.

### D11 — Corpus unit is the product, with multiple formulations per brand; versions deduped — `superseded in part by D14` (no `drugs` rows anymore; the product-vs-brand insight still drives elicitation, and `CORPUS.md` becomes the eval drug set)
- **Context:** A brand like "Tylenol" maps to many openFDA label records. Those records are two different kinds: (a) genuinely different *products/formulations* (Extra Strength 500 mg, Regular Strength 325 mg, 8 HR Arthritis 650 mg ER, Children's liquid) and (b) repeated *label versions* of the same product (same `spl_set_id`, different `effective_time`, or repackagers).
- **Decision:** The corpus unit is the **product**, not the brand. Keep **several meaningfully-different formulations per brand** — differing by strength, form/release, or population/indication — and **skip cosmetic near-duplicates** (caplet vs gelcap, package size). **Dedupe label versions** to the latest `effective_time`, grouped by `spl_set_id`. Each product is its own `drugs` row (`drug_id` = `spl_set_id`); `brand_name` is a shared attribute `find_drug` groups on. Target **~15 brands/categories** × a few formulations each (deliberately widened on user request, ~2026-08-30) ≈ **50–90 products**, mixing OTC and prescription. The curated brand list lives in `docs/CORPUS.md`.
- **Why:** Multiple real formulations give users genuine options *and* create the natural ambiguity that makes `find_drug` + elicitation meaningful (a single product per brand would rarely trigger a clarifying question). Different formulations also have different max doses, so disambiguating is the *safe* behavior, not a nicety. Deduping versions removes noise that would otherwise give the exact-lookup tools several near-identical answers with no clear "the" answer.
- **Note:** "Dedupe by `spl_set_id`" alone is insufficient — the same medicine also appears under *different* `spl_set_id`s via repackagers and multiple package sizes. Canonical-record selection is refined in D12.

### D12 — Canonical record selection: prefer original packager, collapse repackagers, then newest — `accepted`
- **Context:** Even `brand_name.exact:"TYLENOL Extra Strength"` returned three records that are the *same medicine* (500 mg acetaminophen) but different `spl_set_id`/`product_ndc`: the original Kenvue product (`50580-449`, `is_original_packager: true`), a repackage by Select Consumer Group (`85237-1946`, with `original_packager_product_ndc: 50580-449`), and a second Kenvue package size (`50580-108`). Sorting `effective_time:desc` and taking the top record picks the *repackager* (Jun 27) over the original manufacturer (Jun 15). Separately: `meta.last_updated` is the dataset rebuild date and is unrelated to any label's `effective_time`, so a June label inside an Aug dataset is expected, not stale.
- **Decision:** When selecting the one canonical record for a product: (1) **prefer `is_original_packager: true`** over repackagers; (2) **collapse repackagers onto their original** via `original_packager_product_ndc` so copies don't count as separate products; (3) **only then** pick the newest `effective_time`. Do not choose by newest `effective_time` alone. Group/identify by the original `product_ndc`, not raw `spl_set_id`.
- **Why:** A repackager re-filing later shouldn't outrank the real manufacturer's label; the original packager is the authoritative, usually cleaner source. This keeps one clean canonical record per real product and stops repackaged copies from inflating the corpus or splitting a drug into look-alike duplicates.
- **Note (after D14):** Still in force, but applied **at request time** when a tool picks one record out of live openFDA results, instead of at ingestion.

### D13 — Label text needs a cleaning pass before semantic indexing — `accepted (dormant)` — no semantic index after D14; the cleaning rule still applies to any tool that returns label or recall free text to the client
- **Context:** Real openFDA label text contains typos and OCR-style garbage (observed: "common col", "toothach", "andchildren", "PRINICIPAL DISPALY PANEL"), inconsistent bullet characters (`■`), and embedded HTML in the `*_table` fields.
- **Decision:** Add a **text-cleaning step** in `normalize.py` before section text is stored/embedded: strip HTML, normalize whitespace and bullet glyphs, and drop the `*_table` HTML fields. Do **not** attempt to fix spelling (risk of corrupting clinical terms) — just normalize structure. Preferring the original packager (D12) also tends to yield cleaner text.
- **Why:** Garbage and markup degrade semantic-search quality and make stored sections unreadable. Structural normalization is safe and high-value; spell-correction on clinical text is risky and out of scope. This is a future step (Phase 1 normalize / Phase 3 embeddings), recorded now so it isn't forgotten.

---

*D14–D19 record the 2026-10-29 pivot: from a curated-corpus database project to a consumer-facing MCP server that queries openFDA live.*

### D14 — No database; query openFDA live at request time — `accepted`
- **Context:** The database existed to hold a curated corpus, embeddings for semantic search, and an extracted-facts table. After the consumer pivot (D15), users ask about *any* product, the tools are live lookups, and openFDA already does the searching and counting on its own servers.
- **Decision:** Drop Postgres/pgvector and the ingestion pipeline. Each tool call queries openFDA directly. **Store only data that is ours** (e.g. a future user watchlist, our own logs), never a copy of data openFDA already serves well. If such data appears, start with the smallest store that fits (SQLite/Redis), not a mirror.
- **Why:** Simpler, so effort goes into the MCP server, which is the product. **Freshness is a safety property here**: recalls and shortages change weekly, and a stale local copy could miss a Class I recall. Mirroring an API without a reason is also a weak engineering signal.
- **Costs accepted:** dependence on openFDA uptime and rate limits, network latency, and being limited to openFDA's keyword query language. These are covered by caching and resilience (D17) and recorded fixtures (D18).

### D15 — Target user: everyday consumers; five tools — `accepted`
- **Context:** Starting from "what tech can I show" produced a generic project. Starting from "who struggles, and with what" produces a product. The user's market research into existing openFDA products and MCP servers found these consumer use cases under-served.
- **Decision:** Target everyday people managing their household's medicines, food, and personal-care products. Five tools:
  1. `check_drug_recalls` — is my medicine recalled, and is my lot affected?
  2. `check_food_recalls` — is this food/brand recalled?
  3. `get_side_effect_reports` — what have people reported for this drug (with honest caveats)?
  4. `check_drug_shortage` — is it in national shortage, and which FDA-rated equivalents exist (`te_code`)?
  5. `get_cosmetic_reports` — what injury reports exist for this cosmetic brand/product?
  The cosmetic tool deliberately serves a slightly different user, which leaves room to grow a beauty-domain tool set later.
- **Why:** A specific user with specific problems makes the tools useful and the project's story clear. Recalls are the strongest, most factual, least risky use case, so they're built first.
- **Rejected:** a foreign/off-label drug cross-referencer. openFDA covers only US products (no foreign-name mapping, so the mapping would come from the LLM's memory), and off-label uses are by definition absent from the label.

### D16 — Tools return facts *and their limits* — `accepted`
- **Context:** Some openFDA data is easy to over-read. FAERS and cosmetic adverse-event counts are voluntary reports: no denominator (how many people took it), heavily influenced by drug popularity, news and litigation, and never proof of cause. openFDA itself says to "assume all results are unvalidated." A bare "412 reports" invites the LLM to say "common side effect."
- **Decision:** Every tool's output carries the caveats its data needs, as structured fields the LLM must see (e.g. `data_limitations`, `not_a_rate: true`), plus the data's freshness (`last_updated`). Tool names must not promise more than the data supports (hence `get_cosmetic_reports`, not `audit_cosmetic_safety`). Suggestions such as equivalent generics are framed as "options to ask your pharmacist about," never instructions.
- **Why:** The LLM can only be as honest as what the tool hands it. Putting the limits inside the tool output makes honest answers the default instead of relying on the model to remember.

### D17 — Built for scale: stateless server, shared cache, upstream budget, resilience, observability — `accepted`
- **Context:** Without a database, the project's engineering weight moves to serving the MCP server reliably to many users. openFDA allows 240 requests/minute and 120,000/day per API key, and that budget is shared by every user of a hosted server.
- **Decision:**
  - **Transport:** stdio for local dev → Streamable HTTP for remote.
  - **Stateless instances:** no per-user state inside a server process, so N copies can run behind a load balancer and scale horizontally.
  - **Caching:** in-process TTL cache locally → shared cache (Redis) once there are multiple instances. TTLs set per data type (recalls/shortages short, stable data longer).
  - **Upstream rate budget:** a limiter that keeps total openFDA traffic under the key's limits; requests coalesced and cached rather than duplicated. Do **not** rotate multiple API keys to get around limits (against openFDA's terms).
  - **Resilience:** timeouts on every call, retries with backoff for transient errors, a circuit breaker when openFDA is down, and clear "data source unavailable" results to the LLM instead of crashes.
  - **Client-side protection:** per-client rate limiting and API-key auth for the MVP; OAuth 2.1 only if it becomes genuinely multi-tenant.
  - **Observability:** structured logs, metrics (latency, cache hit rate, upstream errors, elicitation rate), tracing (OpenTelemetry).
- **Why:** These are the production skills an MCP server actually needs, and they replace the database as the project's engineering showcase.

### D18 — Recorded fixtures for tests and evals — `accepted`
- **Context:** Live data changes, so tests and evals can't depend on it. D10's snapshot idea solved reproducibility for a corpus that no longer exists.
- **Decision:** Record real openFDA responses once and save them as **fixtures** (committed test data under `tests/fixtures/`). Unit tests and the eval harness replay fixtures with no network. A separate, clearly-marked live smoke test checks that openFDA's response shapes haven't changed.
- **Why:** Deterministic, fast, offline tests and evals; the eval golden set always sees identical data. `CORPUS.md` becomes the drug list for the golden set and fixtures.

### D19 — Cosmetic reports are searched by brand/product, not ingredient — `accepted`
- **Context:** The cosmetic adverse-event records (`/cosmetic/event.json`, ~85.5k reports) list only `product_name` and `role` per product. They contain no ingredient lists.
- **Decision:** `get_cosmetic_reports` searches by brand/product name. Ingredient-level questions ("is this chemical risky?") are explicitly out of scope for this data, and the tool says so instead of guessing.
- **Why:** The data can't support ingredient claims; pretending otherwise would break D16.

### D20 — Public HTTP server uses a managed OAuth provider; privacy-safe access logging — `proposed` (final pick during scale & ops)
- **Context:** The server will be public over HTTP. We want records of who accessed it, and per-user fair use of the shared openFDA budget (D17). Building login ourselves is risky. This updates D17's "API key for MVP" line: a public server for anyone is multi-tenant, so OAuth is in scope.
- **Decision:** The MCP server is only an OAuth 2.1 **resource server** (it validates tokens, including the audience check). A managed provider is the **authorization server**. It must support CIMD (preferred) or DCR, so MCP clients can register automatically. Social logins (Google/GitHub) are offered *inside* the provider, never used as the authorization server directly. OAuth applies to the HTTP transport only; stdio stays credential-free per the spec. Candidates, decided when Phase 5 starts:
  - **WorkOS AuthKit:** CIMD + DCR; free tier ~1M MAU. Most generous, MCP-oriented.
  - **Auth0 (Okta):** CIMD + DCR ("Auth for MCP" GA May 2026); free tier 25k MAU. Most recognizable name.
  - (Considered: Stytch, with DCR and partial CIMD, ~10k MAU free. Keycloak: free, but self-hosting auth defeats the purpose.)
  Free-tier numbers to be re-verified on vendor pricing pages at decision time.
- **Logging rule:** log user ID, time, tool, latency, outcome, elicitation flag. Do **not** tie raw query text (drug names, symptoms) to identity by default; keep any query samples for debugging/evals separate and anonymized. Set a retention limit (30–90 days) and publish a short privacy policy.
- **Why:** Identity enables per-user rate limits, access records and the future watchlist. Managed auth avoids building security-critical code. The logging rule keeps us from holding personal health data tied to identity.

### D21 — Project name: SafeCabinet — `accepted`
- **Context:** The old name (`Clinical-Guidelines-MCP`) described the abandoned CDC project. The product now covers medicines, food and cosmetics for everyday users, so drug-only ("Rx") names no longer fit either.
- **Decision:** Name the project **SafeCabinet**. Distribution name `safecabinet` in `pyproject.toml`; import package `src/safecabinet/`. GitHub repo rename is done separately in GitHub settings.
- **Why:** It pictures the user's own cabinets (medicine, kitchen, bathroom), which covers all five tools. It was unused on PyPI and GitHub when checked (2026-11-01). It avoids "FDA" in the name, which could look like an official FDA product.
