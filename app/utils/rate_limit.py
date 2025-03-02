import time
from functools import wraps
from fastapi import HTTPException, status, Request
from collections import defaultdict, deque
from typing import Any
from app.config import settings


def rate_limited(max_calls: int, time_frame: int):
    """
    decorator from limit coll reqiest in ine IP-address.

    :param max_calls: maz call request.
    :param time_frame: time interval in minutes.
    """
    ip_calls: defaultdict[Any, deque] = defaultdict(deque)

    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            if not settings.RATE_LIMIT_ENABLED:
                return await func(request, *args, **kwargs)
            if "x-forwarded-for" in request.headers:
                ip = request.headers["x-forwarded-for"].split(",")[0].strip()
            elif request.client:
                ip = request.client.host
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Could not determine client IP address.",
                )

            now = time.time()
            time_frame_in_seconds = time_frame * 60

            ip_calls[ip] = deque(
                call for call in ip_calls[ip] 
                if call > now - time_frame_in_seconds
            )

            if len(ip_calls[ip]) >= max_calls:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded for this IP.",
                )

            ip_calls[ip].append(now)

            return await func(request, *args, **kwargs)

        return wrapper

    return decorator
