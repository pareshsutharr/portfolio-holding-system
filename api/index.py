"""Vercel entrypoint for the existing portfolio analysis API.

Vercel treats ``api/index.py`` as the catch-all Python function for ``/api/*``.
Keeping the application object in ``api.main`` also preserves the existing
Uvicorn and Render development workflows.
"""

from api.main import app

__all__ = ["app"]
