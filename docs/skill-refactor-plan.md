# 2足球框架 V17.4.22.2 优化重构计划

> 目标：在不破坏“情报优先、方向优先、诚实闭环”核心纪律的前提下，降低执行门槛、提高可维护性、让准确率提升真正落在数据闭环上。

---

## 一、修改总纲

### 1.1 总体目标

1. **降低心智负担**：把 V17.4.22.2 中交织的数十条规则、补丁、版本号梳理成清晰的三层结构。
2. **强化执行闭环**：让 `反剧本收据`、`RMA 双仓`、`一原子/空槽` 从“概念”变成可 lint、可统计、可复盘的工具链。
3. **数据驱动迭代**：规则修改必须以 fingerprint / RMA 热力图为依据，单场 miss 不再升级 skill。
4. **提升可移植性**：减少对本地文件结构、脚本、黑话的强依赖，提供无脚本降级工作流。
5. **统一对外口径**：明确区分研究层（01）、对外合同层（02）、复盘对账层（03），避免命中率口径造假。

### 1.2 核心原则

| 原则 | 含义 |
|------|------|
| **诚实优先** | 无 lean、无锁则 02 空槽；宁可 skip，也不并集刷命中。 |
| **方向优先** | 先锁 1X2 方向，再拆进球档与比分；方向未定前先不扩比分篮。 |
| **一仓一刀** | 方向 miss 只修方向条款，比分 miss 只修比分条款，禁止一场比赛同时改两仓。 |
| **数据驱动** | 新规则/软清单/纪律补丁的引入，必须有 ≥2 次同 fingerprint 结构化 miss 或结构性口径错误作为依据。 |
| **奥卡姆剃刀** | 能合并的规则合并，能删除的删除；新补丁必须附带“如果不加会怎样”的失效案例。 |
| **渐进迁移** | 不直接废弃 V17，而是先并行跑 V18-lite，验证后再冻结旧版本。 |

### 1.3 阶段划分

| 阶段 | 时间 | 重点任务 | 产出物 |
|------|------|---------|--------|
| **Phase 1：止血** | 1–2 周 | 严格执行现有 lint + 复盘必填；统计当前最大执行遗漏 | `执行遗漏热力图.md` |
| **Phase 2：精简** | 2–4 周 | 术语统一、软清单瘦身、纪律合并、版本号整理 | `V18-core.md` |
| **Phase 3：重构** | 4–8 周 | 工具链补全、数据层建设、阈值回测 | `scripts/*`、`data/fingerprint_db.jsonl` |
| **Phase 4：固化** | 8–12 周 | 合并为新主版本 V18，冻结 V17 补丁，发布迁移指南 | `SKILL.md` V18 正式版 |

---

## 二、详细修改说明

### 2.1 术语与版本层：统一命名，结束历史包袱

#### 问题
- 当前 skill 中同时存在 `V17.4.22.2`、`V15.6`、`V17.4.9/15/16/20/21/22.1/22.2` 等多层版本号。
- 黑话密集：`λ→λ′`、`StarFactor`、`Kryptonite`、`Jinx`、`Zombie`、`Edge_Refine`、`slim pack` 等对新用户极不友好。
- 历史补丁与当前主版本混排，阅读成本高。

#### 动作
1. **版本号统一**：
   - 主版本号统一为 `V18`（代表重构后的稳定版）。
   - 子模块使用语义化命名：`V18-intel-first`、`V18-output`、`V18-patches`、`V18-receipts`。
   - 旧版本号仅在 `V18-changelog.md` 中保留，便于追溯。

2. **术语表化**：
   - 在 `references/V18-glossary.md` 中建立术语表，每个术语给出：中文名、英文缩写、一句话定义、典型使用场景。
   - skill 正文首次出现术语时给出中文解释，后续可缩写。

