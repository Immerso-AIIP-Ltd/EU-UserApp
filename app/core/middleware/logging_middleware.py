import time
from typing import Awaitable, Callable

from fastapi import Request
from loguru import logger
from starlette.responses import Response


async def logging_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Logging middleware."""
    # Request interceptor start
    req_start = time.time()

    # Request interceptor end (before endpoint)
    req_end = time.time()

    # Actual endpoint execution
    response = await call_next(request)

    # Response interceptor end
    res_end = time.time()

    # Interceptor timings
    req_time = (req_end - req_start) * 1000  # ms
    res_time = (res_end - req_end) * 1000
    total_time = (res_end - req_start) * 1000

    # Existing access log
    client_ip = request.client.host if request.client else "unknown"
    process_time = total_time  # reuse total_time

    logger.bind(
        client_ip=client_ip,
        method=request.method,
        path=request.url.path,
        query_params=str(request.query_params),
        headers=dict(request.headers),
        status_code=response.status_code,
        process_time=f"{process_time:.2f}ms",
    ).info("access")

    # New interceptor log
    logger.bind(
        event="interceptor",
        method=request.method,
        path=request.url.path,
        req_ms=f"{req_time:.2f}",
        res_ms=f"{res_time:.2f}",
        total_ms=f"{total_time:.2f}",
    ).info(
        f"{request.method} {request.url.path} | "
        f"req={req_time:.2f}ms res={res_time:.2f}ms total={total_time:.2f}ms",
    )

    return response
