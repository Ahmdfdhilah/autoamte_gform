"""
Background processing service untuk Google Forms automation
"""

import logging
import os
import threading
import tempfile
from typing import Dict, Any
import pandas as pd
from datetime import datetime

from ...core.system import GoogleFormsAutomationSystem
from ...core.config import REQUEST_CONFIG, AUTOMATION_CONFIG, RABBITMQ_CONFIG
from .job_tracker import job_tracker, JobStatus

logger = logging.getLogger(__name__)

class BackgroundProcessor:
    """Background processor untuk menjalankan Google Forms automation"""
    
    def __init__(self):
        self.temp_dir = "temp"
        os.makedirs(self.temp_dir, exist_ok=True)
    
    def process_form_async(self, job_id: str, form_url: str, file_content: bytes, 
                          filename: str, headless: bool = True, threads: int = 1):
        """Process Google Form in background thread"""
        
        def _process():
            temp_file_path = None
            try:
                job = job_tracker.get_job(job_id)
                if not job:
                    logger.error(f"Job {job_id} not found")
                    return
                
                # Store thread reference for cancellation
                job.thread_ref = threading.current_thread()
                
                job_tracker.start_job(job_id)
                
                # Check for cancellation before starting
                if job.is_cancelled():
                    logger.info(f"Job {job_id} was cancelled before processing")
                    return
                
                job_tracker.update_job_progress(job_id, 5, "Saving uploaded file...")
                
                # Save file to temp directory with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_ext = os.path.splitext(filename)[1]
                temp_filename = f"{job_id}_{timestamp}{file_ext}"
                temp_file_path = os.path.join(self.temp_dir, temp_filename)
                
                with open(temp_file_path, 'wb') as f:
                    f.write(file_content)
                
                job_tracker.update_job_progress(job_id, 10, "Reading file data...")
                
                # Check for cancellation
                if job.is_cancelled():
                    logger.info(f"Job {job_id} cancelled during file reading")
                    return
                
                # Read and validate file (all rows are data, no header)
                if file_ext.lower() == '.csv':
                    df = pd.read_csv(temp_file_path, header=None)
                else:
                    df = pd.read_excel(temp_file_path, header=None)
                
                if df.empty:
                    raise Exception("File kosong atau tidak berisi data")
                
                rows_count = len(df)
                job_tracker.update_job_progress(job_id, 20, f"File loaded: {rows_count} rows")
                
                # Check for cancellation
                if job.is_cancelled():
                    logger.info(f"Job {job_id} cancelled before initialization")
                    return
                
                # Initialize automation system
                job_tracker.update_job_progress(job_id, 25, "Initializing automation system...")
                
                system = GoogleFormsAutomationSystem(
                    form_url,
                    REQUEST_CONFIG,
                    RABBITMQ_CONFIG,
                    AUTOMATION_CONFIG['timezone']
                )
                
                # Apply automation config settings
                if AUTOMATION_CONFIG.get('dry_run', False):
                    logger.info(f"🔧 Dry run mode enabled - no actual form submissions")
                
                if AUTOMATION_CONFIG.get('delay_between_submits', 0) > 0:
                    logger.info(f"⏱️ Delay between submits: {AUTOMATION_CONFIG['delay_between_submits']}s")
                
                # Configure system
                system.set_headless_mode(headless)
                
                if headless and threads > 1:
                    system.set_threading_config(threads)
                    job_tracker.update_job_progress(job_id, 30, f"Multi-threading enabled: {threads} threads")
                else:
                    job_tracker.update_job_progress(job_id, 30, "Single-threaded processing")
                
                # Hook progress callback untuk update job progress
                original_update_stats = system._update_stats
                
                def progress_callback(success: bool, row_id):
                    # Check for cancellation
                    if job.is_cancelled():
                        logger.info(f"Job {job_id} cancelled during processing row {row_id}")
                        # Try to stop the system gracefully
                        try:
                            system.cleanup()
                        except:
                            pass
                        return
                    
                    # Call original stats update
                    original_update_stats(success, row_id)
                    
                    # Update job progress
                    processed = system.stats['processed']
                    progress = min(95, 30 + int((processed / rows_count) * 60))  # 30-90%
                    job_tracker.update_job_progress(
                        job_id, 
                        progress, 
                        f"Processing row {processed}/{rows_count}"
                    )
                
                # Replace stats update method
                system._update_stats = progress_callback
                
                job_tracker.update_job_progress(job_id, 35, "Starting form processing...")
                
                # Check if file has ETA data by reading jobs first
                from ...data.csv_reader import CSVDataReader
                reader = CSVDataReader(temp_file_path, form_url)
                if not reader.load_data():
                    raise Exception("Failed to load CSV/Excel data")
                
                jobs = reader.get_job_list(system.scheduler.timezone.zone)
                
                # Check if any job has ETA for future scheduling
                has_eta = any(job.get('eta') is not None for job in jobs)
                
                if has_eta:
                    logger.info(f"📅 ETA detected in file, using scheduled mode")
                    job_tracker.update_job_progress(job_id, 40, "ETA detected, using scheduled mode...")
                    # Run scheduled processing
                    system.run_scheduled_mode(temp_file_path)
                else:
                    logger.info(f"📦 No ETA detected, using batch mode")
                    job_tracker.update_job_progress(job_id, 40, "No ETA detected, using batch mode...")
                    # Run batch processing
                    system.run_batch_mode(temp_file_path)
                
                job_tracker.update_job_progress(job_id, 95, "Processing completed, finalizing...")
                
                # Prepare result
                result = {
                    "form_url": form_url,
                    "file_processed": filename,
                    "rows_processed": rows_count,
                    "headless_mode": headless,
                    "threads_used": threads,
                    "stats": {
                        "processed": system.stats['processed'],
                        "succeeded": system.stats['succeeded'], 
                        "failed": system.stats['failed'],
                        "success_rate": round((system.stats['succeeded'] / system.stats['processed']) * 100, 2) if system.stats['processed'] > 0 else 0
                    },
                    "completed_at": datetime.now().isoformat()
                }
                
                # Cleanup system
                system.cleanup()
                
                # Mark job as completed
                job_tracker.complete_job(job_id, result)
                
            except Exception as e:
                logger.error(f"Background processing failed for job {job_id}: {str(e)}")
                job_tracker.fail_job(job_id, str(e))
            
            finally:
                # Clean up temp file
                if temp_file_path and os.path.exists(temp_file_path):
                    try:
                        os.unlink(temp_file_path)
                        logger.info(f"Cleaned up temp file: {temp_file_path}")
                    except Exception as e:
                        logger.warning(f"Failed to cleanup temp file {temp_file_path}: {e}")
        
        # Start processing in background thread
        thread = threading.Thread(target=_process, daemon=True)
        thread.start()
    
    def cleanup_temp_files(self, max_age_hours: int = 2):
        """Clean up old temporary files"""
        try:
            import time
            cutoff_time = time.time() - (max_age_hours * 3600)
            
            for filename in os.listdir(self.temp_dir):
                file_path = os.path.join(self.temp_dir, filename)
                if os.path.isfile(file_path):
                    file_mtime = os.path.getmtime(file_path)
                    if file_mtime < cutoff_time:
                        os.unlink(file_path)
                        logger.info(f"Cleaned up old temp file: {filename}")
        except Exception as e:
            logger.warning(f"Temp file cleanup failed: {e}")

# Global background processor instance
background_processor = BackgroundProcessor()