3. **补丁归一**：
   - 将 `V15.6 五补丁` 整体吸收进 `V18-patches` 模块，不再以“历史补丁”形式出现。
   - 每个补丁注明：触发条件、作用、在 pipeline 中的位置、与反剧本收据的交互关系。

#### 验收标准
- `SKILL.md` 正文中只出现一个主版本号 `V18`。
- 任意新用户能在 15 分钟内通过 `V18-glossary.md` 理解全部核心术语。
- 旧版本号不再出现在执行流程中。

---

### 2.2 规则层瘦身：合并重复、删除噪音

#### 问题
- 禁止清单 20+ 项、软清单 7 项、纪律 12 项，规则之间相互重叠（如德比谨慎同时出现在软清单和纪律中）。
- 规则过多导致 agent 执行时遗漏率高。

#### 动作
1. **软清单压缩为 4 条核心约束**：
   - `soft#A`：低含金量主胜（SP≤1.50 且证据单薄）封顶三星、不进 TOP2。
   - `soft#B`：次回合领先方 / 德比 / 首回 0-0 定生死，默认不进 TOP1；进 TOP2 须有额外硬证据。
   - `soft#C`：刚大胜/屠杀后短期复赛，不满星 TOP1。
   - `soft#D`：continuation_guest 默认不进 TOP2，除非同时满足客上轮净胜≤1 且主核心缺阵≥2。
   - 原 90′ 自检、杯赛首回合主场约束并入 `soft#B` 的“晋级叙事≠竞彩 90′”说明中。

2. **纪律合并为 8 条**：
   - `discipline#1`：环境维不焊方向。
   - `discipline#2`：方向未 Receipt 闸前不扩比分篮（逃生口规则）。
   - `discipline#3`：HT/FT 分轨 + 开口备路径。
   - `discipline#4`：领先两球 / 大比分半场 ≠ 终场锁定。
   - `discipline#5`：体能税只加权，不占小胜上限。
   - `discipline#6`：揭幕/小球教练画像不焊平。
   - `discipline#7`：翻盘局旁挂多球，加时/点球≠90′。
   - `discipline#8`：同链反回声 + 单格 Top3 + 低结构约束。

3. **禁止清单分级**：
   - `fatal`（fatal-violation）：先算 Edge 再编故事、三格套餐、混主客胜族、用天气焊方向、空槽冒充锁平。
   - `warn`（warn-violation）：邻格凑数、旁注混入公开格、标题晋级主语复制进 90′ 方向。

#### 验收标准
- 软清单 ≤4 条、纪律 ≤8 条、禁止清单 `fatal` ≤10 条。
- `lint_draft.py` 能自动区分 `fatal` 和 `warn` 并给出不同退出码。
- 任意一场 miss 最多只关联一条软清单/纪律项，便于归因。

---

### 2.3 反剧本收据工具化：不让 Receipt 流于形式

#### 问题
- 反剧本收据概念强，但依赖人工填写，易出现字段不全或空话。
- `clause_id` 引用的是 skill 内部的条款号，agent 容易写错或引用已删除条款。

#### 动作
1. **schema 强制**：
   - 新增 `references/receipt_schema.json`：
     ```json
     {
       "required": ["weld_tag", "counter_direction", "counter_one_liner", "why_reject", "clause_id", "intel_slots"],
       "properties": {
         "weld_tag": {"enum": ["revenge_home", "weld_draw", "manage_tie", "derby_caution", "continuation_guest"]},
         "counter_direction": {"enum": ["主胜", "平", "客胜"]},
         "counter_one_liner": {"type": "string", "minLength": 10},
         "why_reject": {"type": "string"},
         "clause_id": {"pattern": "^(soft|discipline|script)#[A-Za-z0-9]+$"},
         "intel_slots": {"type": "array", "minItems": 1}
       }
     }
     ```

2. **lint 自动检查**：
   - `lint_draft.py` 增加 `--receipt` 模式，对 01 文本中命中 weld_tag 的场次自动检查 receipt 字段。
   - `counter_one_liner` 必须能在【取证清单】或【情报叙事】中找到关键字匹配。

