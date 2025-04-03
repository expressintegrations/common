import json
from datetime import datetime, timedelta, timezone
from typing import Union

from google.api_core.exceptions import NotFound
from google.cloud import tasks_v2
from google.cloud.tasks_v2 import Queue, RateLimits, RetryConfig, Task
from google.protobuf import timestamp_pb2

from common.services.base import BaseService


class CloudTasksService(BaseService):
    def __init__(
        self,
        cloud_tasks_client: tasks_v2.CloudTasksClient,
        project: str,
        location: str,
        base_url: str,
        service_account_email: str,
    ) -> None:
        self.cloud_tasks_client = cloud_tasks_client
        self.project = project
        self.location = location
        self.base_url = base_url
        self.service_account_email = service_account_email
        super().__init__(log_name="cloud_tasks.service")

    def enqueue(
        self,
        queue: str,
        handler_uri: str,
        payload: dict | list | None = None,
        payload_json: str | None = None,
        in_seconds: int = None,
        base_url: str = None,
        service_account: str = None,
    ) -> Task:
        parent = self.cloud_tasks_client.queue_path(self.project, self.location, queue)

        # Construct the request body.
        base_url = base_url.strip("/") if base_url else self.base_url.strip("/")
        handler_uri = handler_uri.strip("/")
        url = (
            handler_uri
            if handler_uri.startswith("https://")
            else f"{base_url}/{handler_uri}"
        )
        self.logger.log_debug(f"Enqueueing task on {url}")
        task = {
            "http_request": {  # Specify the type of request.
                "http_method": tasks_v2.HttpMethod.POST,
                "url": url,  # The full url path that the task will be sent to.
                "oidc_token": {
                    "service_account_email": service_account
                    if service_account
                    else self.service_account_email,
                    "audience": base_url,
                },
            }
        }

        if payload is not None and payload_json is not None:
            raise ValueError("You can only specify one of `payload` or `payload_json`.")

        if payload is not None:
            # The API expects a payload of type bytes.
            converted_payload = json.dumps(payload).encode()

            # Add the payload to the request.
            task["http_request"]["body"] = converted_payload

        elif payload_json is not None:
            # The API expects a payload of type bytes.
            converted_payload = payload_json.encode()

            # Add the payload to the request.
            task["http_request"]["body"] = converted_payload

        if in_seconds is not None:
            # Convert "seconds from now" into a rfc3339 datetime string.
            d = datetime.now(tz=timezone.utc) + timedelta(seconds=in_seconds)
            timestamp = timestamp_pb2.Timestamp()
            timestamp.FromDatetime(d)

            # Add the timestamp to the tasks.
            task["schedule_time"] = timestamp
        request = {"parent": parent, "task": task}
        return self.cloud_tasks_client.create_task(request=request)

    def get_queue(self, name: str) -> Union[None, Queue]:
        queue_name = f"projects/{self.project}/locations/{self.location}/queues/{name}"
        try:
            return self.cloud_tasks_client.get_queue(name=queue_name)
        except NotFound:
            return

    def create_queue(self, name: str, max_concurrent_dispatches: int = 1000) -> Queue:
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
        queue_name = f"projects/{self.project}/locations/{self.location}/queues/{name}"
        try:
            return self.cloud_tasks_client.delete_queue(name=queue_name)
        except NotFound:
            return
