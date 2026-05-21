# Terminal Coding Agent Evaluation — Daily-Driver Decision

**Date:** 2026-05-21
**Context:** lite-llm-bridge project. Currently **Claude Code + a self-built LiteLLM gateway** (Claude Max + Ollama Cloud working).
**Goal:** Choose a stable long-term **terminal daily driver** with **free model-backend choice**, ideally **reusing the existing workflow stack** (GSD / Superpowers / Impeccable / AutoMem / context-mode). Single tool for everything, including GSD orchestration. Willing to invest one-off rework time for a better day-to-day.

> Verified against first-party docs/repos and the local install (May 2026). Community/third-party items are flagged. "Not found / not documented" means exactly that.

---

## TL;DR — recommendation

- **OpenCode is the pragmatic winner.** It's the only non-Claude tool where the **entire** stack is *officially* supported (GSD, Superpowers, Impeccable all list it) **and** you get full model freedom + native MCP for AutoMem/context-mode. Residual cost: rewrite the two stack hooks (AutoMem recall/store, context-mode routing) as OpenCode plugins, and accept GSD's known OpenCode rough edges.
- **Pi is the principled alternative** (matches the "minimal core, add what you need" ethos). Everything is achievable — Impeccable is officially supported, Superpowers skills load, and **subagents + MCP exist as mature community extensions** — but **GSD on Pi is alpha community ports only**, which is real risk for a daily driver.
- **Claude Code stays the benchmark:** only place the whole stack runs natively, but it does **not** solve model freedom (the reason we started).
- **Goose drops** for *this* goal: best engine in the field, but **none of the three stack plugins target it** → most rebuild, not least.
- **Codex** is officially stack-supported but **OpenAI-locked** for subscriptions and has maturity bugs.

**Decisive next step:** spike OpenCode (install the stack, wire AutoMem via MCP, log in with ChatGPT Plus, run a real agentic GSD flow). If the ethos pull wins, spike Pi with `pi-subagents` + `pi-mcp-adapter`.

---

## Why this came up

Claude Code is **hard-wired to the Anthropic Messages API shape**. Every non-Anthropic backend must be *translated* by the gateway (LiteLLM), and translation fidelity is the ceiling:

- Claude Max ✅ and Ollama/deepseek ✅ translate cleanly (verified, in production).
- **ChatGPT Plus via the gateway FAILED** (spike PROV-01, see appendix): the ChatGPT/Codex backend rejects the system role → forces `supports_system_message: false` → which folds Claude Code's *block-array* system prompt → triggers `can only concatenate list (not str) to list` in LiteLLM 1.85.0's `map_system_message_pt`. Auth, transport, and tool-calling all worked; only system-message handling broke.

→ **Real model-backend freedom comes from a model-agnostic client** that speaks each provider natively, removing the translation tax. Hence this evaluation.

---

## Decision criteria

1. **Model-backend freedom** — native multi-provider, arbitrary OpenAI-compatible `base_url`, local models, and (ideally) **consumer-subscription login** (ChatGPT Plus, Claude Max, Copilot).
2. **Stack portability** — can the existing stack *run* (not be rebuilt)? Needs: MCP servers, lifecycle hooks, Agent Skills (SKILL.md), named subagents, custom slash commands.
3. **Daily-driver maturity** — stability, governance/bus-factor, churn.

### The stack and what each piece needs

| Component | What it is | Primitive it needs |
|---|---|---|
| **GSD** (`get-shit-done-cc`) | Planning/orchestration | named subagents + custom slash commands + hooks + a node CLI (`gsd-sdk`) |
| **Superpowers** (`obra/superpowers`) | Skill pack | Agent Skills/SKILL.md (+ subagents for 2 skills) |
| **Impeccable** (`pbakaus/impeccable`) | Design skill | Agent Skills/SKILL.md (single-session) |
| **AutoMem** | Custom memory | MCP server + session hooks (recall/store) |
| **context-mode** | Context manager | MCP server + PreToolUse hook |

---

## The deciding finding: the stack is far more portable than expected

