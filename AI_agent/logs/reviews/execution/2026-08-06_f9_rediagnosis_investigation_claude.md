# F-9 重新定性：`resolve_window_hosts` 崩溃（Claude Sonnet 5 席位，纯只读）

- **日期**：2026-08-06
- **席位**：Claude Sonnet 5 子代理（派工单原写 GLM-5.2，orchestrator 已按 delta 改派本席位）
- **基点**：主工作树 `/workspaces/EnergyPlus-Agent-dev`，分支 `6.15_ValidationArchM0toM4`，
  HEAD `dfbd62a`（delta 指定的基点，非派工单原写的 `b379cd8`）
- **性质**：纯只读调查。**零生产代码改动、零测试改动、零 LLM 调用、零重抽**。
  复现走一次性脚本（`/tmp/claude-0/.../scratchpad/repro_f9.py` + `repro_f9_detail.py`，未落回仓库）。

## 0. 开工自检

```
$ git log --oneline -1
dfbd62a 08.06_WrapUp_F10_Wall3_F11_Closed_0to5_ThroughAndF12_Diagnosed
$ git status --short
?? AI_agent/logs/reviews/request/2026-08-06_f8_and_max_retries_scoping_claude.md
?? case_tests/e2e_tests/sm21_anchor/run_2026-08-04_e1_haiku_e2e/0_reading/cv_evidence/
?? case_tests/e2e_tests/sm21_anchor/run_2026-08-04_smoke_downstream/
?? case_tests/e2e_tests/sm21_anchor/run_2026-08-05_smoke_downstream_r2/1_correction/
?? case_tests/e2e_tests/sm21_anchor/run_2026-08-06_wall3_a_retest/
$ pwd
/workspaces/EnergyPlus-Agent-dev
```

四个 `case_tests/` 未跟踪目录与 delta 描述吻合（未动）。多出的第五项
`AI_agent/logs/reviews/request/2026-08-06_f8_and_max_retries_scoping_claude.md` 是另一份并行派工单
（F-8/`MAX_RETRIES` 相关，非本单范围），**未打开、未动**，如实记录存在。

产物来源：`.claude/worktrees/f7-manual`（分支 `f7-source-ids-sonnet`，HEAD `19d9ec6`，只读挂载）。
该 worktree 的 `src/agent/correction/{parse.py,window_sources.py}` 与
`src/validator/checks/mep.py`/`output_coordinates.py` 相对主树有小量后续差异（F-2c/F-7 rework 的注释与
分类细化、F-10 相关改动），**均不涉及 `_BASE_SIGN`**（逐字比对见下）；本单**用主工作树（今天 HEAD）的代码**
去跑那份产物的复现，因为主树是 f7-manual 分支的超集（已合并 F-7），复现路径与 08-05 报告一致。

```
$ diff .claude/worktrees/f7-manual/src/agent/correction/window_sources.py src/agent/correction/window_sources.py
```
（差异仅限 `build_observation_reference_catalog_from_run` 的 `required_for_v3` 参数与三处错误分类注释/拆分，
`_BASE_SIGN = {"North": -1, "South": 1, "East": 1, "West": -1}` 一字未改。）

---

## 1. 复现（零 LLM）

```python
geom = CorrectedGeometryV3.model_validate(json.loads(correction_geometry.json))
verified_inputs = build_verified_window_inputs_from_run(
    producer_draw=geom, run_dir=RUN_DIR, reading_dir=RUN_DIR/"0_reading",
)
finalize_correction_draw(geom, vector_dir=RUN_DIR/"0_reading",
                          target=correction_target("orthogonal_polygon"),
                          verified_window_inputs=verified_inputs)
```

逐字重现同一个 `WindowHostResolutionError`，`.conflicts` 长度 4，与 08-05 报告的记录逐字节一致
（window_id / reason_code / raw_span 全部相同）。

**精确调用链**（本次独立打印 traceback 拿到的行号，今天 HEAD 上仍成立）：

