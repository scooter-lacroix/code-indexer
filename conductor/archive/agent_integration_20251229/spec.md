# Specification: Enhanced Agent Integration

## Overview
This track focuses on deepening the integration of `code-indexer` with various AI agents and environments, moving beyond the standard Model Context Protocol (MCP) where beneficial. The goal is to provide "Skills" or native hooks that allow agents to use the Unified Core Engine more effectively and autonomously.

## Key Objectives
-   **CLI Entry Point:** Create a dedicated CLI command (e.g., `code-search`) that agents can invoke directly via shell execution, wrapping the `CoreEngine` search capabilities.
-   **Skill Definition:** Create a `SKILL.md` (or equivalent) that instructs agents (like Claude Code) to prefer this CLI tool over built-in search mechanisms.
-   **Installation Scripts:** specific scripts to automate the configuration of `code-indexer` for different environments (Claude Code, OpenAI, VS Code, etc.).
-   **Hooks:** Implement file watching hooks (if needed beyond `realtime_indexer`) for deeper IDE integration.

## Technical Requirements
-   **New CLI:** `code-search` command exposing `search` and `ask` functionality of `CoreEngine`.
-   **Skill Template:** A rebranded `SKILL.md` emphasizing the use of `code-search`.
-   **Installers:** Python scripts to detect environment and register the tool/skill.

## Success Criteria
-   `code-search` CLI works from terminal.
-   `SKILL.md` is generated and valid.
-   Installation scripts successfully configure at least one target agent (e.g. Claude Code) or provide clear instructions.
