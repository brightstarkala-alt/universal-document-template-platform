"""
Storage abstraction layer over Supabase Storage.

No other module should call `get_supabase_admin().storage` directly — this
is the only seam that knows the bucket name and the Supabase Storage API
shape, so swapping storage providers later only touches this file.
Company/file naming strategy lives one layer up, in
`app/services/file_service.py`; this module only knows how to move bytes
in and out of a bucket given a path.
"""

from app.core.config import settings
from app.core.supabase import get_supabase_admin

BUCKET_NAME = settings.STORAGE_BUCKET_NAME


def upload_object(*, path: str, content: bytes, content_type: str) -> None:
    client = get_supabase_admin()
    client.storage.from_(BUCKET_NAME).upload(path, content, {"content-type": content_type})


def create_signed_url(*, path: str, expires_in: int) -> str:
    client = get_supabase_admin()
    response = client.storage.from_(BUCKET_NAME).create_signed_url(path, expires_in)
    return str(response["signedURL"])


def delete_object(*, path: str) -> None:
    client = get_supabase_admin()
    client.storage.from_(BUCKET_NAME).remove([path])
