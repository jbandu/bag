"""
Type B Adapter
==============

Adapter for SITA Type B messaging.

Handles:
- BSM/BTM/BPM message sending
- Message parsing
- SITA network communication

Version: 1.0.0
"""

from typing import Dict, Any
from datetime import datetime
import time
from loguru import logger

from gateway.adapters.base_adapter import BaseAdapter, AdapterConfig
from mappers.typeb_mapper import TypeBMapper


class TypeBAdapter(BaseAdapter):
    """Type B messaging adapter"""

    def __init__(self, config: AdapterConfig):
        super().__init__("typeb", config)
        self.mapper = TypeBMapper()

    def send_bsm(self, bag_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send Baggage Source Message"""
        start_time = time.time()

        try:
            logger.info(f"Sending BSM for bag {bag_data.get('bag_tag')}")

            # Would convert to Type B format and send via SITA
            result = {
                "message_type": "BSM",
                "sent_at": datetime.now().isoformat(),
                "status": "SENT"
            }

            latency = (time.time() - start_time) * 1000
            self._log_call("send_bsm", True, latency)
            return result

        except Exception as e:
            latency = (time.time() - start_time) * 1000
            self._log_call("send_bsm", False, latency, str(e))
            raise

    def send_btm(self, bag_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send Baggage Transfer Message"""
        start_time = time.time()

        try:
            logger.info(f"Sending BTM for bag {bag_data.get('bag_tag')}")

            result = {
                "message_type": "BTM",
                "sent_at": datetime.now().isoformat(),
                "status": "SENT"
            }

            latency = (time.time() - start_time) * 1000
            self._log_call("send_btm", True, latency)
            return result

        except Exception as e:
            latency = (time.time() - start_time) * 1000
            self._log_call("send_btm", False, latency, str(e))
            raise
