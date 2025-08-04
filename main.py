#!/usr/bin/env python3
"""
Google Forms Automation - CSV + ETA + RabbitMQ
All-in-one solution for automated Google Forms submission
"""

import argparse
import sys
import os
import json
import logging
import time
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union

# Third-party imports
import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
import pika
import schedule
import pytz

# Configuration
from config import FORM_URL, REQUEST_CONFIG, AUTOMATION_CONFIG, RABBITMQ_CONFIG

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GoogleFormAutomation:
    """Google Forms automation class"""
    
    def __init__(self, form_url: str, request_config: Dict = None):
        self.form_url = form_url
        self.action_url = None
        self.entry_fields = []
        self.request_config = request_config or REQUEST_CONFIG
        self.session = requests.Session()
        self.session.headers.update(self.request_config['headers'])
    
    def extract_form_info(self) -> tuple[List[str], Optional[str]]:
        """Extract entry IDs and action URL from Google Form"""
        try:
            response = self.session.get(self.form_url, timeout=self.request_config['timeout'])
            response.raise_for_status()
            
            # Extract entry IDs
            entry_pattern = r'entry\.(\d+)'
            entries = re.findall(entry_pattern, response.text)
            self.entry_fields = list(set(entries))
            
            # Generate action URL
            self.action_url = self.form_url.replace('/viewform', '/formResponse')
            
            return self.entry_fields, self.action_url
        except Exception as e:
            logger.error(f"Error extracting form info: {e}")
            return [], None
    
    def submit_form(self, form_data: Dict) -> bool:
        """Submit data to Google Form"""
        try:
            processed_data = {}
            for key, value in form_data.items():
                if isinstance(value, list):
                    processed_data[key] = ', '.join(str(item) for item in value)
                else:
                    processed_data[key] = str(value)
            
            response = self.session.post(
                self.action_url, 
                data=processed_data, 
                timeout=self.request_config['timeout']
            )
            
            if response.status_code == 200:
                return True
            else:
                logger.error(f"HTTP Error: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Submit error: {e}")
            return False

