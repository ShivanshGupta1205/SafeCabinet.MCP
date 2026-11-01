# CLAUDE.md — operating rules for this repo

Full spec: `PROJECT_BRIEF.md`. Why-we-chose-things: `DECISIONS.md`. Build/learning journal: `LEARNING_LOG.md`. Read the brief at the start of a session.

## How we work (code-first)
This is a **code-first, learn-by-doing** project. The teaching-project gate that governed earlier CDC work is **retired** (see DECISIONS.md D9).

- **The user implements first.** For a given piece, the user writes the real code themselves. Then they hand it to Claude to review, refine, correct, and explain how to improve — and to teach the underlying concept *from their actual code*.
- **Claude decides what to build, in what order, and with which tools** (architecture/sequencing), and guides. The user drives the keyboard on first implementation unless they explicitly hand a piece to Claude to write.
- Don't jump ahead and write a whole module the user meant to write themselves. When in doubt about who writes a piece, ask.

## Communication
Plain, student–teacher. Explain the "why" before the "what". Define a term the first time it's used. Short sentences, few ideas per paragraph. Being plain must not drop critical information. (Persisted in memory: `communication-style-plain`.)

## Conventions
- Python + official `mcp` SDK, managed with `uv` (`pyproject.toml` is the dependency source of truth). stdio → Streamable HTTP per `PROJECT_BRIEF.md`.
- Data comes **live from the openFDA JSON API** — no database, no scraping, no PDF parsing (DECISIONS.md D14). Store only data that is ours.
- Only the `openfda/` client knows openFDA URLs. Tools go through it.
- Every tool returns the shared output envelope, **including its data limitations** (D16). Tool names must not promise more than the data supports.
- Every tool needs a `pytest` test before it's considered done. Tests run against **recorded fixtures**, never live openFDA (D18). Live checks are separate and clearly marked.
- Keep `CHANGELOG.md` — one line per meaningful change, every session that ships something.
- Record notable choices in `DECISIONS.md` (short: context → decision → why).
- After building something, add a short entry to `LEARNING_LOG.md` (what was built, what it taught, what tripped us up).
- Don't silently deviate from the tool signatures or output envelope in `PROJECT_BRIEF.md`. If something looks wrong once you're building it, flag it and ask rather than quietly changing it.
