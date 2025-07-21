import pika
import threading
import json
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Literal
from elasticsearch import Elasticsearch
from src.code_index_mcp.content_extractor import ContentExtractor
from src.code_index_mcp.constants import ES_INDEX_NAME
from src.code_index_mcp.logger_config import logger # Import the centralized logger

IndexingOperation = Dict[str, Any]

class RabbitMQProducer:
    """
    A RabbitMQ producer for sending indexing requests.
    """
    def __init__(self, host: str, port: int, exchange: str, routing_key: str):
        self.host = host
        self.port = port
        self.exchange = exchange
        self.routing_key = routing_key
        self.connection: Optional[pika.BlockingConnection] = None
        self.channel: Optional[pika.channel.Channel] = None
        self._connect()
        logger.info(f"RabbitMQProducer initialized for {host}:{port}, exchange='{exchange}', routing_key='{routing_key}'",
                    extra={'component': 'RabbitMQProducer', 'host': host, 'port': port, 'exchange': exchange, 'routing_key': routing_key})

    def _connect(self):
        """Establishes a connection to RabbitMQ."""
        try:
            self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.host, port=self.port))
            self.channel = self.connection.channel()
            self.channel.exchange_declare(exchange=self.exchange, exchange_type='topic', durable=True)
            logger.info("Successfully connected to RabbitMQ and declared exchange.",
                        extra={'component': 'RabbitMQProducer', 'action': 'connect_success'})
        except pika.exceptions.AMQPConnectionError as e:
            logger.error(f"Failed to connect to RabbitMQ at {self.host}:{self.port}: {e}",
                        extra={'component': 'RabbitMQProducer', 'action': 'connect_failure', 'host': self.host, 'port': self.port, 'error': str(e)})
            self.connection = None
            self.channel = None
        except Exception as e:
            logger.error(f"An unexpected error occurred during RabbitMQ connection: {e}",
                        extra={'component': 'RabbitMQProducer', 'action': 'connect_unexpected_error', 'error': str(e)})
            self.connection = None
            self.channel = None

    def publish(self, message: Dict[str, Any]):
        """Publishes a message to the RabbitMQ exchange."""
        if not self.channel or not self.connection or self.connection.is_closed:
            logger.warning("RabbitMQ connection lost, attempting to reconnect...",
                           extra={'component': 'RabbitMQProducer', 'action': 'reconnect_attempt'})
            self._connect()
            if not self.channel:
                logger.error("Failed to reconnect to RabbitMQ, message not sent.",
                            extra={'component': 'RabbitMQProducer', 'action': 'publish_failed_reconnect'})
                return

        try:
            self.channel.basic_publish(
                exchange=self.exchange,
                routing_key=self.routing_key,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE # Make message persistent
                )
            )
            logger.debug(f"Published message to RabbitMQ: {message.get('type')} for {message.get('file_path')}",
                         extra={'component': 'RabbitMQProducer', 'action': 'publish_success', 'message_type': message.get('type'), 'file_path': message.get('file_path')})
        except pika.exceptions.AMQPConnectionError as e:
            logger.error(f"Lost connection to RabbitMQ while publishing: {e}. Message not sent.",
                        extra={'component': 'RabbitMQProducer', 'action': 'publish_connection_error', 'error': str(e)})
            self.connection = None # Mark for reconnection
        except Exception as e:
            logger.error(f"Error publishing message to RabbitMQ: {e}",
                        extra={'component': 'RabbitMQProducer', 'action': 'publish_unexpected_error', 'error': str(e)})

    def close(self):
        """Closes the RabbitMQ connection."""
        if self.connection and self.connection.is_open:
            self.connection.close()
            logger.info("RabbitMQProducer connection closed.",
                        extra={'component': 'RabbitMQProducer', 'action': 'close_connection'})

