"""
BHS Adapter
===========

Adapter for Baggage Handling System.

Handles:
- Bag location tracking
- Scan history
- Real-time updates

Version: 1.0.0
"""

from typing import Dict, Any, List
from datetime import datetime
import time
from loguru import logger

from gateway.adapters.base_adapter import BaseAdapter, AdapterConfig


class BHSAdapter(BaseAdapter):
    """BHS API adapter"""

    def __init__(self, config: AdapterConfig):
        super().__init__("bhs", config)

    def get_location(self, bag_tag: str) -> Dict[str, Any]:
        """Get current bag location"""
        start_time = time.time()

        try:
            logger.info(f"Getting location for bag: {bag_tag}")

            result = {
                "bag_tag": bag_tag,
                "location": "LAX_T4_SORT_01",
                "location_type": "SORTATION",
                "timestamp": datetime.now().isoformat()
            }

            latency = (time.time() - start_time) * 1000
            self._log_call("get_location", True, latency)
            return result

        except Exception as e:
            latency = (time.time() - start_time) * 1000
            self._log_call("get_location", False, latency, str(e))
            raise

    def get_scan_history(self, bag_tag: str) -> List[Dict[str, Any]]:
        """Get scan history"""
        start_time = time.time()

        try:
            logger.info(f"Getting scan history for: {bag_tag}")

            result = [
                {
                    "type": "CHECKIN",
                    "location": "LAX_T4_CKI_12",
                    "timestamp": "2025-11-13T10:00:00Z"
                },
                {
                    "type": "SORTATION",
                    "location": "LAX_T4_SORT_01",
                    "timestamp": "2025-11-13T10:15:00Z"
                }
            ]

            latency = (time.time() - start_time) * 1000
            self._log_call("get_scan_history", True, latency)
            return result

        except Exception as e:
            latency = (time.time() - start_time) * 1000
            self._log_call("get_scan_history", False, latency, str(e))
            raise
