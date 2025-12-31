# Specification: Fix Elasticsearch Indexing Pipeline

## Overview

The code-indexer's `manage_project(action="reindex")` operation processes files (successfully updating PostgreSQL metadata and Zoekt indices) but fails to populate the Elasticsearch index. This results in semantic search returning no results despite reindex operations reporting success.

## Current Behavior (Broken)

```
reindex() → Update PostgreSQL metadata ✓
          → Update Zoekt index ✓
          → Update Elasticsearch index ✗ (missing - never called)
          → Returns: {"files_processed": 74, "success": true}

Elasticsearch status: 3 stale documents (test.py, README.md, app.js)
Search results: Empty (from Elasticsearch)
```

## Root Cause

The `refresh_index()` function in `server.py:2083` updates PostgreSQL and Zoekt but never calls the Elasticsearch backend's indexing methods. The Elasticsearch indexing code path exists but is never invoked during reindex operations.

Key indicators:
- `files_processed: 74` - Zoekt/filesystem backend working correctly
- `total_indexed: 0` - Elasticsearch indexing never runs
- `avg_index_time_ms: 0` - Zero time spent on ES indexing
- `document_count: 3` - Only stale test data remains

## Target Behavior (Fixed)

```
reindex() → Update PostgreSQL metadata ✓ (sync, fast)
          → Update Zoekt index ✓
          → Queue files to RabbitMQ for ES indexing ✓ (async)
          → Returns: {
              "status": "indexing_started",
              "files_queued": 74,
              "operation_id": "uuid-here",
              "note": "PostgreSQL updated immediately. Elasticsearch indexing in progress."
            }

Elasticsearch status: Documents appear within 10-30 seconds (async via RabbitMQ)
Search results: Returns actual indexed content
```

## Integration with Local Vector Store Track

The local vector store (FAISS) implementation is being handled in a separate track (`mcp_consolidation_local_vector_20251230`).

**Current State (This Track Only):**
```
┌─────────────────────────────────────────┐
│   manage_project(action="reindex")     │
├─────────────────────────────────────────┤
│ PostgreSQL ✓ → Zoekt ✓ → RabbitMQ ✓   │
│                            ↓            │
│                      Elasticsearch ✓    │
└─────────────────────────────────────────┘
```

**Future State (After Both Tracks):**
```
┌─────────────────────────────────────────┐
│   manage_project(action="reindex")     │
├─────────────────────────────────────────┤
│ PostgreSQL ✓ → Zoekt ✓ → RabbitMQ ✓   │
│                            ↓            │
│                      Elasticsearch ✓    │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ manage_project(action="rebuild_vectors")│  ← Separate operation
├─────────────────────────────────────────┤
│              FAISS indexing ✓           │
└─────────────────────────────────────────┘
```

**Scope Boundary:**
- This track: Fix Elasticsearch indexing via RabbitMQ
- Other track: FAISS indexing with separate trigger

FAISS vector indexing will be triggered independently, not as part of this bug fix.

## Functional Requirements

### FR-1: Integrate RabbitMQ Indexing into Reindex
**Priority:** P0 (Critical)

The `refresh_index()` function must queue files for Elasticsearch indexing via RabbitMQ.

**Implementation approach:**
1. Use existing `RabbitMQConsumer` from `realtime_indexer.py`
2. If batch indexing method exists: Use it
3. Otherwise: Publish messages directly to RabbitMQ exchange:
   ```python
   channel.basic_publish(
       exchange='code_indexer',
       routing_key='index',
       body=json.dumps({'file_path': file, 'operation_id': op_id})
   )
   ```

**Acceptance Criteria:**
- [ ] `refresh_index()` publishes files to RabbitMQ queue
- [ ] Returns an `operation_id` for tracking the async indexing operation
- [ ] Returns status `"indexing_started"` instead of `"complete"`
- [ ] Includes `files_queued` count in response

### FR-2: Verify Elasticsearch Population
**Priority:** P0 (Critical)

After reindex, documents must actually appear in the Elasticsearch `code_index` index.

