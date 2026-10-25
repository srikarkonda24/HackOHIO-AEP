"""Customer network context API."""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, HTTPException

from network_context_service import build_network_context

router = APIRouter(tags=["customers"])

_db_path: str | None = None


def configure(db_path: str) -> APIRouter:
    global _db_path
    _db_path = db_path
    return router


def _connect() -> sqlite3.Connection:
    if not _db_path:
        raise HTTPException(status_code=503, detail="Network context API not configured")
    con = sqlite3.connect(_db_path)
    con.row_factory = sqlite3.Row
    return con


@router.get("/customers/{premise_id}/network-context")
def get_customer_network_context(premise_id: str):
    """
    Evidence-typed premise context: service location, upstream membership, GIS attributes.
    Does not infer serial connectivity or reconcile conflicting circuit IDs.
    """
    with _connect() as con:
        try:
            return build_network_context(con, premise_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Premise not found") from exc
