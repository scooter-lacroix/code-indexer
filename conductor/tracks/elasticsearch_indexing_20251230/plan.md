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

## Phase 2: RabbitMQ Integration (Unit Tests - TDD)

- [ ] Task: Write unit test `test_refresh_index_queues_to_rabbitmq` (TDD - Write Test)
  - Create test file `tests/unit/test_elasticsearch_indexing.py`
  - Mock RabbitMQ connection
  - Test that `refresh_index()` publishes to RabbitMQ
  - Test return value includes `operation_id` and `"indexing_started"` status
  - Verify test fails initially (TDD red phase)

- [ ] Task: Implement RabbitMQ publishing in `refresh_index()` (TDD - Implement)
  - Import `RabbitMQConsumer` from `realtime_indexer.py`
  - Add RabbitMQ pre-flight check
  - Publish files to RabbitMQ queue after PostgreSQL update
  - Generate and return `operation_id`
  - Update return value to `"indexing_started"` status
  - Verify unit test passes

- [ ] Task: Write unit test `test_rabbitmq_unavailable_fails_gracefully` (TDD - Write Test)
  - Mock RabbitMQ as unavailable/down
  - Test that `refresh_index()` returns error (does not hang)
  - Test error message mentions RabbitMQ requirement
  - Verify test fails initially

- [ ] Task: Implement RabbitMQ error handling (TDD - Implement)
  - Add `_rabbitmq_connected()` check method
  - Return error early if RabbitMQ unavailable
  - Include helpful error message with setup instructions
  - Verify unit test passes

- [ ] Task: Write unit test `test_operation_tracking_created` (TDD - Write Test)
  - Test that operation tracker records new operation
  - Test operation has correct `operation_id`
  - Test operation status is `"in_progress"`
  - Verify test fails initially

- [ ] Task: Implement operation tracking in `refresh_index()` (TDD - Implement)
  - Create operation record via operation tracker
  - Set `files_queued` count
  - Set initial status to `"in_progress"`
  - Return `operation_id` in response
  - Verify unit test passes

- [ ] Task: Conductor - Codex-Reviewer Rigor Check 'Phase 2' (Zero Tolerance - Tsar of Excellence)
  - Deploy codex-reviewer agent to conduct comprehensive review
  - Review must cover: TDD compliance, error handling, operation tracking
  - All findings must be debugged (amp-code or opencode-scaffolder)
  - After fixes, codex-reviewer re-reviews for rigor verification
  - Only proceed to Phase 3 when codex-reviewer approves

## Phase 3: Integration Tests and End-to-End Verification

- [ ] Task: Write integration test `test_end_to_end_reindex_to_search`
  - Create test file `tests/integration/test_elasticsearch_indexing.py`
  - Start with empty Elasticsearch index
  - Run `manage_project(action="reindex")` on test project
  - Wait up to 30 seconds for async indexing
  - Assert Elasticsearch document count matches file count
  - Run search query and verify results

- [ ] Task: Verify Elasticsearch population works end-to-end
  - Ensure RabbitMQ consumer processes messages
  - Verify Elasticsearch documents contain actual file content
  - Confirm stale test data is replaced/updated
  - Test search returns results from newly indexed content

- [ ] Task: Write integration test `test_operation_status_tracking`
  - Run reindex on test project
  - Immediately query operation status
  - Assert status is `"in_progress"` with `files_queued`
  - Wait for indexing to complete
  - Query operation status again
  - Assert status is `"complete"` with `files_completed == files_queued`

- [ ] Task: Implement operation status updates
  - Ensure operation tracker updates status during indexing
  - Update `files_completed` count as files are processed
  - Transition status from `"in_progress"` to `"complete"`
  - Handle failed indexing scenarios

- [ ] Task: Conductor - Codex-Reviewer Rigor Check 'Phase 3' (Zero Tolerance - Tsar of Excellence)
  - Deploy codex-reviewer agent to conduct comprehensive review
  - Review must cover: integration tests, end-to-end flow, operation status
  - All findings must be debugged (amp-code or opencode-scaffolder)
  - After fixes, codex-reviewer re-reviews for rigor verification
  - Only proceed to Phase 4 when codex-reviewer approves

## Phase 4: Success Metrics and Documentation

- [ ] Task: Verify all success metrics pass
  - Elasticsearch document count matches file count (not 3 stale docs)
  - Search results return actual content (not empty)
  - Reindex operation completes in <5 seconds (async)
  - RabbitMQ messages processed within 30 seconds

- [ ] Task: Run full test suite
  - Execute `pytest tests/` with coverage
  - Verify all new tests pass
  - Verify no regressions in existing tests
  - Ensure coverage >90% for new code

- [ ] Task: Update documentation
  - Document Elasticsearch indexing behavior in README.md
  - Add troubleshooting section for RabbitMQ issues
  - Update CHANGELOG.md with bug fix details
  - Add error scenarios to help documentation

- [ ] Task: Verify success metrics table
  - Run verification script from spec
  - Confirm all metrics show "Target" achieved
  - Document any metrics in "Failure Scenario" column

- [ ] Task: Conductor - Codex-Reviewer Rigor Check 'Phase 4' (Zero Tolerance - Tsar of Excellence)
  - Deploy codex-reviewer agent to conduct comprehensive review
  - Review must cover: success metrics, documentation, test coverage
  - All findings must be debugged (amp-code or opencode-scaffolder)
  - After fixes, codex-reviewer re-reviews for rigor verification
  - Only proceed to user manual verification when codex-reviewer approves

- [ ] Task: Conductor - User Manual Verification 'Phase 4' (Protocol in workflow.md)

## Success Criteria

Track is complete when:
- [ ] All 4 functional requirements (FR-1 through FR-4) are implemented
- [ ] All unit tests pass (3 tests)
- [ ] All integration tests pass (2 tests)
- [ ] Test coverage >90% for new code
- [ ] All success metrics from spec are achieved
- [ ] Elasticsearch documents populate after reindex
- [ ] Search returns results from indexed content
- [ ] Phases 1-4 approved by codex-reviewer with rigor checks passed
