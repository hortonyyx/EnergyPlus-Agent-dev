# B4a 批施工细稿出稿请求（派 sol 次高档，2026-07-14）

**任务**：为 C2 的 **B4a 批（gt-v-next + gt_from_dxf 重写 + render_gt/overlay 升级）**出一份代码级施工细稿，落盘 `AI_agent/proposals/c2_b4a_detail_spec.md`（v1）。**本轮只出稿：不改任何代码、测试、golden、gt 资产或其他文档。**

## 1. 权威输入（优先序）

1. [AI_agent/proposals/c2_full_unlock_design.md](../../proposals/c2_full_unlock_design.md) v2.2：**B4a 行**＝gt-v-next（polygon footprint / zone polygon / per-floor / 边界段 / opening→段 ref / north_axis / validator）+ gt_from_dxf 重写（LWPOLYLINE polygonize + 拓扑验证，floor/view/role 配置化，窗归最近合法边界段；**先合成 L/U DXF round-trip 再接 sm25/26**）+ render_gt/overlay 升级（闭 B-03）；依赖 Vg（已施工 CLOSED）；§T'（sm25-L/sm26-U 画法验收器）；E4 定案（gt v-next 加可选 `north_axis_deg` 随 B4a）；DAG 位置（B4a→B4b，B4b 才是段级 scorer）。
2. **已收录实码（以实码为准，出稿前亲自读盘）**：`src/agent/judge/gt.py`（唯一 gt loader，gt 铁律执行点）、`scripts/tool_scripts/gt_from_dxf.py` + `inspect_dxf.py`（现 DXF 通路）、`render_gt.py` + `render_gt_overlay.py` + `render_grade.py`（gt 渲染/判卷 overlay 画法，B-03 语境）、`score_reading_vs_gt.py`（现 scorer 消费的 gt 形状）、`src/agent/correction/schema.py`（strict v3）、`cell_geometry.py`（polygon helper）、`facade_visibility.py`（Vg 核）。
3. 相关细稿定稿：`c2_b2_detail_spec.md` v6（schema v3 精确类型先例）、`c2_vg_detail_spec.md` v3、`c2_va_detail_spec.md` v2（B4b 接缝语境：per-claim denominator / NA 机读形状；**completeness user/dataset 生成通路归 B4b——B4a 不吃**）。
4. 现行 gt 资产与 DXF 前情：`case_tests/test_baseline/gt/`（现 gt.json 形状、`wall_thickness_m: 0.24` outer-skin 换算 W5、sm24 无 gt 待补）；[cad_to_gt_extraction_plan.md](../../proposals/cad_to_gt_extraction_plan.md)（天正 DXF 现实约束：对象需图形导出、按构件分层须先空间切视图、源 DXF 放 gt 根外）。

## 2. 上位定案（不得偏离）

- **gt 铁律**：gt 只 gate② judge / 人可读，gate①/执行器绝不 import——v-next schema 与 loader 改造不得开任何生产侧读 gt 的口子。
- **建筑复杂度可扩展性铁律**：gt-v-next 不得烤死矩形/四标准立面假设——polygon / per-floor footprint / 段级 / opening→段 ref 正是本批目的；接口为 C2.1（局部/内院立面开放集）留缝。
- **零 golden 改动**逐批照旧；既有矩形 case gt（sm20/sm21 等）的迁移策略必须显式设计（migration 还是 dual-read，给出裁决建议与测试锁）。
- **合成用例先行**：用户 sm25-L/sm26-U 图与 sm24 DXF 未到——细稿的验收链必须先建立在合成 L 形/U 形 DXF round-trip 上，真图接入列为后续接缝。
- `north_axis_deg` 可选槽位随本批（E4/B-O 已 CLOSED：出口契约 = Relative + Building.North Axis=θ）。
- **XL 批**：细稿必须给分 Phase 施工切分（先例 = B2b Phase A/B），每 Phase 独立可验收、可单独派工。

## 3. 细稿纪律（硬要求）

- **累计式自包含施工合同**：新执行者只读本稿即可施工；禁止「沿用 vN 未变」式引用；schema 全字段、签名、wire 形状、validator 规则、测试族全部写全。
- 精确类型（pydantic strict / Literal），无隐式默认容差；新容差走配置 + 登记，禁裸字面量。
- 施工前置门只断言**已收录依赖**的机械条件（不预读本批自建之物——B2b r1 教训）；前置门与施工后自检拆分。
- 明确批次边界：本稿只放行 B4a；不放行 B4b/B5 顺带施工。

## 交付

1. 细稿落盘 `AI_agent/proposals/c2_b4a_detail_spec.md`。
2. 回复只给 terse report（稿结构概要 / 关键定案与裁决建议 / **review-ask**（自报不确定处、需主控裁的判断题）），不贴稿全文。

审向：**Fable 最高档交叉审（GPT 侧稿→Claude 侧审，谁写谁不批）**。
