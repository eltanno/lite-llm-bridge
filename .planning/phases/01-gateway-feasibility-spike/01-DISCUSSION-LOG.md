# Phase 1: Gateway + Feasibility Spike — Discussion Log

**Mode:** `--auto` (autonomous; decisions auto-selected from prior project discussion)
**Date:** 2026-05-20

This phase's implementation decisions were largely settled during project initialization (extensive design discussion captured in `.planning/PROJECT.md` and `.planning/research/SUMMARY.md`). In `--auto` mode the remaining open implementation choices were resolved with the recommended default; no interactive questioning was performed. Full decisions are in `01-CONTEXT.md`.

## Areas & auto-selected decisions

| Area | Decision (auto / recommended) | Source |
|------|-------------------------------|--------|
| Alias → backend mapping | `claude-opus`/`claude-sonnet` → Max; `claude-haiku` → Ollama Cloud | exercises both paths (D-01) |
| Ollama model | `qwen3-coder` default; verify tool support in spike, swap if needed | recommended default (D-02) |
| OAuth forwarding | `forward_client_headers_to_llm_api` scoped to Claude groups only | research/SUMMARY.md (D-03) |
| Ollama wiring | `openai/<model>` + `api_base: https://ollama.com/v1`, no daemon | research/SUMMARY.md (D-04) |
| Header/param safety | `drop_params: true`; betas disabled for Ollama group | PITFALLS (D-05) |
| Deployment & secrets | docker-compose, pinned image, `.env` (master key + Ollama key), `.env.example` | user decision (D-06) |
| Validation | agentic spike (real tool use) + `/status` Max check; API-key fallback gate | ROADMAP decision gate (D-07) |

## Deferred (to v2, per REQUIREMENTS.md)
Fallbacks/retries · model discovery toggle · OpenAI/Gemini providers · Admin UI / DB hot-reload.

## Claude's discretion
Exact config filenames, README layout, precise current Claude model IDs behind the Max aliases.
