from fastapi import Header, HTTPException

from src.config import settings


async def require_api_key(
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    """
    If API_KEY is set in env, require it in Authorization: Bearer <key>
    or in X-API-Key header. If API_KEY is empty, allow all.
    """
    if settings.api_key is None:
        return

    expected = settings.api_key.get_secret_value()
    if x_api_key and x_api_key == expected:
        return

    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer" and token == expected:
            return

    raise HTTPException(status_code=401, detail="Unauthorized")
