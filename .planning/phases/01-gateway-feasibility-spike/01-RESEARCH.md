# Phase 1: Gateway + Feasibility Spike - Research

**Researched:** 2026-05-20
**Domain:** LiteLLM proxy, Docker Compose, Claude Max OAuth forwarding, Ollama Cloud direct API
**Confidence:** HIGH (core configs and env vars verified against first-party docs; one empirical gap remains for Ollama Cloud `api_base` exact form with LiteLLM)

> **⚠ MODEL UPDATE (2026-05-20, user decision):** The Ollama-backed `claude-haiku` model is now **`deepseek-v4-pro`** (current newest DeepSeek on Ollama Cloud; `tools` capability listed in the live cloud catalog at ollama.com/search?c=cloud). Fallback chain is now **`qwen3.5`** → **`glm-5.1`**. This **SUPERSEDES every `qwen3-coder-next` and `qwen3-coder:480b-cloud` reference below** — treat those as historical research notes, not the chosen model. The authoritative config lives in `01-01-PLAN.md` / `01-03-PLAN.md`, which grep-gate `openai/deepseek-v4-pro:cloud`. The architecture specs/`[VERIFIED]` URLs cited below for `qwen3-coder-next` do NOT transfer to deepseek-v4-pro; its exact cloud tag suffix and tool-call fidelity through LiteLLM are confirmed by the **E-02** (curl) and **E-03** (agentic spike) gates.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** `claude-opus` → Claude (Max via OAuth forwarding); `claude-sonnet` → Claude (Max via OAuth forwarding); `claude-haiku` → Ollama Cloud model. Alias prefix `claude-` so names pass Claude Code's model-name filter (AL-01).
- **D-02:** Default `claude-haiku` backend to `qwen3-coder-next:cloud` (or fallback). MUST verify tool-calling support during agentic spike (OLL-02); swap model if tools fail.
- **D-03:** `model_group_settings.forward_client_headers_to_llm_api: [claude-opus, claude-sonnet]` — scoped forwarding; Ollama group must NOT receive the forwarded Anthropic bearer. Fallback if per-group key syntax fails: keep global forwarding but Ollama group is authenticated by `OLLAMA_API_KEY` (no Anthropic key in container, so a leaked bearer is harmless).
- **D-04:** Reach Ollama Cloud directly: `openai/<model>` + `api_base: https://ollama.com/v1` + `api_key: os.environ/OLLAMA_API_KEY`. `curl`-test the exact URL before committing config.
- **D-05:** `drop_params: true` in `litellm_settings`; `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1` for Ollama group; `anthropic-beta`/`anthropic-version` reach Claude backends but not Ollama (HDR-01).
- **D-06:** docker-compose, single service, port 4000, `ghcr.io/berriai/litellm:main-stable` (never 1.82.7/1.82.8). `config.yaml` bind-mounted read-only. `.env` gitignored. Commit `.env.example` and short README.
- **D-07:** Validation is agentic: real Claude Code tool-use session through Ollama-backed alias (OLL-02); `/status` confirms Max subscription for Claude-backed alias (MAX-02). Decision gate: if Max OAuth forwarding is broken, fall back to API key before proceeding.

### Claude's Discretion
- Exact filenames (`compose.yaml` vs `docker-compose.yml`), README structure, precise current Claude model IDs behind the Max aliases.

### Deferred Ideas (OUT OF SCOPE)
- Fallback chains / retries (REL-01)
- Gateway model discovery toggle (DISC-01)
- OpenAI + Gemini providers (PROV-01/02)
- LiteLLM Admin UI / DB-backed hot-reload (OPS-01)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| GW-01 | LiteLLM runs as single docker-compose service at localhost:4000, image pinned to `ghcr.io/berriai/litellm:main-stable` | Docker Compose shape verified; image registry confirmed |
| GW-02 | `docker compose up/down` starts/stops; compose.yaml and config.yaml committed | Verified docker-compose command syntax; config mount path `/app/config.yaml` confirmed |
| GW-03 | Secrets only in gitignored `.env` (LITELLM_MASTER_KEY, OLLAMA_API_KEY); no secrets baked in | `os.environ/VAR_NAME` syntax confirmed; env_file pattern documented |
| CC-01 | Claude Code reaches gateway via `ANTHROPIC_BASE_URL=http://localhost:4000` + `ANTHROPIC_AUTH_TOKEN` absent when using CUSTOM_HEADERS; `ANTHROPIC_API_KEY` absent | Auth precedence confirmed; ANTHROPIC_CUSTOM_HEADERS mechanism verified |
| CC-02 | Gateway serves Anthropic Messages API (`/v1/messages`) for every backend | LiteLLM unified endpoint confirmed; non-Anthropic translation confirmed |
| CC-03 | Model selectable via `claude --model <alias>` | model_name field in model_list drives this; confirmed |
| AL-01 | Aliases `claude-opus`, `claude-sonnet`, `claude-haiku` pass model-name filter | Names containing `claude` pass the discovery filter per Claude Code docs |
| AL-02 | Each alias backend defined in config.yaml; change by editing + restart | model_list structure confirmed; no live reload needed |
| MAX-01 | At least one alias routes to Claude via Max subscription OAuth forwarding | `forward_client_headers_to_llm_api` mechanism confirmed in LiteLLM tutorial |
| MAX-02 | Verified via `/status` that Max subscription is in use | `/status` command behavior documented in IAM docs |
| OLL-01 | At least one alias routes to Ollama Cloud via `openai/<model>` + `api_base` + `OLLAMA_API_KEY` | Ollama Cloud OpenAI-compat confirmed; `api_base: https://ollama.com/v1` verified |
| OLL-02 | Agentic fidelity: real Claude Code tool-use session through Ollama-backed alias | Empirical — must run real session; model swap protocol defined |
| HDR-01 | `anthropic-beta`/`anthropic-version` reach Claude but not Ollama; `drop_params: true` + beta disable | `drop_params` syntax confirmed; `model_group_settings` scoping confirmed |
</phase_requirements>

