import os
from urllib.parse import urlparse
import boto3

AWS_KEY = os.getenv("AWS_KEY")
AWS_SECRET = os.getenv("AWS_SECRET")
AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-2")
AWS_BUCKET = os.getenv("AWS_BUCKET")
AWS_S3_FOLDER = os.getenv("AWS_S3_FOLDER", "curriculums")

s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_KEY,
    aws_secret_access_key=AWS_SECRET,
    region_name=AWS_DEFAULT_REGION,
)

def s3_key_for_cv(vacancy_id: int, applicant_id: int, filename: str) -> str:
    import re, time
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", filename or "cv.pdf")
    ts = int(time.time())
    return f"{AWS_S3_FOLDER}/vacancy_{vacancy_id}/applicant_{applicant_id}_{ts}_{safe}"

def public_url_from_key(key: str) -> str:
    return f"https://{AWS_BUCKET}.s3.{AWS_DEFAULT_REGION}.amazonaws.com/{key}"

def extract_key_from_cv_path(cv_path: str) -> str | None:
    """Acepta KEY puro o URL completa y devuelve la KEY."""
    if not cv_path:
        return None
    if cv_path.startswith("http://") or cv_path.startswith("https://"):
        p = urlparse(cv_path)
        return p.path.lstrip("/") or None
    return cv_path


def delete_cv_key(key: str) -> None:
    """Borra el objeto en S3; ignora si no existe."""
    if not key:
        return
    try:
        s3_client.delete_object(Bucket=AWS_BUCKET, Key=key)
    except Exception:
        import logging
        logging.exception("No se pudo eliminar objeto S3: %s", key)


def make_presigned_url(key: str, expires_seconds: int = 1200) -> str:
    """Genera una URL firmada temporal para descargar el CV."""
    return s3_client.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": AWS_BUCKET, "Key": key},
        ExpiresIn=expires_seconds
    )