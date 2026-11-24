"""三平台采集器：GitHub / GitLab / Gitee。

统一输出仓库记录：
  key        平台:owner/repo（小写，用于跨天对齐）
  platform   github | gitlab | gitee
  full_name  owner/repo（原样，用于展示）
  stars      当前总星数
  forks      当前 fork 数
  language / description / url / created / source / rank
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone

from http_client import Http

log = logging.getLogger("forge_pulse.collect")

GITHUB_API = "https://api.github.com"
GITLAB_API = "https://gitlab.com/api/v4"
GITEE_API = "https://gitee.com/api/v5"

TRENDING_RE = re.compile(r'<h2[^>]*>\s*<a[^>]*href="/([^"]+)"', re.S)


def parse_watchlist(path: str) -> dict[str, list[str]]:
    """读取固定追踪清单，按平台分组。无前缀默认 github。"""
    out: dict[str, list[str]] = {"github": [], "gitlab": [], "gitee": []}
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if ":" in line:
                    plat, name = line.split(":", 1)
                    plat, name = plat.strip().lower(), name.strip()
                else:
                    plat, name = "github", line
                if plat in out and name:
                    out[plat].append(name)
    except FileNotFoundError:
        log.warning("找不到 %s，跳过固定追踪清单", path)
    return out


def make_record(platform: str, full_name: str, stars, forks=None,
                language=None, description=None, url=None, created=None,
                source="api", rank=None) -> dict:
    full_name = (full_name or "").strip("/")
    if not full_name:
        return {}
    base = {"github": "https://github.com/", "gitlab": "https://gitlab.com/",
            "gitee": "https://gitee.com/"}[platform]
    return {
        "key": f"{platform}:{full_name.lower()}",
        "platform": platform,
        "full_name": full_name,
        "stars": int(stars or 0),
        "forks": int(forks or 0) if forks is not None else None,
        "language": language,
        "description": (description or "").strip()[:300] or None,
        "url": url or base + full_name,
        "created": (created or "")[:10] or None,
        "source": source,
        "rank": rank,
    }


# ────────────────────────── GitHub ──────────────────────────

def github_trending(http: Http, window: str, limit: int) -> list[dict]:
    """解析 GitHub Trending 页，只拿仓库名和当日排名，不消耗 REST 配额。"""
    url = "https://github.com/trending"
    if window != "daily":
        url += f"?since={window}"
    r = http.get(url)
    if not r or r.status != 200:
        log.warning("Trending 页抓取失败：%s", r.status if r else "no response")
        return []
    names = TRENDING_RE.findall(r.text())
    out = []
    for i, name in enumerate(dict.fromkeys(names)):
        if "/" not in name:
            continue
        out.append(make_record("github", name, 0, source="trending", rank=i + 1))
        if len(out) >= limit:
            break
    log.info("Trending 发现 %d 个仓库", len(out))
    return out


def github_search(http: Http, lookback: int, min_stars: int, limit: int, token: str) -> list[dict]:
    """可选渠道：搜索近期创建且已有星数的新项目（结果自带 stargazers_count）。"""
    if limit <= 0:
        return []
    since = (datetime.now(timezone.utc) - timedelta(days=lookback)).strftime("%Y-%m-%d")
    q = f"created:>{since} stars:>{min_stars}"
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = http.get(f"{GITHUB_API}/search/repositories",
                 params={"q": q, "sort": "stars", "order": "desc", "per_page": min(limit, 100)},
                 headers=headers)
    if not r or r.status != 200:
        log.warning("GitHub 搜索失败：%s", r.status if r else "no response")
        return []
    out = []
    for i, item in enumerate((r.json() or {}).get("items", [])):
        out.append(make_record(
            "github", item.get("full_name"), item.get("stargazers_count"),
            forks=item.get("forks_count"), language=item.get("language"),
            description=item.get("description"), url=item.get("html_url"),
            created=item.get("created_at"), source="search", rank=i + 1,
        ))
    return out


def github_repo(http: Http, name: str, token: str) -> dict | None:
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    raw = http.get_json(f"{GITHUB_API}/repos/{name}", headers=headers, allow_404=True)
    if not isinstance(raw, dict) or not raw.get("full_name"):
        return None
    return make_record(
        "github", raw["full_name"], raw.get("stargazers_count"),
        forks=raw.get("forks_count"), language=raw.get("language"),
        description=raw.get("description"), url=raw.get("html_url"),
        created=raw.get("created_at"), source="api",
    )


def collect_github(http: Http, cfg: dict, seeds: list[str]) -> list[dict]:
    token = cfg.get("token", "").strip()
    out: list[dict] = []
    seen: set[str] = set()

    def add(rec):
        if rec and rec.get("key") and rec["key"] not in seen:
            seen.add(rec["key"])
            out.append(rec)

    # ① Trending：只有它能提供当期热点
    if cfg.get("trending_enabled", True):
        for rec in github_trending(http, cfg.get("trending_window", "daily"),
                                   cfg.get("trending_limit", 30)):
            add(rec)

    # ② 固定追踪清单
    for name in seeds:
        add(github_repo(http, name, token))

    # ③ 搜索新项目（默认关闭，避免吃掉匿名配额）
    if cfg.get("search_enabled", False):
        for rec in github_search(http, cfg.get("search_lookback_days", 14),
                                 cfg.get("search_min_stars", 100),
                                 cfg.get("search_limit", 30), token):
            add(rec)

    # Trending 只带名字，这里统一补齐星数（搜索结果已自带，跳过）
    for rec in out:
        if rec["stars"] <= 0 and rec["source"] == "trending":
            full = rec["full_name"]
            detail = github_repo(http, full, token)
            if detail:
                detail["source"] = "trending"
                rec.update(detail)
    return [r for r in out if r["stars"] > 0 or r["source"] != "trending"]


# ────────────────────────── GitLab ──────────────────────────

def collect_gitlab(http: Http, cfg: dict, seeds: list[str]) -> list[dict]:
    """GitLab 探索接口按 star_count 排序，一次请求拿 Top N，无需 token。"""
    out: list[dict] = []
    seen: set[str] = set()
    top_n = int(cfg.get("top_n", 40))

    raw = http.get_json(f"{GITLAB_API}/projects", params={
        "order_by": "star_count", "sort": "desc",
        "per_page": min(top_n, 100), "page": 1,
    })
    if isinstance(raw, list):
        for i, item in enumerate(raw):
            rec = make_record(
                "gitlab", item.get("path_with_namespace"), item.get("star_count"),
                forks=item.get("forks_count"), description=item.get("description"),
                url=item.get("web_url"), created=item.get("created_at"),
                source="explore", rank=i + 1,
            )
            if rec["full_name"] and rec["key"] not in seen:
                seen.add(rec["key"])
                out.append(rec)
        log.info("GitLab 探索榜发现 %d 个仓库", len(out))
    else:
        log.warning("GitLab 探索接口返回异常：%s", type(raw).__name__)

    # 固定追踪清单里可能有探索榜外的项目
    for name in seeds:
        data = http.get_json(f"{GITLAB_API}/projects/{urllib_quote(name)}", allow_404=True)
        if not isinstance(data, dict) or not data.get("path_with_namespace"):
            continue
        rec = make_record(
            "gitlab", data["path_with_namespace"], data.get("star_count"),
            forks=data.get("forks_count"), description=data.get("description"),
            url=data.get("web_url"), created=data.get("created_at"), source="seed",
        )
        if rec["key"] not in seen:
            seen.add(rec["key"])
            out.append(rec)
    return out


def urllib_quote(name: str) -> str:
    from urllib.parse import quote
    return quote(name, safe="")


# ────────────────────────── Gitee ──────────────────────────

def collect_gitee(http: Http, cfg: dict, seeds: list[str]) -> list[dict]:
    """Gitee 没有公开的探索 API，用实测可用的种子清单逐个取仓库详情。"""
    out = []
    for name in seeds:
        raw = http.get_json(f"{GITEE_API}/repos/{name}", allow_404=True)
        if not isinstance(raw, dict) or not raw.get("full_name"):
            log.warning("Gitee 仓库读取失败：%s", name)
            continue
        rec = make_record(
            "gitee", raw["full_name"], raw.get("stargazers_count"),
            forks=raw.get("forks_count"), language=raw.get("language"),
            description=raw.get("description"), url=raw.get("html_url"),
            created=raw.get("created_at"), source="seed",
        )
        out.append(rec)
    log.info("Gitee 采集 %d 个仓库", len(out))
    return out


# ────────────────────────── 汇总 ──────────────────────────

def collect_all(http: Http, cfg: dict, watchlist_path: str) -> tuple[list[dict], dict]:
    seeds = parse_watchlist(watchlist_path)
    repos: list[dict] = []
    stats: dict[str, int] = {}

    if cfg.get("github", {}).get("enabled", True):
        g = collect_github(http, cfg["github"], seeds["github"])
        repos += g
        stats["github"] = len(g)
    if cfg.get("gitlab", {}).get("enabled", True):
        gl = collect_gitlab(http, cfg["gitlab"], seeds["gitlab"])
        repos += gl
        stats["gitlab"] = len(gl)
    if cfg.get("gitee", {}).get("enabled", True):
        gt = collect_gitee(http, cfg["gitee"], seeds["gitee"])
        repos += gt
        stats["gitee"] = len(gt)
    return repos, stats
