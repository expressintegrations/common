from google.cloud import storage

from common.services.base import BaseService


class StorageService(BaseService):
    def __init__(
        self,
        storage_client: storage.Client,
    ) -> None:
        self.storage_client = storage_client
        super().__init__(log_name="storage.service")

    def upload_file_from_memory(
        self, bucket_name: str, destination_file_name: str, contents
    ) -> None:
        bucket = self.storage_client.bucket(bucket_name=bucket_name)
        blob = bucket.blob(destination_file_name)
        blob.upload_from_string(contents)

    def download_file(
        self, bucket_name: str, source_file_name: str, destination_file_name: str
    ):
        """Downloads a blob from the bucket.
        The ID of your GCS bucket
        bucket_name = "your-bucket-name"

        The ID of your GCS object
        source_file_name = "storage-object-name"

        The path to which the file should be downloaded
        destination_file_name = "local/path/to/file"
        """

        bucket = self.storage_client.bucket(bucket_name=bucket_name)
        blob = bucket.blob(source_file_name)
        blob.download_to_filename(destination_file_name)

    def download_file_to_memory(self, bucket_name: str, source_file_name: str):
        """Downloads a blob from the bucket.
        The ID of your GCS bucket
        bucket_name = "your-bucket-name"

        The ID of your GCS object
        source_file_name = "storage-object-name"
        """

        bucket = self.storage_client.bucket(bucket_name=bucket_name)
        blob = bucket.blob(source_file_name)
        return blob.download_to_string()
