"""
Service untuk analisis form Google Forms secara dinamis per URL
"""

import logging
from typing import Dict, List, Optional, Tuple
from ....utils.field_analyzer import FormFieldAnalyzer
from ...schemas import FormField, FieldMapping

logger = logging.getLogger(__name__)

class DynamicFormAnalyzer:
    """Analyzer untuk menganalisis Google Form secara dinamis berdasarkan URL"""
    
    def __init__(self):
        self.field_analyzer = FormFieldAnalyzer()
    
    def analyze_form(self, form_url: str) -> Dict:
        """
        Analisis form Google berdasarkan URL
        
        Args:
            form_url: URL Google Form
            
        Returns:
            Dict berisi informasi form dan fields
        """
        try:
            logger.info(f"🔍 Analyzing form: {form_url}")
            
            # Analisis field types dari URL
            field_types = self.field_analyzer.analyze_field_types_from_url(form_url)
            
            if not field_types:
                logger.error("Failed to extract field information from form")
                return {
                    'success': False,
                    'message': 'Failed to analyze form fields',
                    'fields': [],
                    'total_fields': 0
                }
            
            # Convert ke format FormField
            form_fields = []
            for entry_id, field_info in field_types.items():
                form_field = FormField(
                    entry_id=entry_id,
                    field_type=field_info['type'],
                    label=f"Field {entry_id.replace('entry.', '')}",  # Default label
                    required=False,  # Default, bisa diupdate jika ada info lebih
                    options=field_info.get('sample_values', []) if field_info.get('multiple_values') else None
                )
                form_fields.append(form_field)
            
            logger.info(f"✅ Successfully analyzed {len(form_fields)} fields")
            
            # Hitung statistik field types
            type_stats = {}
            for field in form_fields:
                field_type = field.field_type
                type_stats[field_type] = type_stats.get(field_type, 0) + 1
            
            logger.info("📊 Field type distribution:")
            for field_type, count in type_stats.items():
                logger.info(f"  - {field_type}: {count} fields")
            
            return {
                'success': True,
                'message': f'Successfully analyzed {len(form_fields)} form fields',
                'fields': form_fields,
                'total_fields': len(form_fields),
                'type_stats': type_stats,
                'form_url': form_url
            }
            
        except Exception as e:
            logger.error(f"❌ Form analysis error: {str(e)}")
            return {
                'success': False,
                'message': f'Form analysis failed: {str(e)}',
                'fields': [],
                'total_fields': 0
            }
    
    def map_csv_to_form(self, form_url: str, csv_headers: List[str]) -> Dict:
        """
        Mapping header CSV dengan form fields
        
        Args:
            form_url: URL Google Form
            csv_headers: List header dari CSV
            
        Returns:
            Dict berisi mapping information
        """
        try:
            logger.info(f"🔗 Mapping CSV headers to form fields")
            logger.info(f"📋 CSV headers: {csv_headers}")
            
            # Analisis form terlebih dahulu
            form_analysis = self.analyze_form(form_url)
            if not form_analysis['success']:
                return form_analysis
            
            form_fields = form_analysis['fields']
            
            # Simple mapping berdasarkan nama field
            mappings = []
            unmapped_columns = []
            unmapped_entries = []
            
            # Entry fields yang tersedia
            available_entries = {field.entry_id: field for field in form_fields}
            used_entries = set()
            
            # Coba mapping setiap header CSV
            for header in csv_headers:
                mapped = False
                
                # Cari exact match dengan entry ID
                if header in available_entries:
                    field = available_entries[header]
                    mapping = FieldMapping(
                        csv_column=header,
                        form_entry=header,
                        field_type=field.field_type,
                        confidence=1.0
                    )
                    mappings.append(mapping)
                    used_entries.add(header)
                    mapped = True
                    logger.info(f"✅ Exact match: {header} -> {header}")
                
                # Jika tidak ada exact match, coba fuzzy matching
                if not mapped:
                    # Implementasi sederhana: cari berdasarkan similarity
                    best_match = None
                    best_confidence = 0.0
                    
                    for entry_id, field in available_entries.items():
                        if entry_id not in used_entries:
                            # Simple similarity check (bisa diperbaiki dengan algoritma yang lebih baik)
                            if header.lower() in entry_id.lower() or entry_id.lower() in header.lower():
                                confidence = 0.7
                                if confidence > best_confidence:
                                    best_confidence = confidence
                                    best_match = (entry_id, field)
                    
                    if best_match and best_confidence > 0.5:
                        entry_id, field = best_match
                        mapping = FieldMapping(
                            csv_column=header,
                            form_entry=entry_id,
                            field_type=field.field_type,
                            confidence=best_confidence
                        )
                        mappings.append(mapping)
                        used_entries.add(entry_id)
                        mapped = True
                        logger.info(f"🔍 Fuzzy match: {header} -> {entry_id} (confidence: {best_confidence})")
                
                if not mapped:
                    unmapped_columns.append(header)
                    logger.warning(f"❓ Unmapped column: {header}")
            
            # Entry yang tidak terpakai
            for entry_id in available_entries:
                if entry_id not in used_entries:
                    unmapped_entries.append(entry_id)
            
            logger.info(f"📊 Mapping results:")
            logger.info(f"  - Mapped: {len(mappings)} fields")
            logger.info(f"  - Unmapped columns: {len(unmapped_columns)}")
            logger.info(f"  - Unmapped entries: {len(unmapped_entries)}")
            
            return {
                'success': True,
                'message': f'Successfully mapped {len(mappings)} fields',
                'mappings': mappings,
                'unmapped_columns': unmapped_columns,
                'unmapped_entries': unmapped_entries,
                'mapping_stats': {
                    'total_columns': len(csv_headers),
                    'mapped_fields': len(mappings),
                    'unmapped_columns': len(unmapped_columns),
                    'unmapped_entries': len(unmapped_entries)
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Field mapping error: {str(e)}")
            return {
                'success': False,
                'message': f'Field mapping failed: {str(e)}',
                'mappings': [],
                'unmapped_columns': csv_headers.copy(),
                'unmapped_entries': []
            }
    
    def get_field_types_for_url(self, form_url: str) -> Dict:
        """
        Generate field types configuration untuk URL tertentu
        
        Args:
            form_url: URL Google Form
            
        Returns:
            Dict field types dalam format yang bisa digunakan sistem
        """
        try:
            logger.info(f"🔧 Generating field types for: {form_url}")
            
            # Analisis field types dari URL
            field_types = self.field_analyzer.analyze_field_types_from_url(form_url)
            
            if field_types:
                logger.info(f"✅ Generated field types for {len(field_types)} fields")
                return field_types
            else:
                logger.error("Failed to generate field types")
                return {}
                
        except Exception as e:
            logger.error(f"❌ Field types generation error: {str(e)}")
            return {}