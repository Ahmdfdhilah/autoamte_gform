"""
Scheduler untuk Google Forms Automation
Menangani cron job dan scheduling berdasarkan ETA dari CSV/Excel data
"""

import schedule
import time
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import threading
from queue import Queue
import logging
import pytz

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduler.log'),
        logging.StreamHandler()
    ]
)

class JobScheduler:
    """
    Class untuk scheduling jobs berdasarkan ETA
    """
    
    def __init__(self, queue_handler=None, timezone='Asia/Jakarta'):
        """
        Initialize scheduler
        
        Args:
            queue_handler: Handler untuk mengirim job ke queue (RabbitMQ)
            timezone: Timezone untuk scheduling (default: WIB)
        """
        self.jobs = []
        self.queue_handler = queue_handler
        self.running = False
        self.scheduler_thread = None
        self.timezone = pytz.timezone(timezone)
        
        # Show timezone info
        now_local = datetime.now(self.timezone)
        logging.info(f"🕐 Scheduler timezone: {timezone} (WIB)")
        logging.info(f"🕐 Current time: {now_local.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
    def add_job_from_data(self, job_data: Dict) -> bool:
        """
        Add job dari data dengan ETA
        
        Args:
            job_data: Dictionary berisi form_data, eta, priority, dll
            
        Returns:
            True jika berhasil add job
        """
        try:
            row_id = job_data.get('row_id')
            eta = job_data.get('eta')
            priority = job_data.get('priority', 'normal')
            form_data = job_data.get('form_data', {})
            
            if not eta:
                # Jika tidak ada ETA, schedule immediately
                self.schedule_immediate_job(row_id, form_data, priority)
            else:
                # Parse ETA dan schedule accordingly
                self.schedule_eta_job(row_id, eta, form_data, priority)
            
            return True
            
        except Exception as e:
            logging.error(f"Error adding job: {e}")
            return False
    
    def schedule_eta_job(self, row_id: int, eta: str, form_data: Dict, priority: str):
        """
        Schedule job berdasarkan ETA tertentu (timezone-aware)
        
        Args:
            row_id: ID row dari CSV
            eta: ETA string (format: YYYY-MM-DD HH:MM:SS) - assumed to be in WIB
            form_data: Data form yang akan dikirim
            priority: Priority job
        """
        try:
            # Parse ETA dan assume sebagai WIB
            naive_dt = datetime.strptime(eta, '%Y-%m-%d %H:%M:%S')
            eta_dt_wib = self.timezone.localize(naive_dt)
            
            # Current time dalam WIB
            now_wib = datetime.now(self.timezone)
            
            if eta_dt_wib <= now_wib:
                # ETA sudah lewat, schedule immediately
                logging.warning(f"Row {row_id}: ETA {eta} WIB sudah lewat (now: {now_wib.strftime('%Y-%m-%d %H:%M:%S %Z')}), scheduling immediately")
                self.schedule_immediate_job(row_id, form_data, priority)
                return
            
            # Calculate delay
            delay_seconds = (eta_dt_wib - now_wib).total_seconds()
            
            # Schedule job
            def job_function():
                self.execute_job(row_id, form_data, priority, eta)
            
            # Add ke schedule dengan format waktu yang sesuai
            schedule.every().day.at(eta_dt_wib.strftime('%H:%M')).do(job_function).tag(f'row_{row_id}')
            
            logging.info(f"Row {row_id}: Scheduled for {eta} WIB (in {delay_seconds:.0f}s) - Priority: {priority}")
            
        except ValueError as e:
            logging.error(f"Row {row_id}: Invalid ETA format {eta}: {e}")
            self.schedule_immediate_job(row_id, form_data, priority)
    
    def schedule_immediate_job(self, row_id: int, form_data: Dict, priority: str):
        """
        Schedule job untuk dijalankan sekarang juga
        
        Args:
            row_id: ID row dari CSV
            form_data: Data form yang akan dikirim
            priority: Priority job
        """
        def job_function():
            self.execute_job(row_id, form_data, priority, 'immediate')
        
        schedule.every(1).seconds.do(job_function).tag(f'row_{row_id}')
        logging.info(f"Row {row_id}: Scheduled immediately - Priority: {priority}")
    
    def execute_job(self, row_id: int, form_data: Dict, priority: str, eta: str):
        """
        Execute job (kirim ke queue atau langsung submit)
        
        Args:
            row_id: ID row dari CSV
            form_data: Data form yang akan dikirim
            priority: Priority job
            eta: Original ETA
        """
        try:
            job_payload = {
                'row_id': row_id,
                'form_data': form_data,
                'priority': priority,
                'eta': eta,
                'scheduled_at': datetime.now().isoformat(),
                'status': 'executing'
            }
            
            if self.queue_handler:
                # Kirim ke RabbitMQ queue
                success = self.queue_handler.send_to_queue(job_payload)
                if success:
                    logging.info(f"Row {row_id}: Sent to queue successfully")
                else:
                    logging.error(f"Row {row_id}: Failed to send to queue")
            else:
                # Direct execution (fallback)
                logging.info(f"Row {row_id}: Executing directly (no queue handler)")
                self.direct_submit(job_payload)
            
            # Remove job setelah execute
            schedule.clear(f'row_{row_id}')
            
        except Exception as e:
            logging.error(f"Row {row_id}: Error executing job: {e}")
    
    def direct_submit(self, job_payload: Dict):
        """
        Direct submit ke Google Forms (fallback tanpa queue)
        
        Args:
            job_payload: Job data yang akan disubmit
        """
        try:
            from google_forms_automation import GoogleFormAutomation
            from config import FORM_URL, REQUEST_CONFIG
            
            automation = GoogleFormAutomation(FORM_URL, REQUEST_CONFIG)
            automation.extract_form_info()
            
            success = automation.submit_form(job_payload['form_data'])
            
            if success:
                logging.info(f"Row {job_payload['row_id']}: Direct submit successful")
            else:
                logging.error(f"Row {job_payload['row_id']}: Direct submit failed")
                
        except Exception as e:
            logging.error(f"Row {job_payload['row_id']}: Direct submit error: {e}")
    
    def start_scheduler(self):
        """
        Start scheduler dalam background thread
        """
        if self.running:
            logging.warning("Scheduler already running")
            return
        
        self.running = True
        
        def run_scheduler():
            logging.info("🚀 Scheduler started")
            while self.running:
                schedule.run_pending()
                time.sleep(1)
            logging.info("⏹️ Scheduler stopped")
        
        self.scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        self.scheduler_thread.start()
    
    def stop_scheduler(self):
        """
        Stop scheduler
        """
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=2)
        logging.info("Scheduler stopped")
    
    def get_pending_jobs(self) -> List[Dict]:
        """
        Get list of pending jobs
        
        Returns:
            List of pending jobs info
        """
        jobs_info = []
        for job in schedule.get_jobs():
            jobs_info.append({
                'tag': list(job.tags)[0] if job.tags else 'unknown',
                'next_run': job.next_run.isoformat() if job.next_run else None,
                'interval': str(job.interval),
                'unit': job.unit
            })
        return jobs_info
    
    def clear_all_jobs(self):
        """
        Clear semua scheduled jobs
        """
        schedule.clear()
        logging.info("All jobs cleared")