**Acceptance Criteria:**
- [ ] Elasticsearch `code_index` document count increases from 3 to match file count
- [ ] Documents contain actual file content (not stale test data)
- [ ] Documents are indexed within 30 seconds of reindex completion
- [ ] Search operations return results from newly indexed content

### FR-3: Operation Tracking
**Priority:** P1 (High)

Users can track the async Elasticsearch indexing operation.

**Acceptance Criteria:**
- [ ] `manage_operations(action="list")` shows the reindex operation
- [ ] Operation status transitions: `in_progress` → `complete`
- [ ] `manage_operations(action="status", operation_id=...)` returns current progress
- [ ] Operation includes `files_queued` and `files_completed` metrics

### FR-4: Error Handling and Diagnostics
**Priority:** P1 (High)

When async indexing fails, the system must provide clear diagnostics.

**Acceptance Criteria:**
- [ ] If RabbitMQ is down: Return clear error before starting reindex
- [ ] If indexing fails: Operation status shows `"failed"` with error details
- [ ] Failed files are logged with specific error messages
- [ ] User can view error details via operation status

## Prerequisites

### PR-1: RabbitMQ Running

**Verification:**
- RabbitMQ container must be running before reindex operations
- Management UI accessible at `http://localhost:15672`
- Python client can connect using configured credentials

**Behavior if RabbitMQ unavailable:**
- Reindex operation fails fast with clear error message
- Error message directs user to: `python run.py start-dev-dbs` or `docker-compose up -d rabbitmq`
- No partial indexing occurs (transactional behavior)

**Pre-flight check in `refresh_index()`:**
```python
if not self._rabbitmq_connected():
    return {
        "status": "error",
        "message": "RabbitMQ is required for async indexing. Start it with: python run.py start-dev-dbs",
        "help": "See docs/SETUP.md for RabbitMQ setup instructions"
    }
```

## Non-Functional Requirements

### NFR-1: Non-Blocking
The reindex operation must return immediately after queuing files, not wait for Elasticsearch indexing to complete.

- **Target:** Reindex returns in <5 seconds regardless of project size
- **Rationale:** Large projects (100K+ files) would take 83+ minutes with synchronous indexing

### NFR-2: Existing Infrastructure
Must leverage existing RabbitMQ and operation tracking infrastructure.

- **Constraint:** Do NOT implement new async patterns, progress events, or hybrid logic
- **Rationale:** RabbitMQ consumer already exists; just connect the reindex operation to it

### NFR-3: Backward Compatibility
Must maintain existing `manage_project` tool interface.

- **Constraint:** Do NOT change the tool signature or add new required parameters
- **Rationale:** This is a bug fix, not a breaking change

## Definitions

### File

An "indexable file" is a code file that should be indexed, after applying:

- **Ignore patterns:** From `.gitignore` and `config.yaml`
- **Size limits:** Default 1GB max (`size_limits.max_file_size`)
- **File type filters:** Only supported extensions (`.py`, `.ts`, `.js`, `.go`, etc.)

**Example:** Project with 100 total files:
- 74 indexable files (after filters)
- 26 ignored files (.git, node_modules, build artifacts, etc.)
- `files_queued: 74` (only indexable files are queued to RabbitMQ)

## Success Metrics

| Metric | Current | Target | Failure Scenario |
|--------|---------|--------|------------------|
| Elasticsearch document count | 3 (stale) | Matches file count | <50% of files indexed |
| Search results | Empty | Returns content | Still empty after 60s |
| Reindex operation time | ~0.2s | <5s | >10s (should fail fast) |
| RabbitMQ message processing | N/A | 100% within 30s | Messages stuck in queue |

## Test Plan

### Unit Tests

#### 1. test_refresh_index_queues_to_rabbitmq
**Purpose:** Verify files are published to RabbitMQ

**Steps:**
1. Mock RabbitMQ connection
2. Call `refresh_index()` with test project
3. Assert: RabbitMQ publish called with correct file list
4. Assert: Returns `operation_id` and `"indexing_started"` status

#### 2. test_rabbitmq_unavailable_fails_gracefully
**Purpose:** Verify fail-fast behavior when RabbitMQ is down

