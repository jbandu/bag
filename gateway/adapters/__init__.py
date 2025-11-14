"""
Gateway Adapters
================

Adapters for all external systems.

Available adapters:
- DCSAdapter: Departure Control System (Amadeus/Sabre)
- BHSAdapter: Baggage Handling System
- WorldTracerAdapter: IATA WorldTracer PIR
- TypeBAdapter: SITA Type B messaging
- XMLAdapter: BaggageXML API
- CourierAdapter: 3PL services (FedEx, UPS, DHL)
- NotificationAdapter: SMS/Email/Push (Twilio, SendGrid, Firebase)
"""

from gateway.adapters.base_adapter import BaseAdapter, AdapterConfig
from gateway.adapters.dcs_adapter import DCSAdapter
from gateway.adapters.bhs_adapter import BHSAdapter
from gateway.adapters.worldtracer_adapter import WorldTracerAdapter
from gateway.adapters.typeb_adapter import TypeBAdapter
from gateway.adapters.xml_adapter import XMLAdapter
from gateway.adapters.courier_adapter import CourierAdapter
from gateway.adapters.notification_adapter import NotificationAdapter

__all__ = [
    'BaseAdapter',
    'AdapterConfig',
    'DCSAdapter',
    'BHSAdapter',
    'WorldTracerAdapter',
    'TypeBAdapter',
    'XMLAdapter',
    'CourierAdapter',
    'NotificationAdapter'
]