class CronJobManager:
    """
    Manager untuk cron-style scheduling
    """
    
    def __init__(self, scheduler: JobScheduler):
        self.scheduler = scheduler
    
    def schedule_daily_at(self, time_str: str, job_data_list: List[Dict]):
        """
        Schedule jobs untuk dijalankan daily pada waktu tertentu
        
        Args:
            time_str: Waktu dalam format "HH:MM"
            job_data_list: List of job data
        """
        def daily_job():
            logging.info(f"Daily job triggered at {time_str}")
            for job_data in job_data_list:
                self.scheduler.add_job_from_data(job_data)
        
        schedule.every().day.at(time_str).do(daily_job)
        logging.info(f"Daily job scheduled at {time_str} for {len(job_data_list)} jobs")
    
    def schedule_interval(self, interval_minutes: int, job_data_list: List[Dict]):
        """
        Schedule jobs untuk dijalankan setiap interval tertentu
        
        Args:
            interval_minutes: Interval dalam menit
            job_data_list: List of job data
        """
        def interval_job():
            logging.info(f"Interval job triggered (every {interval_minutes} minutes)")
            for job_data in job_data_list:
                self.scheduler.add_job_from_data(job_data)
        
        schedule.every(interval_minutes).minutes.do(interval_job)
        logging.info(f"Interval job scheduled every {interval_minutes} minutes for {len(job_data_list)} jobs")

if __name__ == "__main__":
    # Test scheduler
    scheduler = JobScheduler()
    
    # Sample job data
    sample_jobs = [
        {
            'row_id': 1,
            'form_data': {'entry.625591749': 'Test 1'},
            'eta': '2024-08-05 10:30:00',
            'priority': 'high'
        },
        {
            'row_id': 2,
            'form_data': {'entry.625591749': 'Test 2'},
            'eta': None,  # Immediate
            'priority': 'normal'
        }
    ]
    
    # Add jobs
    for job in sample_jobs:
        scheduler.add_job_from_data(job)
    
    # Start scheduler
    scheduler.start_scheduler()
    
    # Show pending jobs
    pending = scheduler.get_pending_jobs()
    print(f"Pending jobs: {json.dumps(pending, indent=2)}")
    
    # Run for a while
    try:
        time.sleep(60)  # Run for 1 minute
    except KeyboardInterrupt:
        pass
    finally:
        scheduler.stop_scheduler()