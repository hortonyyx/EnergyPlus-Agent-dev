# 天正转换器多层改造定案（GPT 施工席）

日期：2026-08-20  
分支：`6.15_ValidationArchM0toM4`  
结论：施工完成，代码留在工作区未提交；全仓回归通过，可交 GLM 做 neuter 复审、由 orchestrator 跑主控轻门。

## 定案与实现

采用的形态是：**一份源 DXF → 一份规范化 DXF，继续使用 canonical `GTV3_*` 图层；每层各有一个 `PlanViewBinding`，依靠该视图的 clip box、`world_from_source_m` 与 `handle_mode: only_listed` selector 隔离几何。** 多层入口逐 plan 跑原有 S0–S8，再一次性写入同一 DXF；source map 逐层构造后合并；G9/G10 在合并文档上各跑一次。单 plan + 单 floor 仍直接委托原 `run_p2_conversion` 路径。

立面侧同时修正了信任根缺口：提取器先用已算出的 z 区间唯一确定 evidence 所属 floor，再把 floor identity 带入开洞候选筛选；沿墙代价和 tie/歧义判定没有放宽。两层上下对齐开洞因此按层归属，单层原有歧义仍照常报错。

否掉的方案：按层拆成多份规范化 DXF、给 canonical 图层加楼层后缀、在全文档要求唯一 `GTV3_FOOTPRINT`、继续只持久化 `plan_views[0]`、仅按沿墙距离给立面开洞配对、为守旧签字值伪造旧 provenance 哈希。它们分别破坏现行 manifest 契约、跨层光栅/溯源或真实 provenance。

## §四四条前提、§三 D/E 及三处 `plan_views[0]` 复核

1. **前提 1：按第二次修订后的口径成立。** 计划图正确形态确为单 DXF + canonical 图层 + 每视图 clip/affine/handle-pinned selector；原先“提取器无需改”不成立，已按修订范围补上 z-derived floor 筛选。原提取器同层名两层夹具实跑 `2 passed`；本批两层完整正例产出 2 floor（z=0/3.6）、2 个 PlanViewBinding、各层独立 handles，28 条立面记录和每层各 14 个带 z 的 opening。
2. **前提 2：不能把全部门简单逐层重复。** G1 是文档输入事实与 plan 几何的混合门；G2–G8 按 plan 跑并保留逐层 evidence（G6 的房间数、near-threshold 与真人确认也按层汇总）；G9 是合并后的 v3 extraction preflight，G10 是合并文档的人审 overlay，二者各跑一次。文档级输入诊断去重，不会每层重复报警。
3. **前提 3 / §三 E：成立且已实测。** `floor_datums` 的 list 结构足够；四个立面各放入 F1/F2 两个 datum，完整转换和提取成功，立面 audit 同时覆盖两层，无需改 schema。
4. **前提 4：已补核。** 合并 DXF、manifest、source map 与 review bundle rerun 均按真实现行实现重算内容/实现哈希，没有保留旧戳；签字后 rerun 的多层候选包仍通过 review index。`gt_promote.py` 无隐含单层分支，实跑晋升后读取到 F1/F2 两层且 verification 为 `human_verified`。

§三 D 的结论：旧 `_build_source_map(request, plan_view, ...)` 确是单 plan 构造器；现多层入口对每个 persisted plan 调用并合并，正例实测 entry 的 `floor_id` 集合为 `{F1, F2}`。§三 E 结论同上。

三处保留的 `plan_views[0]` 均无害：两处只读取立面标题映射/门块规则，而多层入口已强制所有 plan 的 document dialect 完全相同；另一处只在 raster binding 集合非法时为文档级诊断选择 fallback handle，不参与几何、归层或有效标定。真正的 plan raster 轮廓查找已改为按 view 的 footprint handles。

## 三把硬锁、信任根附加锁与 neuter

- 多层正锁：两层完整正例绿。neuter 为恢复“只写第一 plan”，manifest 立即以 `each floor requires exactly one plan` 变红，未污染其他判定。
- sm24 单层内容锁：源 DXF 经完整四立面路径重跑，规范化 DXF SHA-256 与签字 conversion report 一致；`floors/openings/north_axis` 的 canonical 几何字节与签字 `gt.json` 一致。neuter 为摘掉 deterministic DXF metadata pin，只有规范化 DXF 字节锁变红，几何逐项仍相等。
- 多层 raster handle 锁：正常时两层均通过；neuter 为退回全文档第一条 footprint，恰好只产生 1 条 `tarch_raster_calibration_invalid`，对象为 `plan-F2`，F1 不受牵连。
- 立面信任根 must-red：neuter 为取消 z-derived floor filter，上下对齐开洞令 G9 以 `elevation_opening_assignment_ambiguous` 变红；相对未签候选原有的 G6/G10 状态，唯一新增红门是 G9，未放宽任何单层歧义规则。

