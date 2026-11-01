# LEARNING_LOG.md — build & learning journal

A running record of what got built, what concept it taught, and what tripped us up. This is code-first: we learn by building, then reflect here.

> History: this file started as a two-gate table (concept cleared / implementation understood) for the earlier CDC teaching-project workflow. That gate is retired (see DECISIONS.md D9). Kept as a journal because being able to *talk about what you learned* is worth a lot in interviews.

## How to use it
After building a meaningful piece, add an entry:

```
### <date> — <what you built>
- **Built:** one line on the actual thing (file/function/tool).
- **Concept it taught:** the idea you now understand because you built it.
- **Tripped me up:** the bug, confusion, or wrong turn — and how it resolved.
- **Could explain in an interview?** yes / not yet
```

## Entries

### 2026-08-30 — Project pivot (CDC → openFDA) + repo cleanup
- **Built:** Nothing runnable yet. Reset the repo for the new direction: cleaned junk, trimmed deps, rewrote the brief, added a decisions log.
- **Concept it taught:** Data-source quality decides project difficulty more than the concept does. A clean API (openFDA) beats scraping (CDC) for the same skills.
- **Tripped me up:** Spent a week on CDC theory with no code and a painful, structureless data source. Fix: code-first, and pick sources with real APIs.
- **Could explain in an interview?** yes (this is a good "what would you do differently" story)

### 2026-10-29 — Second pivot: consumer product-safety MCP server, no database
- **Built:** No code. Explored the openFDA endpoints (`explore.py`), researched existing openFDA products and MCP servers, then re-scoped: everyday consumers, five tools (drug recalls, food recalls, side-effect reports, shortages + equivalents, cosmetic reports), live queries instead of a database.
- **Concept it taught:** Start from a user and a problem, not from the tech you want to show. And: store only data that is yours. Copying a well-served API into your own database adds weight and, for recalls, makes data dangerously stale.
- **Tripped me up:** The database felt "production-grade" but wasn't serving the product. Also: adverse-event counts look like statistics but aren't rates (no denominator), so tools must ship their limits with the numbers (D16).
- **Could explain in an interview?** yes

<!-- next entry: Phase 1 — openFDA client + first fixtures -->
