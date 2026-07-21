---
name: football-predict-v17
description: >-
  Executes AQQ 2足球框架 V17.4.6 football predictions (体彩 default unless 北单).
  FORCE_SEARCH evidence, λ→λ′ Poisson, V15.6 patches (Kryptonite/Zombie/Jinx/
  Edge_Refine/StarFactor), dual Edge gates (1X2≥1%, 让球/进球≥3%), and
  DIM_REDUCTION when 1X2 fails. Use for 竞彩 fixtures, odds, 球赛预测,
  挪超/芬超/瑞超/英超/世界杯 analysis.
---

# 2足球框架 V17.4.6 · 可分发执行器（双闸门 · 降维 · V15.6补丁）

## ROOT（便携）

1. `SKILL_DIR/references/`（若有 `球赛预测框架.txt`）  
2. 否则仓库根目录  
3. 或环境变量 `AQQ_FOOTBALL_ROOT`  

禁止 `原足球框架`。冲突：本 skill > 主控 > 人设 > 插件。

## 必读

| 每次 | `外部模型启动卡.txt` · `球赛预测框架.txt`（`[DIM_REDUCTION]`·`[V15.6_PATCHES]`）· `p_model手算.txt`（§5b·§5c）· `投注分析专家_人设提示词.txt` |
|------|------|
| 补丁 | `rules/V15.6_patches.txt`（规范）· 可执行 `rules/V15.6_patches.py` |
| Tier3 | `小联赛数据.txt` |
| 五大 | `五大联赛分析.txt` |
| 杯赛 | `世界杯.txt` |

## 双闸门（V17.4.5 起）

| 通道 | Edge_eff 闸门 | 实战含义 |
|------|---------------|----------|
| 胜平负 | **≥ 1%** | 击穿体彩抽水后的稳胆/串关素材 |
| 让球 / 进球数 | **≥ 3%** | 子盘方差大；≥**5%** 宜标「高赔单关主推」 |

## V15.6 五补丁（永久 · 每场必扫）

| 补丁 | 触发 | 动作 |
|------|------|------|
| **StarFactor** | 客队传统三强 + 后防伤≥2 + 中前场全勤 + 客胜赔≤1.50 | λ_A×1.15、λ_H×1.10；**仅子盘** |
| **Kryptonite** | 客队近10交锋≥8胜 | P_A 偏移后归一化（Edge 前） |
| **Jinx** | 主场近5交锋≥3平 | P_D 6:4 平滑；若最高→平局首选+0-0/1-1 |
| **Zombie** | 主队垫底2 + 胜≤1 + 受让≥1 | 让球 Edge×0.60×0.65 + 深盘陷阱预警 |
| **Edge_Refine** | 主盘 Edge_eff≤-5% | 冷门扫描；≥3%→高赔首选并覆盖比分 |

**Pipeline：** 取证 → StarFactor → 泊松 → Kryptonite/Jinx → Edge → Zombie → Edge_Refine → 出票

## 作业流

1. WebSearch → 【取证清单】（关键槽≥2 才可介入；含 H2H/排名胜场）  
2. 定方向 → λ（RAW→λ′）→ **StarFactor(子盘)** → 泊松 0～5 比分表 → **Kryptonite/Jinx**  
3. **胜平负** Edge_eff → **Zombie(让球)** → **Edge_Refine**；≥**1%** → 出票通道=胜平负  
4. **若 Edge_eff_1X2 < 1%** 且未硬弃单 → **必须降维**：  
   - A 让球三项（§5b）→ Edge≥**3%** 则通道=让球（星级≤★★★☆☆；≥5% 可标单关高推）  
   - B 仍不足 → 总进球/大小（须 SP，闸同 ≥3%）  
   - 都失败 → 不荐，仍给【结果预测】  
5. 硬弃单（取证不足/证据打架/MKT_CONFLICT/无λ）→ 不降维，直接不荐  

## 禁止

- 胜平负无 Edge 就全弃且**不跑降维**  
- 主盘 Edge≤-5% **不跑 Edge_Refine** 仍推热门  
- 命中 Zombie 却不写「⚠️ 深盘陷阱预警」  
- 无让球/进球 SP 却口头推大球当出票  
- 降维方向与结果预测打架  
- 用统一 3% 闸门卡住本已 ≥1% 的胜平负稳胆  

## 必出

【取证清单】【硬闸自检】含出票通道+【降维】+【V15.6补丁】【结果预测】【出票】【投注星级】

详见 [output-template.md](output-template.md)。