---

## Summary

This phase stands up the complete v1 LiteLLM gateway proof-of-concept. The core infrastructure is two committed files (`compose.yaml`, `config.yaml`) plus a gitignored `.env`. Claude Code connects once via `ANTHROPIC_BASE_URL=http://localhost:4000` and never reconfigures; model selection is per-command via `--model <alias>`.

**The Max OAuth path is the documented intended use case.** The LiteLLM "Using Claude Code Max Subscription" tutorial explicitly shows `forward_client_headers_to_llm_api: true` forwarding the Claude Code OAuth bearer to Anthropic. The key subtlety: Claude Code must send its LiteLLM key via `ANTHROPIC_CUSTOM_HEADERS` (as `x-litellm-api-key: Bearer <sk-...>`), NOT as `ANTHROPIC_AUTH_TOKEN`, because `ANTHROPIC_AUTH_TOKEN` would be sent in the `Authorization` header — the same header the OAuth bearer occupies. The two credentials must travel in separate headers.

**The Ollama Cloud path** uses `openai/<model>` + `api_base: https://ollama.com/v1` + `OLLAMA_API_KEY` Bearer. LiteLLM's OpenAI-compatible provider does NOT auto-append `/v1` — it must be in the `api_base`. The Ollama Cloud native endpoint uses `/api/chat` but also exposes `/v1/chat/completions` for OpenAI compatibility (confirmed by the Fabio Rehm practical test and Ollama docs cross-reference). The recommended cloud model for agentic use is `qwen3-coder-next:cloud` (80B MoE, 3B active, 256K context, confirmed to work with Claude Code out-of-the-box); fallback is `qwen3-coder:480b-cloud`.

**Primary recommendation:** Follow the exact config below. The only empirical unknown is whether `model_group_settings.forward_client_headers_to_llm_api` list syntax is active in the current `main-stable` build — test it in Wave 0 or fall back to global forwarding (safe because no `ANTHROPIC_API_KEY` is in the container env).

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Alias resolution (opus/sonnet/haiku) | LiteLLM container | — | model_list in config.yaml; LiteLLM resolves at request time |
| Anthropic Messages API format | LiteLLM container | — | LiteLLM /v1/messages endpoint; handles all format translation |
| Max OAuth token forwarding | LiteLLM container | Claude Code (host) | Claude Code holds the OAuth bearer; LiteLLM forwards it via header passthrough |
| LiteLLM gateway authentication | Claude Code (host) env | — | `ANTHROPIC_CUSTOM_HEADERS` carries `x-litellm-api-key: Bearer <master-key>` |
| Ollama Cloud API routing | LiteLLM container | — | openai/ provider + api_base; OLLAMA_API_KEY in container env |
| Secrets management | Host .env + container env | — | docker-compose injects; config.yaml uses os.environ/ references |
| Header scoping (beta headers) | LiteLLM container | — | model_group_settings controls forwarding per group; drop_params strips unknown params |
| Agentic tool-use translation | LiteLLM container | — | Unified /v1/messages endpoint translates tool_use/tool_result blocks |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| LiteLLM Proxy | `main-stable` (~v1.83.x–v1.85.x as of 2026-05-20) | Gateway exposing Anthropic Messages API; routes and translates to backends | Named in Anthropic's Claude Code LLM-gateway docs; only known proxy with Max OAuth forwarding tutorial |
| Docker Compose v2 | CE latest | Container runtime | User requirement; stateless; `docker compose up/down` |

**Image registries (both valid):**
- `ghcr.io/berriai/litellm:main-stable` — GitHub Container Registry, cosign-signed [VERIFIED: ghcr.io registry]
- `docker.litellm.ai/berriai/litellm:main-stable` — LiteLLM's own registry (shown in deploy docs) [VERIFIED: docs.litellm.ai/docs/proxy/deploy]

Use `ghcr.io/berriai/litellm:main-stable` per D-06.

**Supply-chain constraint:** NEVER use tag `latest`, PyPI v1.82.7, or PyPI v1.82.8 — those specific versions contain confirmed credential-stealing malware. [VERIFIED: code.claude.com/docs/en/llm-gateway]

### No Additional Packages

This phase installs no Node.js/Python/Rust packages beyond the LiteLLM Docker image. No package legitimacy audit required.

---

## Architecture Patterns

### System Architecture Diagram

```
┌──────────────────────────────────────────────────────┐
│  HOST MACHINE                                         │
│                                                       │
│  claude --model claude-opus (or -sonnet, -haiku)      │
│    env:                                               │
│      ANTHROPIC_BASE_URL=http://localhost:4000         │
│      ANTHROPIC_CUSTOM_HEADERS=                        │
│        "x-litellm-api-key: Bearer sk-<master-key>"   │
│      (no ANTHROPIC_API_KEY, no ANTHROPIC_AUTH_TOKEN)  │
│    carries:                                           │
│      Authorization: Bearer <Max OAuth token>          │
│      x-litellm-api-key: Bearer sk-<master-key>        │
└───────────────────┬──────────────────────────────────┘
                    │ POST /v1/messages
                    ▼
┌──────────────────────────────────────────────────────┐
│  DOCKER CONTAINER (localhost:4000)                    │
│  image: ghcr.io/berriai/litellm:main-stable           │
│                                                       │
│  LiteLLM Proxy                                        │
│    1. Validates x-litellm-api-key = LITELLM_MASTER_KEY│
│    2. Looks up model_name in config.yaml model_list   │
│    3a. claude-opus / claude-sonnet:                   │
│         forwards Authorization: Bearer <OAuth token>  │
│         (model_group_settings scopes forwarding)      │
│    3b. claude-haiku (Ollama):                         │
│         translates → OpenAI chat format               │
│         adds Authorization: Bearer <OLLAMA_API_KEY>   │
│         drops anthropic-beta header                   │
│         drops_params: strips unknown params           │
└────────┬─────────────────────┬────────────────────────┘
         │                     │
         ▼                     ▼
┌────────────────┐    ┌────────────────────────────────┐
│ ANTHROPIC API  │    │ OLLAMA CLOUD                    │
│ api.anthropic  │    │ https://ollama.com/v1           │
│ .com/v1/       │    │ Bearer OLLAMA_API_KEY           │
│ messages       │    │ model: qwen3-coder-next:cloud   │
│ (Max sub)      │    │ POST /v1/chat/completions        │
└────────────────┘    └────────────────────────────────┘
```

