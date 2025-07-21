"""
Shared constants for the Code Index MCP server.
"""

# Directory and file names
GLOBAL_CONFIG_FILE = "~/.code_indexer_mcp_global_config.json" # New global config file
SETTINGS_DIR = "code_indexer"
PERSISTENT_SETTINGS_DIR = ".code_indexer_data"
CONFIG_FILE = "config.json"
INDEX_FILE = "file_index.pickle"
CACHE_FILE = "content_cache.pickle"
METADATA_FILE = "file_metadata.pickle"

# Elasticsearch constants
ES_HOST = "localhost"
ES_PORT = 9200
ES_INDEX_NAME = "code_index"

# RabbitMQ constants
RABBITMQ_HOST = "localhost"
RABBITMQ_PORT = 5672
RABBITMQ_QUEUE_NAME = "indexing_queue"
RABBITMQ_EXCHANGE_NAME = "indexing_exchange"
RABBITMQ_ROUTING_KEY = "file_changes"
