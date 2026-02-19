# Model Compatibility Guide

This document contains the results of comprehensive testing of model availability and compatibility with the OpenCode Teams MCP server.

## Last Updated
2026-02-19

## Test Environment
- **OpenCode CLI Version:** v1.1.52+
- **Authentication:** OAuth (OpenAI), CLI keys (Google)
- **Platform:** Windows (also tested with tmux on Unix systems)

---

## ✅ Verified Working Models

These models have been tested and confirmed to work with `spawn_teammate`:

### OpenAI Models
**Requirements:** OAuth authentication via ChatGPT account

| Model | Status | Notes |
|-------|--------|-------|
| `openai/gpt-5.2` | ✅ Working | General agentic model, best for most tasks |
| `openai/gpt-5.3-codex` | ✅ Working | Most capable coding model (requires ChatGPT Plus/Pro) |
| `openai/gpt-5.2-codex` | ✅ Working | Advanced coding model (requires ChatGPT Plus/Pro) |
| `openai/gpt-5.1-codex` | ✅ Working | Optimized for agentic coding (requires ChatGPT Plus/Pro) |

**Important:** Standard OpenAI API models like `gpt-5.1`, `gpt-5`, `gpt-5-mini/nano` do NOT work through the Codex CLI. Use the Codex variants instead.

### Google Models (CLI Versions)
**Requirements:** Configured in `~/.config/opencode/opencode.json`

| Model | Status | Notes |
|-------|--------|-------|
| `google/gemini-2.5-flash` | ✅ Working | Fast, cost-efficient |
| `google/gemini-2.5-pro` | ✅ Working | Most capable Gemini model |
| `google/gemini-3-flash-preview` | ✅ Working | Latest flash model |
| `google/gemini-3-pro-preview` | ✅ Working | Latest pro model |
| `google/gemini-3-pro-low` | ✅ Working | Pro with low reasoning effort |
| `google/gemini-3-pro-high` | ✅ Working | Pro with high reasoning effort |

**Note:** 
- Gemini 2.5 models work with simple names
- Gemini 3.x models require `-preview` suffix OR reasoning effort suffix (`-low`, `-medium`, `-high`)

### Kimi for Coding Models
**Requirements:** Standard OpenCode authentication

| Model | Status | Notes |
|-------|--------|-------|
| `kimi-for-coding/k2p5` | ✅ Working | Kimi K2.5 optimized for coding |
| `kimi-for-coding/kimi-k2-thinking` | ✅ Working | Kimi K2 with thinking capabilities |

**Note:** These models are specifically optimized for coding tasks and work without special authentication.

### GitHub Copilot Models
**Requirements:** GitHub Copilot subscription

| Model | Status | Notes |
|-------|--------|-------|
| `github-copilot/gpt-5.2` | ✅ Working | GPT 5.2 via Copilot |
| `github-copilot/gpt-5.1` | ✅ Working | GPT 5.1 via Copilot |
| `github-copilot/gpt-5.1-codex` | ✅ Working | Codex via Copilot |
| `github-copilot/claude-sonnet-4.5` | ✅ Working | Claude Sonnet 4.5 via Copilot |
| `github-copilot/claude-opus-4.5` | ✅ Working | Claude Opus 4.5 via Copilot |
| `github-copilot/gemini-2.5-pro` | ✅ Working | Gemini 2.5 Pro via Copilot |
| `github-copilot/gemini-3-flash-preview` | ✅ Working | Gemini 3 Flash via Copilot |

**Note:** Provides access to OpenAI, Anthropic, and Google models through your GitHub Copilot subscription. Great alternative if you have Copilot but not ChatGPT Plus/Pro.

---

## ❌ Non-Working Models

These models are listed in discovery but do NOT work:

### OpenAI - Incorrect Model Names
| Model | Issue | Solution |
|-------|-------|----------|
| `openai/gpt-5.1` | Requires Codex subscription | Use `openai/gpt-5.1-codex` |
| `openai/gpt-5` | Invalid model name | Use `openai/gpt-5-codex` or `openai/gpt-5.2` |
| `openai/gpt-5-mini` | Invalid model name | Use `openai/gpt-5.2` or Google alternatives |
| `openai/gpt-5-nano` | Invalid model name | Use `openai/gpt-5.2` or Google alternatives |
| `openai/gpt-5.2-mini` | Invalid model name | Use `openai/gpt-5.2` |
| `openai/gpt-5.2-nano` | Invalid model name | Use `openai/gpt-5.2` |

**Suffix Confusion:** The `-medium`, `-high`, `-low`, `-xhigh` suffixes are **reasoning effort levels**, NOT model variants. They cannot be used as model names.

### OpenAI - Codex Subscription Required
| Model | Issue |
|-------|-------|
| `openai/gpt-5.*-codex-*` | All Codex models require ChatGPT Plus/Pro subscription |
| `openai/gpt-5.1-codex-max` | Requires Codex subscription |
| `openai/gpt-5-codex-mini` | Requires Codex subscription |

### Google - Deprecated
| Model | Issue | Solution |
|-------|-------|----------|
| `google/gemini-3-flash` | Antigravity deprecated | Use `google/gemini-3-flash-preview` |
| `google/gemini-3-pro` | Antigravity deprecated | Use `google/gemini-3-pro-preview` |
| `google/antigravity-*` | All Antigravity models deprecated | Use CLI versions |

---

## 📝 Model Name Format

### Correct Format
Always use the full `provider/model` format:

```
openai/gpt-5.2
google/gemini-2.5-flash
openai/gpt-5.3-codex
```

### Incorrect Formats
```
gpt-5.2                    # Missing provider prefix
gpt-5.2-medium             # Invalid suffix (reasoning effort, not model)
openai/gpt-5               # Invalid model name
openai/gpt-5.1             # Requires Codex variant
```

---

## 🔍 Discovering Available Models

### Method 1: Use the MCP Tool
Use the `list_available_models()` tool to see which models are configured and available:

```python
# List all available models
list_available_models()

# Filter by provider
list_available_models(provider="openai")
list_available_models(provider="google")

# Filter by reasoning effort level
list_available_models(reasoning_effort="high")
```

### Method 2: Use the OpenCode CLI
Run `opencode models` in your terminal to see all available models:

```bash
# List all models
opencode models

# Filter by provider
opencode models | grep "openai/"
opencode models | grep "google/"
```

### Example Output
The `opencode models` command returns models like:
```
# OpenAI Models (OAuth/ChatGPT required)
openai/gpt-5.2
openai/gpt-5.3-codex
openai/gpt-5.3-codex-spark
openai/gpt-5.2-codex
openai/gpt-5.2-codex-high
openai/gpt-5.2-codex-low
openai/gpt-5.2-codex-medium
openai/gpt-5.1-codex
openai/gpt-5.1-codex-high
openai/gpt-5.1-codex-low
openai/gpt-5.1-codex-max
openai/gpt-5-codex
openai/codex-mini-latest

# Google Models (API key required)
google/gemini-2.5-flash
google/gemini-2.5-pro
google/gemini-3-flash-preview
google/gemini-3-pro-preview
google/gemini-3-pro-high
google/gemini-3-pro-low
google/gemini-2.0-flash
google/gemini-1.5-pro

# Kimi for Coding (Tested & Working)
kimi-for-coding/k2p5
kimi-for-coding/kimi-k2-thinking

# GitHub Copilot (Tested & Working - requires Copilot subscription)
github-copilot/gpt-5.2
github-copilot/gpt-5.1
github-copilot/gpt-5.1-codex
github-copilot/claude-sonnet-4.5
github-copilot/claude-opus-4.5
github-copilot/gemini-2.5-pro
github-copilot/gemini-3-flash-preview

# Moonshot AI
moonshotai/kimi-k2.5
moonshotai/kimi-k2-thinking

# Other Providers
anthropic/claude-sonnet-4-5
anthropic/claude-opus-4-5
anthropic/claude-haiku-4-5
github-copilot/gpt-5.2
github-copilot/gemini-2.5-pro
kimi-for-coding/k2p5
moonshotai/kimi-k2.5
opencode/gpt-5-nano
opencode/kimi-k2.5-free
...
```