### Recommended Project Structure

```
lite-llm-bridge/
├── compose.yaml            # docker-compose service definition
├── config.yaml             # model_list, general_settings, litellm_settings (no secrets)
├── .env                    # gitignored secrets (LITELLM_MASTER_KEY, OLLAMA_API_KEY)
├── .env.example            # committed template with placeholder values
├── .gitignore              # includes .env
└── README.md               # setup steps: docker compose up -d, Claude Code env vars,
                            # claude Max login flow, /status check
```

---

## Implementation-Ready Specifications

### 1. Exact `config.yaml`

```yaml
# config.yaml
# Committed to repo — contains no secrets.
# Secrets are in .env and referenced as os.environ/VAR_NAME.

model_list:

  # claude-opus → Claude (Max subscription via OAuth forwarding)
  - model_name: claude-opus
    litellm_params:
      model: anthropic/claude-opus-4-7
      # No api_key here — OAuth bearer forwarded from Claude Code

  # claude-sonnet → Claude (Max subscription via OAuth forwarding)
  - model_name: claude-sonnet
    litellm_params:
      model: anthropic/claude-sonnet-4-6
      # No api_key here — OAuth bearer forwarded from Claude Code

  # claude-haiku → Ollama Cloud (OpenAI-compatible API, no local daemon)
  - model_name: claude-haiku
    litellm_params:
      model: openai/qwen3-coder-next:cloud
      api_base: https://ollama.com/v1        # /v1 MUST be included — LiteLLM does not auto-append it
      api_key: os.environ/OLLAMA_API_KEY

general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY
  # NOTE: forward_client_headers_to_llm_api scoped to Claude groups only (see model_group_settings).
  # This is the safest approach: Ollama group never receives the Anthropic OAuth bearer.

model_group_settings:
  forward_client_headers_to_llm_api:
    - claude-opus
    - claude-sonnet
  # Ollama (claude-haiku) is intentionally absent — it uses OLLAMA_API_KEY, not the forwarded bearer.
  # EMPIRICAL GATE: if model_group_settings list syntax fails on main-stable,
  # fall back to: general_settings: forward_client_headers_to_llm_api: true
  # (safe fallback — no ANTHROPIC_API_KEY is in the container env,
  #  so a forwarded OAuth bearer reaching Ollama is rejected harmlessly)

litellm_settings:
  drop_params: true   # Strips unknown params (e.g., Anthropic-specific fields) before sending to Ollama
```

**Model ID notes (verified against platform.claude.com/docs/en/docs/about-claude/models, 2026-05-20):**
- `claude-opus-4-7` — Current most capable, 1M context, Jan 2026 knowledge cutoff [VERIFIED: platform.claude.com/docs]
- `claude-sonnet-4-6` — Best speed/intelligence balance, 1M context [VERIFIED: platform.claude.com/docs]
- `claude-haiku-4-5-20251001` (alias: `claude-haiku-4-5`) — Not used here; Ollama backs the haiku alias

**Warning:** `claude-sonnet-4-20250514` and `claude-opus-4-20250514` are deprecated and retire June 15, 2026. Do not use them. [VERIFIED: platform.claude.com/docs]

### 2. Exact `compose.yaml`

```yaml
# compose.yaml
# Use Compose v2: `docker compose up -d` / `docker compose down`

services:
  litellm:
    image: ghcr.io/berriai/litellm:main-stable
    # NEVER use: latest, 1.82.7, 1.82.8 (malware confirmed by Anthropic docs)
    ports:
      - "4000:4000"
    volumes:
      - ./config.yaml:/app/config.yaml:ro    # :ro = read-only inside container
    env_file:
      - .env                                  # injects LITELLM_MASTER_KEY and OLLAMA_API_KEY
    command: ["--config", "/app/config.yaml", "--port", "4000"]
    restart: unless-stopped
```

**Notes:**
- Config mounts at `/app/config.yaml` inside the container [VERIFIED: docs.litellm.ai/docs/proxy/deploy]
- `env_file` injects from `.env`; docker-compose v2 supports this natively
- `restart: unless-stopped` keeps the gateway up across reboots
- No `DATABASE_URL` or `litellm-database` image — not needed for single-user PoC [VERIFIED: docs.litellm.ai/docs/proxy/deploy]
- Healthcheck not shown in LiteLLM deploy docs; omit from v1. Kubernetes examples use port 4000 liveness probe — could add `curl http://localhost:4000/health/liveliness` if desired [ASSUMED]

### 3. Exact `.env` and `.env.example`

```bash
# .env  — NEVER commit; add to .gitignore
LITELLM_MASTER_KEY=sk-<generate-a-random-32-char-string>
OLLAMA_API_KEY=<from https://ollama.com/settings/keys>
```

```bash
# .env.example  — COMMIT this file
LITELLM_MASTER_KEY=sk-change-me-generate-random-value
OLLAMA_API_KEY=ollama-your-api-key-from-settings
```

`LITELLM_MASTER_KEY` must start with `sk-` [VERIFIED: docs.litellm.ai/docs/proxy/configs]. Generate with `openssl rand -hex 16` or similar.

