"""
Shared constants for the Code Index MCP server.

This module contains all magic numbers, configuration defaults, and
constant values used throughout the codebase. Each constant includes
documentation explaining its purpose and usage.
"""

# ============================================================================
# Directory and File Names
# ============================================================================

"""Global configuration file path for user-level settings."""
GLOBAL_CONFIG_FILE = "~/.code_indexer_mcp_global_config.json"

"""Settings directory name within project root."""
SETTINGS_DIR = "code_indexer"

"""Persistent data directory for project-specific data."""
PERSISTENT_SETTINGS_DIR = ".code_indexer_data"

"""Configuration file name."""
CONFIG_FILE = "config.json"

"""File index pickle file name."""
INDEX_FILE = "file_index.pickle"

"""Content cache pickle file name."""
CACHE_FILE = "content_cache.pickle"

"""File metadata pickle file name."""
METADATA_FILE = "file_metadata.pickle"

# ============================================================================
# Elasticsearch Configuration
# ============================================================================

"""Default Elasticsearch host."""
ES_HOST = "localhost"

"""Default Elasticsearch port."""
ES_PORT = 9200

"""Default Elasticsearch index name."""
ES_INDEX_NAME = "code_index"

"""Default Elasticsearch URL."""
ES_DEFAULT_URL = "http://localhost:9200"

# ============================================================================
# RabbitMQ Configuration
# ============================================================================

"""Default RabbitMQ host."""
RABBITMQ_HOST = "localhost"

"""Default RabbitMQ port."""
RABBITMQ_PORT = 5672

"""Queue name for file indexing operations."""
RABBITMQ_QUEUE_NAME = "indexing_queue"

"""Exchange name for message routing."""
RABBITMQ_EXCHANGE_NAME = "indexing_exchange"

"""Routing key for file change messages."""
RABBITMQ_ROUTING_KEY = "file_changes"

# ============================================================================
# File Size Limits (in bytes)
# ============================================================================

"""Default maximum file size for indexing (5MB)."""
DEFAULT_MAX_FILE_SIZE = 5242880

"""Maximum size for Python/JavaScript files (1MB)."""
TYPE_SPECIFIC_MAX_SIZE_DEFAULT = 1048576

"""Maximum size for JSON/YAML/XML files (512KB)."""
TYPE_SPECIFIC_MAX_SIZE_SMALL = 524288

"""No file size limit (infinity)."""
NO_FILE_SIZE_LIMIT = float('inf')

"""Maximum file size for large files (1GB)."""
LARGE_FILE_MAX_SIZE = 1073741824

# ============================================================================
# Directory Limits
# ============================================================================

"""Default maximum files per directory (1000)."""
DEFAULT_MAX_FILES_PER_DIRECTORY = 1000

"""Maximum subdirectories per directory (100)."""
DEFAULT_MAX_SUBDIRECTORIES_PER_DIRECTORY = 100

"""Large directory threshold - maximum files (10000)."""
LARGE_MAX_FILES_PER_DIRECTORY = 10000

"""Large directory threshold - maximum subdirectories (1000)."""
LARGE_MAX_SUBDIRECTORIES_PER_DIRECTORY = 1000

# ============================================================================
# Search Result Limits
# ============================================================================

"""Default maximum search results (1000)."""
DEFAULT_MAX_SEARCH_RESULTS = 1000

"""Maximum search results for Elasticsearch (10000)."""
ES_MAX_SEARCH_RESULTS = 10000

"""Maximum search results for PostgreSQL (5000)."""
POSTGRESQL_MAX_SEARCH_RESULTS = 5000

"""Default file versions to retrieve (100)."""
DEFAULT_FILE_VERSIONS_LIMIT = 100

"""Recent operations limit for monitoring (10)."""
RECENT_OPERATIONS_LIMIT = 10

# ============================================================================
# Cache and Timeout Settings (in seconds)
# ============================================================================

"""Default cache TTL for search results (300 seconds = 5 minutes)."""
DEFAULT_CACHE_TTL = 300

"""Health check cache timeout (300 seconds = 5 minutes)."""
HEALTH_CHECK_CACHE_TIMEOUT = 300

"""Cleanup interval for background tasks (300 seconds = 5 minutes)."""
DEFAULT_CLEANUP_INTERVAL = 300

"""Short connection timeout (3 seconds)."""
SHORT_CONNECTION_TIMEOUT = 3

