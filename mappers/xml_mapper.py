"""
BaggageXML Mapper
=================

Bidirectional mapper between BaggageXML format
and Canonical Bag model.

BaggageXML is a modern XML standard for baggage manifest exchange.

Version: 1.0.0
Date: 2025-11-13
"""

from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger
import xml.etree.ElementTree as ET
from xml.dom import minidom

from models.canonical_bag import (
    CanonicalBag,
    AirportCode,
    FlightNumber,
    BagState,
    BagType,
    DataSource
)


class XMLMapper:
    """
    Maps between BaggageXML format and Canonical Bag model

    BaggageXML Format:
    ```xml
    <BaggageManifest>
      <Flight>
        <Carrier>AA</Carrier>
        <FlightNumber>123</FlightNumber>
        <Origin>LAX</Origin>
        <Destination>JFK</Destination>
        <DepartureDate>2025-11-13T10:00:00Z</DepartureDate>
      </Flight>
      <BaggageList>
        <Baggage>
          <BagTag>0291234567</BagTag>
          <LicensePlate>BHS123456789</LicensePlate>
          <Passenger>
            <Name>SMITH/JOHN MR</Name>
            <PNR>ABC123</PNR>
          </Passenger>
          <Itinerary>
            <Origin>LAX</Origin>
            <Destination>JFK</Destination>
            <Connections>
              <Stop>ORD</Stop>
            </Connections>
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
            <State>IN_SYSTEM</State>
            <LastLocation>LAX_T4_SORT_01</LastLocation>
            <LastScan>2025-11-13T10:05:00Z</LastScan>
          </Status>
        </Baggage>
      </BaggageList>
    </BaggageManifest>
    ```
    """

    @staticmethod
    def parse_xml(xml_string: str) -> Dict[str, Any]:
        """
        Parse BaggageXML into structured data

        Args:
            xml_string: XML string

        Returns:
            Parsed data dict
        """
        try:
            root = ET.fromstring(xml_string)

            # Check if root is BaggageManifest or single Baggage
            if root.tag == 'BaggageManifest':
                # Extract flight info
                flight_elem = root.find('Flight')
                flight = {}

                if flight_elem is not None:
                    flight['carrier'] = XMLMapper._get_text(flight_elem, 'Carrier')
                    flight['number'] = XMLMapper._get_text(flight_elem, 'FlightNumber')
                    flight['origin'] = XMLMapper._get_text(flight_elem, 'Origin')
                    flight['destination'] = XMLMapper._get_text(flight_elem, 'Destination')
                    flight['departure_date'] = XMLMapper._get_text(flight_elem, 'DepartureDate')

                # Extract baggage list
                baggage_list = root.find('BaggageList')

                if baggage_list is not None:
                    bags = []

                    for bag_elem in baggage_list.findall('Baggage'):
                        bag = XMLMapper._parse_bag_element(bag_elem)
                        # Add flight info to bag
                        bag['flight'] = flight
                        bags.append(bag)

                    return {'manifest': {'flight': flight, 'bags': bags}}
            elif root.tag == 'Baggage':
                # Single baggage element
                bag = XMLMapper._parse_bag_element(root)
                return bag
            else:
                raise ValueError(f"Unknown root element: {root.tag}")

        except ET.ParseError as e:
            logger.error(f"Failed to parse XML: {e}")
            raise

    @staticmethod
    def _parse_bag_element(elem: ET.Element) -> Dict[str, Any]:
        """Parse a Baggage XML element"""

        bag = {}

        # Basic fields
        bag['bag_tag'] = XMLMapper._get_text(elem, 'BagTag')
        bag['license_plate'] = XMLMapper._get_text(elem, 'LicensePlate')

        # Passenger
        passenger_elem = elem.find('Passenger')

        if passenger_elem is not None:
            bag['passenger'] = {
                'name': XMLMapper._get_text(passenger_elem, 'Name'),
                'pnr': XMLMapper._get_text(passenger_elem, 'PNR'),
                'ticket': XMLMapper._get_text(passenger_elem, 'Ticket'),
                'email': XMLMapper._get_text(passenger_elem, 'Email'),
                'phone': XMLMapper._get_text(passenger_elem, 'Phone')
            }

        # Itinerary
        itinerary_elem = elem.find('Itinerary')

        if itinerary_elem is not None:
            bag['itinerary'] = {
                'origin': XMLMapper._get_text(itinerary_elem, 'Origin'),
                'destination': XMLMapper._get_text(itinerary_elem, 'Destination')
            }

            # Connections
            connections_elem = itinerary_elem.find('Connections')

            if connections_elem is not None:
                stops = [XMLMapper._get_text(stop, '.') for stop in connections_elem.findall('Stop')]
                bag['itinerary']['connections'] = stops

        # Bag details
        details_elem = elem.find('BagDetails')

        if details_elem is not None:
            bag['details'] = {
                'sequence': XMLMapper._get_int(details_elem, 'Sequence'),
                'total_bags': XMLMapper._get_int(details_elem, 'TotalBags'),
                'type': XMLMapper._get_text(details_elem, 'Type')
            }

            # Weight
            weight_elem = details_elem.find('Weight')

            if weight_elem is not None:
                unit = weight_elem.get('unit', 'kg')
                weight_value = float(weight_elem.text or '0')

                # Convert to kg if needed
                if unit == 'lb' or unit == 'lbs':
                    weight_value = weight_value * 0.453592

                bag['details']['weight_kg'] = weight_value

            # Dimensions
            dim_elem = details_elem.find('Dimensions')

            if dim_elem is not None:
                bag['details']['dimensions'] = {
                    'length_cm': XMLMapper._get_int(dim_elem, 'Length'),
                    'width_cm': XMLMapper._get_int(dim_elem, 'Width'),
                    'height_cm': XMLMapper._get_int(dim_elem, 'Height')
                }

        # Status
        status_elem = elem.find('Status')

        if status_elem is not None:
            bag['status'] = {
                'state': XMLMapper._get_text(status_elem, 'State'),
                'last_location': XMLMapper._get_text(status_elem, 'LastLocation'),
                'last_scan': XMLMapper._get_text(status_elem, 'LastScan')
            }

        return bag

    @staticmethod
    def _get_text(elem: ET.Element, tag: str) -> Optional[str]:
        """Get text content from XML element"""
        child = elem.find(tag) if tag != '.' else elem
        return child.text if child is not None else None

    @staticmethod
    def _get_int(elem: ET.Element, tag: str) -> Optional[int]:
        """Get integer from XML element"""
        text = XMLMapper._get_text(elem, tag)
        return int(text) if text else None

    @staticmethod
    def to_canonical(xml_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map BaggageXML data to canonical format

        Args:
            xml_data: Parsed XML data

        Returns:
            Dict compatible with CanonicalBag
        """
        logger.debug(f"Mapping BaggageXML data to canonical format")

        canonical = {}

        try:
            # Handle both manifest and single bag formats
            if 'manifest' in xml_data:
                # This is a manifest with multiple bags
                # For now, just take the first bag
                bags = xml_data['manifest'].get('bags', [])

                if bags:
                    bag_data = bags[0]
                    flight_data = xml_data['manifest'].get('flight', {})
                else:
                    raise ValueError("No bags in manifest")
            else:
                # Single bag
                bag_data = xml_data
                flight_data = xml_data.get('flight', {})

            # Identity
            if 'bag_tag' in bag_data:
                canonical['bag_tag'] = str(bag_data['bag_tag']).zfill(10)

            if 'license_plate' in bag_data:
                canonical['license_plate'] = bag_data['license_plate']

            # Passenger
            passenger = bag_data.get('passenger', {})

            if passenger:
                if 'name' in passenger:
                    canonical['passenger_name'] = passenger['name']

                    # Try to split name
                    if '/' in passenger['name']:
                        parts = passenger['name'].split('/')
                        if len(parts) >= 2:
                            canonical['passenger_last_name'] = parts[0].strip()
                            canonical['passenger_first_name'] = parts[1].strip()

                if 'pnr' in passenger:
                    canonical['pnr'] = passenger['pnr']

                if 'ticket' in passenger:
                    canonical['ticket_number'] = passenger['ticket']

                # Contact
                if passenger.get('email') or passenger.get('phone'):
                    canonical['contact'] = {}

                    if passenger.get('email'):
                        canonical['contact']['email'] = passenger['email']

                    if passenger.get('phone'):
                        canonical['contact']['phone'] = passenger['phone']

            # Itinerary
            itinerary = bag_data.get('itinerary', {})

            if itinerary:
                if 'origin' in itinerary:
                    canonical['origin'] = {'iata_code': itinerary['origin'].upper()}

                if 'destination' in itinerary:
                    canonical['destination'] = {'iata_code': itinerary['destination'].upper()}

                if 'connections' in itinerary and itinerary['connections']:
                    canonical['intermediate_stops'] = [
                        {'iata_code': stop.upper()}
                        for stop in itinerary['connections']
                    ]

            # Flight (from flight_data or manifest)
            if flight_data:
                if 'carrier' in flight_data and 'number' in flight_data:
                    canonical['outbound_flight'] = {
                        'airline_code': flight_data['carrier'],
                        'flight_number': flight_data['number']
                    }

                    if 'departure_date' in flight_data:
                        canonical['outbound_flight']['departure_date'] = flight_data['departure_date']

                if 'departure_date' in flight_data:
                    canonical['expected_departure'] = flight_data['departure_date']

            # Bag details
            details = bag_data.get('details', {})

            if details:
                if 'sequence' in details:
                    canonical['bag_sequence'] = details['sequence']

                if 'total_bags' in details:
                    canonical['total_bags'] = details['total_bags']

                if 'type' in details:
                    # Map type string to BagType enum
                    type_map = {
                        'CHECKED': BagType.CHECKED,
                        'CABIN': BagType.CABIN,
                        'TRANSFER': BagType.TRANSFER,
                        'PRIORITY': BagType.PRIORITY
                    }

                    bag_type = type_map.get(details['type'].upper(), BagType.CHECKED)
                    canonical['bag_type'] = bag_type

                # Dimensions
                dimensions = {}

                if 'weight_kg' in details:
                    dimensions['weight_kg'] = details['weight_kg']

                if 'dimensions' in details:
                    dim = details['dimensions']

                    if 'length_cm' in dim:
                        dimensions['length_cm'] = dim['length_cm']

                    if 'width_cm' in dim:
                        dimensions['width_cm'] = dim['width_cm']

                    if 'height_cm' in dim:
                        dimensions['height_cm'] = dim['height_cm']

                if dimensions:
                    canonical['dimensions'] = dimensions

            # Status
            status = bag_data.get('status', {})

            if status:
                # Map state string to BagState enum
                if 'state' in status:
                    try:
                        canonical['current_state'] = BagState(status['state'])
                    except ValueError:
                        canonical['current_state'] = BagState.IN_SYSTEM

                if 'last_location' in status:
                    canonical['current_location'] = {
                        'location_code': status['last_location'],
                        'location_type': 'UNKNOWN'
                    }

                if 'last_scan' in status:
                    canonical['last_scan_at'] = status['last_scan']

            # Add timestamp
            canonical['timestamp'] = datetime.now().isoformat()

            logger.debug(f"Successfully mapped BaggageXML data for bag {canonical.get('bag_tag')}")

            return canonical

        except Exception as e:
            logger.error(f"Error mapping BaggageXML data to canonical: {e}")
            logger.debug(f"XML data: {xml_data}")
            raise

    @staticmethod
    def from_canonical(canonical_bag: CanonicalBag) -> str:
        """
        Map canonical bag to BaggageXML format

        Args:
            canonical_bag: CanonicalBag instance

        Returns:
            BaggageXML string
        """
        logger.debug(f"Mapping canonical bag {canonical_bag.bag_tag} to BaggageXML format")

        try:
            # Create root element
            baggage = ET.Element('Baggage')

            # Basic fields
            ET.SubElement(baggage, 'BagTag').text = canonical_bag.bag_tag

            if canonical_bag.license_plate:
                ET.SubElement(baggage, 'LicensePlate').text = canonical_bag.license_plate

            # Passenger
            passenger = ET.SubElement(baggage, 'Passenger')
            ET.SubElement(passenger, 'Name').text = canonical_bag.passenger_name

            if canonical_bag.pnr:
                ET.SubElement(passenger, 'PNR').text = canonical_bag.pnr

            if canonical_bag.ticket_number:
                ET.SubElement(passenger, 'Ticket').text = canonical_bag.ticket_number

            if canonical_bag.contact:
                if canonical_bag.contact.email:
                    ET.SubElement(passenger, 'Email').text = canonical_bag.contact.email

                if canonical_bag.contact.phone:
                    ET.SubElement(passenger, 'Phone').text = canonical_bag.contact.phone

            # Itinerary
            itinerary = ET.SubElement(baggage, 'Itinerary')
            ET.SubElement(itinerary, 'Origin').text = canonical_bag.origin.iata_code
            ET.SubElement(itinerary, 'Destination').text = canonical_bag.destination.iata_code

            if canonical_bag.intermediate_stops:
                connections = ET.SubElement(itinerary, 'Connections')

                for stop in canonical_bag.intermediate_stops:
                    ET.SubElement(connections, 'Stop').text = stop.iata_code

            # Bag details
            details = ET.SubElement(baggage, 'BagDetails')
            ET.SubElement(details, 'Sequence').text = str(canonical_bag.bag_sequence)
            ET.SubElement(details, 'TotalBags').text = str(canonical_bag.total_bags)
            ET.SubElement(details, 'Type').text = canonical_bag.bag_type.value

            if canonical_bag.dimensions:
                if canonical_bag.dimensions.weight_kg:
                    weight = ET.SubElement(details, 'Weight')
                    weight.set('unit', 'kg')
                    weight.text = str(canonical_bag.dimensions.weight_kg)

                if all([
                    canonical_bag.dimensions.length_cm,
                    canonical_bag.dimensions.width_cm,
                    canonical_bag.dimensions.height_cm
                ]):
                    dimensions = ET.SubElement(details, 'Dimensions')
                    ET.SubElement(dimensions, 'Length').text = str(canonical_bag.dimensions.length_cm)
                    length_elem = dimensions.find('Length')
                    length_elem.set('unit', 'cm')

                    ET.SubElement(dimensions, 'Width').text = str(canonical_bag.dimensions.width_cm)
                    width_elem = dimensions.find('Width')
                    width_elem.set('unit', 'cm')

                    ET.SubElement(dimensions, 'Height').text = str(canonical_bag.dimensions.height_cm)
                    height_elem = dimensions.find('Height')
                    height_elem.set('unit', 'cm')

            # Status
            status = ET.SubElement(baggage, 'Status')
            ET.SubElement(status, 'State').text = canonical_bag.current_state.value

            if canonical_bag.current_location:
                ET.SubElement(status, 'LastLocation').text = canonical_bag.current_location.location_code

            if canonical_bag.last_scan_at:
                ET.SubElement(status, 'LastScan').text = canonical_bag.last_scan_at.isoformat()

            # Convert to pretty-printed XML string
            xml_string = ET.tostring(baggage, encoding='unicode')

            # Pretty print
            dom = minidom.parseString(xml_string)
            pretty_xml = dom.toprettyxml(indent='  ')

            # Remove XML declaration for cleaner output
            lines = pretty_xml.split('\n')[1:]  # Skip first line (<?xml...?>)
            pretty_xml = '\n'.join(lines)

            logger.debug(f"Successfully mapped canonical bag to BaggageXML format")

            return pretty_xml.strip()

        except Exception as e:
            logger.error(f"Error mapping canonical bag to BaggageXML format: {e}")
            raise


    @staticmethod
    def parse_from_xml_string(xml_string: str) -> Dict[str, Any]:
        """
        Parse XML string and convert to canonical format

        Args:
            xml_string: BaggageXML string

        Returns:
            Canonical format dict
        """
        parsed = XMLMapper.parse_xml(xml_string)
        return XMLMapper.to_canonical(parsed)
