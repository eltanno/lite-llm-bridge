# Project Research Summary

**Project:** lite-llm-bridge
**Domain:** Local Dockerized LLM gateway — Anthropic Messages API proxy with semantic model aliasing
**Researched:** 2026-05-20
**Confidence:** HIGH (core stack and architecture verified against first-party LiteLLM, Anthropic, and Ollama docs; one medium-confidence empirical gap remains)

> Note: The raw research files `STACK.md` and `PITFALLS.md` contain a now-SUPERSEDED conclusion that "Claude Max via LiteLLM is prohibited/banned." That verdict came from a news outlet + an unknown blog + an anecdote and was overridden after first-party verification. This summary reflects the corrected state.

---

## Executive Summary

lite-llm-bridge is a single-container LiteLLM proxy that gives Claude Code one stable local endpoint (`localhost:4000`) while routing `opus`/`sonnet`/`haiku` aliases to swappable backends. Claude Code sends Anthropic Messages API requests to LiteLLM; LiteLLM resolves the alias in `config.yaml`, translates the request to the target provider's format, and translates the response back. All format translation is LiteLLM's responsibility — Claude Code never changes shape. v1 fronts two backends: **Claude Max** (via OAuth-token forwarding to `api.anthropic.com`) and **Ollama Cloud** (via direct OpenAI-compatible API at `https://ollama.com/v1`, no local daemon).

The mechanism for Claude Max access — `general_settings: forward_client_headers_to_llm_api: true`, scoped per-model via `model_group_settings` — is confirmed in two first-party sources: the LiteLLM "Using Claude Code Max Subscription" tutorial and Anthropic's own Claude Code LLM-gateway documentation. The ToS clause that the raw research flagged targets abuse/reselling/identity-spoofing by third-party commercial tools; a user routing their own Claude Code through their own local proxy is the documented use case. The Max OAuth credential is NOT an env var — it comes from `claude` browser login at runtime and is forwarded transparently.

The main remaining risk is empirical, not policy: whether LiteLLM's translation faithfully preserves tool-calling semantics (`tool_use`/`tool_result` blocks, streaming events, stop reasons) when routing **agentic** Claude Code sessions through an Ollama-backed alias. Text round-trips cannot validate this. Phase 1 must include a real agentic spike (file edits, bash, tool use) through an Ollama-backed alias before the gateway is declared working. Two supply-chain constraints apply regardless: pin LiteLLM to `ghcr.io/berriai/litellm:main-stable` and explicitly exclude v1.82.7 / v1.82.8 (confirmed credential-stealing malware, cited in Anthropic's own docs).

---

## Key Findings

### Recommended Stack

- **LiteLLM Proxy** (`ghcr.io/berriai/litellm:main-stable`): Gateway exposing `/v1/messages` in Anthropic Messages format, translating outbound to each provider. Named in Anthropic's Claude Code LLM-gateway docs. Avoid v1.82.7 / v1.82.8 (malware).
- **Docker / docker-compose** (user-mandated): Single-service compose, port 4000, `config.yaml` as read-only bind mount, secrets via `.env`. No database needed for single-user PoC. `docker compose up/down`.
- **Ollama Cloud** (external, no local daemon): Direct OpenAI-compatible REST API at `https://ollama.com/v1`, `OLLAMA_API_KEY` Bearer auth. LiteLLM wires it with `openai/<model>` + `api_base`.
- **Anthropic API / Claude Max** (external): via OAuth-token forwarding — LiteLLM forwards the Claude Code bearer to `api.anthropic.com`. `ANTHROPIC_API_KEY` must NOT be in Claude Code's environment (it silently overrides the subscription).

**Auth wiring:** `ANTHROPIC_AUTH_TOKEN` (= `LITELLM_MASTER_KEY`) authenticates Claude Code to the gateway. The Max OAuth bearer is forwarded to Claude model groups only via `model_group_settings.forward_client_headers_to_llm_api`. Ollama groups do not receive the Claude bearer.

