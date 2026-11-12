# FootballPredictions · 足球预测框架 V18

体彩/竞彩足球预测框架 + 可分发 Agent Skill。**当前执行版 = V18 概率校准版**，细则以 `SKILL.md` 为准。

- 候选分诊、多源取证、01a 过程稿、赛前冻结与证据/票面审计保留。
- 同一动态尾部截断比分矩阵派生胜平负、让球、总进球与精确比分。
- 实际 SP 使用 `p_be=1/SP`、`EV=p_model×SP-1`；去水概率只作市场基准。
- 每个选项同时记录模型与保守概率，核心数据足够且整票保守 EV>0 才出票。
- V15.6、固定 RAW 折扣、固定翻倍、主客/让平/腿序硬闸退出新稿概率与票面决策。
- 研究方向与出票分轨；比分和总球缺乏可靠分布时可未估/弃权。
- 复盘以 Log Loss、Brier、校准曲线和 walk-forward 时间外验证为主，不用短期 ROI 冒充校准。

历史版本及旧规则来由保留在 `references/版本史.md`，不再作为当前执行口径。

**完整用法（装完配合什么）→ [使用.md](./使用.md)** · 作业细则 → [SKILL.md](./SKILL.md) · 取证 URL → [references/取证速查.md](./references/取证速查.md)

仓库：https://github.com/yuansql/FootballPredictions

---

## 别人怎么用

### 方式 A · Skills CLI（推荐）

```bash
npx skills add yuansql/FootballPredictions --skill football-predict-v17
```

装完读 skill 包内 **`使用.md`**：「下载后配合什么用」（日夹 + 直接请求 + ego + lint）。

### 方式 B · Git 克隆

```bash
git clone https://github.com/yuansql/FootballPredictions.git
cd FootballPredictions
bash scripts/sync-skill-bundle.sh
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
├── 使用.md                 ← 安装/配套说明（sync 进 skill）
├── README.md
├── SKILL.md
├── output-template.md
├── 防偷懒.md
├── SYNC_STAMP.txt
├── references/
├── rules/
├── scripts/
│   ├── sync-skill-bundle.sh
│   └── lint_draft.py
└── skills/football-predict-v17/
    ├── SKILL.md
    ├── 使用.md
    ├── output-template.md
    ├── references/
    └── scripts/
```

---

## 维护者

改 `SKILL.md` / `output-template.md` / `使用.md` / `references/` / `rules/` 后必须：

```bash
bash scripts/sync-skill-bundle.sh
python3 scripts/lint_draft.py <日夹>/01-竞彩分析.md
```

`README.md` 只留仓库根；`使用.md` **会**随 sync 进 skill 包（改版本号时两份文首都要手改）。

---

## 免责声明

仅供研究与学习；不构成投注建议；足球结果存在不确定性。
