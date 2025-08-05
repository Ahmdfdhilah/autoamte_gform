"""
Main Google Forms automation system
"""

import logging
from typing import Dict

from ..automation.forms import GoogleFormAutomation
from ..messaging.rabbitmq import RabbitMQHandler
from ..scheduling.scheduler import JobScheduler
from ..data.csv_reader import CSVDataReader

logger = logging.getLogger(__name__)


class GoogleFormsAutomationSystem:
    """Main automation system"""
    
    def __init__(self, form_url: str, request_config: Dict, rabbitmq_config: Dict, timezone: str = 'Asia/Jakarta'):
        self.form_url = form_url
        self.form_automation = GoogleFormAutomation(form_url, request_config)
        self.rabbitmq_handler = RabbitMQHandler(rabbitmq_config)
        self.scheduler = JobScheduler(self.rabbitmq_handler, timezone)
        self.stats = {'processed': 0, 'succeeded': 0, 'failed': 0}
    
    def initialize(self, csv_headers: list = None) -> bool:
        """Initialize system"""
        try:
            # Extract form info
            entries, action_url = self.form_automation.extract_form_info(csv_headers)
            if not entries:
                logger.error("Failed to extract form information")
                return False
            
            logger.info(f"✅ Form initialized: {len(entries)} fields detected")
            return True
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            return False
    
    def process_job(self, job_data: Dict) -> bool:
        """Process single job"""
        try:
            row_id = job_data.get('row_id')
            form_data = job_data.get('form_data', {})
            
            logger.info(f"🔄 Processing Row {row_id}")
            
            # Submit form
            success = self.form_automation.submit_form(form_data)
            
            # Update stats
            self.stats['processed'] += 1
            if success:
                self.stats['succeeded'] += 1
                logger.info(f"✅ Row {row_id} completed successfully")
            else:
                self.stats['failed'] += 1
                logger.error(f"❌ Row {row_id} failed")
            
            return success
        except Exception as e:
            logger.error(f"Job processing error: {e}")
            self.stats['failed'] += 1
            return False
    
    def run_batch_mode(self, csv_path: str):
        """Run in batch mode"""
        logger.info("📦 Running in BATCH mode...")
        
        # Load CSV with form URL for entry order
        reader = CSVDataReader(csv_path, self.form_url)
        if not reader.load_data():
            return
        
        # Re-initialize with CSV headers
        if not self.initialize(reader.headers):
            logger.error("Re-initialization with CSV headers failed")
            return
        
        jobs = reader.get_job_list(self.scheduler.timezone.zone)
        logger.info(f"📋 Processing {len(jobs)} jobs")
        
        # Process all jobs immediately
        for job in jobs:
            self.process_job(job)
        
        self.print_stats()
    
    def run_scheduled_mode(self, csv_path: str):
        """Run in scheduled mode"""
        logger.info("⏰ Running in SCHEDULED mode...")
        
        # Load CSV with form URL for entry order
        reader = CSVDataReader(csv_path, self.form_url)
        if not reader.load_data():
            return
        
        # Re-initialize with CSV headers
        if not self.initialize(reader.headers):
            logger.error("Re-initialization with CSV headers failed")
            return
        
        jobs = reader.get_job_list(self.scheduler.timezone.zone)
        logger.info(f"📋 Scheduling {len(jobs)} jobs")
        
        # Schedule jobs
        self.scheduler.schedule_jobs(jobs)
        
        # Start worker
        logger.info("🔄 Starting worker to process scheduled jobs...")
        self.rabbitmq_handler.start_worker(self.process_job)
    
    def run_worker_mode(self):
        """Run in worker mode"""
        logger.info("👷 Running in WORKER mode...")
        logger.info("Waiting for jobs from queue...")
        
        self.rabbitmq_handler.start_worker(self.process_job)
    
    def print_stats(self):
        """Print processing statistics"""
        logger.info("📊 Processing Statistics:")
        logger.info(f"   Processed: {self.stats['processed']}")
        logger.info(f"   Succeeded: {self.stats['succeeded']}")
        logger.info(f"   Failed: {self.stats['failed']}")
        
        if self.stats['processed'] > 0:
            success_rate = (self.stats['succeeded'] / self.stats['processed']) * 100
            logger.info(f"   Success Rate: {success_rate:.1f}%")
    
    def cleanup(self):
        """Cleanup resources"""
        self.rabbitmq_handler.disconnect()
        self.print_stats()