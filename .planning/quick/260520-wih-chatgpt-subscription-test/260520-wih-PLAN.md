---
phase: quick-260520-wih
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - config.yaml
  - compose.yaml
  - .gitignore
# autonomous=false because: OAuth device sign-in + the agentic acceptance session are human-interactive
autonomous: false
requirements: [PROV-01]   # Feasibility spike for the DEFERRED v2 item PROV-01 (OpenAI provider) — not adoption
user_setup:
  - service: chatgpt
    why: "ChatGPT Plus/Pro subscription reused via LiteLLM's chatgpt/ provider (OAuth device-code 'Sign in with ChatGPT'); no API key, no per-token billing"
    dashboard_config:
      - task: "Complete the OAuth device-code sign-in (open the verification URL LiteLLM emits, sign in with the ChatGPT account, enter the code)"
        location: "Browser — URL surfaced from LiteLLM during Task 2"

must_haves:
  truths:
    - "Gateway loads a new `chatgpt-test` alias and the container starts healthy (no model-load crash)"
    - "The ChatGPT OAuth device-code flow can be triggered and completed by the user; the cached token survives a `docker compose restart`"
    - "A raw curl to /v1/messages for chatgpt-test with a tool definition returns 200 with an Anthropic-shaped body that decodes to the chatgpt/openai provider (the known block-array 'concatenate list to list' crash does NOT occur)"
    - "A real `claude --model chatgpt-test` session performs a file edit + a bash call + at least one multi-turn tool loop end-to-end through the gateway"
    - "A clear PASS/FAIL verdict is recorded with specific failure modes; config.yaml/compose.yaml/.gitignore and the token dir are cleanly reverted"
  artifacts:
    - path: "config.yaml"
      provides: "Temporary chatgpt-test model entry (chatgpt/<model>, model_info.mode=responses), NOT in forward_client_headers_to_llm_api"
      contains: "model_name: chatgpt-test"
    - path: "compose.yaml"
      provides: "Writable host-mounted, gitignored token dir + CHATGPT_TOKEN_DIR env so the OAuth token persists across recreate"
      contains: ".chatgpt-auth"
    - path: ".gitignore"
      provides: "Ignore rule for the OAuth token dir so the cached credential is never committed"
      contains: ".chatgpt-auth"
  key_links:
    - from: "config.yaml chatgpt-test"
      to: "ChatGPT subscription via chatgpt/ provider"
      via: "litellm_params.model: chatgpt/<model> + model_info.mode: responses"
      pattern: "chatgpt/"
    - from: "Claude Code /v1/messages (Anthropic shape, content block-arrays + tools)"
      to: "OpenAI /responses"
      via: "LiteLLM anthropic_unified messages_to_responses mapping"
      pattern: "v1/messages"
---

<objective>
Feasibility spike: expose a ChatGPT-subscription GPT model on the already-running LiteLLM gateway under a NEW, temporary `chatgpt-test` alias and prove (or disprove) that it drives Claude Code **agentically** — Anthropic `/v1/messages` (with content block-arrays + tool definitions) round-tripping to OpenAI `/responses` and back, including multi-turn tool calls.

Purpose: Resolve the deferred v2 item PROV-01 (OpenAI provider) empirically before deciding whether to adopt it. PROJECT.md "Out of Scope" notes consumer ChatGPT subscriptions "are not API access; wiring them likely needs paid API keys — to be investigated later." LiteLLM's first-party `chatgpt/` provider (verified this session against docs.litellm.ai/docs/providers/chatgpt) reuses the subscription via OAuth — this spike tests whether that holds for Claude Code's agentic workload. This is a DISPOSABLE test, not a permanent feature.

Output: A PASS/FAIL verdict on agentic feasibility with documented failure modes, after which the gateway is reverted to its exact v1.0 state (3 aliases, no chatgpt-test, no token dir).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md

EXECUTION REALITY (read before starting — this plan is NOT worktree-isolated):
- The live container `lite-llm-bridge-litellm-1` reads the MAIN working tree's `config.yaml` via the `:ro` bind mount. A worktree copy would not be seen by the running container, so the orchestrator (not a worktree subagent) executes this in the main tree.
- Two steps are human-interactive and MUST pause: the OAuth device sign-in (Task 2) and the agentic acceptance session (Task 3). Surface the exact data/commands the user needs and wait.
- Mirror the rigor of the verified Ollama path (01-03-SUMMARY): prove routing autonomously via a decoded response id from raw curl, THEN prove agentic tool-use via a real human-driven `claude` session — a hello-world chat is NOT sufficient.
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/STATE.md
@./CLAUDE.md
@./config.yaml
@./compose.yaml
@./.gitignore
@.planning/phases/01-gateway-feasibility-spike/01-03-SUMMARY.md

