from __future__ import annotations

from typing import Iterable

from fastapi import HTTPException, Request


def ensure_role(request: Request, allowed: Iterable[str]) -> None:
    role = request.headers.get("X-Role") or request.query_params.get("role") or ""
    if role not in allowed:
        raise HTTPException(status_code=403, detail="Forbidden for this role")
