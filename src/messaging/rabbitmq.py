"""
RabbitMQ handler module for job queue management with robust connection handling
"""

import json
import logging
import time
import threading
from datetime import datetime
from typing import Dict, Callable, Optional
import pika
from pika.exceptions import AMQPConnectionError, ConnectionClosed, ChannelClosed

logger = logging.getLogger(__name__)


class RabbitMQHandler:
    """RabbitMQ handler for job queue with robust connection management"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.connection = None
        self.channel = None
        self.consuming = False
        self._connection_lock = threading.Lock()
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 5
    
    def _create_connection_parameters(self):
        """Create connection parameters with robust settings"""
        credentials = pika.PlainCredentials(
            self.config.get('username', 'guest'), 
            self.config.get('password', 'guest')
        )
        
        return pika.ConnectionParameters(
            host=self.config.get('host', 'localhost'),
            port=self.config.get('port', 5672),
            virtual_host=self.config.get('virtual_host', '/'),
            credentials=credentials,
            heartbeat=600,  # 10 minutes heartbeat
            blocked_connection_timeout=300,  # 5 minutes
            socket_timeout=10,
            connection_attempts=3,
            retry_delay=2,
            # Additional stability parameters
            channel_max=20,
            frame_max=131072
        )
    
    def connect(self) -> bool:
        """Connect to RabbitMQ with retry logic"""
        with self._connection_lock:
            try:
                # Close existing connection if any
                if self.connection and not self.connection.is_closed:
                    try:
                        self.connection.close()
                    except Exception:
                        pass
                
                # Create new connection
                parameters = self._create_connection_parameters()
                self.connection = pika.BlockingConnection(parameters)
                self.channel = self.connection.channel()
                
                queue_name = self.config.get('queue_name', 'google_forms_jobs')
                
                # Declare queue with conflict handling
                try:
                    # Try to declare queue with our settings
                    self.channel.queue_declare(
                        queue=queue_name,
                        durable=True
                    )
                    logger.info(f"✅ Queue '{queue_name}' created/confirmed")
                except pika.exceptions.ChannelClosedByBroker as e:
                    # Queue exists with different settings, reconnect and use existing
                    logger.warning(f"Queue exists with different settings, using existing queue")
                    try:
                        self.connection.close()
                    except Exception:
                        pass
                    
                    # Reconnect
                    self.connection = pika.BlockingConnection(parameters)
                    self.channel = self.connection.channel()
                    
                    # Use existing queue (passive=True)
                    try:
                        result = self.channel.queue_declare(
                            queue=queue_name,
                            passive=True
                        )
                        logger.info(f"✅ Using existing queue '{queue_name}' with {result.method.message_count} pending messages")
                    except Exception as passive_error:
                        logger.error(f"Failed to connect to existing queue: {passive_error}")
                        raise
                
                # Reset reconnect attempts on successful connection
                self._reconnect_attempts = 0
                logger.info(f"✅ Connected to RabbitMQ: {self.config.get('host', 'localhost')}")
                return True
                
            except Exception as e:
                self._reconnect_attempts += 1
                logger.error(f"RabbitMQ connection failed (attempt {self._reconnect_attempts}): {e}")
                
                if self._reconnect_attempts < self._max_reconnect_attempts:
                    wait_time = min(2 ** self._reconnect_attempts, 30)  # Exponential backoff, max 30s
                    logger.info(f"⏳ Retrying connection in {wait_time} seconds...")
                    time.sleep(wait_time)
                    return self.connect()  # Recursive retry
                else:
                    logger.error(f"❌ Max reconnection attempts ({self._max_reconnect_attempts}) reached")
                    return False
    
    def ensure_connection(self) -> bool:
        """Ensure connection is active, reconnect if necessary"""
        try:
            # Check if connection exists and is open
            if not self.connection or self.connection.is_closed:
                logger.info("🔄 Connection lost, reconnecting...")
                return self.connect()
            
            # Test connection by checking if channel is open
            if not self.channel or self.channel.is_closed:
                logger.info("🔄 Channel lost, recreating...")
                try:
                    self.channel = self.connection.channel()
                    return True
                except Exception as e:
                    logger.warning(f"⚠️ Failed to recreate channel: {e}")
                    return self.connect()
            
            # Test with a lightweight operation
            try:
                # This will raise an exception if connection is broken
                self.channel.queue_declare(
                    queue=self.config.get('queue_name', 'google_forms_jobs'),
                    passive=True
                )
                return True
            except Exception as e:
                logger.warning(f"⚠️ Connection test failed: {e}")
                return self.connect()
                
        except Exception as e:
            logger.error(f"❌ Connection check failed: {e}")
            return self.connect()

    def send_job_threadsafe(self, job_data: Dict):
        """A thread-safe method to send a job. It creates a new connection."""
        connection = None
        try:
            parameters = self._create_connection_parameters()
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()
            
            # Ensure the queue exists
            channel.queue_declare(queue=self.config.get('queue_name', 'google_forms_jobs'), durable=True)
            
            serializable_data = self._make_serializable(job_data)
            message = json.dumps(serializable_data)

            channel.basic_publish(
                exchange='',
                routing_key=self.config.get('queue_name', 'google_forms_jobs'),
                body=message,
                properties=pika.BasicProperties(delivery_mode=2)
            )
            logger.info(f"📤 Job sent to queue (thread-safe): Row {job_data.get('row_id')}")
        except Exception as e:
            logger.error(f"❌ Failed to send job from a thread: {e}")
        finally:
            if connection and connection.is_open:
                connection.close()
    
    def send_job(self, job_data: Dict, max_retries: int = 3) -> bool:
        """Send job to queue with retry logic"""
        for attempt in range(max_retries):
            try:
                if not self.ensure_connection():
                    raise Exception("Could not establish connection")
                
                # Convert datetime objects to strings for JSON serialization
                serializable_data = self._make_serializable(job_data)
                message = json.dumps(serializable_data)
                
                self.channel.basic_publish(
                    exchange='',
                    routing_key=self.config.get('queue_name', 'google_forms_jobs'),
                    body=message,
                    properties=pika.BasicProperties(
                        delivery_mode=2,  # Make message persistent
                        timestamp=int(time.time())
                    )
                )
                
                logger.info(f"📤 Job sent to queue: Row {job_data.get('row_id')}")
                return True
                
            except Exception as e:
                logger.warning(f"❌ Send job attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.info(f"⏳ Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"❌ Failed to send job after {max_retries} attempts")
                    return False
        
        return False
    
    def _make_serializable(self, obj):
        """Convert datetime objects to strings for JSON serialization"""
        if isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]
        elif isinstance(obj, datetime):
            return obj.isoformat()
        else:
            return obj
    
    def start_worker(self, callback_func: Callable, prefetch_count: int = 1):
        """Start worker to process jobs with robust error handling"""
        def wrapper(ch, method, properties, body):
            job_id = None
            try:
                job_data = json.loads(body)
                job_id = job_data.get('job_id', 'unknown')
                
                logger.info(f"🔄 Processing job {job_id}")
                success = callback_func(job_data)
                
                if success:
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                    logger.info(f"✅ Job {job_id} completed successfully")
                else:
                    logger.warning(f"⚠️ Job {job_id} failed, requeuing...")
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                    
            except json.JSONDecodeError as e:
                logger.error(f"❌ Invalid JSON in message: {e}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)  # Don't requeue bad JSON
            except Exception as e:
                logger.error(f"❌ Worker error processing job {job_id}: {e}")
                try:
                    # Try to nack the message
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                except Exception as nack_error:
                    logger.error(f"❌ Failed to nack message: {nack_error}")
        
        # Connection loop with auto-reconnection
        while True:
            try:
                if not self.ensure_connection():
                    logger.error("❌ Could not establish connection for worker")
                    time.sleep(5)
                    continue
                
                self.channel.basic_qos(prefetch_count=prefetch_count)
                self.channel.basic_consume(
                    queue=self.config.get('queue_name', 'google_forms_jobs'),
                    on_message_callback=wrapper
                )
                
                logger.info("🔄 Worker started, waiting for jobs...")
                self.consuming = True
                
                try:
                    self.channel.start_consuming()
                except KeyboardInterrupt:
                    logger.info("⏹️ Worker stopped by user")
                    self.stop_worker()
                    break
                except (ConnectionClosed, ChannelClosed, AMQPConnectionError) as e:
                    logger.warning(f"⚠️ Connection lost during consuming: {e}")
                    self.consuming = False
                    logger.info("🔄 Attempting to reconnect in 5 seconds...")
                    time.sleep(5)
                    continue
                    
            except Exception as e:
                logger.error(f"❌ Worker error: {e}")
                time.sleep(5)
                continue
    
    def stop_worker(self):
        """Stop worker safely"""
        try:
            if self.consuming and self.channel and not self.channel.is_closed:
                self.channel.stop_consuming()
                self.consuming = False
                logger.info("⏹️ Worker stopped")
        except Exception as e:
            logger.error(f"Error stopping worker: {e}")
    
    def purge_queue(self) -> bool:
        """Clear all messages from queue"""
        try:
            if not self.ensure_connection():
                return False
            
            queue_name = self.config.get('queue_name', 'google_forms_jobs')
            result = self.channel.queue_purge(queue=queue_name)
            logger.info(f"🧹 Purged {result.method.message_count} messages from queue '{queue_name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to purge queue: {e}")
            return False
    
    def get_queue_info(self) -> Dict:
        """Get queue information"""
        try:
            if not self.ensure_connection():
                return {}
            
            queue_name = self.config.get('queue_name', 'google_forms_jobs')
            method = self.channel.queue_declare(queue=queue_name, passive=True)
            
            return {
                'queue_name': queue_name,
                'message_count': method.method.message_count,
                'consumer_count': method.method.consumer_count
            }
        except Exception as e:
            logger.error(f"Failed to get queue info: {e}")
            return {}
    
    def disconnect(self):
        """Disconnect from RabbitMQ safely"""
        try:
            if self.consuming:
                self.stop_worker()
            
            if self.connection and not self.connection.is_closed:
                self.connection.close()
                logger.info("🚪 Disconnected from RabbitMQ")
        except Exception as e:
            logger.error(f"Error disconnecting: {e}")

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()