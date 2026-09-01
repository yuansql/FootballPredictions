# 2026-09-01 自主预测 run 摘要

> 说明：本次 run 为 Phase A 完成后首批真实数据填充。包含 1 场赛后回顾 + 1 场赛前预测。

---

## 已分析场次

| # | 日期 | 对阵 | 联赛 | 类型 | 研究方向 | 实际结果 | RMA |
|---|------|------|------|------|---------|---------|-----|
| 1 | 2026-09-01 | 阿斯顿维拉 vs 阿森纳 | 英超 | 回顾性预测 | 客胜（防平） | 0-1 客胜 | closed |
| 2 | 2026-09-01 | 都灵 vs 蒙扎 | 意大利杯 | 赛前预测 | 主胜（防平） | 待回填 | — |

---

## 情报来源

- 阿斯顿维拉 vs 阿森纳：新浪体育赛事前瞻 + Polymarket 比赛结果页
- 都灵 vs 蒙扎：Toffeeweb 赛事前瞻 + 搜狐赛事前瞻

---

## Lint 结果

```bash
python3 scripts/lint_draft.py data/prediction-runs/2026-09-01/01-阿斯顿维拉vs阿森纳.md --warn-only
python3 scripts/lint_draft.py data/prediction-runs/2026-09-01/01-都灵vs蒙扎.md --warn-only
```

**结果**：
- 阿斯顿维拉 vs 阿森纳：2 个 warn（outside_goals_band：0-2/1-1 总球 2 不在 parser 解析的 {1,3} 中）
- 都灵 vs 蒙扎：1 个 warn（outside_goals_band：1-1 总球 2 不在 parser 解析的 {1,3} 中）

**说明**：当前 `lint_draft.py` 的进球档解析器把 "1-3 球" 解析为端点集合 {1, 3}，不支持连续区间 {1,2,3}。这是 lint 脚本的已知限制，不影响实际分析质量。后续 Phase B 可修复解析器。

---

## Canonical Log

已写入 `data/prediction_log.jsonl` 2 行：

- `run_id=20260901-retro-avl-ars`（closed，方向/比分均命中）
- `run_id=20260901-tor-mon`（pre_match only，待赛后回填 post_match）

验证：`python3 scripts/log_append.py --validate-only < data/prediction_log.jsonl` → Validated 2 row(s)

---

## 后续行动

1. **都灵 vs 蒙扎赛后**：将实际比分回填到 `data/prediction-runs/2026-09-01/03-复盘-都灵vs蒙扎.md`，并按 RMA 规则分类；同时追加一条带 `post_match` 的 log 行到 `data/prediction_log.jsonl`。
2. **继续跑下去**：每 1–2 天找 1–3 场比赛，重复本流程，目标是 30–50 场完整数据。
3. **修复 lint**：在 Phase B 修复 `lint_draft.py` 的进球档解析器，使其支持 "1-3 球" 连续区间。

---

## 文件清单

- `data/prediction-runs/2026-09-01/01-阿斯顿维拉vs阿森纳.md`
- `data/prediction-runs/2026-09-01/02-头条正文-阿斯顿维拉vs阿森纳.txt`
- `data/prediction-runs/2026-09-01/03-复盘-阿斯顿维拉vs阿森纳.md`
- `data/prediction-runs/2026-09-01/01-都灵vs蒙扎.md`
- `data/prediction-runs/2026-09-01/02-头条正文-都灵vs蒙扎.txt`
- `data/prediction-runs/2026-09-01/RUN-SUMMARY.md`
- `data/prediction_log.jsonl`
