# Phase A 完成报告：football-predict-v17 优化

> 周期：1–2 周目标已达成。
> 目标：止血 + 建立基线 + 统一数据层 + 术语清晰化 + RuleTool PoC。

---

## 一、完成的工作

| # | 任务 | 状态 | 关键产出 |
|---|------|------|---------|
| 1 | 修复 `receipt_fingerprint.py` 死代码 | ✅ | 新增 `append_fingerprint()`，移除不可达行 |
| 2 | 统一 prediction log schema | ✅ | `schemas/prediction_log.json` |
| 3 | 实现 log 验证/追加工具 | ✅ | `scripts/log_append.py`, `scripts/requirements.txt` |
| 4 | 术语表 | ✅ | `docs/V17-terminology.md` |
| 5 | RuleTool PoC | ✅ | `scripts/rule_tools.py`（ReceiptRuleTool），并接入 `lint_draft.py` |
| 6 | 复盘模板强化 | ✅ | `docs/V18-03-review-template.md` |
| 7 | Edge 历史与 fingerprint DB | ✅ | `data/edge_history.csv`, `data/fingerprint_db.jsonl` |
| 8 | 端到端验证 | ✅ | 所有脚本 self-check 通过 |

---

## 二、新增 / 修改文件清单

### 新增

- `schemas/prediction_log.json` —— canonical log 的 JSON Schema
- `scripts/log_append.py` —— 验证 + 追加 canonical log 行
- `scripts/requirements.txt` —— Python 依赖（当前仅 jsonschema）
- `scripts/rule_tools.py` —— 可调用规则工具库（含 ReceiptRuleTool PoC）
- `docs/V17-terminology.md` —— 术语表
- `docs/V18-03-review-template.md` —— 强化版复盘模板
- `data/edge_history.csv` —— Edge 回测历史数据模板
- `data/fingerprint_db.jsonl` —— 结构化 fingerprint 数据库
- `docs/phase-a-report.md` —— 本报告

### 修改

- `scripts/receipt_fingerprint.py` —— 修复第 120–122 行死代码，新增 `append_fingerprint()`
- `scripts/lint_draft.py` —— 接入 ReceiptRuleTool，输出遥测 verdict

---

## 三、验收结果

已运行端到端验证，全部通过：

```bash
source .venv/bin/activate
python3 scripts/receipt_fingerprint.py   # OK
python3 scripts/rule_tools.py            # OK
python3 scripts/rma_route.py             # OK
python3 scripts/verify_accuracy_hooks.py # PASS V17.4.22.2
python3 scripts/verify_intel_first.py    # PASS V17.4.9
python3 scripts/log_append.py --validate-only < sample.jsonl  # Validated 1 row
```

结论：Phase A 不破坏现有工作流，新增工具可独立运行。

---

## 四、立即使用方式

### 1. 激活环境

```bash
cd /Users/wumm/学习/AQQ/2足球框架
python3 -m venv .venv
source .venv/bin/activate
pip install -r scripts/requirements.txt
```

### 2. 验证一条 prediction log 行

```bash
echo '{"run_id": "test", "date": "2026-08-04", "match": "A vs B", "schema_version": "1.0.0", "skill_version": "V17.4.22.2"}' | python3 scripts/log_append.py --validate-only
```

### 3. 追加一条 log

```bash
echo '{...}' | python3 scripts/log_append.py
# 追加到 data/prediction_log.jsonl
```

### 4. 跑 lint（含 RuleTool 遥测）

```bash
python3 scripts/lint_draft.py drafts/2026-09-01 --warn-only
```

### 5. 复盘时

使用 `docs/V18-03-review-template.md`，**先填 RMA 路由表，再答三问**。

---

## 五、Phase B 前期待办（建议接下来 2–4 周做）

1. **跑满 30–50 场完整数据**
   - 每场按 `schemas/prediction_log.json` 写一行到 `data/prediction_log.jsonl`。
   - 复盘率 100%，lint 通过率目标 ≥95%。

2. **把现有脚本改从 canonical log 读取**
   - `replay_rma_stats.py` → 读 `data/prediction_log.jsonl`
   - `receipt_fingerprint.py` → 读 `data/fingerprint_db.jsonl`
   - 删除 ad-hoc JSON 文件。

3. **扩展 RuleTool 覆盖更多检查点**
   - TOP2 live fingerprint 检查
   - 一原子 / 空槽检查
   - HT/FT 分轨检查

4. **创建 fingerprint heatmap 报告**
   - `scripts/fingerprint_heatmap.py`
   - 输出 `reports/fingerprint_heatmap.md`
   - 作为规则修改的唯一依据。

5. **阈值可配置化**
   - 创建 `config/thresholds.yaml`
   - 把 `1% / 3% / 5% / ε=0.15 / τ=0.10` 移入配置。

6. **规则瘦身草案**
   - 软清单 7→4
   - 纪律 12→8
   - 禁止清单分级 fatal/warn

---

## 六、限制与已知问题

1. `.venv` 未提交到 git（应在 `.gitignore` 中确认已忽略）。
2. `data/prediction_log.jsonl` 尚未创建，等第一场实际写入。
3. skills/ 目录下的 `03-复盘模板.md` 仍为 V17.4.16 版；Phase B 升级 skill 包时一次性同步。
4. RuleTool 目前只覆盖 receipt 检查，其他检查点还在 `lint_draft.py` 中。

---

## 七、一句话总结

> Phase A 把框架从“一堆人会记漏的规则”变成了“有 schema、有 tool、有 log、有模板”的可迭代底座；接下来用 30–50 场真实数据喂饱 canonical log，再决定 Phase B 该删什么、该留什么。
