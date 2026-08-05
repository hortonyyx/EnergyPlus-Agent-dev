# F-9 候选调查报告（Sonnet 席位，纯只读）

- **日期**：2026-08-05
- **席位**：Claude Sonnet 5（本单原抬头写 GLM，orchestrator 已改派本席位，内容照用）
- **worktree**：`/workspaces/EnergyPlus-Agent-dev/.claude/worktrees/f7-manual`（分支 `f7-source-ids-sonnet`，HEAD `ca5e26c`，自检通过）
- **性质**：纯只读调查。**零生产代码改动、零测试改动、零 LLM 调用**（见 §0，复现走离线脚本）。

---

## 0. 复现方法（回答派工单 §Q1 的"代价评估"前置问题）

**没有重跑 correction 抽签、没有消耗任何 LLM 额度。** 崩溃那次重抽虽未被归档（硬崩不归档），
但 `run_correction()`（`src/agent/pipeline.py:704-707`）在崩溃**之前**就已把解析后的
`CorrectedGeometryV3` 写入了 `1_correction/correction_geometry.json`（此文件时间戳 10:04，
与崩溃时刻吻合，且窗户 ID 形态 `W-F1-N-1` 等与 attempt 001 失败时的 `win_1F_N_1` 不同 —— 确认是
同一次重抽的产物，不是 attempt 001 的残留）。

用一次性脚本（`/tmp/.../scratchpad/repro_f9.py` + `repro_f9_detail.py`，已在 `/tmp` 完成、未落回仓库）：
1. 加载 `correction_geometry.json` 作为 `geom`；
2. 调用 `build_verified_window_inputs_from_run(producer_draw=geom, run_dir=..., reading_dir=...)`
   （纯读盘 + 校验，零 LLM）；
3. 调用 `finalize_correction_draw(geom, ...)`（纯确定性代码路径，零 LLM）。

**逐字重现了同一个 `WindowHostResolutionError`**，且 `.conflicts` 完整可读（见 §1）。
**⇒ 本单可以、也已经在零额度代价下完成，无需重抽。**

---

## Q1 ⭐⭐ `conflicts` 里到底是什么？

**4 个冲突，全部是 `reason_code="source_geometry_mismatch"`，全部在 North 立面，跨两层：**

| window_id | floor | raw_span (m，来自平面) | 冲突原因 |
|---|---|---|---|
| `W-F1-N-1` | floor-1 | [1.24, 3.64] | 立面来源世界区间与平面声明区间不重叠 |
| `W-F1-N-3` | floor-1 | [11.36, 13.76] | 同上 |
| `W-F2-N-1` | floor-2 | [1.95, 5.55] | 同上 |
| `W-F2-N-2` | floor-2 | [9.45, 13.05] | 同上 |

触发点：`src/agent/correction/window_host.py:720-723`——

```python
if any(min(raw.hi, interval.hi) - max(raw.lo, interval.lo) <= tolerances.window_host_span_epsilon_m
       for _, interval in mapped_sources):
    conflicts.append(_conflict(window, "source_geometry_mismatch", ...))
```

即：该窗 `existence` 声明引用的**所有**来源（平面 + 立面）各自换算出的世界坐标区间，
必须与平面草图给的 `window.span` 重叠；只要有一个不重叠就判冲突。

**同一批 North 窗里 `W-F1-N-2`（中间那扇）没有冲突** —— 但不是因为它算对了，
是巧合躲过了这个检查（见 §2 的数值推导，它的位置恰好接近立面中轴、镜像后与原位置仍有部分重叠）。

`WindowHostResolutionError.conflicts` **本身是有诊断信息的**（`WindowHostConflictV1`：
`window_id` / `reason_code` / `raw_span` / `source_input_ids` / `candidate_segment_ids` 等字段齐全，
见 `window_host.py:296-310`）——问题不是"没有诊断"，而是它没被打印出来（见 §4）。

---

## Q2 ⭐⭐ 这是「模型真的画错了」还是「又一个接口错位」？

**结论：这是接口/约定错位，不是模型画错。已用源图逐位核实，证据链完整。**

### 推导过程

1. `ElevationSourceWindowV1.local_along_interval` **不是** correction LLM 发明的数字，
   是从 0_reading 的原始 stroke 数据 `x_range_m` **原样透传**而来
   （`src/agent/correction/window_sources.py:333`，中间零变换）。correction LLM 唯一做的事
   是在 `existence.source_ids` 里**引用**这些 observation id（如 `"North_view/S5"`），
   世界坐标换算完全是确定性代码做的（`window_sources.py:951-1008` 的 `sign`/`along_origin`）。