"""Default connection timeout (5 seconds)."""
DEFAULT_CONNECTION_TIMEOUT = 5

"""Medium connection timeout (10 seconds)."""
MEDIUM_CONNECTION_TIMEOUT = 10

"""Long connection timeout (30 seconds)."""
LONG_CONNECTION_TIMEOUT = 30

"""Elasticsearch operation timeout (60 seconds)."""
ES_OPERATION_TIMEOUT = 60

"""Elasticsearch connection timeout (300 seconds = 5 minutes)."""
ES_CONNECTION_TIMEOUT = 300

"""Zoekt indexing timeout (300 seconds = 5 minutes)."""
ZOEKT_INDEXING_TIMEOUT = 300

"""Zoekt search timeout (30 seconds)."""
ZOEKT_SEARCH_TIMEOUT = 30

"""Default Elasticsearch client timeout (30 seconds)."""
ES_CLIENT_TIMEOUT = 30

"""Elasticsearch connection test timeout (2 seconds)."""
ES_CONNECTION_TEST_TIMEOUT = 2

"""Thread join timeout (5 seconds)."""
THREAD_JOIN_TIMEOUT = 5

# ============================================================================
# Cache Sizes
# ============================================================================

"""Default search cache max size (128 entries)."""
DEFAULT_SEARCH_CACHE_MAX_SIZE = 128

"""Maximum loaded files in memory (100)."""
MAX_LOADED_FILES_IN_MEMORY = 100

# ============================================================================
# Pattern and Query Limits
# ============================================================================

"""Maximum pattern length to prevent DoS (1000 characters)."""
MAX_PATTERN_LENGTH = 1000

"""Maximum wildcard count in pattern (50)."""
MAX_WILDCARD_COUNT = 50

"""Maximum regex alternations (20)."""
MAX_REGEX_ALTERNATIONS = 20

"""Maximum query length for search (1000 characters)."""
MAX_QUERY_LENGTH = 1000

"""Minimum search limit value (1)."""
MIN_SEARCH_LIMIT = 1

"""Maximum search limit value (1000)."""
MAX_SEARCH_LIMIT = 1000

# ============================================================================
# Memory Limits (in MB)
# ============================================================================

"""Soft memory limit for profiler (512MB)."""
MEMORY_PROFILER_SOFT_LIMIT_MB = 512.0

"""Hard memory limit for profiler (1024MB = 1GB)."""
MEMORY_PROFILER_HARD_LIMIT_MB = 1024.0

"""Soft memory limit from config (8192MB = 8GB)."""
CONFIG_SOFT_LIMIT_MB = 8192

"""Hard memory limit from config (16384MB = 16GB)."""
CONFIG_HARD_LIMIT_MB = 16384

"""Elasticsearch heap memory limit (4096MB = 4GB)."""
ES_HEAP_MEMORY_LIMIT_MB = 4096

# ============================================================================
# Elasticsearch Index Settings
# ============================================================================

"""Number of shards for Elasticsearch index (3)."""
ES_INDEX_NUMBER_OF_SHARDS = 3

"""Number of replicas for Elasticsearch index (0 for single-node clusters)."""
ES_INDEX_NUMBER_OF_REPLICAS = 0

"""Index refresh interval in seconds (1s)."""
ES_INDEX_REFRESH_INTERVAL = "1s"

"""Minimum n-gram size for code analyzer (2)."""
ES_CODE_ANALYZER_MIN_NGRAM = 2

"""Maximum n-gram size for code analyzer (3)."""
ES_CODE_ANALYZER_MAX_NGRAM = 3

# ============================================================================
# Worker/Thread Settings
# ============================================================================

"""Default maximum workers for parallel processing (4)."""
DEFAULT_MAX_WORKERS = 4

"""Elasticsearch installer timeout (300 seconds = 5 minutes)."""
ES_INSTALLER_TIMEOUT = 300

# ============================================================================
# Retry Settings
# ============================================================================

"""Default maximum retries for connection attempts (3)."""
DEFAULT_MAX_RETRIES = 3

"""Default wait time for completion (2 seconds)."""
DEFAULT_WAIT_FOR_COMPLETION = 2

# ============================================================================
# Monitoring and Cleanup
# ============================================================================

"""Max age for search operations before cleanup (24 hours)."""
SEARCH_OPERATIONS_MAX_AGE_HOURS = 24.0

"""Max age hours in seconds (24 * 3600)."""
MAX_AGE_SECONDS = 24.0 * 3600
