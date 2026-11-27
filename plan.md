# plan.md — spring-break build plan (5–6 days)

> Replanned 2026-11-25 (D23). The old 3-day plan assumed full-time focus and didn't survive a semester. This one assumes you're a student on break: real days, but not endless ones. **Finish line for this sprint: all five tools working locally in Claude Desktop, with tests.** HTTP, auth, deploy, and CI eval all move to the backlog at the bottom — they're real, just not this week's problem.

Code-first, same as before: **you write the code, then hand it to Claude for review** (`docs/CLAUDE.md`). The difference this time: fewer research/planning steps, more "open an editor and write a function" steps. Elicitation and deploy-host questions are already decided (D22) so you don't spend a day deciding instead of building.

**Rule:** if a step blows past 2× its time, stop, write down what's blocking, and move on. Cut order if you fall behind: cache → mini-eval → polish. Never cut tests.

---

## Day 1 — openFDA client + first tool's logic (no MCP yet) ✅ done 2026-11-26
Goal: a plain Python function that answers "is this drug recalled?" — provably, with tests, no network at test time.

1. **Commit the loose ends (10 min).** `git add -A && git commit` the doc updates already sitting in your working tree, so Day 1 starts from a clean slate.
2. **Build the openFDA client (1.5 h).** `openfda/client.py`: one function, e.g. `get(endpoint, search, limit, count=None)`. Uses the API key, a timeout, builds the query string. Turns failures into clear errors: `NotFound` (openFDA's 404 for zero matches), `RateLimited` (429), `UpstreamError` (5xx/timeout).
3. **Record fixtures (20 min).** Call it live once for drug recalls, for one drug from `docs/CORPUS.md`. Save the raw response to `tests/fixtures/drug_enforcement_<drug>.json`. Save one "no results" response too.
4. **Build `check_drug_recalls` logic (2 h).** `tools/drug_recalls.py` — plain function, no MCP. Input: product, optional manufacturer, optional lot number. Output: the shared envelope (`results`, `match_count`, `source`, `data_last_updated`, `data_limitations`, `disclaimer`). Ambiguous match with no manufacturer given → return a `needs_clarification` result (D22), not a guess.
   - **First, 15 min research (D24):** settle which parameters the tool accepts (manufacturer, lot, status, date; location optional) and the "ask only when the answer changes the result" rule. Add the one-firm fixture (e.g. metformin + Teva) for the no-question test. Report the true total as `match_count`, never just the page size.
5. **Tests (included above, not separate time).** `tests/test_drug_recalls.py` against fixtures only, no network: recall found, no recall found, lot match, ambiguous case.

6. **CI (20 min).** `.github/workflows/tests.yml`: on every push and pull request, install with `uv` and run `pytest`. No secrets needed, since tests use fixtures. Live checks and evals stay out of CI.

**Done when:** `uv run pytest` is green with zero network calls, and GitHub shows a green check on the push.

---

## Day 2 — First tool live in Claude Desktop
Goal: you ask Claude Desktop a real question and your code answers it.

1. **Wrap as an MCP server (1 h).** `server/main.py`: Prefect's FastMCP (D25), **stdio**, one tool (`check_drug_recalls`) calling your Day 1 function. Write a clear tool description — the LLM picks tools by reading it.
2. **Elicitation branch (45 min, D22 + D25 postscript).** For the ambiguous-firm case, three branches: client didn't declare elicitation → return `needs_clarification` as-is; client on protocol 2026-07-28 → return an `InputRequiredResult` and read the answer from `ctx.input_responses` on the retry; older protocol → `await ctx.elicit(...)`. Branch on what the client actually declared, never guess.
2b. **Manufacturer question refinements (1 h, D24 update 2026-11-27).** In `tools/drug_recalls.py`: `all_manufacturers` input; firm list via `count=recalling_firm.exact`, merged and ranked, capped at 8 + "Any manufacturer"; clause-list `build_search` (D26); store/pharmacy scope limitation. Record a `count` fixture. Tests first-class, as on Day 1.
3. **Smoke-test with the Inspector (20 min).** `npx @modelcontextprotocol/inspector`, call the tool by hand, confirm the envelope comes back, and confirm which elicitation branch the Inspector takes (it's a reference client, so it likely supports elicitation — good sanity check that your `elicit()` call itself works before trusting it with Claude Desktop).
4. **Connect to Claude Desktop (30 min).** Add the server to its config. Ask: "Is Tylenol recalled?", an ambiguous one, a junk product. **This is also your real answer to "does Claude Desktop support elicitation" — trust what you observe here, not a search result.** Note which branch it took in `DECISIONS.md` under D22 as a one-line postscript.
5. **Write down every miss** (wrong tool, misread output, dropped caveat) — these become your mini-eval set on Day 5.
6. **Commit + one `LEARNING_LOG.md` entry.**

**Done when:** Claude answers a real recall question using your server.

---

## Day 3 — Tools 2 and 3: food recalls + drug shortage
Same shape as Day 1–2, twice. These two don't depend on each other — do them in either order.

1. **`check_food_recalls` (1 h).** Same endpoint shape as drug recalls (`/food/enforcement`). Reuse Day 1's helpers; only pull out shared code once you've seen the duplication twice.
2. **`check_drug_shortage` (1.5 h).** Look at `/drug/shortages` and `/drug/drugsfda` for 2 drugs from `CORPUS.md`; match a shortage to FDA-rated equivalents via `te_code` (e.g. `AB`). Caveats: national, not local; equivalents are "ask your pharmacist," not a substitution order.
3. **Register both in `server/main.py`, verify in Claude Desktop.**
4. **Commit.**

**Done when:** tests green for both; both answer real questions in Claude Desktop.

---

## Day 4 — Tools 4 and 5: side-effect reports + cosmetic reports
Same pattern again. This is the riskiest pair for over-claiming, so the caveats matter more than the plumbing.

1. **`get_side_effect_reports` (1.5 h).** `count=patient.reaction.reactionmeddrapt.exact` on `/drug/event`. Optional `symptom` filter. Must carry `not_a_rate: true` plus the limits (no denominator, popularity/news bias, not proof of cause). **Write a test that fails if the caveats are missing** — not optional.
2. **`get_cosmetic_reports` (1 h).** `/cosmetic/event`, searched by brand/product only (D19, no ingredient data). Same caveat set plus "no ingredient-level data."
3. **Register both, verify in Claude Desktop.** Specifically check: does Claude still say "common side effect" despite the caveat? Note it either way.
4. **Commit + `LEARNING_LOG.md` entry.**

**Done when:** tests green for both; all **five** tools now work locally. This is the core deliverable — if the week ran out here, you'd already have a complete, demoable project.

---

## Day 5 — Cache, a small eval, polish
Goal: tie it off, don't open new scope.

1. **In-process TTL cache (1 h, cut first if behind).** Same query within N minutes skips the network call. Short TTL for recalls/shortages. Test: call twice, assert the second made no request.
2. **Mini eval, run by hand (1.5 h, cut second if behind).** Not the 40–60-query CI harness from the old brief — just 10–15 queries in a YAML/script, covering all five tools plus your Day 2 miss-notes (must include: a follow-up question that keeps the earlier product, e.g. "what about Cardinal Health?" after a Tylenol question; "any brand" in the first message → no question asked; "recalls at my CVS" → honest scope answer), scored by eye: right tool? right params? asked when ambiguous? caveats kept? Write down the score once. This is your before/after interview story, done cheaply.
3. **README + a short demo clip (1 h).** Who it's for, the 5 tools, one example conversation, "Roots: skipped, and why," your eval score.
4. **Commit.**

**Done when:** a stranger could read the README and understand (even if they can't run) the project.

---

## Day 6 — Buffer (use it, don't plan for it)
This day only exists because 5 tight days rarely survive contact with reality. If you're on schedule, use it for:
- Whatever slipped from Days 1–5 (most likely: the cache, or the mini eval).
- If genuinely ahead: switch the server to **Streamable HTTP** locally and confirm the Inspector still connects. That's it — no deploy, no auth, stop there.

If you're not ahead, just stop at Day 5's finish line. A working 5-tool local MCP server with tests is the deliverable, full stop.

---

## Explicitly out of scope for this sprint (real backlog, not a cut corner)
This is everything from Phase 5 of `docs/PROJECT_BRIEF.md`. It's legitimate follow-on work, and it's exactly where "scale and production" talking points come from for an interview — just not this week's job.
1. Deploy over HTTPS (pick a free Docker host, record the choice in `DECISIONS.md`).
2. OAuth via WorkOS AuthKit or Auth0 (D20) + per-user rate limits + privacy-safe access logs.
3. Retries with backoff + circuit breaker in the openFDA client.
4. Upstream rate budget across all users (D17).
5. Structured logs + metrics + tracing (OpenTelemetry).
6. Grow the eval set to 40–60 queries, move it into GitHub Actions, add LLM-as-judge for caveats.
7. Multiple instances behind a load balancer + Redis cache.
8. **More primary search keys (D26):** manufacturer-centric ("all Teva recalls") and date-centric ("recalls this month") searches, with `product` optional and "at least one key" required. Searches already use the clause-list pattern, so this is mostly new `if`s + tests.
9. Stretch: medication watchlist with new-recall alerts; more beauty-domain tools.

## Known risks to watch
- **openFDA matching is messy** (brand vs. generic names, lot numbers buried in free text). Expect most debugging time here — that's the real learning, budget for it.
- **Elicitation is already decided** (D22 + D25 postscript: branch on capability and protocol version) — don't re-open that question mid-week.
- **5 days is still tight against finals coming up.** If behind, cut in this order: Day 6 stretch → Day 5 cache → Day 5 mini-eval. Never cut a tool's tests.
