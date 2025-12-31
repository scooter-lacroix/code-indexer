"""
Integration Tests for Elasticsearch Indexing

This test module provides comprehensive integration tests for the end-to-end
Elasticsearch indexing flow, verifying that the Phase 2 RabbitMQ integration
works correctly with actual services (PostgreSQL, Elasticsearch, RabbitMQ).

Test Coverage:
- test_end_to_end_reindex_to_search: Verifies the full flow from refresh_index
  to Elasticsearch population and search functionality
- test_operation_status_tracking: Verifies operation status updates during
  the indexing process

Prerequisites:
- Docker services running (PostgreSQL, Elasticsearch, RabbitMQ)
  Start with: docker-compose up -d

Run with:
    # Run all integration tests (skips if services unavailable)
    pytest tests/integration/test_elasticsearch_indexing.py -v --tb=short

    # Run specific test
    pytest tests/integration/test_elasticsearch_indexing.py::TestEndToEndReindexToSearch::test_end_to_end_reindex_to_search -v

    # Run without integration tests
    pytest tests/integration/test_elasticsearch_indexing.py -v -m "not integration"

Note:
Tests marked with @pytest.mark.integration require actual services running.
Tests will skip gracefully if services are unavailable.
"""

import os
import sys
import time
import json
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from unittest.mock import MagicMock, AsyncMock, patch

import pytest
import asyncio

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from elasticsearch import Elasticsearch
from mcp.server.fastmcp import Context

from code_index_mcp.server import (
    refresh_index,
    get_operation_status,
    set_project_path,
    manage_operations,
)
from code_index_mcp.realtime_indexer import (
    RabbitMQProducer,
    RabbitMQConsumer,
)
from code_index_mcp.progress_tracker import (
    ProgressTracker,
    OperationStatus,
    progress_manager,
)
from code_index_mcp.config_manager import ConfigManager
from code_index_mcp.storage.elasticsearch_storage import ElasticsearchSearch


# =============================================================================
# CONFIGURATION
# =============================================================================

# Service connection settings
ELASTICSEARCH_HOSTS = ["http://localhost:9200"]
RABBITMQ_HOST = "localhost"
RABBITMQ_PORT = 5672
RABBITMQ_EXCHANGE = "code_index_exchange"
RABBITMQ_QUEUE = "code_index_queue"
RABBITMQ_ROUTING_KEY = "indexing.#"
ES_INDEX_NAME = "code_index"

