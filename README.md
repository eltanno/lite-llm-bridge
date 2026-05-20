# LiteLLM Bridge

A local, Dockerized **LiteLLM gateway** that lets Claude Code reach multiple model providers behind stable aliases — `claude-opus`, `claude-sonnet`, `claude-haiku`. Claude Code points once at `http://localhost:4000` and never changes its config; you pick the model per command with `claude --model <alias>`, and you swap the backend behind any alias by editing `config.yaml`.

In this v1:

| Alias | Backend |
|-------|---------|
| `claude-opus` | Claude (Max subscription via OAuth forwarding) → `anthropic/claude-opus-4-7` |
| `claude-sonnet` | Claude (Max subscription via OAuth forwarding) → `anthropic/claude-sonnet-4-6` |
| `claude-haiku` | Ollama Cloud → `openai/deepseek-v4-pro:cloud` |

## Prerequisites

- **Docker + Docker Compose v2** — check with `docker compose version`
- A **Claude Max subscription** — the `claude-opus`/`claude-sonnet` aliases reuse it via OAuth forwarding (no per-token API billing)
- An **Ollama Cloud API key** — create one at https://ollama.com/settings/keys

## 1. Configure secrets

Secrets live only in a local `.env`, which is **gitignored and must never be committed**. A committed `.env.example` documents the shape.

```bash
cp .env.example .env
```

Then edit `.env`:

- `LITELLM_MASTER_KEY` — the key Claude Code uses to authenticate to the gateway. It **must start with `sk-`**. Generate a random value:
  ```bash
  echo "sk-$(openssl rand -hex 16)"
  ```
- `OLLAMA_API_KEY` — paste your key from https://ollama.com/settings/keys

`config.yaml` and `compose.yaml` contain **no secrets** — they reference `os.environ/LITELLM_MASTER_KEY` and `os.environ/OLLAMA_API_KEY`, which Docker injects from `.env`.

## 2. Run the gateway

```bash
docker compose up -d        # start (pulls the pinned image on first run)
docker compose down         # stop and remove the container
```

Health check:

```bash
curl -fsS http://localhost:4000/health/readiness
# -> {"status":"healthy","db":"Not connected"}
```

## 3. Point Claude Code at the gateway

Three things must be true in the shell that runs Claude Code:

- `ANTHROPIC_BASE_URL` points at the gateway.
- The gateway key travels in `ANTHROPIC_CUSTOM_HEADERS` as `x-litellm-api-key: Bearer …` — **not** in `ANTHROPIC_AUTH_TOKEN`.
- Both `ANTHROPIC_API_KEY` and `ANTHROPIC_AUTH_TOKEN` are **unset** (see why below).

### Shell exports

```bash
export ANTHROPIC_BASE_URL=http://localhost:4000
export ANTHROPIC_CUSTOM_HEADERS="x-litellm-api-key: Bearer sk-<your-LITELLM_MASTER_KEY>"

unset ANTHROPIC_API_KEY      # if set, overrides the Max subscription and bills per-token
unset ANTHROPIC_AUTH_TOKEN   # if set, rides in Authorization and collides with the Max OAuth bearer
```

### Or persist in `~/.claude/settings.json`

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "http://localhost:4000",
    "ANTHROPIC_CUSTOM_HEADERS": "x-litellm-api-key: Bearer sk-<your-LITELLM_MASTER_KEY>"
  }
}
```

> Do **not** add `ANTHROPIC_API_KEY` or `ANTHROPIC_AUTH_TOKEN` here either.

**Why both must be absent:**

- `ANTHROPIC_API_KEY` takes auth precedence over the Max OAuth login. If it is set anywhere in the environment, Claude Code calls Anthropic directly with that key (per-token billing) and bypasses the gateway entirely.
- `ANTHROPIC_AUTH_TOKEN` is sent as `Authorization: Bearer …` — the same header the Max OAuth bearer occupies. Setting it replaces the OAuth bearer and breaks Max forwarding. That is why the gateway key travels in a separate header (`x-litellm-api-key`) via `ANTHROPIC_CUSTOM_HEADERS`.

## 4. Log in to Claude Max

With `ANTHROPIC_API_KEY` unset, start Claude Code and log in through the browser with your Max account:

```bash
claude            # opens a browser login (or prints a URL) the first time
claude /status    # confirm it shows the Max subscription, not an API key
```

Claude Code stores the OAuth bearer locally; every request then carries it in `Authorization: Bearer …`. With `ANTHROPIC_BASE_URL` set, that bearer reaches the gateway, which forwards it to Anthropic for the `claude-opus` and `claude-sonnet` aliases.

## 5. Select a model per command

```bash
claude --model claude-opus      # Claude Opus 4.7   (Max)
claude --model claude-sonnet    # Claude Sonnet 4.6 (Max)
claude --model claude-haiku     # Ollama Cloud (deepseek-v4-pro)
```

When using the Ollama-backed `claude-haiku` alias, also set `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1` for that session so Anthropic beta headers are never sent to Ollama:

```bash
CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1 claude --model claude-haiku "your prompt"
```

## 6. Change a backend

Edit the alias's `litellm_params.model` (and `api_base`/`api_key` if needed) in `config.yaml`, then restart — Claude Code's configuration never changes:

```bash
docker compose restart
```

## Verified (Phase 1)

The **Max path is confirmed working**: `claude --model claude-sonnet` round-trips through the gateway to Anthropic on the **Claude Max subscription** — verified by `claude /status` showing the subscription (not an `sk-ant-` API key) and a correct live response. Header forwarding is scoped to the `claude-opus`/`claude-sonnet` groups via `model_group_settings.forward_client_headers_to_llm_api`, so the Ollama alias never receives the Anthropic bearer.

## Troubleshooting

- **`429 Too Many Requests` from `api.anthropic.com`** — the Max subscription is being rate-limited (common when two Claude Code sessions hit Max at once). It also confirms forwarding is working; wait and retry.
- **`400 Invalid model name passed in model=claude-...`** — the request used a *canonical* model id instead of an alias. Only `claude-opus`/`claude-sonnet`/`claude-haiku` are in `config.yaml`'s `model_list`, so a bare `claude` (no `--model`) or some background calls that send the resolved id are rejected. Always pass `claude --model <alias>`, or add the canonical ids as extra `model_list` entries if you want bare/background requests to route too.

---

*Single-developer, localhost-only proof of concept. The gateway binds `4000:4000`; do not expose it beyond loopback.*
