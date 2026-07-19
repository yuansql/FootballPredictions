# FootballPredictions · 2足球框架 V17.4.5

体彩/竞彩足球预测框架 + 可分发 Agent Skill。

**完整用法（含 `sync-skill-bundle.sh` 说明）→ [使用.md](./使用.md)**

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

- Cursor：克隆后用 `@` 引用 `skills/football-predict-v17`，或自行复制到 `~/.cursor/skills`（可选，非必须）
- 项目内分发入口：`skills/football-predict-v17/`（框架在 `references/`）

复制到个人 Cursor skills（可选；作者本机默认不装）：

```bash
mkdir -p ~/.cursor/skills/football-predict-v17
cp -R skills/football-predict-v17/SKILL.md skills/football-predict-v17/output-template.md ~/.cursor/skills/football-predict-v17/
# 框架在 references/，保持与 SKILL 同级目录结构：
cp -R skills/football-predict-v17/references ~/.cursor/skills/football-predict-v17/
```

卸载本机 Cursor skill：

```bash
rm -rf ~/.cursor/skills/football-predict-v17
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
├── 使用.md                            ← 完整使用说明
├── README.md
├── scripts/
│   └── sync-skill-bundle.sh           ← 源文件同步到 references
├── skills/
│   └── football-predict-v17/
│       ├── SKILL.md
│       ├── output-template.md
│       └── references/                ← 框架副本（供别人安装）
└── *.txt                              ← 开发用源文件
```

---

## 维护者（你）

改根目录分文件后：

```bash
python3 rebuild_一键投喂.py
bash scripts/sync-skill-bundle.sh   # 只同步 skills/.../references，不装本机
# 若要临时装本机：bash scripts/sync-skill-bundle.sh --local-cursor
git add -A && git commit -m "…" && git push
```

---

## 免责声明

仅供研究与学习；不构成投注建议；足球结果存在不确定性。
