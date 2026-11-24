"""Forge Pulse 一键入口：采集 → 算增量 → 生成看板。"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from analyze import build, load_snapshots, save_snapshot, write_outputs  # noqa: E402
from collectors import collect_all  # noqa: E402
from describe import enrich  # noqa: E402
from http_client import BudgetExceeded, Http  # noqa: E402
from render import write_page  # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_cfg() -> dict:
    with open(os.path.join(BASE, "config", "settings.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    # GitHub Actions 注入 GITHUB_TOKEN：配置里没填 token 时用它，
    # 拿到 5000 次/小时配额，避免匿名 60 次/小时导致大量仓库采不到。
    if not (cfg.get("github", {}).get("token") or "").strip():
        env_token = os.environ.get("GITHUB_TOKEN", "").strip()
        if env_token:
            cfg.setdefault("github", {})["token"] = env_token
    return cfg


def today(cfg: dict) -> str:
    tz = timedelta(hours=int(cfg.get("board", {}).get("tz_offset_hours", 8)))
    return datetime.now(timezone(tz)).strftime("%Y-%m-%d")


def main() -> int:
    p = argparse.ArgumentParser(description="Forge Pulse 多平台涨星榜")
    p.add_argument("--collect", action="store_true", help="只采集快照")
    p.add_argument("--analyze", action="store_true", help="只重算榜单")
    p.add_argument("--render", action="store_true", help="只重新生成看板")
    p.add_argument("--all", action="store_true", help="完整跑一遍（默认）")
    args = p.parse_args()
    do_all = args.all or not (args.collect or args.analyze or args.render)

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s",
                        datefmt="%H:%M:%S")
    cfg = load_cfg()
    net = cfg.get("network", {})
    http = Http(timeout=net.get("timeout_seconds", 20),
                retries=net.get("retries", 2),
                gap=net.get("request_gap_seconds", 0.15),
                max_wait=net.get("max_wait_seconds", 600))
    data_dir = os.path.join(BASE, "data")
    snap_dir = os.path.join(data_dir, "snapshots")

    if do_all or args.collect:
        print(">> 开始采集 GitHub / GitLab / Gitee …")
        try:
            repos, stats = collect_all(http, cfg, os.path.join(BASE, "config", "watchlist.txt"))
        except BudgetExceeded as e:
            print("!! 请求配额或等待预算耗尽：" + str(e))
            return 3
        day = today(cfg)
        path = save_snapshot(snap_dir, day, repos)
        print(f">> 采集汇总：{stats}；保存 {len(repos)} 条到 {path}")
        print(">> " + http.summary())

    result = None
    if do_all or args.analyze:
        snaps = load_snapshots(snap_dir)
        result = build(snaps, cfg.get("board", {}))
        enrich(result.get("rows", []), result.get("latest_date") or today(cfg))
        write_outputs(result, data_dir)
        s = result.get("stats", {})
        print(f">> 榜单已生成：{s.get('tracked_repos', 0)} 个仓库，"
              f"{s.get('snapshot_days', 0)} 天快照，日期 {s.get('latest_date')}")

    if do_all or args.render:
        page = os.path.join(BASE, "docs", "index.html")
        write_page(page, result)
        print(">> 看板已生成（数据内嵌，可离线/手机打开）：" + page)

    print("完成。双击 docs/index.html 或运行「查看看板.bat」查看。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
