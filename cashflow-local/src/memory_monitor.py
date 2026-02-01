"""
Memory monitoring utilities for CashFlow-Local

Provides lightweight memory profiling to help identify memory issues.
"""

import logging
import psutil
import os
from typing import Dict, Any

logger = logging.getLogger(__name__)


class MemoryMonitor:
    """Simple memory monitoring utility."""
    
    @staticmethod
    def get_memory_usage() -> Dict[str, Any]:
        """
        Get current memory usage statistics.
        
        Returns:
            Dictionary with memory metrics in MB
        """
        try:
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            
            return {
                'rss_mb': memory_info.rss / (1024 * 1024),  # Resident Set Size
                'vms_mb': memory_info.vms / (1024 * 1024),  # Virtual Memory Size
                'percent': process.memory_percent(),
            }
        except Exception as e:
            logger.warning(f"Failed to get memory usage: {e}")
            return {'rss_mb': 0, 'vms_mb': 0, 'percent': 0}
    
    @staticmethod
    def log_memory_usage(label: str = ""):
        """
        Log current memory usage with optional label.
        
        Args:
            label: Optional label for the log message
        """
        usage = MemoryMonitor.get_memory_usage()
        label_str = f"[{label}] " if label else ""
        logger.info(
            f"{label_str}Memory: RSS={usage['rss_mb']:.1f}MB, "
            f"VMS={usage['vms_mb']:.1f}MB, "
            f"Percent={usage['percent']:.1f}%"
        )


# Singleton instance
memory_monitor = MemoryMonitor()
