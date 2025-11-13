"""
Mappers Package
===============

Bidirectional mappers between external formats and canonical bag model.

Available mappers:
- DCSMapper: Departure Control System
- BHSMapper: Baggage Handling System
- WorldTracerMapper: IATA WorldTracer PIR
- TypeBMapper: SITA Type B messages (BTM/BSM/BPM)
- XMLMapper: BaggageXML format
"""

from mappers.dcs_mapper import DCSMapper
from mappers.bhs_mapper import BHSMapper
from mappers.worldtracer_mapper import WorldTracerMapper
from mappers.typeb_mapper import TypeBMapper
from mappers.xml_mapper import XMLMapper

__all__ = [
    'DCSMapper',
    'BHSMapper',
    'WorldTracerMapper',
    'TypeBMapper',
    'XMLMapper'
]
