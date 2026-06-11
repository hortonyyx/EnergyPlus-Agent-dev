# 0–5 管线各环节 capability 升级建议（活文档）

> **定位**：记录 0–5 管线**六个子环节**各自的 capability（能力/质量）升级建议，供后续依次升级。**不是硬伤清单**——硬伤走 [review/request/2026-06-10_pipeline_0-5_full_audit_request.md](../logs/review/request/2026-06-10_pipeline_0-5_full_audit_request.md) → review 闭环。
>
> **状态（2026-06-10）**：骨架 + 当前已知建议（Opus 起草）。明天 Fable 5 做完整体检时，顺手发现的 capability 想法往这里加。**这些升级先不实施**，按用户路线（§ 路线图）在 test_baseline + 国产 VLM 接通后，**依次提升建筑复杂度时**再逐项落地。
>
> 权威接线见 [pipeline_stage_contracts.md](pipeline_stage_contracts.md)。术语：识图=0_reading / 校正=1_correction / 建模=2_modelling / 切配=3_split_pairing / 物理=4_mep / 装配=5_intakeoutput。

---

## 0_reading（识图）

- **跨画法/风格泛化**：识图库（`reading_guide.md`）扩充——墙的多种画法、家具/铺装/楼梯/轴网符号长相，提升对杂乱真实图的 keep-set 分类与杂物排除（plan.md B1.5.b / B7）。
- **全自动 VLM**：`llm.yaml:intake_reading` 段预留未接；pivot 后接国产 VLM API（见路线图）。
- **尺寸链自洽校验**：识图阶段对 dimension chain 做和校验（子链 vs 总链），不自洽时标 `null` + note，而非硬填（sm23 已暴露内部子链 ~100–200mm 偏差）。

## 1_correction（校正，LLM）

- **稳定性**（2026-06-10 已加重试 + 窗自检兜底，commit `fd3d4bf`）：进一步可加——结构化输出约束 / 更细的自检（区数 vs testdata、楼层 z-stack 连续性、外包闭合）。
- **多层 z-stack 合成**：2 层已验证，**3 层（sm20）2026-06-11 audit 实证通过**（0/3.6/7.2 连续、各层窗 z 落位正确、一发即中）；facade_local→world 的逐层 z 偏移仍是易错点（z 连续性确定性守卫属硬伤修复，见 [audit review H2](../logs/review/review/2026-06-11_pipeline_0-5_full_audit_review.md)）。
- **仲裁/先验丰富度**：A3 仲裁 + A4 几何先验目前偏薄，复杂图（凹形/退台）下需要更强的常识仲裁。

## 2_modelling（建模·几何，确定性）

- **非矩形 footprint**：当前矩形 cell；L/U 形、凹凸异型需 cell 多边形 + straight-skeleton（plan.md B5，[geometry_first_zonification.md](geometry_first_zonification.md)）。
- **zonification 粒度**：sm23 暴露——走廊被横墙切成多段、房间粗合并。怎么定 zone 边界（贴房间 vs 贴热区）是 capability 主线（[recognition_modeling_capability.md](../capability/recognition_modeling_capability.md)）。

## 3_split_pairing（切配·仿真，确定性）

- **覆盖完整性**：InterZone 门的覆盖洞盲区（两侧都标 Outdoors 的"内部边界"）——长期解走 shapely（plan.md B1.5.g 残留、B5）。
- **非矩形切配**：跨层不同 footprint 的面切分（退台/挑空，plan.md B6）。

## 4_mep（物理撰写，LLM）

- **schedule 完整性**（2026-06-10 已加确定性门 + authoring 硬化，commit `04e7dbe`）：先验库 `mep.md` 目前是 office 单一种子；扩成多建筑类型（学校/商业/住宅）的 MEP 先验库。
- **构造/材料真实性**：当前占位构造（Default_*）；接真实构造库 + 按气候区选型。
- **材料质量跨 draw 波动**（2026-06-11 audit 顺手发现）：同一 prompt 下 sm21 某次 draw 全配 no-mass 材料 → EP "building has no thermal mass" warning，sm20 同期正常。可在 authoring.md 加"外墙/楼板至少一层有质量材料"硬规则，或入契约校验。
- **数值合理性**（2026-06-11 audit 顺手发现）：sm20 的 OFFICE_ACTIVITY 活动量 schedule 数值超出 70–1000 W/person 典型区间（19 条 EP warning）；可在 mep.md 先验里给典型值表。
- **仿真控制默认值**（2026-06-11 audit 顺手发现）：4_mep 不产 design days 但 SimulationControl 默认要求 design-day 仿真（EP warning）；地温缺省走 EP 默认 18 °C。可补 authoring 默认块。
- **HVAC 升级**：当前 IdealLoads；后续可扩真实系统（plan.md 远期）。

## 5_intakeoutput（装配，确定性）

- **契约校验扩展**：`validate_contract` 现查 construction 引用；可扩到 schedule/material 引用闭包的全量校验。
- 目前较稳，升级优先级低。

---

## 路线图锚点（用户定，2026-06-10）

1. Fable 5 完整体检 0–5（找硬伤）→ 修硬伤。
2. 拿 **sm20 + sm21** 两个干净 anchor → 建 **test_baseline**。
3. 接**国产 VLM API** 做一套全流程（0_reading 自动化）。
4. **依次提升建筑复杂度**（矩形→非矩形→退台/挑空→规范化绘图），每升一档**强化对应的 0–5 环节能力**——本文档的建议在此阶段逐项落地。

详见 [../plan.md](../plan.md) 阶段 3 (B5–B7) + 远期。
