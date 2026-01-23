#!/usr/bin/env python3
"""
Initialize DataLake directory structure.

Creates the medallion architecture folders:
- data_lake/raw/orders
- data_lake/processed/daily_sales
"""

from pathlib import Path
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def init_datalake(base_path: str = "data_lake") -> bool:
    """
    Initialize DataLake directory structure.
    
    Args:
        base_path: Root path for DataLake (default: data_lake/)
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        base = Path(base_path)
        
        # Bronze layer
        bronze_orders = base / "raw" / "orders"
        bronze_orders.mkdir(parents=True, exist_ok=True)
        logger.info(f"✓ Created bronze layer: {bronze_orders}")
        
        # Silver layer
        silver_sales = base / "processed" / "daily_sales"
        silver_sales.mkdir(parents=True, exist_ok=True)
        logger.info(f"✓ Created silver layer: {silver_sales}")
        
        # Create .gitkeep files to preserve empty directories in git
        for layer_dir in [bronze_orders, silver_sales]:
            gitkeep = layer_dir / ".gitkeep"
            gitkeep.touch()
            logger.info(f"✓ Created {gitkeep}")
        
        logger.info("\n✓ DataLake initialized successfully!")
        logger.info(f"Root: {base.resolve()}")
        return True
        
    except Exception as e:
        logger.error(f"✗ Failed to initialize DataLake: {e}")
        return False


if __name__ == "__main__":
    success = init_datalake()
    sys.exit(0 if success else 1)