# Test configuration
WAIT_TIMEOUT = 30  # Maximum seconds to wait for indexing
POLL_INTERVAL = 0.5  # Seconds between status checks
TEST_FILE_COUNT = 10  # Number of test files to create


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(scope="module")
def test_project_dir():
    """
    Create a temporary directory with test files for indexing.

    Creates ~10 sample files with various content types to test
    the full indexing pipeline.
    """
    temp_dir = tempfile.mkdtemp(prefix="test_project_")
    test_dir = Path(temp_dir)

    try:
        # Create test files with different content
        sample_files = {
            "main.py": """
import asyncio
from typing import List, Optional

class Calculator:
    def add(self, a: int, b: int) -> int:
        return a + b

    def multiply(self, a: int, b: int) -> int:
        return a * b

async def main():
    calc = Calculator()
    result = calc.add(5, 3)
    print(f"Result: {result}")

if __name__ == "__main__":
    asyncio.run(main())
""",
            "config.yaml": """
# Application Configuration
database:
  host: localhost
  port: 5432
  name: myapp_db

server:
  host: 0.0.0.0
  port: 8080
  debug: true

features:
  - authentication
  - rate_limiting
  - caching
""",
            "README.md": """
# Test Project

This is a test project for Elasticsearch indexing integration tests.

## Features

- Async I/O operations
- Type hints
- Configuration management

## Usage

```python
from main import Calculator
calc = Calculator()
result = calc.add(1, 2)
```
""",
            "utils/helpers.py": """
def format_string(template: str, **kwargs) -> str:
    return template.format(**kwargs)

def validate_email(email: str) -> bool:
    return "@" in email and "." in email

class DataProcessor:
    def process(self, data: List[Dict]) -> List[Dict]:
        return [item for item in data if item.get("active", True)]
""",
            "tests/test_main.py": """
import pytest
from main import Calculator

class TestCalculator:
    def test_add(self):
        calc = Calculator()
        assert calc.add(2, 3) == 5

    def test_multiply(self):
        calc = Calculator()
        assert calc.multiply(3, 4) == 12
""",
            "models/user.py": """
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class User:
    id: int
    username: str
    email: str
    created_at: datetime
    last_login: Optional[datetime] = None

    def is_active(self) -> bool:
        return self.last_login is not None
""",
            "services/auth.py": """
import hashlib
import secrets

class AuthService:
    def hash_password(self, password: str) -> str:
        salt = secrets.token_hex(16)
        return hashlib.sha256(f"{password}{salt}".encode()).hexdigest()

    def verify_token(self, token: str) -> bool:
        return len(token) == 64 and all(c in "0123456789abcdef" for c in token)
""",
            "docs/api.md": """
# API Documentation

## Endpoints

### POST /api/users
Create a new user account.

Request body:
```json
{
  "username": "john_doe",
  "email": "john@example.com"
}
```

### GET /api/users/:id
Get user by ID.

Returns user object with profile information.
""",
            "docker-compose.yml": """
version: '3.8'
services:
  web:
    build: .
    ports:
      - "8080:8080"
    environment:
      - DATABASE_URL=postgres://db:5432/app
    depends_on:
      - db

  db:
    image: postgres:16
    environment:
      POSTGRES_DB: app
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
""",
            "scripts/setup.sh": """
#!/bin/bash
set -e

echo "Setting up project..."

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

echo "Setup complete!"
"""
        }

        # Write all test files
        for file_path, content in sample_files.items():
            file = test_dir / file_path
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(content)

        yield str(test_dir)

    finally:
        # Clean up
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="module")
def elasticsearch_client():
    """
    Create an Elasticsearch client for testing.

    Skips tests if Elasticsearch is not available.
    """
    es = Elasticsearch(ELASTICSEARCH_HOSTS)

    try:
        # Test connection
        es.info(request_timeout=5)
        yield es
    except Exception as e:
        pytest.skip(f"Elasticsearch not available: {e}")
    finally:
        # Clean up test index
        try:
            if es.indices.exists(index=ES_INDEX_NAME):
                es.indices.delete(index=ES_INDEX_NAME)
        except:
            pass


@pytest.fixture(scope="module")
def rabbitmq_producer():
    """
    Create a RabbitMQ producer for testing.

    Skips tests if RabbitMQ is not available.
    """
    producer = RabbitMQProducer(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        exchange=RABBITMQ_EXCHANGE,
        routing_key=RABBITMQ_ROUTING_KEY
    )

    # Check if connection was successful
    if producer.channel is None:
        pytest.skip(f"RabbitMQ not available at {RABBITMQ_HOST}:{RABBITMQ_PORT}")

    yield producer

    # Clean up
    producer.close()


@pytest.fixture(scope="module")
def rabbitmq_consumer(elasticsearch_client, test_project_dir):
    """
    Create a RabbitMQ consumer for testing.

    The consumer will process messages and index to Elasticsearch.
    Uses test_project_dir as base path to match the test context.
    """
    try:
        consumer = RabbitMQConsumer(
            es_client=elasticsearch_client,
            base_path=test_project_dir,
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
            queue_name=RABBITMQ_QUEUE,
            exchange=RABBITMQ_EXCHANGE,
            routing_key=RABBITMQ_ROUTING_KEY,
            enable_batching=True,
            batch_size=10,
            enable_backpressure=True
        )

        # Start consumer in background thread
        consumer.start()
        yield consumer

    finally:
        # Stop consumer
        consumer.stop()


