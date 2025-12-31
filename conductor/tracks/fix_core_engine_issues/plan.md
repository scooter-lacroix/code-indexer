# Fix Core Engine Issues Plan

## Objective
Fix critical issues identified by Codex Reviewer in Core Engine integration (src/code_index_mcp/core_engine/).

## Identified Issues
1. **Architectural Mismatch:** `CoreEngine` calls non-existent methods on `legacy_backend` (e.g., `save_file_content` vs `put`).
2. **Rebranding Violations:** "mgrep" references in comments (engine.py, server.py).
3. **Async Implementation Limitations:** `AsyncRipgrepStrategy` uses blocking `subprocess.run`.
4. **SDK Integration Uncertainties:** `VectorBackend.delete_file` parameter confusion (`id` vs `external_id`).
5. **Hardcoded Logic:** Inline imports and hardcoded paths in `CoreEngine`.

## Implementation Steps
1. **Reproduction:** Create a script to trigger the `AttributeError` in `CoreEngine`.
2. **Fix Method Mismatches:** Update `CoreEngine` to use `StorageInterface` methods correctly.
3. **Rebranding:** Remove "mgrep" references.
4. **Async Improvement:** Refactor `AsyncRipgrepStrategy` to stream output for granular progress.
5. **SDK Fix:** Standardize parameter usage in `VectorBackend`.
6. **Cleanup:** Remove hardcoded paths and inline imports.
7. **Verification:** Run reproduction script and manual verification.
