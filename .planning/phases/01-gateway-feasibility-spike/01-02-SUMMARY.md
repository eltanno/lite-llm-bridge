---
phase: 01-gateway-feasibility-spike
plan: 02
subsystem: infra
tags: [claude-max, oauth-forwarding, anthropic, litellm, claude-code, auth]

requires:
  - phase: 01-01
    provides: "Running gateway at localhost:4000 with config.yaml (3 aliases, scoped forwarding)"
provides:
  - "Verified Max OAuth path: claude --model claude-sonnet round-trips through the gateway to Anthropic on the Max subscription"
  - "E-01 confirmed: model_group_settings scoped forwarding is active on main-stable (no global fallback needed)"
  - "Confirmed Claude Code host wiring: ANTHROPIC_BASE_URL + ANTHROPIC_CUSTOM_HEADERS, both ANTHROPIC_API_KEY and ANTHROPIC_AUTH_TOKEN unset (per-command, D-08)"
affects: [01-03 (Ollama agentic round-trip)]

tech-stack:
  added: []
  patterns: ["Per-command host env for the Max test shell (never global ~/.claude); executor never runs claude (D-08)"]

key-files:
  created: []
  modified: [README.md]

key-decisions:
  - "E-01 resolved as SCOPED forwarding active (kept config.yaml model_group_settings list; no global-forwarding fallback)"
  - "D-07 decision gate: PASSED on the OAuth path — no Anthropic API-key fallback taken, PROJECT.md unchanged"

patterns-established:
  - "Behavioral proof over display: a 200 + a 429 from api.anthropic.com (real request_id) + Max session meter hitting 100% prove the Max bearer is forwarded and consumed"

requirements-completed: [CC-01, CC-03, MAX-01, MAX-02]

duration: ~10min active (85min wall-clock incl. human checkpoint)
completed: 2026-05-20
---

# Phase 1 Plan 02: Max OAuth Path Verified Summary

**Claude Max subscription confirmed serving the `claude-opus`/`claude-sonnet` aliases through the gateway via scoped OAuth-bearer forwarding — the D-07 make-or-break gate passed, no API-key fallback needed.**

## Performance

- **Duration:** ~10 min active work (≈85 min wall-clock including the human checkpoint wait)
- **Started:** 2026-05-20T20:01:43Z
- **Completed:** 2026-05-20T21:27:03Z
- **Tasks:** 3 (1 autonomous, 1 human checkpoint, 1 docs)
- **Files modified:** 1 (README.md)

## Accomplishments
- **E-01 confirmed (autonomous + behavioral):** the `model_group_settings.forward_client_headers_to_llm_api: [claude-opus, claude-sonnet]` scoped list parses and is honored on `ghcr.io/berriai/litellm:main-stable`. No global-forwarding fallback was needed; `config.yaml` is unchanged.
- **MAX-01 / MAX-02 confirmed (human checkpoint):** `claude --model claude-sonnet "What is 2+2?"` returned a correct response (gateway log shows `POST /v1/messages 200 OK`), routed to `https://api.anthropic.com/v1/messages`. The Max **current-session usage meter reached 100%** from the test traffic — proof the Max subscription (not an API key) served the requests.
- **CC-01 / CC-03 confirmed:** host wired with `ANTHROPIC_BASE_URL=http://localhost:4000` + `ANTHROPIC_CUSTOM_HEADERS` (`x-litellm-api-key: Bearer …`), both `ANTHROPIC_API_KEY` and `ANTHROPIC_AUTH_TOKEN` unset; switching aliases needed only `--model`.
- **D-08 honored:** the executor never ran `claude`; the live login/round-trip was the human's, env vars were per-command in a separate shell, global `~/.claude/` untouched.

## Task Commits

1. **Task 1: Wire host env + E-01 forwarding probe** — no commit (config parsed clean; scoped forwarding worked first try, so no config edit)
2. **Task 2: Max login + live round-trip (human checkpoint)** — no commit (human verification)
3. **Task 3: Record verified Max path + troubleshooting** — `e61a237` (docs)

**Plan metadata:** (this SUMMARY commit)

## Files Created/Modified
- `README.md` — added a "Verified (Phase 1)" note (Max path confirmed via `/status`) and a "Troubleshooting" section (429 usage-limit and 400 canonical-id guidance)

## Decisions Made
- **E-01 → scoped forwarding (no fallback):** the scoped list is active on the pinned image, so the more precise config was kept; the global-forwarding fallback was not needed.
- **D-07 → no fallback:** the OAuth path works, so the Claude aliases stay on Max OAuth forwarding (no Anthropic API key introduced; PROJECT.md not modified).

## Deviations from Plan
None - plan executed as written. Task 1's documented E-01 fallback was not triggered because scoped forwarding worked on first try.

## Issues Encountered
- **Transient `429 Too Many Requests` from `api.anthropic.com`** — confirmed by the user to be **Max usage limits** (current 5h session 100% used; weekly all-models 96% used; resets ~2026-05-21), NOT a config issue. The 429 originating from `api.anthropic.com` is itself positive evidence that forwarding works. Documented in README troubleshooting.
- **`400 Invalid model name passed in model=claude-sonnet-4-6`** — requests that send the *canonical* model id rather than the `claude-sonnet` alias (e.g. a bare `claude` with no `--model`, or some Claude Code background calls) are rejected because only the aliases are in `config.yaml`'s `model_list`. The designed alias path (`claude --model claude-sonnet`) returns 200. Documented in README; optional future enhancement is to add canonical-id `model_list` entries so bare/background requests also route. **Surfaced to the user as a decision (architectural — would extend D-01's alias-only model); not auto-applied.**

## User Setup Required
None new — the existing global Max login is reused (D-08). Max browser login was already in place; the test consumed Max session quota as expected.

## Next Phase Readiness
- Max path proven. **Plan 01-03 (Ollama agentic round-trip) does NOT use Max** — it routes `claude --model claude-haiku` to Ollama Cloud, so the user's current Max usage-limit exhaustion will not block it.
- Carry-forward: E-03 (deepseek-v4-pro tool-calling fidelity through LiteLLM) is the remaining empirical gate, validated in Plan 01-03.
- Open question for the user: whether to add canonical model ids (e.g. `claude-sonnet-4-6`) as extra aliases so bare/background Claude Code requests route too.

---
*Phase: 01-gateway-feasibility-spike*
*Completed: 2026-05-20*
