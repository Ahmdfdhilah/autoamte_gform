"""
Main Google Forms automation system
"""

import logging
from typing import Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

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
        self.headless_mode = True  # Default to headless
        self.max_threads = 1  # Default single thread
        self._stats_lock = None  # Will be initialized if threading is used
    
    def set_headless_mode(self, headless: bool):
        """Set headless mode for browser automation"""
        self.headless_mode = headless
        self.form_automation.set_headless_mode(headless)
    
    def set_threading_config(self, max_threads: int):
        """Set multi-threading configuration"""
        import threading
        self.max_threads = max_threads
        self._stats_lock = threading.Lock()  # Thread-safe stats updates
    
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
            
            # Create a new form automation instance for thread safety
            if self.max_threads > 1:
                # Each thread gets its own form automation instance
                thread_automation = GoogleFormAutomation(self.form_url, self.form_automation.request_config)
                thread_automation.set_headless_mode(self.headless_mode)
                thread_automation.field_types = self.form_automation.field_types
                thread_automation.entry_fields = self.form_automation.entry_fields
                success = thread_automation.submit_form(form_data)
            else:
                # Use main instance for single-threaded
                success = self.form_automation.submit_form(form_data)
            
            # Update stats (thread-safe)
            self._update_stats(success, row_id)
            
            return success
        except Exception as e:
            logger.error(f"Job processing error for Row {job_data.get('row_id', '?')}: {e}")
            self._update_stats(False, job_data.get('row_id', '?'))
            return False
    
    def _update_stats(self, success: bool, row_id):
        """Thread-safe stats update"""
        if self._stats_lock:
            with self._stats_lock:
                self.stats['processed'] += 1
                if success:
                    self.stats['succeeded'] += 1
                    logger.info(f"✅ Row {row_id} completed successfully")
                else:
                    self.stats['failed'] += 1
                    logger.error(f"❌ Row {row_id} failed")
        else:
            # Single-threaded, no lock needed
            self.stats['processed'] += 1
            if success:
                self.stats['succeeded'] += 1
                logger.info(f"✅ Row {row_id} completed successfully")
            else:
                self.stats['failed'] += 1
                logger.error(f"❌ Row {row_id} failed")
    
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
        
        # Process jobs with threading support
        if self.max_threads > 1 and len(jobs) > 1:
            logger.info(f"🧵 Using {self.max_threads} concurrent threads")
            self._process_jobs_threaded(jobs)
        else:
            # Single-threaded processing
            for job in jobs:
                self.process_job(job)
        
        self.print_stats()
    
    def _process_jobs_threaded(self, jobs):
        """Process jobs using ThreadPoolExecutor"""
        with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            # Submit all jobs
            future_to_job = {executor.submit(self.process_job, job): job for job in jobs}
            
            # Process completed jobs
            for future in as_completed(future_to_job):
                job = future_to_job[future]
                try:
                    success = future.result()
                except Exception as exc:
                    logger.error(f"Thread execution error for job {job.get('row_id', '?')}: {exc}")
                    
                # Small delay to prevent overwhelming the form server
                time.sleep(0.5)
    
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