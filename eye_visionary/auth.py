from __future__ import annotations

from dataclasses import dataclass

from fastapi import Header, HTTPException, status

from .config import get_settings


@dataclass(frozen=True)
class Principal:
    key_id: str
    scopes: frozenset[str]

    def can(self, scope: str) -> bool:
        return scope in self.scopes or "*" in self.scopes


def require_scope(scope: str):
    async def dependency(x_api_key: str | None = Header(default=None)) -> Principal:
        settings = get_settings()
        configured = settings.api_key_scopes()
        if not configured and settings.allow_anonymous:
            return Principal("anonymous", frozenset({"*"}))
        if not x_api_key or x_api_key not in configured:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"code": "unauthorized", "message": "A valid X-API-Key is required"})
        principal = Principal(x_api_key[:8], frozenset(configured[x_api_key]))
        if not principal.can(scope):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"code": "forbidden", "message": f"Scope {scope} is required"})
        return principal

    return dependency
