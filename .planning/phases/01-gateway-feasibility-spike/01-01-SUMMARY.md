---
phase: 01-gateway-feasibility-spike
plan: 01
subsystem: infra
tags: [litellm, docker-compose, gateway, ollama-cloud, anthropic, oauth-forwarding]

requires: []
provides:
  - "Running LiteLLM gateway at localhost:4000 (docker compose up -d) with /health/readiness 200"
  - "config.yaml: three aliases claude-opus/claude-sonnet (Anthropic Max via OAuth forwarding) + claude-haiku (Ollama Cloud deepseek-v4-pro)"
  - "Scoped header forwarding (claude-opus/sonnet only) + drop_params: true (HDR-01 config-level)"
  - ".env.example template + .env-driven secrets via os.environ refs (no committed secrets)"
  - "README documenting run, Claude Code wiring, and the Max login flow"
affects: [01-02 (Max OAuth round-trip), 01-03 (Ollama agentic round-trip)]

tech-stack:
  added: ["LiteLLM proxy (ghcr.io/berriai/litellm:main-stable)", "Docker Compose v2"]
  patterns: ["Secrets only in gitignored .env via os.environ/VAR_NAME", "Pinned image tag; never latest/malware builds", "Read-only config bind mount"]

key-files:
  created: [compose.yaml, config.yaml, .env.example, README.md]
  modified: []

key-decisions:
  - "Ollama-backed alias uses deepseek-v4-pro:cloud (D-02 user choice; supersedes research-body qwen3-coder-next), E-02 curl-confirmed present in cloud catalog"
  - "Kept model_group_settings scoped forwarding (E-01 not refuted at parse time — config loaded clean, all 3 aliases registered)"
  - "api_base https://ollama.com/v1 used as-is — no D-04/E-02 fallback needed"

patterns-established:
  - "Acceptance-gate-driven config: every config knob has a grep gate the executor must pass before commit"
  - "Empirical gate before trust: E-02 curl validates the Ollama endpoint before the alias is committed"

requirements-completed: [GW-01, GW-02, GW-03, AL-01, AL-02, CC-02, OLL-01, HDR-01]

duration: 4min
completed: 2026-05-20
---

# Phase 1 Plan 01: Gateway Infrastructure Summary

**LiteLLM gateway stood up on docker-compose at localhost:4000 with three aliases (claude-opus/sonnet → Anthropic Max via scoped OAuth forwarding; claude-haiku → Ollama Cloud deepseek-v4-pro), secrets externalized to a gitignored .env, and a setup README.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-05-20T19:55:51Z
- **Completed:** 2026-05-20T20:00:38Z
- **Tasks:** 3
- **Files created:** 4 (compose.yaml, config.yaml, .env.example, README.md)

## Accomplishments
- Gateway runs via `docker compose up -d`; `/health/readiness` returns HTTP 200 and a clean `docker compose down`/`up` cycle was verified (GW-01, GW-02).
- `config.yaml` exposes the three aliases with the research-specified backends, header-forwarding scoped to the Claude groups only, and `drop_params: true` (AL-01, AL-02, CC-02, OLL-01, HDR-01 at config level).
- E-02 empirical gate passed: `GET https://ollama.com/v1/models` → HTTP 200, 39 models, `deepseek-v4-pro` present.
- No secrets in any committed file; `.env` is gitignored; `.env.example` holds placeholders only (GW-03).

## Task Commits

Each task was committed atomically:

1. **Task 1: Validate Ollama endpoint (E-02) + config/secrets scaffold** - `491b869` (feat)
2. **Task 2: compose.yaml + bring gateway up; health + clean down/up** - `84d309e` (feat)
3. **Task 3: setup README (run, Claude Code wiring, Max login)** - `6e53728` (docs)

## Files Created/Modified
- `config.yaml` - model_list (3 aliases), general_settings.master_key, scoped model_group_settings forwarding, drop_params
- `compose.yaml` - single litellm service, pinned image, port 4000, :ro config mount, env_file .env
- `.env.example` - committed placeholder template (LITELLM_MASTER_KEY, OLLAMA_API_KEY)
- `README.md` - prerequisites, secrets setup, run/stop, Claude Code env wiring, Max login, alias selection, backend swap

## Decisions Made
- **Model:** `openai/deepseek-v4-pro:cloud` per D-02 (user choice 2026-05-20). The RESEARCH body still names `qwen3-coder-next`; its top-of-file MODEL UPDATE banner, SKELETON.md, and this plan's grep gates all supersede that. Fallbacks `qwen3-coder-next`/`glm-5.1` confirmed live in the cloud catalog if Plan 03 needs a swap.
- **Ollama api_base:** `https://ollama.com/v1` worked directly — no D-04 fallback (`https://ollama.com` / `ollama_chat/`) needed.
- **E-01 (model_group_settings):** config parsed cleanly on `main-stable` and all 3 aliases registered, so no fallback to global forwarding at this stage. Behavioral confirmation that the Anthropic bearer actually forwards (and does not leak to Ollama) is deferred to Plans 02/03.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Reworded compose.yaml image comment to avoid tripping the plan's own leak gate**
- **Found during:** Task 2 (compose.yaml creation)
- **Issue:** The research's exact compose.yaml comment lists the literal malware tags `1.82.7`/`1.82.8`, which this plan's own acceptance gate `grep -E '1\.82\.(7|8)|:latest'` treats as a failure when present anywhere in the file.
- **Fix:** Kept the safety warning but referred to the bad builds without the literal version tokens (e.g., "known-malware credential-stealing builds").
- **Files modified:** compose.yaml
- **Verification:** `! grep -qE '1\.82\.(7|8)|:latest' compose.yaml` passes; image still pinned to `main-stable`.
- **Committed in:** `84d309e` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug/consistency)
**Impact on plan:** Cosmetic comment wording only; pinned-image intent and supply-chain guard fully preserved. No scope creep.

## Issues Encountered
None - planned work executed cleanly; the gateway came up healthy on first boot with no config-parse errors.

## User Setup Required
The user-supplied secrets were already present in a local `.env` (OLLAMA_API_KEY, LITELLM_MASTER_KEY), so execution was not blocked. For a fresh clone, see `README.md` §1 (copy `.env.example` → `.env`, generate `LITELLM_MASTER_KEY`, paste the Ollama key from https://ollama.com/settings/keys).

## Next Phase Readiness
- Gateway is running and healthy — Plan 02 (Max OAuth round-trip) can wire the host Claude Code env and run the interactive Max login + `/status` checkpoint directly against it.
- Open empirical items carried forward: E-01 (Max bearer actually forwards / does not leak to Ollama) → Plan 02/03; E-03 (deepseek-v4-pro tool-calling fidelity through LiteLLM) → Plan 03.

---
*Phase: 01-gateway-feasibility-spike*
*Completed: 2026-05-20*
