---
name: football-predict-v17
description: >-
  Executes AQQ 2足球框架 V17.4.2 football match predictions (体彩 default unless
  北单). Forces web search evidence checklist, λ→λ′ Poisson Edge_eff gates,
  出票/星级, and result prediction even when 不荐. Use when user pastes 竞彩
  fixtures/odds, asks 球赛预测/框架预测/出票, or analyzes 挪超/芬超/瑞超/英超/
  西甲/德甲/意甲/法甲/世界杯 matches.
---

# 2足球框架 V17.4.2 · 可分发执行器

## 根路径 ROOT（便携，禁止写死本机用户目录）

按顺序解析，命中即用：

1. 本 skill 目录下的 `references/`（`npx skills add` / 克隆后的标准布局）
2. 若在完整仓库内开发：仓库根目录（与 `球赛预测框架.txt` 同级）
3. 环境变量 `AQQ_FOOTBALL_ROOT`（可选覆盖）

```text
SKILL_DIR = 本 SKILL.md 所在目录
ROOT = SKILL_DIR/references   若存在 球赛预测框架.txt
     否则 = 仓库根（含 球赛预测框架.txt 的目录）
```

用 Read 工具打开 `$ROOT/...` 文件；**禁止**读取任何 `原足球框架`。

冲突优先级：本 skill > `$ROOT/球赛预测框架.txt` > `$ROOT/投注分析专家_人设提示词.txt` > 插件。

## Step 0 · 开场必读（按联赛只读需要的）

| 优先级 | 文件（相对 ROOT） |
|--------|-------------------|
| 每次 | `外部模型启动卡.txt` |
| 每次 | `球赛预测框架.txt`（`[FORCE_SEARCH]` `[ANTI_FALSE_EDGE]` `[NO_ACTION]`） |
| 每次 | `p_model手算.txt` |
| 每次 | `投注分析专家_人设提示词.txt` |
| 挪/芬/瑞等 | `小联赛数据.txt` |
| 英西德意法 | `五大联赛分析.txt` |
| 世界杯等 | `世界杯.txt` |
| 纠偏 | `初始框架.txt` · `完整样例_体彩默认.txt` |

外发千问可用 `一键投喂_全量合并.txt`；Cursor 预测优先分文件 Read。

## Step 1 · 强制搜索（无清单 = 废稿）

有 WebSearch / 浏览器 → **必须先搜再写 λ**。禁止凭记忆编积分/伤停/主客场均。

```text
【取证清单】
| 槽位 | 优先源 | HIT/UNKNOWN | SOURCE_URL或SEARCH_Q | 摘要 |
| 积分榜 | Soccerway/FotMob/联赛官网 | | | |
| 主客GF/GA或近5 | SoccerSTATS/SofaScore/FotMob | | | |
| 伤停 | Transfermarkt/FotMob | | | |
| xG/npxG | Understat 或 NO_NPXG | | | |
| SP | 用户粘贴或 sporttery.cn | | | |
关键槽有源数=_/3（须≥2才允许可介入）
```

关键槽有源 <2 → 出票不荐，原因=`取证不足(FORCE_SEARCH)`。

## Step 2 · 口径与方向

1. 有 Understat → `npxG`；否则 `RAW_GOALS` / `NO_NPXG`  
2. **先**定方向（主胜|客胜|平局|胶着），禁止先编胜率  
3. 挪超 = **Tier 3**

## Step 3 · p_model / Edge

RAW：`λ'=0.65λ+0.35·LG_HALF` → 泊松 0～5 → `p_model`。  
SP：用户 > sporttery（北单 bjlot）。乘法去水 → `Edge_raw` → `Edge_eff`。

| 口径 | Edge_eff | 可介入 |
|------|----------|--------|
| npxG | = Edge_raw | ≥5% |
| RAW | ×0.60（小样本×0.85） | ≥8% |

`Edge_raw≥12%` 且对打热门 → 须 ≥2 条非λ证据，否则 `FALSE_EDGE_MKT_CONFLICT`。  
禁止弃单后改推大球/半全场/亚盘当主推。

## Step 4 · 结果与出票

方向 → 净胜档（BLOWOUT）→ 主/次/防 → 区间。  
不荐也必须【结果预测】；星级☆☆☆☆☆；未要求娱乐仓则不要建议购买。

## 必出块（缺一废稿）

```text
【取证清单】…
【硬闸自检】层级｜口径｜取证｜λ→λ′｜SP｜p_fair｜方向｜p_model｜Edge_raw｜Edge_eff
【结果预测】【出票】【投注星级】弃单原因=
```

## 多场 / 频道

一场一条；同轮 Tier3 同构客胜小胜可介入最多 1 场。未写北单 → 体彩默认。

## 安装后自检

确认 `$ROOT/球赛预测框架.txt` 可读；确认含 `V17.4.2` 与 `[FORCE_SEARCH]`。

模板：[output-template.md](output-template.md) · 规则全文在 `references/`。
