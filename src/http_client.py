"""限流感知的 HTTP 客户端（仅 Python 标准库）。

三平台的公开接口都实测过：
  GitHub  /repos/{owner}/{repo}   匿名 60 次/小时，带 token 5000 次/小时
  GitLab  /api/v4/projects         公开可读，探索接口一次返回 Top N
  Gitee   /api/v5/repos/{o}/{r}    匿名 60 次/小时（X-RateLimit-Remaining）

统一在这里处理请求间隔、429/403 退避、以及重试，避免每个采集器各写一套。
"""

from __future__ import annotations

import http.client
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request

log = logging.getLogger("forge_pulse.http")

TRANSIENT = (
    urllib.error.URLError,
    http.client.HTTPException,
    TimeoutError,
    ConnectionError,
    OSError,
)

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"


class BudgetExceeded(RuntimeError):
    """等待预算耗尽，主动中止，避免定时任务卡死。"""


class Response:
    def __init__(self, status: int, headers: dict, body: bytes, url: str):
        self.status = status
        self.headers = headers
        self.body = body
        self.url = url

    def json(self):
        if not self.body:
            return None
        try:
            return json.loads(self.body.decode("utf-8", errors="replace"))
        except json.JSONDecodeError:
            return None

    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")


class Http:
    def __init__(self, timeout=20, retries=2, gap=0.15, max_wait=600):
        self.timeout = timeout
        self.retries = retries
        self.gap = gap
        self.max_wait = max_wait
        self.requests_made = 0
        self.seconds_waited = 0.0
        self._last = 0.0

    def _sleep(self, seconds: float, reason: str):
        if seconds <= 0:
            return
        if self.seconds_waited + seconds > self.max_wait:
            raise BudgetExceeded(f"等待 {seconds:.0f}s 超过上限（{reason}），已发 {self.requests_made} 次请求")
        log.warning("等待 %.0fs：%s", seconds, reason)
        time.sleep(seconds)
        self.seconds_waited += seconds

    def _gap(self):
        left = self.gap - (time.time() - self._last)
        if left > 0:
            time.sleep(left)

    def get(self, url: str, params: dict | None = None, headers: dict | None = None,
            allow_404: bool = False) -> Response | None:
        if params:
            url = url + "?" + urllib.parse.urlencode(params)
        hdrs = {"User-Agent": UA, "Accept": "application/json, text/html;q=0.9, */*;q=0.8"}
        if headers:
            hdrs.update(headers)

        attempt = 0
        while True:
            attempt += 1
            self._gap()
            req = urllib.request.Request(url, headers=hdrs, method="GET")
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    body = r.read()
                    out = Response(r.status, {k.lower(): v for k, v in r.headers.items()}, body, url)
                self._last = time.time()
                self.requests_made += 1
                return out
            except urllib.error.HTTPError as e:
                self._last = time.time()
                self.requests_made += 1
                body = e.read()
                headers = {k.lower(): v for k, v in (e.headers or {}).items()}
                if e.code == 404 and allow_404:
                    return None
                # 配额真正耗尽时，按 reset 时间精确等待；重置太久就跳过，
                # 不让它拖垮整轮采集（GitHub / Gitee 都会回这个头）。
                if e.code in (403, 429) and headers.get("x-ratelimit-remaining") == "0":
                    try:
                        wait = int(headers["x-ratelimit-reset"]) - time.time() + 2
                    except (KeyError, TypeError, ValueError):
                        wait = 60
                    if 0 < wait <= self.max_wait - self.seconds_waited:
                        self._sleep(wait, "配额耗尽，等待重置")
                        continue
                    log.warning("配额耗尽且重置时间过长，跳过 %s", url[:80])
                    return Response(e.code, headers, body, url)
                if e.code in (403, 429) and attempt <= self.retries:
                    retry_after = headers.get("retry-after")
                    try:
                        wait = int(retry_after) if retry_after else min(60, 2 ** attempt)
                    except (TypeError, ValueError):
                        wait = min(60, 2 ** attempt)
                    self._sleep(wait, f"HTTP {e.code} @ {url[:80]}")
                    continue
                if e.code in (500, 502, 503, 504) and attempt <= self.retries:
                    self._sleep(min(30, 2 ** attempt), f"HTTP {e.code}，重试")
                    continue
                return Response(e.code, {}, body, url)
            except TRANSIENT as e:
                self._last = time.time()
                if attempt <= self.retries:
                    self._sleep(min(30, 2 ** attempt), f"网络错误 {type(e).__name__}")
                    continue
                log.error("请求最终失败 %s -> %s", url[:100], e)
                return None

    def get_json(self, url, **kwargs) -> dict | list | None:
        r = self.get(url, **kwargs)
        return r.json() if r and r.status == 200 else None

    def summary(self) -> str:
        return f"共 {self.requests_made} 次请求，等待 {self.seconds_waited:.0f}s"
