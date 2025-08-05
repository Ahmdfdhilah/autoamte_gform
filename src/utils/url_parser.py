"""
URL parameter parser to extract entry IDs in order
"""

import re
import logging
from urllib.parse import urlparse, parse_qs
from typing import List

logger = logging.getLogger(__name__)


def extract_entry_order_from_url(form_url: str) -> List[str]:
    """Extract entry IDs in order from prefilled URL"""
    try:
        # Parse URL to get query parameters
        parsed_url = urlparse(form_url)
        
        # Get the full query string to preserve order
        query_string = parsed_url.query
        
        # Extract all entry parameters in order they appear
        entry_pattern = r'entry\.(\d+)='
        entries = re.findall(entry_pattern, query_string)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_entries = []
        for entry in entries:
            entry_key = f"entry.{entry}"
            if entry_key not in seen:
                seen.add(entry_key)
                unique_entries.append(entry_key)
        
        logger.info(f"✅ Extracted {len(unique_entries)} entry IDs from URL in order")
        return unique_entries
        
    except Exception as e:
        logger.error(f"Error extracting entry order from URL: {e}")
        return []


def get_clean_form_url(form_url: str) -> str:
    """Get clean form URL without parameters for submission"""
    try:
        base_url = form_url.split('?')[0]
        return base_url.replace('/viewform', '/formResponse')
    except Exception as e:
        logger.error(f"Error creating clean URL: {e}")
        return None


def generate_prefilled_url(base_form_url: str, entry_order: List[str], form_data: dict) -> str:
    """Generate prefilled URL with CSV data"""
    try:
        # Get clean base URL
        base_url = base_form_url.split('?')[0]
        
        # Build query parameters
        params = []
        params.append("usp=pp_url")  # Standard prefilled parameter
        
        # Add entry data in order
        for entry_key in entry_order:
            if entry_key in form_data:
                value = form_data[entry_key]
                if value and str(value).strip():  # Only add non-empty values
                    # URL encode the value
                    import urllib.parse
                    encoded_value = urllib.parse.quote_plus(str(value))
                    params.append(f"{entry_key}={encoded_value}")
        
        # Combine base URL with parameters
        prefilled_url = f"{base_url}?{'&'.join(params)}"
        
        logger.info(f"✅ Generated prefilled URL with {len([p for p in params if 'entry.' in p])} entries")
        return prefilled_url
        
    except Exception as e:
        logger.error(f"Error generating prefilled URL: {e}")
        return base_form_url