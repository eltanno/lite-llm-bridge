# Roadmap: LiteLLM Bridge

## Overview

One phase delivers the entire v1 PoC: stand up the docker-compose gateway, wire both backend paths (Claude Max via OAuth forwarding and Ollama Cloud via direct API), prove agentic tool use end-to-end through an Ollama-backed alias, and confirm the Max subscription is in use through the gateway. At coarse granularity this is one coherent deliverable — every v1 requirement feeds into it and there is no second natural cluster that would justify splitting.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Gateway + Feasibility Spike** - Stand up the LiteLLM gateway and prove both backend paths end-to-end with real agentic tool use

## Phase Details

### Phase 1: Gateway + Feasibility Spike

**Goal**: The LiteLLM gateway is running, both backend paths are validated end-to-end with real Claude Code agentic sessions, and the Max subscription is confirmed in use through the gateway.
**Mode:** mvp
**Depends on**: Nothing (first phase)
**Requirements**: GW-01, GW-02, GW-03, CC-01, CC-02, CC-03, AL-01, AL-02, MAX-01, MAX-02, OLL-01, OLL-02, HDR-01
**Success Criteria** (what must be TRUE):

  1. `docker compose up` starts the gateway and `curl http://localhost:4000/health` returns a healthy response; `docker compose down` stops it cleanly; `compose.yaml` and `config.yaml` are committed and no secrets appear in either.
  2. `claude --model claude-haiku` (or another Ollama-backed alias) completes a real agentic tool-use session — file edit plus bash command — routed through the gateway to Ollama Cloud with no errors.
  3. `claude --model claude-sonnet` (or the Max-backed alias) returns a correct response and `/status` confirms the Max subscription is in use, not a per-token API key.
  4. `ANTHROPIC_BASE_URL=http://localhost:4000` is set once in Claude Code's environment; switching backends requires only `--model <alias>`, no other config change.
  5. A request to an Ollama-backed alias does not fail due to forwarded `anthropic-beta` headers or Anthropic-specific params (verified by the agentic spike completing successfully).

**Plans**: 3 plans

Plans:
**Wave 1**

- [x] 01-01-PLAN.md — Walking Skeleton: stand up the gateway (compose.yaml, config.yaml, .env scaffold, README) + E-02 Ollama-endpoint gate

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 01-02-PLAN.md — Max OAuth path end-to-end: wire Claude Code, E-01 forwarding gate, Max login, /status confirms subscription (D-07 decision gate)

**Wave 3** *(blocked on Wave 2 completion)*

- [ ] 01-03-PLAN.md — Ollama Cloud path + agentic spike: OLL-02 file-edit+bash session, model swap (E-03), HDR-01 verification

**Decision gate (Phase 1):** If Max OAuth forwarding (`forward_client_headers_to_llm_api`) fails on `ghcr.io/berriai/litellm:main-stable`, fall back to Anthropic API key (per-token) and note the decision in PROJECT.md before proceeding. Do not build workarounds.

## Progress

**Execution Order:**
Phases execute in numeric order.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Gateway + Feasibility Spike | 2/3 | In Progress|  |
