"""
Utility functions and helpers
"""

import logging
import pandas as pd

logger = logging.getLogger(__name__)


def create_sample_csv(filename: str = 'sample_data.csv'):
    """Create sample CSV file"""
    data = {
        'entry.625591749': ['Option 1', 'Option 2', 'Option 3'],
        'eta': ['2025-08-05 08:00:00', '2025-08-05 08:05:00', '2025-08-05 08:10:00'],
        'priority': ['high', 'normal', 'low']
    }
    
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False)
    logger.info(f"✅ Sample CSV created: {filename}")