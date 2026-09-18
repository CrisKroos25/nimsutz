import boto3
from botocore.client import Config
import os

BUCKET_NAME = os.environ["MINIO_BUCKET_NAME"]

# Cliente interno: para operaciones que hace el backend mismo (crear bucket, verificar, etc.)
s3_interno = boto3.client(
    "s3",
    endpoint_url=os.environ.get("MINIO_ENDPOINT"),  # http://minio:9000
    aws_access_key_id=os.environ["MINIO_ACCESS_KEY"],
    aws_secret_access_key=os.environ["MINIO_SECRET_KEY"],
    config=Config(signature_version="s3v4"),
)

# Cliente para generar URLs firmadas que usará el navegador del usuario
s3_publico = boto3.client(
    "s3",
    endpoint_url=os.environ.get("MINIO_PUBLIC_ENDPOINT"),  # http://localhost:9000
    aws_access_key_id=os.environ["MINIO_ACCESS_KEY"],
    aws_secret_access_key=os.environ["MINIO_SECRET_KEY"],
    config=Config(signature_version="s3v4"),
)

s3_interno.create_bucket(Bucket=BUCKET_NAME)
print("Bucket creado correctamente")