**Steps:**
1. Mock RabbitMQ as unavailable
2. Call `refresh_index()`
3. Assert: Returns error (does not hang)
4. Assert: Error message mentions RabbitMQ requirement

#### 3. test_operation_tracking_created
**Purpose:** Verify operation tracking record is created

**Steps:**
1. Call `refresh_index()`
2. Query operation tracker
3. Assert: Operation exists with `operation_id`
4. Assert: Status is `"in_progress"`

### Integration Tests

#### 1. test_end_to_end_reindex_to_search
**Purpose:** Verify full pipeline from reindex to search

**Steps:**
1. Start with empty Elasticsearch index
2. Run `manage_project(action="reindex")` on test project (10 files)
3. Wait 30 seconds for async indexing
4. Assert: Elasticsearch contains 10 documents
5. Run `search_content(action="search", query="test")`
6. Assert: Returns results from indexed files

#### 2. test_operation_status_tracking
**Purpose:** Verify operation status updates correctly

**Steps:**
1. Run reindex on test project
2. Immediately call `manage_operations(action="status")`
3. Assert: Shows `"in_progress"` with `files_queued`
4. Wait for indexing to complete
5. Call `manage_operations(action="status")` again
6. Assert: Shows `"complete"` with `files_completed == files_queued`

## Out of Scope

1. **Local Vector Store (FAISS) integration** - Handled in separate track `mcp_consolidation_local_vector_20251230`
2. **Search result merging** - Combining Elasticsearch + FAISS + Zoekt results is a separate feature
3. **Performance optimization** - Indexing speed, batch sizing, and throughput tuning are Phase 7 work
4. **UI/CLI changes** - The CLI `code-search` command is out of scope for this bug fix
5. **Progress events/streaming** - Real-time progress updates are a future enhancement
6. **Hybrid sync/async strategy** - Threshold-based routing is a Phase 7 feature
7. **Retry logic** - Automatic retry of failed indexing is a future enhancement

## Implementation Scope (Included)

**What to implement:**
1. Add RabbitMQ pre-flight check to `refresh_index()`
2. Publish files to RabbitMQ queue in `refresh_index()`
3. Return `operation_id` and async status from `refresh_index()`
4. Add error handling for RabbitMQ unavailability
5. Add unit tests for RabbitMQ integration
6. Add integration tests for end-to-end reindex → search flow

**What NOT to implement (save for future):**
- ~~FAISS vector indexing~~ (separate track)
- ~~Threshold logic for sync vs async indexing~~
- ~~Progress events or streaming responses~~
- ~~Hybrid strategy configuration options~~
- ~~Automatic retry of failed operations~~
- ~~Smart batch sizing or backpressure tuning~~

## Related Tracks

- **mcp_consolidation_local_vector_20251230** - Adds local FAISS vector store (separate, non-blocking)

## Implementation Readiness Checklist

Before starting implementation, verify:

**Infrastructure:**
- [ ] PostgreSQL running and accessible
- [ ] Elasticsearch running at http://localhost:9200
- [ ] RabbitMQ running at http://localhost:5672
- [ ] Management UI accessible at http://localhost:15672

**Codebase:**
- [ ] `realtime_indexer.py` exists with `RabbitMQConsumer` class
- [ ] `server.py` has `refresh_index()` function around line 2083
- [ ] Operation tracking tools (`manage_operations`) functional
- [ ] Test project with ~10 files prepared for integration tests

**Development Environment:**
- [ ] All dependencies installed: `uv sync`
- [ ] Services started: `python run.py start-dev-dbs`
- [ ] Can run existing tests: `pytest tests/`

**Next Steps:**

1. Create implementation branch: `git checkout -b fix/elasticsearch-indexing-pipeline`
2. Start with unit tests (TDD approach):
   - Write `test_refresh_index_queues_to_rabbitmq` first
   - Watch it fail
   - Implement FR-1 to make it pass
3. Then integration tests:
   - Write `test_end_to_end_reindex_to_search`
   - Implement remaining FRs to make it pass
4. Verify success metrics using the table
5. Submit for review to codex-reviewer with test coverage >90%