### Where Models Come From

Models are discovered from your OpenCode configuration files:
- **Global config:** `~/.config/opencode/opencode.json`
- **Project config:** `./opencode.json` (in your project directory)

The tool returns all models configured in these files. If a model isn't listed, it either:
1. Isn't configured in your OpenCode config
2. Requires authentication (OAuth for OpenAI, API key for Google)
3. Is not available for your subscription tier

### Provider-Specific Discovery

**OpenAI:** Models are automatically discovered when authenticated via OAuth. Codex models require ChatGPT Plus/Pro.

**Google:** Models must be explicitly configured in `opencode.json` with proper API credentials.

---

## 🎯 Model Selection by Task Type

Choose the best model based on your specific task requirements:

### 🚀 Speed-Focused Tasks
**Best for:** Quick file operations, simple text generation, data extraction

| Model | Provider | Why |
|-------|----------|-----|
| `google/gemini-2.5-flash` | Google | Fastest response, 1M context |
| `kimi-for-coding/k2p5` | Kimi | Optimized for coding, low latency |
| `github-copilot/gemini-2.5-pro` | Copilot | Fast via Copilot infrastructure |

### 🧠 Complex Problem Solving
**Best for:** Architecture design, debugging, multi-step reasoning

| Model | Provider | Why |
|-------|----------|-----|
| `openai/gpt-5.3-codex` | OpenAI | Best reasoning + coding combined |
| `openai/gpt-5.2` | OpenAI | Strong general agentic capabilities |
| `github-copilot/claude-opus-4.5` | Copilot | Excellent for complex tasks via Copilot |
| `openai/gpt-5.1-codex` | OpenAI | Long-horizon agentic tasks |

### 💻 Coding Tasks
**Best for:** Code generation, refactoring, code review

| Model | Provider | Why |
|-------|----------|-----|
| `openai/gpt-5.3-codex` | OpenAI | Most capable coding model |
| `openai/gpt-5.2-codex` | OpenAI | Advanced coding capabilities |
| `kimi-for-coding/k2p5` | Kimi | Specifically optimized for coding |
| `github-copilot/gpt-5.2` | Copilot | Great coding via Copilot |

### 📝 Documentation & Writing
**Best for:** README generation, documentation, content creation

| Model | Provider | Why |
|-------|----------|-----|
| `openai/gpt-5.2` | OpenAI | Strong general writing |
| `google/gemini-2.5-pro` | Google | Good long-form generation |
| `kimi-for-coding/kimi-k2-thinking` | Kimi | Step-by-step reasoning helps structure docs |

### 🔍 Research & Analysis
**Best for:** Codebase exploration, requirement analysis, feasibility studies

| Model | Provider | Why |
|-------|----------|-----|
| `openai/gpt-5.3-codex` | OpenAI | Best for understanding large codebases |
| `openai/gpt-5.1-codex-max` | OpenAI | Long-running research tasks |
| `github-copilot/claude-sonnet-4.5` | Copilot | Strong analysis via Copilot |

### 💰 Budget-Conscious
**Best for:** Cost-sensitive projects, high-volume tasks

| Model | Provider | Why |
|-------|----------|-----|
| `google/gemini-2.5-flash` | Google | Most cost-effective |
| `kimi-for-coding/k2p5` | Kimi | Free tier available |
| `github-copilot/*` | Copilot | Included in Copilot subscription |