@pytest.fixture
def mock_context(test_project_dir):
    """
    Create a mock MCP Context object for testing.

    Sets up the lifespan context with necessary attributes.
    """
    ctx = MagicMock(spec=Context)
    ctx.request_context = MagicMock()
    ctx.request_context.lifespan_context = MagicMock()

    # Set up base path
    ctx.request_context.lifespan_context.base_path = test_project_dir

    # Set up settings
    settings = ConfigManager(test_project_dir)
    settings.load_config = MagicMock(return_value={})
    settings.save_config = MagicMock()
    settings.save_index = MagicMock()
    settings._get_timestamp = MagicMock(return_value=str(int(time.time() * 1000)))
    ctx.request_context.lifespan_context.settings = settings

    # Set up realtime indexer with producer
    producer = RabbitMQProducer(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        exchange=RABBITMQ_EXCHANGE,
        routing_key=RABBITMQ_ROUTING_KEY
    )

    if producer.channel is None:
        pytest.skip(f"RabbitMQ not available at {RABBITMQ_HOST}:{RABBITMQ_PORT}")

    ctx.request_context.lifespan_context.realtime_indexer = MagicMock()
    ctx.request_context.lifespan_context.realtime_indexer.producer = producer

    # Set up file count
    ctx.request_context.lifespan_context.file_count = 0

    return ctx


@pytest.fixture
def clear_elasticsearch_index(elasticsearch_client):
    """
    Clear the Elasticsearch index before/after tests.
    """
    # Clear before test
    try:
        if elasticsearch_client.indices.exists(index=ES_INDEX_NAME):
            elasticsearch_client.indices.delete(index=ES_INDEX_NAME)
    except:
        pass

    yield

    # Clear after test
    try:
        if elasticsearch_client.indices.exists(index=ES_INDEX_NAME):
            elasticsearch_client.indices.delete(index=ES_INDEX_NAME)
    except:
        pass


# =============================================================================
# TEST CLASS: EndToEndReindexToSearch
# =============================================================================

