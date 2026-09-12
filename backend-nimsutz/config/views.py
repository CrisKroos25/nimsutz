import boto3
import os
from botocore.client import Config
from django.http import JsonResponse

def generar_url_prueba(request):
    s3 = boto3.client(
        "s3",
        endpoint_url=os.environ.get("MINIO_ENDPOINT"),
        aws_access_key_id=os.environ.get("MINIO_ACCESS_KEY"),
        aws_secret_access_key=os.environ.get("MINIO_SECRET_KEY"),
        config=Config(signature_version="s3v4"),
    )

    url = s3.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": os.environ.get("MINIO_BUCKET_NAME"),
            "Key": "prueba.txt",
        },
        ExpiresIn=300,  # la URL expira en 5 minutos
    )

    return JsonResponse({"url_firmada": url})