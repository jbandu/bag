"""
Base Parser

Abstract base class for all input parsers.
Provides common functionality and interface.
"""
from abc import ABC, abstractmethod
from typing import Union, Dict, Any
from loguru import logger
import hashlib

from app.parsers.models import BagEvent, ParseResult, ParsingMetadata


class BaseParser(ABC):
    """
    Base parser class

    All parsers inherit from this and implement parse() method.
    """

    def __init__(self, parser_name: str, parser_version: str = "1.0.0"):
        """
        Initialize parser

        Args:
            parser_name: Name of the parser (e.g., "TypeBParser")
            parser_version: Version string
        """
        self.parser_name = parser_name
        self.parser_version = parser_version

    @abstractmethod
    def parse(self, input_data: Union[str, Dict[str, Any]]) -> ParseResult:
        """
        Parse input data into canonical BagEvent

        Args:
            input_data: Raw input (string or dict)

        Returns:
            ParseResult with event and metadata
        """
        pass

    def create_success_result(
        self,
        event: BagEvent,
        confidence_score: float = 1.0,
        warnings: list = None,
        raw_input: str = None
    ) -> ParseResult:
        """
        Create successful parse result

        Args:
            event: Parsed BagEvent
            confidence_score: Confidence in parsing (0.0 to 1.0)
            warnings: Optional list of warnings
            raw_input: Original input for debugging

        Returns:
            ParseResult indicating success
        """
        return ParseResult(
            success=True,
            event=event,
            errors=[],
            warnings=warnings or [],
            confidence_score=confidence_score,
            parser_name=self.parser_name,
            raw_input=raw_input
        )

    def create_error_result(
        self,
        errors: list,
        raw_input: str = None,
        partial_event: BagEvent = None
    ) -> ParseResult:
        """
        Create failed parse result

        Args:
            errors: List of error messages
            raw_input: Original input for debugging
            partial_event: Partially parsed event (if any)

        Returns:
            ParseResult indicating failure
        """
        return ParseResult(
            success=False,
            event=partial_event,
            errors=errors,
            warnings=[],
            confidence_score=0.0,
            parser_name=self.parser_name,
            raw_input=raw_input
        )

    def compute_input_hash(self, input_data: str) -> str:
        """
        Compute hash of input for deduplication

        Args:
            input_data: Input string

        Returns:
            SHA256 hash
        """
        return hashlib.sha256(input_data.encode()).hexdigest()

    def create_metadata(
        self,
        confidence_score: float,
        errors: list = None,
        raw_input: str = None
    ) -> ParsingMetadata:
        """
        Create parsing metadata

        Args:
            confidence_score: Parsing confidence (0.0 to 1.0)
            errors: Optional parsing errors
            raw_input: Optional raw input for hashing

        Returns:
            ParsingMetadata instance
        """
        return ParsingMetadata(
            parser_name=self.parser_name,
            parser_version=self.parser_version,
            confidence_score=confidence_score,
            parsing_errors=errors or [],
            raw_input_hash=self.compute_input_hash(raw_input) if raw_input else None
        )

    def validate_required_fields(
        self,
        data: Dict[str, Any],
        required_fields: list
    ) -> list:
        """
        Validate that required fields are present

        Args:
            data: Data dictionary
            required_fields: List of required field names

        Returns:
            List of missing field errors
        """
        errors = []
        for field in required_fields:
            if field not in data or not data[field]:
                errors.append(f"Missing required field: {field}")
        return errors

    def safe_get(self, data: Dict[str, Any], key: str, default=None):
        """
        Safely get value from dictionary

        Args:
            data: Dictionary
            key: Key to retrieve
            default: Default value if key missing

        Returns:
            Value or default
        """
        return data.get(key, default)

    def log_parse_attempt(self, input_type: str, input_preview: str):
        """
        Log parsing attempt

        Args:
            input_type: Type of input (e.g., "Type B", "Scan Event")
            input_preview: Preview of input (first 100 chars)
        """
        logger.debug(f"{self.parser_name}: Parsing {input_type} - {input_preview[:100]}...")

    def log_parse_success(self, event_id: str, bag_tag: str):
        """
        Log successful parse

        Args:
            event_id: Generated event ID
            bag_tag: Bag tag number
        """
        logger.info(f"{self.parser_name}: ✅ Successfully parsed event {event_id} for bag {bag_tag}")

    def log_parse_failure(self, errors: list):
        """
        Log parsing failure

        Args:
            errors: List of error messages
        """
        logger.error(f"{self.parser_name}: ❌ Parsing failed - {', '.join(errors)}")
