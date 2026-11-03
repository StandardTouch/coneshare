from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from coneshare_mcp.feature_gate import is_mcp_enabled


class McpFeatureGateMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if not is_mcp_enabled():
            return Response(status_code=404)
        return await call_next(request)