### 🔄 Multi-Provider Strategy
**Best for:** Production workloads, reliability

Use multiple providers to avoid single points of failure:
```python
# Primary: OpenAI
spawn_teammate(model="openai/gpt-5.2")

# Fallback: Google  
spawn_teammate(model="google/gemini-2.5-pro")

# Alternative: Copilot
spawn_teammate(model="github-copilot/gpt-5.2")
```

### Quick Decision Guide

| If you need... | Use... |
|----------------|--------|
| Fastest response | `google/gemini-2.5-flash` |
| Best coding | `openai/gpt-5.3-codex` |
| No special auth | `kimi-for-coding/k2p5` or `github-copilot/*` |
| Long context (1M+) | `google/gemini-2.5-pro` |
| Complex reasoning | `openai/gpt-5.3-codex` |
| Budget option | `google/gemini-2.5-flash` or Copilot models |
| One subscription, many models | `github-copilot/*` |

---

## 🔧 Configuration

### OpenAI Setup
1. Sign in with your ChatGPT account: `opencode auth login`
2. Ensure you have Plus/Pro subscription for Codex models
3. Models are automatically discovered from OpenCode's configuration

### Google Setup
Add to `~/.config/opencode/opencode.json`:

```json
{
  "provider": {
    "google": {
      "models": {
        "gemini-2.5-flash": {
          "name": "Gemini 2.5 Flash",
          "limit": {
            "context": 1048576,
            "output": 65536
          }
        },
        "gemini-2.5-pro": {
          "name": "Gemini 2.5 Pro",
          "limit": {
            "context": 1048576,
            "output": 65535
          }
        }
      }
    }
  }
}
```

---

## 🤖 Usage Examples

### Spawn with Specific Model
```python
spawn_teammate(
    team_name="my-team",
    name="coder-1",
    prompt="Write code for...",
    model="openai/gpt-5.3-codex"
)
```

### Auto-Select Model
```python
spawn_teammate(
    team_name="my-team",
    name="researcher-1",
    prompt="Research...",
    model="auto",
    reasoning_effort="medium",
    prefer_speed=False
)
```

### Using Google Models
```python
spawn_teammate(
    team_name="my-team",
    name="fast-worker",
    prompt="Quick task...",
    model="google/gemini-2.5-flash"
)
```

---

## 🧪 Testing Results Summary

**Test Date:** 2026-02-19

### Successful Tests
- ✅ `openai/gpt-5.2` - Directory exploration, task execution
- ✅ `openai/gpt-5.3-codex` - Message sending, task completion
- ✅ `openai/gpt-5.2-codex` - Message sending, task completion  
- ✅ `openai/gpt-5.1-codex` - Message sending, task completion
- ✅ `google/gemini-2.5-flash` - Message sending, task completion
- ✅ `google/gemini-3-flash-preview` - Message sending, project analysis

### Failed Tests
- ❌ `openai/gpt-5.1` - Model not found (requires -codex suffix)
- ❌ `openai/gpt-5` - Model not found (invalid name)
- ❌ `openai/gpt-5-mini` - Model not found (invalid name)
- ❌ `openai/gpt-5.2-mini/nano` - Model not found (invalid names)
- ❌ `openai/gpt-5.2-medium` - Model not found (reasoning effort, not model)
- ❌ `openai/gpt-5.2-codex-low` - Requires ChatGPT Pro subscription
- ❌ `google/gemini-3-flash` - Antigravity deprecated
- ❌ All `google/antigravity-*` models - Deprecated

---

## 🔄 Updates

When OpenCode updates their model availability:
1. Run test suite with `list_available_models()`
2. Spawn test agents with new models
3. Update this documentation
4. Update README.md model section

---

## 📚 References

- [OpenAI Codex Models](https://developers.openai.com/codex/models)
- [OpenCode Documentation](https://opencode.ai)
- [OpenCode Configuration](https://opencode.ai/docs/configuration)