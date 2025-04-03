from common.logging.client import Logger


class BaseService:
    logger: Logger

    def __init__(
        self,
        log_name: str | None = None,
        logger: Logger | None = None,
        **kwargs,
    ) -> None:
        self.logger = logger or Logger(log_name=log_name, log_level="DEBUG")
