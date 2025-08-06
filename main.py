#!/usr/bin/env python3
"""
Google Forms Automation - CSV + ETA + RabbitMQ
All-in-one solution for automated Google Forms submission
"""

import argparse
import logging

# Configuration
from config import FORM_URL, REQUEST_CONFIG, AUTOMATION_CONFIG, RABBITMQ_CONFIG

# Modular imports
from src.core.system import GoogleFormsAutomationSystem
from src.utils.helpers import create_sample_csv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main function with CLI"""
    parser = argparse.ArgumentParser(description='Google Forms Automation')
    parser.add_argument('mode', choices=['batch', 'scheduled', 'worker'], help='Execution mode')
    parser.add_argument('--file', '--csv', type=str, dest='file', help='Path to data file (CSV or XLSX)')
    parser.add_argument('--create-sample', action='store_true', help='Create sample CSV')
    parser.add_argument('--verbose', action='store_true', help='Verbose logging')
    parser.add_argument('--no-headless', action='store_true', help='Run with browser visible (headless=False)')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if args.create_sample:
        create_sample_csv()
        return
    
    if args.mode in ['batch', 'scheduled'] and not args.file:
        logger.error("Data file required for batch and scheduled modes (CSV or XLSX)")
        return
    
    # Validate file extension
    if args.file:
        import os
        file_ext = os.path.splitext(args.file)[1].lower()
        if file_ext not in ['.csv', '.xlsx', '.xls']:
            logger.error(f"Unsupported file format: {file_ext}. Please use CSV or XLSX files.")
            return
        
        if not os.path.exists(args.file):
            logger.error(f"File not found: {args.file}")
            return
        
        logger.info(f"📁 Data file: {args.file} ({file_ext.upper()})")
    
    # Initialize system
    system = GoogleFormsAutomationSystem(
        FORM_URL, 
        REQUEST_CONFIG, 
        RABBITMQ_CONFIG, 
        AUTOMATION_CONFIG['timezone']
    )
    
    # Set headless mode based on flag
    if hasattr(args, 'no_headless') and args.no_headless:
        system.set_headless_mode(False)
        logger.info("🔍 Running with browser visible (headless=False)")
    
    # Don't initialize here - will be done in each mode with CSV headers
    
    try:
        logger.info("🚀 Google Forms Automation System")
        logger.info(f"📋 Mode: {args.mode}")
        logger.info(f"📄 Form URL: {FORM_URL}")
        
        if args.file:
            logger.info(f"📊 Data File: {args.file}")
        
        logger.info("-" * 50)
        
        if args.mode == 'batch':
            system.run_batch_mode(args.file)
        elif args.mode == 'scheduled':
            system.run_scheduled_mode(args.file)
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