```
finalize.py:120  finalize_correction_draw
  → deterministic.py:1061  apply_deterministic_core
    → deterministic.py:778  _apply_envelope_reconcile
      → envelope_transform.py:536  apply_v3_envelope_transaction  (pre-transform 调用，无 try/except)
        → envelope_transform.py:478  _dry_resolve_current_ring
          → window_host.py:877  resolve_window_hosts
            raise WindowHostResolutionError(tuple(conflicts))
```

`run_stage.py` 里包 `finalize_correction_draw` 调用的 try/except **只认 `WindowResolverInputError`**
（`window_sources.py:75`），而 `WindowHostResolutionError`（`window_host.py:379`）是**独立的
`ValueError` 子类，与 `WindowResolverInputError` 无继承关系** —— `except WindowResolverInputError`
不会捕获它，异常穿透 `run_stage.py` 的 draw 循环、整条 flow 硬崩。这与 08-05 报告的诊断一致，本次独立核实。

---

## 2. ⭐⭐ Q1：`conflicts` 里到底是什么

4 个冲突，全部 `reason_code="source_geometry_mismatch"`、全部在北立面、跨两层：

| window_id | floor | 平面声明区间（=`window.span`=`raw`） | 立面来源换算出的世界区间（`sign=-1`,`along_origin=14.88`）| 与平面声明区间的关系 |
|---|---|---|---|---|
| `W-F1-N-1` | floor-1 | `[1.24, 3.64]` | `[11.24, 13.64]` | **不重叠**，差 ≈ 10.0 m |
| `W-F1-N-3` | floor-1 | `[11.36, 13.76]` | `[1.12, 3.52]` | **不重叠**，差 ≈ 10.24 m |
| `W-F2-N-1` | floor-2 | `[1.95, 5.55]` | `[9.33, 12.93]` | **不重叠**，差 ≈ 7.4 m |
| `W-F2-N-2` | floor-2 | `[9.45, 13.05]` | `[1.83, 5.43]` | **不重叠**，差 ≈ 7.6 m |

触发点 `window_host.py:719-722`：existence 声明引用的**每一个**来源都要各自换算出与
`window.span` 重叠的世界区间；`raw`（=plan 来源换算值，二者本就相同，见下）与 elevation
来源换算值不重叠 ⇒ 4 条全部命中。

同一批北窗里 `W-F1-N-2`（span `[6.3,8.7]`）**没有冲突**：其立面换算值 `[6.18,8.58]` 与平面声明
`[6.3,8.7]` 差 0.12 m（在 `window_host_span_epsilon_m` 容差内）——不是它算对了，是它恰好落在
立面对称轴附近（详见 §3）。

---

## 3. ⭐⭐ Q2 定性：方向约定是对的，那它到底崩在哪

**判据（可独立复算，非印象）**：拿每个冲突窗口的「立面来源换算世界区间」，不只跟**自己**的平面声明区间比，
也跟**它的镜像搭档窗口**（同立面、跨过立面对称轴 7.44 m 的另一扇窗）的平面声明区间比。

| window_id | 立面换算区间 | 与**自己**平面区间之差 | 镜像搭档 | 与**搭档**平面区间之差 |
|---|---|---|---|---|
| `W-F1-N-1` | `[11.24, 13.64]` | ≈10.0 m（不匹配） | `W-F1-N-3` `[11.36,13.76]` | **0.12 m（两端一致）** |
| `W-F1-N-3` | `[1.12, 3.52]` | ≈10.24 m（不匹配） | `W-F1-N-1` `[1.24,3.64]` | **0.12 m（两端一致）** |
| `W-F2-N-1` | `[9.33, 12.93]` | ≈7.4 m（不匹配） | `W-F2-N-2` `[9.45,13.05]` | **0.12 m（两端一致）** |
| `W-F2-N-2` | `[1.83, 5.43]` | ≈7.6 m（不匹配） | `W-F2-N-1` `[1.95,5.55]` | **0.12 m（两端一致）** |

