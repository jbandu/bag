"""
Test Fixtures for Workflow Data
Test data for LangGraph workflow testing
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any
import random


# Workflow input templates
SCAN_PROCESSOR_INPUT = {
    "scan_data": {
        "bag_tag": "CM123456",
        "location": "PTY_RAMP",
        "scan_type": "ARRIVAL_SCAN",
        "scanned_at": datetime.utcnow().isoformat() + "Z",
        "scanned_by": "AGENT_101",
        "device_id": "SCANNER_05",
        "confidence_score": 0.95
    },
    "context": {
        "flight_number": "CM101",
        "expected_location": "PTY_RAMP",
        "expected_time_window": {
            "start": (datetime.utcnow() - timedelta(hours=1)).isoformat() + "Z",
            "end": (datetime.utcnow() + timedelta(hours=1)).isoformat() + "Z"
        }
    }
}

MISHANDLED_BAG_WORKFLOW_INPUT = {
    "bag_tag": "CM777777",
    "incident_type": "delayed_arrival",
    "discovery_location": "MIA_BAGGAGE_CLAIM",
    "discovery_time": datetime.utcnow().isoformat() + "Z",
    "passenger": {
        "passenger_name": "Maria Garcia",
        "pnr": "MNO777",
        "contact": {
            "email": "maria.garcia@example.com",
            "phone": "+507-555-7777"
        },
        "loyalty_tier": "Platinum"
    },
    "flight": {
        "flight_number": "CM777",
        "origin": "PTY",
        "destination": "MIA",
        "arrival_time": (datetime.utcnow() - timedelta(hours=2)).isoformat() + "Z"
    },
    "last_known_location": "PTY_RAMP",
    "last_known_scan": (datetime.utcnow() - timedelta(hours=4)).isoformat() + "Z",
    "urgency": "high"
}

TRANSFER_COORDINATION_INPUT = {
    "bag_tag": "CM555555",
    "inbound_flight": {
        "flight_number": "CM101",
        "origin": "PTY",
        "destination": "MIA",
        "arrival_time": (datetime.utcnow() + timedelta(minutes=30)).isoformat() + "Z",
        "arrival_gate": "D12"
    },
    "outbound_flight": {
        "flight_number": "CM555",
        "origin": "MIA",
        "destination": "GRU",
        "departure_time": (datetime.utcnow() + timedelta(hours=2)).isoformat() + "Z",
        "departure_gate": "E5",
        "boarding_time": (datetime.utcnow() + timedelta(hours=1, minutes=30)).isoformat() + "Z"
    },
    "connection_time_minutes": 90,
    "minimum_connection_time": 45,
    "transfer_path": ["MIA_RAMP", "MIA_TRANSFER", "MIA_SORTING", "MIA_E_CONCOURSE"],
    "risk_factors": ["tight_connection", "gate_distance"]
}

COURIER_BOOKING_INPUT = {
    "bag_tag": "CM888888",
    "passenger": {
        "passenger_name": "David Martinez",
        "pnr": "PQR888",
        "contact": {
            "email": "david.martinez@example.com",
            "phone": "+507-555-8888"
        },
        "delivery_address": {
            "street": "123 Main Street",
            "city": "Miami",
            "state": "FL",
            "zip": "33101",
            "country": "USA"
        }
    },
    "current_location": "MIA_STORAGE",
    "delivery_type": "same_day",
    "delivery_priority": "high",
    "special_instructions": "Call passenger 30 minutes before delivery",
    "compensation_approved": True,
    "compensation_amount": 100.00
}

PIR_CREATION_INPUT = {
    "incident_type": "mishandled_bag",
    "bag_tag": "CM777777",
    "passenger": {
        "passenger_name": "Maria Garcia",
        "pnr": "MNO777",
        "contact": {
            "email": "maria.garcia@example.com",
            "phone": "+507-555-7777"
        },
        "address": {
            "street": "456 Oak Avenue",
            "city": "Miami",
            "state": "FL",
            "zip": "33102",
            "country": "USA"
        }
    },
    "flight": {
        "flight_number": "CM777",
        "date": datetime.utcnow().date().isoformat(),
        "origin": "PTY",
        "destination": "MIA"
    },
    "bag_description": {
        "type": "suitcase",
        "color": "black",
        "brand": "Samsonite",
        "size": "large",
        "distinctive_features": "Red ribbon on handle"
    },
    "contents_value": 500.00,
    "interim_needs": ["toiletries", "change_of_clothes"],
    "reported_by": "AGENT_205",
    "reported_at": datetime.utcnow().isoformat() + "Z"
}


# Workflow state templates
WORKFLOW_STATES = {
    "scan_processor": {
        "initial": {
            "state": "initiated",
            "scan_data": SCAN_PROCESSOR_INPUT["scan_data"],
            "validated": False,
            "enriched": False,
            "risk_assessed": False
        },
        "validated": {
            "state": "validated",
            "scan_data": SCAN_PROCESSOR_INPUT["scan_data"],
            "validated": True,
            "validation_results": {
                "bag_tag_valid": True,
                "location_valid": True,
                "timestamp_valid": True,
                "device_authorized": True
            },
            "enriched": False,
            "risk_assessed": False
        },
        "completed": {
            "state": "completed",
            "scan_data": SCAN_PROCESSOR_INPUT["scan_data"],
            "validated": True,
            "enriched": True,
            "risk_assessed": True,
            "risk_score": 0.15,
            "actions_taken": ["update_location", "notify_next_handler"]
        }
    },
    "mishandled_bag": {
        "initial": {
            "state": "incident_reported",
            "bag_tag": "CM777777",
            "incident_type": "delayed_arrival",
            "pir_created": False,
            "worldtracer_filed": False,
            "passenger_notified": False,
            "search_initiated": False
        },
        "in_progress": {
            "state": "investigation",
            "bag_tag": "CM777777",
            "pir_created": True,
            "pir_number": "MIAPTY20250115001",
            "worldtracer_filed": True,
            "worldtracer_ref": "CMAA123456",
            "passenger_notified": True,
            "search_initiated": True,
            "search_locations": ["PTY_RAMP", "PTY_STORAGE", "MIA_TRANSFER"]
        },
        "resolved": {
            "state": "resolved",
            "bag_tag": "CM777777",
            "resolution": "bag_found",
            "found_location": "PTY_STORAGE",
            "delivery_method": "courier",
            "courier_booking_id": "DHL123456789",
            "estimated_delivery": (datetime.utcnow() + timedelta(hours=24)).isoformat() + "Z",
            "compensation_offered": 100.00
        }
    },
    "transfer_coordination": {
        "initial": {
            "state": "monitoring",
            "bag_tag": "CM555555",
            "inbound_landed": False,
            "bag_unloaded": False,
            "in_transfer": False,
            "loaded_outbound": False
        },
        "in_progress": {
            "state": "active_transfer",
            "bag_tag": "CM555555",
            "inbound_landed": True,
            "bag_unloaded": True,
            "in_transfer": True,
            "current_location": "MIA_TRANSFER",
            "estimated_completion": (datetime.utcnow() + timedelta(minutes=45)).isoformat() + "Z",
            "on_track": True
        },
        "at_risk": {
            "state": "at_risk",
            "bag_tag": "CM555555",
            "inbound_delayed": True,
            "delay_minutes": 25,
            "connection_at_risk": True,
            "contingency_plan": "expedited_transfer",
            "ground_crew_notified": True,
            "alternative_routing_prepared": True
        },
        "completed": {
            "state": "completed",
            "bag_tag": "CM555555",
            "transfer_successful": True,
            "loaded_outbound": True,
            "time_to_complete_minutes": 42,
            "connection_made": True
        }
    }
}


# Expected workflow outputs
WORKFLOW_OUTPUTS = {
    "scan_processor_success": {
        "status": "success",
        "bag_tag": "CM123456",
        "scan_processed": True,
        "risk_score": 0.15,
        "risk_level": "low",
        "actions": [
            {
                "action": "update_bag_location",
                "location": "PTY_RAMP",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            },
            {
                "action": "publish_event",
                "event_type": "bag_scanned",
                "subscribers": ["tracking_service", "analytics"]
            }
        ],
        "processing_time_ms": 245
    },
    "mishandled_bag_success": {
        "status": "success",
        "bag_tag": "CM777777",
        "pir_number": "MIAPTY20250115001",
        "worldtracer_reference": "CMAA123456",
        "resolution": "bag_found_and_delivered",
        "actions_completed": [
            "pir_created",
            "worldtracer_filed",
            "passenger_notified",
            "bag_located",
            "courier_booked",
            "compensation_processed"
        ],
        "resolution_time_hours": 18,
        "customer_satisfaction_score": 4.5
    },
    "transfer_coordination_success": {
        "status": "success",
        "bag_tag": "CM555555",
        "connection_made": True,
        "transfer_time_minutes": 42,
        "on_time": True,
        "actions_completed": [
            "inbound_tracked",
            "bag_unloaded",
            "transfer_routed",
            "outbound_loaded",
            "confirmation_sent"
        ]
    },
    "courier_booking_success": {
        "status": "success",
        "bag_tag": "CM888888",
        "courier_provider": "DHL",
        "tracking_number": "DHL123456789",
        "pickup_scheduled": (datetime.utcnow() + timedelta(hours=2)).isoformat() + "Z",
        "estimated_delivery": (datetime.utcnow() + timedelta(hours=24)).isoformat() + "Z",
        "cost": 45.00,
        "passenger_notified": True
    },
    "pir_creation_success": {
        "status": "success",
        "pir_number": "MIAPTY20250115001",
        "worldtracer_reference": "CMAA123456",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "case_priority": "high",
        "assigned_agent": "AGENT_305",
        "estimated_resolution_time": 24
    }
}


# Error scenarios for testing
ERROR_SCENARIOS = {
    "invalid_bag_tag": {
        "input": {
            **SCAN_PROCESSOR_INPUT,
            "scan_data": {
                **SCAN_PROCESSOR_INPUT["scan_data"],
                "bag_tag": "INVALID"
            }
        },
        "expected_error": "Invalid bag tag format"
    },
    "duplicate_pir": {
        "input": MISHANDLED_BAG_WORKFLOW_INPUT,
        "expected_error": "PIR already exists for this bag"
    },
    "impossible_connection": {
        "input": {
            **TRANSFER_COORDINATION_INPUT,
            "connection_time_minutes": 15,
            "minimum_connection_time": 45
        },
        "expected_error": "Connection time below minimum"
    },
    "courier_service_unavailable": {
        "input": COURIER_BOOKING_INPUT,
        "expected_error": "No courier service available for delivery area"
    }
}


# Performance test scenarios
PERFORMANCE_SCENARIOS = {
    "high_volume_scans": {
        "concurrent_workflows": 100,
        "input_template": SCAN_PROCESSOR_INPUT,
        "expected_max_duration_ms": 500,
        "expected_success_rate": 0.99
    },
    "bulk_mishandled_bags": {
        "concurrent_workflows": 50,
        "input_template": MISHANDLED_BAG_WORKFLOW_INPUT,
        "expected_max_duration_ms": 2000,
        "expected_success_rate": 0.95
    },
    "peak_transfer_load": {
        "concurrent_workflows": 200,
        "input_template": TRANSFER_COORDINATION_INPUT,
        "expected_max_duration_ms": 1000,
        "expected_success_rate": 0.98
    }
}


def generate_workflow_input(workflow_type: str, **overrides) -> Dict[str, Any]:
    """Generate workflow input with optional overrides"""
    templates = {
        "scan_processor": SCAN_PROCESSOR_INPUT,
        "mishandled_bag": MISHANDLED_BAG_WORKFLOW_INPUT,
        "transfer_coordination": TRANSFER_COORDINATION_INPUT,
        "courier_booking": COURIER_BOOKING_INPUT,
        "pir_creation": PIR_CREATION_INPUT
    }

    template = templates.get(workflow_type, {})
    return {**template, **overrides}


def generate_bulk_workflow_inputs(
    workflow_type: str,
    count: int = 10,
    **overrides
) -> List[Dict[str, Any]]:
    """Generate multiple workflow inputs for bulk testing"""
    inputs = []
    for i in range(count):
        input_data = generate_workflow_input(workflow_type, **overrides)
        # Vary bag tags
        if "bag_tag" in input_data:
            input_data["bag_tag"] = f"CM{100000 + i}"
        inputs.append(input_data)
    return inputs
