import time
import uuid

from google.cloud import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import Message


class LoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        log_name = 'middleware'
        logging_client = logging.Client()
        self.logger = logging_client.logger(log_name)

    @staticmethod
    async def set_body(request):
        receive_ = await request.receive()

        async def receive() -> Message:
            return receive_

        request._receive = receive

    async def dispatch(self, request, call_next):
        req_uuid = str(uuid.uuid4())
        await self.set_body(request)
        body = await request.body()
        request_details = {
            "uuid": req_uuid,
            "type": "api-request",
            "method": str(request.method).upper(),
            "url": str(request.url),
            "headers": str(request.headers),
            "payload": body[:1200] if body else None,
        }
        self.logger.log_text(
            f"Request: {request_details}",
            severity='INFO'
        )
        start_time = time.time()
        response = await call_next(request)
        process_time = (time.time() - start_time) * 1000
        formatted_process_time = "{0:.2f}".format(process_time)
        response_details = {
            "uuid": req_uuid,
            "type": "api-response",
            "url": f"[{str(request.method).upper()}] {str(request.url)}",
            "headers": str(response.headers),
            "code": response.status_code,
            "elapsed_time": f"{formatted_process_time}ms",
        }
        self.logger.log_text(
            f"Response: {response_details}",
            severity='INFO'
        )
        return response
