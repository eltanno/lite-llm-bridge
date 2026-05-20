<!-- GSD:project-start source:PROJECT.md -->
## Project

**LiteLLM Bridge**

A local, Dockerized **LiteLLM gateway** that lets Claude Code drive multiple model providers behind stable semantic aliases (`opus` / `sonnet` / `haiku`). Claude Code points only at the gateway (`ANTHROPIC_BASE_URL=http://localhost:4000`) and never changes its config; each alias maps to a configurable backend, selected per-invocation with `claude --model <alias>`. Built for a single developer running locally. v1 fronts a **Claude Max** subscription and **Ollama Cloud**.

**Core Value:** Point Claude Code at one stable local endpoint and reach any chosen model through `opus`/`sonnet`/`haiku` aliases — swapping the provider underneath without ever touching Claude Code's configuration.

### Constraints

- **Tech stack**: LiteLLM as the gateway, Docker / docker-compose — user asked for a "container".
- **Verification (process)**: Every technical decision must be verified against official LiteLLM / Anthropic / Ollama documentation and working examples before adoption; `docs/` is not a source of truth.
- **Cost**: Reuse the existing Claude Max subscription instead of per-token Anthropic API billing — achieved via LiteLLM OAuth-token forwarding (verified). Avoid setting `ANTHROPIC_API_KEY` in Claude Code's environment (it overrides the subscription).
- **Deployment**: Local-only (`localhost`), single developer.
- **Compatibility**: Must work with Claude Code's model selection (`claude --model <alias>`) and the Anthropic Messages API shape.
- **Client-config stability**: Claude Code's `ANTHROPIC_BASE_URL` is set once and never changed to switch models.
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## Critical Pre-Reading: Claude Max Feasibility Decision
## Recommended Stack
### Core Technologies
| Technology | Version/Tag | Purpose | Why Recommended |
|------------|-------------|---------|-----------------|
| LiteLLM Proxy | `main-stable` (v1.85.0 as of 2026-05-20) | Gateway — translates Anthropic Messages API to/from provider APIs | Official gateway explicitly supported by Claude Code docs; named in Claude Code's LLM gateway guide |
| Docker / docker-compose | Docker CE latest; Compose v2 | Container runtime | User requirement; stateless config-file-driven, no DB needed for single-user PoC |
- [LiteLLM Docker Hub tags](https://hub.docker.com/r/litellm/litellm/tags) | Confidence: HIGH
- [LiteLLM GitHub releases](https://github.com/BerriAI/litellm/releases) | Confidence: HIGH
- [Claude Code LLM gateway docs — LiteLLM section](https://code.claude.com/docs/en/llm-gateway) | Confidence: HIGH
## 1. Docker Compose Shape (Minimal Working Example)
# docker-compose.yml
# .env  (never commit this file)
- The config file mounts at `/app/config.yaml` inside the container.
- `LITELLM_MASTER_KEY` must start with `sk-` and is required for the proxy to enforce auth on incoming requests.
- Provider credentials are passed as env vars and referenced in config.yaml via `os.environ/VAR_NAME` syntax.
- For a PoC with no DB, omit `DATABASE_URL` and use the plain `litellm:main-stable` image (not `litellm-database`).
## 2. config.yaml Model List Structure
# config.yaml
- `model_name` is the public-facing alias Claude Code uses with `claude --model <alias>`.
- `litellm_params.model` is the routing string in `provider/model-id` format.
- `os.environ/VAR_NAME` is LiteLLM's syntax for pulling values from environment at runtime.
- Do not hard-code credentials in this file.
## 3. Claude Code Client Configuration
### Required variables
### Optional: gateway model discovery
### Settings file alternative (persistent across sessions)
### Per-command model selection
## 4. Ollama Cloud Access Through LiteLLM
### Reference doc claim (from docs/claude-code-litellm-setup.md)
### Verdict: PARTIALLY REFUTED
### Correct approach: Direct Ollama Cloud (no local daemon required)
- model_name: haiku
### If direct access fails: local daemon fallback
- model_name: haiku
- [LiteLLM Ollama provider docs](https://docs.litellm.ai/docs/providers/ollama) — only shows local daemon | Confidence: HIGH
- [LiteLLM OpenAI-compatible endpoints](https://docs.litellm.ai/docs/providers/openai_compatible) | Confidence: HIGH
- [Ollama Cloud docs](https://docs.ollama.com/cloud) — confirms direct API at `https://ollama.com/v1` | Confidence: HIGH
- [Fabio Rehm blog — Raspberry Pi + Ollama Cloud API, Apr 2026](https://fabiorehm.com/blog/2026/04/12/pi-ollama-cloud-api/) — third-party, not authoritative | Confidence: MEDIUM
## 5. Anthropic/Claude Backend Through LiteLLM
### Credentials required
### Model string format
- `anthropic/claude-opus-4-5`
- `anthropic/claude-sonnet-4-5-20250929`
- `anthropic/claude-haiku-3-5`
### Config example
- model_name: sonnet
## 6. Secrets and Auth: Local Single-User Setup
### LiteLLM master key
# config.yaml
# .env
### Virtual keys
### .env handling
- Keep a `.env` file at repo root (gitignored).
- docker-compose reads `.env` automatically for `${VAR}` interpolation.
- Never embed credentials in `config.yaml` or `docker-compose.yml`.
- All credentials in config.yaml reference `os.environ/VAR_NAME`.
### Claude Code auth to gateway
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
## Reference Doc Claim Audit
| Claim | Status | Finding |
|-------|--------|---------|
| `ANTHROPIC_BASE_URL=http://localhost:4000` | CONFIRMED | Verified in official Claude Code env-vars docs |
| `CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY=1` | CONFIRMED | Variable exists; exact name verified in Claude Code env-vars docs; requires Claude Code v2.1.129+ |
| `ANTHROPIC_AUTH_TOKEN=your-litellm-key` | CONFIRMED | Verified; sent as `Authorization: Bearer` header to the gateway |
| `ollama_chat/qwen3-coder:cloud` + `api_base: http://localhost:11434` | PARTIALLY REFUTED | Works but requires local Ollama daemon; direct cloud access via `openai/` + `https://ollama.com` avoids daemon |
| "Ollama exposes Anthropic-compatible endpoints" | MISLEADING | Local Ollama exposes OpenAI-compat endpoints, NOT Anthropic-compat; LiteLLM is the Anthropic translation layer |
| Claude Max routes through LiteLLM | REFUTED | Anthropic banned third-party OAuth use (enforced April 2026); API key required instead |
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
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
