# Stack Research

**Domain:** Local Dockerized LiteLLM gateway for Claude Code
**Researched:** 2026-05-20
**Confidence:** HIGH (all key claims verified against official documentation)

---

## Critical Pre-Reading: Claude Max Feasibility Decision

**The primary hypothesis — route Claude Max subscription through LiteLLM — is BLOCKED as of April 4, 2026.**

Anthropic updated its Terms of Service in February 2026 and enforced them on April 4, 2026: using OAuth tokens from Claude Free, Pro, or Max subscriptions in any third-party tool is explicitly prohibited. A local LiteLLM proxy is a third-party tool under this policy. The only workaround that avoids per-token API billing is Claude Code itself (the official binary), which is permitted to use Max subscription credentials directly.

**Implication for this project:** The gateway can still be built, but the Anthropic/Claude backend MUST use an Anthropic API key (pay-per-token), NOT a Max subscription OAuth token. The Claude Max angle does not apply here. This is the primary risk flagged in PROJECT.md and it is confirmed: the hypothesis is refuted.

**Source:** [The Register — Anthropic clarifies ban on third-party Claude access, Feb 2026](https://www.theregister.com/2026/02/20/anthropic_clarifies_ban_third_party_claude_access/) | Confidence: HIGH

---

## Recommended Stack

### Core Technologies

| Technology | Version/Tag | Purpose | Why Recommended |
|------------|-------------|---------|-----------------|
| LiteLLM Proxy | `main-stable` (v1.85.0 as of 2026-05-20) | Gateway — translates Anthropic Messages API to/from provider APIs | Official gateway explicitly supported by Claude Code docs; named in Claude Code's LLM gateway guide |
| Docker / docker-compose | Docker CE latest; Compose v2 | Container runtime | User requirement; stateless config-file-driven, no DB needed for single-user PoC |

**Image registry:** Use `ghcr.io/berriai/litellm:main-stable` (GitHub Container Registry, all images cosign-signed) OR `litellm/litellm:main-stable` (Docker Hub). The tag `main-stable` tracks the latest release that has passed CI/CD and 3 days of production testing. Do NOT use `latest` on Docker Hub — `main-stable` is the stable tag.

**Warning:** LiteLLM PyPI/Docker versions 1.82.7 and 1.82.8 were found to contain credential-stealing malware (confirmed by Anthropic's own Claude Code LLM gateway docs). Avoid those specific versions; `main-stable` is currently v1.85.0 and safe.

**Sources:**
- [LiteLLM Docker Hub tags](https://hub.docker.com/r/litellm/litellm/tags) | Confidence: HIGH
- [LiteLLM GitHub releases](https://github.com/BerriAI/litellm/releases) | Confidence: HIGH
- [Claude Code LLM gateway docs — LiteLLM section](https://code.claude.com/docs/en/llm-gateway) | Confidence: HIGH

---

## 1. Docker Compose Shape (Minimal Working Example)

**Verified against:** [LiteLLM deploy docs](https://docs.litellm.ai/docs/proxy/deploy) | Confidence: HIGH

```yaml
# docker-compose.yml
services:
  litellm:
    image: ghcr.io/berriai/litellm:main-stable
    ports:
      - "4000:4000"
    volumes:
      - ./config.yaml:/app/config.yaml:ro
    environment:
      - LITELLM_MASTER_KEY=${LITELLM_MASTER_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - OLLAMA_API_KEY=${OLLAMA_API_KEY}
    command: ["--config", "/app/config.yaml", "--port", "4000"]
    restart: unless-stopped
```

```env
# .env  (never commit this file)
LITELLM_MASTER_KEY=sk-my-local-master-key
ANTHROPIC_API_KEY=sk-ant-...
OLLAMA_API_KEY=ollama_...
```

Notes:
- The config file mounts at `/app/config.yaml` inside the container.
- `LITELLM_MASTER_KEY` must start with `sk-` and is required for the proxy to enforce auth on incoming requests.
- Provider credentials are passed as env vars and referenced in config.yaml via `os.environ/VAR_NAME` syntax.
- For a PoC with no DB, omit `DATABASE_URL` and use the plain `litellm:main-stable` image (not `litellm-database`).

---

## 2. config.yaml Model List Structure

**Verified against:** [LiteLLM proxy configs docs](https://docs.litellm.ai/docs/proxy/configs) and [Anthropic provider docs](https://docs.litellm.ai/docs/providers/anthropic) | Confidence: HIGH

```yaml
# config.yaml

model_list:

  # Semantic alias -> Anthropic API (requires ANTHROPIC_API_KEY, pay-per-token)
  - model_name: opus
    litellm_params:
      model: anthropic/claude-opus-4-5          # provider/model-id format
      api_key: os.environ/ANTHROPIC_API_KEY

  - model_name: sonnet
    litellm_params:
      model: anthropic/claude-sonnet-4-5-20250929
      api_key: os.environ/ANTHROPIC_API_KEY

  - model_name: haiku
    litellm_params:
      model: anthropic/claude-haiku-3-5         # use current Anthropic model names
      api_key: os.environ/ANTHROPIC_API_KEY

  # Ollama Cloud model via OpenAI-compatible endpoint (see Section 4)
  - model_name: haiku                             # or a separate alias e.g. qwen-cloud
    litellm_params:
      model: openai/qwen3-coder                  # openai/ prefix for OpenAI-compat endpoints
      api_base: https://ollama.com               # Ollama Cloud base (no /v1 — LiteLLM adds it)
      api_key: os.environ/OLLAMA_API_KEY

general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY

litellm_settings:
  drop_params: true                               # discard unknown params rather than error
```

Key rules:
- `model_name` is the public-facing alias Claude Code uses with `claude --model <alias>`.
- `litellm_params.model` is the routing string in `provider/model-id` format.
- `os.environ/VAR_NAME` is LiteLLM's syntax for pulling values from environment at runtime.
- Do not hard-code credentials in this file.

**Anthropic model IDs:** Check [Anthropic model docs](https://docs.anthropic.com/en/docs/about-claude/models) for current IDs; the format is `anthropic/claude-<name>-<version>`.

---

## 3. Claude Code Client Configuration

**Verified against:** [Claude Code env-vars docs](https://code.claude.com/docs/en/env-vars) and [Claude Code LLM gateway docs](https://code.claude.com/docs/en/llm-gateway) | Confidence: HIGH

### Required variables

```bash
export ANTHROPIC_BASE_URL=http://localhost:4000
export ANTHROPIC_AUTH_TOKEN=sk-my-local-master-key   # matches LITELLM_MASTER_KEY
```

`ANTHROPIC_BASE_URL` — Verified real. Overrides the API endpoint. Claude Code sends all requests to this URL instead of `api.anthropic.com`.

`ANTHROPIC_AUTH_TOKEN` — Verified real. Sent as `Authorization: Bearer <value>`. This is how Claude Code authenticates TO the LiteLLM gateway (not to Anthropic). Set it to your `LITELLM_MASTER_KEY` value.

`ANTHROPIC_API_KEY` — Do NOT set this in the shell when using a gateway. The official docs state: "When set, this key is used instead of your Claude Pro, Max, Team, or Enterprise subscription even if you are logged in." Setting it would override gateway auth and attempt to call Anthropic directly.

### Optional: gateway model discovery

```bash
export CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY=1
```

**Verified real.** This variable exists in the official Claude Code env-vars docs. When set to `1`, Claude Code queries the gateway's `/v1/models` endpoint at startup and populates the `/model` picker with the results. Requires Claude Code v2.1.129 or later. Off by default because shared-key gateways would otherwise expose all accessible models to every user. Only models whose ID begins with `claude` or `anthropic` are added by default — set model names accordingly or use `availableModels` allowlist.

Discovery caches results to `~/.claude/cache/gateway-models.json`.

### Settings file alternative (persistent across sessions)

```json
// ~/.claude/settings.json
{
  "env": {
    "ANTHROPIC_BASE_URL": "http://localhost:4000",
    "ANTHROPIC_AUTH_TOKEN": "sk-my-local-master-key",
    "CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY": "1"
  }
}
```

### Per-command model selection

```bash
claude --model opus      # routes to opus alias in LiteLLM config
claude --model sonnet    # routes to sonnet alias
claude --model haiku     # routes to haiku alias
```

---

## 4. Ollama Cloud Access Through LiteLLM

**This section requires careful reading. The reference doc's claim is partially refuted.**

### Reference doc claim (from docs/claude-code-litellm-setup.md)

> ```yaml
> model: ollama_chat/qwen3-coder:cloud
> api_base: http://localhost:11434
> ```
> 
> This requires a local Ollama daemon.

### Verdict: PARTIALLY REFUTED

The `ollama_chat/` prefix in LiteLLM points to a LOCAL Ollama daemon. LiteLLM's official Ollama provider docs only show `http://localhost:11434` as `api_base` — there is no direct Ollama Cloud support in the `ollama_chat/` or `ollama/` LiteLLM provider. Using `api_base: http://localhost:11434` requires a running local Ollama daemon.

**However**, Ollama Cloud exposes an OpenAI-compatible REST API at `https://ollama.com/v1` (confirmed by Ollama Cloud docs). LiteLLM can reach it via the `openai/` provider prefix with a custom `api_base`, bypassing the need for a local daemon.

### Correct approach: Direct Ollama Cloud (no local daemon required)

```yaml
- model_name: haiku
  litellm_params:
    model: openai/qwen3-coder    # openai/ prefix = OpenAI-compat endpoint
    api_base: https://ollama.com  # LiteLLM appends /v1/chat/completions automatically
    api_key: os.environ/OLLAMA_API_KEY
```

**Important:** Set `api_base: https://ollama.com` — do NOT include `/v1` in the base URL. LiteLLM's OpenAI-compatible provider appends `/v1/chat/completions` automatically; including `/v1` in the base would double it.

**API key:** Create at [ollama.com/settings/keys](https://ollama.com/settings/keys). Set as `OLLAMA_API_KEY` env var.

**Model names for Ollama Cloud:** The `:cloud` suffix (`qwen3-coder:cloud`) is used when routing through a local Ollama daemon (Option A in the reference doc). When calling Ollama Cloud directly via its REST API, omit the suffix — use `qwen3-coder` or the exact model tag shown in Ollama's cloud model catalog.

**Confidence:** MEDIUM — the `openai/` + `api_base: https://ollama.com` combination is inferred from LiteLLM's OpenAI-compatible provider pattern (verified in LiteLLM docs) and Ollama Cloud's confirmed OpenAI-compatible API (verified in Ollama docs). A direct LiteLLM + Ollama Cloud example was not found in LiteLLM's official docs. Test this first in the PoC before treating it as settled.

### If direct access fails: local daemon fallback

Install Ollama locally (`ollama serve`) and use the reference doc's approach:

```yaml
- model_name: haiku
  litellm_params:
    model: ollama_chat/qwen3-coder:cloud
    api_base: http://ollama:11434   # if Ollama in same docker-compose network
```

The `:cloud` suffix instructs the local Ollama daemon to offload inference to Ollama Cloud. This is fully documented by Ollama. The daemon itself becomes the cloud bridge.

**Sources:**
- [LiteLLM Ollama provider docs](https://docs.litellm.ai/docs/providers/ollama) — only shows local daemon | Confidence: HIGH
- [LiteLLM OpenAI-compatible endpoints](https://docs.litellm.ai/docs/providers/openai_compatible) | Confidence: HIGH
- [Ollama Cloud docs](https://docs.ollama.com/cloud) — confirms direct API at `https://ollama.com/v1` | Confidence: HIGH
- [Fabio Rehm blog — Raspberry Pi + Ollama Cloud API, Apr 2026](https://fabiorehm.com/blog/2026/04/12/pi-ollama-cloud-api/) — third-party, not authoritative | Confidence: MEDIUM

---

## 5. Anthropic/Claude Backend Through LiteLLM

**Verified against:** [LiteLLM Anthropic provider docs](https://docs.litellm.ai/docs/providers/anthropic) | Confidence: HIGH

### Credentials required

LiteLLM needs a standard Anthropic API key (`sk-ant-...`) from [console.anthropic.com](https://console.anthropic.com). Claude Max subscription OAuth is NOT usable here (see Critical Pre-Reading above).

### Model string format

```
anthropic/<model-id>
```

Examples:
- `anthropic/claude-opus-4-5`
- `anthropic/claude-sonnet-4-5-20250929`
- `anthropic/claude-haiku-3-5`

Always verify current model IDs at [Anthropic model docs](https://docs.anthropic.com/en/docs/about-claude/models) — these change frequently.

### Config example

```yaml
- model_name: sonnet
  litellm_params:
    model: anthropic/claude-sonnet-4-5-20250929
    api_key: os.environ/ANTHROPIC_API_KEY
```

No `api_base` needed for Anthropic — LiteLLM uses `api.anthropic.com` by default.

---

## 6. Secrets and Auth: Local Single-User Setup

**Verified against:** [LiteLLM proxy configs](https://docs.litellm.ai/docs/proxy/configs), [Claude Code LLM gateway docs](https://code.claude.com/docs/en/llm-gateway) | Confidence: HIGH

### LiteLLM master key

The `LITELLM_MASTER_KEY` authenticates requests TO the LiteLLM proxy. For a single-user local setup this is also the virtual key. Must start with `sk-`.

```yaml
# config.yaml
general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY
```

```bash
# .env
LITELLM_MASTER_KEY=sk-my-local-master-key-change-me
```

### Virtual keys

For a single-developer local PoC, virtual key management is unnecessary overhead. Use the master key directly in `ANTHROPIC_AUTH_TOKEN`. Skip virtual key administration.

### .env handling

- Keep a `.env` file at repo root (gitignored).
- docker-compose reads `.env` automatically for `${VAR}` interpolation.
- Never embed credentials in `config.yaml` or `docker-compose.yml`.
- All credentials in config.yaml reference `os.environ/VAR_NAME`.

### Claude Code auth to gateway

```
Claude Code  --(Bearer ANTHROPIC_AUTH_TOKEN)--> LiteLLM  --(ANTHROPIC_API_KEY)--> Anthropic
```

`ANTHROPIC_AUTH_TOKEN` = LiteLLM master key (local gateway auth)
`ANTHROPIC_API_KEY` = Anthropic API key (set in LiteLLM's env, not Claude Code's env)

Do NOT set `ANTHROPIC_API_KEY` in Claude Code's shell environment — that would bypass the gateway and call Anthropic directly.

---

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| `ghcr.io/berriai/litellm:main-stable` | `litellm/litellm:latest` on Docker Hub | `main-stable` tag is more explicit about stability; both work |
| `openai/` prefix for Ollama Cloud | `ollama_chat/` prefix | `ollama_chat/` requires local daemon; `openai/` hits cloud REST API directly |
| Anthropic API key | Claude Max OAuth token | OAuth in third-party tools banned by Anthropic since April 2026 |
| No database (plain image) | `litellm-database` image + Postgres | Single-user PoC has no need for spend tracking or multi-user audit logs |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| LiteLLM v1.82.7 / v1.82.8 | Confirmed credential-stealing malware | `main-stable` (v1.85.0+) |
| `ANTHROPIC_API_KEY` in Claude Code shell env | Bypasses the gateway, calls Anthropic directly | `ANTHROPIC_AUTH_TOKEN` set to LiteLLM master key |
| `ollama_chat/<model>:cloud` + `api_base: http://localhost:11434` | Requires local Ollama daemon (reference doc pattern) | `openai/<model>` + `api_base: https://ollama.com` for daemon-free cloud access |
| Hard-coded credentials in config.yaml | Security and reproducibility | `os.environ/VAR_NAME` references + `.env` file |
| Claude Max subscription OAuth via LiteLLM | Violates Anthropic ToS since April 2026 | Anthropic API key (pay-per-token) |

---

## Reference Doc Claim Audit

Claims from `docs/claude-code-litellm-setup.md` (ChatGPT-authored, non-authoritative):

| Claim | Status | Finding |
|-------|--------|---------|
| `ANTHROPIC_BASE_URL=http://localhost:4000` | CONFIRMED | Verified in official Claude Code env-vars docs |
| `CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY=1` | CONFIRMED | Variable exists; exact name verified in Claude Code env-vars docs; requires Claude Code v2.1.129+ |
| `ANTHROPIC_AUTH_TOKEN=your-litellm-key` | CONFIRMED | Verified; sent as `Authorization: Bearer` header to the gateway |
| `ollama_chat/qwen3-coder:cloud` + `api_base: http://localhost:11434` | PARTIALLY REFUTED | Works but requires local Ollama daemon; direct cloud access via `openai/` + `https://ollama.com` avoids daemon |
| "Ollama exposes Anthropic-compatible endpoints" | MISLEADING | Local Ollama exposes OpenAI-compat endpoints, NOT Anthropic-compat; LiteLLM is the Anthropic translation layer |
| Claude Max routes through LiteLLM | REFUTED | Anthropic banned third-party OAuth use (enforced April 2026); API key required instead |

---

## Sources

- [Claude Code environment variables (official)](https://code.claude.com/docs/en/env-vars) — `ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_API_KEY`, `CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY`
- [Claude Code LLM gateway configuration (official)](https://code.claude.com/docs/en/llm-gateway) — full LiteLLM integration guide, auth methods, model discovery behavior
- [LiteLLM Docker deploy docs](https://docs.litellm.ai/docs/proxy/deploy) — image name, docker-compose shape
- [LiteLLM proxy configs docs](https://docs.litellm.ai/docs/proxy/configs) — config.yaml structure, `os.environ/`, `master_key`
- [LiteLLM Anthropic provider docs](https://docs.litellm.ai/docs/providers/anthropic) — model string format
- [LiteLLM Ollama provider docs](https://docs.litellm.ai/docs/providers/ollama) — local daemon only; no cloud mention
- [LiteLLM OpenAI-compatible endpoints](https://docs.litellm.ai/docs/providers/openai_compatible) — `openai/` prefix + custom `api_base`
- [LiteLLM GitHub releases](https://github.com/BerriAI/litellm/releases) — v1.85.0 current stable
- [Ollama Cloud docs](https://docs.ollama.com/cloud) — direct API at `https://ollama.com`, API key auth
- [Ollama OpenAI compatibility docs](https://docs.ollama.com/api/openai-compatibility) — OpenAI-compat endpoint behavior
- [The Register — Anthropic bans third-party OAuth, Feb 2026](https://www.theregister.com/2026/02/20/anthropic_clarifies_ban_third_party_claude_access/)
- [Kersai — third-party Claude access workarounds, Apr 2026](https://kersai.com/anthropic-killed-third-party-claude-access-heres-every-workaround-that-still-works/)
