"""
Elasticsearch-based storage backend for full-text search.
"""

import logging
import re # Import the re module
from typing import Any, Dict, Optional, List, Tuple
from abc import ABC, abstractmethod

# Assuming elasticsearch-py client
from elasticsearch import Elasticsearch, NotFoundError, ConnectionError

from .storage_interface import SearchInterface

logger = logging.getLogger(__name__)

class ElasticsearchSearch(SearchInterface):
    """
    Elasticsearch-based full-text search capabilities.
    This implements the SearchInterface.
    """
    def __init__(self, hosts: List[str], index_name: str = "code_index",
                 api_key: Optional[Tuple[str, str]] = None,  # (id, api_key) tuple
                 http_auth: Optional[Tuple[str, str]] = None, # (username, password) tuple
                 use_ssl: bool = True,
                 verify_certs: bool = True,
                 ca_certs: Optional[str] = None,
                 client_cert: Optional[str] = None,
                 client_key: Optional[str] = None):
        self.hosts = hosts
        self.index_name = index_name
        self.es = None
        
        # Ensure hosts have the correct scheme
        formatted_hosts = []
        for host in hosts:
            if isinstance(host, str):
                if not host.startswith(('http://', 'https://')):
                    scheme = "https" if use_ssl else "http"
                    formatted_hosts.append(f"{scheme}://{host}")
                else:
                    formatted_hosts.append(host)
            else:
                formatted_hosts.append(host)

        connection_params = {
            "hosts": formatted_hosts,
            "verify_certs": verify_certs,
            "ssl_show_warn": False, # Suppress SSL warnings if verify_certs is False
            "headers": {"Accept": "application/vnd.elasticsearch+json; compatible-with=8"}  # Force compatibility with Elasticsearch 8.x
        }

        if use_ssl and ca_certs:
            connection_params["ca_certs"] = ca_certs
        if use_ssl and client_cert and client_key:
            connection_params["client_cert"] = client_cert
            connection_params["client_key"] = client_key

        if api_key:
            connection_params["api_key"] = api_key
            logger.info("Using API Key for Elasticsearch connection.")
        elif http_auth:
            connection_params["basic_auth"] = http_auth  # Changed from http_auth to basic_auth
            logger.info("Using HTTP Basic Auth for Elasticsearch connection.")
        
        try:
            self.es = Elasticsearch(**connection_params)
            self.es.info() # Test connection
            logger.info(f"Successfully connected to Elasticsearch at {hosts} with secure settings.")
            self._ensure_index()
        except ConnectionError as e:
            logger.error(f"Could not connect to Elasticsearch at {hosts} with provided credentials: {e}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred during Elasticsearch connection: {e}")
            raise

    def _ensure_index(self):
        """Ensure the Elasticsearch index exists with appropriate mappings."""
        # Only create the index if it doesn't exist
        if self.es.indices.exists(index=self.index_name):
            logger.info(f"Elasticsearch index '{self.index_name}' already exists, skipping creation")
            return

        logger.info(f"Creating Elasticsearch index: {self.index_name}")
        # Define mapping and settings for the Elasticsearch index
        index_body = {
          "settings": {
            "index": {
              "number_of_shards": 3,
              "number_of_replicas": 1,
              "refresh_interval": "1s"
            },
            "analysis": {
              "analyzer": {
                "code_analyzer": {
                  "type": "custom",
                  "tokenizer": "whitespace",
                  "filter": [
                    "lowercase",
                    "code_stop",
                    "kstem",
                    "code_ngram"
                  ]
                },
                "path_analyzer": {
                  "type": "custom",
                  "tokenizer": "path_hierarchy",
                  "filter": [
                    "lowercase"
                  ]
                }
              },
              "filter": {
                "code_stop": {
                  "type": "stop",
                  "stopwords": [
                    "if", "for", "while", "do", "return", "class", "function", "def", "import", "from", "const", "let", "var", "public", "private", "protected", "static", "void", "int", "string", "bool", "true", "false", "null", "this", "new", "try", "catch", "finally", "throw", "async", "await"
                  ]
                },
                "code_ngram": {
                  "type": "ngram",
                  "min_gram": 2,
                  "max_gram": 3
                }
              }
            }
          },
          "mappings": {
            "properties": {
              "file_id": {
                "type": "keyword"
              },
              "path": {
                "type": "keyword",
                "fields": {
                  "analyzed": {
                    "type": "text",
                    "analyzer": "path_analyzer"
                  }
                }
              },
              "content": {
                "type": "text",
                "analyzer": "code_analyzer"
              },
              "language": {
                "type": "keyword"
              },
              "last_modified": {
                "type": "date"
              },
              "size": {
                "type": "long"
              },
              "checksum": {
                "type": "keyword"
              },
              "metadata": {
                "type": "object",
                "enabled": False
              }
            }
          }
        }
        self.es.indices.create(index=self.index_name, body=index_body) # Removed ignore=400 as we explicitly delete
        logger.info(f"Created Elasticsearch index: {self.index_name}")

    def index_document(self, doc_id: str, document: Dict[str, Any]) -> bool:
        """
        Indexes a document into Elasticsearch.
        `document` should contain at least 'file_path' and 'content'.
        """
        try:
            content_preview = ""
            if 'content' in document and isinstance(document['content'], str):
                content_preview = document['content'][:200] + ('...' if len(document['content']) > 200 else '')
            logger.debug(f"Attempting to index document {doc_id}. Content preview: '{content_preview}'")

            response = self.es.index(index=self.index_name, id=doc_id, document=document)
            logger.debug(f"Successfully indexed document {doc_id}. Elasticsearch response: {response}")
            return response['result'] in ['created', 'updated']
        except Exception as e:
            logger.error(f"Error indexing document {doc_id}: {e}. Full Elasticsearch response (if available): {getattr(e, 'info', 'N/A')}", exc_info=True)
            return False

    def update_document(self, doc_id: str, document: Dict[str, Any]) -> bool:
        """
        Updates an existing document in Elasticsearch.
        """
        try:
            response = self.es.update(index=self.index_name, id=doc_id, doc=document)
            logger.debug(f"Updated document {doc_id}: {response['result']}")
            return response['result'] == 'updated'
        except NotFoundError:
            logger.warning(f"Document {doc_id} not found for update.")
            return False
        except Exception as e:
            logger.error(f"Error updating document {doc_id}: {e}")
            return False

    def delete_document(self, doc_id: str) -> bool:
        """
        Deletes a document from Elasticsearch.
        """
        try:
            response = self.es.delete(index=self.index_name, id=doc_id)
            logger.debug(f"Deleted document {doc_id}: {response['result']}")
            return response['result'] == 'deleted'
        except NotFoundError:
            logger.warning(f"Document {doc_id} not found for deletion.")
            return False
        except Exception as e:
            logger.error(f"Error deleting document {doc_id}: {e}")
            return False

    def _translate_sqlite_pattern_to_es_query(self, pattern: str, field: str) -> Dict[str, Any]:
        """
        Translates SQLite LIKE/GLOB patterns to Elasticsearch Query DSL.

        Args:
            pattern: The SQLite LIKE or GLOB pattern.
            field: The Elasticsearch field to apply the query to.

        Returns:
            A dictionary representing the Elasticsearch query DSL.
        """
        try:
            # Handle SQL LIKE patterns
            if '%' in pattern or '_' in pattern:
                # Convert SQL LIKE wildcards to Elasticsearch wildcards
                # % -> * (any sequence of characters)
                # _ -> ? (any single character)
                es_wildcard_pattern = pattern.replace('%', '*').replace('_', '?')

                # If pattern starts with '%' and ends with '%', it's a contains search
                if pattern.startswith('%') and pattern.endswith('%') and len(pattern) > 1:
                    term = pattern[1:-1]
                    # Use match query for full-text search if it's a simple contains
                    return {"match": {field: term}}
                elif pattern.endswith('%'):
                    # Use prefix query for 'starts with'
                    return {"prefix": {field: es_wildcard_pattern[:-1]}}
                elif pattern.startswith('%'):
                    # Use wildcard query for 'ends with' or general wildcards
                    return {"wildcard": {field: es_wildcard_pattern}}
                else:
                    # General wildcard query for patterns with % or _ in the middle
                    return {"wildcard": {field: es_wildcard_pattern}}
            
            # Handle SQLite GLOB patterns (which are essentially regex)
            # Elasticsearch regexp query uses Java-style regex, which is mostly compatible
            # with Python's re, but some differences exist.
            # For simplicity, we'll directly use the pattern as a regexp.
            # Escaping special regex characters might be needed for literal matches,
            # but for GLOB-like behavior, direct translation is often sufficient.
            # SQLite GLOB: * matches any sequence, ? matches any single character.
            # Equivalent regex: .* for *, . for ?
            # We need to escape other regex special characters if they are meant literally.
            
            # First, escape all regex special characters
            escaped_pattern = re.escape(pattern)
            
            # Then, convert GLOB wildcards back to regex wildcards
            # The order is important: escape first, then unescape and convert GLOB wildcards
            es_regexp_pattern = escaped_pattern.replace(r'\*', '.*').replace(r'\?', '.')

            return {"regexp": {field: es_regexp_pattern}}
        except Exception as e:
            logger.error(f"Error translating SQLite pattern '{pattern}' to ES query for field '{field}': {e}")
            # Fallback to a match query or raise an error depending on desired behavior
            return {"match_all": {}} # Fallback to match_all or a simple match query


    def search_content(self, query: str, is_sqlite_pattern: bool = False,
                       fuzziness: Optional[str] = None,
                       content_boost: float = 1.0, file_path_boost: float = 1.0,
                       highlight_pre_tags: Optional[List[str]] = None,
                       highlight_post_tags: Optional[List[str]] = None) -> List[Tuple[str, Any]]:
        """
        Search across file content using Elasticsearch with advanced features.
        Can handle both direct queries and SQLite-style patterns.
        """
        results = []
        try:
            # Removed highlight settings for simplification
            # highlight_settings = {
            #     "fields": {
            #         "content": {},
            #         "file_path": {}
            #     }
            # }
            # if highlight_pre_tags:
            #     highlight_settings["pre_tags"] = highlight_pre_tags
            # if highlight_post_tags:
            #     highlight_settings["post_tags"] = highlight_post_tags

            if is_sqlite_pattern:
                es_query_dsl = self._translate_sqlite_pattern_to_es_query(query, "content")
                body = {
                    "query": es_query_dsl
                    # "highlight": highlight_settings # Removed for simplification
                }
            else:
                # Simplified to a basic match query on 'content' field
                body = {
                    "query": {
                        "match": {
                            "content": query
                        }
                    }
                    # "highlight": highlight_settings # Removed for simplification
                }
            
            response = self.es.search(index=self.index_name, body=body)
            logger.debug(f"Elasticsearch search response: {response}")
            for hit in response['hits']['hits']:
                logger.debug(f"Processing hit: {hit}")
                source = hit['_source']
                highlight = hit.get('highlight', {}) # Still get highlight if available, but not used in query
                logger.debug(f"Source: {source}, Highlight: {highlight}")
                result_doc = {
                    "file_path": source.get('path'),  # Changed from 'file_path' to 'path'
                    "content": source.get('content'),
                    "highlight": highlight # Keep highlight in result_doc for potential future use
                }
                tuple_result = (source.get('path'), result_doc)
                logger.debug(f"Appending tuple result: {tuple_result}")
                results.append(tuple_result)  # Changed from 'file_path' to 'path'
        except Exception as e:
            logger.error(f"Error searching content in Elasticsearch: {e}")
        
        logger.debug(f"Final results list length: {len(results)}")
        if results:
            logger.debug(f"First result structure: {results[0]}")
        return results

    def search_file_paths(self, query: str, is_sqlite_pattern: bool = False,
                          fuzziness: Optional[str] = None,
                          file_path_boost: float = 1.0,
                          highlight_pre_tags: Optional[List[str]] = None,
                          highlight_post_tags: Optional[List[str]] = None) -> List[str]:
        """
        Search across file paths using Elasticsearch with advanced features.
        Can handle both direct queries and SQLite-style patterns.
        """
        paths = []
        try:
            highlight_settings = {
                "fields": {
                    "path": {}
                }
            }
            if highlight_pre_tags:
                highlight_settings["pre_tags"] = highlight_pre_tags
            if highlight_post_tags:
                highlight_settings["post_tags"] = highlight_post_tags

            if is_sqlite_pattern:
                es_query_dsl = self._translate_sqlite_pattern_to_es_query(query, "path")
                body = {
                    "query": es_query_dsl,
                    "highlight": highlight_settings
                }
            else:
                match_query = {
                    "query": query,
                    "boost": file_path_boost
                }
                if fuzziness:
                    match_query["fuzziness"] = fuzziness

                body = {
                    "query": {
                        "match": {
                            "path": match_query
                        }
                    },
                    "highlight": highlight_settings,
                    "_source": ["path"]
                }
            
            response = self.es.search(index=self.index_name, body=body)
            for hit in response['hits']['hits']:
                highlighted_path = hit.get('highlight', {}).get('path', [hit['_source']['path']])[0]
                paths.append(highlighted_path)
        except Exception as e:
            logger.error(f"Error searching file paths in Elasticsearch: {e}")
        return paths

    def close(self) -> None:
        """Close the Elasticsearch search backend."""
        if self.es:
            # In newer elasticsearch-py versions, client connections are managed automatically.
            # Explicit close might not be necessary unless using specific connection pools.
            logger.info("ElasticsearchSearch client connection implicitly closed or managed by client.")
        else:
            logger.info("ElasticsearchSearch client was not initialized.")