3. **clause_id 索引**：
   - 维护 `references/clause-index.json`，列出所有有效的 `clause_id` 及对应规则摘要。
   - lint 时校验 `clause_id` 是否存在且最新。

4. **Receipt 热力图**：
   - 在 `data/receipt_heatmap.json` 中按 `(weld_tag, clause_id, counter_direction)` 聚合 `counter_hit` / `weld_ok` / `weld_failure`。
   - 每 30 场生成一次 `reports/receipt_heatmap.md`，用于判断某标签是否应被降权或禁用。

#### 验收标准
- 所有“焊死方向并冲 TOP2”的场次 100% 包含完整 receipt。
- `clause_id` 引用错误率 0%。
- 每 30 场更新一次 receipt 热力图。

---

### 2.4 RMA 双仓与 Fingerprint 闭环：让复盘真正驱动迭代

#### 问题
- RMA 双仓设计好，但复盘可能流于“方向错了”一句带过。
- fingerprint 依赖 `miss_fingerprint_ledger.jsonl`，但没有统一的结构化查询和热力分析。

#### 动作
1. **复盘模板强制化**：
   - `03-复盘模板.md` 增加 RMA 路由表，每场必须先选：
     - `direction_rework` / `score_rework` / `closed` / `skip`
     - 子标签：`counter_hit` / `weld_ok` / `weld_failure`
   - 未填 RMA 路由的 `03-复盘.md` 不允许写入。

2. **fingerprint 数据库化**：
   - 将 `data/miss_fingerprint_ledger.jsonl` 升级为 `data/fingerprint_db.jsonl`，字段：
     ```json
     {
       "date": "2026-09-01",
       "match": "A vs B",
       "rma_route": "direction_rework",
       "weld_tag": "revenge_home",
       "clause_id": "soft#A",
       "counter_direction": "客胜",
       "intel_slot_shape": ["主核心伤停≥2", "客近5态3胜2平"],
       "score_miss_class": "in_contract_pack",
       "result": "主胜焊死，实际客胜2-1",
       "tag_version": "V18"
     }
     ```

3. **热力报告自动化**：
   - 新增 `scripts/fingerprint_heatmap.py`，读取 fingerprint_db 输出：
     - 各 `clause_id` 的 `方向 miss 率`
     - 各 `intel_slot_shape` 的 `误信率`
     - TOP3 高频误信情报组合
   - 输出 `reports/fingerprint_heatmap.md`，作为规则修改的唯一依据。

4. **规则冻结机制**：
   - 单场 miss → 只记录 fingerprint，不改 skill。
   - 同 fingerprint ≥2 次方向 miss 或结构性口径错误 → 才允许提案改 skill。
   - 修改 skill 时必须引用 `reports/fingerprint_heatmap.md` 中的具体行。

#### 验收标准
- 复盘 RMA 路由填写率 100%。
- 每场 miss 都有 fingerprint 记录。
- 规则修改 100% 附带 fingerprint 热力依据。

---

### 2.5 Edge 阈值与统计校准：从“拍脑袋”到回测

#### 问题
- `Edge_eff ≥1% / ≥3% / ≥5%`、ε=0.15、τ=0.10 等阈值缺少校准依据。
- 不同联赛、不同盘口类型的最优阈值可能不同。

#### 动作
1. **历史回测数据建设**：
   - 维护 `data/edge_history.csv`，字段：`日期、联赛、盘口类型、Edge_eff、推荐方向、实际结果、是否命中`。
   - 每月按联赛/盘口分层统计：不同 Edge 阈值下的实际命中率、ROI。

2. **阈值可配置化**：
   - 新增 `config/thresholds.yaml`：
     ```yaml
     defaults:
       1x2_min_edge: 0.01
       handicap_min_edge: 0.03
       goals_min_edge: 0.03
       high_push_min_edge: 0.05
       epsilon_margin: 0.15
       tau_counter_leaf: 0.10
     per_league:
       英超: {1x2_min_edge: 0.015}
       挪超: {handicap_min_edge: 0.04}
     ```

