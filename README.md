# FootballPredictions · 2足球框架 V17.4.43

体彩/竞彩足球预测框架 + 可分发 Agent Skill。  
**当前执行版 = V17.4.43**（`SKILL.md` / `output-template.md` / `references/03-复盘模板.md`）。

主菜：伤停/战意/形态/剧本定方向。佐料：盘口/SP/Edge 只做出票闸。  
方向必须给（锁\* / 主不败 / 客不败）；禁胶着；`01` 场场 `排除=`｜`剩余=`｜`二次=`。  
**V17.4.43**：票面 8|12；一张二串一或两张稳+博；半全场可组合；比分/半全场可单场。  
**V17.4.42**：票面/研究二串一可跨 **胜平负×进球数×比分×让球**；点名最少二串一→方案≥二串；预算听用户。  
**V17.4.41**：【今日票面】主交卷；票面席=可买腿；复盘主 KPI=票中。  
**V17.4.38**：【让球稳健推荐】——让球盘稳则可荐（单场或让球 B 串）。

**完整用法 → [使用.md](./使用.md)** · 作业细则 → [SKILL.md](./SKILL.md)

仓库：https://github.com/yuansql/FootballPredictions

---

## 别人怎么用

### 方式 A · Skills CLI（推荐）

```bash
npx skills add yuansql/FootballPredictions --skill football-predict-v17
```

### 方式 B · Git 克隆

```bash
git clone https://github.com/yuansql/FootballPredictions.git
cd FootballPredictions
```

### 方式 C · 千问 / DeepSeek（精简分贴）

按联赛粘贴：`外部模型启动卡` + `球赛预测框架` + **一个**插件（小联赛/五大/世界杯）+ `p_model手算` + `投注分析专家`。  
**不要**再找「一键投喂全量合并」（已废除）。

### 方式 D · OpenSkills

```bash
openskills install yuansql/FootballPredictions
```

---

## 目录结构

```text
FootballPredictions/
├── 使用.md
├── README.md
├── SKILL.md                 ← 执行器正文（与 skills/ 同文）
├── output-template.md
├── SYNC_STAMP.txt
├── references/              ← 8 个框架正文 + 03-复盘模板
├── rules/                   ← V15.6 补丁
├── scripts/
│   ├── sync-skill-bundle.sh
│   ├── lint_draft.py
│   ├── structure_gate.py
│   ├── deep_away_trap.py
│   └── gen_rma_detail_table.py
└── skills/football-predict-v17/
    ├── SKILL.md
    ├── output-template.md
    └── references/          ← sync 生成的精简副本
```

已删：`archive/`、回测文档/空 drafts、离线回测脚本、ICS/红旗独立 CLI（规则留在 SKILL，稿内自评 + lint 兜底）。
---

## 维护者

改 `SKILL.md` / `output-template.md` / `references/*.txt` / `rules/` 后必须：

```bash
bash scripts/sync-skill-bundle.sh
python3 scripts/lint_draft.py <日夹|01|03> --warn-only
```

`README.md` 与 `使用.md` **不在** sync 脚本里，改版本号时要手改这两份。

---

## 免责声明

仅供研究与学习；不构成投注建议；足球结果存在不确定性。
