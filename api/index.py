"""Vercel entrypoint for the existing portfolio analysis API.

Vercel treats ``api/index.py`` as the catch-all Python function for ``/api/*``.
Keeping the application object in ``api.main`` also preserves the existing
Uvicorn and Render development workflows.
"""

from urllib.parse import parse_qs

from api.main import app as portfolio_app


class VercelPathAdapter:
    """Restore the public API path after Vercel rewrites to this function."""

    def __init__(self, application):
        self.application = application

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope.get("path") in {"/api", "/api/index"}:
            query = parse_qs(scope.get("query_string", b"").decode())
            forwarded = query.get("__route", [""])[0].strip("/")
            if forwarded:
                scope = {**scope, "path": f"/{forwarded}", "raw_path": f"/{forwarded}".encode()}
        await self.application(scope, receive, send)


app = VercelPathAdapter(portfolio_app)

__all__ = ["app"]
