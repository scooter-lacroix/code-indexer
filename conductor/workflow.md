# Project Workflow

## 1. Test Coverage
- **Requirement:** >95% code coverage.
- **Verification:** Run tests before marking any task as complete.

## 2. Commit Strategy
- **Frequency:** Stage changes aggressively. Do not commit after every small task.
- **Threshold:** Accumulate changes into the largest possible logical commits.
- **Notification:** When the staging area is significantly large or a logical phase is complete, **notify the user** to review and confirm the commit.
- **Content:** Commit messages must be descriptive but concise.

## 3. Task Summaries
- **Method:** Use Git Notes (or concise commit bodies if notes are unavailable).
- **Style:** Brief and to the point.
- **Constraint:** **NEVER** mention "mgrep" in any summary, note, or commit message. Use "internal search engine", "enhanced indexing", or "core search" instead.

## 4. Phase Completion Verification Protocol
1.  **Review:** Verify all tasks in the phase are marked as completed.
2.  **Test:** Execute the full test suite to ensure no regressions.
3.  **Lint:** Run the project's linter (e.g., `ruff check .`, `npm run lint`).
4.  **Checkpoint:** Prompt the user to perform a manual review of the phase deliverables.