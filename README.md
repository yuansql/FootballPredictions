# FootballPredictions · 2足球框架 V17.4.2

体彩/竞彩足球预测框架 + Cursor / Agent Skill。支持强制取证、RAW 假 Edge 闸、出票星级。

仓库：https://github.com/yuansql/FootballPredictions

---

## 别人怎么用（拉取）

### 方式 A · Skills CLI（推荐）

```bash
npx skills add yuansql/FootballPredictions --skill football-predict-v17
```

全局安装：

```bash
npx skills add yuansql/FootballPredictions --skill football-predict-v17 -g
```

安装后 skill 在 `.agents/skills/football-predict-v17/`（或全局目录）。  
框架正文在 skill 内 **`references/`**，Agent 按 `SKILL.md` 解析 `ROOT`。

### 方式 B · Git 克隆整仓

```bash
git clone https://github.com/yuansql/FootballPredictions.git
cd FootballPredictions
```

- Cursor：打开该文件夹为工作区，或 `@football-predict-v17`
- 项目内已有：`skills/football-predict-v17/` 与 `.cursor/skills/football-predict-v17/`

复制到个人 Cursor skills：

```bash
mkdir -p ~/.cursor/skills/football-predict-v17
cp -R skills/football-predict-v17/* ~/.cursor/skills/football-predict-v17/
```

### 方式 C · 只给千问 / DeepSeek

下载或复制 `skills/football-predict-v17/references/一键投喂_全量合并.txt`  
（或仓库根目录同名文件）上传为知识库，按文件内「激活句」使用。

### 方式 D · OpenSkills

```bash
openskills install yuansql/FootballPredictions
```

---

## 目录结构

```text
FootballPredictions/
├── README.md
├── skills/
│   └── football-predict-v17/          ← npx skills 发现入口
│       ├── SKILL.md
│       ├── output-template.md
│       └── references/                ← 框架全文（便携 ROOT）
│           ├── 球赛预测框架.txt
│           ├── 外部模型启动卡.txt
│           ├── …
│           └── 一键投喂_全量合并.txt
├── .cursor/skills/football-predict-v17/  ← Cursor 项目 skill
└── *.txt                              ← 开发用源文件（与 references 同步）
```

---

## 维护者（你）

改根目录分文件后：

```bash
python3 rebuild_一键投喂.py
./scripts/sync-skill-bundle.sh   # 同步到 skills/.../references 与 .cursor/skills
git add -A && git commit -m "…" && git push
```

---

## 免责声明

仅供研究与学习；不构成投注建议；足球结果存在不确定性。
