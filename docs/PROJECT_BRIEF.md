# PROJECT_BRIEF.md — Consumer Product-Safety MCP Server (openFDA)

Read this alongside `CLAUDE.md` (operating rules), `DECISIONS.md` (why each choice was made) and `LEARNING_LOG.md` (build journal). This brief is the north star.

> Repo/package name is still `Clinical-Guidelines-MCP` / `clinical_guidelines_mcp` for now (DECISIONS.md D8). Revisit before public launch.

## What this is
An **MCP server for everyday people** that answers practical safety questions about the medicines, food and personal-care products in their home, using **live, official FDA data** from openFDA.

- *"Is my blood-pressure medicine recalled? Is my bottle's lot affected?"*
- *"The pharmacy says my prescription is backordered. Is it a national shortage, and what FDA-rated equivalents exist?"*
- *"I got a rash after starting this drug. Have other people reported that?"*
- *"Is this baby formula brand under a recall?"*
- *"Are there injury reports for this skincare brand?"*

The LLM handles the messy parts (reading a pasted medication list or a label photo, explaining legal recall language in plain words). The MCP tools supply the **hard facts**, so the LLM never has to guess them.

Not medical advice. openFDA's own disclaimer is carried in tool output and in the server prompt.

## Principles (each one is a decision in DECISIONS.md)
1. **Consumer-first** (D15). One kind of user, real problems, five focused tools.
2. **Live data, no database** (D14). Query openFDA per request; store only data that is ours.
3. **Facts and their limits** (D16). Every tool returns the caveats its data needs, so honest answers are the default.
4. **Elicitation is core** (D4). When a question is ambiguous (which manufacturer? which lot? which formulation?), the server asks before answering. This is a true MCP capability with no RAG equivalent.
5. **Built to scale** (D17). Stateless instances, shared cache, an upstream rate budget, resilience, observability.
6. **Reproducible tests and evals** (D18). Recorded openFDA responses (fixtures), not live data.

## Data source — openFDA (`https://api.fda.gov/`)
Clean JSON over HTTP. Free API key raises limits to 240 requests/min and 120,000/day per key. That budget is shared by every user of a hosted server (see D17).

| Endpoint | Records (Oct 2026) | Key fields | Used by |
|---|---|---|---|
| `/drug/enforcement.json` | ~18k (≈1.75k Class I) | `classification`, `status`, `reason_for_recall`, `recalling_firm`, `product_description`, `code_info` (lot numbers, free text), `distribution_pattern`, `recall_initiation_date` | `check_drug_recalls` |
| `/food/enforcement.json` | ~29.5k | same as drug, plus `more_code_info` | `check_food_recalls` |
| `/drug/event.json` (FAERS) | millions | `count=patient.reaction.reactionmeddrapt.exact` → ranked reaction counts | `get_side_effect_reports` |
| `/drug/shortages.json` | ~1.6k | `generic_name`, `status`, `availability`, `therapeutic_category`, `company_name`, `presentation`, `update_date` | `check_drug_shortage` |
| `/drug/drugsfda.json` | — | `products[].te_code` (therapeutic-equivalence code, e.g. `AB`), `brand_name`, `active_ingredients`, `marketing_status` | `check_drug_shortage` (equivalents) |
| `/cosmetic/event.json` | ~85.5k | `products[].product_name`, `reactions`, `outcomes`. **No ingredient lists** (D19). | `get_cosmetic_reports` |
| `/drug/label.json`, `/drug/ndc.json` | — | brand/generic names, `is_original_packager`, `product_ndc` | name resolution + canonical record selection (D12) |

Known data limits the tools must surface (D16):
- **Adverse-event counts** (FAERS, cosmetics) are voluntary reports. No denominator, so they are **not rates**. They are skewed by popularity, news and lawsuits, and they never prove cause.
- **Shortages** are national. They can't say whether a local pharmacy is out.
- **Lot numbers** live inside free text (`code_info`). Matching is best-effort and must say so.
- **US products only.** No foreign brand names, and no off-label uses (absent from labels by definition).

## The five tools
```python
check_drug_recalls(product: str, manufacturer: str | None = None, lot_number: str | None = None)
check_food_recalls(brand: str, product: str | None = None, lot_number: str | None = None)
get_side_effect_reports(drug: str, symptom: str | None = None, top_k: int = 10)
check_drug_shortage(drug: str)                     # includes FDA-rated equivalents via te_code
get_cosmetic_reports(brand_or_product: str, top_k: int = 10)
```
Signatures are a starting point. Refine them while building, and record changes in DECISIONS.md.

