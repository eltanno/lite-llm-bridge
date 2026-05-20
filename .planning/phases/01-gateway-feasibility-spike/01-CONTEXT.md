# Phase 1: Gateway + Feasibility Spike - Context

**Gathered:** 2026-05-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Stand up the LiteLLM gateway in docker-compose and prove the full v1 PoC end-to-end: Claude Code talks only to the gateway, `opus`/`sonnet`/`haiku` aliases route to swappable backends, the Claude Max subscription is used through the gateway via OAuth forwarding, an Ollama Cloud model is reachable directly, and a real agentic Claude Code session works through an Ollama-backed alias. Covers all 13 v1 requirements (GW/CC/AL/MAX/OLL/HDR). Hardening, fallbacks, discovery, and extra providers are explicitly out (v2).
</domain>

<decisions>
## Implementation Decisions

These were settled in the project discussion (see PROJECT.md / SUMMARY.md) or auto-selected as the recommended default for open implementation choices. Downstream research/planning may refine the auto-selected ones.

### Alias → backend mapping (initial)
- **D-01:** `claude-opus` → Claude (Max via OAuth forwarding); `claude-sonnet` → Claude (Max via OAuth forwarding); `claude-haiku` → an Ollama Cloud model. Rationale: exercises BOTH paths in one config (2 Max-backed + 1 Ollama-backed) and satisfies MAX-01 + OLL-01 together. Aliases use the `claude-` prefix so they pass Claude Code's model-name filter (AL-01).

### Ollama Cloud model choice
- **D-02:** Default the `claude-haiku` backend to a coding-capable Ollama Cloud model (recommended: `qwen3-coder`). MUST verify tool-calling support during the agentic spike (OLL-02); if it lacks tools, swap to another Ollama Cloud model (e.g. a deepseek/kimi/qwen variant that supports tools). Tool support is the deciding criterion, not model size.

### Claude path / OAuth forwarding
- **D-03:** Use `general_settings: forward_client_headers_to_llm_api: true` scoped to the Claude model groups via `model_group_settings.forward_client_headers_to_llm_api: [claude-opus, claude-sonnet]`. The Ollama group must NOT receive the forwarded Anthropic bearer. Fallback if the per-group key syntax differs on the pinned LiteLLM version: keep general forwarding on but isolate Ollama in its own model group authenticated by `OLLAMA_API_KEY` (a leaked bearer is then harmless). No `ANTHROPIC_API_KEY` anywhere in Claude Code's env.

### Ollama Cloud wiring
- **D-04:** Reach Ollama Cloud directly (no local/containerized daemon): `openai/<model>` + `api_base: https://ollama.com/v1` + `api_key: os.environ/OLLAMA_API_KEY`. `curl`-test the exact base URL before committing config (fallback `https://ollama.com`, or `ollama_chat/` + api_base if `openai/` auth doesn't carry).

### Header/param safety
- **D-05:** `drop_params: true` in `litellm_settings`; `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1` for the Ollama group; ensure `anthropic-beta`/`anthropic-version` reach Claude backends but not Ollama (HDR-01).

### Deployment & secrets
- **D-06:** docker-compose, single service, port 4000, image pinned to `ghcr.io/berriai/litellm:main-stable` (never 1.82.7/1.82.8). `config.yaml` bind-mounted read-only. `.env` (gitignored) holds `LITELLM_MASTER_KEY` (recommend generating a random value) + `OLLAMA_API_KEY` (user supplies from ollama.com/settings/keys). Commit a `.env.example` and a short README documenting `docker compose up -d`, the Claude Code env vars, and the `claude` Max login. The Max OAuth credential is runtime-only (browser login), never an env var.

### Claude's Discretion
- Exact filenames (`compose.yaml` vs `docker-compose.yml`), README structure, and the precise current Claude model IDs behind the Max aliases (planner/researcher to confirm against current docs).

### Validation approach (the "spike" half of the phase)
- **D-07:** Validation is agentic, not a curl round-trip: drive a real Claude Code tool-use session (file edit + bash) through the Ollama-backed alias (OLL-02), and confirm `/status` shows the Max subscription in use for a Claude-backed alias (MAX-02). Decision gate: if Max OAuth forwarding is broken on `main-stable`, fall back to an Anthropic API key and record it in PROJECT.md before proceeding — no workarounds.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project planning docs
- `.planning/PROJECT.md` — corrected project context (Max-via-LiteLLM verified viable)
- `.planning/REQUIREMENTS.md` — the 13 v1 requirements + Out of Scope
- `.planning/ROADMAP.md` — Phase 1 goal, success criteria, decision gate
- `.planning/research/SUMMARY.md` — verified findings, exact config knobs, pitfalls, roadmap implications
- `.planning/research/STACK.md`, `ARCHITECTURE.md`, `FEATURES.md`, `PITFALLS.md` — detail behind SUMMARY (note: STACK.md & PITFALLS.md contain a SUPERSEDED "Max blocked" verdict — SUMMARY.md corrects it)
- `docs/claude-code-litellm-setup.md` — original ChatGPT reference; NON-AUTHORITATIVE, verify everything

### External first-party docs (verify against these, not blogs)
- LiteLLM "Using Claude Code Max Subscription": https://docs.litellm.ai/docs/tutorials/claude_code_max_subscription
- LiteLLM "Claude Code with Non-Anthropic Models": https://docs.litellm.ai/docs/tutorials/claude_non_anthropic_models
- LiteLLM Anthropic unified endpoint: https://docs.litellm.ai/docs/anthropic_unified
- LiteLLM proxy config: https://docs.litellm.ai/docs/proxy/configs
- Anthropic Claude Code LLM-gateway: https://code.claude.com/docs/en/llm-gateway
- Anthropic Claude Code authentication: https://code.claude.com/docs/en/iam
- Ollama Cloud: https://docs.ollama.com/cloud
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — greenfield. Only `docs/claude-code-litellm-setup.md` exists (unverified reference). No code, no prior config.

### Established Patterns
- Repo is git-initialized; `.planning/` is committed. New artifacts: `compose.yaml`/`config.yaml` committed, `.env` gitignored.

### Integration Points
- The gateway integrates with the host's Claude Code via `ANTHROPIC_BASE_URL`/`ANTHROPIC_AUTH_TOKEN` env (or `~/.claude/settings.json`). External: Anthropic API (Max OAuth) and Ollama Cloud (`https://ollama.com/v1`).
</code_context>

<specifics>
## Specific Ideas

- Single stable endpoint, never reconfigure Claude Code to switch models — only `claude --model <alias>`.
- "It's just a router for the Max sub" — the Claude path is Claude Code's own Max login forwarded; not an API key.
- Portability: `docker compose up`/`down`, everything committed except `.env`.
</specifics>

<deferred>
## Deferred Ideas

Already captured as v2 in REQUIREMENTS.md — do not build in Phase 1:
- Fallback chains / retries (REL-01)
- Gateway model discovery toggle (DISC-01)
- OpenAI + Gemini providers (PROV-01/02) — need paid API keys
- LiteLLM Admin UI / DB-backed hot-reload (OPS-01)

None — discussion stayed within phase scope.
</deferred>

---

*Phase: 1-Gateway + Feasibility Spike*
*Context gathered: 2026-05-20*
