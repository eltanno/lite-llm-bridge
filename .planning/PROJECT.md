# LiteLLM Bridge

## What This Is

A local, Dockerized **LiteLLM gateway** that lets Claude Code drive multiple model providers behind stable semantic aliases (`opus` / `sonnet` / `haiku`). Claude Code points only at the gateway (`ANTHROPIC_BASE_URL=http://localhost:4000`) and never changes its config; each alias maps to a configurable backend, selected per-invocation with `claude --model <alias>`. Built for a single developer running locally. v1 fronts a **Claude Max** subscription and **Ollama Cloud**.

## Core Value

Point Claude Code at one stable local endpoint and reach any chosen model through `opus`/`sonnet`/`haiku` aliases — swapping the provider underneath without ever touching Claude Code's configuration.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

Validated in Phase 1 (Gateway + Feasibility Spike), 2026-05-20:

- [x] LiteLLM runs as a local Docker container at `localhost:4000`, started/stopped with `docker compose up/down` (GW-01/02)
- [x] Claude Code connects via `ANTHROPIC_BASE_URL` set once, no per-use config changes (CC-01)
- [x] Gateway exposes aliases `claude-opus`/`claude-sonnet`/`claude-haiku` (the `claude-` prefix is required to pass Claude Code's model-name filter), selectable via `claude --model <alias>` (AL-01, CC-03)
- [x] Each alias's backend is defined in `config.yaml` and changeable by editing it + restart (AL-02)
- [x] Claude Max reachable via OAuth-token forwarding — confirmed live end-to-end (`/status` shows the Max subscription; MAX-01/MAX-02)
- [x] Ollama Cloud reachable + agentic tool-use proven through `claude-haiku` → `deepseek-v4-pro` (OLL-01/OLL-02)
- [x] Secrets kept out of the image via gitignored `.env` + `os.environ/` references (GW-03)
- [x] Anthropic beta headers/params do not leak to Ollama; setup documented in README (HDR-01, CC-02)

### Active

<!-- Current scope. Hypotheses until shipped and validated. -->

All v1 requirements were shipped and validated in Phase 1 — see **Validated** above. The next scope is defined at the v2 milestone (currently deferred): fallbacks/retries (REL-01), gateway model discovery (DISC-01), OpenAI + Gemini providers (PROV-01/02), and LiteLLM Admin UI / DB-backed hot-reload (OPS-01).

Carried-forward consideration from Phase 1: optionally add canonical model ids (e.g. `claude-sonnet-4-6`) as extra `model_list` aliases so a bare `claude` (no `--model`) and Claude Code background requests route too (today only the three semantic aliases are mapped).

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
  - that Claude Max can be routed through LiteLLM at all — **VERIFIED viable** via OAuth-token forwarding (`forward_client_headers_to_llm_api: true`); see Key Decisions. Gotcha: do NOT set `ANTHROPIC_API_KEY` in Claude Code's env — it overrides the subscription. The LiteLLM 1.82.7/1.82.8 malware warning is confirmed in Anthropic's own llm-gateway doc — pin a known-good official image.
- The user does **not** currently run a local Ollama daemon, but will install one **if** research confirms it is required to reach Ollama Cloud.
- Subscriptions in play: **Claude Max (5x)**, **Ollama Cloud**.

## Constraints

- **Tech stack**: LiteLLM as the gateway, Docker / docker-compose — user asked for a "container".
- **Verification (process)**: Every technical decision must be verified against official LiteLLM / Anthropic / Ollama documentation and working examples before adoption; `docs/` is not a source of truth.
- **Cost**: Reuse the existing Claude Max subscription instead of per-token Anthropic API billing — achieved via LiteLLM OAuth-token forwarding (verified). Avoid setting `ANTHROPIC_API_KEY` in Claude Code's environment (it overrides the subscription).
- **Deployment**: Local-only (`localhost`), single developer.
- **Compatibility**: Must work with Claude Code's model selection (`claude --model <alias>`) and the Anthropic Messages API shape.
- **Client-config stability**: Claude Code's `ANTHROPIC_BASE_URL` is set once and never changed to switch models.

## Key Decisions

<!-- Decisions that constrain future work. -->

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Use LiteLLM as the gateway | User-specified; translates Anthropic ↔ provider APIs, supports aliasing & fallbacks | ✓ Shipped (Phase 1) — `ghcr.io/berriai/litellm:main-stable` via docker-compose |
| Expose models as semantic aliases | Stable names so Claude Code config never changes; backends swappable underneath | ✓ Shipped (Phase 1) as `claude-opus`/`claude-sonnet`/`claude-haiku` (the `claude-` prefix passes Claude Code's model-name filter) |
| v1 providers = Claude Max + Ollama Cloud only | Prove the concept; defer GPT/Gemini | ✓ Both verified end-to-end (Phase 1) |
| Model swap via per-command `claude --model <alias>` | Simpler than live remap; satisfies the on-the-fly need | ✓ Verified (Phase 1) — only `--model` changes; `ANTHROPIC_BASE_URL` set once |
| Use Claude Max via LiteLLM OAuth-token forwarding (no API key) | Documented first-party path: Claude Code OAuth login → LiteLLM forwards the bearer token to Anthropic; reuses Max, no per-token billing | ✓ Verified end-to-end (Phase 1) — `/status` shows the Max subscription; scoped `model_group_settings` forwarding (E-01) |
| Ollama Cloud via direct Cloud API (no local daemon) | Official OpenAI-compatible endpoint reachable directly | ✓ Resolved (Phase 1) — `openai/deepseek-v4-pro:cloud` + `api_base: https://ollama.com/v1` (E-02) |
| `docs/` reference treated as non-authoritative | User instruction; ChatGPT output is unverified | ✓ Held — every choice verified against first-party docs |

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
*Last updated: 2026-05-20 — Phase 1 complete: v1 PoC validated end-to-end (gateway up; Max OAuth path and Ollama agentic path both proven live).*
