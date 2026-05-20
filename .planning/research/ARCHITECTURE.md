# Architecture Research

**Domain:** Local LiteLLM gateway for Claude Code — semantic model aliasing proxy
**Researched:** 2026-05-20
**Confidence:** HIGH (all key claims verified against official LiteLLM docs, official Claude Code docs, and Ollama Cloud docs)

---

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│  CLAUDE CODE (host machine)                                          │
│  ANTHROPIC_BASE_URL=http://localhost:4000                            │
│  claude --model opus | sonnet | haiku                                │
└───────────────────────────┬─────────────────────────────────────────┘
                            │  HTTP  Anthropic Messages API format
                            │  POST /v1/messages
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│  DOCKER CONTAINER  (localhost:4000)                                  │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  LiteLLM Proxy                                                │  │
│  │                                                               │  │
│  │  Receives Anthropic Messages API request                      │  │
│  │  Looks up model alias in config.yaml model_list               │  │
│  │  ↓                                                            │  │
│  │  Route A (Claude):  forwards verbatim + OAuth token header    │  │
│  │  Route B (Ollama Cloud): translates → OpenAI chat format      │  │
│  │  ↓                                                            │  │
│  │  Translates response back → Anthropic Messages format         │  │
│  │  Returns to Claude Code                                       │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  config.yaml    (bind-mounted volume, not baked into image)          │
│  .env           (secrets, not baked into image)                      │
└──────┬──────────────────────────────────────────────────────────────┘
       │
       ├──── A: ANTHROPIC API  (api.anthropic.com/v1/messages)
       │         auth: Bearer {oauth_token forwarded from Claude Code}
       │
       └──── B: OLLAMA CLOUD   (https://ollama.com/v1)
                auth: Authorization: Bearer {OLLAMA_API_KEY}
```

---

## 1. End-to-End Data Flow and Translation Responsibility

**Claim in docs/claude-code-litellm-setup.md:** LiteLLM translates Anthropic API requests.
**Verdict: CONFIRMED.** LiteLLM's `/v1/messages` endpoint is the authoritative translation point.

### How it works

Claude Code always speaks Anthropic Messages API (`POST /v1/messages`). When `ANTHROPIC_BASE_URL` points at the LiteLLM proxy, every request lands at LiteLLM in Anthropic format. LiteLLM then:

1. Receives the request in Anthropic Messages API format.
2. Looks up the requested model name in `model_list` in `config.yaml`.
3. Determines the backend provider from `litellm_params.model`.
4. If the backend is Anthropic: passes the request through with minimal transformation (forwards required headers `anthropic-beta`, `anthropic-version`).
5. If the backend is a non-Anthropic provider (e.g., OpenAI-compatible): translates parameters into that provider's format, sends request, receives response, translates response back into Anthropic Messages API format.
6. Returns the Anthropic-format response to Claude Code.

Translation is entirely LiteLLM's responsibility. Claude Code does not know or care what is downstream. This is the core architectural value of the proxy.

**Source (HIGH confidence):**
- [LiteLLM /v1/messages endpoint docs](https://docs.litellm.ai/docs/anthropic_unified/)
- [Claude Code LLM gateway requirements](https://code.claude.com/docs/en/llm-gateway) — confirms gateway must expose `/v1/messages` and forward `anthropic-beta`/`anthropic-version` headers
- [LiteLLM non-Anthropic models tutorial](https://docs.litellm.ai/docs/tutorials/claude_non_anthropic_models)

### Critical header forwarding requirement

The Claude Code gateway docs explicitly state the gateway must forward `anthropic-beta` and `anthropic-version` request headers, or Claude Code features will degrade. LiteLLM's unified `/v1/messages` endpoint handles this automatically. The pass-through endpoint (`/anthropic`) also does this correctly.

---

## 2. Claude Access Options: Three Architectural Shapes

### Option A: Anthropic API Key (token-billed)

**Shape:**
```
Claude Code → LiteLLM proxy → api.anthropic.com (API key, pay-per-token)
```

**Mechanics:**
- LiteLLM holds an `ANTHROPIC_API_KEY` in `.env`.
- Config: `model: anthropic/claude-sonnet-4-20250514` (or whichever model).
- LiteLLM authenticates to Anthropic using the API key on every request.
- Claude Code authenticates to LiteLLM with `ANTHROPIC_AUTH_TOKEN` (sent as `Authorization: Bearer`).

**Config YAML:**
```yaml
model_list:
  - model_name: sonnet
    litellm_params:
      model: anthropic/claude-sonnet-4-20250514
      api_key: os.environ/ANTHROPIC_API_KEY
```

**Feasibility:** HIGH — standard, fully documented, production-grade.

**Cost implication:** Incurs Anthropic API token billing. Defeats the goal of reusing Claude Max.

---

### Option B: Claude Max Subscription via OAuth Token Forwarding (PRIMARY HYPOTHESIS)

**Shape:**
```
Claude Code  →  LiteLLM proxy  →  api.anthropic.com
   [OAuth token in Authorization header]
   [x-litellm-api-key header for LiteLLM auth]
         |
         LiteLLM forwards the OAuth token verbatim
         to Anthropic, which validates against Max subscription
```

**Mechanics (verified against official LiteLLM docs):**

When a user runs `claude` without `ANTHROPIC_API_KEY`, Claude Code authenticates via Anthropic's OAuth flow (browser-based login) and obtains an OAuth Bearer token. That token is sent in the `Authorization` header on every request.

When LiteLLM has `forward_client_headers_to_llm_api: true` in `general_settings`, it passes this `Authorization` header directly to Anthropic's API, allowing Anthropic to validate the Max subscription rather than an API key.

Claude Code sends two relevant headers simultaneously:
- `Authorization: Bearer {oauth_token}` — for Anthropic subscription validation
- `x-litellm-api-key: Bearer {litellm_virtual_key}` — for LiteLLM gateway auth (via `ANTHROPIC_CUSTOM_HEADERS`)

**Required config.yaml:**
```yaml
model_list:
  - model_name: sonnet
    litellm_params:
      model: anthropic/claude-sonnet-4-20250514

  - model_name: opus
    litellm_params:
      model: anthropic/claude-opus-4-20250514

  - model_name: haiku
    litellm_params:
      model: anthropic/claude-haiku-4-20250514

general_settings:
  forward_client_headers_to_llm_api: true

litellm_settings:
  master_key: os.environ/LITELLM_MASTER_KEY
```

**Required Claude Code env vars:**
```bash
export ANTHROPIC_BASE_URL=http://localhost:4000
export ANTHROPIC_CUSTOM_HEADERS="x-litellm-api-key: Bearer {litellm_virtual_key}"
# ANTHROPIC_API_KEY must NOT be set — its presence overrides OAuth flow
```

**Source (MEDIUM confidence — officially documented but marked experimental by risk):**
- [LiteLLM Claude Code Max Subscription tutorial](https://docs.litellm.ai/docs/tutorials/claude_code_max_subscription) — documents this exact flow
- [Claude Code env-vars docs](https://code.claude.com/docs/en/env-vars) — confirms `ANTHROPIC_AUTH_TOKEN`/`ANTHROPIC_CUSTOM_HEADERS` mechanics

**Feasibility assessment:** Mechanically documented. PRIMARY RISK: Anthropic may rate-limit, reject, or invalidate OAuth tokens used through third-party proxies. The Pitfalls researcher should investigate this separately. The *architecture* is well-defined; the *policy* feasibility is the unknown.

**Do NOT set `ANTHROPIC_API_KEY`** in the environment when using this option — its presence overrides the OAuth flow regardless of `ANTHROPIC_BASE_URL`.

---

### Option C: Hybrid — Claude Code Uses Max Directly; LiteLLM Only Fronts Ollama

**Shape:**
```
Claude Code (Max subscription, direct to Anthropic) — no proxy for Claude
Claude Code (--model haiku) → LiteLLM proxy → Ollama Cloud
```

**Mechanics:**

This requires two separate `ANTHROPIC_BASE_URL` values — one for Claude aliases, one for Ollama. Claude Code does not support per-model base URL overrides; `ANTHROPIC_BASE_URL` is global. **This architecture is not achievable with a single Claude Code instance.**

The workaround is to NOT use `ANTHROPIC_BASE_URL` at all (Claude Code goes to Anthropic directly for all Claude models), and run the proxy only for Ollama — but then you lose the unified gateway benefit and cannot use `claude --model haiku` to reach Ollama through the proxy.

**Feasibility: NOT RECOMMENDED for this project.** It undermines the "single stable endpoint" requirement. If Option B proves unworkable, fall back to Option A (pay API billing for Claude) rather than Option C.

---

## 3. Ollama Cloud Routing: Option A vs Option B

### Official Ollama Cloud API

**Verified:** Ollama Cloud exposes two interfaces:
1. **Native Ollama API:** `https://ollama.com/api/chat` — requires `Authorization: Bearer {OLLAMA_API_KEY}` header
2. **OpenAI-compatible API:** `https://ollama.com/v1` — accepts `Authorization: Bearer {OLLAMA_API_KEY}`, OpenAI chat format

No local daemon required for either. API keys created at `ollama.com/settings/keys`.

**Source (MEDIUM confidence):**
- [Ollama Cloud official docs](https://docs.ollama.com/cloud)
- [Fabio Rehm blog post on Ollama Cloud API](https://fabiorehm.com/blog/2026/04/12/pi-ollama-cloud-api/) — practical verification; notes `https://ollama.com/v1` is the correct OpenAI-compatible base, not `/api/v1`

---

### Option A: LiteLLM → Local Ollama Daemon → Ollama Cloud

**Shape:**
```
LiteLLM proxy → http://localhost:11434 (local Ollama daemon) → Ollama Cloud
```

**Claim in docs/claude-code-litellm-setup.md:** "Officially documented, stable, easiest setup."
**Verdict: PARTIALLY ACCURATE.** Using `ollama_chat/model:cloud` with a local daemon routes through Ollama Cloud, but calling it "officially documented" in the LiteLLM sense is misleading — LiteLLM's Ollama provider docs describe only local Ollama. The `:cloud` suffix behavior is Ollama daemon behavior, not LiteLLM behavior.

**Config YAML:**
```yaml
model_list:
  - model_name: haiku
    litellm_params:
      model: ollama_chat/qwen3-coder:cloud
      api_base: http://localhost:11434
      # No api_key needed — local daemon handles Ollama Cloud auth
```

**Docker networking note:** When LiteLLM runs in Docker and Ollama daemon runs on the host, `api_base` must be `http://host.docker.internal:11434` (Linux: may require `--add-host=host.docker.internal:host-gateway`).

**Requirements:** Local Ollama daemon installed and running. User authenticated via `ollama signin`.

**Feasibility:** MEDIUM — adds a required process (Ollama daemon) the user does not currently run. Introduces a process-management dependency outside Docker. The `:cloud` suffix behavior should be verified against Ollama daemon documentation.

---

### Option B: LiteLLM → Ollama Cloud API Directly (No Local Daemon)

**Shape:**
```
LiteLLM proxy → https://ollama.com/v1 (Ollama Cloud OpenAI-compatible API)
```

**Claim in docs/claude-code-litellm-setup.md:** "Less battle-tested, some auth/header issues exist."
**Verdict: VERIFIABLE IN PRINCIPLE.** Ollama Cloud exposes an OpenAI-compatible endpoint at `https://ollama.com/v1`. LiteLLM supports calling any OpenAI-compatible endpoint using the `openai/` model prefix. This is architecturally sound.

**Config YAML:**
```yaml
model_list:
  - model_name: haiku
    litellm_params:
      model: openai/qwen3-coder   # openai/ prefix for OpenAI-compatible endpoint
      api_base: https://ollama.com/v1
      api_key: os.environ/OLLAMA_API_KEY

  - model_name: opus
    litellm_params:
      model: openai/deepseek-r1
      api_base: https://ollama.com/v1
      api_key: os.environ/OLLAMA_API_KEY
```

**Authentication:** `OLLAMA_API_KEY` in `.env`, from `ollama.com/settings/keys`.

**Source (MEDIUM confidence):**
- [LiteLLM OpenAI-compatible endpoints docs](https://docs.litellm.ai/docs/providers/openai_compatible) — confirms `openai/` prefix + custom `api_base` pattern
- [Ollama Cloud docs](https://docs.ollama.com/cloud) — confirms direct API key access
- [Fabio Rehm blog](https://fabiorehm.com/blog/2026/04/12/pi-ollama-cloud-api/) — confirms `https://ollama.com/v1` endpoint, no local daemon

**Feasibility:** MEDIUM-HIGH. No daemon required; simpler operational model. The only caveat is that no official LiteLLM documentation specifically tests `ollama.com/v1` as a target — it must be treated as "OpenAI-compatible endpoint" which is a well-supported generic path.

---

### Recommendation: Option B (Direct Cloud API)

Use Option B for this project. Rationale:

1. **No local daemon.** The user does not currently run Ollama. Option A would require installing, running, and managing a persistent Ollama daemon process outside Docker — adding operational complexity that is unnecessary for this use case.
2. **Simpler Docker compose.** Option B needs only the LiteLLM container. Option A requires either the daemon runs on the host (networking complexity) or a second container.
3. **PROJECT.md explicitly states:** "Hosting local models on this machine" is out of scope, and Ollama daemon installation is only warranted "if research confirms it is required." It is not required.
4. **Architecturally cleaner.** The `openai/` prefix + `api_base` pattern is well-established in LiteLLM for any OpenAI-compatible endpoint; no special-casing needed.
5. **LiteLLM response-format concern:** LiteLLM must translate OpenAI-format responses from Ollama Cloud back into Anthropic Messages format before returning to Claude Code. This is LiteLLM's standard job for the unified `/v1/messages` endpoint and is not specific to Ollama.

The docs reference's "auth/header issues" claim is unverified and unsourced — treat it as LOW confidence. Verify in implementation by testing with `curl`.

---

## 4. Component Boundaries, Config/Secrets, and Build Order

### Component Boundaries

| Component | Responsibility | Lives Where |
|-----------|---------------|-------------|
| Claude Code | Issues Anthropic Messages API requests; selects model via `--model` | Host machine |
| LiteLLM proxy | Receives requests, resolves aliases, translates formats, forwards to providers | Docker container, port 4000 |
| `config.yaml` | Defines `model_list` (alias → backend mapping), general_settings | Bind-mounted volume: `./config.yaml:/app/config.yaml` |
| `.env` | Secrets: `LITELLM_MASTER_KEY`, `OLLAMA_API_KEY`, optionally `ANTHROPIC_API_KEY` | Host filesystem, never in image |
| Ollama Cloud | Hosts open models (qwen, deepseek, kimi, etc.) | External: `https://ollama.com/v1` |
| Anthropic API | Hosts Claude models | External: `https://api.anthropic.com` |

### Where Config and Secrets Live

```
lite-llm-bridge/
├── docker-compose.yml      # service definition, port mapping, volume mounts
├── config.yaml             # model_list and LiteLLM settings (NOT secret, version-control safe)
├── .env                    # secrets (gitignored)
│   ├── LITELLM_MASTER_KEY  # LiteLLM gateway auth key
│   └── OLLAMA_API_KEY      # Ollama Cloud auth key
└── docs/
    └── claude-code-setup.md  # how to set ANTHROPIC_BASE_URL on the host
```

`config.yaml` is NOT a secret — it contains model routing but no credentials. All API keys are in `.env` and referenced as `os.environ/VAR_NAME` in config.yaml.

### Build Order (Dependency Chain for Roadmap)

The component dependencies determine a natural build order:

```
1. Docker/compose scaffold (no dependencies)
       ↓
2. LiteLLM container starts with minimal config.yaml (validates proxy is reachable)
       ↓
3. Claude Code → LiteLLM connectivity (ANTHROPIC_BASE_URL works, auth works)
       ↓ (splits into two parallel tracks)
4a. Ollama Cloud integration          4b. Claude Max / Anthropic integration
    (Option B: openai/ + api_base)        (Option B: OAuth forwarding)
    Unambiguous feasibility               PRIMARY RISK — validate first or in parallel
       ↓                                         ↓
5. Semantic alias verification (all three aliases work end-to-end)
       ↓
6. Developer experience (env var documentation, startup script)
```

**Build-order implication for roadmap phases:**

- Phase 1 should be the scaffold + LiteLLM container with a trivial working model (an Anthropic model with a real API key is the simplest possible first test — Option A — even if the goal is Option B).
- Phase 2 should validate Ollama Cloud (Option B) as it is lower risk.
- Phase 3 should attempt Claude Max OAuth forwarding (Option B for Claude). This is the primary risk; if it fails, the fallback is API-key billing (Option A), which must be decided before v1 is declared complete.
- Semantic aliases (`opus`/`sonnet`/`haiku`) are a config concern, not a new component; they can be added to config.yaml as early as Phase 1.

---

## Architectural Patterns

### Pattern 1: Unified Anthropic Messages Endpoint (Recommended)

**What:** All routes use LiteLLM's `/v1/messages` endpoint. Claude Code sets only `ANTHROPIC_BASE_URL`.
**When to use:** Always for this project.
**Trade-offs:**
- Pro: Single env var (`ANTHROPIC_BASE_URL`), full LiteLLM features (fallbacks, logging, cost tracking).
- Pro: LiteLLM handles all format translation.
- Con: LiteLLM must correctly implement parameter translation for every provider used.

### Pattern 2: Pass-Through Endpoint (Alternative, not recommended for v1)

**What:** `ANTHROPIC_BASE_URL=http://localhost:4000/anthropic` — LiteLLM proxies Anthropic verbatim without translation.
**When to use:** Only if you only route to Anthropic (no non-Claude backends) and want to minimize LiteLLM involvement.
**Trade-offs:**
- Pro: No translation risk for Anthropic calls.
- Con: Cannot route to non-Anthropic backends through the same base URL.
- Not applicable for this project's Ollama requirement.

### Pattern 3: `os.environ/VAR_NAME` for Secrets in config.yaml

**What:** Reference secrets by environment variable name in config.yaml rather than hardcoding.
**When to use:** Always.
**Trade-offs:**
- Pro: config.yaml stays safe to commit; secrets remain in `.env`.
- LiteLLM natively supports this syntax.

---

## Anti-Patterns

### Anti-Pattern 1: Setting ANTHROPIC_API_KEY When Targeting Claude Max

**What people do:** Set both `ANTHROPIC_BASE_URL` and `ANTHROPIC_API_KEY` when testing.
**Why it's wrong:** `ANTHROPIC_API_KEY` presence in Claude Code's environment overrides the OAuth flow even when `ANTHROPIC_BASE_URL` is set. Claude Code uses the API key directly and bills against it, bypassing the Max subscription. This is documented in official Claude Code env-var docs.
**Do this instead:** Use `ANTHROPIC_AUTH_TOKEN` (for LiteLLM virtual key) and `ANTHROPIC_CUSTOM_HEADERS` (for `x-litellm-api-key`), never `ANTHROPIC_API_KEY`, when the intent is Max subscription reuse.

### Anti-Pattern 2: Baking Secrets Into the Docker Image

**What people do:** Put API keys in the Dockerfile or as ENV directives in the image.
**Why it's wrong:** Keys end up in image layers, git history, and container inspect output.
**Do this instead:** Use `.env` with docker-compose `env_file:` directive. Reference in config.yaml via `os.environ/VAR_NAME`.

### Anti-Pattern 3: Using `:cloud` Suffix with Direct Ollama Cloud API

**What people do:** Combine `ollama_chat/model:cloud` with `api_base: https://ollama.com/v1`.
**Why it's wrong:** The `:cloud` suffix is interpreted by the local Ollama daemon to offload execution to Ollama Cloud. If there is no local daemon, the `:cloud` suffix is meaningless or will error. The direct cloud API route (Option B) uses `openai/model-name` without the `:cloud` suffix.
**Do this instead:** Use `openai/qwen3-coder` + `api_base: https://ollama.com/v1` for Option B.

### Anti-Pattern 4: Trusting Unverified "Claude Code CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY" Env Var Advice

**Note — this is NOT an anti-pattern; it IS real.** The docs/claude-code-litellm-setup.md reference listed it without source. Verified: `CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY=1` is a real, documented env var (Claude Code v2.1.129+) that queries `/v1/models` at startup and populates the `/model` picker. It is optional and off by default. Useful once the gateway is working, not needed for v1 bootstrap.

---

## Integration Points

### External Services

| Service | Integration Pattern | Auth | Notes |
|---------|---------------------|------|-------|
| Anthropic API | LiteLLM forwards to `api.anthropic.com/v1/messages` | OAuth token (forwarded) or API key | Must forward `anthropic-beta`, `anthropic-version` headers |
| Ollama Cloud | LiteLLM calls `https://ollama.com/v1` as OpenAI-compatible endpoint | `OLLAMA_API_KEY` Bearer token | `openai/` model prefix; no local daemon |
| Claude Code | Connects to LiteLLM at `localhost:4000` | `ANTHROPIC_AUTH_TOKEN` → LiteLLM virtual key | `ANTHROPIC_BASE_URL` set once |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Claude Code ↔ LiteLLM | HTTP/1.1 to `localhost:4000` | LiteLLM exposes Anthropic Messages API format |
| LiteLLM ↔ config.yaml | File read at startup (or hot reload if configured) | Bind-mounted volume |
| LiteLLM ↔ .env | Environment variables injected at container start | Via docker-compose `env_file:` |

---

## Claims in docs/claude-code-litellm-setup.md: Verification Summary

| Claim | Status | Finding |
|-------|--------|---------|
| "Ollama exposes Anthropic-compatible endpoints" | REFUTED | Ollama Cloud exposes native Ollama API + OpenAI-compatible API. NOT Anthropic-compatible natively. LiteLLM handles the translation. |
| `ollama_chat/<model>:cloud` + `api_base: http://localhost:11434` | PARTIALLY CORRECT | Works IF a local Ollama daemon is running. The daemon routes `:cloud` to Ollama Cloud. Not needed if using direct cloud API (Option B). |
| "Claude Max can be routed through LiteLLM" | PLAUSIBLE | Officially documented by LiteLLM. Policy feasibility (Anthropic ToS/rate limits) is the open risk. Architecture is sound. |
| `CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY=1` | CONFIRMED | Real env var, Claude Code v2.1.129+. Documented at code.claude.com/docs/en/llm-gateway. |
| "Anthropic API compatibility already handled" (for Ollama) | MISLEADING | Compatibility is handled by LiteLLM, not Ollama. Ollama itself is not Anthropic-compatible. |
| "Option A (via local daemon) is officially documented" | MISLEADING | Local Ollama daemon usage is documented in LiteLLM's Ollama provider page. The `:cloud` suffix behavior is Ollama daemon behavior, not a LiteLLM feature. |

---

## Sources

- [LiteLLM LLM gateway config (official)](https://code.claude.com/docs/en/llm-gateway) — HIGH confidence; gateway requirements, ANTHROPIC_BASE_URL, header forwarding
- [Claude Code env-vars (official)](https://code.claude.com/docs/en/env-vars) — HIGH confidence; CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY, ANTHROPIC_AUTH_TOKEN, ANTHROPIC_CUSTOM_HEADERS
- [LiteLLM /v1/messages unified endpoint](https://docs.litellm.ai/docs/anthropic_unified/) — HIGH confidence; translation mechanics
- [LiteLLM Claude Code Max Subscription tutorial](https://docs.litellm.ai/docs/tutorials/claude_code_max_subscription) — MEDIUM confidence; OAuth forwarding mechanics (documented but feasibility risk remains)
- [LiteLLM Ollama provider docs](https://docs.litellm.ai/docs/providers/ollama) — HIGH confidence; local Ollama setup; no direct cloud API documented here
- [LiteLLM OpenAI-compatible endpoints](https://docs.litellm.ai/docs/providers/openai_compatible) — HIGH confidence; `openai/` prefix + `api_base` pattern
- [Ollama Cloud official docs](https://docs.ollama.com/cloud) — HIGH confidence; direct API key access, `https://ollama.com/api/chat` and `https://ollama.com/v1` endpoints
- [Fabio Rehm: Pi + Ollama Cloud API](https://fabiorehm.com/blog/2026/04/12/pi-ollama-cloud-api/) — MEDIUM confidence; practical verification of `https://ollama.com/v1` without local daemon

---

*Architecture research for: LiteLLM bridge — local Dockerized gateway for Claude Code*
*Researched: 2026-05-20*
