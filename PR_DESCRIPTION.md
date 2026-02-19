# 🚀 Critical Fixes & Improvements for OpenCode-Teams-MCP

## Summary

This PR addresses **critical bugs** and adds **significant improvements** to make the repository production-ready and discoverable.

## 🔴 Critical Bug Fixes

### 1. Fixed Wrong Install URL (CRITICAL)
**Before:** `github.com/DasBluEyedDevil/opencode-teams-mcp`
**After:** `github.com/9thLevelSoftware/OpenCode-Teams-MCP@v0.1.0`

This was preventing users from installing the correct repository!

## ✨ New Features & Improvements

### README.md Enhancements
- ✅ **Added badges** (Python 3.12+, MIT License, OpenCode Compatible, Kimi K2.5)
- ✅ **Added version pinning warning** to protect users from breaking changes
- ✅ **Added Configuration section** with environment variable documentation
- ✅ **Added Claude Code configuration** showing dual-client support
- ✅ **Added comparison table** highlighting 15 tools vs parent's 11
- ✅ **Improved About section** with "What You Get" bullet points
- ✅ **Added Project Roadmap section** surfacing hidden `.planning/` documentation
- ✅ **Added Development & Contributing sections**

### New GitHub Workflows
- ✅ **Created `release.yml`** - Tag-triggered releases with cross-platform testing
- ✅ **Expanded `ci.yml`** - Now tests on Ubuntu, macOS, and Windows

### Documentation
- ✅ **Created `CHANGELOG.md`** - Comprehensive changelog with comparison table

## 📊 Comparison with Parent Repository

| Feature | Parent (cs50victor) | This Fork | Improvement |
|---------|---------------------|-----------|-------------|
| **MCP Tools** | 11 | **15** | +36% |
| **Test Files** | 8 | **12** | +50% |
| **CI Platforms** | 3 | **3** | Parity |
| **Release Automation** | ✅ | **✅** | Parity |
| **Kimi K2.5 Optimization** | ❌ | **✅** | New |
| **Task Complexity Analysis** | ❌ | **✅** | New |
| **Dynamic Model Discovery** | ❌ | **✅** | New |

## 🎯 Expected Impact

After merging this PR:
- Users can correctly install the repository
- Repository becomes discoverable with proper documentation
- Professional appearance with badges and clear structure
- Cross-platform CI ensures reliability
- Release automation enables version pinning

## 📝 Checklist

- [x] Fixed critical install URL bug
- [x] Added badges for visual credibility
- [x] Added version pinning warning
- [x] Added configuration documentation
- [x] Added comparison table
- [x] Created release workflow
- [x] Expanded CI to all platforms
- [x] Created comprehensive changelog

## 🔗 Related

- Parent repository: [cs50victor/claude-code-teams-mcp](https://github.com/cs50victor/claude-code-teams-mcp)
- Fork comparison: 86 commits ahead, 13 behind

---

**Note:** After merging, the repository owner should:
1. Add GitHub Topics: `mcp`, `mcp-server`, `agents`, `ai-agents`, `opencode`, `kimi`, `agent-teams`, `multi-agent`
2. Create the v0.1.0 release using the new release workflow
3. Update repository description to: "Multi-agent orchestration for OpenCode with Kimi K2.5. Spawn agent teams, share tasks, and coordinate AI workflows via MCP."
