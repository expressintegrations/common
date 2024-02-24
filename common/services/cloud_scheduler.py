from google.cloud import scheduler_v1
from google.cloud.scheduler_v1 import Job, PauseJobRequest, ResumeJobRequest

from common.services.base import BaseService


class CloudSchedulerService(BaseService):

    def __init__(
        self,
        scheduler_client: scheduler_v1.CloudSchedulerClient,
    ) -> None:
        self.scheduler_client = scheduler_client
        super().__init__(log_name='cloud_scheduler.service')

    def pause(
        self,
        job_name: str
    ) -> Job:
        return self.scheduler_client.pause_job(
            request=PauseJobRequest(
                {'name': job_name},
            )
        )

    def resume(
        self,
        job_name: str
    ) -> Job:
        return self.scheduler_client.resume_job(
            request=ResumeJobRequest(
                {'name': job_name},
            )
        )
