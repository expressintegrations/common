"""Logging client for either local or Google Cloud logging with robust functionality."""

import json
import logging as python_logging
import sys
import traceback
from enum import Enum
from typing import Any, Protocol

from google.cloud import logging as cloud_logging
from google.cloud.logging_v2 import Client
from google.cloud.logging_v2.logger import Logger as CloudLogger


class Severity(str, Enum):
    """Severity levels for logging with corresponding Python logging levels."""

    DEFAULT = "DEFAULT"
    DEBUG = "DEBUG"
    INFO = "INFO"
    NOTICE = "NOTICE"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    ALERT = "ALERT"
    EMERGENCY = "EMERGENCY"

    @property
    def python_level(self) -> int:
        """Get the corresponding Python logging level."""
        return {
            self.DEFAULT: python_logging.INFO,
            self.DEBUG: python_logging.DEBUG,
            self.INFO: python_logging.INFO,
            self.NOTICE: python_logging.INFO,
            self.WARNING: python_logging.WARNING,
            self.ERROR: python_logging.ERROR,
            self.CRITICAL: python_logging.CRITICAL,
            self.ALERT: python_logging.CRITICAL,
            self.EMERGENCY: python_logging.CRITICAL,
        }[self]

    @classmethod
    def from_python_level(cls, level: int) -> "Severity":
        """Convert Python logging level to Severity."""
        return {
            python_logging.DEBUG: cls.DEBUG,
            python_logging.INFO: cls.INFO,
            python_logging.WARNING: cls.WARNING,
            python_logging.ERROR: cls.ERROR,
            python_logging.CRITICAL: cls.CRITICAL,
        }[level]


class CloudEntry(Protocol):
    """Protocol for cloud logging entries."""

    severity: str | None
    payload: dict[str, Any]


class Logger:
    """Unified client for local and cloud logging with advanced features."""

    def __init__(
        self,
        log_name: str,
        log_level: str = "INFO",
        use_cloud: bool = False,
        logging_client: Client | None = None,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Initialize logging client with advanced configuration.

        Args:
            log_name: Name of the logger
            log_level: Minimum log level to record
            use_cloud: Whether to use Google Cloud logging
            logging_client: Optional preconfigured logging client for GCP
            labels: Optional labels to add to all log entries
        """
        self._log_level = log_level
        self._logging_client = logging_client
        self._use_cloud = str(use_cloud).lower() == "true"
        # Initialize with the log name
        self._log_name = log_name
        self._labels = labels or {}
        self._initialize_logger()

    def _initialize_logger(self) -> None:
        """Initialize or reinitialize the logger with current settings."""
        if self._use_cloud:
            try:
                client: Client = self._logging_client or cloud_logging.Client()
                self._logger: CloudLogger | python_logging.Logger = client.logger(
                    name=self._log_name, labels=self._labels
                )
            except Exception as e:
                sys.stderr.write(f"Failed to initialize cloud logging: {e}\n")
                sys.stderr.write("Falling back to local logging\n")
                self._use_cloud = False
                self._setup_local_logging(self._log_level)
        else:
            self._setup_local_logging(self._log_level)

    def _setup_local_logging(self, log_level: str) -> None:
        """Configure local logging with formatting and handlers."""
        self._logger = python_logging.getLogger(self._log_name)
        self._logger.setLevel(getattr(python_logging, log_level))

        # Remove existing handlers to prevent duplicate logging
        self._logger.handlers.clear()

        formatter = python_logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )

        # Console handler
        console_handler = python_logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self._logger.addHandler(console_handler)

    @property
    def log_name(self) -> str:
        """Get the current log name."""
        return self._log_name

    @log_name.setter
    def log_name(self, value: str) -> None:
        """Set a new log name and reinitialize the logger.

        Args:
            value: New log name to use

        Raises:
            ValueError: If the log name is empty
        """
        if not value:
            raise ValueError("Log name cannot be empty")

        # Update the name and reinitialize
        self._log_name = value
        self._initialize_logger()

    def _prepare_payload(
        self,
        message: str | dict,
        labels: dict[str, str] | None,
    ) -> tuple[dict[str, Any], dict[str, str]]:
        """Prepare log payload with metadata and context."""
        if isinstance(message, dict):
            payload: dict[str, Any] = message.copy()
        else:
            payload = {"message": message}

        final_labels = self._labels | (labels or {})

        return payload, final_labels

    # Property to update logger labels
    @property
    def labels(self) -> dict[str, str]:
        """Get the current logger labels."""
        return self._labels

    @labels.setter
    def labels(self, value: dict[str, Any]) -> None:
        """Set new labels for the logger."""
        self._labels = {str(k): str(v) for k, v in value.items()}
        self._initialize_logger()

    def add_labels(self, labels: dict[str, Any]) -> None:
        """Add new labels to the logger."""
        self._labels.update({str(k): str(v) for k, v in labels.items()})
        self._initialize_logger()

    def log_struct(
        self,
        payload: dict,
        severity: Severity | None = None,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Log structured data with optional severity and labels."""
        prepared_payload, final_labels = self._prepare_payload(payload, labels)

        if isinstance(self._logger, CloudLogger):
            self._logger.log_struct(prepared_payload, severity=severity, labels=final_labels)
        else:
            level = (severity or Severity.DEFAULT).python_level
            self._logger.log(level, json.dumps(prepared_payload | final_labels))

    def log_text(
        self,
        message: str,
        severity: Severity | None = None,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Log a text message with metadata."""
        self.log_struct({"message": message}, severity=severity, labels=labels)

    def log_exception(
        self,
        exc: Exception,
        additional_message: str | None = None,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Log an exception with full traceback."""
        exc_type = type(exc).__name__
        exc_traceback = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))

        payload = {
            "exception_type": exc_type,
            "exception_message": str(exc),
            "traceback": exc_traceback,
        }

        if additional_message:
            payload["additional_message"] = additional_message

        self.log_struct(payload, severity=Severity.ERROR, labels=labels)

    # Convenience methods for different severity levels
    def log_debug(self, message: str, labels: dict[str, str] | None = None) -> None:
        self.log_text(message, severity=Severity.DEBUG, labels=labels)

    def log_info(self, message: str, labels: dict[str, str] | None = None) -> None:
        self.log_text(message, severity=Severity.INFO, labels=labels)

    def log_warning(self, message: str, labels: dict[str, str] | None = None) -> None:
        self.log_text(message, severity=Severity.WARNING, labels=labels)

    def log_error(self, message: str, labels: dict[str, str] | None = None) -> None:
        self.log_text(message, severity=Severity.ERROR, labels=labels)

    def log_alert(self, message: str, labels: dict[str, str] | None = None) -> None:
        self.log_text(message, severity=Severity.ALERT, labels=labels)

    def log_critical(self, message: str, labels: dict[str, str] | None = None) -> None:
        self.log_text(message, severity=Severity.CRITICAL, labels=labels)