3. **阈值优化脚本**：
   - 新增 `scripts/threshold_optimizer.py`，基于 `data/edge_history.csv` 用网格搜索优化阈值。
   - 输出推荐阈值及置信区间，但不自动覆盖，须经人工确认后写入 `config/thresholds.yaml`。

4. **诚实声明强化**：
   - 在输出中增加一行 Edge 来源说明：
     > “本场均使用体彩官方 SP，RAW→λ′ 口径，多数场次 Edge 为负属正常；仅当作辅助闸门。”

#### 验收标准
- 阈值有 6 个月以上历史回测支撑，或在回测不足时标注“实验值”。
- 每季度至少更新一次 `config/thresholds.yaml`。
- Edge 阈值不得用于覆盖已定方向。

---

### 2.6 输出层与对外口径：01/02/03 边界清晰化

#### 问题
- 01 研究层和 02 对外层边界容易混淆，导致研究层“胶着”被对外层收窄、命中率口径造假。
- 02 “今晚我钉 K 场”与研究层 TOP 排序脱节。

#### 动作
1. **三层职责明确**：
   | 文件 | 性质 | 允许内容 | 禁止内容 |
   |------|------|---------|---------|
   | `01-研究分析.md` | 内部scout | 胶着三向、权重 Top3、旁注、低结构 | 不对外承担命中率 |
   | `02-对外推荐.md` | 公开合同 | 一原子、锁平、空槽、≤2 钉场 | 禁止胶着三向、禁止套餐 |
   | `03-复盘.md` | 对账 | RMA 路由、命中率分数、三本账 | 禁止只报好看的 |

2. **02 输出模板化**：
   - 提供固定结构：
     ```
     今日钉场（K=0/1/2）：
     场 X：主胜（1-0/2-0），依据：...
     今日观望：...（仅写方向 lean，不写锁定比分）
     ```
   - 如果 K=0，必须有“今日无钉场，全部观望/空槽”的显式说明。

3. **三本账同屏模板**：
   - `03-复盘.md` 命中率区域强制三栏：
     ```
     | 对外三场 | 01 篮 | 全表 |
     |---------|-------|------|
     | 方向 X/Y | 方向 A/B | 方向 M/N |
     ```

4. **空槽与 skip 的可视化**：
   - 在 02 中以 `∅ 空槽` 显式标记，不隐匿为“观望”。
   - `route_rma_public` 对空槽返回 `skip`，不进对外分母。

#### 验收标准
- 01/02/03 三层内容不再互相冒充。
- 02 钉场数 K∈[0,2]，超过 2 自动 lint 报错。
- 03 命中率必须同屏展示三本账。

---

### 2.7 可移植性与工具链：让框架能独立跑起来

#### 问题
- 强依赖 `~/.agents/skills/football-predict-v17` 路径和多个本地脚本，换环境容易失效。
- 没有 `requirements.txt` 或安装说明，新人很难跑通工具链。

#### 动作
1. **路径解耦**：
   - 所有脚本和 skill 指令中的路径统一从 `SKILL_DIR` 或 `AQQ_FOOTBALL_ROOT` 环境变量解析。
   - 不再写死 `~/.agents/skills/football-predict-v17`。

2. **工具包化**：
   - 在 `scripts/` 下增加：
     - `setup.py`
     - `requirements.txt`（列出 pandas、jsonschema、pyyaml 等依赖）
     - `README.md`（说明如何安装、如何跑 lint、如何复盘）

3. **无脚本降级流程**：
   - 在 `docs/manual-mode.md` 中提供：没有 Python 环境时，如何用纯 Markdown 模板完成 01/02/03 输出。
   - 手动模式下仍可通过チェックリスト保证核心纪律。

