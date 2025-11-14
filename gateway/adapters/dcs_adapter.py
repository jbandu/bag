"""
DCS Adapter
===========

Adapter for Departure Control System (Amadeus/Sabre).

Handles:
- Passenger PNR retrieval
- Baggage information
- Check-in status

Version: 1.0.0
"""

from typing import Dict, Any
from datetime import datetime
import time
from loguru import logger

from gateway.adapters.base_adapter import BaseAdapter, AdapterConfig


class DCSAdapter(BaseAdapter):
    """DCS API adapter"""

    def __init__(self, config: AdapterConfig):
        super().__init__("dcs", config)

    def get_pnr(self, pnr: str) -> Dict[str, Any]:
        """Get passenger booking"""
        start_time = time.time()

        try:
            logger.info(f"Fetching PNR: {pnr}")

            # Mock response
            result = {
                "pnr": pnr,
                "passenger": {
                    "surname": "SMITH",
                    "given_name": "JOHN",
                    "email": "john.smith@example.com"
                },
                "itinerary": {
                    "origin": "LAX",
                    "destination": "JFK",
                    "outbound_flight": {"carrier": "AA", "number": "123"}
                }
            }

            latency = (time.time() - start_time) * 1000
            self._log_call("get_pnr", True, latency)
            return result

        except Exception as e:
            latency = (time.time() - start_time) * 1000
            self._log_call("get_pnr", False, latency, str(e))
            raise

    def get_baggage(self, bag_tag: str) -> Dict[str, Any]:
        """Get baggage information"""
        start_time = time.time()

        try:
            logger.info(f"Fetching baggage: {bag_tag}")

            result = {
                "bag_tag": bag_tag,
                "passenger": "SMITH/JOHN",
                "weight_kg": 23.5,
                "destination": "JFK"
            }

            latency = (time.time() - start_time) * 1000
            self._log_call("get_baggage", True, latency)
            return result

        except Exception as e:
            latency = (time.time() - start_time) * 1000
            self._log_call("get_baggage", False, latency, str(e))
            raise
