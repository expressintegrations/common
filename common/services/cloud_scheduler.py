from google.cloud import scheduler_v1
from google.cloud.scheduler_v1 import Job
from google.cloud.scheduler_v1.services.cloud_scheduler.pagers import ListJobsPager

from common.services.base import BaseService


class CloudSchedulerService(BaseService):
    def __init__(
        self,
        scheduler_client: scheduler_v1.CloudSchedulerClient,
        project: str,
        location: str,
    ) -> None:
        self.scheduler_client = scheduler_client
        self.parent = f"projects/{project}/locations/{location}"
        super().__init__(log_name="cloud_scheduler.service")

    def create(
        self,
        job_name: str,
        target_uri: str,
        service_account_email: str,
        audience: str,
        schedule: str,
    ) -> Job:
        return self.scheduler_client.create_job(
            parent=self.parent,
            job=Job(
                {
                    "name": f"{self.parent}/jobs/{job_name}",
                    "http_target": {
                        "uri": target_uri,
                        "http_method": "POST",
                        "headers": {
                            "key": "User-Agent",
                            "value": "Google-Cloud-Scheduler",
                        },
                        "oidc_token": {
                            "service_account_email": service_account_email,
                            "audience": audience,
                        },
                    },
                    "schedule": schedule,
                    "time_zone": "Etc/UTC",
                }
            ),
        )

    def delete(self, job_name: str) -> None:
        self.scheduler_client.delete_job(name=f"{self.parent}/jobs/{job_name}")

    def list(self) -> ListJobsPager:
        return self.scheduler_client.list_jobs(parent=self.parent)

    def get(self, job_name: str) -> Job:
        return self.scheduler_client.get_job(name=f"{self.parent}/jobs/{job_name}")

    def pause(self, job_name: str) -> Job:
        return self.scheduler_client.pause_job(name=f"{self.parent}/jobs/{job_name}")

    def resume(self, job_name: str) -> Job:
        return self.scheduler_client.resume_job(name=f"{self.parent}/jobs/{job_name}")
