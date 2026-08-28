# 裁决 · F-A 生产方读数接线（`cbaaeb9`）· orchestrator 判

- **日期**：2026-08-29 · **施工**：GLM 执行档 · **裁决方**：orchestrator（Claude 主控，⛔ 非作者）
- **裁决**：**APPROVE**（0 阻断）

## 一、我独立复现的（⛔ 不照收自述）

| | 读数 |
|---|---|
| 范围 | `denominator.py` 79/3 + 新测试 241/0 = **2 文件**；⭐ **与并行 Claude 席位零文件重叠**（逐个比对确认）|
| **权威全量** | **`3195 passed / 13 xfailed / 0 failed`** · `PYTEST_EXIT=0` · 949.56s · `-n 6` · ⛔ 无 `-m` |
| `.pth` 前后 | `58f547fa…` 同值 · **HEAD 跑前跑后同为 `2757cb6`** ⇒ ⛔ 不是「跑测途中被改」那种假读数 |
| 算术 | **3167 + 28 = 3195**（`--collect-only` 实读两新文件共 28） |

**接线效果（我自己跑的）**：

| | gates | S4 闭合 | BLOCK 诊断 |
|---|---|---|---|
| 签字件 F1 / F2 | `G1✓ G2✓ G3✓ G5✓` | `dangles 0 / cuts 0 / invalid 0` | **0** |
| 原图（重签）F1 | ⛔ **`G1✗` `G5✗`** | ⛔ **`dangles 4`** | ⛔ **3** |

⇒ **不是恒真式**：反例真的报失败。
**退化线定位**：`handles ["13DC"]` + `points [[-19349.0, 33973.6]]` + `locatable true`
⭐ **正是 orchestrator 此前只能手扫 DXF 才找到的那条** —— 那次手扫现在不需要了。

## 二、它更正我题面的一处（**更精确，且更诚实**）

我写「`tarch_wall_degenerate_line` 的 `context` 是空的 `{}`」——属实，**但病灶更精确**：
转换器把定位放在 `source_entity_handles` / `source_points_dxf_mm`（schema 自己的 BLOCK-localizable 校验用的正是这对），
是 `_diagnostic_records` **恰好只透 `context`** 才丢的。
⇒ 修法 = **补透那对字段 + `locatable` 显式标记**，⭐ **没有伪造任何定位** —— 与我「⛔ 不许伪造定位信息」的要求一致。

## 三、我认可它的三条判断

1. **第 3 条无需停下上报**：`dangles`/`cuts` 本来就在 `P1PlanViewGeometry` 上（int 计数），没碰 `tarch_normalize.py` ✓
2. ⚠️ **只有计数、没有残差几何** —— 「能给几何就给几何」那半给不出，dangle 的定位点经 `tarch_wall_free_end`（带 point）出去。
   ⇒ **接受现状**；要成批出残差几何得改转换器（触发重签），归 B4-②b。
3. **超出一行**：`DenominatorUnavailable` 也带 `gates`。⭐ **不撤** —— 依据是 F-126 的异常契约
   「empty run 知道的一切都要带出来」，方向一致。

## 四、⭐ 它自己点名的陷阱验证（我最看重的一格）

派工单埋的提醒：「gates 透出来之后，『全 pass』在签字件上是**恒真的** ⇒ 那不是锁，是恒真式。」
它的 **M-gates-lie 变异**（把 `passed` 恒置 True）实测：L6/L6b/L8 红，⭐ **L5 仍绿**
⇒ **实测证实了「签字件上全 pass 确是恒真方向」**，而反例夹具（重签名 as-received，`G1✗ G5✗`）咬得住说谎的读数。
⇒ [[gate-with-only-negative-assertions-is-unobservable]] 这条，本次是**被显式验过**的，不是靠自觉。