**四条全部精确命中「搭档」而非「自己」，且四次的系统性残差都恰好是同一个 0.12 m**
（= `along_origin=14.88` 与北立面尺寸链总宽 `15.0` 之差，一个与本次缺陷无关的、独立存在的基准偏移，
08-05 报告已指出）。这不是巧合、不是"我看着像"——是可重算的精确数字重合，四次独立命中。

**⇒ 结论：这 4 个窗口的 `existence.source_ids` 里，correction 抽签把「立面观测笔画」引用错了对象
——引用成了它镜像搭档窗口的那一笔，而不是自己的。**

**逐条证实**（`correction_geometry.json` 的 `existence.source_ids` + `0_reading` 原始笔画）：

| window | 引用的立面笔画 | 该笔画的局部值 `x_range_m`（`North_view.json`）| 平面来源笔画 | 局部值（世界值，plan 无镜像歧义）|
|---|---|---|---|---|
| `W-F1-N-1`（plan=west,`[1.24,3.64]`）| `North_view/S5` | `[1.24, 3.64]` | `1f_view/S11` | `[1.24, 3.64]` |
| `W-F1-N-3`（plan=east,`[11.36,13.76]`）| `North_view/S7` | `[11.36, 13.76]` | `1f_view/S13` | `[11.36, 13.76]` |
| `W-F2-N-1`（plan=west,`[1.95,5.55]`）| `North_view/S3` | `[1.95, 5.55]` | `2f_view/S11` | `[1.95, 5.55]` |
| `W-F2-N-2`（plan=east,`[9.45,13.05]`）| `North_view/S4` | `[9.45, 13.05]` | `2f_view/S12` | `[9.45, 13.05]` |

**引用的立面笔画的局部 `x_range_m`，逐字节等于该窗口自己的（世界系）平面声明值** ——
这正是「按裸数值巧合配对」的指纹：平面世界坐标（无镜像）与立面局部坐标（要镜像）在数值上
"看起来一样"，抽签按**原始数字相同**去配对了两个视图里的笔画，而不是按`_BASE_SIGN`规定的镜像
关系去配对。这套配对方式只要窗口位置**关于立面中轴不对称**就必然配反（因为镜像后数值就不再相同）
——`W-F1-N-2` 恰好长在中轴附近所以"蒙对"、没能识破 4 条真错配。

**North 立面尺寸链 `1240|2400|2660|2400|2660|2400|1240`（回文）本身证明不了任何方向**
（上一份 08-05 调查已因此栽过一次，本单不复用它做方向证据）；**但它解释了为什么这个配对错误
在数值层面完全"自洽"、模型/代码都没有从数字本身得到任何报警信号**——回文意味着镜像搭档窗口的
**宽度**恒等，配对错了也不会在宽度上露出马脚，唯一能拆穿它的是`resolve_window_hosts`这类同时
持有平面与立面两条独立来源、并强制施加`_BASE_SIGN`镜像关系的确定性检查——而它确实拆穿了，
这正是 B5 host resolver 设计初衷生效的证据，不是它的缺陷。

**旁证（South/East 无一冲突，进一步排除"检查本身有毛病"）**：South/East 的 `_BASE_SIGN=+1`
（不镜像），同样的「裸数值配对」策略在 sign=+1 下**本来就等价于正确配对**，所以 South 5 扇窗、
East 2 扇窗全部通过检查——不是因为这批抽签在南/东立面上更认真，是因为符号恰好为 +1 时，
"错误的配对方法"与"正确的配对方法"给出同一个答案。这进一步坐实：**问题出在配对方法本身
（不区分局部系与世界系、忽略镜像），只是在 sign=+1 的立面上被掩盖，在 sign=-1 的立面上暴露。**

**责任归属**（不改变本单"只调查不定案"的性质，但按 F-7 已有分类习惯记录）：
`window.span`（along/width）逐条来自 **plan** 来源（`method: dimension_chain_C_top`，只引用 `1f_view`/`2f_view`），
与立面无关、不受镜像影响、可信。`existence.source_ids` 里额外引用的**立面**笔画，其配对选择
（选 S5 还是 S7）**完全是这次抽签自己做的判断**，没有任何确定性代码在抽签之前替它做过世界系换算或
候选排序——即"要不要应用镜像"这个判断被留给了模型自己在裸局部数字和裸世界数字之间做匹配，
模型选择了"数字看着一样"的那个，选错了。

