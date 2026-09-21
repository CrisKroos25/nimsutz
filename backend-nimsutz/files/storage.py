# files/storage.py
import boto3
from botocore.client import Config
from django.conf import settings

BUCKET_NAME = settings.MINIO_BUCKET_NAME

_s3_interno = boto3.client(
    "s3",
    endpoint_url=settings.MINIO_ENDPOINT,
    aws_access_key_id=settings.MINIO_ACCESS_KEY,
    aws_secret_access_key=settings.MINIO_SECRET_KEY,
    config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
)

_s3_publico = boto3.client(
    "s3",
    endpoint_url=settings.MINIO_PUBLIC_ENDPOINT,
    aws_access_key_id=settings.MINIO_ACCESS_KEY,
    aws_secret_access_key=settings.MINIO_SECRET_KEY,
    config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
)


def generate_upload_url(*, storage_key, content_type, expires_in=300):
    return _s3_publico.generate_presigned_url(
        "put_object",
        Params={"Bucket": BUCKET_NAME, "Key": storage_key, "ContentType": content_type},
        ExpiresIn=expires_in,
    )


def generate_download_url(*, storage_key, original_name, expires_in=300):
    return _s3_publico.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": BUCKET_NAME,
            "Key": storage_key,
            "ResponseContentDisposition": f'attachment; filename="{original_name}"',
        },
        ExpiresIn=expires_in,
    )


def head_object(*, storage_key):
    """Devuelve metadata real del objeto, o None si no existe todavía."""
    from botocore.exceptions import ClientError

    try:
        return _s3_interno.head_object(Bucket=BUCKET_NAME, Key=storage_key)
    except ClientError as e:
        if e.response["Error"]["Code"] in ("404", "NoSuchKey"):
            return None
        raise


def delete_object(*, storage_key):
    _s3_interno.delete_object(Bucket=BUCKET_NAME, Key=storage_key)