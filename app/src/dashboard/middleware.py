from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.dashboard import store

EXCLUDED_PATHS = {"/", "/dashboard/stats"}


class RequestCounterMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        route = request.scope.get("route")
        route_template = route.path if route is not None else request.url.path
        if route_template in EXCLUDED_PATHS:
            return response

        store.increment(f"{request.method} {route_template}", response.status_code)
        return response
