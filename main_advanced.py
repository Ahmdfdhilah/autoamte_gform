#!/usr/bin/env python3
"""
Google Forms Automation - Advanced Main Script
Script utama dengan CSV/Excel support, cron jobs, dan RabbitMQ
"""

import argparse
import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from job_processor import JobProcessor, create_default_config
from data_reader import DataReader, create_sample_csv
from rabbitmq_handler import RabbitMQHandler, create_rabbitmq_config
from config import FORM_URL, REQUEST_CONFIG, AUTOMATION_CONFIG

def main():
    """
    Main function dengan command line interface
    """
    parser = argparse.ArgumentParser(
        description='Google Forms Automation with CSV/Excel, Cron Jobs, and RabbitMQ'
    )
    
    parser.add_argument(
        'mode',
        choices=['batch', 'scheduled', 'consumer', 'worker'],
        help='Execution mode'
    )
    
    parser.add_argument(
        '--csv',
        type=str,
        help='Path to CSV/Excel file containing form data'
    )
    
    parser.add_argument(
        '--create-sample',
        action='store_true',
        help='Create sample CSV file'
    )
    
    parser.add_argument(
        '--workers',
        type=int,
        default=3,
        help='Number of worker threads (default: 3)'
    )
    
    parser.add_argument(
        '--no-rabbitmq',
        action='store_true',
        help='Disable RabbitMQ (direct execution)'
    )
    
    parser.add_argument(
        '--rabbitmq-host',
        type=str,
        default='localhost',
        help='RabbitMQ host (default: localhost)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run mode (don\'t actually submit forms)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose output'
    )
    
    args = parser.parse_args()
    
    # Create sample CSV jika diminta
    if args.create_sample:
        sample_file = create_sample_csv('sample_forms_data.csv')
        print(f"✅ Sample CSV created: {sample_file}")
        return
    
    # Validate CSV file untuk modes yang membutuhkan
    if args.mode in ['batch', 'scheduled'] and not args.csv:
        print("❌ CSV file required for batch and scheduled modes")
        print("Use --csv <file_path> or --create-sample to create sample file")
        return
    
    if args.csv and not os.path.exists(args.csv):
        print(f"❌ CSV file not found: {args.csv}")
        return
    
    # Create configuration
    config = create_default_config()
    
    # Update config dari arguments
    config['form_url'] = FORM_URL
    config['request_config'] = REQUEST_CONFIG
    config['automation_config'] = AUTOMATION_CONFIG
    config['num_workers'] = args.workers
    config['use_rabbitmq'] = not args.no_rabbitmq
    config['mode'] = args.mode
    
    # RabbitMQ config
    if not args.no_rabbitmq:
        config['rabbitmq_config'] = create_rabbitmq_config(
            host=args.rabbitmq_host
        )
    
    # Dry run mode
    if args.dry_run:
        print("🧪 DRY RUN MODE - Forms will not be actually submitted")
        config['dry_run'] = True
    
    # Verbose mode
    if args.verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
    
    print("🚀 Google Forms Automation (Advanced)")
    print("=" * 60)
    print(f"📋 Mode: {args.mode}")
    print(f"📄 Form URL: {config['form_url']}")
    
    if args.csv:
        print(f"📊 Data File: {args.csv}")
    
    print(f"👥 Workers: {args.workers}")
    print(f"🐰 RabbitMQ: {'Enabled' if not args.no_rabbitmq else 'Disabled'}")
    
    if not args.no_rabbitmq:
        print(f"🔗 RabbitMQ Host: {args.rabbitmq_host}")
    
    print("-" * 60)
    
    # Initialize processor
    processor = JobProcessor(config)
    
    if not processor.initialize():
        print("❌ Failed to initialize job processor")
        return
    
    try:
        # Execute berdasarkan mode
        if args.mode == 'batch':
            print("📦 Running in BATCH mode...")
            processor.run_batch_mode(args.csv)
            
        elif args.mode == 'scheduled':
            print("⏰ Running in SCHEDULED mode...")
            print("Jobs will be executed based on ETA column in CSV")
            print("Press Ctrl+C to stop...")
            processor.run_scheduled_mode(args.csv)
            
        elif args.mode == 'consumer':
            print("🔄 Running in CONSUMER mode...")
            print("Waiting for jobs from RabbitMQ queue...")
            print("Press Ctrl+C to stop...")
            processor.start_consumer()
            
        elif args.mode == 'worker':
            print("👷 Running in WORKER mode...")
            print("Processing jobs from RabbitMQ queue...")
            print("Press Ctrl+C to stop...")
            processor.start_consumer()
    
    except KeyboardInterrupt:
        print("\n⏹️ Stopping automation...")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        processor.cleanup()

def show_examples():
    """
    Show usage examples
    """
    examples = """
📚 USAGE EXAMPLES:

1. Create sample CSV file:
   python main_advanced.py batch --create-sample

2. Batch mode (process all data immediately):
   python main_advanced.py batch --csv data.csv

3. Scheduled mode (process based on ETA column):
   python main_advanced.py scheduled --csv data.csv

4. Consumer mode (wait for jobs from RabbitMQ):
   python main_advanced.py consumer

5. Worker mode with custom settings:
   python main_advanced.py worker --workers 5 --rabbitmq-host 192.168.1.100

6. Dry run mode (test without submitting):
   python main_advanced.py batch --csv data.csv --dry-run

7. Without RabbitMQ (direct execution):
   python main_advanced.py batch --csv data.csv --no-rabbitmq

📋 CSV FILE FORMAT:
   - Header row (row 1): entry.123456789, entry.987654321, eta, priority
   - Data rows: values corresponding to form fields
   - eta column: YYYY-MM-DD HH:MM:SS (optional)
   - priority column: high, normal, low (optional)

🐰 RABBITMQ SETUP:
   1. Install RabbitMQ server
   2. Start RabbitMQ service
   3. Use default credentials (guest/guest) or configure custom

⏰ CRON JOBS:
   - ETA column controls when each job runs
   - Jobs without ETA run immediately
   - Format: 2024-08-05 10:30:00
    """
    print(examples)

if __name__ == "__main__":
    if len(sys.argv) == 1 or (len(sys.argv) == 2 and sys.argv[1] in ['-h', '--help']):
        show_examples()
    
    main()