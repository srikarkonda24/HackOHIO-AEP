"""Load local .env files for FastAPI (never commit real secrets)."""
from __future__ import annotations

from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

_PKG_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _PKG_DIR.parent


def load_gridaware_env() -> None:
    if load_dotenv is None:
        return
    load_dotenv(_REPO_ROOT / ".env", override=False)
    load_dotenv(_PKG_DIR / ".env", override=False)
