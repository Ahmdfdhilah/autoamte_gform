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
    system = GoogleFormsAutomationSystem(
        FORM_URL, 
        REQUEST_CONFIG, 
        RABBITMQ_CONFIG, 
        AUTOMATION_CONFIG['timezone']
    )
    
    # Don't initialize here - will be done in each mode with CSV headers
    
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