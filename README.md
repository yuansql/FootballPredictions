# FootballPredictions · 2足球框架 V17.4.87

体彩/竞彩足球预测框架 + 可分发 Agent Skill。  
**当前执行版 = V17.4.87**（细则以 `SKILL.md` 为准）。  
**V17.4.87**：账本单关放行（每晚≤1张、SP≥2.0、我估≥40%、≤4元、稳不放行；免 CAUTION 复式）。  
**V17.4.86**：票面候选认真拆必开捷报教练分析/裁判分析/捷报猫（01a【三页取证】；猫页 AI 生成只摘事实）；风格判断不加闸。  
**V17.4.85**：每张票每条命中路返还 ≥2 倍本金；CAUTION 场进票须复式罩冷门点名结果。  
**V17.4.84**：每天资金默认 12 元（形态自配，复式可）；每张票最少二串一（禁单关，串数不封顶）；稳/博/大博玩法不限；稳只须命中返还>本金。  
**V17.4.83**：【市场漏】降为只记账——选场回准确率，没边不挡票；我估开赛前写死；30 场复查。  
**V17.4.82**：票面候选须写【市场漏】（隐含/我估/漏）。  
**V17.4.81**：没边就空仓（非空仓须 `账本=过`）；押客腿禁共同胆；排主胜须 `主场=挡得住`。  
**V17.4.80**：低结构场最多进 1 张票（禁当共同胆）；认真拆硬排须【强弱对位】且打得到=否。  
**V17.4.79**：票面**稳腿硬闸**——CAUTION/弱置信禁稳；客热锁客/客胜/让负禁进稳第二腿；让负进稳须净胜≥2。  
**V17.4.78**：取证**接口优先**——`analysisJs`+`detail` 直接请求落盘；**ego** 补列表 SPF 与教练/裁判/猫；REA 兜底。  
**V17.4.77**：锁\*/深让可锁/屠杀档→比分篮须含净胜≥3；票面默认少买精确比分。  
**V17.4.76**：博/稳过关腿默认跨场；稳让胜(主-N)须主推净胜≥N+1。  
**V17.4.75**：认真拆可采教练/裁判/捷报猫（禁页内荐单焊锁\*）。  
**V17.4.74**：取证全捷报；体彩官网与雷速不再必采；默认不写单关。  
**V17.4.72–71**：候选 `01a`；先选【票面候选】≤3；默认票面 16 元 8+4+2+2。

主菜：伤停/战意/形态/剧本定方向。佐料：盘口/SP/Edge 只做出票闸。  
方向必须给（锁\* / 主不败 / 客不败）；禁胶着；`01` 场场 `排除=`｜`剩余=`｜`二次=`。

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
