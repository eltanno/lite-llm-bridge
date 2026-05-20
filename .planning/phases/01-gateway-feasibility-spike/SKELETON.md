# Walking Skeleton — LiteLLM Bridge

**Phase:** 1
**Generated:** 2026-05-20

## Capability Proven End-to-End

A developer runs `docker compose up -d`, points Claude Code at `http://localhost:4000` once, and reaches BOTH a Claude-Max-backed alias and an Ollama-Cloud-backed alias by changing only `--model <alias>` — with the Max subscription (not an API key) confirmed in use and a real agentic tool-use session completing through the Ollama path.

The thinnest end-to-end proof, in slice order:
1. Gateway is up and reachable (`/health` healthy), config validated for both backends at the static level, no secrets committed.
2. First real round-trip: `claude --model claude-sonnet "hello"` returns a correct Anthropic-shaped response routed through the gateway to Anthropic via forwarded Max OAuth; `/status` shows the Max subscription.
3. Agentic round-trip: `claude --model claude-haiku` completes a file-edit + bash tool-use session routed through the gateway to Ollama Cloud.

## Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Gateway | LiteLLM Proxy, image `ghcr.io/berriai/litellm:main-stable` | Named in Anthropic's Claude Code LLM-gateway docs; only proxy with a first-party Max OAuth forwarding tutorial. NEVER tag `latest`, NEVER PyPI 1.82.7/1.82.8 (confirmed credential-stealing malware). |
| Runtime | Docker Compose v2, single service, port 4000 | User requirement; stateless config-file-driven; `docker compose up/down`. No database (single-user PoC). |
| Config files | `compose.yaml` + `config.yaml`, both committed | `config.yaml` bind-mounted read-only at `/app/config.yaml`; holds the alias→backend `model_list` and settings, never secrets. |
| Secrets | gitignored `.env` (`LITELLM_MASTER_KEY`, `OLLAMA_API_KEY`) referenced via `os.environ/VAR_NAME`; committed `.env.example` with placeholders only | No secret is ever baked into the image or committed. Max OAuth credential is runtime-only (browser login), never an env var. |
| Alias → backend map | `claude-opus` → `anthropic/claude-opus-4-7` (Max); `claude-sonnet` → `anthropic/claude-sonnet-4-6` (Max); `claude-haiku` → `openai/qwen3-coder-next:cloud` @ `https://ollama.com/v1` (Ollama Cloud) | D-01. `claude-` prefix passes Claude Code's model-name filter (AL-01). Exercises both backend paths in one config. |
| Claude → Max auth | LiteLLM auth via `ANTHROPIC_CUSTOM_HEADERS="x-litellm-api-key: Bearer <master-key>"`; Max OAuth bearer rides in `Authorization` and is forwarded by LiteLLM to Anthropic. `ANTHROPIC_API_KEY` AND `ANTHROPIC_AUTH_TOKEN` MUST be unset in Claude Code's env. | D-03. `ANTHROPIC_AUTH_TOKEN` would occupy the `Authorization` header and collide with / replace the OAuth bearer; the two credentials must travel in separate headers. |
| Header forwarding scope | `model_group_settings.forward_client_headers_to_llm_api: [claude-opus, claude-sonnet]`; `drop_params: true`; `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1` for the Ollama session | D-05. Anthropic `anthropic-beta`/`anthropic-version` reach Claude backends but not Ollama. Empirical fallback (E-01): global `forward_client_headers_to_llm_api: true` — safe because no Anthropic key lives in the container. |
| Validation strategy | Agentic, not curl-only: real Claude Code tool-use session (file edit + bash) through the Ollama alias (OLL-02); `/status` confirms Max for the Claude alias (MAX-02) | D-07. Curl round-trips cannot validate tool_use/tool_result translation fidelity. |
| Directory layout | Flat repo root: `compose.yaml`, `config.yaml`, `.env`, `.env.example`, `.gitignore`, `README.md` | Single-service PoC; no source tree needed. |

## Stack Touched in Phase 1

- [x] Project scaffold — `compose.yaml` + `config.yaml` (the entire "build"; no language toolchain)
- [x] Routing — gateway exposes Anthropic Messages API at `localhost:4000`; three aliases resolve to two backends
- [x] "Database"/state — N/A (stateless proxy); the real read+write is proven via the agentic file-edit+bash session against the live backends
- [x] Real interaction wired to the API — `claude --model <alias>` drives real round-trips through the gateway to Anthropic (Max) and Ollama Cloud
- [x] Deployment — running locally via `docker compose up -d`; documented full-stack run command in README.md

## Out of Scope (Deferred to Later Slices)

These are explicitly NOT in the skeleton — do not re-litigate Phase 1's minimalism:

- Fallback chains / retries between backends (REL-01, v2)
- Gateway model discovery toggle so aliases appear in `/model` picker (DISC-01, v2)
- OpenAI + Gemini providers (PROV-01/02, v2 — require paid API keys)
- LiteLLM Admin UI + DB-backed hot-reload without restart (OPS-01, v2 — requires PostgreSQL)
- TLS, rate limiting, production hardening, observability stack
- Multi-user / networked / remote access (localhost-only binding)
- Hosting local on-device models (cloud backends only)
- Live/hot backend remap without restart (v1 = edit `config.yaml` + `docker compose restart`)
- Routing Claude via an Anthropic API key by default (intentionally using Max via OAuth forwarding; API key is a documented fallback only if forwarding proves broken on the pinned version — decision gate D-07)

## Subsequent Slice Plan

Each later phase adds one vertical slice on top of this skeleton without altering its architectural decisions:

- Phase 2 (v2): Reliability (fallbacks/retries) + DX (model discovery toggle, expanded README/startup docs)
- Phase 3 (v2): Provider expansion (OpenAI, Gemini) behind new aliases — gated on paid API keys existing
- Phase 4 (v2): Operations (Admin UI + DB-backed hot-reload via PostgreSQL)
