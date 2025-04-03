"""Service for interacting with Google Cloud Tasks."""

import json
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

from google.api_core.exceptions import NotFound
from google.cloud import tasks_v2
from google.cloud.tasks_v2 import Queue, RateLimits, RetryConfig, Task
from google.protobuf import timestamp_pb2

from common.cloud_tasks.models.tasks import OidcTokenConfig
from common.logging.client import Logger
from common.logging.context import LoggingContext


def is_valid_url(url_string: str) -> bool:
    try:
        result = urlparse(url_string)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False


class CloudTasksService:
    """
    Service for interacting with Google Cloud Tasks.

    Args:
        cloud_tasks_client (tasks_v2.CloudTasksClient): The Cloud Tasks client.
        project (str): The Google Cloud project ID.
        location (str): The location of the Cloud Tasks queue.
        base_url (str): The default base URL for the service. Can be overridden when enqueuing a task.
        service_account_email (str): The default email of the service account. Can be overridden when enqueuing a task.

    Methods:
        enqueue(
            queue,
            handler_uri,
            payload=None,
            in_seconds=None,
            base_url=None,
            service_account=None
        ):
            Enqueues a task in the specified queue.

        get_queue(name):
            Retrieves the specified queue.

        create_queue(name, max_concurrent_dispatches=1000):
            Creates a queue with name and maximum concurrent dispatches.

        delete_queue(name):
            Deletes the specified queue.
    """

    cloud_tasks_client: tasks_v2.CloudTasksClient
    project: str
    location: str
    base_url: str
    service_account_email: str
    logger: Logger

    def __init__(
        self,
        cloud_tasks_client: tasks_v2.CloudTasksClient,
        project: str,
        location: str,
        base_url: str,
        service_account_email: str,
        logger: Logger | None = None,
    ) -> None:
        self.cloud_tasks_client = cloud_tasks_client
        self.project = project
        self.location = location
        self.base_url = base_url.rstrip("/")
        self.service_account_email = service_account_email
        self.logger = logger or Logger(
            log_name="cloud-tasks-service", log_level="DEBUG"
        )

    def _build_url(self, handler_uri: str) -> tuple[str, bool]:
        """Build the full URL and determine if it's external."""
        handler_uri = handler_uri.lstrip("/")
        is_external = handler_uri.startswith(("http://", "https://"))

        if is_external:
            if not is_valid_url(handler_uri):
                raise ValueError(f"Invalid handler URI: {handler_uri}")
            return handler_uri, True

        return f"{self.base_url}/{handler_uri}", False

    def _build_oidc_config(
        self,
        url: str,
        oidc_token_config: OidcTokenConfig | None,
        is_external: bool,
    ) -> OidcTokenConfig:
        """Build OIDC token configuration."""
        if oidc_token_config:
            return oidc_token_config

        if is_external:
            raise ValueError("OIDC token config is required for external URLs")

        return OidcTokenConfig(
            service_account_email=self.service_account_email,
            audience=url,
        )

    def enqueue(
        self,
        queue: str,
        handler_uri: str,
        payload: dict | list | str | None = None,
        in_seconds: int | None = None,
        oidc_token_config: OidcTokenConfig | None = None,
        headers: dict[str, str] | None = None,
    ) -> Task:
        """Enqueues a task in the specified queue with correlation ID propagation."""
        parent = self.cloud_tasks_client.queue_path(self.project, self.location, queue)

        url, is_external = self._build_url(handler_uri)
        oidc_config = self._build_oidc_config(url, oidc_token_config, is_external)

        # Start with provided headers or empty dict
        task_headers = headers or {}

        # Automatically propagate correlation ID from context if available
        correlation_id = LoggingContext.get_correlation_id()
        if correlation_id and "X-Correlation-ID" not in task_headers:
            task_headers["X-Correlation-ID"] = correlation_id

        self.logger.log_debug(f"Enqueueing task on {url}")

        task = {
            "http_request": {
                "http_method": tasks_v2.HttpMethod.POST,
                "url": url,
                "oidc_token": oidc_config.model_dump(),
            }
        }

        if payload is not None:
            task["http_request"]["body"] = (
                json.dumps(payload).encode()
                if isinstance(payload, (dict, list))
                else payload.encode()
            )

        # Add headers if we have any
        if task_headers:
            task["http_request"]["headers"] = task_headers

        if in_seconds is not None:
            # Create schedule time
            schedule_time = datetime.now(UTC) + timedelta(seconds=in_seconds)
            timestamp = timestamp_pb2.Timestamp()
            timestamp.FromDatetime(schedule_time)
            task["schedule_time"] = {
                "seconds": timestamp.seconds,
                "nanos": timestamp.nanos,
            }

        return self.cloud_tasks_client.create_task(
            request={"parent": parent, "task": task}
        )

    def get_queue(self, name: str) -> None | Queue:
        """Retrieves the specified queue."""
        queue_path = self.cloud_tasks_client.queue_path(
            self.project, self.location, name
        )
        try:
            return self.cloud_tasks_client.get_queue(name=queue_path)
        except NotFound:
            return None

    def create_queue(self, name: str, max_concurrent_dispatches: int = 1000) -> Queue:
        """Create a new queue with specified name and max concurrent dispatches."""
        return self.cloud_tasks_client.create_queue(
            parent=f"projects/{self.project}/locations/{self.location}",
            queue=Queue(
                name=f"projects/{self.project}/locations/{self.location}/queues/{name}",
                rate_limits=RateLimits(
                    max_concurrent_dispatches=max_concurrent_dispatches
                ),
                retry_config=RetryConfig(max_attempts=-1),
            ),
        )

    def delete_queue(self, name: str) -> None:
        """Deletes the specified queue."""
        queue_path = self.cloud_tasks_client.queue_path(
            self.project, self.location, name
        )
        try:
            self.logger.log_info(f"Deleting queue: {queue_path}")
            return self.cloud_tasks_client.delete_queue(name=queue_path)
        except NotFound:
            return None
