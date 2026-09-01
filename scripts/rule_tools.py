#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""可调用规则工具（RuleTool）PoC — Phase A。

目标：把 lint_draft.py 中依赖人脑记忆的检查点逐步变成可调用、可记录、可统计的工具。
每个 RuleTool 接收一个 context dict，返回结构化 verdict，并可选记录遥测。
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class RuleVerdict:
    """规则工具返回的结构化判定。"""

    rule_id: str
    verdict: str  # PASS, FORBID, FLAG, SKIP
    message: str | None = None
    latency_ms: float | None = None
    telemetry: dict = field(default_factory=dict)


class RuleTool:
    """规则工具基类。"""

    rule_id: str
    description: str

    def run(self, context: dict) -> RuleVerdict:
        raise NotImplementedError


# -----------------------------------------------------------------------------
# 反剧本收据规则工具
# -----------------------------------------------------------------------------

RECEIPT_MARKERS = ("【反剧本收据】", "counter_direction=", "counter_one_liner=")

# (tag, trigger_words)
WELD_HINTS: list[tuple[str, tuple[str, ...]]] = [
    ("revenge_home", ("讨债", "同址刚", "三日再战")),
    ("weld_draw", ("焊平", "平局味最浓")),
    ("manage_tie", ("管理比赛", "输一场仍晋级", "晋级≠90")),
    ("derby_caution", ("德比", "同城德比")),
    ("continuation_guest", ("客队刚赢", "同址客胜", "刚赢再战")),
]


def _guess_weld_tag(block: str, direction: str) -> str | None:
    """从文本中猜测是否命中 weld_tag。"""
    best: tuple[int, str] | None = None
    for tag, words in WELD_HINTS:
        hits = sum(1 for w in words if w in block)
        if tag == "weld_draw" and direction.strip() in ("平", "平局"):
            hits += 2
        if tag == "revenge_home" and "主胜" in direction and ("讨债" in block or "同址" in block):
            hits += 1
        if hits and (best is None or hits > best[0]):
            best = (hits, tag)
    if best and best[0] >= 2:
        return best[1]
    return None


def _needs_receipt(block: str, direction: str, tag: str | None) -> bool:
    """判断是否需要反剧本收据。与 lint_draft.py 逻辑保持一致。"""
    if not tag:
        return False
    if tag == "continuation_guest":
        return False  # 降权标签，不强制收据
    if any(m in block for m in RECEIPT_MARKERS):
        return False
    if tag == "revenge_home" and ("防平" in direction or "胶着" in direction):
        return False
    if tag == "weld_draw" and ("客不败" in direction or "并列" in direction):
        return False
    return True


class ReceiptRuleTool(RuleTool):
    """
    检查：当文本使用 weld_tag 焊死方向并冲 TOP 时，是否已填写完整反剧本收据。
    对应 lint_draft.py 中的 _needs_receipt 与 clause_id/counter_direction 检查。
    """

    rule_id = "receipt_required"
    description = "焊叙事标签必须附带完整反剧本收据"

    def run(self, context: dict) -> RuleVerdict:
        start = time.perf_counter()
        block = context.get("block", "")
        direction = context.get("direction", "")
        tag = context.get("weld_tag") or _guess_weld_tag(block, direction)

        if not tag:
            latency = (time.perf_counter() - start) * 1000
            return RuleVerdict(self.rule_id, "PASS", latency_ms=latency)

        if _needs_receipt(block, direction, tag):
            latency = (time.perf_counter() - start) * 1000
            return RuleVerdict(
                self.rule_id,
                "FORBID",
                message=f"疑似 {tag} 焊叙事但未写【反剧本收据】（V17.4.15）",
                latency_ms=latency,
                telemetry={"weld_tag": tag},
            )

        # continuation_guest 不需要收据，直接放行
        if tag == "continuation_guest":
            latency = (time.perf_counter() - start) * 1000
            return RuleVerdict(self.rule_id, "PASS", latency_ms=latency)

        # 其他 weld_tag 已有收据，进一步检查必要字段
        missing: list[str] = []
        if "counter_direction=" not in block:
            missing.append("counter_direction")
        if "counter_one_liner=" not in block:
            missing.append("counter_one_liner")
        if "why_reject=" not in block:
            missing.append("why_reject")
        if "clause_id=" not in block:
            missing.append("clause_id")

        latency = (time.perf_counter() - start) * 1000
        if missing:
            return RuleVerdict(
                self.rule_id,
                "FLAG",
                message=f"【反剧本收据】字段不完整：缺少 {', '.join(missing)}",
                latency_ms=latency,
                telemetry={"weld_tag": tag, "missing_fields": missing},
            )

        return RuleVerdict(self.rule_id, "PASS", latency_ms=latency)


# -----------------------------------------------------------------------------
# 规则工具注册与编排
# -----------------------------------------------------------------------------

REGISTRY: dict[str, type[RuleTool]] = {
    ReceiptRuleTool.rule_id: ReceiptRuleTool,
}


def get_tool(rule_id: str) -> RuleTool:
    if rule_id not in REGISTRY:
        raise KeyError(f"Unknown rule tool: {rule_id}")
    return REGISTRY[rule_id]()


def run_pipeline(context: dict, rule_ids: list[str] | None = None) -> list[RuleVerdict]:
    """按顺序运行一组规则工具。"""
    if rule_ids is None:
        rule_ids = list(REGISTRY.keys())
    return [get_tool(rid).run(context) for rid in rule_ids]


# -----------------------------------------------------------------------------
# 自检
# -----------------------------------------------------------------------------

def _self_check() -> None:
    tool = ReceiptRuleTool()

    # 1. 无 weld_tag，PASS
    v = tool.run({"block": "普通分析", "direction": "主胜"})
    assert v.verdict == "PASS", v

    # 2. 有复仇叙事但无收据，FORBID
    block2 = "主队同址刚输要面子，方向｜比分：主胜｜**2-1** 主推"
    v2 = tool.run({"block": block2, "direction": "主胜"})
    assert v2.verdict == "FORBID", v2

    # 3. 有完整收据，PASS
    block3 = """主队同址刚输要面子，【反剧本收据】counter_direction=客胜｜
counter_one_liner=客队近期连胜｜why_reject=主核心复出｜clause_id=script#1
方向｜比分：主胜｜**2-1** 主推"""
    v3 = tool.run({"block": block3, "direction": "主胜"})
    assert v3.verdict == "PASS", v3

    # 4. 有收据但缺字段，FLAG
    block4 = "主队同址刚输要面子，【反剧本收据】counter_direction=客胜\n方向｜比分：主胜｜**2-1** 主推"
    v4 = tool.run({"block": block4, "direction": "主胜"})
    assert v4.verdict == "FLAG", v4

    # 5. continuation_guest 不需要收据
    block5 = "客队刚赢再战，方向｜比分：主胜｜**2-1** 主推"
    v5 = tool.run({"block": block5, "direction": "主胜"})
    assert v5.verdict == "PASS", v5

    print("OK rule_tools self-check")


if __name__ == "__main__":
    _self_check()