2. 换算公式（`facade.py:144-145`）：`world = along_origin + sign * local_x`。
   对 North：`_BASE_SIGN["North"] = -1`（`window_sources.py:42`），
   在 `mirrored=false, local_x_positive="image_left_to_right"`（本 run 的 North_view 声明值，
   逐字取自 `0_reading/North_view.json` 的 `facade` 块）下不翻转，`sign` 最终取 `-1`，
   `along_origin = hi = 14.88`。即代码假定"北立面沿着局部 x 增大方向对应世界 x **减小**方向（朝西）"
   ——这是"人站在建筑外侧、面朝南看北墙"时的物理镜像惯例，写在
   `skills/intake_pipeline/1_correction/A1_coordinate_normalization.md` §2.2 的表里
   （"North | world x | west (−x)"）。

3. **我读了源图逐位核实这个假设对不对**（`case_tests/e2e_tests/sm21_anchor/case_data/North_view.png`
   和 `South_view.png`，真实 CAD 图纸截图）：
   - North 立面底部尺寸链 `1240|2400|2660|2400|2660|2400|1240`（总 15000mm）：
     **最左边**那扇窗起点 1240、宽 2400 → `[1.24, 3.64]` m —— 与 `W-F1-N-1` 的平面草图区间**逐位相同**；
     最右边窗对应 `[11.36, 13.76]` m —— 与 `W-F1-N-3` 逐位相同。
   - South 立面同样：最左窗 `[3.44, 4.64]` 对应 `F1-office-south-west`（西侧房间）。
   - **⇒ 这栋楼的北、南立面图纸实际绘制惯例是"与平面共用同一套轴网、左=西、右=东，两个立面都不镜像"**
     ——这是天正等国内建筑制图里**很常见的真实惯例**（立面轴网标注直接照抄平面轴网，不做视角镜像），
     但 **不是** `A1_coordinate_normalization.md` §2.2 表格假设的"外侧观察镜像"惯例。
   - South 的默认 `sign=+1`（不镜像）**凑巧**与这套"不镜像"真实惯例一致，所以 South 五扇窗全部通过检查；
     North 的默认 `sign=-1`（镜像）**恰好相反**，于是所有偏离立面中轴的北窗全部触发 `source_geometry_mismatch`。

4. **0_reading 的转录是对的**（`x_range_m` 逐位对应源图尺寸链数字，我肉眼核对过）；
   **correction LLM 的引用配对也是对的**（`North_view/S5` 精确对应 `W-F1-N-1`，数值分毫不差）。
   **出错的是确定性代码这一层的默认符号假设，对这批真实图纸不成立。**

5. **W-F1-N-2 逃过检测不代表它没问题**：它在 [1.24,14.88] 范围内位置接近整栋建筑中轴（7.5m），
   错误的镜像变换算出的世界区间 `(6.18,8.58)` 与真实草图区间 `(6.3,8.7)` 恰好还有 2.28m 重叠
   （> `window_host_span_epsilon_m`），检查因此放行——但这只是这扇窗恰好长在对称位置的运气，
   **换算结果本身仍是错的**，只是没被这道检查抓到。这提示该检查本身也有盲区（数值上"凑巧重叠"
   会掩盖同一个 bug）。

6. **West 立面无法验证（结构性受限，不是反例）**：本 case 只有一扇 West 窗（`W-F2-W-1`），
   且恰好长在西立面正中央（`[3.4,4.6]`，立面范围 `[0.12,7.88]`，中点 4.0）——
   `_BASE_SIGN["West"]` 同为 `-1`，同一类 bug 结构上大概率也适用于 West，
   但这栋楼的西立面窗户位置对称到无法用重叠检验暴露，**未经证实、仅结构性怀疑**。

### 与本批既有教训的对齐

派工单点名"F-5/F-7 都是接口错位"——**F-9 属于同一族，但形状不同**：F-5/F-7 是字段名/词表对不上；
F-9 是**方向/符号约定对不上真实制图习惯**，且恰好被本批之前已经记录在案的
`[[sm21-review-backlog]]`（"仅剩 South 2F 窗 x 真 bug（核 correction along-facade x）"）
和 `[[reading-lever-is-measurement-enforcement]]`（R1.5：立面读图方向机器未强制校验）两条记忆
预先点名过——**这不是新类型的缺陷，是旧的、已知未闭合的立面方向问题，第一次被 B5 host resolver
真正跑通后暴露成了硬崩。**

---

## Q3 它该硬崩还是该归档重抽？

