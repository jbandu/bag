"""
WorldTracer Adapter
===================

Adapter for IATA WorldTracer API (PIR management).

Handles:
- Creating PIRs (Property Irregularity Reports)
- Updating PIR status
- Querying PIRs
- Authentication via SITA network

Version: 1.0.0
"""

from typing import Dict, Any, Optional
from datetime import datetime
import time
from loguru import logger

from gateway.adapters.base_adapter import BaseAdapter, AdapterConfig
from models.canonical_bag import CanonicalBag
from mappers.worldtracer_mapper import WorldTracerMapper


class WorldTracerAdapter(BaseAdapter):
    """WorldTracer API adapter"""

    def __init__(self, config: AdapterConfig):
        super().__init__("worldtracer", config)
        self.mapper = WorldTracerMapper()

    def create_pir(
        self,
        bag: CanonicalBag,
        irregularity_type: str,
        description: str
    ) -> Dict[str, Any]:
        """
        Create Property Irregularity Report

        Args:
            bag: Canonical bag data
            irregularity_type: DELAYED, DAMAGED, LOST, etc.
            description: Issue description

        Returns:
            PIR details with OHD reference
        """
        start_time = time.time()

        try:
            logger.info(f"Creating PIR for bag {bag.bag_tag}: {irregularity_type}")

            # Convert canonical to WorldTracer format
            wt_data = self.mapper.from_canonical(bag)
            wt_data['pir_type'] = irregularity_type
            wt_data['irregularity']['remarks'] = description

            # In real implementation: POST to WorldTracer API
            # response = requests.post(f"{self.config.base_url}/pir/create", ...)

            # Mock response
            ohd_reference = f"{bag.origin.iata_code}{bag.outbound_flight.airline_code}{datetime.now().strftime('%H%M%S')}"

            result = {
                "ohd_reference": ohd_reference,
                "status": "CREATED",
                "created_at": datetime.now().isoformat(),
                "bag_tag": bag.bag_tag
            }

            latency = (time.time() - start_time) * 1000
            self._log_call("create_pir", True, latency)

            return result

        except Exception as e:
            latency = (time.time() - start_time) * 1000
            self._log_call("create_pir", False, latency, str(e))
            raise

    def update_status(
        self,
        pir_reference: str,
        status: str,
        location: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update PIR status"""
        start_time = time.time()

        try:
            logger.info(f"Updating PIR {pir_reference} to status {status}")

            # In real implementation: PUT to WorldTracer API
            result = {
                "ohd_reference": pir_reference,
                "status": status,
                "updated_at": datetime.now().isoformat()
            }

            if location:
                result["current_location"] = location

            latency = (time.time() - start_time) * 1000
            self._log_call("update_status", True, latency)

            return result

        except Exception as e:
            latency = (time.time() - start_time) * 1000
            self._log_call("update_status", False, latency, str(e))
            raise

    def get_pir(self, pir_reference: str) -> Dict[str, Any]:
        """Get PIR details"""
        start_time = time.time()

        try:
            logger.info(f"Fetching PIR {pir_reference}")

            # In real implementation: GET from WorldTracer API
            result = {
                "ohd_reference": pir_reference,
                "status": "TRACING",
                "created_at": datetime.now().isoformat(),
                "pir_type": "DELAYED"
            }

            latency = (time.time() - start_time) * 1000
            self._log_call("get_pir", True, latency)

            return result

        except Exception as e:
            latency = (time.time() - start_time) * 1000
            self._log_call("get_pir", False, latency, str(e))
            raise
