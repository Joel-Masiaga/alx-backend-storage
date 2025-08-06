#!/usr/bin/env python3

# Web caching utility using Redis.


from typing import Optional
import redis
import requests


def get_page(url: str) -> Optional[str]:
    r = redis.Redis()
    count_key = f"count:{url}"
    cache_key = f"cached:{url}"

    # increment access counter
    r.incr(count_key)

    # try to return cached response
    cached = r.get(cache_key)
    if cached is not None:
        try:
            return cached.decode("utf-8")
        except Exception:
            return str(cached)

    # fetch and cache
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        content = resp.text
        # store in redis with 10s expiry
        r.setex(cache_key, 10, content)
        return content
    except Exception:
        return None
