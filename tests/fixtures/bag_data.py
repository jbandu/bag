"""
Test Fixtures for Bag Data
Comprehensive test data for baggage tracking and workflows
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any
import random


def generate_bag_tag() -> str:
    """Generate a realistic bag tag number"""
    airline = random.choice(['CM', 'AA', 'UA', 'DL'])
    return f"{airline}{random.randint(100000, 999999)}"


def generate_flight_number() -> str:
    """Generate a realistic flight number"""
    airline = random.choice(['CM', 'AA', 'UA', 'DL'])
    return f"{airline}{random.randint(100, 9999)}"


def generate_passenger() -> Dict[str, Any]:
    """Generate test passenger data"""
    first_names = ['John', 'Jane', 'Maria', 'Carlos', 'Ana', 'David', 'Sofia']
    last_names = ['Smith', 'Garcia', 'Rodriguez', 'Martinez', 'Lopez', 'Johnson']

    return {
        "passenger_name": f"{random.choice(first_names)} {random.choice(last_names)}",
        "contact": {
            "email": f"test.passenger{random.randint(1000, 9999)}@example.com",
            "phone": f"+507-{random.randint(100, 999)}-{random.randint(1000, 9999)}"
        },
        "pnr": f"ABC{random.randint(100, 999)}",
        "frequent_flyer": random.choice([None, f"CM{random.randint(1000000, 9999999)}"]),
        "loyalty_tier": random.choice(['None', 'Silver', 'Gold', 'Platinum'])
    }


def generate_flight(origin: str = "PTY", destination: str = "MIA") -> Dict[str, Any]:
    """Generate test flight data"""
    now = datetime.utcnow()
    departure = now + timedelta(hours=random.randint(1, 24))
    arrival = departure + timedelta(hours=random.randint(2, 8))

    return {
        "flight_number": generate_flight_number(),
        "origin": origin,
        "destination": destination,
        "departure_time": departure.isoformat() + "Z",
        "arrival_time": arrival.isoformat() + "Z",
        "aircraft_type": random.choice(['B737', 'A320', 'B787', 'A321']),
        "status": random.choice(['Scheduled', 'Boarding', 'Departed', 'In Flight'])
    }


def generate_bag(
    status: str = "checked_in",
    risk_level: str = "low",
    origin: str = "PTY",
    destination: str = "MIA"
) -> Dict[str, Any]:
    """Generate test bag data"""
    passenger = generate_passenger()
    flight = generate_flight(origin, destination)

    return {
        "bag_tag": generate_bag_tag(),
        "passenger": passenger,
        "flight": flight,
        "status": status,
        "risk_level": risk_level,
        "weight_kg": round(random.uniform(10.0, 30.0), 1),
        "dimensions": {
            "length_cm": random.randint(50, 80),
            "width_cm": random.randint(30, 50),
            "height_cm": random.randint(20, 40)
        },
        "special_handling": random.choice([None, "Fragile", "Heavy", "Priority"]),
        "created_at": datetime.utcnow().isoformat() + "Z"
    }


def generate_scan_event(
    bag_tag: str,
    location: str = "PTY_BAGGAGE_CLAIM",
    scan_type: str = "ARRIVAL_SCAN"
) -> Dict[str, Any]:
    """Generate test scan event data"""
    return {
        "bag_tag": bag_tag,
        "location": location,
        "scan_type": scan_type,
        "scanned_at": datetime.utcnow().isoformat() + "Z",
        "scanned_by": f"AGENT_{random.randint(100, 999)}",
        "device_id": f"SCANNER_{random.randint(10, 99)}",
        "data_quality": random.choice(['good', 'fair', 'poor'])
    }


# Pre-defined test bags for specific scenarios
NORMAL_BAG = {
    "bag_tag": "CM123456",
    "passenger": {
        "passenger_name": "John Doe",
        "contact": {
            "email": "john.doe@example.com",
            "phone": "+507-555-1234"
        },
        "pnr": "ABC123",
        "frequent_flyer": "CM1234567",
        "loyalty_tier": "Gold"
    },
    "flight": {
        "flight_number": "CM101",
        "origin": "PTY",
        "destination": "MIA",
        "departure_time": (datetime.utcnow() + timedelta(hours=2)).isoformat() + "Z",
        "arrival_time": (datetime.utcnow() + timedelta(hours=5)).isoformat() + "Z",
        "aircraft_type": "B737",
        "status": "Scheduled"
    },
    "status": "checked_in",
    "risk_level": "low",
    "weight_kg": 22.5,
    "dimensions": {
        "length_cm": 70,
        "width_cm": 40,
        "height_cm": 30
    },
    "special_handling": None
}

HIGH_RISK_BAG = {
    "bag_tag": "CM999999",
    "passenger": {
        "passenger_name": "Jane Smith",
        "contact": {
            "email": "jane.smith@example.com",
            "phone": "+507-555-9999"
        },
        "pnr": "XYZ999",
        "frequent_flyer": None,
        "loyalty_tier": "None"
    },
    "flight": {
        "flight_number": "CM999",
        "origin": "PTY",
        "destination": "MIA",
        "departure_time": (datetime.utcnow() + timedelta(hours=1)).isoformat() + "Z",
        "arrival_time": (datetime.utcnow() + timedelta(hours=4)).isoformat() + "Z",
        "aircraft_type": "A320",
        "status": "Boarding"
    },
    "status": "checked_in",
    "risk_level": "high",
    "weight_kg": 29.9,
    "dimensions": {
        "length_cm": 80,
        "width_cm": 50,
        "height_cm": 40
    },
    "special_handling": "Priority"
}

MISHANDLED_BAG = {
    "bag_tag": "CM777777",
    "passenger": {
        "passenger_name": "Maria Garcia",
        "contact": {
            "email": "maria.garcia@example.com",
            "phone": "+507-555-7777"
        },
        "pnr": "MNO777",
        "frequent_flyer": "CM7777777",
        "loyalty_tier": "Platinum"
    },
    "flight": {
        "flight_number": "CM777",
        "origin": "PTY",
        "destination": "MIA",
        "departure_time": (datetime.utcnow() - timedelta(hours=3)).isoformat() + "Z",
        "arrival_time": (datetime.utcnow()).isoformat() + "Z",
        "aircraft_type": "B787",
        "status": "Arrived"
    },
    "status": "mishandled",
    "risk_level": "critical",
    "weight_kg": 25.0,
    "dimensions": {
        "length_cm": 75,
        "width_cm": 45,
        "height_cm": 35
    },
    "special_handling": "Fragile"
}

TRANSFER_BAG = {
    "bag_tag": "CM555555",
    "passenger": {
        "passenger_name": "Carlos Rodriguez",
        "contact": {
            "email": "carlos.rodriguez@example.com",
            "phone": "+507-555-5555"
        },
        "pnr": "DEF555",
        "frequent_flyer": "CM5555555",
        "loyalty_tier": "Silver"
    },
    "flight": {
        "flight_number": "CM555",
        "origin": "MIA",
        "destination": "GRU",
        "departure_time": (datetime.utcnow() + timedelta(hours=1)).isoformat() + "Z",
        "arrival_time": (datetime.utcnow() + timedelta(hours=9)).isoformat() + "Z",
        "aircraft_type": "B787",
        "status": "Boarding"
    },
    "status": "in_transit",
    "risk_level": "medium",
    "weight_kg": 23.0,
    "dimensions": {
        "length_cm": 72,
        "width_cm": 42,
        "height_cm": 32
    },
    "special_handling": None,
    "connecting_flight": {
        "flight_number": "CM101",
        "origin": "PTY",
        "destination": "MIA",
        "arrival_time": (datetime.utcnow() + timedelta(minutes=30)).isoformat() + "Z"
    }
}


# Scan event scenarios
SCAN_SCENARIOS = {
    "normal_journey": [
        {"scan_type": "CHECK_IN_SCAN", "location": "PTY_CHECK_IN"},
        {"scan_type": "SECURITY_SCAN", "location": "PTY_SECURITY"},
        {"scan_type": "LOAD_SCAN", "location": "PTY_RAMP"},
        {"scan_type": "ARRIVAL_SCAN", "location": "MIA_RAMP"},
        {"scan_type": "CLAIM_SCAN", "location": "MIA_BAGGAGE_CLAIM"}
    ],
    "delayed_journey": [
        {"scan_type": "CHECK_IN_SCAN", "location": "PTY_CHECK_IN"},
        {"scan_type": "SECURITY_SCAN", "location": "PTY_SECURITY"},
        {"scan_type": "HOLD_SCAN", "location": "PTY_HOLD"},
        {"scan_type": "LOAD_SCAN", "location": "PTY_RAMP"},
        {"scan_type": "ARRIVAL_SCAN", "location": "MIA_RAMP"},
        {"scan_type": "CLAIM_SCAN", "location": "MIA_BAGGAGE_CLAIM"}
    ],
    "mishandled_journey": [
        {"scan_type": "CHECK_IN_SCAN", "location": "PTY_CHECK_IN"},
        {"scan_type": "SECURITY_SCAN", "location": "PTY_SECURITY"},
        {"scan_type": "ARRIVAL_SCAN", "location": "BOG_RAMP"},  # Wrong airport!
        {"scan_type": "REROUTE_SCAN", "location": "BOG_TRANSFER"},
        {"scan_type": "LOAD_SCAN", "location": "BOG_RAMP"},
        {"scan_type": "ARRIVAL_SCAN", "location": "MIA_RAMP"},
        {"scan_type": "CLAIM_SCAN", "location": "MIA_BAGGAGE_CLAIM"}
    ],
    "transfer_journey": [
        {"scan_type": "CHECK_IN_SCAN", "location": "PTY_CHECK_IN"},
        {"scan_type": "TRANSFER_TAG_SCAN", "location": "PTY_TRANSFER"},
        {"scan_type": "LOAD_SCAN", "location": "PTY_RAMP"},
        {"scan_type": "ARRIVAL_SCAN", "location": "MIA_RAMP"},
        {"scan_type": "TRANSFER_SCAN", "location": "MIA_TRANSFER"},
        {"scan_type": "LOAD_SCAN", "location": "MIA_RAMP"},
        {"scan_type": "ARRIVAL_SCAN", "location": "GRU_RAMP"},
        {"scan_type": "CLAIM_SCAN", "location": "GRU_BAGGAGE_CLAIM"}
    ]
}


# Bulk test data generators
def generate_bulk_bags(count: int = 100, **kwargs) -> List[Dict[str, Any]]:
    """Generate multiple bags for bulk testing"""
    return [generate_bag(**kwargs) for _ in range(count)]


def generate_bulk_scans(bag_tags: List[str], scenario: str = "normal_journey") -> List[Dict[str, Any]]:
    """Generate multiple scan events for bulk testing"""
    scans = []
    scenario_scans = SCAN_SCENARIOS.get(scenario, SCAN_SCENARIOS["normal_journey"])

    for bag_tag in bag_tags:
        for scan_template in scenario_scans:
            scan = generate_scan_event(
                bag_tag=bag_tag,
                location=scan_template["location"],
                scan_type=scan_template["scan_type"]
            )
            scans.append(scan)

    return scans