---

## 4. ⭐⭐ Q3：修法选项（不动手，仅列后果与代价）

**选项 A——什么都不改**：
每次真实抽签只要在某个 `sign=-1` 立面上撞到"窗口位置关于该立面中轴不对称 + 宽度或局部数值容易与
另一扇窗数值重合/接近"的布局，就会**大概率**复现本次的裸数值配对错误，**且必定硬崩整条 flow**
（因为 pre-transform 调用点没有 try/except，见 §1）。对称/近对称立面布局在建筑图纸里并不罕见
（本 case 恰好北立面回文），代价 = **这类布局的 case 在 1_correction 阶段 100% 不可能跑完**，
且崩溃点离真正病因隔着 5 层调用栈、报错信息只有 `WindowHostResolutionError` 的默认 message，
不看 `.conflicts` 字段完全定位不到——下一个人大概率要重新做一遍本次的溯源。

**选项 B——补齐 pre-transform 的优雅拒绝路径（与 post-transform 对称）**：
在 `envelope_transform.py:536` 的调用外包一层 try/except，仿照同文件 `:576-591` 已有的写法：
捕获 `WindowHostResolutionError`，若冲突里没有 `invariant_no_geometry_commit` 的 `fallback_action`
（本次 4 条全部是 `needs_input_no_geometry_commit`，不会命中这条硬性子句），转成
`EnvelopeTransformRejected`，走该函数已有的 `except EnvelopeTransformRejected` 分支——回滚到变换前几何、
把冲突证据（`row.model_dump(mode="json")`，含 window_id/reason_code/raw_span/source_input_ids 全套字段）
追加进 `geom.conflicts`，`apply_v3_envelope_transaction` 正常返回，不崩。
- **后果**：1_correction 不再因这类窗口硬崩；这 4 个窗口的 existence 声明变成**结构化记录在案的
  冲突**（而不是吞掉/静默丢弃），下游可读 `geom.conflicts` 知道这几扇窗没通过验证。
  **但错误的配对本身没有被修正**——这 4 扇窗最终会以"未确认"状态存在于产出的 `CorrectedGeometry`
  里（具体降级成 unsupported 还是仍保留但标记冲突，取决于 `apply_v3_envelope_transaction`
  失败后 `apply_deterministic_core` 怎么处理 `geom.conflicts` 非空的情况——**本单未验证这一步**，
  只验证了"不再硬崩"这一层）。
  代价：只是把"硬崩在 1_correction 中段"换成"1_correction 跑完但产出物里 4 扇北窗验证失败"，
  症状变温和了，**没有解决"这类布局下裸数值配对会系统性配反"这个抽签行为本身**。
  实现成本低（对称补一段 try/except，复用已有的 `_conflict_shape`/`EnvelopeTransformRejected`/
  `geom.conflicts` 结构，无需新概念），且直接对齐"post-transform 已经这么做了"的既有先例，
  风险最小、最不容易引入新的假绿/假红。

**选项 C——从源头消除裸数值配对的机会（结构性修法，成本最高）**：
在把候选立面笔画呈现给抽签之前，由确定性代码先按`_BASE_SIGN`把每条候选立面笔画的局部区间
**换算成世界区间**（正是`_source_world_interval`已经在下游做的同一段计算，只是挪到抽签之前），
连同笔画 ID 一起提供给模型做为"候选观测的世界位置"参考，让模型按世界系去匹配，而不是按裸局部数字
去匹配。
- **后果**：从根上避免"数字看着一样就配对"这一类系统性错误，本质是把"要不要镜像"这个几何判断
  彻底移出模型的隐式直觉、交回代码（更贴合项目不变量 #1"代码做所有几何"）。
  代价：需要改 prompt/候选呈现层（不只是本单只读范围内的 `envelope_transform.py`），涉及
  `build_observation_reference_catalog_from_run`（或另开一条呈现候选世界位置的通道）与 correction
  prompt 的改动，**权属/施工成本明显高于 B**，且要重新验证不会引入新的 prompt 稳定性问题
  （如内容变化导致 hash/缓存失效等，需要走完整的施工+对抗审流程，而不是一次窄修）。
  这是"治本"选项，但已超出本次"调查单"的范围，只登记为方向候选。

