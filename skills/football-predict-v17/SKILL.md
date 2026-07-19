---
name: football-predict-v17
description: >-
  Executes AQQ 2足球框架 V17.4.5 football predictions (体彩 default unless 北单).
  FORCE_SEARCH evidence, λ→λ′ Poisson, dual Edge gates (1X2≥1%, 让球/进球≥3%),
  and DIM_REDUCTION when 1X2 fails. Use for 竞彩 fixtures, odds, 球赛预测,
  挪超/芬超/瑞超/英超/世界杯 analysis.
---

# 2足球框架 V17.4.5 · 可分发执行器（双闸门 · 降维）

## ROOT（便携）

1. `SKILL_DIR/references/`（若有 `球赛预测框架.txt`）  
2. 否则仓库根目录  
3. 或环境变量 `AQQ_FOOTBALL_ROOT`  

禁止 `原足球框架`。冲突：本 skill > 主控 > 人设 > 插件。

## 必读

| 每次 | `外部模型启动卡.txt` · `球赛预测框架.txt`（`[DIM_REDUCTION]`）· `p_model手算.txt`（§5b）· `投注分析专家_人设提示词.txt` |
|------|------|
| Tier3 | `小联赛数据.txt` |
| 五大 | `五大联赛分析.txt` |
| 杯赛 | `世界杯.txt` |

## 双闸门（V17.4.5）

| 通道 | Edge_eff 闸门 | 实战含义 |
|------|---------------|----------|
| 胜平负 | **≥ 1%** | 击穿体彩抽水后的稳胆/串关素材 |
| 让球 / 进球数 | **≥ 3%** | 子盘方差大；≥**5%** 宜标「高赔单关主推」 |

## 作业流

1. WebSearch → 【取证清单】（关键槽≥2 才可介入）  
2. 定方向 → λ（RAW→λ′）→ 泊松 0～5 比分表  
3. **胜平负** Edge_eff；≥**1%** → 出票通道=胜平负  
4. **若 Edge_eff_1X2 < 1%** 且未硬弃单 → **必须降维**：  
   - A 让球三项（§5b）→ Edge≥**3%** 则通道=让球（星级≤★★★☆☆；≥5% 可标单关高推）  
   - B 仍不足 → 总进球/大小（须 SP，闸同 ≥3%）  
   - 都失败 → 不荐，仍给【结果预测】  
5. 硬弃单（取证不足/证据打架/MKT_CONFLICT/无λ）→ 不降维，直接不荐  

## 禁止

- 胜平负无 Edge 就全弃且**不跑降维**  
- 无让球/进球 SP 却口头推大球当出票  
- 降维方向与结果预测打架  
- 用统一 3% 闸门卡住本已 ≥1% 的胜平负稳胆  

## 必出

【取证清单】【硬闸自检】含出票通道+【降维】行【结果预测】【出票】【投注星级】

详见 [output-template.md](output-template.md)。