### 4. Claude Code Wiring (Host Environment)

**The Max OAuth forwarding mechanism requires two separate headers:**

```bash
# Set these in shell or in ~/.claude/settings.json

# Route Claude Code to the gateway (not to api.anthropic.com)
export ANTHROPIC_BASE_URL=http://localhost:4000

# Authenticate TO the gateway — sent as x-litellm-api-key: Bearer header
# (NOT sent as Authorization: Bearer — that slot is reserved for the Max OAuth token)
export ANTHROPIC_CUSTOM_HEADERS="x-litellm-api-key: Bearer sk-<your-LITELLM_MASTER_KEY>"

# MUST be absent — its presence takes precedence #3 in auth chain and would bypass OAuth
unset ANTHROPIC_API_KEY

# MUST be absent — would be sent as Authorization: Bearer, colliding with the OAuth token
# (or if set, would replace the OAuth token, breaking Max subscription forwarding)
unset ANTHROPIC_AUTH_TOKEN
```

**Why `ANTHROPIC_CUSTOM_HEADERS` not `ANTHROPIC_AUTH_TOKEN`:**
- `ANTHROPIC_AUTH_TOKEN` → sent as `Authorization: Bearer <value>` [VERIFIED: code.claude.com/docs/en/iam]
- The Max OAuth token also rides in `Authorization: Bearer <oauth-token>`
- LiteLLM tutorial uses `x-litellm-api-key: Bearer <virtual-key>` via `ANTHROPIC_CUSTOM_HEADERS` to send the LiteLLM credential separately [VERIFIED: docs.litellm.ai/docs/tutorials/claude_code_max_subscription]
- LiteLLM reads `x-litellm-api-key` as the gateway auth header alongside the forwarded `Authorization`

**Alternative persistent config (survives shell sessions):**

```json
// ~/.claude/settings.json
{
  "env": {
    "ANTHROPIC_BASE_URL": "http://localhost:4000",
    "ANTHROPIC_CUSTOM_HEADERS": "x-litellm-api-key: Bearer sk-<your-LITELLM_MASTER_KEY>"
  }
}
```

**Max subscription login flow:**
1. Ensure `ANTHROPIC_API_KEY` is unset in the shell environment.
2. Run `claude` in terminal (first time or after `/logout`).
3. Claude Code opens browser or prints a login URL — log in with the Claude Max account.
4. After authentication, Claude Code holds an OAuth bearer token (stored in `~/.claude/.credentials.json` on Linux).
5. Every subsequent request carries `Authorization: Bearer <oauth-token>`.
6. With `ANTHROPIC_BASE_URL=http://localhost:4000`, that bearer goes to LiteLLM instead of Anthropic directly.
7. LiteLLM's `forward_client_headers_to_llm_api` scoped to `claude-opus` and `claude-sonnet` groups forwards the bearer to `api.anthropic.com`.

**Verifying Max is in use:**
```bash
# Inside a claude session:
/status
```
The `/status` output shows the active authentication method. With Max OAuth active, it will show the Claude.ai subscription, not an API key. [CITED: code.claude.com/docs/en/iam — auth precedence table]

**Auth precedence reminder (from official IAM docs):** [VERIFIED: code.claude.com/docs/en/iam]
1. Cloud provider env vars (Bedrock/Vertex/Foundry) — not set
2. `ANTHROPIC_AUTH_TOKEN` — must be unset
3. `ANTHROPIC_API_KEY` — must be unset
4. `apiKeyHelper` — not configured
5. `CLAUDE_CODE_OAUTH_TOKEN` — not set
6. **OAuth credentials from `/login`** — this is the active path

### 5. Ollama Cloud Wiring

**API endpoint confirmed:**
- OpenAI-compatible: `https://ollama.com/v1` [CITED: Fabio Rehm blog 2026-04-12; Ollama Cloud models show this URL; consistent with search results]
- Native Ollama API: `https://ollama.com/api/chat` [VERIFIED: docs.ollama.com/cloud]
- LiteLLM uses the OpenAI-compatible path via `openai/` prefix

**Critical: LiteLLM does NOT auto-append `/v1`** to `api_base`. [VERIFIED: docs.litellm.ai/docs/providers/openai_compatible — explicit warning: "make sure your api_base has the /v1 postfix"]
- Correct: `api_base: https://ollama.com/v1`
- Wrong: `api_base: https://ollama.com` (LiteLLM would call `https://ollama.com/chat/completions`, not `/v1/chat/completions`)

**Model name format for cloud models:** `:cloud` suffix required [CITED: docs.ollama.com/cloud; Fabio Rehm blog confirms cloud models use `:cloud` tag]. Without it, Ollama would attempt local inference.

**Pre-commit curl test to validate endpoint:**
```bash
curl -s https://ollama.com/v1/models \
  -H "Authorization: Bearer $OLLAMA_API_KEY" | jq '.data[].id' | head -20
```
If this returns model IDs, the endpoint and key are valid. If it returns 401, the key is wrong. If it returns 404 or connection refused, the URL is wrong.

**Curl smoke test for a chat request:**
```bash
curl -s https://ollama.com/v1/chat/completions \
  -H "Authorization: Bearer $OLLAMA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3-coder-next:cloud",
    "messages": [{"role": "user", "content": "Say hello"}],
    "stream": false
  }' | jq '.choices[0].message.content'
```

**API key creation:** [VERIFIED: docs.ollama.com/cloud] Create at `https://ollama.com/settings/keys`. Set as `OLLAMA_API_KEY` in `.env`.

### 6. Header and Parameter Handling (HDR-01)

**`drop_params: true`** in `litellm_settings`: [VERIFIED: docs.litellm.ai/docs/proxy/configs]
- Strips any Anthropic-specific parameters (e.g., `top_k`, `system` if format differs) before sending to Ollama.
- This prevents LiteLLM from rejecting requests when Claude Code sends parameters the Ollama endpoint doesn't understand.

