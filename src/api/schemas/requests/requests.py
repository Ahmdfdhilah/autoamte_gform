"""
Pydantic schemas untuk request models
"""

from pydantic import BaseModel, HttpUrl, Field
from typing import Optional
from fastapi import UploadFile

class GoogleFormRequest(BaseModel):
    """Schema untuk request processing Google Form"""
    form_url: HttpUrl = Field(..., description="URL Google Form yang akan diproses")
    headless: bool = Field(True, description="Jalankan browser dalam mode headless")
    threads: int = Field(1, ge=1, le=5, description="Jumlah thread concurrent (1-5)")

class FormAnalysisRequest(BaseModel):
    """Schema untuk request analisis form"""
    form_url: HttpUrl = Field(..., description="URL Google Form untuk dianalisis")
    
class FieldMappingRequest(BaseModel):
    """Schema untuk request mapping field"""
    form_url: HttpUrl = Field(..., description="URL Google Form")
    csv_headers: list[str] = Field(..., description="Header CSV untuk dimapping")