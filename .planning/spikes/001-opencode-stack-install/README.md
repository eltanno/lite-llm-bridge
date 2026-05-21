---
spike: 001
name: opencode-stack-install
type: standard
validates: "Given OpenCode + the official stack installed, when OpenCode starts, then all components load and GSD commands run"
verdict: VALIDATED
related: [002, 003, 004]
tags: [opencode, gsd, install, superpowers, context-mode, impeccable]
---

# Spike 001: OpenCode + Stack Install

## What This Validates
Given OpenCode and the official, unedited stack installed (GSD via `--opencode`, Superpowers, context-mode, Impeccable), when OpenCode starts, then all components load without error and `/gsd-*` commands resolve and run. AutoMem = spike 002; full subagent orchestration = spike 004.

## How to Run
```bash
# install (additive — OpenCode config lives in ~/.config/opencode; ~/.claude untouched)
npm i -g opencode-ai
npx -y get-shit-done-cc --opencode --global
npm i -g context-mode
cp -r ~/.claude/plugins/marketplaces/impeccable/.opencode/skills/impeccable ~/.config/opencode/skills/
# ~/.config/opencode/opencode.json: plugin ["superpowers@git+...","context-mode"] + mcp {context-mode}

# verify
opencode models     # free models incl. qwen3.6-plus-free
OPENCODE_DISABLE_CLAUDE_CODE_SKILLS=1 opencode run --model opencode/qwen3.6-plus-free "/gsd-help"
```

## What to Expect
- `opencode models` lists free models with no auth: `qwen3.6-plus-free`, `deepseek-v4-flash-free`, `nemotron-3-super-free`, `big-pickle`.
- `/gsd-help` (with Claude-skill reading disabled) prints the GSD entry points.

## Investigation Trail
1. Installed **OpenCode 1.15.7** (npm; user-owned nvm prefix, no sudo). Additive: config in `~/.config/opencode`, `~/.claude` untouched. `~/.claude` backed up first → `~/claude-config-backup-20260521-183404.tgz`.
2. `npx -y get-shit-done-cc --opencode --global` → **GSD v1.32.0** to `~/.config/opencode`: 60 commands, 21 agents, 6 hooks. Auto-set `resolve_model_ids: "omit"` in `~/.gsd/defaults.json` (sidesteps the model-tiering bug #2256). **GSD installs as *commands* on OpenCode, not skills.** It also installed OpenCode-format hooks (`.js`) — contradicting the earlier assumption that GSD hooks don't transfer.
3. Installed context-mode globally; wrote `opencode.json` with plugins `[superpowers, context-mode]` + `mcp {context-mode}`. Copied Impeccable's prebuilt `.opencode` skill to `~/.config/opencode/skills/`.
4. `opencode models --print-logs`: **superpowers fetched from git (~6s) and context-mode both loaded, zero errors.** Discovered OpenCode ships **free models** (OpenCode Zen), including **`qwen3.6-plus-free`** — our chosen synthesis model, available with no auth.
5. Free-model smoke test → returned `OPENCODE_OK`. ✓
6. **Wrinkle:** `/gsd-help` first ran the **Claude-Code `gsd-help` *skill*** (OpenCode reads `~/.claude/skills/` for compatibility), which pointed at `~/.claude/get-shit-done/` paths not in OpenCode's allowlist → permission rejection → failure. OpenCode was preferring Claude's GSD *skills* over its own GSD *commands*.
7. **Fix:** `OPENCODE_DISABLE_CLAUDE_CODE_SKILLS=1` → `/gsd-help` then ran the native OpenCode GSD command and printed the entry points correctly. ✓

## Results
**VALIDATED** (scope: install + load + command resolution). The full official stack installs additively and loads cleanly on OpenCode; GSD commands run on the free qwen3.6 model once Claude-skill reading is disabled.

**Key requirement discovered:** OpenCode must run with `OPENCODE_DISABLE_CLAUDE_CODE_SKILLS=1`, or it double-loads Claude's GSD *skills* (wrong, `~/.claude`-bound paths) instead of its native GSD *commands*. Needs to be set permanently (shell profile or equivalent) for daily-driver use.

**Surprises:** (a) free models incl. `qwen3.6-plus-free` ship with OpenCode — no gateway/OAuth needed to test, and it covers the AutoMem synthesis engine for free; (b) GSD *did* install OpenCode-format hooks (earlier research said it wouldn't).

**Deferred:** AutoMem MCP + bespoke plugin (spike 002); full GSD plan→execute→verify with subagents on a non-Anthropic backend (spike 004).
