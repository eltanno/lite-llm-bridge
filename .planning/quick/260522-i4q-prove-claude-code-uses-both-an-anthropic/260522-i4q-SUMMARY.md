---
id: 260522-i4q
slug: prove-claude-code-uses-both-an-anthropic
date: 2026-05-22
type: quick
status: complete
---

# Quick Task 260522-i4q — Summary

## Outcome: SUCCESS

A single LiteLLM gateway serves an Anthropic-Max alias **and** Ollama-Cloud aliases at the
same time, and Claude Code drives both. Verified end-to-end via `claude -p` (reusing the stored
Max OAuth creds), with extended thinking ON globally — the real-world condition:

| Alias                       | Backend                               | Claude Code result |
|-----------------------------|---------------------------------------|--------------------|
| `claude-opus`               | `openai/deepseek-v4-pro` (Ollama)     | `ROUTED_OPUS` ✓    |
| `claude-sonnet`             | `openai/kimi-k2.6` (Ollama)           | curl-validated ✓   |
| `claude-haiku-4-5-20251001` | `anthropic/claude-haiku-4-5-20251001` (Anthropic, Max via OAuth forwarding) | `ROUTED_HAIKU` ✓ |

## Verified facts

- **Max OAuth forwarding works.** `model_group_settings.forward_client_headers_to_llm_api`,
  scoped to the Anthropic alias only, makes LiteLLM forward Claude Code's Max OAuth bearer to
  Anthropic (real Anthropic `request_id`s returned). No Anthropic API key in play.
- **Header scoping holds.** The Ollama aliases authenticate with `OLLAMA_API_KEY`; the OAuth
  bearer is never forwarded to Ollama (Ollama calls succeed, would 401 if the bearer leaked).
- **Gateway auth for the mixed setup:** `ANTHROPIC_CUSTOM_HEADERS='x-litellm-api-key: Bearer <master-key>'`,
  with `ANTHROPIC_API_KEY` and `ANTHROPIC_AUTH_TOKEN` UNSET (the `Authorization` slot must stay
  free for the Max OAuth bearer).
- **`drop_params: true` strips thinking/effort for Ollama (OpenAI-compat) backends**, so
  `claude-opus`/`claude-sonnet` keep stable alias names and still work with thinking on.

## Key finding — an Anthropic-Haiku alias must be version-pinned

Claude Code decides whether to send extended thinking / the `effort` param by **pattern-matching
the model-ID string** ([model-config docs](https://code.claude.com/docs/en/model-config)), not by
the tier slot. Haiku 4.5 rejects both params.

- Stable `claude-haiku` alias → Claude Code doesn't recognize it as Haiku → sends thinking/effort → `400`.
- Real ID `claude-haiku-4-5-20251001` → recognized as Haiku → params omitted → works.
- Tier-pin via `ANTHROPIC_DEFAULT_HAIKU_MODEL=claude-haiku` did **not** help (detection is by string).
- `_SUPPORTED_CAPABILITIES` (the documented capability override) does **not** apply over a gateway
  — docs say only `_NAME`/`_DESCRIPTION` do.

Implication: this only bites the Anthropic-**Haiku** slot. Ollama slots and Anthropic Opus/Sonnet
slots keep stable alias names. If a stable `claude-haiku` matters more, don't back that slot with
Anthropic-Haiku.

## Client env (for the eventual global rollout — NOT applied; out of scope)

```bash
export ANTHROPIC_BASE_URL=http://localhost:4000
export ANTHROPIC_CUSTOM_HEADERS="x-litellm-api-key: Bearer <LITELLM_MASTER_KEY>"
export CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY=1
export ANTHROPIC_DEFAULT_OPUS_MODEL=claude-opus
export ANTHROPIC_DEFAULT_SONNET_MODEL=claude-sonnet
export ANTHROPIC_DEFAULT_HAIKU_MODEL=claude-haiku-4-5-20251001
# ANTHROPIC_API_KEY and ANTHROPIC_AUTH_TOKEN must remain UNSET
```

## Operational gotcha (WSL2 + Docker Desktop)

`config.yaml` is a **single-file bind mount**. Editing it swaps the inode, so `docker compose
restart` FAILS with a stale-mount error. Reload with `docker compose up -d --force-recreate litellm`
instead. Consider mounting the directory rather than the single file to remove this footgun.

## Deviations from plan

- Alias naming: chose `claude-*` (for `/model` discovery); the haiku slot was further pinned to the
  version ID after the thinking finding above.
- Executed inline (not via a worktree `gsd-executor`) — the live `docker` restart + `claude`
  round-trip can't run inside a git worktree (container mounts `config.yaml` from the main tree).
- Approach A (gateway `additional_drop_params`) was tried and rejected — it does not strip native
  Anthropic params on the `/v1/messages` → `anthropic/` passthrough.

## Follow-ups (not in this task)

- Promote to the global default for all folders (the env block above in the shell profile).
- Clean up OpenCode leftovers: `OPENCODE_DISABLE_CLAUDE_CODE_SKILLS=1` in `~/.bashrc`, `~/.config/opencode`.
- Optionally change `compose.yaml` to a directory mount to avoid the restart footgun.