**`anthropic-beta` header scoping:**
- LiteLLM's unified `/v1/messages` endpoint is required by Claude Code to forward `anthropic-beta` and `anthropic-version` to Claude backends [VERIFIED: code.claude.com/docs/en/llm-gateway].
- When routing to Ollama via `openai/` prefix, these headers would reach the OpenAI-compat endpoint and be rejected.
- The `model_group_settings.forward_client_headers_to_llm_api` list scopes header forwarding to Claude groups only. The Ollama group (`claude-haiku`) receives no forwarded client headers.
- Additional safety net: set `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1` in Claude Code's env when testing the Ollama alias specifically. This prevents Claude Code from sending `anthropic-beta` headers at all for that session.

**`CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1` scoping note:** [CITED: code.claude.com/docs/en/llm-gateway]
- This is a client-side env var. It cannot be set per-alias in the gateway config.
- For the feasibility spike (OLL-02), set it in the shell when running the Ollama-backed alias test.
- For production use, LiteLLM's header scoping (`model_group_settings`) is the correct mechanism.

---

## Ollama Cloud Model Recommendations

### Primary (D-02 default): `qwen3-coder-next:cloud`
- **Architecture:** 80B total / 3B active (MoE), 256K context [VERIFIED: ollama.com/library/qwen3-coder-next]
- **Tool calling:** Confirmed — "Works with coding agents like Claude Code, Qwen Code, Cline, and OpenCode out of the box" [VERIFIED: ollama.com/library/qwen3-coder-next]
- **Cloud tag:** `qwen3-coder-next:cloud` confirmed to exist in Ollama library [VERIFIED: ollama.com/library/qwen3-coder-next:cloud]
- **Usage:** High (per library page)

### Fallback: `qwen3-coder:480b-cloud`
- **Architecture:** 480B, 256K context [VERIFIED: ollama.com/library/qwen3-coder]
- **Tool calling:** Qwen3-Coder is described as "most agentic code model" with tool-calling updates [CITED: ollama.com/library/qwen3-coder; ollama.com/blog/coding-models]
- **Cloud tag:** `qwen3-coder:480b-cloud` confirmed [VERIFIED: ollama.com search result]

### Secondary fallback: `glm-5.1:cloud` (if Qwen3 tools fail)
- Tested by Fabio Rehm blog with Claude Code tool-use (file read/write/edit/bash) [CITED: fabiorehm.com/blog/2026/04/12/pi-ollama-cloud-api/]
- "Hundreds of rounds and thousands of tool calls" — empirical tool-call fidelity evidence [CITED: same source]

**Model swap protocol (OLL-02):** If the primary model fails tool-calling during the agentic spike, swap `model` in config.yaml and restart the container. No other config changes needed.

---

## Agentic Validation Procedure

### OLL-02: Prove Ollama-backed alias tool use

**Goal:** A real Claude Code session drives file edit + bash through `claude-haiku` (Ollama-backed).

```bash
# Step 1: Set env for Ollama test session
export ANTHROPIC_BASE_URL=http://localhost:4000
export ANTHROPIC_CUSTOM_HEADERS="x-litellm-api-key: Bearer sk-<master-key>"
export CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1
unset ANTHROPIC_API_KEY
unset ANTHROPIC_AUTH_TOKEN

# Step 2: Run a task that requires file edit AND bash execution
claude --model claude-haiku "Create a file called test-oll02.txt with the text 'hello from ollama', then read it back and tell me its contents"

# Expected: Claude Code runs, invokes Write tool, then Read or Bash tool.
# Success: File is created, Claude reports its contents without error.
# Failure: LiteLLM returns an error, or tool_use blocks are malformed, or no file is created.
```

**What to watch for:**
- LiteLLM logs (docker compose logs litellm) should show the request being routed to Ollama Cloud
- If the Ollama model fails to produce well-formed tool_use JSON, Claude Code will error — this means swap the model
- `drop_params: true` should prevent parameter-mismatch errors; if they still occur, check LiteLLM logs

### MAX-02: Prove Max subscription is in use

```bash
# Step 1: Set env for Max test session (no ANTHROPIC_CUSTOM_HEADERS collision)
export ANTHROPIC_BASE_URL=http://localhost:4000
export ANTHROPIC_CUSTOM_HEADERS="x-litellm-api-key: Bearer sk-<master-key>"
unset ANTHROPIC_API_KEY
unset ANTHROPIC_AUTH_TOKEN

# Step 2: Confirm Max login is active
claude /status

# Step 3: Run a simple Claude-backed request
claude --model claude-sonnet "What is 2+2?"

# Step 4: Check /status shows Max subscription (not API key)
```

**`/status` output to look for:** [CITED: code.claude.com/docs/en/iam]
The status command shows the active authentication method. Max subscription will appear as subscription-based login, not as an API key credential. If you see `API key: sk-ant-...`, then `ANTHROPIC_API_KEY` is being used instead — check that it is unset.

---

## Common Pitfalls

### Pitfall 1: `ANTHROPIC_AUTH_TOKEN` collides with Max OAuth bearer

**What goes wrong:** Setting `ANTHROPIC_AUTH_TOKEN=sk-<master-key>` causes Claude Code to send `Authorization: Bearer sk-<master-key>`. LiteLLM receives this in the Authorization header. When `forward_client_headers_to_llm_api` is active, LiteLLM forwards the master key (not the OAuth token) to Anthropic — Anthropic rejects it.

**Why it happens:** `ANTHROPIC_AUTH_TOKEN` takes auth precedence #2, above OAuth (#6). It replaces the OAuth token rather than adding a second credential.

