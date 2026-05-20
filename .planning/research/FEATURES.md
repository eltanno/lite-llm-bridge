# Feature Research: LiteLLM Gateway for Claude Code

**Domain:** Local LLM gateway — model aliasing, provider translation, Claude Code integration
**Researched:** 2026-05-20
**Confidence:** MEDIUM-HIGH (core mechanics verified against official docs; Claude Max OAuth path has a known bug history)

---

## Feature Landscape

### Table Stakes (Users Expect These)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Model aliasing via `model_name` in config.yaml | Core premise — `opus`/`sonnet`/`haiku` must map to arbitrary backends | LOW | Verified: `model_name` = user-facing alias; `litellm_params.model` = actual backend. Multiple entries with same `model_name` = load balancing. Source: [docs.litellm.ai/docs/proxy/configs](https://docs.litellm.ai/docs/proxy/configs) |
| Anthropic Messages API (`/v1/messages`) served to Claude Code | Claude Code sends Anthropic-format requests; gateway must accept them | LOW | Verified: LiteLLM's `/v1/messages` unified endpoint accepts Anthropic-format requests and translates to all supported providers. Source: [docs.litellm.ai/docs/anthropic_unified/](https://docs.litellm.ai/docs/anthropic_unified/) |
| `ANTHROPIC_BASE_URL` routing to gateway | Claude Code's single config change to reach the proxy | LOW | Verified by official Claude Code docs: `ANTHROPIC_BASE_URL=http://localhost:4000` redirects all requests; combined with the LiteLLM unified endpoint this is the canonical setup. Source: [code.claude.com/docs/en/llm-gateway](https://code.claude.com/docs/en/llm-gateway) |
| Per-invocation model selection via `claude --model <alias>` | User's mechanism for choosing a model each time | LOW | Verified: `--model` flag sets the model for that session only. Priority order: `/model` (in-session) > `--model` (startup) > `ANTHROPIC_MODEL` env > settings file. Source: [code.claude.com/docs/en/model-config](https://code.claude.com/docs/en/model-config) |
| Backend provider credentials kept outside the image | Secrets management hygiene | LOW | Standard Docker practice: pass via `.env` / environment variables; LiteLLM supports `os.environ/VAR_NAME` in config.yaml to reference env vars. |
| Container startup with a static config.yaml | Reproducible setup | LOW | Verified: `litellm --config /path/to/config.yaml` is the canonical startup command. Source: [docs.litellm.ai/docs/proxy/quick_start](https://docs.litellm.ai/docs/proxy/quick_start) |

---

### How Model Aliasing Actually Works

**Verified config.yaml structure** (HIGH confidence):

```yaml
model_list:
  - model_name: opus          # what claude --model opus sends
    litellm_params:
      model: anthropic/claude-opus-4-7   # actual backend
      api_key: os.environ/ANTHROPIC_API_KEY

  - model_name: sonnet
    litellm_params:
      model: anthropic/claude-sonnet-4-6
      api_key: os.environ/ANTHROPIC_API_KEY

  - model_name: haiku
    litellm_params:
      model: ollama_chat/qwen3-coder     # Ollama Cloud model
      api_base: https://ollama.com
      api_key: os.environ/OLLAMA_API_KEY
```

**Critical detail:** Claude Code's built-in `opus`/`sonnet`/`haiku` are *its own* resolution aliases pointing to `api.anthropic.com`. When `ANTHROPIC_BASE_URL` is set, Claude Code sends whatever string it resolves (`claude-opus-4-7`, `claude-sonnet-4-6`, etc.) to the gateway's `/v1/messages`. The gateway must have a `model_name` matching that string — **or** the operator must use `ANTHROPIC_DEFAULT_OPUS_MODEL`, `ANTHROPIC_DEFAULT_SONNET_MODEL`, `ANTHROPIC_DEFAULT_HAIKU_MODEL` env vars to override what Claude Code resolves the aliases to before sending.

**Simplest approach for this project:** Set `ANTHROPIC_DEFAULT_OPUS_MODEL=opus`, `ANTHROPIC_DEFAULT_SONNET_MODEL=sonnet`, `ANTHROPIC_DEFAULT_HAIKU_MODEL=haiku` so Claude Code sends the short alias strings, and define those exact strings as `model_name` in LiteLLM config. Source: [code.claude.com/docs/en/model-config](https://code.claude.com/docs/en/model-config) — HIGH confidence.

---

### How Claude Code Discovers Gateway Models

**Verified behavior** (HIGH confidence, source: [code.claude.com/docs/en/llm-gateway](https://code.claude.com/docs/en/llm-gateway)):

- By default, Claude Code does NOT query the gateway for available models.
- Setting `CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY=1` makes Claude Code query `/v1/models` at startup and add returned models to the `/model` picker.
- Discovery filter: only model IDs starting with `claude` or `anthropic` are added.
- Results cached to `~/.claude/cache/gateway-models.json`; refreshed each startup.
- Requires Claude Code v2.1.129 or later.

**Implication for this project:** If aliases are named `opus`/`sonnet`/`haiku` (not `claude-opus` etc.), discovery will not add them to the picker. Two options:
1. Name aliases `claude-opus`, `claude-sonnet`, `claude-haiku` — discovery works automatically.
2. Use `ANTHROPIC_DEFAULT_*_MODEL` overrides to map Claude Code's built-in aliases to the gateway names — no discovery needed, picker shows the built-in aliases.

Option 2 is cleaner for v1. The ChatGPT doc's recommendation of `CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY=1` is **real and documented**, but irrelevant if using Option 2.

---

### Anthropic Messages API Translation by Provider

**Verified** (HIGH confidence, source: [docs.litellm.ai/docs/anthropic_unified/](https://docs.litellm.ai/docs/anthropic_unified/)):

| Provider | Translation Needed | Notes |
|----------|--------------------|-------|
| `anthropic/claude-*` | None (native) | Direct passthrough |
| `openai/gpt-*` | Yes — LiteLLM handles it | Format differences abstracted |
| `gemini/*`, `vertex_ai/*` | Yes — LiteLLM handles it | |
| `bedrock/*` | Yes — LiteLLM handles it | |
| `ollama_chat/*` | Yes — LiteLLM handles it | Ollama uses its own native format |

LiteLLM's `/v1/messages` unified endpoint handles all provider translation. Claude Code talks Anthropic format; LiteLLM translates outbound and translates responses back. This is the core compatibility guarantee.

**The ChatGPT doc claim "Ollama exposes Anthropic-compatible endpoints"** is FALSE/MISLEADING. Ollama's native API (`/api/chat`) is its own format. LiteLLM's `ollama_chat/` provider prefix instructs LiteLLM to translate. The `anthropic_unified` endpoint in LiteLLM is what provides Anthropic compatibility — not Ollama itself.

---

### Differentiators (Available but Not Required for v1)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Fallbacks between model groups | Automatic failover if a backend is down or rate-limited | LOW | Config: `litellm_settings: fallbacks: [{"opus": ["sonnet"]}]`. No DB required. Source: [docs.litellm.ai/docs/proxy/reliability](https://docs.litellm.ai/docs/proxy/reliability) |
| Retries within a model group | Resilience against transient errors | LOW | `litellm_settings: num_retries: 3`. Works without DB. |
| Context-window fallbacks | Graceful handling of token limit errors | LOW | `context_window_fallbacks: [{"opus": ["haiku"]}]` |
| Load balancing across multiple backends for one alias | Distribute load across e.g. multiple Anthropic keys | LOW | Define multiple `model_list` entries with the same `model_name` |
| LiteLLM Admin UI | Visual model management without config edits | HIGH | **Requires PostgreSQL database.** Not available in DB-free config. |
| Dynamic model add via `/model/new` API | Add models at runtime without restart | MEDIUM | Available in the open-source proxy; requires a running proxy with master_key set. Without DB, changes are not persistent across restarts. |
| `CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY=1` | Populates Claude Code `/model` picker from gateway `/v1/models` | LOW | Only useful if model names start with `claude` or `anthropic`. Requires v2.1.129+. |
| `ANTHROPIC_CUSTOM_MODEL_OPTION` | Inject a single custom model into the `/model` picker | LOW | Workaround for models that don't match the discovery filter. |

---

### Anti-Features (Avoid for v1)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| LiteLLM Admin UI + PostgreSQL | Nice visual model management | Requires Postgres container; adds significant complexity for a local single-user PoC. Virtual keys, spend tracking, UI all coupled to DB. | Config-file-only mode (no DB) works for v1. Add UI in v2+ if needed. |
| Virtual keys (per-user key management) | Security best practice in multi-user environments | Meaningless for single-user local setup; requires DB. | Set a static `master_key` in config.yaml or omit it entirely. Source: [docs.litellm.ai/docs/proxy/quick_start](https://docs.litellm.ai/docs/proxy/quick_start) confirms proxy runs without master_key. |
| Hot-reload / live config swap without restart | Appealing for backend remapping | Relies on DB-backed model storage (`store_model_in_db`) — the DB dependency is the cost. Without DB, config changes require container restart. Restart is trivial locally. | Restart the container. v1 scope says this is out of scope anyway. |
| Wildcard routing (`anthropic/*`) | Expose all provider models dynamically | Bypasses the stable-alias guarantee; Claude Code would receive unpredictable model IDs | Explicit `model_list` entries only |
| OpenAI/Gemini providers in v1 | More model options | Out of scope per PROJECT.md; their consumer subscriptions (ChatGPT, Gemini) are NOT API access — require paid API keys | Defer to v2+ |

---

## Auth: What is Actually Required for Localhost Single-User

**Verified** (MEDIUM confidence — multiple sources cross-checked):

- **Without `master_key`**: All requests are treated as proxy admin. No auth enforced. Proxy runs. Source: config_settings docs state master_key is optional; quick_start shows a working proxy without it.
- **Without `DATABASE_URL`**: Basic `/chat/completions` and `/v1/messages` calls work. You lose: virtual keys, spend tracking, the Admin UI. This is the correct v1 posture.
- **Simplest v1 auth config**: Either omit `general_settings` entirely, or set a static `master_key` (then set `ANTHROPIC_AUTH_TOKEN=<that key>` on the Claude Code side). The master_key prevents other processes on the machine from calling the proxy without knowing the key — a minor but reasonable precaution.

**For Claude Code to authenticate with the gateway:** Set `ANTHROPIC_AUTH_TOKEN=<master_key_value>`. Claude Code sends this as the `Authorization` header; LiteLLM validates it against `master_key`. Source: [code.claude.com/docs/en/llm-gateway](https://code.claude.com/docs/en/llm-gateway).

---

## Claude Max Subscription Routing: PRIMARY RISK ITEM

**Status:** Documented path exists in LiteLLM, but has a known bug history. HIGH caution warranted.

**What the LiteLLM docs say** (MEDIUM confidence):
- Tutorial at [docs.litellm.ai/docs/tutorials/claude_code_max_subscription](https://docs.litellm.ai/docs/tutorials/claude_code_max_subscription) describes routing Claude Code's Max subscription OAuth tokens through LiteLLM via `forward_client_headers_to_llm_api: true`.
- Mechanism: Claude Code authenticates with Anthropic via browser OAuth; its OAuth token is forwarded through LiteLLM to Anthropic. LiteLLM authenticates the gateway connection separately via `x-litellm-api-key`.

**Known bug** (confirmed via GitHub issue #19618):
- OAuth token forwarding was broken in at least LiteLLM v1.81.2. Root causes: `clean_headers()` strips Authorization header; `_get_forwardable_headers()` doesn't forward it; OAuth handler sets `x-api-key` instead of `Authorization: Bearer`.
- Issue was closed via PR #19912 — fix merged. Current status of the fix in the latest stable release is **unverified**.
- The ChatGPT doc claim "LiteLLM can route Claude Code traffic while preserving Claude workflows" with Max is directionally correct but glosses over this implementation fragility.

**Alternative approach to consider:** Use an Anthropic API key instead of Claude Max OAuth. This costs per-token but is a simpler and more reliable LiteLLM integration. If the goal is to avoid API billing and reuse the Max subscription, the OAuth forwarding path is the only option — and must be validated against the current LiteLLM release before committing.

**This is the primary feasibility risk for the project and must be the first thing validated in Phase 1.**

---

## Ollama Cloud Routing

**Verified** (MEDIUM confidence):

- Ollama Cloud API endpoint: `https://ollama.com/api/chat`
- Auth: Bearer token from ollama.com/settings/keys (set as `OLLAMA_API_KEY`)
- **No local Ollama daemon required.** Ollama Cloud is a direct remote API.
- The ChatGPT doc's Option A (local daemon → Ollama Cloud) is a valid but unnecessary architecture. Direct API access (`api_base: https://ollama.com`) is cleaner for this use case.
- LiteLLM config for direct Ollama Cloud: `model: ollama_chat/<model-name>`, `api_base: https://ollama.com`, `api_key: os.environ/OLLAMA_API_KEY`.

**Claim in ChatGPT doc: `ollama_chat/qwen3-coder:cloud` + `api_base: http://localhost:11434`** — the `:cloud` tag suffix is unverified in official Ollama docs. Official Ollama Cloud docs show direct cloud API access without a local daemon. Flag this claim as LOW confidence / unverified.

---

## Feature Dependencies

```
Claude Code model selection (--model opus)
    └──requires──> Model alias defined in LiteLLM config
                       └──requires──> ANTHROPIC_BASE_URL points to gateway
                                          └──requires──> LiteLLM container running

Anthropic Messages API translation
    └──requires──> LiteLLM /v1/messages unified endpoint (built-in, no extra config)

Claude Max subscription routing
    └──requires──> forward_client_headers_to_llm_api: true
    └──requires──> Claude Code authenticated with Max account (browser OAuth)
    └──RISK──> OAuth forwarding bug must be verified fixed in target LiteLLM version

Fallbacks / retries
    └──requires──> Aliases defined (can fall back between named groups)
    └──optional──> No DB needed

Admin UI
    └──requires──> PostgreSQL database  [OUT OF SCOPE v1]
    └──requires──> master_key set

Hot reload without restart
    └──requires──> PostgreSQL + store_model_in_db  [OUT OF SCOPE v1]
```

---

## MVP Definition

### Launch With (v1)

- [x] `model_list` in config.yaml with `opus`/`sonnet`/`haiku` aliases pointing to Claude Max (Anthropic) and Ollama Cloud backends
- [x] LiteLLM proxy in Docker, no database, no Admin UI
- [x] `ANTHROPIC_BASE_URL=http://localhost:4000` set once in Claude Code environment
- [x] `ANTHROPIC_DEFAULT_OPUS_MODEL=opus` (and sonnet/haiku) to align Claude Code's built-in alias resolution with LiteLLM model names
- [x] Static `master_key` in config for minimal local protection; `ANTHROPIC_AUTH_TOKEN` set on Claude Code side
- [x] Claude Max OAuth forwarding validated against target LiteLLM release — **must pass before the project can proceed**

### Add After Validation (v1.x)

- [ ] Fallbacks — add `litellm_settings: fallbacks` once both backends are working; simple one-line config change
- [ ] `CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY=1` — evaluate only if model names are renamed to `claude-*` prefix

### Future Consideration (v2+)

- [ ] LiteLLM Admin UI + PostgreSQL — when managing multiple aliases becomes unwieldy via config edits
- [ ] OpenAI / Gemini providers — after v1 validates the pattern; requires paid API keys (consumer subscriptions do not apply)
- [ ] Hot reload / `store_model_in_db` — only if alias reconfiguration frequency justifies DB complexity

---

## Verification of ChatGPT Doc Claims

| Claim | Status | Source |
|-------|--------|--------|
| `CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY=1` exists | CONFIRMED — real, documented | [code.claude.com/docs/en/llm-gateway](https://code.claude.com/docs/en/llm-gateway) |
| "Ollama exposes Anthropic-compatible endpoints" | FALSE / MISLEADING — it is LiteLLM that provides Anthropic compatibility, not Ollama | [docs.litellm.ai/docs/anthropic_unified/](https://docs.litellm.ai/docs/anthropic_unified/) |
| Ollama Cloud via local daemon `ollama_chat/<model>:cloud` + `localhost:11434` | UNVERIFIED — official Ollama Cloud docs show direct cloud API; `:cloud` tag suffix not in official docs | [docs.ollama.com/cloud](https://docs.ollama.com/cloud) |
| Claude Max can be routed through LiteLLM | CONDITIONALLY TRUE — documented path exists; OAuth forwarding has known bug history | [docs.litellm.ai/docs/tutorials/claude_code_max_subscription](https://docs.litellm.ai/docs/tutorials/claude_code_max_subscription), [github.com/BerriAI/litellm/issues/19618](https://github.com/BerriAI/litellm/issues/19618) |

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Model aliasing (config.yaml) | HIGH | LOW | P1 |
| Anthropic Messages API translation | HIGH | LOW (built-in) | P1 |
| Claude Code ANTHROPIC_BASE_URL wiring | HIGH | LOW | P1 |
| Claude Max OAuth forwarding | HIGH | MEDIUM (risk: bug) | P1 |
| Ollama Cloud routing | HIGH | LOW-MEDIUM | P1 |
| Static master_key auth | MEDIUM | LOW | P1 |
| Fallbacks / retries | MEDIUM | LOW | P2 |
| Gateway model discovery | LOW | LOW | P2 |
| LiteLLM Admin UI | LOW | HIGH (needs DB) | P3 |
| Hot reload | LOW | HIGH (needs DB) | P3 |

---

## Sources

- [LiteLLM Proxy Config Overview](https://docs.litellm.ai/docs/proxy/configs) — aliasing, model_list structure
- [LiteLLM /v1/messages Unified Endpoint](https://docs.litellm.ai/docs/anthropic_unified/) — Anthropic format + provider translation
- [LiteLLM Fallbacks](https://docs.litellm.ai/docs/proxy/reliability) — fallback/retry config syntax
- [LiteLLM Virtual Keys](https://docs.litellm.ai/docs/proxy/virtual_keys) — auth requirements
- [LiteLLM Quick Start](https://docs.litellm.ai/docs/proxy/quick_start) — minimal no-DB setup
- [LiteLLM Claude Max Tutorial](https://docs.litellm.ai/docs/tutorials/claude_code_max_subscription) — Claude Max subscription routing
- [LiteLLM Model Management](https://docs.litellm.ai/docs/proxy/model_management) — runtime model add API
- [Claude Code Model Config](https://code.claude.com/docs/en/model-config) — --model flag, alias resolution, env vars
- [Claude Code LLM Gateway](https://code.claude.com/docs/en/llm-gateway) — ANTHROPIC_BASE_URL, gateway requirements, CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY
- [Ollama Cloud Docs](https://docs.ollama.com/cloud) — direct cloud API, no local daemon needed
- [LiteLLM OAuth Bug #19618](https://github.com/BerriAI/litellm/issues/19618) — OAuth forwarding bug history

---
*Feature research for: LiteLLM local gateway for Claude Code*
*Researched: 2026-05-20*
