---
phase: 01-gateway-feasibility-spike
plan: 03
subsystem: infra
tags: [ollama-cloud, deepseek-v4-pro, agentic, tool-use, litellm, claude-code, hdr-01]

requires:
  - phase: 01-01
    provides: "Gateway with claude-haiku -> openai/deepseek-v4-pro:cloud @ https://ollama.com/v1"
  - phase: 01-02
    provides: "Host env wired + forwarding form settled (scoped)"
provides:
  - "Verified Ollama Cloud agentic path: claude --model claude-haiku completes a Write + bash tool-use session through the gateway"
  - "OLL-02 confirmed: tool_use/tool_result fidelity survives LiteLLM Anthropic<->OpenAI translation on deepseek-v4-pro (no model swap)"
  - "HDR-01 confirmed: anthropic-beta not forwarded to Ollama; drop_params strips Anthropic params; CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1 session safety net"
affects: []

tech-stack:
  added: []
  patterns: ["Agentic acceptance over curl: tool-use fidelity proven by a real Claude Code session, not a text round-trip (D-07)"]

key-files:
  created: []
  modified: [README.md]

key-decisions:
  - "OLL-02 passed on default deepseek-v4-pro:cloud — no D-02 model swap needed (fallbacks qwen3.5/glm-5.1 untouched)"
  - "OLL-01 also confirmed autonomously via raw curl to the gateway (/v1/messages -> custom_llm_provider:openai -> Ollama), independent of Max limits"

patterns-established:
  - "Two-layer beta safety: client-side CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1 + gateway scoped forwarding + drop_params"

requirements-completed: [OLL-01, OLL-02, CC-03, HDR-01]

duration: 14min
completed: 2026-05-20
---

# Phase 1 Plan 03: Ollama Agentic Path Verified Summary

**A real `claude --model claude-haiku` session created and read back a file (Write + bash) end-to-end through the gateway to Ollama Cloud on deepseek-v4-pro — tool_use/tool_result fidelity confirmed (OLL-02), no model swap needed.**

## Performance

- **Duration:** ~14 min (incl. human agentic checkpoint)
- **Started:** 2026-05-20T21:27:39Z
- **Completed:** 2026-05-20T21:42:25Z
- **Tasks:** 3 (1 autonomous pre-flight, 1 human checkpoint, 1 docs)
- **Files modified:** 1 (README.md)

## Accomplishments
- **OLL-01 (autonomous):** raw `curl` to the gateway's `/v1/messages` for `claude-haiku` returned 200 with an Anthropic-shaped reply; the response id decoded to `litellm:custom_llm_provider:openai` — confirming routing through to Ollama Cloud (`openai/` + `https://ollama.com/v1`), with no local daemon. Works independent of Max usage limits.
- **OLL-02 (human checkpoint):** the agentic session created `test-oll02.txt` ("hello from ollama") via the Write tool and read it back via bash; gateway logs show the multi-turn `tool_calls=tool_calls_for_message` loop returning repeated `200 OK`. Tool-use fidelity holds through LiteLLM's translation on the default model.
- **HDR-01:** no param-mismatch errors reached Ollama (`drop_params: true` working); `anthropic-beta` not forwarded to the Ollama group (scoped forwarding + `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1`).
- **CC-03:** `claude-haiku` selected purely via `--model`, no other config change.
- **D-08 honored:** executor used only raw curl + logs; the agentic `claude` session was the human's; `~/.claude/` untouched.

## Task Commits

1. **Task 1: Ollama routing pre-flight (curl + log check)** — no commit (verification only; config already correct, no edit)
2. **Task 2: Agentic tool-use spike (human checkpoint)** — no commit (human verification)
3. **Task 3: Record verified Ollama agentic path** — `dd69b5d` (docs)

**Plan metadata:** (this SUMMARY commit)

## Files Created/Modified
- `README.md` — extended the "Verified (Phase 1)" section with the Ollama agentic result (model `deepseek-v4-pro`, HDR-01 confirmation)
- `test-oll02.txt` — created by the spike, then removed (test artifact, never committed)

## Decisions Made
- **No model swap (E-03):** `deepseek-v4-pro:cloud` passed tool-calling on the first try, so the D-02 fallback chain (`qwen3.5:cloud` → `glm-5.1:cloud`) was not needed; `config.yaml` is unchanged.

## Deviations from Plan
None - plan executed as written. The optional E-03/D-02 model-swap branch was not triggered.

## Issues Encountered
- **One trailing `400 Bad Request`** on `/v1/messages?beta=true` during the session — consistent with the canonical-id/background pattern documented in Plan 02 (a non-alias request), not the agentic tool loop, which returned 200s. Did not affect the result.
- **`[Non-Blocking] LiteLLM.Success_Call Error: validation error for AnthropicResponse`** — a LiteLLM telemetry/logging-path quirk coercing a streaming `ResponseCompletedEvent` into its `AnthropicResponse` model. LiteLLM itself labels it non-blocking; the request returned 200 and the session succeeded. No functional impact; flagged for awareness.

## User Setup Required
None - reused the existing Max login (D-08); Ollama key already in `.env` from Plan 01.

## Next Phase Readiness
- **Phase 1 walking skeleton is complete end-to-end:** gateway up, Max path verified, Ollama agentic path verified. All 13 v1 requirements exercised.
- Open item for the user (carried from Plan 02): optionally add canonical model ids (e.g. `claude-sonnet-4-6`) as extra `model_list` aliases so bare `claude` / background requests route too.
- Note: the `LiteLLM.Success_Call` logging warning is worth a glance if structured logging/observability is added in v2.

---
*Phase: 01-gateway-feasibility-spike*
*Completed: 2026-05-20*
