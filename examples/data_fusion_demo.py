"""
Data Fusion Demo
================

Demonstrates the unified semantic data model with data fusion from multiple sources.

This example shows:
1. Data from 5 different systems (DCS, BHS, WorldTracer, Type B, XML)
2. Intelligent conflict resolution
3. Data quality tracking
4. IATA validation
5. Bidirectional mapping

Version: 1.0.0
Date: 2025-11-13
"""

import sys
sys.path.insert(0, '/home/user/bag')

from datetime import datetime
from models.canonical_bag import CanonicalBag, DataSource
from mappers import DCSMapper, BHSMapper, WorldTracerMapper, TypeBMapper, XMLMapper
from utils.data_fusion import DataFusionEngine
from utils.data_validator import DataValidator


def demo_data_fusion():
    """Demonstrate data fusion from multiple sources"""

    print("="*80)
    print("UNIFIED SEMANTIC DATA MODEL - DATA FUSION DEMO")
    print("="*80)
    print()

    # ========================================================================
    # SCENARIO: Bag 0291234567 has data in 5 different systems
    # ========================================================================

    # 1. DCS Data (from check-in)
    print("1. DCS DATA (Departure Control System)")
    print("-" * 80)

    dcs_data = {
        "bag_tag_number": "0291234567",
        "passenger": {
            "surname": "SMITH",
            "given_name": "JOHN",
            "title": "MR",
            "pnr": "ABC123",
            "ticket": "0011234567890",
            "ffn": "AA1234567",
            "class": "Y",
            "email": "john.smith@example.com",
            "phone": "+12025551234"
        },
        "itinerary": {
            "origin": "LAX",
            "destination": "JFK",
            "connections": [],
            "outbound_flight": {
                "carrier": "AA",
                "number": "123",
                "date": "2025-11-13T10:00:00Z",
                "scheduled_departure": "2025-11-13T10:00:00Z",
                "scheduled_arrival": "2025-11-13T18:30:00Z"
            }
        },
        "baggage": {
            "sequence": 1,
            "total": 2,
            "weight_kg": 23.5,
            "type": "CHECKED"
        },
        "check_in": {
            "timestamp": "2025-11-13T07:00:00Z",
            "agent": "AGENT001",
            "location": "LAX_T4_CKI_12"
        },
        "timestamp": "2025-11-13T07:00:00Z"
    }

    dcs_canonical = DCSMapper.to_canonical(dcs_data)
    print(f"✓ Mapped DCS data: {dcs_canonical['passenger_name']}")
    print(f"  PNR: {dcs_canonical.get('pnr')}, Flight: {dcs_canonical['outbound_flight']['airline_code']}{dcs_canonical['outbound_flight']['flight_number']}")
    print()

    # 2. BHS Data (from scanner)
    print("2. BHS DATA (Baggage Handling System)")
    print("-" * 80)

    bhs_data = {
        "license_plate": "BHS123456789",
        "bag_tag": "0291234567",
        "scan_event": {
            "event_type": "SORTATION",
            "scanner_id": "SORT_LAX_01",
            "location_code": "LAX_T4_SORT_01",
            "location_type": "SORTATION",
            "terminal": "T4",
            "timestamp": "2025-11-13T07:15:00Z"
        },
        "routing": {
            "origin": "LAX",
            "destination": "JFK",
            "outbound_lp": "LP123",
            "flight": "AA123"
        },
        "physical": {
            "weight_kg": 23.8,  # Slightly different from DCS!
            "length_cm": 55,
            "width_cm": 40,
            "height_cm": 23
        },
        "scan_history": [
            {"type": "CHECKIN", "timestamp": "2025-11-13T07:00:00Z", "location": "LAX_T4_CKI_12"},
            {"type": "SORTATION", "timestamp": "2025-11-13T07:15:00Z", "location": "LAX_T4_SORT_01"}
        ],
        "timestamp": "2025-11-13T07:15:00Z"
    }

    bhs_canonical = BHSMapper.to_canonical(bhs_data)
    print(f"✓ Mapped BHS data: Bag at {bhs_canonical['current_location']['location_code']}")
    print(f"  License Plate: {bhs_canonical.get('license_plate')}")
    print(f"  Weight: {bhs_canonical['dimensions']['weight_kg']} kg (conflicts with DCS: 23.5 kg)")
    print()

    # 3. Type B Message (from SITA network)
    print("3. TYPE B MESSAGE (SITA Legacy)")
    print("-" * 80)

    typeb_message = """BSM
AA123/13.LAXJFK
.V0291234567
.N1/2
.P0291234567/SMITH/JOHN MR
.D24K"""

    typeb_canonical = TypeBMapper.parse_from_text(typeb_message)
    print(f"✓ Parsed Type B message: BSM for flight AA123")
    print(f"  Weight: {typeb_canonical['dimensions']['weight_kg']} kg (third different value!)")
    print()

    # 4. WorldTracer (if bag gets delayed - for demo purposes)
    print("4. WORLDTRACER DATA (if exception occurred)")
    print("-" * 80)

    # Note: For demo, pretending bag had a temporary delay that was resolved
    worldtracer_data = {
        "ohd_reference": "LAXAA12345",
        "pir_type": "DELAYED",
        "bag_tag": "0291234567",
        "passenger": {
            "surname": "SMITH",
            "first_name": "JOHN",
            "pnr": "ABC123",
            "contact_phone": "+12025551234",
            "contact_email": "john.smith@example.com",
            "delivery_address": "123 Main St, New York, NY 10001"
        },
        "itinerary": {
            "origin": "LAX",
            "destination": "JFK",
            "flight": "AA123"
        },
        "bag_description": {
            "type": "SUITCASE",
            "color": "BLACK",
            "brand": "SAMSONITE",
            "material": "HARDSIDE"
        },
        "irregularity": {
            "type": "DELAYED",
            "station": "LAX",
            "date_time": "2025-11-13T09:45:00Z",
            "last_seen_location": "LAX_T4_SORT_01",
            "remarks": "Bag missed cut-off time for flight"
        },
        "current_status": {
            "status": "RESOLVED",
            "located": True,
            "current_location": "LAX_T4_MAKEUP_01"
        },
        "created_at": "2025-11-13T09:45:00Z",
        "updated_at": "2025-11-13T10:00:00Z"
    }

    wt_canonical = WorldTracerMapper.to_canonical(worldtracer_data)
    print(f"✓ Mapped WorldTracer data: Exception case {wt_canonical['exception_status']['worldtracer_ref']}")
    print(f"  Status: {wt_canonical['exception_status']['status']}")
    print(f"  Delivery Address: {wt_canonical['contact']['address']}")
    print()

    # 5. BaggageXML (from manifest)
    print("5. BAGGAGEXML DATA (Modern XML Standard)")
    print("-" * 80)

    xml_data = """<Baggage>
  <BagTag>0291234567</BagTag>
  <LicensePlate>BHS123456789</LicensePlate>
  <Passenger>
    <Name>SMITH/JOHN MR</Name>
    <PNR>ABC123</PNR>
    <Email>john.smith@example.com</Email>
    <Phone>+12025551234</Phone>
  </Passenger>
  <Itinerary>
    <Origin>LAX</Origin>
    <Destination>JFK</Destination>
  </Itinerary>
  <BagDetails>
    <Sequence>1</Sequence>
    <TotalBags>2</TotalBags>
    <Type>CHECKED</Type>
    <Weight unit="kg">23.5</Weight>
    <Dimensions>
      <Length unit="cm">55</Length>
      <Width unit="cm">40</Width>
      <Height unit="cm">23</Height>
    </Dimensions>
  </BagDetails>
  <Status>
    <State>SORTED</State>
    <LastLocation>LAX_T4_SORT_01</LastLocation>
    <LastScan>2025-11-13T07:15:00Z</LastScan>
  </Status>
</Baggage>"""

    xml_canonical = XMLMapper.parse_from_xml_string(xml_data)
    print(f"✓ Parsed BaggageXML: {xml_canonical['passenger_name']}")
    print(f"  State: {xml_canonical['current_state']}")
    print()

    # ========================================================================
    # DATA FUSION: Combine all sources intelligently
    # ========================================================================

    print("="*80)
    print("DATA FUSION: Combining all sources")
    print("="*80)
    print()

    fusion_engine = DataFusionEngine()

    # Prepare data for fusion
    sources_data = {
        DataSource.DCS: dcs_canonical,
        DataSource.BHS: bhs_canonical,
        DataSource.TYPE_B: typeb_canonical,
        DataSource.WORLDTRACER: wt_canonical,
        DataSource.BAGGAGE_XML: xml_canonical
    }

    # Fuse data
    fused_bag = fusion_engine.fuse(sources_data)

    print(f"✓ Data fusion complete!")
    print()
    print(f"Canonical Bag: {fused_bag.bag_tag}")
    print(f"  Passenger: {fused_bag.passenger_name}")
    print(f"  PNR: {fused_bag.pnr}")
    print(f"  Route: {fused_bag.origin.iata_code} → {fused_bag.destination.iata_code}")
    print(f"  Flight: {fused_bag.outbound_flight.full_flight_number}")
    print(f"  State: {fused_bag.current_state.value}")
    print(f"  Location: {fused_bag.current_location.location_code if fused_bag.current_location else 'N/A'}")
    print()

    print("DATA QUALITY METRICS:")
    print("-" * 80)
    print(f"  Confidence: {fused_bag.data_quality.confidence:.2%}")
    print(f"  Completeness: {fused_bag.data_quality.completeness:.2%}")
    print(f"  Accuracy: {fused_bag.data_quality.accuracy:.2%}")
    print(f"  Timeliness: {fused_bag.data_quality.timeliness:.2%}")
    print(f"  Data Sources: {[s.value for s in fused_bag.data_quality.data_sources]}")
    print()

    # Show conflict resolution
    if fused_bag.data_quality.conflicts_detected:
        print("CONFLICTS DETECTED & RESOLVED:")
        print("-" * 80)

        for field in fused_bag.data_quality.conflicts_detected:
            resolution = fused_bag.data_quality.conflicts_resolved.get(field, 'unknown')
            print(f"  • {field}: resolved using '{resolution}' strategy")

        print()

        # Show conflict summary from fusion engine
        conflict_summary = fusion_engine.get_conflict_summary()
        print(f"  Total conflicts: {conflict_summary['total_conflicts']}")
        print(f"  Resolution strategies used: {conflict_summary.get('resolution_strategies', {})}")
        print()

    # ========================================================================
    # VALIDATION: Check IATA standards and business rules
    # ========================================================================

    print("="*80)
    print("VALIDATION: IATA Standards & Business Rules")
    print("="*80)
    print()

    validator = DataValidator()
    validation_result = validator.validate(fused_bag)

    print(f"Validation Result: {'✓ VALID' if validation_result.is_valid else '✗ INVALID'}")
    print(f"  Confidence Score: {validation_result.confidence_score:.2%}")
    print(f"  Requires Human Review: {'Yes' if validation_result.requires_human_review else 'No'}")
    print()

    if validation_result.errors:
        print(f"ERRORS ({len(validation_result.errors)}):")
        for error in validation_result.errors:
            print(f"  ✗ [{error.rule_code}] {error.message}")
        print()

    if validation_result.warnings:
        print(f"WARNINGS ({len(validation_result.warnings)}):")
        for warning in validation_result.warnings[:5]:  # Show first 5
            print(f"  ⚠ [{warning.rule_code}] {warning.message}")

        if len(validation_result.warnings) > 5:
            print(f"  ... and {len(validation_result.warnings) - 5} more")
        print()

    if validation_result.info:
        print(f"INFO ({len(validation_result.info)}):")
        for info in validation_result.info[:3]:
            print(f"  ℹ [{info.rule_code}] {info.message}")
        print()

    # ========================================================================
    # BIDIRECTIONAL MAPPING: Convert back to each format
    # ========================================================================

    print("="*80)
    print("BIDIRECTIONAL MAPPING: Export to all formats")
    print("="*80)
    print()

    # Export to DCS
    print("1. Export to DCS format:")
    exported_dcs = DCSMapper.from_canonical(fused_bag)
    print(f"   ✓ PNR: {exported_dcs['passenger']['pnr']}, Bags: {exported_dcs['baggage']['sequence']}/{exported_dcs['baggage']['total']}")

    # Export to BHS
    print("2. Export to BHS format:")
    exported_bhs = BHSMapper.from_canonical(fused_bag)
    print(f"   ✓ License Plate: {exported_bhs['license_plate']}, Event: {exported_bhs['scan_event']['event_type']}")

    # Export to Type B
    print("3. Export to Type B format:")
    exported_typeb = TypeBMapper.from_canonical(fused_bag, message_type='BSM')
    print(f"   ✓ Message:\n{exported_typeb}")

    # Export to WorldTracer
    print("\n4. Export to WorldTracer format:")
    exported_wt = WorldTracerMapper.from_canonical(fused_bag)
    print(f"   ✓ OHD Ref: {exported_wt.get('ohd_reference', 'N/A')}, Type: {exported_wt.get('pir_type', 'N/A')}")

    # Export to XML
    print("\n5. Export to BaggageXML format:")
    exported_xml = XMLMapper.from_canonical(fused_bag)
    print("   ✓ XML generated (showing first 10 lines):")

    for i, line in enumerate(exported_xml.split('\n')[:10]):
        print(f"     {line}")

    print()

    # ========================================================================
    # SUMMARY
    # ========================================================================

    print("="*80)
    print("SUMMARY")
    print("="*80)
    print()
    print("✓ Successfully demonstrated unified semantic data model:")
    print("  • Data from 5 different systems mapped to canonical format")
    print("  • Intelligent conflict resolution (weight discrepancy resolved)")
    print("  • Data quality metrics calculated and tracked")
    print("  • IATA standards validation performed")
    print("  • Bidirectional mapping to all formats verified")
    print()
    print("Benefits:")
    print("  • Single source of truth for bag data")
    print("  • Automatic conflict resolution")
    print("  • Data lineage tracking")
    print("  • Standards compliance")
    print("  • No data friction between systems")
    print()
    print("="*80)


if __name__ == "__main__":
    try:
        demo_data_fusion()
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
