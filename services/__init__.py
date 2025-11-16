"""
Services Package
================

Business logic services for the baggage tracking platform.
"""

from services.dual_write_service import (
    DualWriteService,
    DualWriteException,
    get_dual_write_service,
    close_dual_write_service
)

__all__ = [
    'DualWriteService',
    'DualWriteException',
    'get_dual_write_service',
    'close_dual_write_service'
]