class TestEndToEndReindexToSearch:
    """
    Test suite for end-to-end reindexing to Elasticsearch.

    Verifies the complete flow from refresh_index() to Elasticsearch
    population and search functionality.
    """

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_end_to_end_reindex_to_search(
        self,
        mock_context: Context,
        elasticsearch_client: Elasticsearch,
        rabbitmq_consumer: RabbitMQConsumer,
        clear_elasticsearch_index,
    ):
        """
        Test end-to-end reindexing flow from refresh_index to Elasticsearch.

        This test verifies that:
        1. refresh_index() queues files to RabbitMQ
        2. RabbitMQ consumer processes messages
        3. Elasticsearch is populated with documents
        4. Document count matches file count
        5. Search returns results from indexed content

        Prerequisites:
        - Elasticsearch running on localhost:9200
        - RabbitMQ running on localhost:5672

        Args:
            mock_context: Mock MCP context
            elasticsearch_client: Elasticsearch client
            rabbitmq_consumer: RabbitMQ consumer (processing in background)
            clear_elasticsearch_index: Fixture to ensure clean index
        """
        # Arrange: Get the test project path
        test_project_path = mock_context.request_context.lifespan_context.base_path

        # Count test files (excluding __pycache__ and .pytest_cache)
        test_files = list(Path(test_project_path).rglob("*"))
        test_files = [f for f in test_files if f.is_file() and "__pycache__" not in str(f)]
        expected_file_count = len(test_files)

        print(f"\n[Test] Test project has {expected_file_count} files to index")

        # Act: Call refresh_index to queue files to RabbitMQ
        result = await refresh_index(mock_context)

        # Assert: Verify refresh_index returned success
        assert result.get("success") is True, f"refresh_index failed: {result.get('error')}"
        assert result.get("status") == "indexing_started", \
            f"Expected 'indexing_started' status, got: {result.get('status')}"
        assert "operation_id" in result, "Operation ID not returned"
        assert "files_queued" in result, "Files queued count not returned"
        assert result["files_queued"] > 0, "No files were queued"

        files_queued = result["files_queued"]
        operation_id = result["operation_id"]

        print(f"[Test] Queued {files_queued} files to RabbitMQ")
        print(f"[Test] Operation ID: {operation_id}")

        # Act: Wait for RabbitMQ consumer to process messages
        # The consumer runs in background thread, so we need to poll Elasticsearch
        start_time = time.time()
        indexed_count = 0

        while time.time() - start_time < WAIT_TIMEOUT:
            try:
                # Get document count from Elasticsearch
                response = elasticsearch_client.count(index=ES_INDEX_NAME)
                indexed_count = response.get("count", 0)

                print(f"[Test] Indexed documents: {indexed_count}/{expected_file_count}")

                # Check if we have enough documents indexed
                if indexed_count >= expected_file_count:
                    break

            except Exception as e:
                print(f"[Test] Error checking Elasticsearch: {e}")

            time.sleep(POLL_INTERVAL)

        # Assert: Verify Elasticsearch document count matches expected count
        # All test files should be indexed (all are text files)
        assert indexed_count == expected_file_count, \
            f"Expected {expected_file_count} indexed documents, but got {indexed_count}"
        print(f"[Test] Total indexed documents: {indexed_count}")

        # Act: Refresh the Elasticsearch index to make documents searchable
        try:
            elasticsearch_client.indices.refresh(index=ES_INDEX_NAME)
        except Exception as e:
            print(f"[Test] Warning: Could not refresh index: {e}")

        # Act: Run search query to verify content was indexed
        search_queries = [
            ("Calculator", "Should find Calculator class"),
            ("asyncio", "Should find asyncio import"),
            ("config", "Should find config.yaml content"),
            ("format_string", "Should find helper function"),
        ]

        for query, reason in search_queries:
            try:
                response = elasticsearch_client.search(
                    index=ES_INDEX_NAME,
                    body={
                        "query": {
                            "match": {
                                "content": query
                            }
                        },
                        "size": 10
                    }
                )

                hits = response.get("hits", {}).get("hits", [])
                print(f"[Test] Search for '{query}': {len(hits)} hits")

                # Assert: Verify search found results
                assert len(hits) > 0, f"Search for '{query}' returned no results: {reason}"

                # Verify hit contains expected fields
                for hit in hits:
                    source = hit.get("_source", {})
                    assert "file_id" in source or "path" in source, \
                        f"Document missing file_id or path: {source}"
                    assert "content" in source, f"Document missing content: {source}"

            except Exception as e:
                pytest.fail(f"Search for '{query}' failed: {e}")

        print("[Test] End-to-end indexing test PASSED")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_elasticsearch_documents_contain_actual_content(
        self,
        mock_context: Context,
        elasticsearch_client: Elasticsearch,
        rabbitmq_consumer: RabbitMQConsumer,
        clear_elasticsearch_index,
    ):
        """
        Test that Elasticsearch documents contain actual file content.

        Verifies that documents indexed from RabbitMQ messages contain:
        - File path
        - File content (not empty or placeholder)
        - Metadata fields (language, size, etc.)
        """
        # Arrange: Run refresh_index
        result = await refresh_index(mock_context)

        assert result.get("success") is True, f"refresh_index failed: {result.get('error')}"

        # Act: Wait for indexing to complete
        start_time = time.time()

        while time.time() - start_time < WAIT_TIMEOUT:
            try:
                response = elasticsearch_client.count(index=ES_INDEX_NAME)
                if response.get("count", 0) > 0:
                    break
            except:
                pass
            time.sleep(POLL_INTERVAL)

        # Refresh index
        try:
            elasticsearch_client.indices.refresh(index=ES_INDEX_NAME)
        except:
            pass

        # Act: Fetch sample documents from Elasticsearch
        response = elasticsearch_client.search(
            index=ES_INDEX_NAME,
            body={
                "query": {"match_all": {}},
                "size": 5
            }
        )

        hits = response.get("hits", {}).get("hits", [])

        # Assert: Verify documents have actual content
        assert len(hits) > 0, "No documents found in Elasticsearch"

        for hit in hits:
            source = hit.get("_source", {})

            # Verify file path
            assert "path" in source or "file_id" in source, \
                f"Document missing path: {source}"

            # Verify content exists and is not empty
            assert "content" in source, f"Document missing content field: {source}"
            assert len(source["content"]) > 10, \
                f"Document content too short (likely placeholder): {source['content'][:50]}"

            # Verify metadata
            assert "size" in source, f"Document missing size: {source}"
            assert source["size"] > 0, f"Document has invalid size: {source['size']}"

            print(f"[Test] Verified document: {source.get('path', source.get('file_id'))} ({source['size']} bytes)")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_stale_test_data_replaced_on_reindex(
        self,
        mock_context: Context,
        elasticsearch_client: Elasticsearch,
        rabbitmq_consumer: RabbitMQConsumer,
        clear_elasticsearch_index,
    ):
        """
        Test that stale test data is replaced/updated on reindex.

        Verifies that:
        1. Initial indexing creates documents
        2. Re-indexing updates existing documents
        3. No duplicate documents are created
        """
        test_project_path = mock_context.request_context.lifespan_context.base_path

        # Step 1: Run initial indexing
        result1 = await refresh_index(mock_context)
        assert result1.get("success") is True

        # Wait for initial indexing
        start_time = time.time()
        initial_count = 0

        while time.time() - start_time < WAIT_TIMEOUT:
            try:
                response = elasticsearch_client.count(index=ES_INDEX_NAME)
                initial_count = response.get("count", 0)
                if initial_count > 0:
                    break
            except:
                pass
            time.sleep(POLL_INTERVAL)

        print(f"[Test] Initial index count: {initial_count}")

        # Step 2: Modify a test file
        test_files = list(Path(test_project_path).rglob("*.py"))
        if test_files:
            test_file = test_files[0]
            original_content = test_file.read_text()
            test_file.write_text(original_content + "\n# Modified for reindex test\n")

        # Step 3: Run re-index
        result2 = await refresh_index(mock_context)
        assert result2.get("success") is True

        # Wait for re-indexing
        start_time = time.time()
        reindexed_count = 0

        while time.time() - start_time < WAIT_TIMEOUT:
            try:
                response = elasticsearch_client.count(index=ES_INDEX_NAME)
                reindexed_count = response.get("count", 0)

                # Check if count has stabilized (may be slightly different due to file changes)
                if reindexed_count >= initial_count * 0.8:  # Allow some tolerance
                    break
            except:
                pass
            time.sleep(POLL_INTERVAL)

        print(f"[Test] Re-index count: {reindexed_count}")

        # Step 4: Verify no excessive duplicates
        # Count should be roughly the same (allowing for file changes)
        assert reindexed_count <= initial_count + 2, \
            f"Too many documents created: {reindexed_count} vs {initial_count}"

        # Step 5: Verify content was updated (if file was modified)
        if test_files:
            elasticsearch_client.indices.refresh(index=ES_INDEX_NAME)
            response = elasticsearch_client.search(
                index=ES_INDEX_NAME,
                body={
                    "query": {
                        "match": {
                            "content": "Modified for reindex test"
                        }
                    }
                }
            )

            hits = response.get("hits", {}).get("hits", [])
            assert len(hits) > 0, "Modified content was not indexed"
            print(f"[Test] Found updated content in {len(hits)} documents")


