# Pitfalls Research

**Domain:** Local Dockerized LiteLLM gateway for Claude Code (Claude Max + Ollama Cloud)
**Researched:** 2026-05-20
**Confidence:** HIGH for pitfalls 1-4; MEDIUM for pitfall 5; HIGH for pitfalls 6-9

---

## VERDICT: Claude Max Without API Billing — NOT FEASIBLE

**This is the most important output of this research document.**

Routing Claude Code's OAuth subscription token through a LiteLLM proxy to Anthropic — so that Max subscription usage is billed at the flat subscription rate rather than per-token — violates Anthropic's Consumer Terms of Service and is actively enforced server-side as of April 4, 2026.

**What Anthropic's official docs say (verbatim):**

> "OAuth authentication is intended exclusively for purchasers of Claude Free, Pro, Max, Team, and Enterprise subscription plans and is designed to support ordinary use of Claude Code and other native Anthropic applications. [...] Anthropic does not permit third-party developers to offer Claude.ai login or to route requests through Free, Pro, or Max plan credentials on behalf of their users. Anthropic reserves the right to take measures to enforce these restrictions and may do so without prior notice."
>
> — [Legal and compliance, Claude Code Docs](https://code.claude.com/docs/en/legal-and-compliance)

**What enforcement looks like:** Server-side detection blocks OAuth tokens used outside the official Claude Code binary. Two error messages are returned: `"invalid x-api-key"` (via x-api-key header) and `"OAuth authentication is currently not supported."` (via Authorization: Bearer). Accounts have been automatically banned within minutes. The enforcement is not limited to commercial tools — the personal Emacs setup of a CLIProxyAPI author stopped working the same day as commercial tools. No documented exception exists for personal localhost proxies.

**Timeline:**
- February 20, 2026: Anthropic updated Consumer Terms to explicitly prohibit OAuth token use in third-party tools
- April 4, 2026: Server-side enforcement deployed; CLIProxyAPI, OpenCode, OpenClaw, and all similar tools blocked simultaneously

**Safe fallbacks, in priority order:**
1. Use Claude Code with Max subscription directly (no gateway for Anthropic traffic), and use the gateway only for Ollama Cloud
2. Add an Anthropic API key (per-token billing) to LiteLLM for the `opus`/`sonnet`/`haiku` aliases — this works cleanly and is the supported path
3. Route Claude models through Amazon Bedrock or Google Vertex AI via LiteLLM (different billing model, full API compatibility)

**Sources (HIGH confidence — official docs + contemporaneous reporting):**
- [Legal and compliance — Claude Code Docs](https://code.claude.com/docs/en/legal-and-compliance)
- [The Register: Anthropic clarifies ban on third-party tool access to Claude](https://www.theregister.com/2026/02/20/anthropic_clarifies_ban_third_party_claude_access/)
- [CLIProxyAPI blocked April 4, 2026](https://rogs.me/2026/02/use-your-claude-max-subscription-as-an-api-with-cliproxyapi/)
- [GitHub anthropics/claude-code issue #28091 — OAuth disabled](https://github.com/anthropics/claude-code/issues/28091)
- [Hacker News community report](https://news.ycombinator.com/item?id=47069299)

---

## Critical Pitfalls

### Pitfall 1: Claude Max OAuth Passthrough — Policy Violation with Account-Ban Risk

**What goes wrong:**
Configuring LiteLLM with `forward_client_headers_to_llm_api: true` to pass Claude Code's OAuth token (sk-ant-oat01-* prefix) through to Anthropic's API. The request is rejected server-side, and the account may be automatically banned. LiteLLM's own tutorial on this ([Using Claude Code Max Subscription](https://docs.litellm.ai/docs/tutorials/claude_code_max_subscription)) documents the pattern but does not note that Anthropic disabled it in April 2026.

**Why it happens:**
The non-authoritative `docs/claude-code-litellm-setup.md` asserts "Claude Max 5x — Works well with Claude Code. LiteLLM can route Claude Code traffic while preserving Claude workflows." This is misleading: it describes routing without clarifying that the Max subscription budget cannot be accessed this way without violating ToS. LiteLLM docs lag the policy enforcement date.

**How to avoid:**
Do not configure LiteLLM to forward OAuth tokens to Anthropic. Use one of the safe fallbacks:
- Route the `opus`/`sonnet`/`haiku` aliases in LiteLLM to an **Anthropic API key** (per-token, from console.anthropic.com), not to an OAuth-derived credential
- Or do not route Claude models through LiteLLM at all — use Claude Code directly against Anthropic, and only use the gateway for Ollama Cloud aliases

**Warning signs:**
- LiteLLM config contains `forward_client_headers_to_llm_api: true` alongside an Anthropic provider entry
- You are using `ANTHROPIC_AUTH_TOKEN` with an sk-ant-oat01- token and a local LiteLLM as the base URL
- Requests return `"OAuth authentication is currently not supported."` or `"invalid x-api-key"`

**Phase to address:** Phase 1 (feasibility / foundation) — decide the architecture before any build work. The entire scope changes if Claude traffic must bypass the gateway.

---

### Pitfall 2: LiteLLM Supply Chain — Installing Compromised PyPI Versions

**What goes wrong:**
Installing LiteLLM from PyPI via `pip install litellm` or using a Dockerfile with `pip install litellm==1.82.7` or `litellm==1.82.8`. These versions were compromised in March 2026 with credential-stealing malware that exfiltrated SSH keys, API keys, environment variables, and cloud credentials.

**Why it happens:**
The LiteLLM PyPI account was compromised via a poisoned Trivy security scanner in CI/CD. Malicious versions were live for ~6 hours on March 24, 2026, but any project that pulled those versions during that window — or any cached dependency resolver that recorded them — is affected. Developers who use `pip install litellm` without pinning are also at risk from any future supply chain event.

**How to avoid:**
- Use the **official Docker image from ghcr.io/berriai/litellm** — this was not compromised because it pins dependencies in `requirements.txt`
- Pin to a specific verified version: safe versions are 1.82.6 or earlier, or 1.83.0 and later
- Never use `latest` tag or floating version specifiers
- From v1.83.0-nightly, images on ghcr.io are signed with cosign — verify with: `cosign verify --key https://raw.githubusercontent.com/BerriAI/litellm/0112e53046018d726492c814b3644b7d376029d0/cosign.pub ghcr.io/berriai/litellm:<tag>`
- In `docker-compose.yml` pin the image tag to a specific semver, e.g. `ghcr.io/berriai/litellm:v1.84.0`

**Warning signs:**
- `docker-compose.yml` uses `image: litellm/litellm:latest` or any PyPI-sourced install
- Missing image signature verification in deployment checklist

**Sources (HIGH confidence):**
- [LiteLLM Security Update March 2026](https://docs.litellm.ai/blog/security-update-march-2026)
- [GitHub issue #24518 — full compromise timeline](https://github.com/BerriAI/litellm/issues/24518)
- [Anthropic Claude Code docs warning](https://code.claude.com/docs/en/llm-gateway) — includes explicit warning about compromised versions

**Phase to address:** Phase 1 — Dockerfile and docker-compose setup.

---

### Pitfall 3: Anthropic Beta Headers Not Forwarded / Forwarded to Wrong Backend

**What goes wrong:**
Claude Code sends `anthropic-beta` headers (e.g., `prompt-caching-scope-2026-01-05`, `advanced-tool-use-2025-11-20`) on every request. If LiteLLM does not forward these to Anthropic backends, Claude Code features silently degrade (no caching, no advanced tool use). If LiteLLM forwards them unchanged to non-Anthropic backends (e.g., Ollama), those providers reject the request with `"invalid beta flag"`.

This was a documented incident in February 2026 affecting LiteLLM versions before v1.81.13-nightly.

**Why it happens:**
The Claude Code LLM gateway docs specify that the gateway "must forward request headers: `anthropic-beta`, `anthropic-version`." LiteLLM now uses `anthropic_beta_headers_config.json` for per-provider header mapping, but the config requires maintenance: new beta features added by Anthropic are not automatically mapped for all providers. Unknown headers are silently dropped without warning.

**How to avoid:**
- Pin LiteLLM to a version >= 1.81.13 (contains the fix)
- When routing to non-Anthropic backends (Ollama), set `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1` to prevent Claude Code from sending beta headers that no backend can handle
- Confirm the gateway is forwarding `anthropic-beta` and `anthropic-version` by proxying a test request through a logging middleware and inspecting outbound headers

**Warning signs:**
- Tool use failing silently when routed through the gateway
- Non-Anthropic backends returning `"invalid beta flag"` errors
- Prompt caching not activating on Anthropic backends

**Sources (HIGH confidence):**
- [LiteLLM incident report: Invalid beta headers](https://docs.litellm.ai/blog/claude-code-beta-headers-incident)
- [Claude Code LLM gateway requirements](https://code.claude.com/docs/en/llm-gateway) — lists mandatory header forwarding
- [GitHub issue #15299 — Vertex AI beta header failure](https://github.com/BerriAI/litellm/issues/15299)

**Phase to address:** Phase 2 (Anthropic API backend integration) and Phase 3 (Ollama backend).

---

### Pitfall 4: Model Name Filter Rejects Non-Anthropic Aliases in Claude Desktop

**What goes wrong:**
Claude Desktop v1.6259.1 introduced client-side model name validation that rejects model IDs not containing `claude`, `sonnet`, `opus`, `haiku`, or `anthropic` as substrings. A gateway alias like `qwen3-coder` or `deepseek` would be rejected in the Desktop app's `/model` picker with: `"expected a gateway model route referencing an Anthropic model"`.

The **CLI is not affected** — `claude --model <any-name>` works without validation. This project uses the CLI only, but the filter still governs gateway discovery results: only models whose ID begins with `claude` or `anthropic` are added to the model picker from `/v1/models`.

**Why it happens:**
Anthropic added validation to enforce that gateway model names semantically describe the underlying model family. The filter also applies to `CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY=1` results — even if the gateway exposes an Ollama alias, it won't appear in the picker unless the name passes the filter.

**How to avoid:**
- Name all gateway aliases with the pattern `claude-opus`, `claude-sonnet`, `claude-haiku` as the reference document recommends (not bare `opus`/`sonnet`/`haiku`)
- For non-Claude backends exposed through the gateway, either prefix the alias (e.g., `claude-haiku` mapping to an Ollama model) or use `ANTHROPIC_CUSTOM_MODEL_OPTION` to manually add a single custom model entry that bypasses validation
- `ANTHROPIC_CUSTOM_MODEL_OPTION` explicitly skips validation — use it for any alias that must contain non-Anthropic keywords

**Warning signs:**
- Model picker shows no discovered models despite `CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY=1` being set
- CLI works with `--model` flag but Desktop picker is empty
- Error message contains "expected a gateway model route referencing an Anthropic model"

**Sources (HIGH confidence — official docs + GitHub issue):**
- [Claude Code model configuration](https://code.claude.com/docs/en/model-config) — ANTHROPIC_CUSTOM_MODEL_OPTION docs
- [GitHub issue #56990 — model name validation breaking third-party gateways](https://github.com/anthropics/claude-code/issues/56990)
- [Claude Code LLM gateway — model selection section](https://code.claude.com/docs/en/llm-gateway)

**Phase to address:** Phase 1 (alias naming design) and Phase 2/3 (alias configuration in LiteLLM config.yaml).

---

### Pitfall 5: Ollama Cloud — Wrong Endpoint URL and Local Daemon Confusion

**What goes wrong:**
Two distinct mistakes cluster here:

1. **Wrong endpoint path:** Attempting `https://ollama.com/api/v1/` (the native Ollama API prefix) instead of the correct OpenAI-compatible endpoint `https://ollama.com/v1`. The `/api` prefix is for native Ollama commands (`ps`, `generate`), not the OpenAI-compatible layer. Using the wrong path returns 404.

2. **`ollama_chat/<model>:cloud` through local daemon vs. direct API:** The `:cloud` suffix in model names is only meaningful when routing through a running local Ollama daemon — it tells the daemon to pull from cloud infrastructure rather than local storage. If you use LiteLLM's `openai_compatible` provider pointing directly at `https://ollama.com/v1`, the `:cloud` suffix must be omitted (the cloud endpoint already knows it's serving cloud models).

The non-authoritative reference doc (`docs/claude-code-litellm-setup.md`) shows `model: ollama_chat/qwen3-coder:cloud` with `api_base: http://localhost:11434`, which requires a running local Ollama daemon. The PROJECT.md correctly notes: "The user does not currently run a local Ollama daemon, but will install one if research confirms it is required."

**Why it happens:**
Ollama's local daemon API and its cloud API share similar URLs but have different path structures. Documentation for both exists in the same namespace, making it easy to mix them up. LiteLLM's own Ollama provider docs only cover local setups — the direct cloud API path is not documented there.

**How to avoid:**
Choose one of two clean architectures and commit to it:

**Option A (direct API, no local daemon — preferred for Docker):**
```yaml
model_list:
  - model_name: claude-haiku
    litellm_params:
      model: openai/qwen3-coder        # No :cloud suffix
      api_base: https://ollama.com/v1
      api_key: ${OLLAMA_API_KEY}
```
Bearer token auth via Authorization header. Model names from the Ollama cloud catalog without `:cloud` suffix.

**Option B (via local daemon — required if daemon is installed):**
```yaml
model_list:
  - model_name: claude-haiku
    litellm_params:
      model: ollama_chat/qwen3-coder:cloud   # :cloud suffix required
      api_base: http://localhost:11434        # local daemon
```
Auth handled by daemon from stored `ollama login` credentials.

**Warning signs:**
- HTTP 404 from Ollama cloud endpoint
- `404 Not Found` on `/api/v1/` paths
- Model loads but silently runs locally despite `:cloud` suffix (daemon didn't pull from cloud)
- LiteLLM returns auth errors because Authorization header format differs between options

**Sources (MEDIUM confidence — official Ollama auth docs + community verification):**
- [Ollama API authentication](https://docs.ollama.com/api/authentication)
- [Ollama OpenAI compatibility](https://docs.ollama.com/api/openai-compatibility)
- [Pi + Ollama Cloud API: community setup post April 2026](https://fabiorehm.com/blog/2026/04/12/pi-ollama-cloud-api/)

**Phase to address:** Phase 3 (Ollama backend integration).

---

### Pitfall 6: System Prompt Attribution Block Breaks Prompt Cache at Gateway

**What goes wrong:**
Claude Code prepends a per-session attribution block (client version + conversation fingerprint) to every request's system prompt. When routed through LiteLLM, the gateway's own prompt cache keys on the full request body. Because the attribution block changes each session/turn, the cache never hits. This adds latency and defeats the purpose of LiteLLM's caching layer.

Note: Anthropic's own API strips this block before processing, so it only matters at the gateway layer.

**Why it happens:**
Claude Code's design for attribution with the first-party API does not interfere with Anthropic's caching. But any intermediate proxy that caches on raw request body will see a different system prompt prefix every request.

**How to avoid:**
Set `CLAUDE_CODE_ATTRIBUTION_HEADER=0` in Claude Code's environment. This disables the attribution block entirely. If LiteLLM caching is not in use (it is off by default for a PoC), this is a low-priority concern.

**Warning signs:**
- LiteLLM cache hit rate is 0% despite identical conversations
- Higher-than-expected latency

**Sources (HIGH confidence):**
- [Claude Code LLM gateway docs — attribution block](https://code.claude.com/docs/en/llm-gateway)
- [GitHub issue #50085 — CLAUDE_CODE_ATTRIBUTION_HEADER undocumented](https://github.com/anthropics/claude-code/issues/50085)

**Phase to address:** Phase 2 (initial LiteLLM integration). Low priority for PoC; important if caching is enabled.

---

### Pitfall 7: ANTHROPIC_API_KEY Takes Silent Precedence Over OAuth / Billing Surprise

**What goes wrong:**
If `ANTHROPIC_API_KEY` is set anywhere in the environment (shell profile, `.env`, Docker env block) alongside Max subscription OAuth credentials, Claude Code silently uses the API key and bills per-token from the API account rather than the subscription. This is the reverse of what the user expects and can produce surprise bills.

**Why it happens:**
Claude Code's authentication precedence order puts `ANTHROPIC_API_KEY` above OAuth subscription credentials. The precedence is: cloud provider > `ANTHROPIC_AUTH_TOKEN` > `ANTHROPIC_API_KEY` > `apiKeyHelper` > `CLAUDE_CODE_OAUTH_TOKEN` > subscription OAuth from login.

**How to avoid:**
- Never set `ANTHROPIC_API_KEY` in the shell profile of a machine where Max subscription usage is intended
- Run `/status` in Claude Code to confirm which auth method is active before starting a session
- If LiteLLM uses an Anthropic API key (fallback 2), set it only in the LiteLLM container's `.env` and do not export it to the shell where Claude Code runs

**Warning signs:**
- `/status` shows API key auth instead of subscription
- Anthropic Console shows API usage when no API work was done
- Balance depleted faster than expected

**Sources (HIGH confidence):**
- [Claude Code authentication docs — authentication precedence](https://code.claude.com/docs/en/authentication)

**Phase to address:** Phase 1 (environment design), Phase 2 (end-to-end verification).

---

### Pitfall 8: Non-Anthropic Backends Reject Claude Code's Anthropic-Specific Parameters

**What goes wrong:**
Claude Code generates requests with Anthropic-specific parameters (e.g., `output_config`) that it sends in the request body. When LiteLLM routes these requests to non-Anthropic backends (Ollama), the parameters are forwarded unchanged, causing the backend to reject the request with `"Unknown parameter: 'output_config'"`.

**Why it happens:**
LiteLLM's translation layer handles most parameter mapping, but newer Anthropic-specific fields added after LiteLLM's provider adapters were written pass through without translation. This is a version-drift problem — Claude Code adds new parameters faster than LiteLLM updates its translation mappings.

**How to avoid:**
- Pin LiteLLM to a version that post-dates issue #22963 (closed March 2026)
- Monitor the LiteLLM changelog when upgrading Claude Code versions, as new Claude Code releases frequently add parameters
- Test routing to each backend with a real Claude Code session, not just curl, immediately after any version change to either component

**Warning signs:**
- Requests to Ollama backend succeed via curl but fail through Claude Code
- Error contains `"Unknown parameter"` or parameter name not in Ollama's API spec
- Failures are intermittent (triggered only by specific Claude Code features)

**Sources (HIGH confidence):**
- [GitHub litellm issue #22963 — output_config failure with non-Anthropic models](https://github.com/BerriAI/litellm/issues/22963)

**Phase to address:** Phase 3 (Ollama integration) and ongoing during version updates.

---

### Pitfall 9: Subscription vs. API Reality — Deferred Providers (ChatGPT Plus, Gemini App)

**What goes wrong:**
Adding OpenAI or Gemini backends to LiteLLM expecting that existing ChatGPT Plus or Gemini app subscriptions provide API access. They do not. This would be the v1 Claude Max mistake repeated for deferred providers in v2.

**Why it happens:**
Consumer product subscriptions (ChatGPT Plus, Gemini Advanced) are entirely separate billing systems from their respective API tiers. There is no credential bridge between them.

**How to avoid:**
Verify before building, not after:
- **OpenAI:** ChatGPT Plus gives access to chatgpt.com; OpenAI API requires a separate account on platform.openai.com with API billing enabled and a separate API key
- **Gemini:** Gemini app / Google One subscription gives access to gemini.google.com; Gemini API requires a separate `GEMINI_API_KEY` from Google AI Studio or a GCP project with the Generative Language API enabled
- **Google Code Assist / Gemini CLI free quota:** These are tied to Google login sessions and are not accessible via API key — the non-authoritative reference doc correctly notes "Probably NOT suitable for LiteLLM integration"

**Warning signs:**
- Attempting to use OAuth tokens or cookie-based credentials with LiteLLM for these providers
- Expecting unlimited usage based on subscription when API has per-token billing

**Sources (HIGH confidence):**
- Non-authoritative reference doc's own "Subscription Reality Check" section correctly identifies this — the one section verified as accurate
- OpenAI and Google API documentation (standard industry knowledge, MEDIUM confidence from training data, LOW risk of being wrong)

**Phase to address:** v2 planning phase before any OpenAI/Gemini integration work begins.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Use `latest` Docker image tag for LiteLLM | No version management work | Supply chain attack exposure; uncontrolled breaking changes | Never — always pin |
| Trust the non-authoritative reference doc without verification | Faster initial setup | Architecture built on unverified claims (Claude Max passthrough being the prime example) | Never |
| Skip `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1` on non-Anthropic backends | Simpler config | Intermittent `"invalid beta flag"` failures as Claude Code adds new betas | Never for non-Anthropic backends |
| Expose `ANTHROPIC_API_KEY` in shell profile for convenience | One-time setup | Silently overrides subscription auth; billing surprise | Never on a Max subscription machine |
| Use `ollama_chat/<model>:cloud` with direct cloud API (instead of local daemon) | Looks like docs | 404 errors; daemon not running | Never — pick one architecture |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Anthropic via LiteLLM | Forwarding OAuth token expecting Max budget | Use Anthropic API key (per-token) OR bypass gateway for Claude models |
| LiteLLM Docker | `pip install litellm` or PyPI install | Use `ghcr.io/berriai/litellm:<pinned-version>` only |
| Ollama Cloud via LiteLLM | Using `/api/v1/` path | Use `/v1/` (OpenAI-compatible layer) |
| Ollama Cloud — model names | Using `:cloud` suffix with direct API | Omit `:cloud` for direct API; use it only when routing through local daemon |
| Claude Code env vars | Setting `ANTHROPIC_API_KEY` on same machine as Max subscription | Set API keys only inside LiteLLM container env; verify with `/status` |
| Gateway model discovery | Expecting non-`claude`/`anthropic` model names to appear in picker | Name all aliases with `claude-` prefix or use `ANTHROPIC_CUSTOM_MODEL_OPTION` |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Installing LiteLLM from PyPI without version pinning | Credential theft (API keys, SSH keys, cloud creds) via supply chain attack | Use official ghcr.io Docker image only; pin version |
| Storing API keys in `.env` committed to git | Credential exposure | Add `.env` to `.gitignore`; use Docker secrets or environment injection |
| Exposing LiteLLM on 0.0.0.0 (not localhost) | Gateway accessible from network, not just local | Bind to `127.0.0.1:4000` only; this is a local PoC |
| Using unverified Docker images | Supply chain risk | Verify cosign signature for LiteLLM >= 1.83.0 |

---

## "Looks Done But Isn't" Checklist

- [ ] **Claude Max routing:** Verify with `/status` in Claude Code that the auth method shown is what you intend (subscription or API key) — not just that requests succeed
- [ ] **Anthropic beta headers:** Confirm with a real Claude Code coding session (not curl) that tool use works correctly end-to-end
- [ ] **Ollama Cloud:** Confirm the model is actually running on cloud infrastructure, not falling back to local (check Ollama Cloud dashboard for inference activity)
- [ ] **Model aliases in picker:** Run `CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY=1` and verify expected aliases appear — absence means the filter rejected the names
- [ ] **LiteLLM version:** Confirm the running container is the pinned version, not a cached `latest`
- [ ] **Attribution header with caching:** If LiteLLM caching is enabled, verify `CLAUDE_CODE_ATTRIBUTION_HEADER=0` is set or cache hit rate is non-zero

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Claude Max OAuth used — account banned | HIGH | Contact Anthropic support; switch to API key authentication permanently |
| Compromised LiteLLM version installed | HIGH | Remove package; rotate all credentials (API keys, SSH keys, cloud creds) found in environment; deploy clean container from ghcr.io |
| Non-Anthropic backend rejecting beta headers | LOW | Set `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1`; upgrade LiteLLM to latest patched version |
| Wrong Ollama Cloud endpoint | LOW | Update `api_base` in config.yaml; restart container |
| Model names failing gateway discovery filter | LOW | Rename aliases with `claude-` prefix or switch to `ANTHROPIC_CUSTOM_MODEL_OPTION` |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Claude Max OAuth passthrough (ToS violation) | Phase 1 — Architecture decision | Architecture doc explicitly shows gateway bypass for Claude traffic OR uses API key provider |
| LiteLLM supply chain / version pinning | Phase 1 — Docker setup | `docker inspect` shows pinned version tag; cosign signature verified |
| Beta header forwarding | Phase 2 — Anthropic backend; Phase 3 — Ollama backend | Real Claude Code session with tool use succeeds on each backend |
| Model name filter rejects aliases | Phase 1 — Alias naming design | Run gateway discovery and confirm aliases appear in picker |
| Ollama Cloud endpoint / `:cloud` confusion | Phase 3 — Ollama backend | Successful API call to cloud model via LiteLLM; Ollama dashboard shows cloud inference |
| Attribution header cache breakage | Phase 2 — Initial integration | Set env var proactively; verify if caching is enabled |
| ANTHROPIC_API_KEY precedence / billing surprise | Phase 1 — Environment design | `/status` shows expected auth method; no unexpected API billing |
| Anthropic-specific params rejected by Ollama | Phase 3 — Ollama backend | Full Claude Code coding session (not curl) succeeds with Ollama backend |
| Subscription vs. API (deferred providers) | v2 planning — before OpenAI/Gemini work | Verify API key exists and has billing enabled before any config work |

---

## Sources

- [Claude Code Legal and compliance — official ToS on OAuth](https://code.claude.com/docs/en/legal-and-compliance)
- [Claude Code LLM gateway configuration — official gateway docs](https://code.claude.com/docs/en/llm-gateway)
- [Claude Code authentication — precedence order](https://code.claude.com/docs/en/authentication)
- [Claude Code model configuration — discovery and ANTHROPIC_CUSTOM_MODEL_OPTION](https://code.claude.com/docs/en/model-config)
- [LiteLLM — Using Claude Code Max Subscription](https://docs.litellm.ai/docs/tutorials/claude_code_max_subscription) (documents pattern; does not note April 2026 enforcement)
- [LiteLLM — Managing Anthropic Beta Headers](https://docs.litellm.ai/docs/tutorials/claude_code_beta_headers)
- [LiteLLM — Security Update March 2026](https://docs.litellm.ai/blog/security-update-march-2026)
- [LiteLLM — Beta headers incident report](https://docs.litellm.ai/blog/claude-code-beta-headers-incident)
- [GitHub BerriAI/litellm #24518 — supply chain compromise timeline](https://github.com/BerriAI/litellm/issues/24518)
- [GitHub BerriAI/litellm #22963 — output_config rejected by non-Anthropic backends](https://github.com/BerriAI/litellm/issues/22963)
- [GitHub anthropics/claude-code #28091 — OAuth disabled for third-party apps](https://github.com/anthropics/claude-code/issues/28091)
- [GitHub anthropics/claude-code #56990 — model name validation rejects non-Anthropic names](https://github.com/anthropics/claude-code/issues/56990)
- [The Register — Anthropic clarifies third-party ban](https://www.theregister.com/2026/02/20/anthropic_clarifies_ban_third_party_claude_access/)
- [rogs.me — CLIProxyAPI blocked April 4, 2026](https://rogs.me/2026/02/use-your-claude-max-subscription-as-an-api-with-cliproxyapi/)
- [Hacker News — Anthropic OAuth ban community discussion](https://news.ycombinator.com/item?id=47069299)
- [Ollama API authentication docs](https://docs.ollama.com/api/authentication)
- [Ollama OpenAI compatibility docs](https://docs.ollama.com/api/openai-compatibility)
- [Pi + Ollama Cloud API (April 2026 community setup)](https://fabiorehm.com/blog/2026/04/12/pi-ollama-cloud-api/)

---
*Pitfalls research for: Local Dockerized LiteLLM gateway (Claude Max + Ollama Cloud)*
*Researched: 2026-05-20*
