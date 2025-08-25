"""
Main Google Forms automation system
"""

import logging
from typing import Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import queue
import threading
import json

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
        self.headless_mode = True
        self.max_threads = 1
        self._stats_lock = threading.Lock()
        self.job_queue = queue.Queue() # Antrian internal untuk pekerjaan

    def set_headless_mode(self, headless: bool):
        self.headless_mode = headless
        self.form_automation.set_headless_mode(headless)
    
    def set_threading_config(self, max_threads: int):
        self.max_threads = max_threads
    
    def initialize(self, csv_headers: list = None) -> bool:
        try:
            entries, action_url = self.form_automation.extract_form_info(csv_headers)
            if not entries:
                logger.error("Failed to extract form information")
                return False
            logger.info(f"✅ Form initialized: {len(entries)} fields detected")
            return True
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            return False

    def _selenium_worker(self):
        """Worker thread yang mengambil pekerjaan dari antrian internal dan menjalankan Selenium."""
        while True:
            try:
                job_data = self.job_queue.get()
                if job_data is None: # Sinyal untuk berhenti
                    break
                
                # Proses pekerjaan
                self.process_job(job_data)
                self.job_queue.task_done()
            except Exception as e:
                logger.error(f"Error in Selenium worker thread: {e}")

    def process_job(self, job_data: Dict) -> bool:
        """Process single job. (Ini dipanggil oleh _selenium_worker)"""
        try:
            row_id = job_data.get('row_id')
            form_data = job_data.get('form_data', {})
            
            logger.info(f"🔄 Processing Row {row_id}")
            
            thread_automation = GoogleFormAutomation(self.form_url, self.form_automation.request_config)
            thread_automation.set_headless_mode(self.headless_mode)
            thread_automation.field_types = self.form_automation.field_types
            thread_automation.entry_fields = self.form_automation.entry_fields
            success = thread_automation.submit_form(form_data)
            
            self._update_stats(success, row_id)
            return success
        except Exception as e:
            logger.error(f"Job processing error for Row {job_data.get('row_id', '?')}: {e}")
            self._update_stats(False, job_data.get('row_id', '?'))
            return False

    def _update_stats(self, success: bool, row_id):
        with self._stats_lock:
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
        reader = CSVDataReader(csv_path, self.form_url)
        if not reader.load_data(): return
        if not self.initialize(reader.headers): return
        jobs = reader.get_job_list(self.scheduler.timezone.zone)
        logger.info(f"📋 Processing {len(jobs)} jobs")

        if self.max_threads > 1 and len(jobs) > 1:
            logger.info(f"🧵 Using {self.max_threads} concurrent threads")
            self._process_jobs_threaded(jobs)
        else:
            for job in jobs: self.process_job(job)
        self.print_stats()

    def _process_jobs_threaded(self, jobs):
        """Process jobs using ThreadPoolExecutor"""
        with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            future_to_job = {executor.submit(self.process_job, job): job for job in jobs}
            for future in as_completed(future_to_job):
                job = future_to_job[future]
                try: future.result()
                except Exception as exc: logger.error(f"Thread execution error for job {job.get('row_id', '?')}: {exc}")
                time.sleep(0.5)

    def run_scheduled_mode(self, csv_path: str):
        """Run in scheduled mode"""
        logger.info("⏰ Running in SCHEDULED mode...")
        reader = CSVDataReader(csv_path, self.form_url)
        if not reader.load_data(): return
        if not self.initialize(reader.headers): return
        jobs = reader.get_job_list(self.scheduler.timezone.zone)
        logger.info(f"📋 Scheduling {len(jobs)} jobs")
        logger.info("🧹 Clearing existing jobs from queue...")
        self.rabbitmq_handler.purge_queue()
        self.scheduler.schedule_jobs(jobs)
        logger.info("⏳ Waiting for all jobs to be scheduled...")
        time.sleep(1)
        logger.info("🔄 Starting worker to process scheduled jobs...")
        self.run_worker_mode()

    def run_worker_mode(self):
        """Run in worker mode"""
        logger.info("👷 Running in WORKER mode...")

        # 1. Mulai thread-thread worker Selenium
        selenium_workers = []
        for i in range(self.max_threads):
            worker_thread = threading.Thread(target=self._selenium_worker, daemon=True)
            worker_thread.start()
            selenium_workers.append(worker_thread)
        logger.info(f"🚀 Started {self.max_threads} Selenium worker threads.")

        # 2. Definisikan callback yang CEPAT untuk RabbitMQ
        def rabbitmq_callback(ch, method, properties, body):
            """Callback ini hanya mengambil pesan dan meletakkannya di antrian internal."""
            try:
                job_data = json.loads(body)
                self.job_queue.put(job_data)
                ch.basic_ack(delivery_tag=method.delivery_tag)
                logger.debug(f"Job {job_data.get('row_id')} received and queued internally.")
            except Exception as e:
                logger.error(f"Error queuing job from RabbitMQ: {e}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        
        # 3. Mulai consumer RabbitMQ, yang akan tetap responsif
        logger.info("...Waiting for jobs from RabbitMQ queue...")
        self.rabbitmq_handler.start_worker(rabbitmq_callback)

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