"""
RabbitMQ Handler untuk Google Forms Automation
Menangani queue system untuk memastikan reliability dan message persistence
"""

import pika
import json
import logging
import time
from typing import Dict, Optional, Callable
from datetime import datetime
import threading

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RabbitMQHandler:
    """
    Handler untuk RabbitMQ operations
    """
    
    def __init__(self, config: Dict = None):
        """
        Initialize RabbitMQ handler
        
        Args:
            config: RabbitMQ configuration
        """
        self.config = config or {
            'host': 'localhost',
            'port': 5672,
            'username': 'guest',
            'password': 'guest',
            'virtual_host': '/',
            'queue_name': 'google_forms_jobs',
            'exchange_name': 'forms_exchange',
            'routing_key': 'forms.submit'
        }
        
        self.connection = None
        self.channel = None
        self.consuming = False
        
    def connect(self) -> bool:
        """
        Connect to RabbitMQ server
        
        Returns:
            True jika berhasil connect
        """
        try:
            # Setup connection parameters
            credentials = pika.PlainCredentials(
                self.config['username'], 
                self.config['password']
            )
            
            parameters = pika.ConnectionParameters(
                host=self.config['host'],
                port=self.config['port'],
                virtual_host=self.config['virtual_host'],
                credentials=credentials,
                heartbeat=600,
                blocked_connection_timeout=300
            )
            
            # Create connection
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            
            # Declare exchange
            self.channel.exchange_declare(
                exchange=self.config['exchange_name'],
                exchange_type='direct',
                durable=True
            )
            
            # Declare queue
            self.channel.queue_declare(
                queue=self.config['queue_name'],
                durable=True,  # Queue survives broker restart
                arguments={
                    'x-message-ttl': 86400000,  # 24 hours TTL
                    'x-max-retries': 3
                }
            )
            
            # Bind queue to exchange
            self.channel.queue_bind(
                exchange=self.config['exchange_name'],
                queue=self.config['queue_name'],
                routing_key=self.config['routing_key']
            )
            
            # Set QoS for fair dispatch
            self.channel.basic_qos(prefetch_count=1)
            
            logger.info(f"✅ Connected to RabbitMQ: {self.config['host']}:{self.config['port']}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to RabbitMQ: {e}")
            return False
    
    def disconnect(self):
        """
        Disconnect from RabbitMQ
        """
        try:
            if self.connection and not self.connection.is_closed:
                self.connection.close()
            logger.info("📤 Disconnected from RabbitMQ")
        except Exception as e:
            logger.error(f"Error disconnecting: {e}")
    
    def send_to_queue(self, job_data: Dict, priority: int = 0) -> bool:
        """
        Send job data to queue
        
        Args:
            job_data: Data job yang akan dikirim
            priority: Priority message (0-255, higher = more priority)
            
        Returns:
            True jika berhasil send
        """
        try:
            if not self.connection or self.connection.is_closed:
                if not self.connect():
                    return False
            
            # Prepare message
            message = {
                'job_data': job_data,
                'sent_at': datetime.now().isoformat(),
                'retry_count': 0,
                'max_retries': 3
            }
            
            # Send message
            self.channel.basic_publish(
                exchange=self.config['exchange_name'],
                routing_key=self.config['routing_key'],
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                    priority=priority,
                    timestamp=int(time.time()),
                    message_id=f"job_{job_data.get('row_id', 'unknown')}_{int(time.time())}"
                )
            )
            
            logger.info(f"📤 Sent job to queue: Row {job_data.get('row_id')}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send to queue: {e}")
            return False
    
    def start_consumer(self, callback_function: Callable, auto_ack: bool = False):
        """
        Start consuming messages from queue
        
        Args:
            callback_function: Function yang akan dipanggil untuk setiap message
            auto_ack: Auto acknowledge messages
        """
        try:
            if not self.connection or self.connection.is_closed:
                if not self.connect():
                    return
            
            def wrapper_callback(ch, method, properties, body):
                """Wrapper untuk callback function"""
                try:
                    # Parse message
                    message = json.loads(body)
                    job_data = message.get('job_data', {})
                    
                    logger.info(f"📥 Processing job: Row {job_data.get('row_id')}")
                    
                    # Call user callback
                    success = callback_function(job_data, message)
                    
                    if success:
                        # Acknowledge message
                        ch.basic_ack(delivery_tag=method.delivery_tag)
                        logger.info(f"✅ Job completed: Row {job_data.get('row_id')}")
                    else:
                        # Handle retry logic
                        retry_count = message.get('retry_count', 0)
                        max_retries = message.get('max_retries', 3)
                        
                        if retry_count < max_retries:
                            # Retry message
                            message['retry_count'] = retry_count + 1
                            self.send_retry_message(message)
                            ch.basic_ack(delivery_tag=method.delivery_tag)
                            logger.warning(f"⚠️ Job failed, retrying: Row {job_data.get('row_id')} (attempt {retry_count + 1})")
                        else:
                            # Move to dead letter queue atau reject
                            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                            logger.error(f"❌ Job failed permanently: Row {job_data.get('row_id')}")
                    
                except Exception as e:
                    logger.error(f"❌ Error processing message: {e}")
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            
            # Start consuming
            self.channel.basic_consume(
                queue=self.config['queue_name'],
                on_message_callback=wrapper_callback,
                auto_ack=auto_ack
            )
            
            self.consuming = True
            logger.info(f"🔄 Started consuming from queue: {self.config['queue_name']}")
            logger.info("Press CTRL+C to stop consuming...")
            
            self.channel.start_consuming()
            
        except KeyboardInterrupt:
            logger.info("⏹️ Stopping consumer...")
            self.stop_consumer()
        except Exception as e:
            logger.error(f"❌ Error in consumer: {e}")
    
    def stop_consumer(self):
        """
        Stop consuming messages
        """
        if self.consuming and self.channel:
            self.channel.stop_consuming()
            self.consuming = False
            logger.info("Consumer stopped")
    
    def send_retry_message(self, message: Dict):
        """
        Send retry message dengan delay
        
        Args:
            message: Message yang akan di-retry
        """
        try:
            # Add delay based on retry count
            retry_count = message.get('retry_count', 0)
            delay_seconds = min(300, 30 * (2 ** retry_count))  # Exponential backoff, max 5 minutes
            
            # Schedule retry (simple implementation)
            def retry_job():
                time.sleep(delay_seconds)
                self.channel.basic_publish(
                    exchange=self.config['exchange_name'],
                    routing_key=self.config['routing_key'],
                    body=json.dumps(message),
                    properties=pika.BasicProperties(delivery_mode=2)
                )
            
            retry_thread = threading.Thread(target=retry_job, daemon=True)
            retry_thread.start()
            
        except Exception as e:
            logger.error(f"Error sending retry message: {e}")
    
    def get_queue_info(self) -> Dict:
        """
        Get informasi tentang queue
        
        Returns:
            Dictionary berisi queue info
        """
        try:
            if not self.connection or self.connection.is_closed:
                if not self.connect():
                    return {}
            
            method = self.channel.queue_declare(
                queue=self.config['queue_name'],
                passive=True  # Don't create, just get info
            )
            
            return {
                'queue_name': self.config['queue_name'],
                'message_count': method.method.message_count,
                'consumer_count': method.method.consumer_count
            }
            
        except Exception as e:
            logger.error(f"Error getting queue info: {e}")
            return {}
    
    def purge_queue(self) -> bool:
        """
        Purge (hapus semua message) dari queue
        
        Returns:
            True jika berhasil purge
        """
        try:
            if not self.connection or self.connection.is_closed:
                if not self.connect():
                    return False
            
            self.channel.queue_purge(queue=self.config['queue_name'])
            logger.info(f"🗑️ Queue purged: {self.config['queue_name']}")
            return True
            
        except Exception as e:
            logger.error(f"Error purging queue: {e}")
            return False

def create_rabbitmq_config(host: str = 'localhost', username: str = 'guest', password: str = 'guest') -> Dict:
    """
    Create RabbitMQ configuration
    
    Args:
        host: RabbitMQ host
        username: Username
        password: Password
        
    Returns:
        Configuration dictionary
    """
    return {
        'host': host,
        'port': 5672,
        'username': username,
        'password': password,
        'virtual_host': '/',
        'queue_name': 'google_forms_jobs',
        'exchange_name': 'forms_exchange',
        'routing_key': 'forms.submit'
    }

if __name__ == "__main__":
    # Test RabbitMQ handler
    config = create_rabbitmq_config()
    handler = RabbitMQHandler(config)
    
    # Test connection
    if handler.connect():
        # Test send message
        test_job = {
            'row_id': 1,
            'form_data': {'entry.625591749': 'Test Message'},
            'priority': 'high'
        }
        
        success = handler.send_to_queue(test_job)
        print(f"Send result: {success}")
        
        # Get queue info
        info = handler.get_queue_info()
        print(f"Queue info: {info}")
        
        handler.disconnect()
    else:
        print("Failed to connect to RabbitMQ")