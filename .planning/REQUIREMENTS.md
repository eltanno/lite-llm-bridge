# Requirements: LiteLLM Bridge

**Defined:** 2026-05-20
**Core Value:** Point Claude Code at one stable local endpoint and reach any chosen model through `opus`/`sonnet`/`haiku` aliases — swapping the provider underneath without ever touching Claude Code's configuration.

## v1 Requirements

Requirements for the initial proof-of-concept. Each maps to a roadmap phase.

### Gateway & Deployment

- [ ] **GW-01**: LiteLLM runs as a single docker-compose service reachable at `localhost:4000`, with the image pinned to `ghcr.io/berriai/litellm:main-stable` (explicitly never 1.82.7 / 1.82.8).
- [ ] **GW-02**: `docker compose up` and `docker compose down` start and stop the gateway; `compose.yaml` and `config.yaml` are committed to the repo.
- [ ] **GW-03**: Secrets exist only in a gitignored `.env` (`LITELLM_MASTER_KEY`, `OLLAMA_API_KEY`); no secrets are baked into the image or committed files.

### Claude Code Integration

- [ ] **CC-01**: Claude Code reaches the gateway with `ANTHROPIC_BASE_URL=http://localhost:4000` set once plus `ANTHROPIC_AUTH_TOKEN=<LITELLM_MASTER_KEY>`, and `ANTHROPIC_API_KEY` is kept absent from Claude Code's environment.
- [ ] **CC-02**: The gateway serves the Anthropic Messages API (`/v1/messages`) and returns correctly-shaped Anthropic responses to Claude Code for every backend.
- [ ] **CC-03**: A model is selectable per command via `claude --model <alias>`.

### Aliasing & Routing

- [ ] **AL-01**: The gateway exposes the semantic aliases `claude-opus`, `claude-sonnet`, and `claude-haiku` (names that pass Claude Code's model-name filter).
- [ ] **AL-02**: Each alias's backend is defined in the committed `config.yaml` and is changed by editing that file (a container restart applies the change; no live-reload required in v1).

### Claude via Max Subscription

- [ ] **MAX-01**: At least one alias routes to Claude using the Max subscription via OAuth-token forwarding (`forward_client_headers_to_llm_api`, scoped to Claude model groups) — no Anthropic API key and no per-token billing.
- [ ] **MAX-02**: It is verified that Claude Code is consuming the Max subscription through the gateway (confirmed via `/status` and a successful real session).

### Ollama Cloud Backend

- [ ] **OLL-01**: At least one alias routes to an Ollama Cloud model via the direct API (`openai/<model>` + `api_base: https://ollama.com/v1` + `OLLAMA_API_KEY`), with no local or containerized Ollama daemon.
- [ ] **OLL-02**: Agentic fidelity is proven — a real Claude Code tool-use session (file edit + bash) completes end-to-end through an Ollama-backed alias (swap the model if the chosen one lacks tool-calling support).

### Header & Parameter Handling

- [ ] **HDR-01**: `anthropic-beta` / `anthropic-version` headers are forwarded to Claude backends but stripped for Ollama, and `drop_params: true` plus `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1` (Ollama group) are set so Anthropic-specific fields don't break Ollama requests.

## v2 Requirements

Deferred to a future release. Tracked but not in the current roadmap.

### Reliability

- **REL-01**: Fallback chains and retries between backends (`litellm_settings: fallbacks` / `num_retries`).

### Discovery

- **DISC-01**: Gateway model discovery (`CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY=1`) so aliases appear in the `/model` picker (requires Claude Code v2.1.129+).

### Provider Expansion

- **PROV-01**: OpenAI provider behind an alias (requires a paid OpenAI API key — a ChatGPT subscription is not API access).
- **PROV-02**: Gemini provider behind an alias (requires `GEMINI_API_KEY`).

### Operations

- **OPS-01**: LiteLLM Admin UI and DB-backed hot-reload of model config without restart (requires PostgreSQL / `store_model_in_db`).

## Out of Scope

Explicitly excluded for v1. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Multi-user / networked / remote access | Local, single-user PoC; bind to localhost only |
| TLS, rate limiting, production hardening, observability stack | Unnecessary for a local PoC |
| Hosting local (on-device) models | Cloud backends only for v1; out of the gateway's purpose |
| Live/hot backend remap without restart | v1 uses per-command selection + config edit + restart (see OPS-01 for the v2 path) |
| Routing Claude via an Anthropic API key by default | Intentionally using the Max subscription via OAuth forwarding; an API key is only a documented fallback if OAuth forwarding proves broken on the pinned version |

## Traceability

Which phase covers which requirement. Populated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| GW-01 | (set by roadmap) | Pending |
| GW-02 | (set by roadmap) | Pending |
| GW-03 | (set by roadmap) | Pending |
| CC-01 | (set by roadmap) | Pending |
| CC-02 | (set by roadmap) | Pending |
| CC-03 | (set by roadmap) | Pending |
| AL-01 | (set by roadmap) | Pending |
| AL-02 | (set by roadmap) | Pending |
| MAX-01 | (set by roadmap) | Pending |
| MAX-02 | (set by roadmap) | Pending |
| OLL-01 | (set by roadmap) | Pending |
| OLL-02 | (set by roadmap) | Pending |
| HDR-01 | (set by roadmap) | Pending |

**Coverage:**
- v1 requirements: 13 total
- Mapped to phases: 0 (filled during roadmap creation)
- Unmapped: 13 (pending roadmap)

---
*Requirements defined: 2026-05-20*
*Last updated: 2026-05-20 after initial definition*