上述硬锁/neuter 集合实跑 `6 passed`；相关转换器/提取器集合实跑 `181 passed, 1 xfailed`。

## sm24 内容零漂移与已接受的 render 差异

**内容零漂移是用 sm24 源 DXF 实跑验证的，不是由“单层是多层特例”推断。** 规范化 DXF 实测 SHA-256 为 `5141994f90dd6a928a5fe805a347bb32563b7a455135d2339fc3b133908fa0a1`，与签字报告一致；完整 floors/zones/footprint/openings 坐标（由 `floors`/`openings` 子树覆盖）及 north-axis 字节一致。因此用户裁定 §5.2 第 3 条的“内容差异停工”分支未触发，历史答案内容仍可信。provenance 戳则按现行代码如实更新。

七张 render 均发现既存字节差异，用户已明确接受并将另行重签；本批未调 renderer、未改签字答案：

| 文件 | 本次 SHA-256 / bytes | 签字 SHA-256 / bytes |
|---|---|---|
| `gt_elev.png` | `d2fb878269f6812ed4271eafcfaf27c959ec47b726112699e17c84f851827aef` / 41473 | `7d4c1ed09f31377253838445733a130c11ff2fedf5ca95ddcdd231a7439abe03` / 41562 |
| `gt_plan.png` | `44d1d1e136f8f21899996d630f98d17b03cec4b6c21ea80041ab7ff783c71610` / 43809 | `2ba9dd15497dc935e9a5e6499ef632ae0034179edb0b44164bfbc5025e655bd7` / 43902 |
| `overlay_1f_view.png` | `ef0fb9f16889e683f844cd864dcd9c88679b165f69b64618aca11a932ceca4a0` / 107025 | `135e2995a07e5acf6ed5d878f7e7d0acfc1baef1fdc3e8a687dd8fada705c675` / 106939 |
| `overlay_East_view.png` | `9c95027546fb33b17991aa749ad506f3bf45c1f9a1e664158b65c822235a53c8` / 105909 | `ae69b4276567305dfc9b9145a9a1f2b28593b399a28090d09004a626bd6ed366` / 105557 |
| `overlay_North_view.png` | `76b145c090692d42a1a68318bca70cba098a45e324293d529582efcb78ea6228` / 210589 | `d4a99cca3128e0335fed6bc7f76bb6c9bd700ab155a61eda7f2de5b8ed7be957` / 210244 |
| `overlay_South_view.png` | `b75cf97e5354533051b3c54210350c0f2994eb6efcd4690db7fce0e1c58e529d` / 120819 | `0e66297543fcaecb0899018af25715197538b37373d555c0fc47a46b3f83302e` / 120539 |
| `overlay_West_view.png` | `1d8c4f877f00dbba73ac6529a2e380ac352c967dce2f7ea7b75e76a76684c92d` / 94202 | `a782dd82fa4c309c0893cdf16b8b1dd6a917825ba4ea0dde37ab893d6eba6375` / 93930 |

## 总回归、边界与顺带登记

`python -m pytest -n auto` 实跑结果：**2918 passed, 14 xfailed, 212 warnings，退出码 0，734.58 秒**。相对派工基线 2911 绿，新增 7 个测试全部为绿；strict xfail 数保持 14。`git diff --check` 通过。

冻结的 `case_tests/test_baseline/gt/**` 与 `skills/intake_pipeline/0_reading/**` diff 均为空；未执行 `git add`/`git commit`。除本定案说明这一明确交付外，未改其他 `AI_agent/` 管理文档；既有 `AI_agent/plan.md` 工作区修改保持原样。

顺带登记但不处理：sm24 签字答案的旧 `vg_implementation_sha256` 与现行 correction 实现不一致，且本批合法修改提取器后 `extractor_sha256` 也应更新；这两类 provenance 必须由现行实现如实重算。七张 render 的重签同样留给用户/orchestrator，本批没有调整任一侧。
