# Claude Code + LiteLLM Unified Gateway Setup

## Goal

Use Claude Code as the single coding interface while routing requests dynamically to:

- Claude Max (Opus / Sonnet / Haiku)
- OpenAI models
- Ollama Cloud models
- Gemini models
- Local Ollama models if desired

without changing environment variables every time.

---

# Recommended Architecture

```text
Claude Code
    ↓
LiteLLM Gateway (localhost:4000)
    ↓
Anthropic
OpenAI
Gemini
Ollama Cloud
Local Ollama
```

Claude Code only talks to LiteLLM.

LiteLLM handles:
- provider routing
- auth
- Anthropic API compatibility
- model swapping
- fallbacks

---

# Key Discovery

Claude Code expects the Anthropic Messages API.

This means:
- Ollama works because it exposes Anthropic-compatible endpoints
- LiteLLM works because it translates Anthropic requests/responses
- OpenAI/Gemini require a compatibility layer

---

# Best Practice: Use "claude-*" Virtual Models

Instead of exposing raw provider names directly:

BAD:

```text
gpt-5
gemini-2.5-pro
deepseek-r1
kimi-k2
```

Use stable semantic aliases:

```text
claude-opus
claude-sonnet
claude-haiku
```

Then swap providers underneath whenever needed.

Benefits:
- no env var changes
- Claude Code discovery works cleanly
- subagents behave properly
- easier fallback handling
- consistent workflows

---

# Example LiteLLM Config

```yaml
model_list:

  - model_name: claude-opus
    litellm_params:
      model: openai/gpt-5

  - model_name: claude-sonnet
    litellm_params:
      model: gemini/gemini-2.5-pro

  - model_name: claude-haiku
    litellm_params:
      model: ollama_chat/qwen3-coder:cloud
      api_base: http://localhost:11434

  - model_name: kimi-k2
    litellm_params:
      model: ollama_chat/kimi-k2.6:cloud
      api_base: http://localhost:11434

  - model_name: deepseek
    litellm_params:
      model: ollama_chat/deepseek-r1:cloud
      api_base: http://localhost:11434
```

---

# Claude Code Environment Variables

```bash
export ANTHROPIC_BASE_URL=http://localhost:4000
export CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY=1
```

Optional:

```bash
export ANTHROPIC_AUTH_TOKEN=your-litellm-key
```

---

# Running Models

Daily usage:

```bash
claude --model claude-sonnet
```

Heavy reasoning:

```bash
claude --model claude-opus
```

Cheap utility work:

```bash
claude --model claude-haiku
```

Direct provider-specific usage:

```bash
claude --model kimi-k2
claude --model deepseek
```

---

# Ollama Cloud Notes

Two possible architectures exist.

## Option A — Recommended

```text
Claude Code
→ LiteLLM
→ local Ollama daemon
→ Ollama Cloud
```

Advantages:
- officially documented
- stable
- Anthropic compatibility already handled
- easiest setup

This requires local Ollama running.

Example:

```yaml
model: ollama_chat/qwen3-coder:cloud
api_base: http://localhost:11434
```

---

## Option B — Direct Ollama Cloud API

Possible in theory:

```text
LiteLLM
→ https://ollama.com/api/chat
```

But:
- less battle-tested
- some LiteLLM issues around auth/header handling exist
- recommended only after testing

---

# Subscription Reality Check

## Claude Max 5x

Works well with Claude Code.

LiteLLM can route Claude Code traffic while preserving Claude workflows.

---

## OpenAI Subscription

IMPORTANT:

ChatGPT subscriptions are NOT OpenAI API credits.

You still need:
- OpenAI API key
- API billing enabled

---

## Ollama Subscription

Good fit for this architecture.

Provides:
- DeepSeek
- Kimi
- Qwen
- others

Can be routed through:
- local Ollama daemon
- potentially direct cloud API

---

## Google / Gemini

Gemini API works well with LiteLLM.

Requires:
- GEMINI_API_KEY

---

## Google Code Assist / Free Gemini CLI Quota

Probably NOT suitable for LiteLLM integration.

Those quotas are tied to:
- Google login
- Gemini CLI
- Code Assist tooling

not normal API key usage.

---

# Recommended Real-World Mapping

## Suggested Roles

```text
claude-opus
    → GPT-5 OR Claude Opus

claude-sonnet
    → Gemini 2.5 Pro OR Claude Sonnet

claude-haiku
    → Qwen / DeepSeek / Kimi
```

---

# Suggested Workflow

Keep Claude Code fixed forever:

```bash
export ANTHROPIC_BASE_URL=http://localhost:4000
```

Never change provider env vars again.

Switch models only with:

```bash
claude --model claude-sonnet
claude --model claude-opus
claude --model kimi-k2
```

---

# Final Recommendation

Best setup today:

```text
Claude Code
→ LiteLLM
→ everything else
```

with:
- semantic "claude-*" aliases
- provider-specific aliases
- local Ollama as the compatibility bridge for Ollama Cloud
- API-key-based providers behind LiteLLM

This gives:
- one stable endpoint
- easy model swapping
- fallback flexibility
- reduced vendor lock-in
- compatibility with Claude Code tooling
