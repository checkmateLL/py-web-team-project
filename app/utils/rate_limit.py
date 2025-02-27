import time
from functools import wraps
from fastapi import HTTPException, status, Request
from collections import defaultdict
from typing import DefaultDict

def rate_limited(max_calls: int, time_frame: int):
    """
    decorator from limit coll reqiest in ine IP-address.

    :param max_calls: Максимальное количество запросов.
    :param time_frame: Временной интервал в минутах.
    """
    ip_calls : DefaultDict[str, list[float]] = defaultdict(list)

    def decorator(func):

        flag = True
        if not flag:
            return func
        
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):

            if request.client is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail='Could not determine client IP address.'
                )
            ip = request.client.host
            now = time.time()


            time_frame_in_seconds = time_frame * 60
            ip_calls[ip] = [call for call in ip_calls[ip] if call > now - time_frame_in_seconds]


            if len(ip_calls[ip]) >= max_calls:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded for this IP."
                )

            ip_calls[ip].append(now)


            return await func(request, *args, **kwargs)

        return wrapper

    return decorator