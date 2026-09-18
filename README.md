# FootballPredictions · 2足球框架 V17.4.36

体彩/竞彩足球预测框架 + 可分发 Agent Skill。  
**当前执行版 = V17.4.36**（`SKILL.md` / `output-template.md` / `references/03-复盘模板.md`）。

主菜：伤停/战意/形态/剧本定方向。佐料：盘口/SP/Edge 只做出票闸。  
方向必须给（锁\* / 主不败 / 客不败）；禁胶着；`01` 场场 `排除=`｜`剩余=`｜`二次=`。  
**V17.4.36**：胜平负未开售 / 只开让球场 → 出票只映射让球；二串一 A/B 分区。

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
│   └── lint_draft.py
└── skills/football-predict-v17/
    ├── SKILL.md
    ├── output-template.md
    └── references/          ← sync 生成的精简副本
```

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