**两者都不对——现有机制里已经有第三条正确路径存在，只是这次没走到。**

关键证据：`apply_v3_envelope_transaction`（`src/agent/correction/envelope_transform.py`）
对同一个函数 `_dry_resolve_current_ring` 调用了**两次**，处理方式不对称：

- **post-transform 调用**（`envelope_transform.py:576-591`）：**有 try/except**，
  把 `WindowHostResolutionError` 捕获后转成 `EnvelopeTransformRejected`
  （`.evidence` 里塞进 `[row.model_dump(...) for row in exc.conflicts]`，即完整冲突数据）。
  这个异常在 `apply_v3_envelope_transaction` 自己的 `except EnvelopeTransformRejected`
  （同文件 `:613-617`）里被**优雅接住**：回滚到变换前的 geometry，往 `geom.conflicts`
  追加一条含 `reason_unresolved` / `evidence` / `fallback_action: "rollback_keep_original_geometry"`
  的记录，**函数正常返回，不崩、不抛**。
- **pre-transform 调用**（同文件 `:536-539`，就是这次崩溃命中的那一行）：
  **完全没有 try/except**，`WindowHostResolutionError` 直接原样上抛，
  经 `deterministic.py:778`（`_apply_envelope_reconcile` 内 `return apply_v3_envelope_transaction(...)`，
  同样无 try/except）→ `deterministic.py:1061` → `finalize.py:120`
  （`apply_deterministic_core` 调用处同样无 try/except）→ 一路硬崩到 `run_stage.py`。

`git log -p` 核实：`pre_hosts`/`post_hosts` 两处调用是**同一个提交**
（`2803fa7 7.18_B5_SpecFinalized_PhaseAB_CLOSED`）一起加进来的，
不对称从落地那天就在，此后此文件再无改动——**这是一个从 07-18 起就存在、从未被真实数据踩到的
遗留缺口**，不是本轮新引入的回归。

**⇒ 回答派工单的问题**：这次崩溃**既不该硬崩，也不该套 F-7 那套"model_draw_error 归档重抽 /
input_integrity_error 硬崩"二分法**——`WindowHostResolutionError` 甚至没有 `.category` 字段
（F-7 引入的分类只加在 `WindowResolverInputError` 上，`window_sources.py:75-93`），
`run_stage.py:411-425` 的 `except WindowResolverInputError` 也**不会**捕获这个类。
**正确的出口是让 pre-transform 那次调用复用 post-transform 已经在用的"优雅拒绝"路径**——
补一个对称的 try/except，把它也转成 `EnvelopeTransformRejected` 走回滚 + `geom.conflicts` 记录，
而不是新建一套分类逻辑。

**⚠️ 但这只是解决"崩不崩"，不解决"对不对"**：即使补上这个 try/except，
只要 Q2 的符号假设 bug 不修，这批北向窗户的草稿依然会被判"冲突"而不是被正确接受——
只是从**硬崩**变成**归档失败 + 盲重抽**。而这个失败是**确定性代码 bug 导致的、每次重抽都会
同样触发**（不是模型运气问题）——按用户 08-05 定的"模型抽签写错才归档重抽"的精神，
**归档重抽在这里也是徒耗额度**，真正该做的是修 Q2 那个符号约定。

---

## Q4 「抛异常不带诊断」要不要单独治？

**派工单 §Q4 的前提需要部分推翻**：`.conflicts` 本身**不是**没有诊断——结构化字段齐全
（见 §Q1）。真正的问题范围更窄：

1. **`WindowHostResolutionError` 是 correction/geometry 模块里唯一一个 `__str__` 不带诊断payload的自定义异常。**
   逐一核对了同族全部 6 个异常类：

   | 异常类 | `__str__`（`super().__init__(...)`）内容 |
   |---|---|
   | `FacadeApplicabilityInvariantError`（`facade_applicability.py:47`） | `f"{code}: {self.context}"` |
   | `FacadeVisibilityInvariantError`（`facade_visibility.py:53`） | `f"{code}: {self.context}"` |
   | `WindowResolverInputError`（`window_sources.py:75`） | `f"{code}: {self.context}"` |
   | `WindowDirectionBindingError`（`window_sources.py:936`） | `f"{code}: {self.context}"` |
   | `WindowParentBindingError`（`modelling.py:639`） | `f"{code}: window={window_id}: {self.context}"` |
   | `EnvelopeTransformRejected`（`envelope_transform.py:92`） | 传入的 `message`（人写的一句话） |
   | **`WindowHostResolutionError`**（`window_host.py:379`） | **固定字符串 `"window host resolution rejected"`，忽略 `conflicts`** |

   ⇒ **不是普遍现象**，其余 5 个兄弟类全部把诊断塞进了 `__str__`；`WindowHostResolutionError`
   是这个家族里唯一的例外。这解释了为什么这次崩溃"一个诊断细节都没有"——如果它也遵循同款惯例，
   uncaught 时的原始 traceback 本就会带上 4 个 window_id + `source_geometry_mismatch`，
   即使 §Q3 的 try/except 缺口不补，这次崩溃也不会像现在这样"看不懂"。