**How to avoid:** Use `ANTHROPIC_CUSTOM_HEADERS="x-litellm-api-key: Bearer sk-<master-key>"` instead. This sends the LiteLLM credential in a separate header that LiteLLM reads for gateway auth, leaving the Authorization header for the OAuth token.

**Source:** [VERIFIED: code.claude.com/docs/en/iam (auth precedence table) + docs.litellm.ai/docs/tutorials/claude_code_max_subscription (ANTHROPIC_CUSTOM_HEADERS usage)]

### Pitfall 2: `ANTHROPIC_API_KEY` in Claude Code's environment silently overrides Max subscription

**What goes wrong:** If `ANTHROPIC_API_KEY` is set anywhere in Claude Code's shell (even exported from a `.bashrc` for other tools), it takes auth precedence #3 and overrides the OAuth login. Claude Code calls Anthropic directly with the API key, bypassing the gateway and incurring per-token billing.

**Why it happens:** Auth precedence is global; there is no per-alias or per-session override.

**How to avoid:** `unset ANTHROPIC_API_KEY` in every shell that runs Claude Code. Verify with `/status` that subscription auth is shown, not an API key.

**Source:** [VERIFIED: code.claude.com/docs/en/iam — "If you have an active Claude subscription but also have ANTHROPIC_API_KEY set in your environment, the API key takes precedence once approved."]

### Pitfall 3: Ollama Cloud `api_base` missing `/v1`

**What goes wrong:** Using `api_base: https://ollama.com` causes LiteLLM to call `https://ollama.com/chat/completions` — which does not exist. Result: 404 or connection error.

**Why it happens:** LiteLLM's `openai/` provider does NOT auto-append `/v1`. The docs explicitly warn: "make sure your api_base has the `/v1` postfix."

**How to avoid:** Always use `api_base: https://ollama.com/v1`. Pre-commit curl test:
```bash
curl -s https://ollama.com/v1/models -H "Authorization: Bearer $OLLAMA_API_KEY"
```

**Source:** [VERIFIED: docs.litellm.ai/docs/providers/openai_compatible — explicit warning quoted]

### Pitfall 4: Using model name without `:cloud` suffix for Ollama Cloud

**What goes wrong:** `model: openai/qwen3-coder-next` (no tag) may route to a different variant or fail. Ollama Cloud models require the `:cloud` suffix to run on Ollama's infrastructure rather than locally.

**Why it happens:** Ollama's model naming convention uses tags; `:cloud` specifies cloud-hosted inference. Without it, behavior is undefined for remote API calls.

**How to avoid:** Always use the full tag: `openai/qwen3-coder-next:cloud` in `litellm_params.model`.

**Source:** [CITED: docs.ollama.com/cloud (model format examples use :cloud suffix); Fabio Rehm blog confirms]

### Pitfall 5: `model_group_settings.forward_client_headers_to_llm_api` not in current main-stable

**What goes wrong:** The list-syntax for per-group header forwarding may not be available in the pinned LiteLLM version. Config loads silently but forwarding is either disabled (breaking Max) or enabled globally (forwarding the OAuth bearer to Ollama).

**Why it happens:** `model_group_settings` is documented in the tutorial but NOT shown in the main proxy/configs reference page. It may be a newer feature or have different syntax.

**How to detect:** Check `docker compose logs litellm` on startup for config parse errors. Test a Claude-backed alias — if it rejects auth, forwarding failed.

**Fallback:** Replace `model_group_settings` block with:
```yaml
general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY
  forward_client_headers_to_llm_api: true
```
This is safe because no `ANTHROPIC_API_KEY` is present in the container env; the only credential the Ollama group can receive is the OAuth bearer, which Ollama will reject with 401 (harmless).

**Source:** [VERIFIED (tutorial): docs.litellm.ai/docs/tutorials/claude_code_max_subscription; NOT FOUND in proxy/configs reference — treat as empirical gate]

### Pitfall 6: LiteLLM malware versions

**What goes wrong:** Running PyPI v1.82.7 or v1.82.8 installs credential-stealing malware that exfiltrates API keys.

**How to avoid:** Always use `ghcr.io/berriai/litellm:main-stable` Docker image. Never `pip install litellm==1.82.7` or `1.82.8`.

**Source:** [VERIFIED: code.claude.com/docs/en/llm-gateway — explicit warning with GitHub issue link]

### Pitfall 7: Agentic tool-use through Ollama may silently fail without real session test

**What goes wrong:** A `curl` round-trip to the gateway succeeds, but a real Claude Code agentic session (file edit + bash) fails because the tool_use / tool_result message format is malformed or truncated in LiteLLM's Anthropic→OpenAI translation.

**Why it happens:** Tool-use involves multi-turn structured JSON blocks that differ between Anthropic and OpenAI formats. LiteLLM's translation layer handles this, but edge cases exist.

**How to avoid:** Do the real agentic spike (OLL-02) — file creation + read-back — as the acceptance test, not a simple text round-trip.

**Source:** [CITED: .planning/research/SUMMARY.md — "The main remaining risk is empirical: whether LiteLLM's translation faithfully preserves tool-calling semantics"]

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Anthropic Messages API translation for Ollama | Custom translation layer | LiteLLM `/v1/messages` unified endpoint | LiteLLM handles tool_use, tool_result, streaming, stop_reason translation; hand-rolling this is months of work |
| Model alias resolution | Custom routing middleware | LiteLLM `model_list` in config.yaml | model_name → litellm_params.model is built-in |
| OAuth bearer forwarding | Custom header proxy | LiteLLM `forward_client_headers_to_llm_api` | Gateway already handles this; hand-rolling is a security risk |
| Credential scoping per backend | Per-route auth middleware | LiteLLM `model_group_settings` | Built-in group-level header control |
| Parameter sanitization for non-Anthropic backends | Custom param stripper | LiteLLM `drop_params: true` | One config line; covers all Anthropic-specific params |

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `ollama_chat/<model>:cloud` via local daemon | `openai/<model>:cloud` + `api_base: https://ollama.com/v1` direct | Ollama Cloud API launch (2025-2026) | No local Ollama daemon required |
| Anthropic API key for Claude via LiteLLM | Max OAuth forwarding via `forward_client_headers_to_llm_api` | LiteLLM added tutorial; Anthropic added LLM-gateway docs (2025) | Reuses Max subscription, no per-token billing |
| `ANTHROPIC_AUTH_TOKEN` for LiteLLM gateway auth | `ANTHROPIC_CUSTOM_HEADERS` with `x-litellm-api-key: Bearer` | LiteLLM Max tutorial specific recommendation | Avoids collision with OAuth bearer in Authorization header |
| LiteLLM `latest` Docker tag | `main-stable` tag | After v1.82.7/1.82.8 malware (2025) | Stable, vetted, cosign-signed images |

