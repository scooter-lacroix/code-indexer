# Initial Concept
The goal is to update the existing `code-indexer` project to its next major version by fully integrating features from the `mgrep` repository (https://github.com/mixedbread-ai/mgrep.git) without any regressions. The integration must be seamless, effectively renaming and absorbing `mgrep` functionalities into the `code-indexer` codebase.

## Core Features & Goals

### 1. **Complete `mgrep` Integration (Renamed)**
-   **Full Feature Absorption:** Meticulously analyze and port all capabilities from `mgrep` into `code-indexer`.
-   **Seamless Rebranding:** Ensure no references to "mgrep" exist within the code, documentation, or system outputs. The functionality should appear native to `code-indexer`.
-   **Dual-Mode Operation:**
    -   **Standalone Power:** Enable `code-indexer` to function as a powerful, standalone tool without external dependencies (PostgreSQL/Elasticsearch), utilizing the ported "mgrep" features (including semantic search, web search, and reranking) alongside existing ripgrep support.
    -   **Augmented Intelligence:** Implement intelligent routing logic where the ported "mgrep" engine serves as the primary driver. PostgreSQL and Elasticsearch should only be invoked to **augment** these capabilities when they offer a distinct advantage (e.g., specific metadata queries, massive scale historical lookups) rather than overriding the new engine.
    -   **Future-Proofing:** Design this integration as a potential long-term replacement for the PostgreSQL/Elasticsearch backend, pending real-world performance validation.

### 2. **Enhanced Agent Integration (Beyond MCP)**
-   **Deeper Integration:** Move beyond the limitations of standard MCP to lower-overhead, high-capability integrations like Skills, Plugins, or Extensions.
-   **Implemented Features:**
    -   **CLI Tool:** `code-search` for direct agent interaction.
    -   **Skill Definition:** Optimized `SKILL.md` for agents like Claude Code.
    -   **Installation Helpers:** Scripts to configure various agent environments.
    -   **Hooks:** Session start hooks to enforce skill usage.
-   **Target Platforms:**
    -   **Priority 1:** Claude Code (Anthropic) and OpenAI (Codex/Custom GPTs).
    -   **Priority 2:** Editor environments like VS Code, Cursor, and Windsurf.
    -   **Priority 3:** CLI tools (OpenCode, Qwen Code, Amp CLI, Droid Factory, Gemini CLI).
    -   **Legacy Support:** Retain standard MCP support specifically for local environments like LM Studio and Ollama.

### 3. **Critical Stability & Performance (No Regressions)**
-   **Real-Time Indexing:** Maintain or improve current indexing speed and accuracy.
-   **Data Integrity:** Strict preservation of version tracking and file history data within the PostgreSQL backend (when active).
-   **Search Stability:** Ensure precision and recall of search results remain consistent or improve, regardless of the underlying engine used.

### 4. **Expanded Capabilities**
-   **Granular Version Tracking:** Enhance the existing system with more detailed diffing and history analysis.
-   **Improved Real-Time Indexing:** Optimize the efficiency and reliability of the asynchronous indexing pipeline.

## Strategic Approach
-   **Source Code Analysis:** A comprehensive analysis of the `mgrep` codebase is the first and most critical step to identify ideal integration points and improvements.
-   **Modular Implementation:** Implement the new search features as a modular component that serves as the core search capability, augmented by legacy backends only when necessary.