2. **最小改法（两条，互相独立，都只是建议）：**
   - **必做**：给 `envelope_transform.py:536` 补上与 `:576-591` 对称的
     `try: ... except WindowHostResolutionError as exc: raise EnvelopeTransformRejected(...)`——
     这是本单最直接、风险最低的修法，且有现成的姐妹代码可以照抄，不是设计判断。
   - **顺手可做**：把 `WindowHostResolutionError.__init__` 的 `super().__init__(...)` 从固定字符串
     改成归纳 `conflicts` 摘要（如 `f"{len(conflicts)} conflict(s): " + ", ".join(f"{c.window_id}:{c.reason_code}" for c in conflicts[:5])`），
     补齐它与另外 5 个兄弟类的一致性——一行小改动，独立于 §Q3 的 try/except 缺口也值得做
     （防的是"以后又有第二个漏加 try/except 的调用点"）。

3. **不是普遍现象，不建议为此扩大排查面**——`src/agent/correction/` 与 `src/agent/geometry/`
   下的异常类已逐一核对（见上表），只有这一个例外；没有必要把 Q4 当成一个系统性专项去扫。

---

## 附：一处未探究的旁支疑点（如实登记，未深入）

`case_tests/.../run_2026-08-05_f7_verify_sonnet/run_config.yaml` 文件头部注释写的是
`# run_2026-08-05_smoke_downstream_r2 (sm21_anchor)`，与所在目录名 `run_2026-08-05_f7_verify_sonnet`
不一致；`models.correction.model_id` 写的是 `deepseek-v4-pro`，并非派工单标题暗示的 "sonnet"。
**这个不一致与本单四个问题无关，也不影响上面任何一条结论**（复现用的是这个目录里实际落盘的
`correction_geometry.json`，与配置文件的自我描述是否准确无关）——只是顺手记一笔，供 orchestrator
判断是否两个 run 曾经共用过 scaffold / 复制过配置文件。**未展开调查，未下结论。**

---

## 证据文件清单

- 复现脚本（`/tmp`，未入库）：
  `/tmp/claude-0/-workspaces-EnergyPlus-Agent-dev/2a823d9a-5699-4868-9da3-62b70d1ab41c/scratchpad/repro_f9.py`
  `/tmp/claude-0/-workspaces-EnergyPlus-Agent-dev/2a823d9a-5699-4868-9da3-62b70d1ab41c/scratchpad/repro_f9_detail.py`
- 崩溃产物（本 run 内，只读）：
  `case_tests/e2e_tests/sm21_anchor/run_2026-08-05_f7_verify_sonnet/1_correction/correction_geometry.json`
  `case_tests/e2e_tests/sm21_anchor/run_2026-08-05_f7_verify_sonnet/1_correction/correction_raw.txt`
  `case_tests/e2e_tests/sm21_anchor/run_2026-08-05_f7_verify_sonnet/0_reading/North_view.json`
- 源图（人工可视核实用）：
  `case_tests/e2e_tests/sm21_anchor/case_data/North_view.png`
  `case_tests/e2e_tests/sm21_anchor/case_data/South_view.png`
  `case_tests/e2e_tests/sm21_anchor/case_data/West_view.png`
- 生产代码（引用行号均见正文）：
  `src/agent/correction/window_host.py`（720-723 冲突触发点 / 379-395 异常类 / 877 raise 点）
  `src/agent/correction/window_sources.py`（41-42 `_BASE_SIGN` / 333 透传 / 951-1008 换算）
  `src/agent/correction/envelope_transform.py`（536-539 无保护调用 / 576-591 有保护调用 / 613-617 优雅接住）
  `src/agent/correction/deterministic.py`（760-786 `_apply_envelope_reconcile`）
  `src/agent/correction/finalize.py`（120-123 调用点）
  `scripts/tool_scripts/run_stage.py`（377-425 F-7 分类逻辑，确认不覆盖本异常）
  `skills/intake_pipeline/1_correction/A1_coordinate_normalization.md`（§2.2 立面方向假设表）