<verified_facts>
<!-- CONFIRMED this session — do not re-derive or contradict; the executor MAY re-verify. -->
- Container: `lite-llm-bridge-litellm-1`, image `ghcr.io/berriai/litellm:main-stable` = LiteLLM **1.85.0** (built 2026-05-17), on `localhost:4000`, up and healthy.
- compose.yaml mounts `./config.yaml:/app/config.yaml:ro`, `env_file: .env`, command `--config /app/config.yaml --port 4000`, `restart: unless-stopped`. NO named/persistent volume — files written inside the container are on the ephemeral container FS and are LOST on `docker compose down`/recreate (a plain `restart` keeps them, recreate does not). This is WHY a host-mounted token dir is required.
- config.yaml: `claude-opus`->anthropic/claude-opus-4-7, `claude-sonnet`->anthropic/claude-sonnet-4-6 (Max via OAuth forwarding), `claude-haiku`->openai/deepseek-v4-pro:cloud (Ollama, api_base https://ollama.com/v1, api_key os.environ/OLLAMA_API_KEY). `general_settings.master_key: os.environ/LITELLM_MASTER_KEY`. `model_group_settings.forward_client_headers_to_llm_api` scoped to ONLY [claude-opus, claude-sonnet]. `litellm_settings.drop_params: true` is GLOBAL.
- .gitignore currently ignores ONLY `.env` and `.DS_Store`. .env holds LITELLM_MASTER_KEY (sk-...) and OLLAMA_API_KEY.
- Client->gateway auth: `ANTHROPIC_BASE_URL=http://localhost:4000` + `ANTHROPIC_AUTH_TOKEN=<LITELLM_MASTER_KEY>`.
</verified_facts>

<verified_research>
<!-- CONFIRMED from first-party LiteLLM docs this session — treat as fact. -->
- LiteLLM ships an OFFICIAL `chatgpt/` provider (docs.litellm.ai/docs/providers/chatgpt) reusing a ChatGPT Plus/Pro/Business subscription. Config entry shape (doc-verified): `model_name`, `litellm_params.model: chatgpt/<model>`, and `model_info.mode: responses`. It works with the PROXY (`litellm --config config.yaml`), not SDK-only.
- Auth = OAuth device-code "Sign in with ChatGPT": LiteLLM "prints a device code and verification URL"; user opens the URL, signs in, enters the code; token caches locally to `auth.json`. Env knobs: `CHATGPT_TOKEN_DIR` (token directory), `CHATGPT_AUTH_FILE` (default `auth.json`). No API key, no per-token billing.
- Anthropic<->OpenAI translation is documented both directions incl. tools/tool_choice (docs.litellm.ai/docs/anthropic_unified/messages_to_responses_mapping) — this is the mechanism Claude Code rides.
- Doc-listed chatgpt/ models: gpt-5.4, gpt-5.4-pro, gpt-5.3-codex, gpt-5.3-codex-spark, gpt-5.3-instant, gpt-5.3-chat-latest. The ChatGPT backend REJECTS max_tokens/max_output_tokens/metadata; LiteLLM strips them (`drop_params: true` already on, so EXPECTED, not an error).
</verified_research>

<known_risks>
1. **Block-array system-message crash (UNCONFIRMED on 1.85.0):** Claude Code sends content as block arrays; an older LiteLLM chatgpt/ system-message converter crashed with `can only concatenate list (not str) to list` (fix pending at v1.83.0; we run 1.85.0 so it MAY be fixed). The curl smoke test in Task 2 MUST probe for it (send a system field + content block-arrays + a tool). If it occurs, the circulating workaround is `supports_system_message: false` on the model — this reroutes the system prompt into a user message, a REAL quality compromise; flag it as a finding, do not treat it as free.
2. **Agentic/tool-call parity is NOT guaranteed by contract** — only a real agentic session (file edit + bash + multi-turn tool loop) proves it, exactly like the deepseek 01-03 gate. A text round-trip is insufficient.
3. **Token loss:** mount is `:ro` and there is no volume — without a writable host-mounted token dir the OAuth token dies on recreate. The dir MUST be gitignored.
</known_risks>

<empirical_unknowns>
<!-- Resolve during execution; do NOT fabricate. The user has ChatGPT Plus and is at the keyboard for interactive parts. -->
- **OAuth device-flow trigger surface on LiteLLM 1.85.0:** the doc says it triggers on first model request and "prints a device code and verification URL", but does not pin whether that print lands in `docker logs lite-llm-bridge-litellm-1` (non-TTY proxy stdout) OR requires an interactive TTY (`docker exec -it ... <login command>`). Plan: trigger the path, observe where the code appears; if nothing appears in logs, fall back to an interactive `docker exec -it` session. Source: docs.litellm.ai/docs/providers/chatgpt (trigger surface unconfirmed there).
- **Model availability on a Plus plan:** `gpt-5.3-codex` is the recommended primary (Codex-tuned -> best agentic shot for a coding agent). `gpt-5.4` is the comparison/fallback. `gpt-5.4-pro` likely needs Pro. Verify callability empirically; swap the alias target if the primary 4xx/403s on Plus.
</empirical_unknowns>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Wire temporary chatgpt-test alias + persistent gitignored OAuth token mount</name>
  <files>config.yaml, compose.yaml, .gitignore</files>
  <action>
Stand up the new alias and a durable, never-committed home for its OAuth token, then reload the gateway. Make ONLY additive edits — do not touch the existing claude-opus/claude-sonnet/claude-haiku entries, general_settings.master_key, the existing forward_client_headers_to_llm_api list, or drop_params.

1. config.yaml — append a new model_list entry (per PROV-01 spike):
   - model_name: chatgpt-test
   - litellm_params.model: chatgpt/gpt-5.3-codex  (primary: Codex-tuned for the best agentic result; gpt-5.4 is the documented fallback if Plus rejects codex — see empirical_unknowns)
   - model_info.mode: responses  (doc-required for the chatgpt/ Responses path)
   - NO api_key line (chatgpt/ uses its own OAuth-cached token, not OLLAMA_API_KEY or a forwarded bearer).
   - Add a comment marking it TEMPORARY/spike-only (PROV-01) so it is obviously disposable.
   Do NOT add chatgpt-test to model_group_settings.forward_client_headers_to_llm_api — forwarding Claude Code's ANTHROPIC OAuth bearer to OpenAI is wrong (per the spike constraints); the chatgpt/ provider authenticates with its own cached token.

2. compose.yaml — give the OAuth token a writable host home that survives recreate (the config mount is :ro and there is no volume):
   - Add a bind mount ./.chatgpt-auth:/app/.chatgpt-auth (read-write; do NOT add :ro).
   - Add an environment: entry CHATGPT_TOKEN_DIR=/app/.chatgpt-auth so LiteLLM writes auth.json there (CHATGPT_AUTH_FILE keeps its default auth.json).
   - Leave the existing env_file: .env, the :ro config mount, ports, command, and restart policy unchanged.

3. .gitignore — add an ignore rule for the token dir so the cached credential is NEVER committed (current .gitignore only covers .env and .DS_Store):
   - Add .chatgpt-auth/ (directory form).

4. Create the host dir and reload so the new mount + env + model take effect. Because compose.yaml changed (new mount/env), a plain restart is insufficient — recreate the container:
   - mkdir -p /home/jim/workspace/lite-llm-bridge/.chatgpt-auth
   - docker compose -f /home/jim/workspace/lite-llm-bridge/compose.yaml up -d   (recreates with the new mount/env)
   - Confirm the container is healthy and chatgpt-test is loaded WITHOUT a crash before finishing (the block-array crash from known_risks #1 is a load/runtime concern — a clean model-load is the first signal it is absent on 1.85.0).
  </action>
  <verify>
    <automated>cd /home/jim/workspace/lite-llm-bridge && grep -q 'chatgpt-test' config.yaml && grep -q 'mode: responses' config.yaml && grep -q 'chatgpt-auth' compose.yaml && grep -q 'CHATGPT_TOKEN_DIR' compose.yaml && grep -qE '^.chatgpt-auth/?' .gitignore && git check-ignore -q .chatgpt-auth/ && ! git check-ignore -q config.yaml && docker ps --filter name=lite-llm-bridge-litellm-1 --filter health=healthy --format '{{.Names}}' | grep -q lite-llm-bridge-litellm-1 && curl -sS -o /dev/null -w '%{http_code}' http://localhost:4000/v1/models -H "Authorization: Bearer $LITELLM_MASTER_KEY" | grep -q 200</automated>
  </verify>
  <done>
config.yaml has a chatgpt-test entry (chatgpt/<model> + model_info.mode: responses), absent from forward_client_headers_to_llm_api; compose.yaml has the read-write ./.chatgpt-auth mount + CHATGPT_TOKEN_DIR env; .gitignore ignores .chatgpt-auth/ (git check-ignore confirms the dir is ignored AND config.yaml is NOT); container is healthy after recreate and /v1/models returns 200. The three existing aliases are byte-for-byte unchanged.
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 2: Trigger ChatGPT OAuth sign-in + autonomous curl routing/crash smoke test + token persistence</name>
  <action>Surface the OAuth device URL+code to the user and wait for sign-in (human-only); then autonomously run the curl smoke test (system + content block-array + tool) to prove chatgpt/ routing and the absence of the block-array crash, and confirm the cached token survives a restart. Full steps in what-built below.</action>
  <what-built>
Task 1 wired the chatgpt-test alias and a persistent gitignored OAuth token dir, and recreated the healthy container. This task triggers the one-time ChatGPT OAuth device sign-in (human-only — only the account owner can sign in), then AUTONOMOUSLY proves routing + the absence of the block-array crash via raw curl with a tool definition, and confirms the token persists.

The executor performs the autonomous parts (curl smoke test, log decode, restart-persistence check) and surfaces ONLY the OAuth step to the user. Execute in this order:

A. TRIGGER + SURFACE THE DEVICE FLOW (executor runs, then PAUSES for the user):
   - In one shell, start tailing logs so the device code is captured if it prints to stdout:
     docker logs -f lite-llm-bridge-litellm-1   (or: docker compose -f /home/jim/workspace/lite-llm-bridge/compose.yaml logs -f litellm)
   - Fire a first request to force the chatgpt/ path to initialize auth:
     curl -sS http://localhost:4000/v1/messages -H "Authorization: Bearer $LITELLM_MASTER_KEY" -H "content-type: application/json" -d '{"model":"chatgpt-test","max_tokens":64,"messages":[{"role":"user","content":[{"type":"text","text":"reply with the single word: ready"}]}]}'
   - OBSERVE where the device code + verification URL appear (empirical_unknowns):
     - If they appear in the docker logs -> surface that URL + code to the user verbatim.
     - If NOTHING appears in logs (LiteLLM may need a TTY), fall back to an interactive login:
       docker exec -it lite-llm-bridge-litellm-1 sh   then run the documented chatgpt login per docs.litellm.ai/docs/providers/chatgpt, capturing the URL+code. Surface it.
   - Tell the user exactly: "Open <URL>, sign in with your ChatGPT account, enter code <CODE>." Then WAIT for them to confirm sign-in is complete.
   - NOTE the actual trigger surface (logs vs TTY) for the SUMMARY — this is a key empirical finding.

B. AUTONOMOUS CURL SMOKE TEST (executor runs after sign-in confirmed — this is the routing + crash probe, mirroring 01-03 OLL-01):
   - Send an Anthropic-shaped request that exercises the risky surfaces: a system field, content as a block-array, AND a tool definition + tool_choice, so the block-array system converter (known_risks #1) is hit:
     curl -sS http://localhost:4000/v1/messages -H "Authorization: Bearer $LITELLM_MASTER_KEY" -H "content-type: application/json" -d '{"model":"chatgpt-test","max_tokens":256,"system":[{"type":"text","text":"You are a terse assistant."}],"messages":[{"role":"user","content":[{"type":"text","text":"What is 2+2? Then call the get_time tool."}]}],"tools":[{"name":"get_time","description":"Get current time","input_schema":{"type":"object","properties":{}}}],"tool_choice":{"type":"auto"}}'
   - PASS signals: HTTP 200; body is Anthropic-shaped (top-level type:"message", role:"assistant", a content array); ideally a content block of type "tool_use" for get_time (proves tool translation), or at minimum coherent text. Decode the response id / check logs for the provider — confirm it routes to the chatgpt/openai Responses path (analogous to 01-03 decoding custom_llm_provider).
   - FAIL signals to capture verbatim: any 500 with "can only concatenate list (not str) to list" (the block-array crash — record it and note the supports_system_message:false workaround as a quality-compromise finding, do NOT silently apply it); a 4xx/403 indicating gpt-5.3-codex is not callable on Plus (record it; the documented fallback is to retry with chatgpt/gpt-5.4 — re-edit config.yaml model + recreate, then re-run); any auth error meaning the OAuth token did not cache.
   - Check gateway logs during the call for the EXPECTED (non-error) stripping of max_tokens/metadata (drop_params) — note it so it is not mistaken for a failure.

C. TOKEN-PERSISTENCE CHECK (executor runs autonomously):
   - Confirm a token file now exists on the host: ls -la /home/jim/workspace/lite-llm-bridge/.chatgpt-auth (expect auth.json).
   - docker compose -f /home/jim/workspace/lite-llm-bridge/compose.yaml restart litellm   then re-run the curl from (B). It must return 200 WITHOUT prompting for OAuth again — proving the host-mounted token survives a restart (and, by virtue of the bind mount, a recreate).
  </what-built>
  <how-to-verify>
1. When the executor surfaces the device URL + code, open the URL in your browser, sign in with your ChatGPT account, and enter the code. Confirm to the executor when done.
2. Confirm the executor reports: smoke-test curl returned 200 with an Anthropic-shaped body (and, ideally, a tool_use block for get_time); the response routed to the chatgpt/ provider; and NO "concatenate list to list" crash occurred.
3. Confirm the executor reports the token persisted: auth.json exists under ./.chatgpt-auth and the post-restart curl returned 200 without re-prompting for OAuth.
4. If the executor reports gpt-5.3-codex was rejected on Plus and it fell back to gpt-5.4, acknowledge the swap.
  </how-to-verify>
  <resume-signal>Type "approved" once you have completed the ChatGPT sign-in and the executor has reported a 200 smoke test + persisted token. Or describe the failure mode observed (crash text, 403, auth failure) so it is recorded in the verdict.</resume-signal>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 3: User-driven agentic acceptance session, record PASS/FAIL verdict, and roll back the spike</name>
  <action>Hand off to a real `claude --model chatgpt-test` session (user-driven) that exercises a Write + bash multi-turn tool loop; record the PASS/FAIL verdict with the captured specifics; then fully roll back config.yaml/compose.yaml/.gitignore and remove the token dir + probe file. Full steps in what-built below.</action>
  <what-built>
Routing and contract-level tool translation were proven by curl in Task 2. This FINAL gate proves true agentic operation in a real Claude Code session (the only proof that counts, per known_risks #2 and the 01-03 precedent), records the PASS/FAIL verdict, then ROLLS BACK the disposable spike.

This is user-driven in the user's OWN Claude Code (the executor must not drive `~/.claude` — mirror D-08 from 01-03). The executor prepares, hands off, records the result, and reverts.

A. AGENTIC ACCEPTANCE SESSION (user runs in their own terminal):
   The user starts a Claude Code session pointed at the gateway and selects the spike alias:
     ANTHROPIC_BASE_URL=http://localhost:4000  ANTHROPIC_AUTH_TOKEN=<LITELLM_MASTER_KEY>  claude --model chatgpt-test
   (Do NOT set ANTHROPIC_API_KEY — it bypasses the gateway, per CLAUDE.md.)
   In that session the user gives a task that forces multi-turn agentic tool use, equivalent to the 01-03 OLL-02 gate:
     "Create a file chatgpt-test-probe.txt containing 'hello from chatgpt', then read it back with bash and tell me its contents."
   This exercises: Write tool (tool_use), a bash call (second tool), and a multi-turn tool_use -> tool_result loop — all round-tripping Anthropic block-arrays <-> OpenAI Responses.
   While it runs, the executor watches the gateway logs for the repeated tool-call loop returning 200s (as 01-03 did: tool_calls loop -> repeated 200 OK).

B. RECORD THE VERDICT (executor writes findings into the SUMMARY — the definition of done):
   - PASS if: the file was created AND read back correctly via bash, with at least one completed multi-turn tool loop, and gateway logs show 200s on the tool-call turns.
   - FAIL if: tools never fire, tool_result is dropped/garbled, the session errors, or it falls back to plain chat with no tool use.
   - In ALL cases record, with specifics: the model actually used (gpt-5.3-codex or gpt-5.4 fallback), the OAuth trigger surface found in Task 2 (logs vs TTY), whether the block-array crash occurred, whether supports_system_message:false was needed (and that it is a quality compromise if so), any 403/availability limits on Plus, and the EXPECTED drop_params stripping. End with an explicit one-line verdict on PROV-01 agentic feasibility and a recommendation (adopt / adopt-with-caveats / do-not-adopt).

C. ROLLBACK — restore the exact v1.0 state (this spike is disposable):
   - Revert config.yaml: remove the chatgpt-test entry (restore to the 3-alias file). Use: git checkout -- config.yaml  (it was committed unchanged before this spike).
   - Revert compose.yaml: remove the ./.chatgpt-auth mount + CHATGPT_TOKEN_DIR env. Use: git checkout -- compose.yaml
   - Revert .gitignore: remove the .chatgpt-auth/ line. Use: git checkout -- .gitignore
   - Remove the token dir + cached credential from the host: rm -rf /home/jim/workspace/lite-llm-bridge/.chatgpt-auth
   - Remove the probe artifact if present: rm -f /home/jim/workspace/lite-llm-bridge/chatgpt-test-probe.txt
   - Recreate the container so it returns to the pre-spike config: docker compose -f /home/jim/workspace/lite-llm-bridge/compose.yaml up -d
   - Confirm restoration: config.yaml contains exactly claude-opus/claude-sonnet/claude-haiku and no chatgpt-test; git status is clean for these three files; .chatgpt-auth no longer exists; container is healthy.
  </what-built>
  <how-to-verify>
1. In your own terminal run: ANTHROPIC_BASE_URL=http://localhost:4000 ANTHROPIC_AUTH_TOKEN=<your LITELLM_MASTER_KEY> claude --model chatgpt-test  (do NOT set ANTHROPIC_API_KEY).
2. Ask it: "Create a file chatgpt-test-probe.txt containing 'hello from chatgpt', then read it back with bash and tell me its contents." Confirm whether it actually used the Write + bash tools and reported the correct contents (PASS) or failed to use tools / errored (FAIL).
3. Tell the executor the outcome (PASS or the specific failure) so it records the verdict.
4. Confirm the executor reports rollback complete: config.yaml/compose.yaml/.gitignore reverted (git status clean for them), .chatgpt-auth removed, container healthy on the original 3-alias config.
  </how-to-verify>
  <resume-signal>Report the agentic session outcome (PASS or the specific failure mode), then type "rollback done" once the executor confirms config/compose/.gitignore are reverted and the token dir is removed.</resume-signal>
</task>

</tasks>

<verification>
- Container healthy throughout; /v1/models returns 200 with the master key.
- Task 2: curl with system + content block-array + tool returns 200 Anthropic-shaped, routes to the chatgpt/ provider, no "concatenate list to list" crash; token (auth.json) present under ./.chatgpt-auth and survives a restart.
- Task 3: a real `claude --model chatgpt-test` session completes a Write + bash multi-turn tool loop (gateway logs show 200s on tool turns) -> agentic PASS/FAIL recorded.
- Secret hygiene: git check-ignore confirms .chatgpt-auth/ is ignored and config.yaml is NOT; no token or OAuth credential is ever staged/committed.
- Rollback: config.yaml/compose.yaml/.gitignore restored to pre-spike (git status clean for them); .chatgpt-auth and the probe file removed; container back on the original 3-alias config.
</verification>

<success_criteria>
A documented PASS/FAIL verdict on whether a ChatGPT-subscription GPT model drives Claude Code AGENTICALLY through the gateway (Anthropic block-arrays + tools <-> OpenAI Responses, multi-turn), with these specifics captured: model used (gpt-5.3-codex or gpt-5.4 fallback), OAuth device-flow trigger surface (logs vs TTY), block-array-crash presence/absence, whether supports_system_message:false was required (flagged as a quality compromise), any Plus-tier availability limits, and a one-line PROV-01 recommendation. The gateway is fully reverted to its v1.0 3-alias state with no committed secrets and no leftover token dir.
</success_criteria>

<output>
Create `.planning/quick/260520-wih-chatgpt-subscription-test/260520-wih-SUMMARY.md` when done, containing the PASS/FAIL verdict, the captured specifics above, and confirmation of clean rollback.
</output>
