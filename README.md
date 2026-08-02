# FootballPredictions · 2足球框架 V17.4.9

体彩/竞彩足球预测框架 + 可分发 Agent Skill。  
**V17.4.9**：**INTEL_FIRST 精简包** + **双轨推荐**（研究五星必含胜平负/进球数/比分；出票可空仓）+ 双闸门 + 降维 + **V15.6 五补丁**。  
已移除一键全量合并 / 说明书 / 初始框架，减少 Agent 噪音。

**完整用法 → [使用.md](./使用.md)**

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
├── rules/                 ← V15.6 补丁
├── scripts/
│   ├── sync-skill-bundle.sh
│   └── verify_intel_first.py
├── skills/football-predict-v17/
│   ├── SKILL.md
│   ├── output-template.md
│   └── references/        ← 精简框架副本
└── *.txt                  ← 源规则（8 个正文）
```

---

## 维护者

```bash
bash scripts/sync-skill-bundle.sh
python3 scripts/verify_intel_first.py
# 需要本机 Cursor 时：bash scripts/sync-skill-bundle.sh --local-cursor
```

---

## 免责声明

仅供研究与学习；不构成投注建议；足球结果存在不确定性。
