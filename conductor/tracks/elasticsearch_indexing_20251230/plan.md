# Implementation Plan: Fix Elasticsearch Indexing Pipeline

## Phase 1: Investigation and Setup [checkpoint: 204dfdf]

- [x] Task: Verify RabbitMQ infrastructure exists and is accessible
  - Check `realtime_indexer.py` for `RabbitMQConsumer` class
  - Verify RabbitMQ connection configuration in `config.yaml`
  - Test RabbitMQ management UI accessibility (http://localhost:15672)
  - Document existing batch indexing methods available

- [x] Task: Analyze current `refresh_index()` implementation
  - Read `server.py:2083` (`refresh_index()` function)
  - Trace current indexing flow (PostgreSQL, Zoekt)
  - Identify where Elasticsearch indexing should be inserted
  - Document current return value structure

- [x] Task: Set up test environment
  - Create test project directory with ~10 sample files
  - Ensure PostgreSQL, Elasticsearch, RabbitMQ are running
  - Verify existing test infrastructure works
  - Run baseline tests to ensure environment is clean

- [x] Task: Conductor - Codex-Reviewer Rigor Check 'Phase 1' (Zero Tolerance - Tsar of Excellence)
  - Deploy codex-reviewer agent to conduct comprehensive review
  - Review must cover: code structure, test setup, infrastructure verification
  - All findings must be debugged (amp-code or opencode-scaffolder)
  - After fixes, codex-reviewer re-reviews for rigor verification
  - Only proceed to Phase 2 when codex-reviewer approves

## Phase 2: RabbitMQ Integration (Unit Tests - TDD) [checkpoint: f4b8a9e]

- [x] Task: Write unit test `test_refresh_index_queues_to_rabbitmq` (TDD - Write Test)
  - Create test file `tests/unit/test_elasticsearch_indexing.py`
  - Mock RabbitMQ connection
  - Test that `refresh_index()` publishes to RabbitMQ
  - Test return value includes `operation_id` and `"indexing_started"` status
  - Verify test fails initially (TDD red phase)

- [x] Task: Implement RabbitMQ publishing in `refresh_index()` (TDD - Implement)
  - Import `RabbitMQConsumer` from `realtime_indexer.py`
  - Add RabbitMQ pre-flight check
  - Publish files to RabbitMQ queue after PostgreSQL update
  - Generate and return `operation_id`
  - Update return value to `"indexing_started"` status
  - Verify unit test passes

- [x] Task: Write unit test `test_rabbitmq_unavailable_fails_gracefully` (TDD - Write Test)
  - Mock RabbitMQ as unavailable/down
  - Test that `refresh_index()` returns error (does not hang)
  - Test error message mentions RabbitMQ requirement
  - Verify test fails initially

- [x] Task: Implement RabbitMQ error handling (TDD - Implement)
  - Add `_rabbitmq_connected()` check method
  - Return error early if RabbitMQ unavailable
  - Include helpful error message with setup instructions
  - Verify unit test passes

- [x] Task: Write unit test `test_operation_tracking_created` (TDD - Write Test)
  - Test that operation tracker records new operation
  - Test operation has correct `operation_id`
  - Test operation status is `"in_progress"`
  - Verify test fails initially

- [x] Task: Implement operation tracking in `refresh_index()` (TDD - Implement)
  - Create operation record via operation tracker
  - Set `files_queued` count
  - Set initial status to `"in_progress"`
  - Return `operation_id` in response
  - Verify unit test passes

- [x] Task: Conductor - Codex-Reviewer Rigor Check 'Phase 2' (Zero Tolerance - Tsar of Excellence)
  - Deploy codex-reviewer agent to conduct comprehensive review
  - Review must cover: TDD compliance, error handling, operation tracking
  - All findings must be debugged (amp-code or opencode-scaffolder)
  - After fixes, codex-reviewer re-reviews for rigor verification
  - Only proceed to Phase 3 when codex-reviewer approves

## Phase 3: Integration Tests and End-to-End Verification [checkpoint: 55fddde]

- [x] Task: Write integration test `test_end_to_end_reindex_to_search`
  - Create test file `tests/integration/test_elasticsearch_indexing.py`
  - Start with empty Elasticsearch index
  - Run `manage_project(action="reindex")` on test project
  - Wait up to 30 seconds for async indexing
  - Assert Elasticsearch document count matches file count
  - Run search query and verify results

- [x] Task: Verify Elasticsearch population works end-to-end
  - Ensure RabbitMQ consumer processes messages
  - Verify Elasticsearch documents contain actual file content
  - Confirm stale test data is replaced/updated
  - Test search returns results from newly indexed content

- [x] Task: Write integration test `test_operation_status_tracking`
  - Run reindex on test project
  - Immediately query operation status
  - Assert status is `"in_progress"` with `files_queued`
  - Wait for indexing to complete
  - Query operation status again
  - Assert status is `"complete"` with `files_completed == files_queued`

- [x] Task: Implement operation status updates
  - Ensure operation tracker updates status during indexing
  - Update `files_completed` count as files are processed
  - Transition status from `"in_progress"` to `"complete"`
  - Handle failed indexing scenarios

- [x] Task: Conductor - Codex-Reviewer Rigor Check 'Phase 3' (Zero Tolerance - Tsar of Excellence)
  - Deploy codex-reviewer agent to conduct comprehensive review
  - Review must cover: integration tests, end-to-end flow, operation status
  - All findings must be debugged (amp-code or opencode-scaffolder)
  - After fixes, codex-reviewer re-reviews for rigor verification
  - Only proceed to Phase 4 when codex-reviewer approves

## Phase 4: Success Metrics and Documentation [checkpoint: 7a8f3c2]

- [x] Task: Verify all success metrics pass
  - Elasticsearch document count matches file count (not 3 stale docs)
  - Search results return actual content (not empty)
  - Reindex operation completes in <5 seconds (async)
  - RabbitMQ messages processed within 30 seconds

- [x] Task: Run full test suite
  - Execute `pytest tests/` with coverage
  - Verify all new tests pass (7 Elasticsearch indexing tests)
  - Verify no regressions in existing tests (189/189 unit tests pass)
  - Ensure coverage >90% for new code

- [x] Task: Update documentation
  - Document Elasticsearch indexing behavior in CHANGELOG.md (v3.0.1 entry added)
  - Add troubleshooting section for RabbitMQ issues in TROUBLESHOOTING.md
  - Document async behavior and operation tracking
  - Add error scenarios to help documentation

- [x] Task: Verify success metrics table
  - Confirm all metrics show "Target" achieved in CHANGELOG.md
  - Document async behavior and expected timelines

- [x] Task: Conductor - Codex-Reviewer Rigor Check 'Phase 4' (Zero Tolerance - Tsar of Excellence)
  - Deploy codex-reviewer agent to conduct comprehensive review
  - Review found 5 BLOCKERs including force_reindex() missing RabbitMQ integration
  - Fixed: Added RabbitMQ integration to force_reindex()
  - Fixed: Added 2 new unit tests for force_reindex()
  - Fixed: Updated CHANGELOG.md and TROUBLESHOOTING.md
  - All findings debugged and fixed

- [x] Task: Codex-Reviewer Re-Review 'Phase 4'
  - Re-deployed codex-reviewer agent to verify all BLOCKERs fixed
  - All 5 BLOCKERs verified as fixed
  - Phase 4 APPROVED by codex-reviewer

- [x] Task: Conductor - User Manual Verification 'Phase 4' (Protocol in workflow.md)
  - Integration tests: 10/10 PASSED in 14.61s (NO HANGING)
  - Unit tests: 7/7 PASSED
  - Codex-Reviewer final Phase 4 review: **APPROVED** ✓

## Success Criteria

Track is complete when:
- [x] All 4 functional requirements (FR-1 through FR-4) are implemented
- [x] All unit tests pass (7 Elasticsearch indexing tests)
- [x] All integration tests pass (10/10 - NO SKIPS)
- [x] Test coverage >90% for new code
- [x] All success metrics from spec are achieved
- [x] Elasticsearch documents populate after reindex (async via RabbitMQ)
- [x] Search returns results from indexed content
- [x] Phases 1-4 approved by codex-reviewer with rigor checks passed
- [x] User manual verification complete

## ✅ **TRACK COMPLETED** - All Phases Approved

**Final Test Results:**
- Unit Tests: 7/7 PASSED
- Integration Tests: 10/10 PASSED (14.61s, NO HANGING)
- Total: 17/17 PASSED

**Codex-Reviewer Final Verdict:**
> "✅ **PHASE 4 APPROVED - ALL BLOCKERS RESOLVED**
>
> Thread Safety: EXCELLENT
> Timeout Handling: EXCELLENT
> Error Recovery: EXCELLENT
> Production Readiness: HIGH
>
> **No remaining BLOCKERs identified.**"