**Alias naming:** Names must contain `claude`/`sonnet`/`opus`/`haiku`/`anthropic` for gateway model discovery. Use `claude-opus`/`claude-sonnet`/`claude-haiku`, or set `ANTHROPIC_DEFAULT_OPUS_MODEL=opus` (etc.) so Claude Code sends short alias strings that match `model_name` entries.

### Expected Features

**Must have (table stakes):**
- Model aliasing via `model_name` in `config.yaml`
- Anthropic Messages API (`/v1/messages`) served to Claude Code — LiteLLM's unified endpoint handles all translation
- `ANTHROPIC_BASE_URL=http://localhost:4000` set once in Claude Code
- Claude Max OAuth forwarding — `forward_client_headers_to_llm_api`, scoped to Claude model groups
- Ollama Cloud routing — `openai/<model>` + `api_base: https://ollama.com/v1` + `OLLAMA_API_KEY`
- Secrets out of image — credentials in `.env`, referenced as `os.environ/VAR_NAME`
- Static `LITELLM_MASTER_KEY` — gateway auth token
- `drop_params: true` — prevents Anthropic-specific params from failing Ollama backends
- `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1` for Ollama group — prevents `anthropic-beta` headers reaching Ollama

**Should have (v1.x after core validation):**
- Fallbacks and retries — `litellm_settings: fallbacks` / `num_retries`; no DB required
- Gateway model discovery — `CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY=1` (requires Claude Code v2.1.129+)

**Defer to v2+:**
- LiteLLM Admin UI (requires PostgreSQL)
- Hot-reload without restart (requires `store_model_in_db`)
- OpenAI / Gemini providers (require paid API keys; consumer subscriptions are not API access)

### Architecture Approach

Three layers: Claude Code on host (issues Anthropic Messages API requests) → LiteLLM container on port 4000 (alias resolution, format translation, selective credential forwarding) → two external APIs. Config is two committed files (`docker-compose.yml`, `config.yaml`); secrets in `.env` (gitignored). Container is stateless — restart is the hot-reload story for v1.

1. **Claude Code (host)** — issues `POST /v1/messages` with alias model name; authenticated via `ANTHROPIC_AUTH_TOKEN`; Max OAuth bearer forwarded transparently
2. **LiteLLM Proxy (Docker, port 4000)** — resolves alias, translates Anthropic↔provider format, forwards `anthropic-beta`/`anthropic-version` to Claude backends, strips them for Ollama, forwards bearer to Claude backends only
3. **`config.yaml` (bind-mounted, committed)** — alias→backend mapping, no secrets
4. **`.env` (gitignored)** — `LITELLM_MASTER_KEY` + `OLLAMA_API_KEY` only; Max OAuth credential is runtime, not env
5. **Ollama Cloud (external)** — OpenAI-compatible at `https://ollama.com/v1`; `OLLAMA_API_KEY` Bearer auth
6. **Anthropic API (external)** — validates forwarded Max OAuth bearer

### Critical Pitfalls