class CSVDataReader:
    """CSV data reader for form data"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.df = None
        self.headers = []
    
    def load_data(self) -> bool:
        """Load data from CSV file"""
        try:
            file_ext = os.path.splitext(self.file_path)[1].lower()
            
            if file_ext == '.csv':
                self.df = pd.read_csv(self.file_path)
            elif file_ext in ['.xlsx', '.xls']:
                self.df = pd.read_excel(self.file_path)
            else:
                logger.error(f"Unsupported file format: {file_ext}")
                return False
            
            self.headers = list(self.df.columns)
            logger.info(f"✅ Loaded {len(self.df)} rows from {self.file_path}")
            return True
        except Exception as e:
            logger.error(f"Error loading file: {e}")
            return False
    
    def get_job_list(self) -> List[Dict]:
        """Convert DataFrame to job list"""
        if self.df is None:
            return []
        
        jobs = []
        timezone = pytz.timezone(AUTOMATION_CONFIG['timezone'])
        
        for index, row in self.df.iterrows():
            # Form data
            form_data = {}
            for col in self.headers:
                if col.startswith('entry.'):
                    value = row[col]
                    if pd.notna(value):
                        form_data[col] = str(value)
            
            # Job info
            job = {
                'row_id': index + 1,
                'form_data': form_data,
                'priority': str(row.get('priority', 'normal')) if 'priority' in self.headers else 'normal',
                'eta': None
            }
            
            # Handle ETA
            if 'eta' in self.headers and pd.notna(row['eta']):
                try:
                    eta_str = str(row['eta'])
                    naive_dt = datetime.strptime(eta_str, '%Y-%m-%d %H:%M:%S')
                    eta_dt = timezone.localize(naive_dt)
                    job['eta'] = eta_dt
                except ValueError as e:
                    logger.warning(f"Row {job['row_id']}: Invalid ETA format: {eta_str}")
            
            jobs.append(job)
        
        return jobs

class RabbitMQHandler:
    """RabbitMQ handler for job queue"""
    
    def __init__(self, config: Dict = None):
        self.config = config or RABBITMQ_CONFIG
        self.connection = None
        self.channel = None
        self.consuming = False
    
    def connect(self) -> bool:
        """Connect to RabbitMQ"""
        try:
            credentials = pika.PlainCredentials(
                self.config['username'], 
                self.config['password']
            )
            
            parameters = pika.ConnectionParameters(
                host=self.config['host'],
                port=self.config['port'],
                virtual_host=self.config.get('virtual_host', '/'),
                credentials=credentials
            )
            
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            
            # Declare queue
            self.channel.queue_declare(
                queue=self.config['queue_name'],
                durable=True
            )
            
            logger.info(f"✅ Connected to RabbitMQ: {self.config['host']}")
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
            
            message = json.dumps(job_data)
            self.channel.basic_publish(
                exchange='',
                routing_key=self.config['queue_name'],
                body=message,
                properties=pika.BasicProperties(delivery_mode=2)
            )
            
            logger.info(f"📤 Job sent to queue: Row {job_data.get('row_id')}")
            return True
        except Exception as e:
            logger.error(f"Failed to send job: {e}")
            return False
    
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
                queue=self.config['queue_name'],
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
    
    def disconnect(self):
        """Disconnect from RabbitMQ"""
        if self.connection and not self.connection.is_closed:
            self.connection.close()

class JobScheduler:
    """Job scheduler with ETA support"""
    
    def __init__(self, rabbitmq_handler: RabbitMQHandler):
        self.rabbitmq_handler = rabbitmq_handler
        self.timezone = pytz.timezone(AUTOMATION_CONFIG['timezone'])
        self.running = False
        self.scheduler_thread = None
        
        # Show current time
        now = datetime.now(self.timezone)
        logger.info(f"🕐 Scheduler timezone: {AUTOMATION_CONFIG['timezone']}")
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

class GoogleFormsAutomationSystem:
    """Main automation system"""
    
    def __init__(self):
        self.form_automation = GoogleFormAutomation(FORM_URL, REQUEST_CONFIG)
        self.rabbitmq_handler = RabbitMQHandler(RABBITMQ_CONFIG)
        self.scheduler = JobScheduler(self.rabbitmq_handler)
        self.stats = {'processed': 0, 'succeeded': 0, 'failed': 0}
    
    def initialize(self) -> bool:
        """Initialize system"""
        try:
            # Extract form info
            entries, action_url = self.form_automation.extract_form_info()
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
        
        # Load CSV
        reader = CSVDataReader(csv_path)
        if not reader.load_data():
            return
        
        jobs = reader.get_job_list()
        logger.info(f"📋 Processing {len(jobs)} jobs")
        
        # Process all jobs immediately
        for job in jobs:
            self.process_job(job)
        
        self.print_stats()
    
    def run_scheduled_mode(self, csv_path: str):
        """Run in scheduled mode"""
        logger.info("⏰ Running in SCHEDULED mode...")
        
        # Load CSV
        reader = CSVDataReader(csv_path)
        if not reader.load_data():
            return
        
        jobs = reader.get_job_list()
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

def create_sample_csv(filename: str = 'sample_data.csv'):
    """Create sample CSV file"""
    data = {
        'entry.625591749': ['Option 1', 'Option 2', 'Option 3'],
        'eta': ['2025-08-05 08:00:00', '2025-08-05 08:05:00', '2025-08-05 08:10:00'],
        'priority': ['high', 'normal', 'low']
    }
    
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False)
    logger.info(f"✅ Sample CSV created: {filename}")

def main():
    """Main function with CLI"""
    parser = argparse.ArgumentParser(description='Google Forms Automation')
    parser.add_argument('mode', choices=['batch', 'scheduled', 'worker'], help='Execution mode')
    parser.add_argument('--csv', type=str, help='Path to CSV file')
    parser.add_argument('--create-sample', action='store_true', help='Create sample CSV')
    parser.add_argument('--verbose', action='store_true', help='Verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if args.create_sample:
        create_sample_csv()
        return
    
    if args.mode in ['batch', 'scheduled'] and not args.csv:
        logger.error("CSV file required for batch and scheduled modes")
        return
    
    # Initialize system
    system = GoogleFormsAutomationSystem()
    
    if not system.initialize():
        logger.error("System initialization failed")
        return
    
    try:
        logger.info("🚀 Google Forms Automation System")
        logger.info(f"📋 Mode: {args.mode}")
        logger.info(f"📄 Form URL: {FORM_URL}")
        
        if args.csv:
            logger.info(f"📊 CSV File: {args.csv}")
        
        logger.info("-" * 50)
        
        if args.mode == 'batch':
            system.run_batch_mode(args.csv)
        elif args.mode == 'scheduled':
            system.run_scheduled_mode(args.csv)
        elif args.mode == 'worker':
            system.run_worker_mode()
    
    except KeyboardInterrupt:
        logger.info("⏹️ Stopping automation...")
    except Exception as e:
        logger.error(f"System error: {e}")
    finally:
        system.cleanup()

if __name__ == "__main__":
    main()