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

## 4. Phase Completion Verification and Checkpointing Protocol (AUTONOMOUS MODE)

**Trigger:** This protocol is executed immediately after a task is completed that also concludes a phase in `plan.md`.

**IMPORTANT:** This workflow runs in AUTONOMOUS mode. All verification proceeds automatically without pausing for user confirmation.

1.  **Announce Protocol Start:** Inform the user that the phase is complete and the verification and checkpointing protocol has begun.

2.  **Ensure Test Coverage for Phase Changes:**
    -   **Step 2.1: Determine Phase Scope:** To identify the files changed in this phase, you must first find the starting point. Read `plan.md` to find the Git commit SHA of the *previous* phase's checkpoint. If no previous checkpoint exists, the scope is all changes since the first commit.
    -   **Step 2.2: List Changed Files:** Execute `git diff --name-only <previous_checkpoint_sha> HEAD` to get a precise list of all files modified during this phase.
    -   **Step 2.3: Verify and Create Tests:** For each file in the list:
        -   **CRITICAL:** First, check its extension. Exclude non-code files (e.g., `.json`, `.md`, `.yaml`).
        -   For each remaining code file, verify a corresponding test file exists.
        -   If a test file is missing, you **must** create one. Before writing the test, **first, analyze other test files in the repository to determine the correct naming convention and testing style.** The new tests **must** validate the functionality described in this phase's tasks (`plan.md`).

3.  **Execute Automated Tests with Proactive Debugging:**
    -   Before execution, announce the exact shell command you will use to run the tests.
    -   **Example Announcement:** "I will now run the automated test suite to verify the phase. **Command:** `CI=true npm test`"
    -   Execute the announced command.
    -   **AUTONOMOUS DEBUGGING:** If tests fail, you **must** attempt to fix them automatically. You may attempt to fix failures up to **5 times**. Use appropriate subagents to diagnose and fix issues. If tests still fail after 5 attempts, **halt execution** and report the persistent failure with full diagnostic information.

4.  **Create Checkpoint Commit:**
    -   Stage all changes. If no changes occurred in this step, proceed with an empty commit.
    -   Perform the commit with a clear and concise message (e.g., `conductor(checkpoint): Checkpoint end of Phase X`).

5.  **Attach Verification Report using Git Notes:**
    -   **Step 5.1: Draft Note Content:** Create a detailed verification report including the automated test command, test results, and any issues resolved.
    -   **Step 5.2: Attach Note:** Use the `git notes` command and the full commit hash from the previous step to attach the full report to the checkpoint commit.

6.  **Get and Record Phase Checkpoint SHA:**
    -   **Step 6.1: Get Commit Hash:** Obtain the hash of the *just-created checkpoint commit* (`git log -1 --format="%H"`).
    -   **Step 6.2: Update Plan:** Read `plan.md`, find the heading for the completed phase, and append the first 7 characters of the commit hash in the format `[checkpoint: <sha>]`.
    -   **Step 6.3: Write Plan:** Write the updated content back to `plan.md`.

7. **Commit Plan Update:**
    -   **Action:** Stage the modified `plan.md` file.
    -   **Action:** Commit this change with a descriptive message following the format `conductor(plan): Mark phase '<PHASE NAME>' as complete`.

8.  **Announce Completion and Continue:** Inform the user that the phase is complete and the checkpoint has been created, then **immediately proceed** to the next phase without waiting for confirmation.

### Quality Gates

Before marking any task complete, verify:

- [ ] All tests pass
- [ ] Code coverage meets requirements (>80%)
- [ ] Code follows project's code style guidelines (as defined in `code_styleguides/`)
- [ ] All public functions/methods are documented (e.g., docstrings, JSDoc, GoDoc)
- [ ] Type safety is enforced (e.g., type hints, TypeScript types, Go types)
- [ ] No linting or static analysis errors (using the project's configured tools)
- [ ] Documentation updated if needed
- [ ] No security vulnerabilities introduced
