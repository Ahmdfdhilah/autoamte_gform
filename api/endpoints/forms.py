"""
Endpoints untuk Google Forms processing
"""

from fastapi import APIRouter, File, UploadFile, HTTPException, Form, Depends
from fastapi.responses import JSONResponse
import tempfile
import os
import logging
from typing import Optional
import pandas as pd

from api.schemas import (
    GoogleFormRequest, 
    FormAnalysisRequest, 
    FieldMappingRequest,
    GoogleFormResponse, 
    FormAnalysisResponse, 
    FieldMappingResponse,
    ProcessingStats
)
from api.services import DynamicFormAnalyzer
from src.core.system import GoogleFormsAutomationSystem
from src.core.config import REQUEST_CONFIG, AUTOMATION_CONFIG, RABBITMQ_CONFIG

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/forms", tags=["Google Forms"])

# Initialize form analyzer
form_analyzer = DynamicFormAnalyzer()

@router.post("/process/", response_model=GoogleFormResponse)
async def process_google_form(
    form_url: str = Form(..., description="URL Google Form yang akan diproses"),
    file: UploadFile = File(..., description="File CSV atau Excel yang berisi data"),
    headless: bool = Form(True, description="Jalankan browser dalam mode headless"),
    threads: int = Form(1, description="Jumlah thread concurrent (1-5)")
):
    """
    Process Google Form dengan data dari CSV/Excel
    
    Args:
        form_url: URL Google Form yang akan diisi
        file: File CSV atau Excel berisi data
        headless: Mode browser (True=headless, False=visible)  
        threads: Jumlah thread concurrent untuk processing
    
    Returns:
        JSON response dengan status dan hasil processing
    """
    
    try:
        # Validasi file extension
        filename = file.filename
        if not filename:
            raise HTTPException(status_code=400, detail="Filename is required")
            
        file_ext = os.path.splitext(filename)[1].lower()
        
        if file_ext not in ['.csv', '.xlsx', '.xls']:
            raise HTTPException(
                status_code=400, 
                detail=f"Format file tidak didukung: {file_ext}. Gunakan CSV atau XLSX."
            )
        
        # Validasi thread count
        if threads < 1 or threads > 5:
            raise HTTPException(
                status_code=400,
                detail="Thread count harus antara 1-5"
            )
        
        # Validasi URL format (basic check)
        if not form_url.startswith('https://docs.google.com/forms/'):
            raise HTTPException(
                status_code=400,
                detail="URL harus berupa Google Forms URL yang valid"
            )
        
        logger.info(f"📋 Processing request - Form: {form_url}")
        logger.info(f"📄 File: {filename} ({file_ext.upper()})")
        logger.info(f"🔧 Headless: {headless}, Threads: {threads}")
        
        # Simpan file upload ke temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Validasi data dalam file
            if file_ext == '.csv':
                df = pd.read_csv(temp_file_path)
            else:
                df = pd.read_excel(temp_file_path)
            
            if df.empty:
                raise HTTPException(
                    status_code=400,
                    detail="File kosong atau tidak berisi data"
                )
            
            logger.info(f"📊 Data rows: {len(df)}")
            
            # Inisialisasi sistem automasi dengan form URL dari request
            # Field types akan di-analyze otomatis oleh sistem
            system = GoogleFormsAutomationSystem(
                form_url,  # Menggunakan form_url dari request body 
                REQUEST_CONFIG,
                RABBITMQ_CONFIG,
                AUTOMATION_CONFIG['timezone']
            )
            
            # Setup konfigurasi browser
            system.set_headless_mode(headless)
            
            # Setup threading jika diperlukan
            if headless and threads > 1:
                system.set_threading_config(threads)
                logger.info(f"🧵 Multi-threading enabled: {threads} concurrent browsers")
            
            # Jalankan batch processing
            logger.info("🚀 Starting Google Forms automation...")
            result = system.run_batch_mode(temp_file_path)
            
            # Prepare stats
            stats = ProcessingStats(
                processed=system.stats['processed'],
                succeeded=system.stats['succeeded'],
                failed=system.stats['failed']
            )
            
            if stats.processed > 0:
                stats.success_rate = round((stats.succeeded / stats.processed) * 100, 2)
            
            # Cleanup sistem
            system.cleanup()
            
            return GoogleFormResponse(
                success=True,
                message="Google Forms automation completed successfully",
                data={
                    "form_url": form_url,
                    "file_processed": filename,
                    "rows_processed": len(df),
                    "headless_mode": headless,
                    "threads_used": threads
                },
                stats=stats
            )
            
        finally:
            # Hapus temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"❌ Processing error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@router.post("/analyze/", response_model=FormAnalysisResponse)
async def analyze_form(request: FormAnalysisRequest):
    """
    Analisis struktur Google Form
    
    Args:
        request: Form analysis request dengan URL
    
    Returns:
        FormAnalysisResponse dengan detail field form
    """
    try:
        form_url = str(request.form_url)
        logger.info(f"🔍 Analyzing form structure: {form_url}")
        
        # Analisis form
        analysis_result = form_analyzer.analyze_form(form_url)
        
        if not analysis_result['success']:
            raise HTTPException(
                status_code=400,
                detail=analysis_result['message']
            )
        
        return FormAnalysisResponse(
            success=True,
            message=analysis_result['message'],
            form_title=f"Google Form - {len(analysis_result['fields'])} fields",
            action_url=form_url,
            fields=analysis_result['fields'],
            total_fields=analysis_result['total_fields']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Form analysis error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Form analysis failed: {str(e)}"
        )

@router.post("/map-fields/", response_model=FieldMappingResponse)
async def map_csv_fields(request: FieldMappingRequest):
    """
    Mapping CSV headers dengan form fields
    
    Args:
        request: Field mapping request dengan URL dan CSV headers
    
    Returns:
        FieldMappingResponse dengan hasil mapping
    """
    try:
        form_url = str(request.form_url)
        csv_headers = request.csv_headers
        
        logger.info(f"🔗 Mapping CSV fields to form: {form_url}")
        logger.info(f"📋 CSV headers: {csv_headers}")
        
        # Lakukan mapping
        mapping_result = form_analyzer.map_csv_to_form(form_url, csv_headers)
        
        if not mapping_result['success']:
            raise HTTPException(
                status_code=400,
                detail=mapping_result['message']
            )
        
        return FieldMappingResponse(
            success=True,
            message=mapping_result['message'],
            mappings=mapping_result['mappings'],
            unmapped_columns=mapping_result['unmapped_columns'],
            unmapped_entries=mapping_result['unmapped_entries']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Field mapping error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Field mapping failed: {str(e)}"
        )