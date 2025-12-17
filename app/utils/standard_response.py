from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.constants import ResponseParams
from app.settings import settings

API_VERSION = settings.api_version


def build_meta(
    request: Request,
    data: Union[List[Any], Dict[str, Any]],
    page: Optional[int] = None,
    limit: Optional[int] = None,
    pages: Optional[int] = None,
    total_records: Optional[int] = None,
) -> Dict[str, Any]:
    """Build a standardized meta object for API responses.

    Args:
        request: The FastAPI request object.
        data: Response data (list or dict).
        page: Current page number (optional).
        limit: Items per page (optional).
        pages: Total number of pages (optional).
        total_records: Explicit total record count (optional).
            If not provided, defaults to len(data) for lists or 1 for dicts.

    Returns:
        Dictionary containing standardized metadata.
    """
    if total_records is None:
        total_records = len(data) if isinstance(data, list) else 1

    meta: Dict[str, Any] = {
        ResponseParams.API_VERSION: API_VERSION,
        ResponseParams.TIMESTAMP: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        ResponseParams.REQUEST_ID: request.headers.get("x-request-id"),
        ResponseParams.TOTAL_RECORDS: total_records,
    }

    if page is not None and limit is not None:
        meta.update(
            {
                ResponseParams.PAGE: page,
                ResponseParams.PER_PAGE: limit,
                ResponseParams.TOTAL_PAGES: pages or 1,
            },
        )

    return meta


def standard_response(
    message: str,
    request: Request,
    data: Union[List[Any], Dict[str, Any]],
    page: Optional[int] = None,
    limit: Optional[int] = None,
    pages: Optional[int] = None,
    total_records: Optional[int] = None,
) -> JSONResponse:
    """Standardized JSON success response for all APIs.

    Args:
        message: Response message.
        request: The FastAPI request object.
        data: Response data payload.
        page: Current page number (optional).
        limit: Items per page (optional).
        pages: Total number of pages (optional).
        total_records: Explicit total record count (optional).

    Returns:
        JSONResponse with standardized structure.
    """
    response_body: Dict[str, Any] = {
        ResponseParams.SUCCESS: True,
        ResponseParams.MESSAGE: message,
        ResponseParams.DATA: data,
        ResponseParams.META: build_meta(
            request=request,
            data=data,
            page=page,
            limit=limit,
            pages=pages,
            total_records=total_records,
        ),
        ResponseParams.ERROR: {},
    }

    return JSONResponse(content=response_body, status_code=200)
