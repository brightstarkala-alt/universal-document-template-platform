"""
Supabase admin client.

Used to verify user JWTs issued by Supabase Auth. Verification is delegated
to the Supabase Auth server (`auth.get_user`) rather than decoding the JWT
locally, so the backend never needs to manage a separate JWT signing
secret — it only needs the service role key already required by
`SUPABASE_SERVICE_ROLE_KEY`.
"""

from functools import lru_cache

from supabase import Client, create_client

from app.core.config import settings


@lru_cache
def get_supabase_admin() -> Client:
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set to use Supabase Auth."
        )
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