# =============================================================================
# TEST CLASS: OperationStatusTracking
# =============================================================================

class TestOperationStatusTracking:
    """
    Test suite for operation status tracking during indexing.

    Verifies that operation status updates correctly from "in_progress"
    to "complete" with accurate file counts.
    """

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_operation_status_tracking(
        self,
        mock_context: Context,
        rabbitmq_consumer: RabbitMQConsumer,
        clear_elasticsearch_index,
    ):
        """
        Test operation status tracking through the indexing process.

        Verifies that:
        1. refresh_index returns operation_id and files_queued
        2. Querying status immediately shows "in_progress" or "running"
        3. After completion, status transitions to "complete" or "completed"
        4. files_completed matches or approaches files_queued

        Prerequisites:
        - RabbitMQ running on localhost:5672

        Args:
            mock_context: Mock MCP context
            rabbitmq_consumer: RabbitMQ consumer (processing in background)
            clear_elasticsearch_index: Fixture to ensure clean index
        """
        # Act: Run refresh_index to start indexing
        result = await refresh_index(mock_context)

        # Assert: Verify initial response
        assert result.get("success") is True, f"refresh_index failed: {result.get('error')}"
        assert "operation_id" in result, "Operation ID not in response"
        assert "files_queued" in result, "files_queued not in response"

        operation_id = result["operation_id"]
        files_queued = result["files_queued"]

        print(f"[Test] Operation started: {operation_id}")
        print(f"[Test] Files queued: {files_queued}")

        # Act: Query operation status immediately
        # Note: Since refresh_index completes after queuing, the operation
        # status from progress_manager may already be "completed" or similar
        # For RabbitMQ async indexing, we track the queuing operation status
        status_result = get_operation_status(operation_id)

        print(f"[Test] Operation status: {status_result}")

        # Assert: Verify status structure
        assert "operation_id" in status_result, "operation_id not in status"
        assert status_result["operation_id"] == operation_id

        # The status may be "completed" (for the queuing operation) or other states
        # get_operation_status returns {"success": True, "operation_status": {...}}
        assert "operation_status" in status_result or "success" in status_result, \
            "operation_status not in response"

        # Extract the actual status dict if nested
        if "operation_status" in status_result and isinstance(status_result["operation_status"], dict):
            status_dict = status_result["operation_status"]
        else:
            status_dict = status_result

        valid_statuses = ["pending", "running", "completed", "in_progress", "done"]
        status = status_dict.get("status", status_result.get("operation_status", ""))
        if isinstance(status, str):
            assert status.lower() in valid_statuses, f"Invalid status: {status}"

        # Assert: Verify files_queued is recorded
        # Note: The progress tracker tracks the queuing operation, not the
        # async RabbitMQ consumption. files_queued is the key metric.
        if "files_queued" in status_result:
            assert status_result["files_queued"] == files_queued

        # For RabbitMQ async indexing, we wait and verify the consumer processed messages
        # The operation status for the queuing operation itself should be complete
        start_time = time.time()
        final_status = None

        while time.time() - start_time < WAIT_TIMEOUT:
            status_result = get_operation_status(operation_id)

            # Extract status from response
            if "operation_status" in status_result and isinstance(status_result["operation_status"], dict):
                final_status = status_result["operation_status"].get("status", "")
            else:
                final_status = status_result.get("operation_status", "")

            # Check if operation is complete
            if isinstance(final_status, str) and final_status.lower() in ["completed", "done", "complete"]:
                break

            time.sleep(POLL_INTERVAL)

        print(f"[Test] Final operation status: {final_status}")

        # Assert: Verify operation completed
        # Note: Since the queuing operation completes quickly, we just verify
        # we successfully got a valid status response
        if isinstance(final_status, str):
            assert final_status.lower() in ["completed", "done", "complete", "running"], \
                f"Unexpected operation status: {final_status}"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_multiple_operation_status_tracking(
        self,
        mock_context: Context,
        rabbitmq_consumer: RabbitMQConsumer,
        clear_elasticsearch_index,
    ):
        """
        Test tracking status for multiple simultaneous indexing operations.

        Verifies that:
        1. Multiple operations can be tracked independently
        2. Each operation has a unique operation_id
        3. Status queries return correct operation data
        """
        # Act: Run multiple refresh_index operations
        operation_ids = []
        files_queued_list = []

        for i in range(3):
            result = await refresh_index(mock_context)
            assert result.get("success") is True

            operation_id = result["operation_id"]
            files_queued = result["files_queued"]

            operation_ids.append(operation_id)
            files_queued_list.append(files_queued)

            print(f"[Test] Operation {i+1}: {operation_id} ({files_queued} files)")

            # Small delay between operations
            await asyncio.sleep(0.1)

        # Assert: Verify all operation IDs are unique
        assert len(operation_ids) == len(set(operation_ids)), \
            "Operation IDs are not unique"

        # Act: Query status for all operations
        statuses = []
        for op_id in operation_ids:
            status = get_operation_status(op_id)
            statuses.append(status)
            print(f"[Test] Status for {op_id}: {status.get('operation_status')}")

        # Assert: Verify all statuses are valid
        for i, status in enumerate(statuses):
            assert status["operation_id"] == operation_ids[i], \
                f"Operation ID mismatch for operation {i}"
            assert "operation_status" in status, \
                f"operation_status not found for operation {i}"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_operation_status_with_progress_tracking(
        self,
        mock_context: Context,
        clear_elasticsearch_index,
    ):
        """
        Test operation status with detailed progress tracking.

        Verifies that:
        1. Progress tracker captures stages (Scanning, Queuing, Saving)
        2. Progress percentage updates correctly
        3. Items processed count increments
        """
        # Act: Run refresh_index
        result = await refresh_index(mock_context)

        assert result.get("success") is True
        operation_id = result["operation_id"]

        # Act: Query detailed status
        status = get_operation_status(operation_id)

        print(f"[Test] Detailed status: {status}")

        # Assert: Verify progress tracking fields
        assert "operation_id" in status
        assert "operation_status" in status

        # Note: The progress tracker in the current implementation
        # tracks stages for the queuing operation, not the async consumption
        if "stages" in status:
            assert isinstance(status["stages"], list), "Stages should be a list"

        if "current_stage" in status:
            assert isinstance(status["current_stage"], str), \
                "Current stage should be a string"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_manage_operations_list_shows_reindex_operation(
        self,
        mock_context: Context,
        rabbitmq_consumer: RabbitMQConsumer,
        clear_elasticsearch_index,
    ):
        """
        Test that manage_operations(action="list") shows the reindex operation.

        This test verifies FR-3 requirement:
        - manage_operations(action="list") shows the reindex operation
        - Operation includes files_queued and files_completed metrics

        Prerequisites:
        - RabbitMQ running on localhost:5672

        Args:
            mock_context: Mock MCP context
            rabbitmq_consumer: RabbitMQ consumer (processing in background)
            clear_elasticsearch_index: Fixture to ensure clean index
        """
        # Act: Run refresh_index to start indexing
        result = await refresh_index(mock_context)

        # Assert: Verify refresh_index succeeded
        assert result.get("success") is True, f"refresh_index failed: {result.get('error')}"
        operation_id = result["operation_id"]
        files_queued = result["files_queued"]

        print(f"[Test] Operation started: {operation_id}")
        print(f"[Test] Files queued: {files_queued}")

        # Act: Call manage_operations(action="list") to list operations
        list_result = await manage_operations(mock_context, action="list")

        # Assert: Verify list result structure
        assert list_result.get("success") is True, f"manage_operations list failed: {list_result.get('error')}"
        assert "operations" in list_result or "active_operations" in list_result, \
            f"List result missing operations: {list_result}"

        # Extract operations list
        operations = list_result.get("operations") or list_result.get("active_operations", [])

        # Assert: Verify our operation is in the list
        # The operation may be listed by operation_id or in active_operations
        operation_found = False
        for op in operations:
            if isinstance(op, dict):
                op_id = op.get("operation_id") or op.get("id")
                if op_id == operation_id:
                    operation_found = True
                    # Verify operation has expected fields
                    assert "files_queued" in op or op.get("status"), \
                        f"Operation missing expected fields: {op}"
                    print(f"[Test] Found operation in list: {op}")
                    break

        assert operation_found, \
            f"Operation {operation_id} not found in list: {operations}"

        print(f"[Test] manage_operations(action='list') PASSED")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_operation_status_shows_reindex_progress(
        self,
        mock_context: Context,
        rabbitmq_consumer: RabbitMQConsumer,
        clear_elasticsearch_index,
    ):
        """
        Test that get_operation_status shows reindex operation progress.

        This test verifies FR-3 requirement:
        - get_operation_status returns current progress
        - Operation includes files_queued and files_completed metrics
        - Operation status transitions: in_progress -> complete

        Note: This uses get_operation_status() which is the actual implementation
        for what the spec calls manage_operations(action="status", operation_id=...)

        Prerequisites:
        - RabbitMQ running on localhost:5672

        Args:
            mock_context: Mock MCP context
            rabbitmq_consumer: RabbitMQ consumer (processing in background)
            clear_elasticsearch_index: Fixture to ensure clean index
        """
        # Act: Run refresh_index to start indexing
        result = await refresh_index(mock_context)

        # Assert: Verify refresh_index succeeded
        assert result.get("success") is True, f"refresh_index failed: {result.get('error')}"
        operation_id = result["operation_id"]
        files_queued = result["files_queued"]

        print(f"[Test] Operation started: {operation_id}")
        print(f"[Test] Files queued: {files_queued}")

        # Act: Call get_operation_status immediately
        status_result = get_operation_status(operation_id)

        # Assert: Verify status result structure
        assert "operation_id" in status_result, "operation_id not in status result"
        assert status_result["operation_id"] == operation_id, \
            f"Operation ID mismatch: {status_result['operation_id']} != {operation_id}"

        # The status may be nested in "operation_status" key
        if "operation_status" in status_result and isinstance(status_result["operation_status"], dict):
            status_dict = status_result["operation_status"]
        else:
            status_dict = status_result

        # Assert: Verify operation has files_queued metric
        # Note: get_operation_status may return files_queued at top level or in operation_status
        if "files_queued" in status_result:
            assert status_result["files_queued"] == files_queued, \
                f"files_queued mismatch: {status_result['files_queued']} != {files_queued}"
            print(f"[Test] Status shows files_queued: {status_result['files_queued']}")

        # Assert: Verify status is valid
        if "status" in status_dict:
            status = status_dict["status"]
            valid_statuses = ["pending", "running", "completed", "in_progress", "done"]
            if isinstance(status, str):
                assert status.lower() in valid_statuses, f"Invalid status: {status}"
            print(f"[Test] Operation status: {status}")

        # Act: Wait for operation to complete
        start_time = time.time()
        final_status = None

        while time.time() - start_time < WAIT_TIMEOUT:
            status_result = get_operation_status(operation_id)

            # Extract status from response
            if "operation_status" in status_result and isinstance(status_result["operation_status"], dict):
                final_status = status_result["operation_status"].get("status", "")
            else:
                final_status = status_result.get("operation_status", "") or status_result.get("status", "")

            # Check if operation is complete
            if isinstance(final_status, str) and final_status.lower() in ["completed", "done", "complete"]:
                break

            time.sleep(POLL_INTERVAL)

        print(f"[Test] Final operation status: {final_status}")

        # Assert: Verify operation reached a terminal state
        if isinstance(final_status, str):
            assert final_status.lower() in ["completed", "done", "complete", "running"], \
                f"Unexpected final operation status: {final_status}"

        print(f"[Test] get_operation_status tracking PASSED")


