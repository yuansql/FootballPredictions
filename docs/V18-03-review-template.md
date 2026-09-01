# 03-复盘模板（V18-Phase A · RMA 双仓强化版）

> **强制顺序**：先填「RMA 路由表」→ 再答「三问」→ 最后写「对 skill 的落地」。
> **未填 RMA 路由表，禁止写三问；未有三本账同屏，禁止写命中率。**
> 对照：`01-竞彩分析.md` / `02-头条正文.html`

---

## 01 · 先说系统改了什么（只写结构性改 skill 的项）

> 规则：单场 MISS 不加软清单/纪律；只有 ≥2 次同 fingerprint 方向 miss 或结构性口径错误才允许提案改 skill。

| 场 | 表象 | RMA | 是否提案改 skill | 理由 / 引用 fingerprint |
|---|---|---|---|---|
| … | … | `direction_rework` \| `score_rework` \| `closed` \| `skip` | 改 / 不改 | … |

**本篇决策摘要**

| 病灶 | 改 / 不改 | 证据来源（reports/fingerprint_heatmap.md 行号） |
|---|---|---|
| … | … | … |

---

## 02 · RMA 路由表（必填 · 赛后先填）

| 场 | 推方向（02 句面） | 实际 1X2 | 推比分篮 | 实际比分 | RMA | 方向子标签 | score_miss_class | fingerprint（方向 miss 时填） |
|---|---|---|---|---|---|---|---|---|
| … | 锁平 \| 锁主 \| 锁客 \| 空槽 \| 两格… | 主胜/平/客胜 | 主/次/防/旁 | x-y | `direction_rework` \| `score_rework` \| `closed` \| `skip` | `counter_hit` \| `weld_ok` \| `weld_failure` \| — | `in_contract_pack` \| `contract_out_blowout` \| — | `{weld_tag, clause_id, counter_direction, intel_slot_shape}` |

**RMA 路由规则**（由 `scripts/rma_route.py` 判定）：

- **direction_rework**：1X2 方向 miss → 只答「方向为啥对/错」，**禁止**展开「若方向对了比分…」。
- **score_rework**：方向对、精确分未挂 → 只答「比分为啥挂/没挂」，**禁止**重审方向。
- **closed**：方向对且篮内命中 → 三问可简写。
- **skip**：对外空槽 / claim=∅ → **不进对外分母**，不是 direction miss。

**对外入口口径**：

- 方向喂 `02` 句面 / `public_allowed_set`；句面「空槽」**不理 01 篮**。
- **并列 ≠ 三向**；禁止用 `01`「胶着」刷对外方向命中。
- 有格子只认格子；句面锁平/锁主/锁客。

**方向仓 miss 带焊标签时**：追加写入 `data/miss_fingerprint_ledger.jsonl` 与 `data/fingerprint_db.jsonl`，供 shadow 闸与热力图。

---

## 03 · 三本账（写了命中率就必须同屏 · V17.4.21 / V18）

> 口头先报真 miss；禁止只甩 1/3。

| 分母 | 方向 | 精确比分 | 口径说明 |
|---|---|---|---|
| **对外三场** | a/3 | b/3 | `02` 句面；三格不含旁；空槽=skip 不计分母 |
| **01 篮** | … | … | 方向用 `02`（胶着不算命中）；比分含 `01` 旁挂 |
| **全表** | … | … | 当日全部场次；滚动窗不是合同 |

### 对外合同留样（V17.4.22.2 / V18）

| 场 | 句面锁 | claim_set | 实际 1X2 | miss_class |
|---|---|---|---|---|
| … | 锁平 \| 锁主 \| 锁客 \| **空槽** | `{平}` / `{主胜}` / `{客胜}` / `∅` | 主胜/平/客胜 | `A` / `lean_flip` / — |

- `miss_class`：`A` = 允许集没有实战 1X2；`lean_flip` = 偏 X 反号；方向对则 `—`（精确 miss 走 score 仓）。
- 比分 miss 另标 `score_miss_class`：`in_contract_pack` / `contract_out_blowout`。合同外（净胜 ≥4 且篮无净 ≥3）**不提案改 skill**。
- K=0：钉槽印空仓要约；看槽仍可拆三场，**有锁才计 1 bit**。

---

## 04 · 三问（按 RMA 只展开对应仓）

> direction_rework 禁写「若方向对了比分…」；score_rework 禁重审方向。

### ① 方向为啥对/错（仅 direction_rework / 方向相关Closed）

### ② 比分为啥挂/没挂（仅 score_rework / 比分相关Closed）

### ③ 剧本推荐为啥准/不准

**带回**：…

---

## 05 · 对 skill 的落地

> 仅当「01 · 系统改了什么」中标记为“改”时才填写。

1. 具体改哪一条 clause_id / 软清单 / 纪律：
2. 引用 fingerprint 热力图或 RMA 统计：
3. 改后如何验证：`bash scripts/sync-skill-bundle.sh` + `python3 scripts/verify_accuracy_hooks.py`

---

## 06 · 口头结论

…