4. **配置集中化**：
   - 所有可调参数迁移到 `config/` 目录：
     - `config/thresholds.yaml`
     - `config/receipt_schema.json`
     - `config/clause-index.json`

#### 验收标准
- 新机器上执行 `pip install -r scripts/requirements.txt && python scripts/lint_draft.py --help` 能直接跑通。
- 无脚本模式下，核心产出物仍符合格式要求。

---

### 2.8 新增配套工具

| 工具 | 职责 | 输入 | 输出 |
|------|------|------|------|
| `lint_draft.py` | 发前检查 | 日夹 / 01 / 02 / 03 | 报告 fatal/warn、Receipt 完整性、一原子合规性 |
| `rma_route.py` | 单场复盘路由 | 赛果 + 公开篮 | RMA 分类 + 子标签 |
| `replay_rma_stats.py` | 批量 RMA 统计 | `03-复盘` 目录 | 方向率 / 比分率 / RMA 分布 |
| `receipt_fingerprint.py` | 指纹记录与 shadow 检查 | fingerprint_db | shadow 警告 / live TOP2 禁令 |
| `fingerprint_heatmap.py` | 误信热力图 | fingerprint_db | 各 clause/intel_shape 命中率 |
| `threshold_optimizer.py` | Edge 阈值回测 | edge_history.csv | 推荐阈值 + 置信区间 |
| `sync-skill-bundle.sh` | skill 修改后同步 | V18 文档 | 更新 SKILL.md 与索引 |

---

### 2.9 文档架构：拆分为 4 本可独立维护的手册

把当前单文件 skill 拆成：

1. **`V18-core.md`**：核心纪律（总原则、软清单、纪律、禁止/必出清单）。
2. **`V18-output.md`**：输出模板与 01/02/03 格式规范。
3. **`V18-tools.md`**：脚本说明、lint 规则、阈值配置、无脚本降级。
4. **`V18-changelog.md`**：版本变更、误信案例、规则热力记录。

`SKILL.md` 作为主入口，只放最高原则、文件索引、作业流概览，不再堆砌全部细节。

---

### 2.10 迁移路径：从 V17.4.22.2 到 V18

#### 迁移检查清单

- [ ] 备份当前 `球赛预测框架.txt` 和 `scripts/`。
- [ ] 创建 `docs/V18/` 并写入 4 本手册。
- [ ] 把 `data/miss_fingerprint_ledger.jsonl` 按新 schema 迁移到 `data/fingerprint_db.jsonl`。
- [ ] 创建 `config/thresholds.yaml` 并以当前阈值作为初始实验值。
- [ ] 跑 10 场 V18-lite 试运行，记录 lint 通过率和 RMA 填写率。
- [ ] 对比 V17 与 V18-lite 同期的方向率 / 比分率 / 公开命中率（三本账同屏）。
- [ ] V18-lite 跑满 50 场且 lint 通过率 ≥95% 后，升级 `SKILL.md` 为 V18 正式版。
- [ ] 冻结 V17 补丁，旧版本号仅保留在 `V18-changelog.md`。

---

## 三、验收标准与关键指标

| 指标 | 当前目标 | 长期目标 |
|------|---------|---------|
| `lint_draft.py` 通过率 | ≥95% | ≥98% |
| 复盘 RMA 路由填写率 | 100% | 100% |
| Receipt 字段完整率 | 100% | 100% |
| 单场 miss 触发规则升级的比例 | ≤5% | ≤2% |
| 02 空槽/空钉场占比 | 诚实反映 | 不人为压低 |
| 方向准确率（对外分母） | 基线 +5% | 持续改进 |
| 比分命中率（01 篮） | 基线 +3% | 持续改进 |
| 三本账展示完整率 | 100% | 100% |

---

## 四、一句话总结

> **把 V17 从“条文越来越多的专家戒律”改成“有工具支撑、有数据闭环、有版本节奏的可迭代系统”。准确率不靠加闸，而靠诚实、归因、执行。**