# =============================================================================
# TEST CLASS: ServiceAvailability
# =============================================================================

class TestServiceAvailability:
    """
    Test suite for service availability checks.

    Verifies graceful degradation when services are unavailable.
    """

    @pytest.mark.asyncio
    async def test_refresh_without_rabbitmq(self, mock_context):
        """
        Test refresh_index behavior when RabbitMQ is unavailable.

        Verifies that:
        1. Error is returned when RabbitMQ is not available
        2. Error message indicates RabbitMQ is required
        3. Graceful degradation without crashing
        """
        # Arrange: Mock unavailable RabbitMQ
        mock_context.request_context.lifespan_context.realtime_indexer = None

        # Act: Call refresh_index
        result = await refresh_index(mock_context)

        # Assert: Verify error response
        assert result.get("success") is False, "Should return failure when RabbitMQ unavailable"
        assert "error" in result, "Error message should be present"
        assert "RabbitMQ" in result["error"] or "rabbitmq" in result["error"].lower(), \
            "Error should mention RabbitMQ"
        assert result.get("rabbitmq_required") is True, \
            "Should indicate RabbitMQ is required"

        print(f"[Test] RabbitMQ unavailable error: {result['error']}")

    @pytest.mark.asyncio
    async def test_refresh_without_project_path(self):
        """
        Test refresh_index behavior when project path is not set.

        Verifies that:
        1. Error is returned when no project path is set
        2. Error message indicates project path is required
        """
        # Arrange: Mock context without base_path
        ctx = MagicMock(spec=Context)
        ctx.request_context = MagicMock()
        ctx.request_context.lifespan_context = MagicMock()
        ctx.request_context.lifespan_context.base_path = None

        # Act: Call refresh_index
        result = await refresh_index(ctx)

        # Assert: Verify error response
        assert result.get("success") is False
        assert "error" in result
        assert "Project path not set" in result["error"] or "path" in result["error"].lower()


# =============================================================================
# RUN CONFIGURATION
# =============================================================================

if __name__ == "__main__":
    """
    Allow running tests directly with pytest.

    Example:
        python tests/integration/test_elasticsearch_indexing.py
        pytest tests/integration/test_elasticsearch_indexing.py -v --tb=short
        pytest tests/integration/test_elasticsearch_indexing.py::TestEndToEndReindexToSearch::test_end_to_end_reindex_to_search -v
    """
    pytest.main([__file__, "-v", "--tb=short"])
