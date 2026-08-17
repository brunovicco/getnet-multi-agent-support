"""Structured logging implementation of the application event port."""

from collections.abc import Mapping

import structlog


class StructlogEventSink:
    """Emit application metadata as stable structlog events."""

    def __init__(self) -> None:
        """Create the service logger."""
        self._logger = structlog.get_logger("getnet_support")

    def emit(self, event: str, fields: Mapping[str, object]) -> None:
        """Write one metadata-only info event."""
        self._logger.info(event, **fields)
