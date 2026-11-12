# -*- coding: utf-8 -*-
"""V15.6 历史标签的 Shadow 记录器；不得进入正式概率或出票链。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

VERSION = "V18-shadow"
ALLOWED_LABELS = frozenset({"StarFactor", "Kryptonite", "Jinx", "Zombie", "Edge_Refine"})


@dataclass(frozen=True)
class ShadowReport:
    labels: tuple[str, ...]


def observe_v156(labels: Iterable[str]) -> ShadowReport:
    unique = tuple(dict.fromkeys(labels))
    unknown = set(unique) - ALLOWED_LABELS
    if unknown:
        raise ValueError(f"未知 V15.6 观察标签: {sorted(unknown)}")
    return ShadowReport(unique)


def format_patch_report(report: ShadowReport) -> str:
    triggered = "+".join(report.labels) if report.labels else "无"
    return "\n".join((
        "【V15.6补丁】状态=历史观察标签｜概率修改=禁用",
        f"触发={triggered}",
        "用途=仅Shadow特征账；不得修改λ、方向、比分、EV或出票",
    ))


__all__ = ["VERSION", "ALLOWED_LABELS", "ShadowReport", "observe_v156", "format_patch_report"]
