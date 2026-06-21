from __future__ import annotations

from collections.abc import Callable
import time
from typing import TypeVar

T = TypeVar("T")


def retry_call(
    func: Callable[[], T],
    *,
    attempts: int = 3,
    delay_seconds: float = 1.0,
    backoff: float = 2.0,
) -> T:
    if attempts < 1:
        raise ValueError("attempts must be at least 1")
    current_delay = delay_seconds
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            return func()
        except Exception as exc:
            last_error = exc
            if attempt == attempts - 1:
                break
            if current_delay > 0:
                time.sleep(current_delay)
            current_delay *= backoff
    raise last_error or RuntimeError("retry failed")
