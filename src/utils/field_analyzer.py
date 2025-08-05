"""
Field analyzer untuk menganalisis input types dari URL prefilled
"""

import logging
from urllib.parse import urlparse, parse_qs
from typing import Dict, List, Set
from collections import Counter

logger = logging.getLogger(__name__)


def analyze_field_types_from_url(form_url: str) -> Dict[str, Dict]:
    """Analyze field types from prefilled URL"""
    try:
        # Parse URL to get query parameters
        parsed_url = urlparse(form_url)
        params = parse_qs(parsed_url.query)
        
        field_info = {}
        entry_counts = Counter()
        
        # Count occurrences of each entry ID
        for param_name in params.keys():
            if param_name.startswith('entry.'):
                base_entry = param_name.split('.')[0] + '.' + param_name.split('.')[1]
                entry_counts[base_entry] += len(params[param_name])
        
        # Analyze each entry
        for param_name, values in params.items():
            if param_name.startswith('entry.') and not param_name.endswith('.other_option_response'):
                base_entry = param_name.split('.')[0] + '.' + param_name.split('.')[1]
                
                if base_entry not in field_info:
                    field_info[base_entry] = {
                        'type': 'text',  # default
                        'has_other_option': False,
                        'multiple_values': False,
                        'sample_values': []
                    }
                
                # Check if it's multiple choice (checkbox/multi-select)
                if entry_counts[base_entry] > 1:
                    field_info[base_entry]['type'] = 'checkbox'
                    field_info[base_entry]['multiple_values'] = True
                
                # Check for other option
                if '__other_option__' in values:
                    field_info[base_entry]['has_other_option'] = True
                
                # Store sample values (exclude __other_option__)
                sample_values = [v for v in values if v != '__other_option__']
                field_info[base_entry]['sample_values'] = sample_values
                
                # Determine type based on sample values
                if len(sample_values) > 0:
                    sample_val = sample_values[0].lower()
                    if sample_val in ['ya', 'tidak', 'yes', 'no']:
                        if not field_info[base_entry]['multiple_values']:
                            field_info[base_entry]['type'] = 'radio'
                    elif sample_val == 'text':
                        field_info[base_entry]['type'] = 'text'
                    elif sample_val.isdigit():
                        field_info[base_entry]['type'] = 'number'
                    elif len(sample_values) == 1 and not field_info[base_entry]['multiple_values']:
                        # Single selection dropdown
                        field_info[base_entry]['type'] = 'select'
        
        logger.info(f"✅ Analyzed {len(field_info)} field types from URL")
        return field_info
        
    except Exception as e:
        logger.error(f"Error analyzing field types: {e}")
        return {}


def generate_prefilled_url_with_types(base_form_url: str, entry_order: List[str], 
                                     form_data: dict, field_types: Dict[str, Dict]) -> str:
    """Generate prefilled URL with proper handling of different field types"""
    try:
        import urllib.parse
        
        # Get clean base URL
        base_url = base_form_url.split('?')[0]
        
        # Build query parameters
        params = []
        params.append("usp=pp_url")  # Standard prefilled parameter
        
        # Add ALL entry IDs in order with proper type handling
        for entry_key in entry_order:
            field_info = field_types.get(entry_key, {'type': 'text', 'multiple_values': False})
            
            if entry_key in form_data and form_data[entry_key] and str(form_data[entry_key]).strip():
                value = str(form_data[entry_key]).strip()
                
                # Handle multiple values for checkbox fields
                if field_info.get('multiple_values', False) and ',' in value:
                    # Split comma-separated values for checkbox
                    values = [v.strip() for v in value.split(',') if v.strip()]
                    for val in values:
                        encoded_value = urllib.parse.quote_plus(val)
                        params.append(f"{entry_key}={encoded_value}")
                else:
                    # Single value
                    encoded_value = urllib.parse.quote_plus(value)
                    params.append(f"{entry_key}={encoded_value}")
            else:
                # No data or empty - add empty placeholder to maintain structure
                params.append(f"{entry_key}=")
        
        # Combine base URL with parameters
        prefilled_url = f"{base_url}?{'&'.join(params)}"
        
        total_entries = len(entry_order)
        filled_entries = len([key for key in entry_order if key in form_data and form_data[key]])
        
        logger.info(f"✅ Generated prefilled URL with {total_entries} entries ({filled_entries} filled)")
        return prefilled_url
        
    except Exception as e:
        logger.error(f"Error generating prefilled URL: {e}")
        return base_form_url


def save_field_types_to_config(field_types: Dict[str, Dict], config_path: str = "field_types.py"):
    """Save analyzed field types to a config file"""
    try:
        with open(config_path, 'w') as f:
            f.write('"""\n')
            f.write('Auto-generated field types configuration\n')
            f.write('"""\n\n')
            f.write('FIELD_TYPES = {\n')
            
            for entry_id, info in field_types.items():
                f.write(f'    "{entry_id}": {{\n')
                f.write(f'        "type": "{info["type"]}",\n')
                f.write(f'        "multiple_values": {info["multiple_values"]},\n')
                f.write(f'        "has_other_option": {info["has_other_option"]},\n')
                f.write(f'        "sample_values": {info["sample_values"]}\n')
                f.write('    },\n')
            
            f.write('}\n')
        
        logger.info(f"✅ Field types saved to {config_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving field types: {e}")
        return False