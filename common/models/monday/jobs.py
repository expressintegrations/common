from firedantic import AsyncModel


class Job(AsyncModel):
    __collection__ = "jobs"

    function: str
    completion_time: float | None = None
