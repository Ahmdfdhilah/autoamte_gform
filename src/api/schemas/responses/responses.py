"""
Pydantic schemas untuk response models
"""

from pydantic import BaseModel
from typing import Optional, Dict, Any, List

class BaseResponse(BaseModel):
    """Base response schema"""
    success: bool
    message: str

class ProcessingStats(BaseModel):
    """Schema untuk statistik processing"""
    processed: int = 0
    succeeded: int = 0
    failed: int = 0
    success_rate: Optional[float] = None

class GoogleFormResponse(BaseResponse):
    """Schema untuk response processing Google Form"""
    data: Optional[Dict[str, Any]] = None
    stats: Optional[ProcessingStats] = None

class FormField(BaseModel):
    """Schema untuk field form"""
    entry_id: str
    field_type: str
    label: str
    required: bool = False
    options: Optional[List[str]] = None

class FormAnalysisResponse(BaseResponse):
    """Schema untuk response analisis form"""
    form_title: Optional[str] = None
    action_url: Optional[str] = None
    fields: List[FormField] = []
    total_fields: int = 0

class FieldMapping(BaseModel):
    """Schema untuk mapping field"""
    csv_column: str
    form_entry: str
    field_type: str
    confidence: float = 0.0

class FieldMappingResponse(BaseResponse):
    """Schema untuk response field mapping"""
    mappings: List[FieldMapping] = []
    unmapped_columns: List[str] = []
    unmapped_entries: List[str] = []