| Tool | When it elicits (asks the user first) | Must-carry caveats |
|---|---|---|
| `check_drug_recalls` | Several manufacturers/products match → "Which manufacturer is on your bottle?" Recall found but no lot given → "What's the lot number on the label?" | Lot matching is best-effort; "no recall found" ≠ "safe"; data freshness |
| `check_food_recalls` | Brand matches many products → "Which product/size?" | Same as drug recalls |
| `get_side_effect_reports` | Name maps to several distinct drugs/formulations | Not a rate; not proof of cause; reporting bias; talk to a clinician |
| `check_drug_shortage` | Ingredient has several formulations/strengths in shortage | National, not local; equivalents are options to ask a pharmacist about |
| `get_cosmetic_reports` | Brand vs. specific product unclear | Same as side effects; no ingredient-level data |

### Shared output envelope
Every tool returns the same outer shape, so the LLM and the evals can rely on it:
```json
{
  "query": {"...": "the resolved inputs actually used"},
  "results": ["... tool-specific items ..."],
  "match_count": 0,
  "source": "openFDA /drug/enforcement",
  "data_last_updated": "2026-10-28",
  "data_limitations": ["..."],
  "disclaimer": "Not medical advice. ..."
}
```

## MCP capabilities
| Primitive | Build? | Notes |
|---|---|---|
| Tools | Core | The five above |
| Elicitation | Core | Per the table above |
| Prompts | Yes, 1–2 | e.g. `medicine_cabinet_check` (walk a pasted medication list through recalls + shortages); carries the disclaimer |
| Resources | Lean / optional | e.g. a static "how to read these results" guide the client can load |
| Sampling | Stretch | Design for it; don't depend on client support |
| Roots | Skip, explicitly | No reason to browse the client's filesystem. Say so in the README |

## Architecture
```
MCP client (Claude Desktop, any MCP client)
        │  stdio (local dev)  →  Streamable HTTP (remote)
        ▼
Load balancer
        ▼
MCP server instances — stateless, N copies
  server/  : tool registration, elicitation, prompts, auth, per-client rate limit
  tools/   : one module per tool — resolve input → query → shape output + caveats
  openfda/ : the ONLY code that knows openFDA URLs — httpx, timeouts,
             retries + backoff, circuit breaker, upstream rate budget
  cache/   : TTL cache (in-process locally → Redis when multi-instance)
        ▼
openFDA API

Telemetry: structured logs + metrics + traces (OpenTelemetry)
Evals: scripted MCP client replaying recorded fixtures, run in CI
```

### Target code layout
```
src/clinical_guidelines_mcp/
  openfda/   client.py (+ response models)
  tools/     drug_recalls.py, food_recalls.py, side_effects.py, shortages.py, cosmetics.py
  cache/
  server/    MCP wiring + entry point
  eval/      golden-set runner
tests/
  fixtures/  recorded openFDA responses (D18)
```
The old `db/` and `ingestion/` packages go away. `ingestion/explore.py` is the exploration spike; its learnings move into `openfda/`.

## Evals
A scripted MCP client (not the Claude Desktop UI) runs a hand-written golden set of 40–60 queries against fixtures, scoring separately:
- **Tool selection**: did it pick the right tool?
- **Parameter extraction**: did it fill the inputs correctly (e.g. pull the manufacturer out of a pasted label)?
- **Answer correctness**: exact match on structured facts (recall class, status, counts).
- **Elicitation precision**: asks on the ambiguous subset, and only there.
- **Caveat compliance**: the final answer keeps the limits (never turns report counts into "common", never calls "no recall found" "safe"). LLM-as-judge with a fixed rubric.
- **Latency**, plus cache hit rate under the replay.

Golden-set products come from `docs/CORPUS.md`. Runs in GitHub Actions on push.

## Tech stack
- Python ≥ 3.11, official `mcp` SDK, managed with `uv` (`pyproject.toml` + `uv.lock`)
- `httpx` for openFDA
- Cache: in-process TTL → Redis
- `pytest` with recorded fixtures; eval harness in GitHub Actions
- Docker; deploy behind a load balancer
- OpenTelemetry for traces/metrics; structured JSON logs
- Auth (HTTP only): OAuth 2.1 via a managed provider, WorkOS AuthKit or Auth0, decided in Phase 5 (D20). Privacy-safe access logs (D20).

## Phases (code-first)
1. **openFDA client.** One small client: build queries, timeouts, typed errors (not found / rate limited / upstream down). Record the first fixtures. Builds directly on `explore.py`.
2. **First tool end-to-end: `check_drug_recalls`.** Running in Claude Desktop over stdio, with elicitation (manufacturer, lot), the shared envelope and caveats, and pytest on fixtures. This proves the whole path before widening.
3. **Remaining four tools.** Food recalls → shortages (+ equivalents) → side-effect reports → cosmetic reports.
4. **Evals.** Golden set, scripted client, CI. Measure before optimizing.
5. **Scale and ops.** Streamable HTTP, stateless instances, cache (in-process → Redis), upstream rate budget, retries/circuit breaker, OAuth via managed provider + per-user rate limits + privacy-safe access logs (D20), Docker, load-balanced deploy, observability.
6. **Stretch.** Medication watchlist with new-recall alerts (first data that is truly ours → small store, per D14), more beauty-domain tools, sampling.
