#!/usr/bin/env python3

# Redis basic exercise module.



from typing import Callable, Optional, Union, Any
from functools import wraps
import uuid
import redis


DataT = Union[str, bytes, int, float]


def count_calls(method: Callable) -> Callable:
    key = method.__qualname__

    @wraps(method)
    def wrapper(self, *args, **kwargs):
        # increment counter in redis
        self._redis.incr(key)
        return method(self, *args, **kwargs)

    return wrapper


def call_history(method: Callable) -> Callable:
    inputs_key = method.__qualname__ + ":inputs"
    outputs_key = method.__qualname__ + ":outputs"

    @wraps(method)
    def wrapper(self, *args, **kwargs):
        # store inputs as a string (ignore kwargs for simplicity)
        self._redis.rpush(inputs_key, str(args))
        result = method(self, *args, **kwargs)
        # store output (stringified) so it can be retrieved later
        self._redis.rpush(outputs_key, str(result))
        return result

    return wrapper


class Cache:

    def __init__(self) -> None:
        self._redis = redis.Redis()
        self._redis.flushdb()

    @count_calls
    @call_history
    def store(self, data: DataT) -> str:
  
        key = str(uuid.uuid4())
        # Redis will accept str, bytes, int, float
        self._redis.set(key, data)
        return key

    def get(self, key: str, fn: Optional[Callable] = None) -> Any:
        value = self._redis.get(key)
        if value is None:
            return None
        if fn:
            return fn(value)
        return value

    def get_str(self, key: str) -> Optional[str]:

        value = self.get(key)
        if value is None:
            return None
        # value is bytes, decode to str
        return value.decode("utf-8")

    def get_int(self, key: str) -> Optional[int]:
        value = self.get(key)
        if value is None:
            return None
        # int accepts bytes or string or number
        return int(value)


def replay(fn: Callable) -> None:

    if not hasattr(fn, "__qualname__"):
        return

    qualname = fn.__qualname__
    # The bound method's self should provide access to the redis instance
    try:
        redis_instance = fn.__self__._redis
    except Exception:
        # fallback to a fresh Redis connection if we can't get the instance
        redis_instance = redis.Redis()

    count = redis_instance.get(qualname)
    try:
        calls = int(count) if count is not None else 0
    except Exception:
        calls = 0

    print(f"{qualname} was called {calls} times:")

    inputs_key = qualname + ":inputs"
    outputs_key = qualname + ":outputs"
    inputs = redis_instance.lrange(inputs_key, 0, -1)
    outputs = redis_instance.lrange(outputs_key, 0, -1)

    for inp, out in zip(inputs, outputs):
        # inputs are stored as str(args) so they are bytes here; decode
        try:
            inp_decoded = inp.decode("utf-8")
        except Exception:
            inp_decoded = str(inp)
        try:
            out_decoded = out.decode("utf-8")
        except Exception:
            out_decoded = str(out)
        print(f"{qualname}(*{inp_decoded}) -> {out_decoded}")
