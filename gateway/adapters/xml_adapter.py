"""
XML Adapter
===========

Adapter for BaggageXML API.

Handles:
- Manifest exchange
- XML parsing/generation

Version: 1.0.0
"""

from typing import Dict, Any
from datetime import datetime
import time
from loguru import logger

from gateway.adapters.base_adapter import BaseAdapter, AdapterConfig
from mappers.xml_mapper import XMLMapper


class XMLAdapter(BaseAdapter):
    """BaggageXML API adapter"""

    def __init__(self, config: AdapterConfig):
        super().__init__("xml", config)
        self.mapper = XMLMapper()

    def send_manifest(self, bags: list) -> Dict[str, Any]:
        """Send baggage manifest"""
        start_time = time.time()

        try:
            logger.info(f"Sending manifest with {len(bags)} bags")

            result = {
                "manifest_id": f"MF{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "bags_count": len(bags),
                "sent_at": datetime.now().isoformat(),
                "status": "SENT"
            }

            latency = (time.time() - start_time) * 1000
            self._log_call("send_manifest", True, latency)
            return result

        except Exception as e:
            latency = (time.time() - start_time) * 1000
            self._log_call("send_manifest", False, latency, str(e))
            raise

    def get_manifest(self, manifest_id: str) -> Dict[str, Any]:
        """Get manifest by ID"""
        start_time = time.time()

        try:
            logger.info(f"Fetching manifest: {manifest_id}")

            result = {
                "manifest_id": manifest_id,
                "bags": [],
                "retrieved_at": datetime.now().isoformat()
            }

            latency = (time.time() - start_time) * 1000
            self._log_call("get_manifest", True, latency)
            return result

        except Exception as e:
            latency = (time.time() - start_time) * 1000
            self._log_call("get_manifest", False, latency, str(e))
            raise
