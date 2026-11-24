"""从每日快照计算涨星榜。

核心只有一句话：增量 = 今天的星数 - N 天前的星数。
没有历史快照就没有增量，所以快照是唯一事实来源，永远保留。
"""

from __future__ import annotations

import json
import logging
import os
from datetime import date, timedelta

log = logging.getLogger("forge_pulse.analyze")


def load_snapshots(snap_dir: str) -> dict[str, dict[str, dict]]:
    """读所有快照，返回 {日期: {仓库 key: 记录}}。"""
    out: dict[str, dict[str, dict]] = {}
    if not os.path.isdir(snap_dir):
        return out
    for fn in sorted(os.listdir(snap_dir)):
        if not fn.endswith(".json"):
            continue
        day = fn[:-5]
        try:
            with open(os.path.join(snap_dir, fn), encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            log.warning("跳过损坏的快照 %s：%s", fn, e)
            continue
        recs = {}
        for r in data.get("repos", []):
            if r.get("key"):
                recs[r["key"]] = r
        if recs:
            out[day] = recs
    return out


def save_snapshot(snap_dir: str, day: str, repos: list[dict]) -> str | None:
    """合并写：同一天补跑时保留已有仓库，只覆盖采集到的 key。"""
    os.makedirs(snap_dir, exist_ok=True)
    path = os.path.join(snap_dir, day + ".json")
    merged: dict[str, dict] = {}
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                for r in json.load(f).get("repos", []):
                    if r.get("key"):
                        merged[r["key"]] = r
        except (OSError, json.JSONDecodeError):
            pass
    for r in repos:
        if r.get("key"):
            merged[r["key"]] = r
    if not merged:
        return None
    payload = {"date": day, "count": len(merged), "repos": list(merged.values())}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    return path


def build(snapshots: dict[str, dict[str, dict]], cfg: dict) -> dict:
    if not snapshots:
        return {"latest_date": None, "rows": [], "boards": {}, "stats": {}}

    days = sorted(snapshots)
    latest = days[-1]
    all_keys: set[str] = set()
    for recs in snapshots.values():
        all_keys.update(recs.keys())

    spark_days = int(cfg.get("sparkline_days", 14))
    history_days = int(cfg.get("history_days", 30))
    rows = []

    for key in all_keys:
        series = [(d, snapshots[d][key]["stars"]) for d in days if key in snapshots[d]]
        if not series:
            continue
        stars_now = series[-1][1]
        lookup = dict(series)
        first_day = date.fromisoformat(series[0][0])
        last_day = date.fromisoformat(series[-1][0])

        def delta_n(n: int):
            target = (last_day - timedelta(days=n)).isoformat()
            if target in lookup:
                return stars_now - lookup[target]
            return None

        d1, d7, d30 = delta_n(1), delta_n(7), delta_n(30)
        # 异常增长标记：单日涨超昨日 30% 且超过 100 星，可能是刷星或运营推广
        suspicious = bool(d1 and d1 > 100 and lookup.get((last_day - timedelta(days=1)).isoformat())
                          and d1 > 0.3 * lookup[(last_day - timedelta(days=1)).isoformat()])

        recent = series[-spark_days:]
        base = snapshots[series[-1][0]][key]
        row = dict(base)
        row.update({
            "stars": stars_now,
            "d1": d1, "d7": d7, "d30": d30,
            "spark": [v for _, v in recent],
            "suspicious": suspicious,
            "days_tracked": (last_day - first_day).days + 1,
        })
        rows.append(row)

    def ranked(field: str, platform: str | None = None, n: int = 50):
        pool = [r for r in rows if (platform is None or r["platform"] == platform)
                and r.get(field) is not None]
        pool.sort(key=lambda r: (-r[field], -r["stars"]))
        return pool[:n]

    boards = {}
    for label, field in (("daily", "d1"), ("weekly", "d7"), ("monthly", "d30"), ("total", "stars")):
        boards[label] = {
            "all": ranked(field, None, 50),
            "github": ranked(field, "github", 30),
            "gitlab": ranked(field, "gitlab", 30),
            "gitee": ranked(field, "gitee", 30),
        }

    stats = {
        "latest_date": latest,
        "snapshot_days": len(days),
        "tracked_repos": len(rows),
        "platforms": sorted({r["platform"] for r in rows}),
        "by_platform": {p: sum(1 for r in rows if r["platform"] == p)
                        for p in sorted({r["platform"] for r in rows})},
        "top_gain_today": max((r["d1"] for r in rows if r.get("d1") is not None), default=0),
        "history_window_days": history_days,
    }
    return {"latest_date": latest, "rows": rows, "boards": boards, "stats": stats}


def write_outputs(result: dict, out_dir: str):
    os.makedirs(out_dir, exist_ok=True)
    payload = {
        "generated_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        **result,
    }
    with open(os.path.join(out_dir, "leaderboard.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    # 浏览器直接双击打开 HTML 时 fetch 本地 JSON 会被 CORS 拦截，
    # 所以额外导出一份 JS 全局变量文件，file:// 下也能用。
    js = "window.FORGE_PULSE = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n"
    with open(os.path.join(out_dir, "leaderboard.js"), "w", encoding="utf-8") as f:
        f.write(js)
