"""
RabbitMQ handler module for job queue management
"""

import json
import logging
from datetime import datetime
from typing import Dict
import pika

logger = logging.getLogger(__name__)


class RabbitMQHandler:
    """RabbitMQ handler for job queue"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.connection = None
        self.channel = None
        self.consuming = False
    
    def connect(self) -> bool:
        """Connect to RabbitMQ"""
        try:
            credentials = pika.PlainCredentials(
                self.config.get('username', 'guest'), 
                self.config.get('password', 'guest')
            )
            
            parameters = pika.ConnectionParameters(
                host=self.config.get('host', 'localhost'),
                port=self.config.get('port', 5672),
                virtual_host=self.config.get('virtual_host', '/'),
                credentials=credentials
            )
            
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
                self.connection.close()
                
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
            
            logger.info(f"✅ Connected to RabbitMQ: {self.config.get('host', 'localhost')}")
            return True
        except Exception as e:
            logger.error(f"RabbitMQ connection failed: {e}")
            return False
    
    def send_job(self, job_data: Dict) -> bool:
        """Send job to queue"""
        try:
            if not self.connection or self.connection.is_closed:
                if not self.connect():
                    return False
            
            # Convert datetime objects to strings for JSON serialization
            serializable_data = self._make_serializable(job_data)
            message = json.dumps(serializable_data)
            
            self.channel.basic_publish(
                exchange='',
                routing_key=self.config.get('queue_name', 'google_forms_jobs'),
                body=message,
                properties=pika.BasicProperties(delivery_mode=2)
            )
            
            logger.info(f"📤 Job sent to queue: Row {job_data.get('row_id')}")
            return True
        except Exception as e:
            logger.error(f"Failed to send job: {e}")
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
    
    def start_worker(self, callback_func):
        """Start worker to process jobs"""
        try:
            if not self.connect():
                return
            
            def wrapper(ch, method, properties, body):
                try:
                    job_data = json.loads(body)
                    success = callback_func(job_data)
                    
                    if success:
                        ch.basic_ack(delivery_tag=method.delivery_tag)
                    else:
                        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                except Exception as e:
                    logger.error(f"Worker error: {e}")
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            
            self.channel.basic_qos(prefetch_count=1)
            self.channel.basic_consume(
                queue=self.config.get('queue_name', 'google_forms_jobs'),
                on_message_callback=wrapper
            )
            
            logger.info("🔄 Worker started, waiting for jobs...")
            self.consuming = True
            self.channel.start_consuming()
        except KeyboardInterrupt:
            logger.info("⏹️ Worker stopped")
            self.stop_worker()
    
    def stop_worker(self):
        """Stop worker"""
        if self.consuming:
            self.channel.stop_consuming()
            self.consuming = False
    
    def purge_queue(self) -> bool:
        """Clear all messages from queue"""
        try:
            if not self.connection or self.connection.is_closed:
                if not self.connect():
                    return False
            
            queue_name = self.config.get('queue_name', 'google_forms_jobs')
            result = self.channel.queue_purge(queue=queue_name)
            logger.info(f"🧹 Purged {result.method.message_count} messages from queue '{queue_name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to purge queue: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from RabbitMQ"""
        if self.connection and not self.connection.is_closed:
            self.connection.close()