**选项 A/B/C 的关系**：B 不排斥 C——B 是"止血"（不崩、留痕），C 是"止血+根治病因"。
若采纳 B 且不追加 C，同款对称/近对称立面布局仍会持续产出"这几扇窗验证失败"的结构化记录，
只是不再拖垮整条 flow；长期看这类 case 的窗户识别成功率不会因为 B 而提高。

---

## 5. ⭐⭐ Q4：该硬崩还是该归档重抽？

**两者都不精确对应本次情况**，理由如下，跟 `correction_draw_issues`/F-7 既有口径对齐着说：

- **不该维持现状的"裸硬崩"**：`WindowHostResolutionError` 完全没有 `.category` 字段
  （`window_host.py:379-390` 的 `__init__` 没有这个属性），不像 F-7 引入的 `WindowResolverInputError`
  区分 `model_draw_error`/`input_integrity_error` 两类。`run_stage.py:411/422` 的
  `except WindowResolverInputError` 因为类型不匹配根本捕获不到它，直接穿透——这不是"设计上判定
  该硬崩"，是"这条异常类型从一开始就没被接进 F-7 那套分类机制"，属于遗留缺口（08-05 报告已指出
  这是 07-18 `2803fa7` 起的历史缺口，本单独立复核行号在今天 HEAD 上仍成立）。

- **该不该走"归档成失败 attempt + 盲重抽"（`correction_draw_issues`/F-7 `model_draw_error` 的口径）**：
  本次的根因（§3）确实是**这次抽签自己的判断失误**（裸数值配对，而不是上游产物本身损坏或被篡改）
  ——从"谁的错"这个维度看，形状更接近 `model_draw_error`（模型犯错，理论上换一次抽签有机会避开）
  而不是 `input_integrity_error`（上游数据本身坏了，重抽无意义）。
  **但**：本单在 §3 指出，这个错误对**这一类布局（立面窗口关于中轴对称/近对称）系统性存在**——
  它不是"模型偶然抽到一个坏值"的随机噪声，而是"裸数值配对策略在这种几何下必然产生的结果"。
  若走盲重抽（`step_orchestrator.py:245` 的 `while True` 循环，`draw_fn(None)` 不传任何反馈），
  模型再抽一次大概率会用**同样的策略**再次裸数值配对、再次配反——除非这次的字面数值巧合恰好没那么
  精确（本例是恰好精确到 3 位小数完全相同，未必每次都这么"整齐"，也未必每次都配反）。
  **⇒ 盲重抽对这一类系统性错误的期望修复率不确定，可能烧掉重抽预算却拿到同样的结果**，
  这与 F-7 修复的那类"这次抽签偶然引用了一个它无权引用的观测 ID"性质不同——F-7 那类错误换一次抽签
  大概率避开，本次这类错误换一次抽签**不保证**避开。

- **落地判断**：**选项 B（补齐优雅拒绝路径）本身不等于"归档重抽"**——它把
  `WindowHostResolutionError` 转成 `EnvelopeTransformRejected` 后走的是
  `apply_v3_envelope_transaction` 自己的"回滚到变换前几何 + 记录冲突证据 + 函数正常返回"分支，
  **不是** `run_stage.py` 那套"file as failed attempt + blind resample"分支——这条路径完全不经过
  `correction_draw_issues`/`step_orchestrator.py` 的重抽循环，走的是另一层（envelope transaction 内部）
  已有的"温和拒绝"机制。若要让本类错误接入 F-7 已有的"model_draw_error → 归档重抽"通道，
  需要在 `WindowHostResolutionError` 上补一个类似 `.category` 的字段（或在 `run_stage.py` 单独加一层
  `except WindowHostResolutionError` 分支），**这是本单未验证过的第三条路径，只作为选项 C 之外的
  补充候选记录，不展开设计**（超出"只调查"范围）。

