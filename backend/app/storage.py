"""MinIO client — object storage for imagery (Phase 11), per TRD §4
("object storage for imagery and survey photos"). Nothing in Phases 1-10
needed this; change detection is the first real user of it.
"""
import io

from minio import Minio

from .config import settings

BUCKET = "ps191-imagery"

_client: Minio | None = None


def get_minio_client() -> Minio:
    global _client
    if _client is None:
        _client = Minio(settings.minio_endpoint, access_key=settings.minio_access_key, secret_key=settings.minio_secret_key, secure=False)
    return _client


def ensure_bucket() -> None:
    client = get_minio_client()
    if not client.bucket_exists(BUCKET):
        client.make_bucket(BUCKET)


def upload_bytes(key: str, data: bytes, content_type: str) -> None:
    ensure_bucket()
    get_minio_client().put_object(BUCKET, key, io.BytesIO(data), length=len(data), content_type=content_type)


def download_bytes(key: str) -> bytes:
    response = get_minio_client().get_object(BUCKET, key)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def object_exists(key: str) -> bool:
    try:
        get_minio_client().stat_object(BUCKET, key)
        return True
    except Exception:
        return False