class RabbitMQConsumer:
    """
    A RabbitMQ consumer for receiving and processing indexing requests.
    Runs in a dedicated thread.
    """
    def __init__(self, es_client: Elasticsearch, base_path: str, host: str, port: int, queue_name: str, exchange: str, routing_key: str):
        self.es_client = es_client
        self.base_path = base_path
        self.host = host
        self.port = port
        self.queue_name = queue_name
        self.exchange = exchange
        self.routing_key = routing_key
        self.connection: Optional[pika.BlockingConnection] = None
        self.channel: Optional[pika.channel.Channel] = None
        self._stop_event = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None
        self.index_name = ES_INDEX_NAME
        self.content_extractor = ContentExtractor(base_path) # Initialize content extractor
        logger.info(f"RabbitMQConsumer initialized for {host}:{port}, queue='{queue_name}'",
                    extra={'component': 'RabbitMQConsumer', 'host': host, 'port': port, 'queue': queue_name})

    def _connect(self):
        """Establishes a connection to RabbitMQ and declares queue/exchange."""
        try:
            self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.host, port=self.port))
            self.channel = self.connection.channel()
            self.channel.exchange_declare(exchange=self.exchange, exchange_type='topic', durable=True)
            result = self.channel.queue_declare(queue=self.queue_name, durable=True)
            self.channel.queue_bind(exchange=self.exchange, queue=self.queue_name, routing_key=self.routing_key)
            logger.info(f"Successfully connected to RabbitMQ, declared queue '{self.queue_name}' and bound to exchange '{self.exchange}'.",
                        extra={'component': 'RabbitMQConsumer', 'action': 'connect_success', 'queue': self.queue_name, 'exchange': self.exchange})
            return True
        except pika.exceptions.AMQPConnectionError as e:
            logger.error(f"Failed to connect to RabbitMQ at {self.host}:{self.port}: {e}",
                        extra={'component': 'RabbitMQConsumer', 'action': 'connect_failure', 'host': self.host, 'port': self.port, 'error': str(e)})
            self.connection = None
            self.channel = None
            return False
        except Exception as e:
            logger.error(f"An unexpected error occurred during RabbitMQ consumer connection: {e}",
                        extra={'component': 'RabbitMQConsumer', 'action': 'connect_unexpected_error', 'error': str(e)})
            self.connection = None
            self.channel = None
            return False

    def _extract_content_and_metadata(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Extracts content and basic metadata from a file using the ContentExtractor.
        """
        return self.content_extractor.extract_content(file_path)

    def _index_document(self, file_path: str, document: Dict[str, Any]):
        """
        Indexes or updates a document in Elasticsearch.
        Uses file_path as the document ID for idempotency.
        """
        try:
            response = self.es_client.index(
                index=self.index_name,
                id=file_path,
                document=document,
                op_type='index'
            )
            logger.info(f"Indexed/Updated document for {file_path}: {response['result']}",
                        extra={'component': 'Elasticsearch', 'action': 'index_document', 'file_path': file_path, 'result': response['result']})
            return True
        except ConnectionError as e:
            logger.error(f"Elasticsearch connection error while indexing {file_path}: {e}. Retrying...",
                        extra={'component': 'Elasticsearch', 'action': 'index_document_connection_error', 'file_path': file_path, 'error': str(e)})
            # In a real system, implement a retry mechanism (e.g., exponential backoff)
            return False
        except Exception as e:
            logger.error(f"Error indexing document for {file_path}: {e}",
                        extra={'component': 'Elasticsearch', 'action': 'index_document_unexpected_error', 'file_path': file_path, 'error': str(e)})
            return False

    def _delete_document(self, file_path: str):
        """
        Deletes a document from Elasticsearch.
        """
        try:
            response = self.es_client.delete(
                index=self.index_name,
                id=file_path,
                ignore=[404]
            )
            if response['result'] == 'deleted':
                logger.info(f"Deleted document for {file_path}",
                            extra={'component': 'Elasticsearch', 'action': 'delete_document', 'file_path': file_path, 'result': response['result']})
                return True
            elif response['result'] == 'not_found':
                logger.warning(f"Document for {file_path} not found in Elasticsearch (already deleted or never existed).",
                               extra={'component': 'Elasticsearch', 'action': 'delete_document_not_found', 'file_path': file_path})
                return True # Consider it successful if it's already gone
            return False
        except ConnectionError as e:
            logger.error(f"Elasticsearch connection error while deleting {file_path}: {e}. Retrying...",
                        extra={'component': 'Elasticsearch', 'action': 'delete_document_connection_error', 'file_path': file_path, 'error': str(e)})
            return False
        except Exception as e:
            logger.error(f"Error deleting document for {file_path}: {e}",
                        extra={'component': 'Elasticsearch', 'action': 'delete_document_unexpected_error', 'file_path': file_path, 'error': str(e)})
            return False

    def _process_message(self, ch, method, properties, body):
        """Callback function to process received messages."""
        try:
            operation: IndexingOperation = json.loads(body.decode('utf-8'))
            op_type = operation.get("type")
            file_path = operation.get("file_path")
            
            logger.info(f"Received message: {op_type} for {file_path}",
                        extra={'component': 'RabbitMQConsumer', 'action': 'message_received', 'op_type': op_type, 'file_path': file_path})

            success = False
            if op_type == "index" or op_type == "update":
                document_data = self._extract_content_and_metadata(file_path)
                if document_data:
                    success = self._index_document(file_path, document_data)
                else:
                    logger.error(f"Failed to extract content for {file_path}, skipping indexing.",
                                extra={'component': 'RabbitMQConsumer', 'action': 'extract_content_failed', 'file_path': file_path})
            elif op_type == "delete":
                success = self._delete_document(file_path)
            else:
                logger.warning(f"Unknown indexing operation type: {op_type}",
                               extra={'component': 'RabbitMQConsumer', 'action': 'unknown_op_type', 'op_type': op_type})
            
            if success:
                ch.basic_ack(delivery_tag=method.delivery_tag)
                logger.info(f"Acknowledged message for {file_path}",
                            extra={'component': 'RabbitMQConsumer', 'action': 'message_acknowledged', 'file_path': file_path})
            else:
                # Requeue message if processing failed
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                logger.warning(f"NACKed message for {file_path}, requeued.",
                               extra={'component': 'RabbitMQConsumer', 'action': 'message_nacked', 'file_path': file_path})

        except json.JSONDecodeError as e:
            logger.error(f"Error decoding message body: {e}. Message: {body.decode('utf-8')}. Rejecting message.",
                        extra={'component': 'RabbitMQConsumer', 'action': 'json_decode_error', 'error': str(e), 'message_body': body.decode('utf-8')})
            ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False) # Don't requeue malformed messages
        except Exception as e:
            logger.error(f"Unhandled error processing message: {e}. Message: {body.decode('utf-8')}. Requeuing message.",
                        extra={'component': 'RabbitMQConsumer', 'action': 'unhandled_processing_error', 'error': str(e), 'message_body': body.decode('utf-8')})
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    def _worker(self):
        """Worker thread function to consume messages."""
        logger.info("RabbitMQConsumer worker thread started.",
                    extra={'component': 'RabbitMQConsumer', 'action': 'worker_start'})
        while not self._stop_event.is_set():
            if not self.channel or self.connection.is_closed:
                logger.warning("RabbitMQ connection not active for consumer, attempting to reconnect...",
                               extra={'component': 'RabbitMQConsumer', 'action': 'worker_reconnect_attempt'})
                if not self._connect():
                    time.sleep(5) # Wait before retrying connection
                    continue
            
            try:
                # Start consuming messages. This call blocks until a message is received
                # or the connection is closed. We use a timeout to allow for graceful shutdown.
                self.channel.basic_consume(
                    queue=self.queue_name,
                    on_message_callback=self._process_message,
                    auto_ack=False # Manual acknowledgment
                )
                self.channel.start_consuming()
            except pika.exceptions.AMQPConnectionError as e:
                logger.error(f"RabbitMQ connection error during consuming: {e}. Attempting to reconnect...",
                            extra={'component': 'RabbitMQConsumer', 'action': 'worker_consume_connection_error', 'error': str(e)})
                self.connection = None # Mark for reconnection
                time.sleep(5)
            except Exception as e:
                logger.error(f"Unhandled error in RabbitMQConsumer worker: {e}",
                            extra={'component': 'RabbitMQConsumer', 'action': 'worker_unhandled_error', 'error': str(e)})
                time.sleep(1) # Prevent busy-loop on persistent errors

        logger.info("RabbitMQConsumer worker thread stopped.",
                    extra={'component': 'RabbitMQConsumer', 'action': 'worker_stop'})

    def start(self):
        """Starts the consumer worker thread."""
        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._stop_event.clear()
            self._worker_thread = threading.Thread(target=self._worker, daemon=True)
            self._worker_thread.start()
            logger.info("RabbitMQConsumer worker thread initiated.")
        else:
            logger.warning("RabbitMQConsumer worker thread is already running.")

    def stop(self):
        """Stops the consumer worker thread and closes connection."""
        if self._worker_thread and self._worker_thread.is_alive():
            logger.info("Signaling RabbitMQConsumer worker thread to stop...")
            self._stop_event.set()
            
            # First stop consuming to prevent new messages
            if self.channel:
                try:
                    # Cancel all consumers first
                    for consumer_tag in getattr(self.channel, '_consumer_tags', []):
                        try:
                            self.channel.basic_cancel(consumer_tag)
                        except Exception as e:
                            logger.debug(f"Error canceling consumer {consumer_tag}: {e}")
                    
                    # Then stop consuming
                    self.channel.stop_consuming()
                except Exception as e:
                    logger.warning(f"Error stopping RabbitMQ channel consuming: {e}")
            
            # Wait for worker thread to finish before closing connection
            self._worker_thread.join(timeout=5)
            
            # Now close the connection
            if self.connection and not self.connection.is_closed:
                try:
                    self.connection.close()
                except Exception as e:
                    logger.warning(f"Error closing RabbitMQ connection: {e}")
            
            # Final check on thread status
            if self._worker_thread.is_alive():
                logger.warning("RabbitMQConsumer worker thread did not stop gracefully.")
            else:
                logger.info("RabbitMQConsumer worker thread stopped successfully.")
        else:
            logger.info("RabbitMQConsumer worker thread is not running.")

class RealtimeIndexer:
    """
    Handles real-time indexing of file changes using RabbitMQ.
    Acts as a producer to send messages to the queue.
    """
    def __init__(self, es_client: Elasticsearch, base_path: str, producer: RabbitMQProducer, consumer: RabbitMQConsumer):
        self.es_client = es_client
        self.base_path = base_path
        self.producer = producer
        self.consumer = consumer
        self.index_name = ES_INDEX_NAME
        logger.info(f"RealtimeIndexer initialized with RabbitMQ producer and consumer for index: {self.index_name}")

    def start(self):
        """Starts the RabbitMQ consumer worker thread."""
        self.consumer.start()
        logger.info("RealtimeIndexer (RabbitMQ consumer) started.")

    def stop(self):
        """Stops the RabbitMQ consumer worker thread."""
        self.consumer.stop()
        self.producer.close() # Close producer connection on stop
        logger.info("RealtimeIndexer (RabbitMQ consumer) stopped and producer connection closed.")

    def enqueue_change(self, file_path: str, change_type: Literal["index", "delete", "update"]):
        """
        Enqueues a file change operation to RabbitMQ.
        'index' and 'update' are treated similarly for upserting.
        """
        operation = {
            "type": change_type,
            "file_path": file_path,
            "timestamp": datetime.now().isoformat()
        }
        self.producer.publish(operation)
        logger.debug(f"Enqueued change to RabbitMQ: {change_type} for {file_path}")

    def wait_for_completion(self, timeout: Optional[float] = None):
        """
        Note: For RabbitMQ, 'wait_for_completion' is not directly equivalent to an in-memory queue's join().
        Messages are asynchronous. This method can be used to wait for a short period
        to allow some messages to be processed, but it won't guarantee all messages
        sent *before* this call are processed, especially if the consumer is in a separate process.
        For testing, you might need to implement a more sophisticated check or
        rely on logs/Elasticsearch state.
        """
        logger.warning("wait_for_completion for RabbitMQ is an approximation. It waits for a short period.")
        time.sleep(timeout if timeout is not None else 2) # Wait for 2 seconds by default
        logger.info("Approximated wait for RabbitMQ messages completed.")