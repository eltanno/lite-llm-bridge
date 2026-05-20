# LiteLLM Bridge

## What This Is

A local, Dockerized **LiteLLM gateway** that lets Claude Code drive multiple model providers behind stable semantic aliases (`opus` / `sonnet` / `haiku`). Claude Code points only at the gateway (`ANTHROPIC_BASE_URL=http://localhost:4000`) and never changes its config; each alias maps to a configurable backend, selected per-invocation with `claude --model <alias>`. Built for a single developer running locally. v1 fronts a **Claude Max** subscription and **Ollama Cloud**.

## Core Value

Point Claude Code at one stable local endpoint and reach any chosen model through `opus`/`sonnet`/`haiku` aliases — swapping the provider underneath without ever touching Claude Code's configuration.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

(None yet — ship to validate)

### Active

<!-- Current scope. Hypotheses until shipped and validated. -->

- [ ] LiteLLM runs as a local Docker container, reachable at `localhost:4000`
- [ ] Claude Code connects to the gateway via `ANTHROPIC_BASE_URL` set once, with no per-use env changes
- [ ] Gateway exposes semantic aliases `opus`/`sonnet`/`haiku`, selectable via `claude --model <alias>`
- [ ] Each alias's backend is defined in LiteLLM config and changeable by editing that config
- [ ] **Claude Max is reachable through the gateway without Anthropic API per-token billing** — PRIMARY HYPOTHESIS, feasibility to be validated in research
- [ ] At least one Ollama Cloud model is reachable through the gateway
- [ ] Secrets/credentials are kept out of the image (`.env`)
- [ ] Setup is reproducible and documented, with every technical choice verified against official docs

### Out of Scope

<!-- Explicit boundaries with reasoning. -->

- **OpenAI and Gemini providers** — deferred to a later version (PoC first). Note: consumer ChatGPT/Gemini *subscriptions* are not API access; wiring them likely needs paid API keys — to be investigated later.
- **Live/hot backend remapping without restart** — v1 uses per-command selection; changing config may require a restart/reload.
- **Multi-user / networked / remote access** — local, single-user only for v1.
- **Production hardening** (TLS, rate limiting, observability stack) — unnecessary for a local PoC.
- **Hosting local models on this machine** — beyond any Ollama daemon required purely as a bridge to Ollama Cloud.

## Context

- This is a **proof-of-concept first version** to prove the alias-and-swap gateway pattern works with Claude Code.
- Claude Code expects the **Anthropic Messages API**; LiteLLM is the translation layer between that shape and each provider's API.
- A ChatGPT-authored reference exists at `docs/claude-code-litellm-setup.md`. It is **explicitly non-authoritative** — a starting map only. Claims from it that must be independently verified before adoption:
  - the Claude Code env var `CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY=1`
  - that "Ollama exposes Anthropic-compatible endpoints"
  - reaching Ollama Cloud via a local Ollama daemon using `ollama_chat/<model>:cloud` + `api_base: http://localhost:11434`
  - that Claude Max can be routed through LiteLLM at all
- The user does **not** currently run a local Ollama daemon, but will install one **if** research confirms it is required to reach Ollama Cloud.
- Subscriptions in play: **Claude Max (5x)**, **Ollama Cloud**.

## Constraints

- **Tech stack**: LiteLLM as the gateway, Docker / docker-compose — user asked for a "container".
- **Verification (process)**: Every technical decision must be verified against official LiteLLM / Anthropic / Ollama documentation and working examples before adoption; `docs/` is not a source of truth.
- **Cost**: Avoid Anthropic API per-token billing — intent is to reuse the existing Claude Max subscription. This is the primary feasibility risk.
- **Deployment**: Local-only (`localhost`), single developer.
- **Compatibility**: Must work with Claude Code's model selection (`claude --model <alias>`) and the Anthropic Messages API shape.
- **Client-config stability**: Claude Code's `ANTHROPIC_BASE_URL` is set once and never changed to switch models.

## Key Decisions

<!-- Decisions that constrain future work. -->

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Use LiteLLM as the gateway | User-specified; translates Anthropic ↔ provider APIs, supports aliasing & fallbacks | — Pending |
| Expose models as `opus`/`sonnet`/`haiku` semantic aliases | Stable names so Claude Code config never changes; backends swappable underneath | — Pending |
| v1 providers = Claude Max + Ollama Cloud only | Prove the concept; defer GPT/Gemini | — Pending |
| Model swap via per-command `claude --model <alias>` | Simpler than live remap; satisfies the on-the-fly need | — Pending |
| Attempt Claude Max via gateway **without** API billing | User wants to reuse Max and avoid API costs | ⚠️ Revisit — feasibility unverified (primary risk) |
| Ollama Cloud routing TBD (local daemon vs direct Cloud API) | Decide by official-docs verification; install local Ollama only if required | — Pending |
| `docs/` reference treated as non-authoritative | User instruction; ChatGPT output is unverified | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-20 after initialization*
