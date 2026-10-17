"""HTTP client shared by every source: identifies itself, retries, and waits between calls."""

from __future__ import annotations

import time

import httpx

USER_AGENT = "jobs-pulse/1.0 (+https://github.com/JoseMayo16/jobs-pulse)"
RETRY_STATUS = {429, 500, 502, 503, 504}


class PoliteClient:
    def __init__(self, delay: float = 1.0, retries: int = 3, timeout: float = 30.0):
        self.delay = delay
        self.retries = retries
        self._last = 0.0
        self._http = httpx.Client(
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            timeout=timeout,
            follow_redirects=True,
        )

    def get_json(self, url: str, params: dict | None = None):
        for attempt in range(self.retries + 1):
            wait = self.delay - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.monotonic()
            try:
                response = self._http.get(url, params=params)
                if response.status_code not in RETRY_STATUS:
                    response.raise_for_status()
                    return response.json()
            except httpx.TransportError:
                if attempt == self.retries:
                    raise
            if attempt == self.retries:
                response.raise_for_status()
            time.sleep(2**attempt * 2)
        raise RuntimeError("unreachable")

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> PoliteClient:
        return self

    def __exit__(self, *exc) -> None:
        self.close()