**Deprecated / do not use:**
- `claude-sonnet-4-20250514`, `claude-opus-4-20250514` — deprecated, retire June 15, 2026 [VERIFIED: platform.claude.com/docs]
- `ANTHROPIC_AUTH_TOKEN` when targeting Max OAuth forwarding — causes auth collision [VERIFIED: docs.litellm.ai tutorial]

---

## Open / Empirical Items

These CANNOT be resolved by documentation alone. The planner must make them explicit validation tasks (acceptance-gate tasks before proceeding).

| # | Item | What to test | Fallback |
|---|------|-------------|---------|
| E-01 | `model_group_settings.forward_client_headers_to_llm_api` list syntax is active on pinned `main-stable` | Deploy config; run `claude --model claude-sonnet "hello"` and check LiteLLM logs that Authorization header was forwarded to Anthropic | Use `general_settings: forward_client_headers_to_llm_api: true` globally (safe — no ANTHROPIC_API_KEY in container) |
| E-02 | Ollama Cloud `api_base: https://ollama.com/v1` works with `openai/qwen3-coder-next:cloud` | Run curl test before docker-compose; if 404, try `https://ollama.com` or check if Ollama changed the URL | Try `https://ollama.com` (but this will likely fail per LiteLLM docs; check LiteLLM logs) |
| E-03 | `qwen3-coder-next:cloud` tool-calling fidelity through LiteLLM translation | Run OLL-02 agentic spike (file edit + bash) | Swap to `glm-5.1:cloud` (field-tested for tool use with Claude Code) or `qwen3-coder:480b-cloud` |
| E-04 | `/status` shows Max subscription after Max login + gateway wiring | Run `claude /status` with ANTHROPIC_BASE_URL set | Check `/login` flow again; ensure ANTHROPIC_API_KEY is unset; check LiteLLM logs for auth errors |
| E-05 | LiteLLM handles `tool_use` / `tool_result` blocks correctly for Ollama backend in streaming mode | OLL-02 must use `--` non-interactive mode or an interactive task that requires multiple tool turns | If streaming fails, try non-streaming (set `stream: false` in litellm_settings — but this is a workaround) |

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker + Compose v2 | GW-01, GW-02 | Check: `docker compose version` | Must be ≥ 2.0 | Install Docker Desktop or Docker CE |
| `ghcr.io/berriai/litellm:main-stable` image | GW-01 | Pulled on `docker compose up` | current main-stable | — |
| Ollama Cloud API key | OLL-01, OLL-02 | User supplies | — | Create at ollama.com/settings/keys |
| Claude Max subscription | MAX-01, MAX-02 | User has Max 5x (per PROJECT.md) | — | Fallback: Anthropic API key (per D-07) |
| `jq` (for curl test validation) | E-02 smoke test | Check: `command -v jq` | any | `python3 -m json.tool` as substitute |

---

## Validation Architecture

### No automated test framework for Phase 1

This phase is a feasibility spike. Validation is manual/agentic:
- E-01 through E-05 are explicit acceptance-gate tasks
- OLL-02 and MAX-02 are the formal acceptance criteria
- No `pytest`/`jest` infrastructure — the "test" is a real Claude Code session

### Phase Requirements → Validation Map

| Req ID | Validation Method | Command / Steps |
|--------|------------------|----------------|
| GW-01 | Manual | `docker compose up -d && curl http://localhost:4000/health/readiness` |
| GW-02 | Manual | `docker compose down && docker compose up -d` |
| GW-03 | Manual | `grep -r "sk-" compose.yaml config.yaml` returns nothing; `.env` is in `.gitignore` |
| CC-01 | Manual | Run `claude --model claude-sonnet "hello"` with CUSTOM_HEADERS set; verify no API key error |
| CC-02 | Manual | Successful response from both Claude and Ollama aliases |
| CC-03 | Manual | `claude --model claude-opus "hello"` and `claude --model claude-haiku "hello"` both succeed |
| AL-01 | Manual | Both alias names work in `--model` flag |
| AL-02 | Manual | Edit config.yaml, `docker compose restart`, re-run; new backend responds |
| MAX-01 | Agentic | `claude --model claude-opus "hello"` returns a response without API-key error |
| MAX-02 | Agentic | `claude /status` shows subscription auth (not API key) |
| OLL-01 | Agentic | `claude --model claude-haiku "hello"` routes through Ollama (check LiteLLM logs) |
| OLL-02 | Agentic | Full tool-use session: file create + read-back via claude-haiku |
| HDR-01 | Log inspection | LiteLLM logs show `anthropic-beta` NOT present in Ollama requests; `drop_params` active |

---

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | Yes — gateway auth | `LITELLM_MASTER_KEY` via `x-litellm-api-key` header; no weak defaults |
| V3 Session Management | No — stateless proxy | — |
| V4 Access Control | No — single user local | — |
| V5 Input Validation | Partial — `drop_params: true` | Strips unknown params; LiteLLM handles |
| V6 Cryptography | No — no custom crypto | Credentials are opaque tokens; TLS to upstream is handled by LiteLLM |

