"""
Job scheduler module with ETA support
"""

import logging
import threading
from datetime import datetime
from typing import Dict, List
import pytz

logger = logging.getLogger(__name__)


class JobScheduler:
    """Job scheduler with ETA support"""
    
    def __init__(self, rabbitmq_handler, timezone_str: str = 'Asia/Jakarta'):
        self.rabbitmq_handler = rabbitmq_handler
        self.timezone = pytz.timezone(timezone_str)
        self.running = False
        self.scheduler_thread = None
        
        # Show current time
        now = datetime.now(self.timezone)
        logger.info(f"🕐 Scheduler timezone: {timezone_str}")
        logger.info(f"🕐 Current time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
    def schedule_jobs(self, jobs: List[Dict]):
        """Schedule jobs based on ETA"""
        now = datetime.now(self.timezone)
        
        for job in jobs:
            eta = job.get('eta')
            
            if eta and eta > now:
                # Schedule for future
                delay = (eta - now).total_seconds()
                logger.info(f"Row {job['row_id']}: Scheduled for {eta.strftime('%Y-%m-%d %H:%M:%S %Z')} (in {delay:.0f}s)")
                
                def schedule_job(job_data=job):
                    self.rabbitmq_handler.send_job(job_data)
                
                # Schedule using threading timer
                timer = threading.Timer(delay, schedule_job)
                timer.daemon = True
                timer.start()
            else:
                # Send immediately
                if eta:
                    logger.warning(f"Row {job['row_id']}: ETA {eta.strftime('%Y-%m-%d %H:%M:%S %Z')} sudah lewat, sending immediately")
                else:
                    logger.info(f"Row {job['row_id']}: No ETA, sending immediately")
                
                self.rabbitmq_handler.send_job(job)