# Spike Manifest

## Idea

Migrate the terminal daily driver from Claude Code to **OpenCode** while keeping the existing workflow stack running — GSD, Superpowers, Impeccable, AutoMem, context-mode. Use **official, unedited** components everywhere they exist; the only bespoke code is a small OpenCode plugin for AutoMem's auto-behavior. Prove it works end-to-end on a non-Anthropic backend (ChatGPT / Ollama). Full design: `docs/research/coding-agent-comparison.md` + `docs/research/automem-opencode-integration.md`.

## Requirements

_Locked decisions — non-negotiable for the build._

- **Official, unedited stack components wherever they exist.** Minimal bespoke code.
- **Additive install.** OpenCode's config lives in `~/.config/opencode` (separate from `~/.claude`). Claude Code stays installed and untouched. `~/.claude` backed up before any GSD install → `~/claude-config-backup-20260521-183404.tgz`.
- **OpenCode must run with `OPENCODE_DISABLE_CLAUDE_CODE_SKILLS=1`** (discovered in spike 001) — otherwise it double-loads Claude's GSD *skills* (wrong `~/.claude` paths) instead of its native GSD *commands*. Must be set permanently for daily-driver use.
- **AutoMem is the only bespoke piece:** an OpenCode plugin reproducing auto-recall (session start) + transcript synthesis (session end/compact), reusing `save-transcript-memory-v2.sh` logic with two edits — transcript source from OpenCode's session store, and synthesis via `opencode run` instead of `claude -p`.
- **Synthesis model: `opencode/qwen3.6-plus-free`** — confirmed live in spike 001 (free, no auth). (Resolves the earlier "qwen 3.6 — verify against catalog" item.)
- **Keep the `chatgpt-test` LiteLLM gateway config** — test OpenCode→gateway→ChatGPT; OpenCode-direct OAuth as fallback. Watch the no-system-role folding's effect on quality.
- **Plugin reference pattern:** context-mode's shipped OpenCode plugin at `~/.claude/plugins/marketplaces/context-mode/src/adapters/opencode/plugin.ts`.

## Prerequisites

- [x] **P0 — Back up `~/.claude`** → `~/claude-config-backup-20260521-183404.tgz` (done 2026-05-21)
- [x] **Install go-ahead** — approved by user; spike 001 installs complete.

## Spikes

Risk-ordered — the one most likely to kill the idea (GSD actually running on OpenCode) runs first.

| # | Name | Type | Validates (Given/When/Then) | Verdict | Tags |
|---|------|------|------------------------------|---------|------|
| 001 | opencode-stack-install | standard | Given OpenCode + the official stack installed (GSD via `--opencode`, Superpowers, context-mode, Impeccable), when OpenCode starts, then all load and `/gsd-*` commands resolve and run (subagent orchestration → 004) | **VALIDATED ✓** | opencode, gsd, install |
| 002 | automem-opencode-plugin | standard | Given the bespoke OpenCode plugin, when a session starts then later ends/compacts, then recall fires on start and transcript memories are synthesised (`opencode run` + qwen3.6) and POSTed to AutoMem | PENDING | automem, plugin, hooks |
| 003 | chatgpt-routing | standard | Given OpenCode → LiteLLM gateway (direct OAuth as fallback), when an agentic session runs on a ChatGPT model, then requests succeed and system-prompt folding doesn't wreck quality | PENDING | chatgpt, litellm, gateway |
| 004 | e2e-gsd-flow | standard | Given the full setup on a non-Anthropic backend, when running a real GSD plan→execute→verify with memory active, then it completes and recall + synthesis fire | PENDING | e2e, gsd, integration |
