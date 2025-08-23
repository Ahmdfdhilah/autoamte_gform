#!/usr/bin/env python3
"""
Google Forms Automation - Main Entry Point
Supports both CLI mode and FastAPI server mode
"""

import argparse
import logging
import sys
import os

# Configuration
from src.core.config import FORM_URL, REQUEST_CONFIG, AUTOMATION_CONFIG, RABBITMQ_CONFIG

# Modular imports
from src.core.system import GoogleFormsAutomationSystem
from src.utils.helpers import create_sample_csv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_cli_mode():
    """Run in CLI mode (original functionality)"""
    parser = argparse.ArgumentParser(description='Google Forms Automation')
    parser.add_argument('mode', choices=['batch', 'scheduled', 'worker', 'api'], help='Execution mode')
    parser.add_argument('--file', '--csv', type=str, dest='file', help='Path to data file (CSV or XLSX)')
    parser.add_argument('--create-sample', action='store_true', help='Create sample CSV')
    parser.add_argument('--verbose', action='store_true', help='Verbose logging')
    parser.add_argument('--no-headless', action='store_true', help='Run with browser visible (headless=False)')
    parser.add_argument('--threads', type=int, default=1, help='Number of concurrent threads (1-5, only works in headless mode)')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='API server host (for api mode)')
    parser.add_argument('--port', type=int, default=8000, help='API server port (for api mode)')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if args.create_sample:
        create_sample_csv()
        return
    
    # API mode - start FastAPI server
    if args.mode == 'api':
        run_api_server(args.host, args.port)
        return
    
    if args.mode in ['batch', 'scheduled'] and not args.file:
        logger.error("Data file required for batch and scheduled modes (CSV or XLSX)")
        return
    
    # Validate file extension
    if args.file:
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
    
    # Validate and set threading
    if args.threads < 1 or args.threads > 5:
        logger.error("❌ Thread count must be between 1-5")
        return
        
    # Set headless mode based on flag
    headless_mode = True
    if hasattr(args, 'no_headless') and args.no_headless:
        headless_mode = False
        system.set_headless_mode(False)
        logger.info("🔍 Running with browser visible (headless=False)")
        
        # Force single thread for visible browser
        if args.threads > 1:
            args.threads = 1
            logger.warning("⚠️ Multi-threading disabled in visible browser mode (--no-headless)")
    
    # Set threading configuration
    if headless_mode and args.threads > 1:
        system.set_threading_config(args.threads)
        logger.info(f"🧵 Multi-threading enabled: {args.threads} concurrent browsers (headless)")
    else:
        logger.info("🔄 Single-threaded processing")
    
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

def run_api_server(host: str = "0.0.0.0", port: int = 8000):
    """Run FastAPI server"""
    try:
        import uvicorn
        from fastapi import FastAPI
        from src.api.endpoints.forms import router as forms_router
        
        # Create FastAPI app
        app = FastAPI(
            title="Google Forms Automation API",
            description="API untuk otomasi pengisian Google Forms dengan data CSV/Excel",
            version="1.0.0",
            docs_url="/docs",
            redoc_url="/redoc"
        )
        
        # Include routers
        app.include_router(forms_router)
        
        # Root endpoint
        @app.get("/")
        async def root():
            """Root endpoint dengan informasi API"""
            return {
                "message": "Google Forms Automation API",
                "version": "1.0.0",
                "docs": "/docs",
                "endpoints": {
                    "POST /forms/process/": "Process Google Form with CSV/Excel data",
                    "POST /forms/analyze/": "Analyze Google Form structure", 
                    "POST /forms/map-fields/": "Map CSV headers to form fields"
                }
            }
        
        @app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {"status": "healthy", "service": "Google Forms Automation API"}
        
        logger.info("🚀 Starting Google Forms Automation API Server")
        logger.info(f"📍 Server: http://{host}:{port}")
        logger.info(f"📚 Docs: http://{host}:{port}/docs")
        logger.info(f"🔄 ReDoc: http://{host}:{port}/redoc")
        logger.info("-" * 50)
        
        # Start server
        uvicorn.run(app, host=host, port=port)
        
    except ImportError as e:
        logger.error(f"❌ FastAPI dependencies not installed: {e}")
        logger.error("💡 Install with: pip install fastapi uvicorn python-multipart")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Failed to start API server: {e}")
        sys.exit(1)

def main():
    """Main entry point"""
    run_cli_mode()

if __name__ == "__main__":
    main()