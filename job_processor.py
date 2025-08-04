"""
Job Processor dan Worker System untuk Google Forms Automation
Memproses jobs dari RabbitMQ queue dengan worker pool
"""

import logging
import json
import time
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import threading
from queue import Queue

from google_forms_automation import GoogleFormAutomation
from rabbitmq_handler import RabbitMQHandler
from data_reader import DataReader
from scheduler import JobScheduler

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class JobProcessor:
    """
    Main job processor yang mengkoordinasi semua komponen
    """
    
    def __init__(self, config: Dict):
        """
        Initialize job processor
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.form_automation = None
        self.rabbitmq_handler = None
        self.scheduler = None
        self.worker_pool = None
        self.running = False
        
        # Statistics
        self.stats = {
            'jobs_processed': 0,
            'jobs_succeeded': 0,
            'jobs_failed': 0,
            'start_time': None
        }
    
    def initialize(self) -> bool:
        """
        Initialize semua komponen
        
        Returns:
            True jika berhasil initialize
        """
        try:
            # Initialize Google Forms automation
            self.form_automation = GoogleFormAutomation(
                form_url=self.config['form_url'],
                request_config=self.config.get('request_config', {})
            )
            
            # Extract form info
            if not self.form_automation.extract_form_info()[0]:
                logger.error("Failed to extract form information")
                return False
            
            # Initialize RabbitMQ handler
            if self.config.get('use_rabbitmq', True):
                self.rabbitmq_handler = RabbitMQHandler(self.config.get('rabbitmq_config', {}))
                if not self.rabbitmq_handler.connect():
                    logger.error("Failed to connect to RabbitMQ")
                    return False
            
            # Initialize scheduler dengan timezone dari config
            timezone = self.config.get('automation_config', {}).get('timezone', 'Asia/Jakarta')
            self.scheduler = JobScheduler(queue_handler=self.rabbitmq_handler, timezone=timezone)
            
            logger.info("✅ Job processor initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize job processor: {e}")
            return False
    
    def load_jobs_from_csv(self, csv_path: str) -> bool:
        """
        Load jobs dari CSV file
        
        Args:
            csv_path: Path ke CSV file
            
        Returns:
            True jika berhasil load
        """
        try:
            # Load data
            reader = DataReader(csv_path)
            if not reader.load_data():
                return False
            
            if not reader.validate_headers():
                return False
            
            # Get form data list
            job_list = reader.get_form_data_list()
            
            logger.info(f"📊 Loaded {len(job_list)} jobs from CSV")
            
            # Schedule jobs
            for job_data in job_list:
                self.scheduler.add_job_from_data(job_data)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error loading jobs from CSV: {e}")
            return False
    
    def start_worker_pool(self, num_workers: int = 3):
        """
        Start worker pool untuk memproses jobs
        
        Args:
            num_workers: Jumlah worker threads
        """
        self.worker_pool = ThreadPoolExecutor(max_workers=num_workers)
        logger.info(f"🔥 Started worker pool with {num_workers} workers")
    
    def stop_worker_pool(self):
        """
        Stop worker pool
        """
        if self.worker_pool:
            self.worker_pool.shutdown(wait=True)
            logger.info("⏹️ Worker pool stopped")
    
    def process_single_job(self, job_data: Dict, message_info: Dict = None) -> bool:
        """
        Process single job
        
        Args:
            job_data: Job data dari queue
            message_info: Additional message info dari RabbitMQ
            
        Returns:
            True jika berhasil process
        """
        try:
            row_id = job_data.get('row_id', 'unknown')
            form_data = job_data.get('form_data', {})
            
            logger.info(f"🔄 Processing job: Row {row_id}")
            
            # Submit form
            success = self.form_automation.submit_form(form_data)
            
            # Update statistics
            self.stats['jobs_processed'] += 1
            if success:
                self.stats['jobs_succeeded'] += 1
                logger.info(f"✅ Job completed successfully: Row {row_id}")
            else:
                self.stats['jobs_failed'] += 1
                logger.error(f"❌ Job failed: Row {row_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error processing job: {e}")
            self.stats['jobs_failed'] += 1
            return False
    
    def start_consumer(self):
        """
        Start consuming jobs dari RabbitMQ
        """
        if not self.rabbitmq_handler:
            logger.error("RabbitMQ handler not initialized")
            return
        
        logger.info("🚀 Starting job consumer...")
        self.running = True
        self.stats['start_time'] = datetime.now()
        
        try:
            self.rabbitmq_handler.start_consumer(
                callback_function=self.process_single_job,
                auto_ack=False
            )
        except KeyboardInterrupt:
            logger.info("⏹️ Consumer stopped by user")
        finally:
            self.running = False
            self.cleanup()
    
    def run_batch_mode(self, csv_path: str):
        """
        Run dalam batch mode (process semua jobs langsung tanpa queue)
        
        Args:
            csv_path: Path ke CSV file
        """
        logger.info("🚀 Starting batch mode...")
        self.stats['start_time'] = datetime.now()
        
        try:
            # Load jobs
            if not self.load_jobs_from_csv(csv_path):
                return
            
            # Start worker pool
            self.start_worker_pool(self.config.get('num_workers', 3))
            
            # Get jobs dari scheduler
            pending_jobs = self.scheduler.get_pending_jobs()
            logger.info(f"📋 Processing {len(pending_jobs)} jobs in batch mode")
            
            # Process jobs
            futures = []
            for job_info in pending_jobs:
                # Mock job data untuk batch mode
                job_data = {
                    'row_id': job_info.get('tag', 'unknown').replace('row_', ''),
                    'form_data': {}  # This would need to be populated from scheduler
                }
                
                future = self.worker_pool.submit(self.process_single_job, job_data)
                futures.append(future)
            
            # Wait for completion
            for future in as_completed(futures):
                try:
                    result = future.result()
                except Exception as e:
                    logger.error(f"Job execution error: {e}")
            
            logger.info("✅ Batch processing completed")
            
        except Exception as e:
            logger.error(f"❌ Error in batch mode: {e}")
        finally:
            self.stop_worker_pool()
            self.print_statistics()
    
    def run_scheduled_mode(self, csv_path: str):
        """
        Run dalam scheduled mode dengan cron jobs
        
        Args:
            csv_path: Path ke CSV file
        """
        logger.info("🚀 Starting scheduled mode...")
        
        try:
            # Load dan schedule jobs
            if not self.load_jobs_from_csv(csv_path):
                return
            
            # Start scheduler
            self.scheduler.start_scheduler()
            
            # Start worker pool jika menggunakan RabbitMQ
            if self.rabbitmq_handler:
                self.start_worker_pool(self.config.get('num_workers', 3))
                self.start_consumer()
            else:
                # Direct execution mode
                logger.info("Running in direct execution mode (without RabbitMQ)")
                while True:
                    time.sleep(1)
            
        except KeyboardInterrupt:
            logger.info("⏹️ Scheduled mode stopped by user")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """
        Cleanup resources
        """
        logger.info("🧹 Cleaning up resources...")
        
        if self.scheduler:
            self.scheduler.stop_scheduler()
        
        if self.worker_pool:
            self.stop_worker_pool()
        
        if self.rabbitmq_handler:
            self.rabbitmq_handler.disconnect()
        
        self.print_statistics()
    
    def print_statistics(self):
        """
        Print processing statistics
        """
        if self.stats['start_time']:
            duration = datetime.now() - self.stats['start_time']
            
            logger.info("📊 Processing Statistics:")
            logger.info(f"   Duration: {duration}")
            logger.info(f"   Jobs Processed: {self.stats['jobs_processed']}")
            logger.info(f"   Jobs Succeeded: {self.stats['jobs_succeeded']}")
            logger.info(f"   Jobs Failed: {self.stats['jobs_failed']}")
            
            if self.stats['jobs_processed'] > 0:
                success_rate = (self.stats['jobs_succeeded'] / self.stats['jobs_processed']) * 100
                logger.info(f"   Success Rate: {success_rate:.1f}%")
    
    def get_status(self) -> Dict:
        """
        Get current status
        
        Returns:
            Status dictionary
        """
        status = {
            'running': self.running,
            'stats': self.stats.copy(),
            'components': {
                'form_automation': bool(self.form_automation),
                'rabbitmq_handler': bool(self.rabbitmq_handler),
                'scheduler': bool(self.scheduler),
                'worker_pool': bool(self.worker_pool)
            }
        }
        
        # Add queue info jika ada RabbitMQ
        if self.rabbitmq_handler:
            status['queue_info'] = self.rabbitmq_handler.get_queue_info()
        
        return status

def create_default_config() -> Dict:
    """
    Create default configuration
    
    Returns:
        Default configuration dictionary
    """
    return {
        'form_url': 'https://docs.google.com/forms/d/e/YOUR_FORM_ID/viewform',
        'request_config': {
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            },
            'timeout': 30,
            'retries': 3
        },
        'use_rabbitmq': True,
        'rabbitmq_config': {
            'host': 'localhost',
            'port': 5672,
            'username': 'guest',
            'password': 'guest',
            'virtual_host': '/',
            'queue_name': 'google_forms_jobs',
            'exchange_name': 'forms_exchange',
            'routing_key': 'forms.submit'
        },
        'num_workers': 3,
        'mode': 'scheduled'  # 'batch', 'scheduled', 'consumer'
    }

if __name__ == "__main__":
    # Example usage
    config = create_default_config()
    
    # Update dengan form URL dari config.py
    try:
        from config import FORM_URL, REQUEST_CONFIG
        config['form_url'] = FORM_URL
        config['request_config'] = REQUEST_CONFIG
    except ImportError:
        logger.warning("Could not import config, using defaults")
    
    # Create processor
    processor = JobProcessor(config)
    
    if processor.initialize():
        # Run dalam batch mode dengan sample data
        processor.run_batch_mode('sample_data.csv')
    else:
        logger.error("Failed to initialize processor")