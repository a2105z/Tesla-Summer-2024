from __future__ import annotations

from fastapi import Header, HTTPException, status


# Validate bearer token before continuing.
def validate_bearer_token(authorization: str | None, allowed_tokens: set[str]) -> str:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bearer token format")
    if token not in allowed_tokens:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API token")
    return token


# Auth dependency factory.
def auth_dependency_factory(allowed_tokens: set[str]):


    # Handle internal logic for auth.
    async def _auth(authorization: str | None = Header(default=None)) -> str:
        return validate_bearer_token(authorization=authorization, allowed_tokens=allowed_tokens)

    return _auth