1. **Supply chain:** LiteLLM v1.82.7 / v1.82.8 contain credential-stealing malware — pin to `main-stable`, never `latest` or PyPI. (Anthropic's own gateway docs + LiteLLM advisory — HIGH.)
2. **`ANTHROPIC_API_KEY` in Claude Code's env silently overrides Max subscription** — keep it only in the container `.env`; verify with `/status`. (Claude Code auth docs — HIGH.)
3. **`anthropic-beta` headers forwarded to Ollama cause rejection** — scope header forwarding to Claude groups; set `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1` as safety net. (LiteLLM incident report + gateway docs — HIGH.)
4. **Anthropic-specific params rejected by Ollama** — `drop_params: true`; validate with a real agentic session, not `curl`. (LiteLLM GitHub #22963 — HIGH.)
5. **Ollama Cloud endpoint confusion** — use `api_base: https://ollama.com/v1`, model name without `:cloud` suffix. (Ollama Cloud docs — MEDIUM on exact URL; `curl`-test before committing.)

---

## Implications for Roadmap

### Phase 1 — Foundation + Feasibility Spike
Every downstream feature depends on both backend paths being proven. Claude Max OAuth forwarding is documented but never composed with alias-swapping in this exact config; the Ollama `openai/` + `api_base` path has no LiteLLM-specific first-party example. Both validations must include real agentic Claude Code tool use.

Delivers: `docker-compose.yml` + `config.yaml` (three aliases); LiteLLM at `localhost:4000` pinned to `main-stable`; Claude Code routing wired (`ANTHROPIC_BASE_URL` + `ANTHROPIC_AUTH_TOKEN`); Max OAuth forwarding confirmed (verify `/status`); Ollama Cloud confirmed via `openai/<model>` + `OLLAMA_API_KEY`; **agentic tool-use spike** through an Ollama-backed alias; `.env` (master key + Ollama key); `drop_params` + beta-header scoping.

Decision gate: if Max OAuth forwarding fails on `main-stable`, fall back to Anthropic API key (per-token) before proceeding — don't build workarounds.

### Phase 2 — Hardening + DX
Fallbacks/retries; startup docs (`docker compose up -d`, `/status`, sample task); alias-naming locked; evaluate `CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY=1`.

### Phase 3 — v2 Provider Expansion (out of v1 scope)
OpenAI/Gemini require paid API keys — verify credentials exist before any config work.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Image, compose, env vars verified vs first-party docs. Gap: exact Ollama Cloud URL with LiteLLM `openai/` — one `curl` resolves it. |
| Features | HIGH | Verified vs LiteLLM proxy/config + Claude Code gateway/model-config docs. |
| Architecture | HIGH | Boundaries, data flow, credential scoping, header forwarding verified vs first-party docs. |
| Pitfalls | HIGH | Supply chain, auth precedence, beta headers first-party. Ollama endpoint MEDIUM. |

**Overall:** HIGH for design; MEDIUM for Ollama Cloud + LiteLLM composition (empirical Phase-1 spike).

### Gaps to Address (Phase 1)
- Ollama Cloud exact `api_base` with LiteLLM `openai/` (`https://ollama.com/v1`; fall back to `https://ollama.com` if `/v1` doubles) — `curl`-test first.
- Tool-calling support on the chosen Ollama model — resolve in agentic spike; swap model if unsupported.
- `model_group_settings.forward_client_headers_to_llm_api` exact YAML syntax vs the pinned LiteLLM version. Fallback: `general_settings: forward_client_headers_to_llm_api: true` with separate Ollama model groups (no Anthropic key, so a leaked bearer is harmless).
- Claude Code version (≥ v2.1.129) for discovery.

---

## Sources

**Primary (HIGH — first-party):**
- `https://code.claude.com/docs/en/llm-gateway` — gateway requirements, header forwarding, malware warning
- `https://code.claude.com/docs/en/iam` — auth precedence (ANTHROPIC_AUTH_TOKEN, ANTHROPIC_API_KEY, OAuth)
- `https://docs.litellm.ai/docs/tutorials/claude_code_max_subscription` — OAuth forwarding mechanism
- `https://docs.litellm.ai/docs/tutorials/claude_non_anthropic_models` — Anthropic-shape translation for non-Claude backends
- `https://docs.litellm.ai/docs/anthropic_unified` — /v1/messages provider support
- `https://docs.litellm.ai/docs/proxy/configs` — model_list, os.environ/, general_settings
- `https://docs.ollama.com/cloud` — direct API, `https://ollama.com`, Bearer key, no daemon required

**Tertiary (discarded as superseded / non-authoritative):**
- The Register, CLIProxyAPI/rogs.me, Hacker News reports — describe commercial third-party tool blocking; not applicable to a personal local proxy (the documented LiteLLM use case). Overridden by first-party verification.
- `docs/claude-code-litellm-setup.md` — ChatGPT-authored; used only as an initial claim list to verify.

---
*Research completed: 2026-05-20 · Ready for roadmap: yes*
