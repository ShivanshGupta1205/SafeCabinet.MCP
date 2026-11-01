# plan.md — 3-day build plan

Code-first. Build → test → see what breaks → fix → note it in `docs/LEARNING_LOG.md`.
Each step has one clear output and a "done when" check. Times are targets, not promises.
**Rule:** if a step blows past 2× its time, stop, write down what's blocking, and cut scope. Don't sink the day into it.

Who writes what: **you write the code first**, then hand it to Claude for review (per `docs/CLAUDE.md`).

---

## Day 1 — One tool, working end to end

The goal for today: Claude Desktop answers "is my medicine recalled?" using *your* server.

### Step 1 — Setup (30 min)
- Get a free openFDA API key. Put it in `.env` (already gitignored), and add a `.env.example` with the variable name only.
- Add `mcp` and `pytest` to `pyproject.toml` via `uv add`. Delete `requirements.txt` (pyproject is the source of truth).
- Create the target folders: `openfda/`, `tools/`, `server/`, `tests/fixtures/`. Remove `db/`. Keep `explore.py` for now as reference.
- **Done when:** `uv run python -c "import mcp, httpx"` works.

### Step 2 — Research: does Claude Desktop support elicitation? (20 min)
- Check the current MCP docs/client support table. Elicitation is a core feature (D4), so we need to know *now* whether the main client can show it.
- Decide the fallback if it can't: the tool returns a `needs_clarification` result listing the options, and the LLM asks the user.
- **Done when:** one line in `DECISIONS.md` saying "elicitation: native" or "elicitation: fallback until supported".

### Step 3 — Build the openFDA client (1.5 h)
- `openfda/client.py`: one function, e.g. `get(endpoint, search, limit, count=None)`.
  - Uses the API key, a timeout, and builds the query string.
  - Turns failures into **clear errors**: `NotFound` (openFDA returns 404 for zero matches), `RateLimited` (429), `UpstreamError` (5xx / timeout).
- **Test:** call it live once for drug recalls, for one drug from `CORPUS.md`. Save that raw response to `tests/fixtures/drug_enforcement_<drug>.json`. Also save one "no results" response.
- **Done when:** a live call returns data; a junk search raises `NotFound`, not a crash.

### Step 4 — Build tool 1 logic: `check_drug_recalls` (2 h)
- `tools/drug_recalls.py`: a plain Python function, **no MCP yet**. Input: product, optional manufacturer, optional lot number. Output: the shared envelope from the brief (`results`, `match_count`, `source`, `data_last_updated`, `data_limitations`, `disclaimer`).
- Each result: classification, status, reason, firm, recall date, product description.
- Lot matching: simple "does the lot appear in `code_info`?" check, labelled best-effort.
- Ambiguity: if several different firms match and no manufacturer was given, return a clarification result instead of guessing.
- **Test:** `tests/test_drug_recalls.py` runs against the fixtures (no network): a recall found, no recall found ("no recall found" ≠ "safe" caveat present), lot match, ambiguous firms.
- **Done when:** `uv run pytest` is green with zero network calls.

### Step 5 — Wrap it as an MCP server (1 h)
- `server/main.py`: an MCP server (official SDK) over **stdio** with one tool, `check_drug_recalls`, that calls your Step 4 function. Write a clear tool description: the LLM picks tools by reading these.
- Add elicitation (or the Step 2 fallback) for the ambiguous-firm case.
- **Test:** run it with the MCP Inspector (`npx @modelcontextprotocol/inspector`) and call the tool by hand.
- **Done when:** the Inspector shows the tool and returns a real envelope.

### Step 6 — Connect to Claude Desktop (30 min)
- Add the server to Claude Desktop's config. Ask in plain English: "Is Tylenol recalled?", then an ambiguous one, then a junk product.
- Write down every time Claude picks the wrong tool, misreads the output, or drops a caveat. These become eval cases on Day 3.
- **Done when:** Claude answers a recall question from your tool's data.
- **End of Day 1:** commit, plus a `LEARNING_LOG.md` entry.

---

## Day 2 — The other four tools

Each tool repeats the Day 1 pattern: **save fixtures → plain function → tests → register in server → try in Claude Desktop.** Steps 7–10 don't depend on each other, so you can do them in any order.

### Step 7 — `check_food_recalls` (1 h)
- Same endpoint shape as drug recalls (`/food/enforcement`). Reuse your Step 4 helpers. If you're copy-pasting a lot, pull shared bits into a helper, but only now that you've seen the duplication twice.
- **Done when:** tests green, and the tool works in Claude Desktop.

