# files/storage/s3_compatible.py
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from .base import StorageBackend


class S3CompatibleStorageBackend(StorageBackend):
    """
    Implementación única para MinIO Y para AWS S3 real, porque ambos hablan
    la misma API. Para AWS real, simplemente no se pasa internal/public
    endpoint_url (o se dejan en None) y boto3 apunta a AWS por defecto.
    """

    def __init__(
        self, *, bucket_name, access_key, secret_key,
        internal_endpoint_url=None, public_endpoint_url=None, region_name="us-east-1",
    ):
        self.bucket_name = bucket_name
        config = Config(signature_version="s3v4", s3={"addressing_style": "path"})

        self._internal_client = boto3.client(
            "s3", endpoint_url=internal_endpoint_url,
            aws_access_key_id=access_key, aws_secret_access_key=secret_key,
            region_name=region_name, config=config,
        )
        self._public_client = boto3.client(
            "s3", endpoint_url=public_endpoint_url or internal_endpoint_url,
            aws_access_key_id=access_key, aws_secret_access_key=secret_key,
            region_name=region_name, config=config,
        )

    def generate_upload_url(self, *, storage_key, content_type, expires_in=300):
        return self._public_client.generate_presigned_url(
            "put_object",
            Params={"Bucket": self.bucket_name, "Key": storage_key, "ContentType": content_type},
            ExpiresIn=expires_in,
        )

    def generate_download_url(self, *, storage_key, original_name, expires_in=300):
        return self._public_client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self.bucket_name, "Key": storage_key,
                "ResponseContentDisposition": f'attachment; filename="{original_name}"',
            },
            ExpiresIn=expires_in,
        )

    def head_object(self, *, storage_key):
        try:
            return self._internal_client.head_object(Bucket=self.bucket_name, Key=storage_key)
        except ClientError as e:
            if e.response["Error"]["Code"] in ("404", "NoSuchKey"):
                return None
            raise

    def delete_object(self, *, storage_key):
        self._internal_client.delete_object(Bucket=self.bucket_name, Key=storage_key)