**⇒ 综合回答**：**既不该维持裸硬崩（缺口需要补），也不能简单套用"归档重抽"就认为万事大吉
（这类错误的重抽期望修复率不确定，需要用真实多轮抽样数据验证，本单没有这个数据、
也不该为了拿这个数据去重抽——违反"零 LLM 成本"边界）。** 最小、最贴合既有代码习惯、
风险最低的下一步是选项 B（结构性止血，与 post-transform 对称），至于要不要在此基础上再叠加
"计入 model_draw_error 归档重抽"或直接上选项 C（结构性根治配对逻辑），需要用户拍板，
本单不代为决定。

---

## TL;DR（给 orchestrator）

① **`conflicts` 是什么**：4 条 `source_geometry_mismatch`，全在北立面（`W-F1-N-1`/`W-F1-N-3`/
`W-F2-N-1`/`W-F2-N-2`）。每条冲突的本质：该窗口引用的立面笔画，按`_BASE_SIGN["North"]=-1`
（用户已定案、本单未改未议）换算出的世界区间，跟这扇窗自己的平面声明区间对不上（差 7–10 m），
**但跟它镜像搭档窗口的平面声明区间几乎精确重合**（四次独立命中，残差恒为同一个 0.12 m 系统偏移）。

② **方向约定是对的，为什么还是对不上**：不是方向错，是**这次抽签在给窗口的 `existence.source_ids`
挑选立面笔画时，用了"裸局部数字 == 裸世界数字"的巧合去配对，没有应用`_BASE_SIGN`规定的镜像**。
北立面尺寸链是回文 ⇒ 镜像搭档窗口宽度相等、数值上"配对成功"看起来毫无破绽，实际上配反了两两一对
共 4 扇窗；南/东立面因为 `sign=+1`（不镜像），同一套裸数值配对策略恰好等价于正确配对，所以完全没暴露
——**不是这批立面的配对更靠谱，是符号刚好为 +1 时藏住了同一个策略缺陷**。这是可独立重算的精确判据
（0.12 m 系统残差 × 4 次命中搭档），不是印象。

③ **修法选项**：A. 什么都不改 —— 这类对称/近对称立面布局的 case 100% 硬崩在 1_correction，
且报错信息离病因隔 5 层调用栈；B. 补齐 `envelope_transform.py:536` 缺失的 try/except（与已有的
post-transform `:576-591` 对称）—— 止血成本最低、不崩、把冲突结构化记录进 `geom.conflicts`，
但**不修正配对错误本身**，同款布局仍会反复触发（只是从崩溃变成"这几扇窗验证失败"）；
C. 把立面候选笔画的世界区间在抽签**之前**由代码算好、连同局部值一起呈现给模型，让配对基于世界系
而非裸局部数字 —— 治本但成本最高、超出本单范围（涉及 prompt/候选呈现层）。B、C 不互斥。

④ **该硬崩还是该归档重抽**：现状的硬崩是**遗留接线缺口**（`WindowHostResolutionError` 没有
`.category`、没被 F-7 的分类机制接住），不是"设计上判定该硬崩"；但套用现成的"model_draw_error
→ 归档盲重抽"也不一定管用——本次错因是**这类几何布局下裸数值配对策略的系统性失误**，不是随机噪声，
盲重抽换不换得到不同结果**不确定**（需要真实多轮抽样数据，本单未做、也不该为此消耗 LLM 额度）。
**建议**：先落选项 B（止血、留证据、成本低、风险低），要不要进一步接入归档重抽通道或直接上选项 C，
交用户拍板 —— 本单不代为决定，也没有踩 §1 的用户定案（全程未讨论、未质疑、未触碰 `_BASE_SIGN` 或
`A1_coordinate_normalization.md` §2.2）。

**停下上报**：本单未触发"停下上报"——派工单陈述的事实（4 个冲突、`f7_verify_sonnet` 产物、
复现路径、调用链非对称）经独立复算全部核实成立，未发现题目本身有误。
