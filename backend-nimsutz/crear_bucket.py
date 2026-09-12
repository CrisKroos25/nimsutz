import boto3
from botocore.client import Config
import os

# Cliente interno: para operaciones que hace el backend mismo (crear bucket, verificar, etc.)
s3_interno = boto3.client(
    "s3",
    endpoint_url=os.environ.get("MINIO_ENDPOINT"),  # http://minio:9000
    aws_access_key_id="nimsutz_admin",
    aws_secret_access_key="nimsutz_admin_pass",
    config=Config(signature_version="s3v4"),
)

# Cliente para generar URLs firmadas que usará el navegador del usuario
s3_publico = boto3.client(
    "s3",
    endpoint_url=os.environ.get("MINIO_PUBLIC_ENDPOINT"),  # http://localhost:9000
    aws_access_key_id="nimsutz_admin",
    aws_secret_access_key="nimsutz_admin_pass",
    config=Config(signature_version="s3v4"),
)

s3_publico.create_bucket(Bucket="nimsutz-storage")
print("Bucket creado correctamentea")