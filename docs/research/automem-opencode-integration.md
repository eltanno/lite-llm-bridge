# AutoMem → OpenCode Integration Plan

**Date:** 2026-05-21
**Status:** Planned (design agreed). Execution is part of the OpenCode spike.
**Context:** Migrating the terminal daily driver to OpenCode (see `coding-agent-comparison.md`). Every stack component is officially supported on OpenCode and installs **unedited** — GSD (`--opencode` installer), Superpowers (plugin line), Impeccable (prebuilt `.opencode` skill), context-mode (shipped OpenCode plugin) — **except AutoMem's auto-firing hooks**. AutoMem ships integrations for Claude Code, Cursor, and Codex only; there is **no OpenCode plugin** ([upstream PLUGIN_INSTALLATION.md](https://github.com/verygoodplugins/mcp-automem/blob/main/PLUGIN_INSTALLATION.md), verified 2026-05-21). This is the one bespoke piece in the whole migration.

---

## What ports unedited

- **AutoMem MCP server** (`@verygoodplugins/mcp-automem`): a standard stdio MCP server → declare it in `opencode.json` under the `mcp` key. `recall_memory` / `store_memory` / `update_memory` / `associate_memories` become callable tools on OpenCode. Same backend (`AUTOMEM_URL` + token) as the Claude Code install — no data migration. **Zero edits.**

The gap is purely the **auto-firing** that Claude Code provided via shell hooks.

---

## What we reproduce (the two Claude Code hooks)

1. **`automem-session-start.sh` — recall.** Injects an `<automem_session_context>` block instructing the agent to call `recall_memory` before its first substantive response. It *prompts* recall; it does not recall itself.
2. **`save-transcript-memory-v2.sh` (SessionEnd + PreCompact) — synthesis.** Backgrounds a worker that: extracts `User:`/`Assistant:` text from the transcript → distills it into discrete memories via `claude -p --model sonnet` (free on Max) using a detailed extraction prompt (importance scoring, type detection, secret redaction) → POSTs each memory to the AutoMem REST API. Chunked fallback if the LLM call errors.

OpenCode has no shell-hook system; it uses TS/JS plugins. Both behaviors collapse into **one small OpenCode plugin**.

---

## Design

### Part 1 — Recall
Thin OpenCode plugin hooks the session-start equivalent (`session.created` / system-prompt injection — the same mechanism Superpowers and context-mode already use on OpenCode) and injects the existing `<automem_session_context>` block verbatim. The model then calls the `recall_memory` MCP tool exactly as today.

### Part 2 — Synthesis
The same plugin hooks the session-end + pre-compact equivalents. On fire:
1. Read the transcript from OpenCode's session store (via the `client` object passed to plugins); write it to a temp file in the simple `User:/Assistant:` shape the existing script already parses.
2. Shell out (OpenCode plugins have shell access), **backgrounded**, to a lightly-adapted copy of `save-transcript-memory-v2.sh`.

### Decisions made
- **Synthesis engine:** `opencode run` with **qwen 3.6** — model-agnostic, no dependency on Claude Code / Max staying installed (consistent with the reason for migrating). Replaces the `claude -p --model sonnet` invocation.
  - ⚠️ **Verify** the exact model ID + provider against the live catalog when wiring OpenCode auth. Do not trust the training-data name (project lesson: the deepseek-v4-pro / qwen3-coder-next episode).
- **Recall:** plugin injection (mirrors current behavior, reliable), **not** an AGENTS.md instruction.
- **Build:** thin TS plugin + adapted bash core — minimizes edits to AutoMem's proven logic.

### Reused verbatim (NOT edited) from `save-transcript-memory-v2.sh`
- Distillation prompt (importance 0.3–0.9, type detection, format rules)
- Secret redaction (regex safety net)
- REST POST to `AUTOMEM_URL` with bearer token (payload shape, tags, `metadata.session_id`)
- Dedup via `/tmp` markers (incl. per-compact counter)
- Backgrounding (return immediately; don't block session exit)
- Chunked fallback when the LLM call errors

### Edits required — the entire bespoke surface
1. **New:** one OpenCode TS plugin (`~/.config/opencode/plugin/automem.*`) — two triggers: session-start → inject recall block; session-end/pre-compact → export transcript + invoke synthesis.
2. **Adapted in the bash script (two boundaries only):**
   - **transcript source** — read the plugin-exported file instead of Claude's `transcript_path` JSONL.
   - **synthesis CLI** — `opencode run --model <qwen-3.6-id>` instead of `claude -p --model sonnet`.

Nothing else changes.

---

## Verify at build time
- OpenCode's exact **session-end + pre-compact event names** and the **transcript-read API**.
  - **Reference (proven, official):** context-mode's shipped OpenCode plugin at `~/.claude/plugins/marketplaces/context-mode/src/adapters/opencode/plugin.ts` already does session capture, compact snapshots (`experimental.session.compacting`), and system injection (`experimental.chat.system.transform`). Copy the pattern.
  - OpenCode may not emit a clean "SessionEnd" — it has `session.idle` / `session.deleted`. May need an idle-based surrogate (context-mode uses a surrogate for session-start similarly).
- Exact **qwen 3.6 model ID + provider** against the live catalog.
- `AUTOMEM_URL` / `AUTOMEM_TOKEN` available in the OpenCode plugin environment.

---

## Fits into: the OpenCode spike
Install OpenCode → install the stack (GSD `npx get-shit-done-cc --opencode --global`, Superpowers plugin line, Impeccable `.opencode` skill, context-mode plugin + MCP, AutoMem MCP block) → **build this AutoMem plugin** → log in (ChatGPT Plus) → run a real GSD planner→executor→verifier flow → confirm recall fires on start and synthesis fires on compact/end.