Earlier framing assumed GSD/Superpowers were Claude-Code-bound. **That was wrong.** All three plugins officially target multiple non-Claude runtimes:

- **GSD — ~15 official runtimes** (per its README/USER-GUIDE): Claude Code, **OpenCode**, Gemini CLI, Kilo, Cursor, Windsurf, Augment, Antigravity, Trae, **Codex** (min CLI v0.130.0), Copilot, Cline, CodeBuddy, Qwen Code, JetBrains (EAP). **Goose and Crush are NOT supported. Pi is community-only.** (Local install corroborates: 121 "opencode", 232 "codex", 192 "text_mode", **1 "goose"** references.)
  - Maturity caveat: Claude Code is primary; OpenCode/Codex are best of the rest but have known bugs — model-tiering ignored on Codex/OpenCode (#2256), `gsd-sdk auto` was Claude-hardcoded on Codex (#2832), stale `~/.claude` paths in Codex installs (#2639).
  - **GSD v2** (`gsd-build/gsd-2`) is a *separate* standalone CLI built on the **Pi SDK** — runs independently of any host agent, with its own bundled subagents. The GSD project itself is betting on Pi's SDK.
- **Superpowers — 8 official platforms:** Claude Code, Codex CLI, Codex App, Factory Droid, Gemini CLI, **OpenCode**, Cursor, Copilot CLI. Adaptation via tool-name mapping files (`copilot-tools.md`, `codex-tools.md`, `gemini-tools.md`). Most skills are plain SKILL.md (load on any Agent-Skills tool); only **`dispatching-parallel-agents`** and **`subagent-driven-development`** need a subagent primitive. **Not Goose/Pi/Crush** officially.
- **Impeccable — 11 official harnesses:** Claude Code, Cursor, Gemini, Codex, Copilot, Kiro, **OpenCode**, **Pi**, Qoder, Trae, Rovo Dev. Ships pre-built per-provider dirs (`.opencode/skills/`, `.pi/skills/`, …). Single-session skill, no subagents/hooks → the most portable of the three. **Not Goose/Crush.**

### Stack-on-tool compatibility matrix

Legend: ✅ official/native · 🟡 works with adaptation/community · ❌ not supported

| Your stack | Claude Code | OpenCode | Pi | Goose | Codex |
|---|---|---|---|---|---|
| **GSD** | ✅ home | ✅ official\* | 🟡 alpha community port | ❌ | ✅ official\* |
| **Superpowers** | ✅ | ✅ official | 🟡 skills load; 2 subagent-skills need ext | ❌ | ✅ official |
| **Impeccable** | ✅ | ✅ official | ✅ official | ❌ | ✅ official |
| **AutoMem + context-mode (MCP)** | ✅ | ✅ native | 🟡 via `pi-mcp-adapter` | ✅ native | ✅ native |
| **AutoMem/context-mode hooks** | ✅ | 🟡 rewrite (TS plugin) | 🟡 rewrite (TS) | 🟡 rewrite | 🟡 rewrite |
| **Model freedom** | 🟡 gateway-only | ✅ | ✅ (best subs) | ✅ | 🟡 OpenAI-locked |

\* officially supported but with known bugs (e.g. GSD #2256/#2832/#2639).

**Reading:** OpenCode is the only non-Claude tool that runs the *whole* stack officially **and** gives model freedom. Goose — despite the best primitives — is worst here because the stack doesn't target it.

---

## Model backends

| Tool | OSS | Model freedom | Subscription login | LiteLLM gateway |
|---|---|---|---|---|
| **Claude Code** | ❌ proprietary | 🟡 gateway-only (Anthropic-shape lock) | Claude Max ✅ · ChatGPT ❌ | required for non-Anthropic |
| **OpenCode** | ✅ MIT | ✅ 75+ providers, any OpenAI-compat base_url, Ollama, OpenRouter | ChatGPT ✅ · Copilot ✅ · Claude Max ⚠️ (ToS-fragile; plugins pulled v1.3.0) | optional/redundant |
| **Pi** | ✅ MIT | ✅ 30+ providers, OpenAI-compat, OpenRouter | **Claude Max ✅ · ChatGPT ✅ · Copilot ✅** ⚠️ Claude Max = per-token overflow, not plan quota | optional/redundant |
| **Codex CLI** | ✅ Apache-2.0 | 🟡 custom providers via **API key**; non-OpenAI only via gateway | ChatGPT ✅ — but **OpenAI-locked** (sub auth can't route through a gateway) | works via `model_providers` + `wire_api` |
| **Goose** | ✅ Apache-2.0 | ✅ 40+ providers, OpenAI-compat, Ollama(+Cloud) | ChatGPT ✅ · Copilot ✅ · Claude Max ❌ (only via Claude Code ACP) | **first-class provider**; optional |
| **Crush** | ⚠️ non-standard | ✅ openai-compat **and** anthropic-compat base_url | ❌ none of big-3 (3rd-party flat-rate only) | easy via `openai-compat` |
| **Aider** | ✅ Apache-2.0 | ✅ embeds LiteLLM; any provider | ❌ API-key only | embedded; external redundant |

---

## Per-tool summaries

**Claude Code** (Anthropic, proprietary) — Best-in-class extensibility (30+ hook events, plugins, skills, MCP, subagents) and the only place the full stack runs natively. Model freedom is real but gateway-mediated; the Anthropic-shape lock is the hard limit (it broke the ChatGPT path).

**OpenCode** (Anomaly, MIT, ~163k★, v1.15.x, TS) — The most "Claude-Code-like" open option: reads `.claude/skills/` and `CLAUDE.md`, native MCP (stdio/remote), TS-plugin hooks (`tool.execute.before/after`, `session.*`), named subagents, markdown slash commands. Officially supported by GSD + Superpowers + Impeccable. Broadest polished provider/subscription coverage (Claude Max OAuth is ToS-fragile — pulled in v1.3.0). Fast release churn.

**Pi** (Earendil — Zechner + Ronacher, MIT, ~52k★, v0.75.x, pre-1.0, TS) — Deliberately minimal core (4 tools + 3 optional); everything else is opt-in TypeScript extensions ("Pi Packages" via npm/git). **Best subscription login** (Claude Max + ChatGPT + Copilot), rich `pi.on()` hooks, SKILL.md native. **No native MCP or subagents — both by design** (see Pi spotlight) but covered by mature community extensions. Reads `AGENTS.md` not `CLAUDE.md`. Claude Max via Pi bills as per-token overflow (not free quota).

**Codex CLI** (OpenAI, Apache-2.0, Rust, v0.132, pre-1.0) — Closest hook model to Claude Code (SessionStart/PreToolUse/PostToolUse/Stop), native MCP + subagents + SKILL.md. Officially supported by GSD/Superpowers/Impeccable. Blockers: **no custom slash commands**, and **subscription auth is OpenAI-locked** (ChatGPT sub can't route through a gateway; non-OpenAI needs an API key).

**Goose** (Block → Linux Foundation, Apache-2.0, ~45k★, v1.34.x, Rust) — Strongest *primitives*: extensions ARE MCP, full lifecycle hooks (v1.34), scans `.claude/skills/`, recipes ≈ subagents (parallel), custom slash commands, 40+ providers with **LiteLLM first-class**, durable governance. **But GSD/Superpowers/Impeccable don't target it** → you'd rebuild the stack as Goose recipes/skills. Great if starting fresh; wrong if reusing the stack.

**Crush** (Charmbracelet, Go, ~24k★, v0.70, pre-1.0) — Charm's renamed "opencode" (distinct from Anomaly's opencode.ai). Excellent model freedom (openai- *and* anthropic-compat base_url), MCP (all 3 transports), reads `~/.claude/skills/` + `CLAUDE.md`, **PreToolUse hooks Claude-Code-compatible** — but hooks are **PreToolUse-only** (no session/PostToolUse → AutoMem session recall can't auto-fire), no user-facing subagents, no slash commands, no big-3 subscription login.

**Aider** (Apache-2.0, ~45k★) — Great interactive pair-programmer, broad model freedom (embeds LiteLLM), but **none** of the stack primitives (no MCP/hooks/skills/subagents/slash). Near-total rebuild for this stack.

### Landscape (scanned, not shortlisted)
- **Amp** (Sourcegraph) — best CC-like extensibility, terminal-first, but **closed-source, no model choice**. Disqualified on model freedom.
- **Cline** — best raw model freedom (200+, any OpenAI-compat) + MCP/hooks/subagents, but **IDE-extension-first** (CLI secondary).
- **Qwen Code** — terminal, Apache-2.0, multi-provider; MCP/hooks unverified. Watch.
- **Gemini CLI** — terminal + MCP, but Google-model-locked.
- **Kilo Code** — 500+ models, MCP, `.kilocode/skills/`, but VS Code-first.
- **OpenHands** (GUI-first), **Plandex** (no extensibility), **Continue** (CLI is a CI checker), **Roo Code** (archived 2026-05-15) — not fits.

---

## Pi spotlight (lead candidate of interest)

**Ethos:** minimal core, add only what you need, no hidden behavior — "you know everything it's doing because everything is a choice you made." This is the explicit design intent (Zechner, "What I learned building an opinionated and minimal coding agent"), not marketing. Extensions are plain TypeScript (run via jiti, no build step) in `~/.pi/agent/`.

**Why no MCP in core (deliberate):** MCP servers are token-heavy (e.g. Playwright MCP ≈ 21 tools/13.7k tokens; Chrome DevTools ≈ 26 tools/18k tokens — 7–9% of context before you start). Pi prefers CLI-tools-with-READMEs (progressive disclosure). → **Fix:** community **`pi-mcp-adapter`** (nicobailon) reads a standard `mcp.json`, auto-registers stdio + HTTP MCP servers as Pi tools, token-efficient. So **AutoMem + context-mode work** via a drop-in adapter (community, not official — pin/verify).

**Why no subagents (deliberate):** Zechner: a subagent is "a black box within a black box" — it violates Pi's promise that you can inspect everything; he'd rather you write an artifact and start a fresh session than spawn hidden context. → **Fix (mature):** **`nicobailon/pi-subagents`** (~1,484★, 75 releases) adds a native `subagent` tool — parallel, sequential chains, session forking, async — via `pi install npm:pi-subagents`. Alternatives: `HazAT/pi-interactive-subagents` (466★), `tintinweb/pi-subagents` (348★). The SDK (`createAgentSession`) also supports building your own (days–weeks).

**Net:** Pi can do everything the stack needs, but via a layer of **community extensions** + an **alpha GSD port** — maximal control and ethos fit, more glue and bus-factor risk. (Two-person core team; Ronacher is a strong signal but it's still small and pre-1.0.)

---

## Cross-cutting conclusions

1. **The stack travels much further than "Claude-Code-only."** GSD (15 runtimes), Superpowers (8), Impeccable (11) all officially target several non-Claude tools — chiefly **OpenCode** and **Codex**.
2. **Skills (SKILL.md) are the most portable layer**; several tools read `~/.claude/skills/` directly.
3. **MCP travels well** (everything except Aider; Pi via community adapter) → AutoMem + context-mode port broadly.
4. **Hooks are the irreducible migration tax** — each tool has its own format; AutoMem's recall/store and context-mode's routing must be rewritten per tool (bounded work).
5. **The LiteLLM gateway becomes largely redundant** with any model-agnostic client (Goose even has it first-class). Keep it only as a single auth/alias/spend point if desired.
6. **Subscription reuse is the same ToS gray area everywhere**; Claude Max in third-party tools is the most fragile (Anthropic-prohibited in OpenCode; per-token overflow in Pi).

---

## Recommendation

For **"replace Claude Code, one tool including GSD, with model freedom, reusing the stack":**

1. **OpenCode** — pragmatic winner. Whole stack officially supported + model freedom + native MCP. Work to do: rewrite 2 hooks as plugins; accept GSD's known OpenCode gaps.
2. **Pi** — principled pick. Ethos fit + best subscriptions; subagents/MCP solved via community; GSD is alpha-port (risk). Choose if you want to own/assemble the toolchain.
3. **Claude Code** — keep as benchmark; only it runs everything natively, but doesn't fix model freedom.
4. **Goose / Codex** — Goose: great engine, stack doesn't target it. Codex: supported but OpenAI-locked subs + bugs.

**Validation plan (either candidate):** install the stack → wire AutoMem via MCP → log in with ChatGPT Plus → run a real agentic planner→executor→verifier GSD flow with one parallel step. Spike **OpenCode first** (should mostly just work = fastest signal).

---

## Open items / next steps
- [ ] Spike the front-runner (OpenCode) end-to-end; if ethos wins, spike Pi with `pi-subagents` + `pi-mcp-adapter`.
- [ ] Scope the hooks rewrite (AutoMem recall/store + context-mode routing) for the chosen tool.
- [ ] Decide the LiteLLM gateway's fate (drop, or keep as alias/auth point).
- [ ] **Keep — do NOT tear down.** Repurpose the `chatgpt-test` gateway config as the **OpenCode→gateway→ChatGPT** test. PROV-01's failure was Claude-Code-specific (its block-array system prompt crashed LiteLLM's `map_system_message_pt`); OpenCode hits the OpenAI-compatible endpoint with a *string* system message, which the spike confirmed works — so the crash shouldn't recur. Verify end-to-end in the spike, including whether the ChatGPT/Codex no-system-role *folding* (happens via the gateway regardless of client) hurts agentic quality. Fallback if it does: OpenCode→ChatGPT **direct** (native OAuth, no gateway).

---

## Appendix — ChatGPT-subscription gateway spike (PROV-01), 2026-05-21

**Verdict: FAIL** for agentic Claude Code use on stock LiteLLM 1.85.0.

- **Root cause (a LiteLLM bug, not an OpenAI/account limit):** ChatGPT/Codex backend forbids the system role → requires `supports_system_message: false` → folding Claude Code's block-array system prompt hits `can only concatenate list (not str) to list` in `map_system_message_pt`. (String system works; block-array crashes.)
- **What worked (proven via curl):** OAuth device login (ChatGPT Plus), token persistence across a full recreate, the Anthropic↔OpenAI-Responses transport, block-array *user* content, and **tool-calling** (`gpt-5.3-codex` callable on Plus — no Pro needed).
- **Operational notes:** the `chatgpt/` provider blocks gateway startup until OAuth completes; `docker compose restart` is broken on WSL2/Docker Desktop (stale bind-mount) — use recreate.
- **Implication:** confirms the Anthropic-shape translation ceiling and motivates moving to a model-agnostic client. Upgrading Plus→Pro would not fix it.

---

## Key sources (first-party unless noted)
- Claude Code: code.claude.com/docs (llm-gateway, env-vars, hooks, skills, plugins, sub-agents)
- OpenCode: opencode.ai/docs (providers, mcp-servers, skills, agents, plugins, commands)
- Pi: pi.dev/docs; mariozechner.at (minimal-agent + no-MCP posts); github.com/earendil-works/pi; nicobailon/pi-subagents; nicobailon/pi-mcp-adapter (community)
- Codex CLI: developers.openai.com/codex; github.com/openai/codex
- Goose: github.com/block/goose (providers, hooks, skills, subagents, slash-commands)
- Crush: github.com/charmbracelet/crush
- Aider: aider.chat/docs
- GSD: github.com/gsd-build/get-shit-done (USER-GUIDE, CONFIGURATION); gsd-build/gsd-2; issues #2256/#2832/#2639; community ports rokicool/gsd-opencode, fulgidus/pi-gsd, eirondev/pi-gsd
- Superpowers: github.com/obra/superpowers
- Impeccable: github.com/pbakaus/impeccable (HARNESSES.md)