**Threat patterns specific to this stack:**

| Pattern | Standard Mitigation |
|---------|---------------------|
| Credential exfiltration via compromised LiteLLM image | Pin to `main-stable`; never `latest` or PyPI v1.82.7/1.82.8 |
| API key in committed files | `os.environ/VAR_NAME` in config.yaml; `.env` gitignored; `.env.example` contains only placeholders |
| Anthropic OAuth bearer leaking to Ollama | `model_group_settings` scoping; fallback: global forwarding safe because no Anthropic key in container |
| `ANTHROPIC_API_KEY` bypass (auto-billing) | Documented in README; `unset` in setup steps |
| LITELLM_MASTER_KEY brute-force | Local-only binding (localhost:4000); single-user; generate 32+ char random value |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `qwen3-coder-next:cloud` tag is currently available on Ollama Cloud and accepts requests via OpenAI-compat API | Ollama model recommendations | Must swap to fallback model; one config.yaml edit + container restart |
| A2 | `https://ollama.com/v1` is the correct `api_base` for Ollama Cloud OpenAI-compat (not `https://ollama.com`) | api_base configuration | 404 errors; fallback: check LiteLLM logs, try alternate URL form |
| A3 | `model_group_settings.forward_client_headers_to_llm_api` list syntax works in current main-stable | config.yaml pattern | Fall back to global `general_settings` forwarding; safe but less precise |
| A4 | `LITELLM_MASTER_KEY` must start with `sk-` prefix | .env specification | LiteLLM may reject auth if prefix is wrong; re-generate with correct prefix |
| A5 | Docker Compose `env_file: .env` auto-injects variables into the container without additional config | compose.yaml pattern | May need explicit `environment:` block referencing ${VAR}; fallback is trivial |
| A6 | LiteLLM healthcheck endpoint is `/health/readiness` at port 4000 | GW-01 validation | Use alternative health check: `curl http://localhost:4000/models` |

---

## Sources

### Primary (HIGH confidence — first-party official docs)
- `https://docs.litellm.ai/docs/tutorials/claude_code_max_subscription` — `forward_client_headers_to_llm_api`, `model_group_settings`, `ANTHROPIC_CUSTOM_HEADERS` pattern, LiteLLM Max subscription config
- `https://code.claude.com/docs/en/llm-gateway` — gateway requirements, `anthropic-beta`/`anthropic-version` forwarding mandate, malware warning, `ANTHROPIC_AUTH_TOKEN` as bearer, `ANTHROPIC_CUSTOM_HEADERS`
- `https://code.claude.com/docs/en/iam` — auth precedence table (1–6), `ANTHROPIC_API_KEY` override behavior, `/status` command, Max login flow
- `https://platform.claude.com/docs/en/docs/about-claude/models` — current Claude model IDs: `claude-opus-4-7`, `claude-sonnet-4-6`, `claude-haiku-4-5`; deprecation warning for `claude-sonnet-4-20250514`/`claude-opus-4-20250514`
- `https://docs.litellm.ai/docs/providers/openai_compatible` — `openai/` prefix format; explicit warning that `/v1` must be in `api_base` (not auto-appended)
- `https://docs.litellm.ai/docs/proxy/configs` — `model_list` structure, `general_settings.master_key`, `litellm_settings.drop_params`, `os.environ/VAR_NAME` syntax
- `https://docs.litellm.ai/docs/proxy/deploy` — Docker compose shape, `/app/config.yaml` mount path, `docker.litellm.ai/berriai/litellm:main-stable` image tag
- `https://docs.ollama.com/cloud` — `https://ollama.com/api/chat` native endpoint, `Authorization: Bearer $OLLAMA_API_KEY`, key creation at `ollama.com/settings/keys`
- `https://ollama.com/library/qwen3-coder-next` — `qwen3-coder-next:cloud` tag, tool calling with Claude Code confirmed
- `https://ollama.com/library/qwen3-coder` — `qwen3-coder:480b-cloud` tag

### Secondary (MEDIUM confidence — third-party verified practical)
- `https://fabiorehm.com/blog/2026/04/12/pi-ollama-cloud-api/` — Confirms `https://ollama.com/v1` for OpenAI-compat; `:cloud` suffix required; `glm-5.1:cloud` tool-call fidelity evidence with Claude Code

### Note on STACK.md superseded verdict
- STACK.md contains a "SUPERSEDED" section claiming Max OAuth is blocked by Anthropic ToS. SUMMARY.md explicitly overrides this with first-party verification. The LiteLLM tutorial and Anthropic's own LLM-gateway docs document the Max OAuth forwarding path as the intended use case. This research follows SUMMARY.md. [VERIFIED: docs.litellm.ai/docs/tutorials/claude_code_max_subscription; code.claude.com/docs/en/llm-gateway]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — image, compose, port, config mount verified against first-party docs
- Claude Code wiring: HIGH — `ANTHROPIC_CUSTOM_HEADERS` + auth precedence verified against IAM docs + LiteLLM tutorial
- Max OAuth forwarding: HIGH (mechanism); EMPIRICAL (E-01 must validate `model_group_settings` syntax on pinned version)
- Ollama Cloud wiring: MEDIUM-HIGH — `/v1` endpoint confirmed by multiple sources; `:cloud` suffix confirmed; LiteLLM `openai/` + `api_base` is standard pattern; no first-party LiteLLM+Ollama Cloud combined example
- Agentic tool-use fidelity: EMPIRICAL — must run OLL-02; cannot be confirmed from docs alone
- Model IDs: HIGH — verified against Anthropic's official model page

**Research date:** 2026-05-20
**Valid until:** 2026-06-20 (model IDs and LiteLLM version may shift; re-check before implementation if delayed)
