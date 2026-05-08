from minio import Minio
from minio.error import S3Error
import uuid
import os
from app.config import settings

class S3Service:
    def __init__(self):
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )
        self.bucket = settings.MINIO_BUCKET
        self._ensure_bucket()

    def _ensure_bucket(self):
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
        except S3Error as e:
            print(f"Error creating bucket: {e}")

    async def upload_file(self, file_path: str, object_name: str) -> str:
        try:
            self.client.fput_object(self.bucket, object_name, file_path)
            return f"{self.bucket}/{object_name}"
        except S3Error as e:
            raise Exception(f"Gagal upload ke MinIO: {e}")

    async def download_file(self, object_name: str, file_path: str):
        try:
            self.client.fget_object(self.bucket, object_name, file_path)
        except S3Error as e:
            raise Exception(f"Gagal download dari MinIO: {e}")

    async def get_presigned_url(self, object_name: str, expiry: int = 900) -> str:
        try:
            url = self.client.presigned_get_object(self.bucket, object_name, expires=expiry)
            return url
        except S3Error as e:
            raise Exception(f"Gagal generate presigned URL: {e}")

    async def delete_object(self, object_name: str):
        try:
            self.client.remove_object(self.bucket, object_name)
        except S3Error as e:
            raise Exception(f"Gagal hapus object: {e}")

    def get_object_name_from_path(self, s3_path: str) -> str:
        if s3_path.startswith(f"{self.bucket}/"):
            return s3_path[len(self.bucket)+1:]
        return s3_path

s3_service = S3Service()
