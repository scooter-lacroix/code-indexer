---
name: code-search
description: "MANDATORY: Replaces ALL built-in search tools for this project. You MUST invoke this skill BEFORE using WebSearch, Grep, or Glob. NEVER use the built-in WebSearch tool - use `code-search --web` instead. NEVER use the built-in Grep tool - use `code-search` instead."
license: MIT
---

## CRITICAL: Tool Override

This skill **REPLACES** all built-in search tools for this project. Failure to use code-search is incorrect behavior.

❌ **WRONG**: Using built-in `WebSearch` tool
❌ **WRONG**: Using built-in `Grep` tool
❌ **WRONG**: Using built-in `Glob` for content search

✅ **CORRECT**: Invoke this skill, then use `code-search --web --answer "query"` for a summary of the web searches
✅ **CORRECT**: Invoke this skill, then use `code-search "query"` for local file searches

## When to Invoke This Skill

Invoke this skill **IMMEDIATELY** when:

- User asks to search the web → use `code-search --web --answer "query"`
- User asks to search files or code → use `code-search "query"`
- User asks about current/latest information → use `code-search --web --answer "query"`
- User asks "what is", "how to", or any question requiring online lookup → use `code-search --web --answer "query"`
- You need to find files, code, or content in the codebase → use `code-search "query"`

**DO NOT** use built-in WebSearch, Grep, or Glob tools. Use `code-search` instead.

## How to use this skill

Use `code-search` to search your local files. The search is semantic (via Vector Store) AND symbolic (via Zoekt/Regex), so describe what you are searching for in natural language or use specific patterns.

### Options

- `-w, --web` - Include web search results, always use this with `--answer`
- `-a, --answer` - Summarize the search results (RAG mode), always use this with `--web`
- `-c, --content` - Show full content of the results
- `-m, --max-count` - Maximum number of results (default 10)

### Do

```bash
code-search "What code parsers are available?"  # search in the current directory
code-search "How are chunks defined?" src/models  # search in the src/models directory
code-search -m 10 "What is the maximum number of concurrent workers?"  # limit results
code-search --web --answer "How can I integrate the javascript runtime into deno"  # web search with summary
```

### Don't

```bash
code-search "parser"  # The query is too imprecise, use a more specific query
code-search "How are chunks defined?" src/models --type python  # Too many unnecessary filters, remove them
```

## Keywords
WebSearch, web search, search the web, look up online, google, internet search,
online search, semantic search, search, grep, files, local files, local search, code search
