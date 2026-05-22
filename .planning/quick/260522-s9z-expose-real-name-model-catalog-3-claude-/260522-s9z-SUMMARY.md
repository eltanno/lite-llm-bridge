---
id: 260522-s9z
slug: expose-real-name-model-catalog-3-claude-
date: 2026-05-22
type: quick
status: complete
---

# Quick Task 260522-s9z — Summary

## Outcome: SUCCESS

Replaced the 3-model test config (260522-i4q) with a **9-model real-name catalog** plus an isolated
launcher (`bin/claude-gw`). All 9 models verified routing through the gateway, and the env-var tier
wiring proven end-to-end.

## Catalog (`config.yaml`)

- **Anthropic (Max OAuth forwarding, scoped):** `claude-opus-4-7`, `claude-sonnet-4-6`, `claude-haiku-4-5-20251001`
- **Ollama Cloud (`OLLAMA_API_KEY`):** `deepseek-v4-pro`, `deepseek-v4-flash`, `kimi-k2.6`, `qwen3.5:397b`, `glm-5.1`, `minimax-m2.7`

## Verification

- `/v1/models` lists all 9.
- 6 Ollama models: HTTP 200 chat completions (names valid, routing works).
- 3 Anthropic models via `bin/claude-gw` (Max OAuth): each returned `ROUTED` — Opus/Sonnet confirmed, not just Haiku.
- **Default-tier wiring:** plain `./bin/claude-gw -p ...` → opus tier (`ANTHROPIC_DEFAULT_OPUS_MODEL=deepseek-v4-pro`) → `ROUTED_DEFAULT`. Confirms a tier swap is just an env-var change — **no container restart**.

## Usage

- **Launch:** `./bin/claude-gw [claude args]` — isolated; sets gateway env in its own process only (no `~/.bashrc`/global change), loads `LITELLM_MASTER_KEY` from `.env`.
- **Swap a tier:** edit the mapping block in `bin/claude-gw`, or override ad-hoc (`ANTHROPIC_DEFAULT_OPUS_MODEL=glm-5.1 ./bin/claude-gw`). No restart.
- **Pick a specific model:** `./bin/claude-gw --model <name>`.
- **Add a catalog model:** edit `config.yaml`, then `docker compose up -d --force-recreate litellm` (NOT `restart` — WSL2 single-file mount).

## Design notes

- Anthropic models use real IDs so Claude Code applies correct capabilities (Haiku = no thinking/effort; Opus/Sonnet = thinking). The Max bearer is forwarded only to the Anthropic group.
- Ollama models: `drop_params` strips Anthropic-only params Claude Code sends; the models reason natively. Per-model thinking is tunable with `reasoning_effort: none|low|medium|high` (Ollama `/v1`); left at model default for now.
- `qwen3.6` excluded — library/local-only, not cloud-hosted (would require a local Ollama daemon).

## Out of scope / follow-ups

- Promote to the **global default** for all folders (put the `bin/claude-gw` env, or its vars, into your shell profile).
- Decide the **real default tier mapping** — the launcher currently defaults to the earlier test mapping (opus=`deepseek-v4-pro`, sonnet=`kimi-k2.6`, haiku=`claude-haiku-4-5-20251001`).
- Clean up OpenCode leftovers (`OPENCODE_DISABLE_CLAUDE_CODE_SKILLS=1` in `~/.bashrc`, `~/.config/opencode`).
- Optional: `compose.yaml` directory mount to avoid the recreate-on-edit footgun.