### Step 8 — `check_drug_shortage` (1.5 h)
- Research first (15 min): look at `/drug/shortages` and `/drug/drugsfda` records for 2 drugs in `CORPUS.md`. Figure out how to match a shortage to equivalents via `te_code` (e.g. `AB` = FDA-rated equivalent).
- Build: shortage status + availability + equivalents. Caveats: national, not local; equivalents are "options to ask your pharmacist about".
- **Done when:** tests green; one shortage case and one no-shortage case verified.

### Step 9 — `get_side_effect_reports` (1.5 h)
- Uses `count=patient.reaction.reactionmeddrapt.exact` on `/drug/event`. Optional `symptom` filter.
- This is the tool most likely to mislead (D16). Output must include `not_a_rate: true` and the limits: no denominator, popularity/news bias, not proof of cause.
- **Test:** a test that *fails* if the caveats are missing.
- **Done when:** tests green; in Claude Desktop, check whether Claude still says "common side effect". Note it if it does.

### Step 10 — `get_cosmetic_reports` (1 h)
- `/cosmetic/event`, searched by brand/product name only (D19). Return top reactions and outcomes, with the same caveats as side effects plus "no ingredient-level data".
- **Done when:** tests green, and the tool works in Claude Desktop.

### Step 11 — Add a cache (1 h)
- An in-process TTL cache inside the openFDA client: the same query within N minutes doesn't hit openFDA again. Use short TTLs for recalls and shortages.
- **Test:** call twice, and assert the second call made no network request.
- **Done when:** tests green. (Redis comes later, only if we run multiple copies.)
- **End of Day 2:** commit, plus a learning-log entry. You now have a complete local product.

---

## Day 3 — Prove it works, then put it online

### Step 12 — Small eval harness (2.5 h)
- Write 20 golden queries in `eval/golden.yaml`, starting from your Day 1–2 notes. Cover every tool, a few ambiguous cases (should ask), and a few side-effect questions (must keep caveats).
- `eval/run.py`: a scripted MCP client that sends each query through an LLM connected to your server and records which tool was called, with what inputs, and the final answer. Score:
  - tool selection
  - parameters
  - asks-when-ambiguous
  - caveats kept (a simple keyword check first; LLM-as-judge later)
- **Done when:** one command prints a score table. **Fix the worst failure** (usually a tool description), re-run, and write down the before/after numbers. That before/after is your best interview story.

### Step 13 — Switch to HTTP (1 h)
- Run the same server over **Streamable HTTP** locally. Keep the server stateless (no per-user data in memory).
- **Test:** the Inspector connects over HTTP, and all five tools work.
- **Done when:** the HTTP server works locally.

### Step 14 — Research + deploy (1.5 h)
- Research (20 min): pick a free host that runs a Docker container over HTTPS (e.g. Fly.io, Render, Google Cloud Run). Record the choice in `DECISIONS.md`.
- Write a `Dockerfile`, deploy, and set the openFDA key as a secret.
- **Done when:** Claude Desktop (or the Inspector) connects to the public URL and calls a tool.
- ⚠️ Until auth is added, keep the URL private or use a simple shared secret, so strangers can't burn your openFDA budget.

### Step 15 — README + demo (1 h)
- README: who it's for, the 5 tools, an example conversation, the design principles (live data, facts + limits, elicitation), eval scores, and "Roots: skipped, and why".
- Record a short GIF/video of Claude Desktop using it.
- **Done when:** a stranger could understand and try it from the README alone.

---

## After day 3 — Scale & ops backlog (in priority order)
Pick these up one at a time; each is independent.
1. **OAuth** via WorkOS AuthKit or Auth0 (D20) + per-user rate limits + privacy-safe access logs.
2. Retries with backoff + circuit breaker in the openFDA client.
3. Upstream rate budget across all users (D17).
4. Structured logs + metrics + tracing (OpenTelemetry).
5. Eval harness in GitHub Actions; grow golden set to 40–60; LLM-as-judge for caveats.
6. Multiple instances behind a load balancer + Redis cache.
7. Stretch: medication watchlist with new-recall alerts; more beauty-domain tools.

## Known risks to watch
- **Elicitation client support** (Step 2): if missing, use the fallback. Don't block on it.
- **openFDA matching is messy** (brand vs. generic names, lot numbers in free text). Expect most of your debugging here; that's the real learning.
- **3 days is tight.** If behind schedule, cut in this order: cosmetic tool → cache → deploy. Never cut tests or the eval.
