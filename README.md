# FootballPredictions · 足球预测框架

体彩/竞彩足球预测框架 + 可分发 Agent Skill。**当前执行版 = 分析优先版**，细则以 `SKILL.md` 为准。

- 默认研究 5 场，主要精力用于核心情报、攻防对位、比赛剧本与反证。
- 同一动态尾部截断比分矩阵派生胜平负、让球、总进球与精确比分。
- 实际 SP 使用 `p_be=1/SP`、`EV=p_model×SP-1`；保守概率由 λ 区间角点脚本导出。
- 核心数据足够且整票保守 EV>0 才出票；研究 5 场不等于必须买 5 场，可以空仓。
- 不再要求 01a、全套原文落盘、证据/票面/冻结 JSON、赛前审计和研究榜单。
- 复盘与校准为独立任务，不占用当场分析时间；短期 ROI 不代表概率准确。

完整用法 → [使用.md](./使用.md) · 作业细则 → [SKILL.md](./SKILL.md) · 输出格式 → [output-template.md](./output-template.md)

仓库：https://github.com/yuansql/FootballPredictions

## 安装

```bash
# Skills CLI
npx skills add yuansql/FootballPredictions --skill football-predict-v17

# 或 Git 克隆
git clone https://github.com/yuansql/FootballPredictions.git
cd FootballPredictions
bash scripts/sync-skill-bundle.sh

# 或 OpenSkills
openskills install yuansql/FootballPredictions
```

外部模型分贴时只贴 `SKILL.md` 与 `output-template.md`；需要概率公式时再贴 `references/p_model手算.txt`。

## 维护

修改框架文件后同步仓内 skill 包：

```bash
bash scripts/sync-skill-bundle.sh --no-local
```

需要同时更新本机 Cursor/Agents 时去掉 `--no-local`。`README.md` 只留仓库根，其余执行文件由同步脚本复制进 `skills/football-predict-v17/`。

历史规则与旧脚本仅作资料保留，不属于当前交卷流程。

## 免责声明

仅供研究与学习；不构成投注建议；足球结果存在不确定性。
