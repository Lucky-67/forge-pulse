"""中文项目导读生成器。

优先使用 config/desc_zh.json 里逐条核对过的精确中文翻译（覆盖 245 条英文描述），
中文原生描述原样保留，无描述的项目基于项目名 + 语言做中性说明。
所有客观数据（星数、语言、时间、来源）来自快照，不编造功能。
"""

from __future__ import annotations

import json
import os
import re

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CN_RE = re.compile(r"[\u4e00-\u9fff]")

SOURCE_ZH = {
    "history": "历史快照基线", "trending": "GitHub Trending 热榜",
    "gh_trending": "GitHub Trending 热榜", "seed": "固定追踪清单",
    "explore": "GitLab 探索榜", "gh_search": "GitHub 搜索",
    "search_api": "GitHub 搜索", "manual": "手动补采",
}

# 无描述项目：从项目名推断用途（只在明确时给判断，否则中性说明）
NAME_HINT = [
    (("gemini-config", "proxy", "scanner"), "代理配置扫描工具",
     "用于批量探测可用代理配置，绕过地区限制访问指定服务"),
    (("skills", "skill-", "-skill", "agent-skills"), "智能体技能集合",
     "为编程智能体提供一组可调用的技能与工作流"),
    (("awesome-", "collection", "list"), "资源精选清单",
     "汇总某个领域的开源项目、工具与学习资源"),
    (("mirror", "备份"), "镜像仓库", "原项目的同步镜像，内容以原仓库为准"),
]

_trans: dict[str, str] = {}


def load_translations() -> None:
    path = os.path.join(BASE, "config", "desc_zh.json")
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                _trans.update(json.load(f))
        except (ValueError, OSError):
            pass


def _clean(text: str, limit: int = 260) -> str:
    """清理描述：去 URL 噪声、压空白、截断过长的英文。"""
    text = re.sub(r"https?://\S+", "", text or "").strip()
    text = re.sub(r"\s+", " ", text)
    if len(text) > limit:
        text = text[:limit].rstrip() + "…"
    return text


def _end(text: str) -> str:
    if text and text[-1] not in "。！？.!?…":
        text += "。"
    return text


def _name_hint(name: str) -> tuple[str, str] | None:
    low = name.lower()
    for keys, typ, summary in NAME_HINT:
        if any(k in low for k in keys):
            return typ, summary
    return None


def _core_desc(repo: dict) -> str:
    """返回具体的功能说明正文（不含客观数据）。"""
    key = repo.get("key") or ""
    desc = _clean(repo.get("description") or "")
    name = repo.get("full_name") or ""

    # 1) 有精确翻译 —— 最优先
    if key in _trans:
        return _end(_trans[key])

    # 2) 中文原生描述 —— 原样保留
    if desc and CN_RE.search(desc):
        return _end(desc)

    # 3) 英文但没翻译到 —— 保留原文 + 中性引导（不瞎猜功能）
    if desc:
        return f"项目自述（原文）：{_end(desc)}"

    # 4) 无描述 —— 基于项目名的保守说明
    hint = _name_hint(name)
    short = name.split("/")[-1]
    if hint:
        typ, summary = hint
        return f"这是{hint[0]}。从项目名看，它{summary}。"
    lang = repo.get("language") or "未标注语言"
    return f"该项目暂无文字描述，从仓库名「{short}」无法判断具体用途，主要使用{lang}开发。"


def zh_brief(repo: dict, as_of: str) -> str:
    """生成一段中文导读：具体功能说明 + 客观事实。"""
    body = _core_desc(repo)

    stars = repo.get("stars") or 0
    forks = repo.get("forks")
    lang = repo.get("language") or "未标注"
    created = repo.get("created") or "未记录"
    stats = f"截至 {as_of}，该项目累计 {stars:,} 星"
    if forks is not None:
        stats += f"、{forks:,} 次 fork"
    stats += f"，主要使用{lang}开发，创建于{created}。"
    d7, d30 = repo.get("d7"), repo.get("d30")
    if d7 is not None:
        stats += f"近 7 天新增 {d7:,} 星"
        if d30 is not None:
            stats += f"，近 30 天新增 {d30:,} 星"
        stats += "。"

    src = SOURCE_ZH.get(repo.get("source") or "", repo.get("source") or "未知渠道")
    days = repo.get("days_tracked")
    tail = f"该项目由{src}纳入追踪"
    if days:
        tail += f"，已连续追踪 {days} 天"

    return body + stats + tail + "。"


def enrich(rows: list[dict], as_of: str) -> None:
    """就地给每行加 zh_brief 字段。"""
    load_translations()
    for r in rows:
        r["zh_brief"] = zh_brief(r, as_of)
