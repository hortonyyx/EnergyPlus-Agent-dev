# 开抽前最小修补 执行日志

- 日期：2026-08-17
- 分支：`6.15_ValidationArchM0toM4`（基线提交 `e9e5d95` 08.17_707repro_prereq_locks_and_overturned_assertions）
- 派工来源：本轮对话内派工（「开抽前最小修补」施工席）
- 施工席位：执行档（Claude Sonnet 5 子代理）
- 裁决书：`AI_agent/logs/reviews/verdict/2026-08-17_707_prereq_review_glm.md`（GLM 跨家族复审，
  CHANGES REQUIRED，0 BLOCKER / 2 MAJOR / 2 MINOR）
- 纪律：⛔ 不 commit（主控统一提交）；⛔ 不跑 `pip install -e`；真解释器 `/opt/venv/bin/python`；
  改 `src/`/`skills/` 前先备份到 `backup/{src,Skill}_history/2026-08-17_prerun_patch/`。

---

## 0. 任务边界（原样引用派工，供审计对照）

四件事，按优先级：
① MAJOR-1 附带项 — `cv_toolbox.md` 仍在教一个已不存在的 raise-era error，同步为当前行为；
② MAJOR-2 — `guide.md` 自检清单「留 null 不算自检失败」一句与门的实际行为（gate① FAIL fact +
v3 typed 判卷 miss）字面打架，如实化后果分档，⛔ 不撤回「留 null 合法」；
③ MINOR-2 — `vision_resize.py` 半数进偶（banker's rounding）边界零锁，补一把可区分案例的边界锁，
neuter 自证（临时副本，⛔ 覆写仓库真实文件）；
④ MAJOR-1 主体 — 判「disagreement 信号补一行侧车聚合」是否可行；若确实只是一行聚合就做，
若需要动 `src/validator/` 或判卷接线（>~20 行、或新增消费者）则停手只登记。

派工方明确声明「错误率 29/29」（上面转述的字段名/行号/后果描述均为二手信息），要求一律回代码核实。

---

## 1. MAJOR-1 附带项：`cv_toolbox.md` 同步当前行为 —— 已修

### 1.1 先读实现，核实实际行为（`src/agent/reading/cv_toolbox/tools.py::px_m_calibrator`）

逐行读完该函数（第 352-524 行）并用 `tests/test_cross_axis_exit.py` 的真实断言交叉核对字段名
（该测试真跑 subprocess，字段名不可能有争议空间）：

- 跨轴 x/y 独立拟合的 `axis_px_per_m` 相对偏差超过 `calibration_max_axis_relative_deviation`
  （0.30%）时，函数**不再 raise**（`421c9d3`/07-31 时代的旧行为），也**不吞掉结果**：
  仍返回一个可用的、blend 出来的 `px_per_m`（对全部锚点做 forced-origin 最小二乘，不区分轴）。
- 同时置位三件事：顶层 `result["axis_calibration_disagreement"] = True`；
  `result["metric"]["confidence"]` 强制降为 `"low"`（注意：**不是**一个叫 `metric_confidence` 的
  平级字段，而是嵌在 `metric` 子对象里的 `confidence` 键 —— 这是我核实后主动改正的一处措辞，
  没有照抄派工单里 `metric_confidence` 这个 Python 局部变量名）；
  顶层 `result["warnings"]` 追加一条 `type: "cross_axis_disagreement"` 的条目，
  携带 `x_px_per_m`/`y_px_per_m`/`relative_deviation`/`relative_deviation_limit` 与一段
  `guidance` 文本（明确写着「re-crop and re-measure...recalibrate」「prefer the single-axis
  scale (axis_px_per_m)...over the blended value」）。
- 顶层同时保留 `axis_px_per_m`（每轴独立值的 dict）供读图器在必要时单独取用。

### 1.2 改了两处（原派工单只点名第 113 行，第 9 行同样在教旧行为，一并修）

`skills/intake_pipeline/0_reading/cv_toolbox.md`：

- **第 9 行**（Tools 清单里 `px_m_calibrator` 一行）：旧句「the tool raises before blending if
  they do not」同样是 raise 时代的残留，若只改第 113 行会留下一处新旧行为互相矛盾的双重说法
  （工具列表说会 raise，Disciplines 说不 raise）。已同步改为如实描述 + 指向下方 Disciplines
  的详细说明。
- **第 113 行**（Disciplines §1 最后一句）：整句改写为——不再 raise、不再扣留结果；说明置位的
  三件事（`axis_calibration_disagreement=true` / confidence 降 `"low"` / `warnings[]` 追加
  `cross_axis_disagreement` 条目）；明确读图器该做什么：把这个组合当作响亮信号而非可以直接
  blend 过去的噪音——重新测量两轴锚点、必要时优先用单轴 `axis_px_per_m` 而非盲目信任 blend 值、
  在 notes 里记下这次分歧。

### 1.3 验证

- `tests/test_cv_toolbox.py` + `tests/test_cross_axis_exit.py` + `tests/test_substrate_fix_tools.py`
  + `tests/test_substrate_sweep_tools.py` + `tests/test_f51_single_frame.py`：113 passed（这些文件
  是全仓唯一引用 `cv_toolbox.md` 内容的测试，均只锁 `--batch` 示例可执行性与库可用性声明，
  不锁 Disciplines 措辞，故未受影响，逐条确认见 §1.3.1）。
- 用户信息未指出、我核实到位的一点：`git log -1 --format="%h %s" -S "A cross-axis disagreement
  error means" -- skills/intake_pipeline/0_reading/cv_toolbox.md` 确认该句引入于 `421c9d3`
  （raise 时代），与裁决书引用一致。

**§1.3.1** 三份引用 `cv_toolbox.md` 的测试文件逐条核实内容：`test_substrate_fix_tools.py`
只锁 `--batch` 示例的具体文件名/路径写法（F-53，与 `<name>` 占位符 shell 元字符坑相关）；
`test_substrate_sweep_policy.py` 只断言库（numpy/PIL/scipy）声明与真实沙箱环境一致；
`test_substrate_sweep_tools.py` 逐条把文档里的 ```bash 示例摘出来真跑一遍 shell。三者都不触碰
「Tools」清单一行简介或「Disciplines」小节的散文措辞，故本次改动不可能踩中它们。

---

## 2. MAJOR-2：`guide.md` 自检清单如实化 —— 已修

### 2.1 先核实两条后果的准确形态（派工单明确要求，⛔ 不许照抄二手描述）

**① gate① 侧**（`src/validator/checks/reading.py::_plan_scale_origin`，第 1002-1064 行）：
plan 视图的 `scale_origin` 缺失/不可用时调用 `rep.add_fail(PLAN_FRAME_CHECK_ID, CheckLayer.CROSS_CHECK,
...)`。`PLAN_FRAME_CHECK_ID = "reading.plan_scale_origin_usable"`（`schema.py:75`，字面核实，非转述）。
`disposition()`（`schema.py:250-258`）对该 check_id 的 FAIL 特判：`run_profile` 不在
`_PLAN_FRAME_PERMISSIVE_PROFILES = frozenset({"exploratory","dev"})`（`schema.py:79`）时返回
`Disposition.BLOCK`，否则返回 `Disposition.FLAG`。**但**——`CheckResult.status` 这个原始事实字段
本身永远是字面 `"fail"`（`CheckStatus.FAIL`），`disposition()` 只是policy 查询层的派生结果，不改写
`status`；而 `reading_checks.json` 落盘时写的是 `reading_report.model_dump_json(...)`
（`pipeline.py:1320-1322`），即完整 `CheckReport`（含逐条 `results[]` 原始 `status`）—— 所以
「exploratory/dev 降为 FLAG」只影响 blocking() 集合，`checks.json` 里那条 fact 本身永远字面
是 FAIL，裁决书这句「但 checks.json 里它就是 FAIL」核实**准确**。

**② v3 typed 判卷侧**（`src/agent/judge/reading_typed_adapter.py`，第 431-458 行）：
`scale_origin` 非 dict 或 `world_x_m`/`world_y_m` 不是严格有限数时抛 `ValueError`，被捕获后返回
`_na_components(..., reason="plan_frame_unavailable", cause_class="product_content",
denominator_disposition="retain_as_miss")`，作用于 `_PLAN_COMPONENTS = ("plan_segments",
"plan_openings")`（第 62 行）——即该视图的**全部墙段和全部开口**。字面核实 `reason`/
`denominator_disposition` 与裁决书转述完全一致。追查 `denominator_disposition` 的三态语义
（`score_schema.py:682` 定义为 `Literal["score","filter","retain_as_miss"]`）：`"filter"`
（trusted_input 类原因）在 `reading_typed_score.py:657-668` 的注释里明写「remain explicitly
visible as zero-unit NA audit rows but never enter a red denominator」——即真正被排除、不计分；
而 `"retain_as_miss"`（本情形，product_content 类原因）**没有**这条排除逻辑，对应的 GT 目标仍
留在 `denominator_target_ids` 里、但因为该视图整体 NA 导致零 observation 可匹配 ⇒ 这些目标全部
按 miss 计分。`reading_typed_adapter.py` 全文 grep `run_profile`：零命中——**这条后果与
run_profile 完全无关**，确认「与档位无关」这句转述准确。

结论：裁决书对这两条后果的技术描述（check_id、reason、denominator_disposition、run_profile 无关性）
**全部核实准确**，没有需要纠正的转述错误。

### 2.2 改动前先读契约锁——发现一处派工单未提及的强约束

`tests/test_reading_schema.py::test_plan_scale_origin_is_an_optional_not_mandatory_reader_instruction_contract`
（第 22-115 行）**不是纯反向断言集合**：除了 5 条「旧措辞不得回潮」的负向断言（第 111-115 行），
它还有多条**正向断言**（第 88-108 行）要求特定短语必须原样存在于 `guide.md`/`pen_library.md`/
`session_kickoff.md` 中，其中第 98 行：

```python
assert "omitting it is not itself a self-check failure" in guide
```

——这正是 MAJOR-2 要求我改写的那句话的**逐字子串**！派工单把这把锁描述成「有反向断言（防旧措辞
回潮）」，隐含的模型是"锁只会阻止我引入危险旧话术"；但实际上锁里还锁着一条**要求这句话的字面
文本继续存在**的正向断言。这是我核实后发现、需要向派工方指出的一处：**若直接删除或改写这句话，
无论新写法多准确，都会让这把契约锁变红**（这也印证了该测试 docstring 自己讲的教训：
「过去这把锁只 pin 一句话的字面措辞，锁错了内容」——现在这把锁自己也有同样的脆弱点，只是这次
锁住的是我恰好需要动的那句）。

**处理方式**：不删除、不改写原句，而是**在原句后面追加**后果说明——保留
`"omitting it is not itself a self-check failure"` 逐字不动（满足正向断言 + 不撤回"留 null
合法"这条底线），紧接着追加一整句如实描述 gate①/v3 判卷后果的话。这样正向断言与负向断言
（第 111-115 行五条禁词，均未出现在我的新增文本里）同时满足。

### 2.3 改动内容

`skills/intake_pipeline/0_reading/guide.md` §6 自检清单，`scale_origin` 那一条：

原句结尾「Fine to omit (`null`) when not cheaply confident — omitting it is not itself a
self-check failure.」

改为（追加，原句逐字保留）：「...omitting it is not itself a self-check failure, and guessing
a number you are not confident of is worse than leaving it out. It is not free either, though:
a plan with no usable `scale_origin` is recorded as a failing check
(`reading.plan_scale_origin_usable`) — non-blocking on `exploratory`/`dev` runs, but blocking
on `golden`/`regression` acceptance runs — and in scored (v3 typed) grading it makes this
view's entire plan channel (every wall segment and opening on it) score as a miss, on any run
profile. Omit it only when you are genuinely not confident; do not guess just to dodge that
cost.」

### 2.4 验证

- `/opt/venv/bin/python -m pytest tests/test_reading_schema.py -q -n0` → **10 passed**（含上述
  契约锁本身）。
- 逐条核对新增文本不含 `test_reading_schema.py` 第 111-115 行的五个禁词
  （`must** declare`/`mandatory container action`/`overall projected maximum building
  boundary`/`SW inner corner`/`all floors share that datum`）——均未出现。
- 未触碰 §1（"leave `scale_origin` `null` rather than guess"）与 §2 schema 注释区域，故那两处
  正向断言（`re.search(r"plan view SHOULD\s+also declare...")` 等）不受影响，理论如此、
  且已被上面的 10/10 通过实测证实。

---

## 3. MINOR-2：`vision_resize.py` 半数进偶边界补锁 —— 已修

### 3.1 先复算派工单给的案例（`max_edge` 未记全，自行推导）

用真实模块（非重写）在临时脚本里直接调用
`resized_size(408, 289, max_edge=1568, max_tokens=160)` → `(396, 280)`；
用 `max_edge ∈ {1568, 2576, 4784, 10000, 100000}` 全部得到同一结果 —— 说明这个案例的分辨力
**完全来自 `max_tokens=160` 这个约束，与 `max_edge` 取值无关**（只要不是过小到反而成为主导约束）。
用标准档 `max_edge=1568` 即可复现，不必猜派工单原始用的具体值。

复算半数进偶差异：把模块级 `round` 名字（Python 允许通过模块 `__dict__` 遮蔽内建名，函数体内的
裸 `round(...)` 调用会先查模块全局命名空间再查内建）替换成 `math.floor(x + 0.5)`（half-up），
同一调用变为 `(395, 280)` —— 长边差 1 像素，与裁决书描述的形状完全一致。

### 3.2 补的锁

`tests/test_f51_single_frame.py` 新增 `test_resized_size_half_to_even_boundary_disagrees_with_half_up_rounding`
（紧跟在原有的 `test_resized_size_matches_anthropic_doc_worked_example` 之后，同一个「0) 纯函数
算法」小节内，不需要 `staging` fixture）：

```python
assert resized_size(408, 289, max_edge=1568, max_tokens=160) == (396, 280)
```

docstring 说明这把锁存在的理由（既有的 12 个案例——A4 官方样例 + 两个真实平面图目标尺寸——全部
不落在 `.5` 边界上，故摘不出这条边界的分辨力）。

### 3.3 neuter 自证（临时 `git worktree`，⛔ 未覆写仓库任何文件）

严格照 GLM 裁决书 N4 同款手法但换成不落盘仓库的版本：

1. `git worktree add --detach <scratchpad>/neuter_f51_boundary HEAD`（新建一个游离于仓库工作树
   之外的临时检出，位于 scratchpad 而非仓库内，HEAD=`e9e5d95`，与当前仓库状态一致）。
2. 把本地已编辑的 `tests/test_f51_single_frame.py`（含新增的这把锁）复制进该 worktree
   （因为 worktree 检出的是 git 对象库里的 HEAD 快照，不包含我尚未 commit 的改动）。
3. 只在 worktree 副本里编辑 `src/agent/execution/vision_resize.py`：加一个 `_half_up` 辅助函数，
   把 `resized_size` 二分搜索里的两处 `round(mid/ar)`/`round(lo/ar)` 换成 `_half_up(...)`
   （`max(round(mid / ar), 1)` → `max(_half_up(mid / ar), 1)`，`lo` 同理）。
4. `cd` 进该 worktree 跑 `pytest tests/test_f51_single_frame.py -q -n0`。

**结果**：`1 failed, 11 passed`——**恰好且仅有**新增的这把锁变红
（`assert (395, 280) == (396, 280)`），其余 11 个既有测试（含 A4 官方样例、两个真实平面图目标
尺寸、立面零改动、MANIFEST 哈希、原图未改、cv_probe 真子进程看到缩放帧、旧 wiring-neuter 测试）
**全部保持绿色**——与裁决书 N4「零红（3 passed）」描述的既有锁盲区完全吻合（旧套件在这个
mutation 下确实测不出问题，我的新锁把这个盲区堵上了），且没有引入任何连带误伤。

5. `git worktree remove <path> --force` 清理；核实真实仓库 `src/agent/execution/vision_resize.py`
   逐行未变（`grep round(` 结果与改动前完全一致，无 `_half_up`）。

### 3.4 备份

在改 `skills/`/`src/` 前应先备份——这一步我做晚了（先编辑了 `cv_toolbox.md`/`guide.md` 才想起
补备份），已用 `git show HEAD:<path>` 把两个文件**编辑前**的内容补写入
`backup/Skill_history/2026-08-17_prerun_patch/0_reading/{cv_toolbox.md,guide.md}`，并用
`diff` 确认备份内容与当前工作区版本不同（即备份确实是编辑前状态，非误存编辑后状态）。
`vision_resize.py` 本身在真实仓库中从未被编辑（mutation 只发生在 worktree 临时副本里），
故不需要为它另建备份。

---

## 4. MAJOR-1 主体：disagreement 信号进不进账本 —— 判定为"需要动 `src/validator/` 或
   判卷接线量级"，⛔ 停手，只登记

### 4.1 先搞清楚"账本"具体指什么、写入点在哪

从 `merge_isolated_output`（`src/agent/execution/isolation.py:323-537`，读图 attempt 归档的
唯一入口）出发逐行读：

- `_build_provenance(staging_root, output_hash)`（`isolation.py:985-1011`）——写
  `attempts/NNN/isolation_provenance.json` 的纯 dict 构造函数，**不是** pydantic 模型，
  当前字段全部来自现成材料（`MANIFEST.json`/`isolation_settings.json`/`guard.py` 各自的哈希 +
  `access_log.jsonl` 的条目数/拒绝数）。
- `_archive_isolation_artifacts(staging_root, attempt_dir)`（`isolation.py:1014-1036`）——只
  把 4 个**固定路径**的文件（`MANIFEST.json`/`isolation_settings.json`/`guard.py`/
  `access_log.jsonl`）复制进 `attempts/NNN/isolation_archive/`。**`out/cv_evidence/` 不在这
  4 个之列**——裁决书这句「merge 链路只搬运 prescan 的 cv_evidence，工具运行时证据不进
  attempts 账本」核实**准确**（虽然它举的行号 `isolation.py:782-787` 实际是 `_copy_prescan`
  这个**构建期**把历史 prescan 证据拷**进** staging 供读图器参考的函数，跟"合并期把本轮工具
  证据拷**出**归档"是两个方向相反的函数——但结论本身，"工具运行时证据不进 attempts 账本"，
  经我独立读 `merge_isolated_output` 全文核实，是对的）。
- `checks.json`（`src/validator/checks/schema.py::CheckReport`）与 `RunManifestV2`/
  `StageRecordV2`（`src/agent/execution/manifest.py:245-314`）都是 **`model_config =
  ConfigDict(extra="forbid")`** 的严格 pydantic 模型，且都带显式 schema 版本字面量
  （`record_schema_version: Literal["2"]`/`REPORT_SCHEMA_VERSION`）——加字段等于改 schema，
  这两个target **明确落在派工单划的红线内**（`checks.json` 是 `src/validator/` 的产物；
  `RunManifestV2` 虽然物理上在 `src/agent/execution/`，但它是全项目的账本身份契约，改动性质
  与"判卷接线"同级，且本身有版本号治理，不是"顺手加一行"能做的）。

### 4.2 关键佐证：这个缺口是被前人**明确看到过、明确记成未来工作**的，不是被漏掉的

`src/agent/reading/cv_toolbox/sidecar.py:109-110`（`write_sidecar` 函数尾部，紧挨着实际写文件
那行）：

```python
# Future attempts collection may archive cv_evidence beside output/checks;
# current behavior is a flat-stage audit sidecar only.
```

这条注释在写 sidecar 机制的**当初**就已经点名了"以后 attempts 归档可能会把 cv_evidence 一起
archive 进去，现在还没做"。这说明当前这道缺口不是本轮才发现的疏漏，而是一个此前有意保留、
留待专门批次处理的设计选择——与裁决书"MAJOR-1 建议"的定位（一条改进建议、非本批次遗漏）一致。

### 4.3 为什么不是"一行聚合"——逐条列出真实工作量

即便把落点严格限定在唯一不碰 `src/validator/`/判卷的候选（`_build_provenance` 返回的 dict），
真要做成一个负责任的改动，至少要过这几关：

1. **没有单一固定路径可以直接照抄 `_archive_isolation_artifacts` 现有的"4 个文件各复制一次"
   模式**：读图器每次调用 `run_cv_probe.py` 时的 `--out-dir` 是它自己按
   `cv_toolbox.md`「`--out-dir out/cv`（or any `out/<name>`）」这条契约自由选的名字，
   sidecar 实际落点是 `evidence_dir(out_dir, source_image)` = `Path(out_dir) / "cv_evidence" /
   Path(source_image).stem`（`sidecar.py:25-26`）——不同调用可能落在
   `out/cv/cv_evidence/...`、`out/measure/cv_evidence/...` 等不同子树下。要收全一次 attempt
   里的全部 cv_evidence，需要一个递归 glob（如 `staging_root.glob("out/**/cv_evidence/**/*.json")`）
   + 逐份 JSON 解析（防守未知/畸形内容），而不是一行 dict 赋值。
2. **需要做一个此摊无权限做的语义决策**：聚合到什么粒度？只统计 `px_m_calibrator` 这一种工具
   的 `axis_calibration_disagreement`，还是把 `overlay_logger` 里 `status="rejected"` 的候选
   也算进广义的"disagreement"？记布尔、计数，还是列出受影响的 `candidate_id`？多次标定里，
   后一次成功的标定是否抵消前一次的 flag？这些都不是"给已有字段填个值"，而是需要人拍板的
   小型设计——这正是 MAJOR-2 反复强调的「语义决策不该由收尾摊顺手定」在这里的同型重演。
3. **本仓的测试文化要求任何新行为都要有真实入口锁 + neuter 自证**（本次任务本身的第 3 部分
   就是活生生的例子）。同类规模的既有测试文件（`test_cross_axis_exit.py` 237 行、
   `test_f51_single_frame.py` 原 297 行）显示，达到本仓惯常质量门槛所需的测试代码量级远超
   "~20 行"生产代码本身。
4. **一个没有消费者的新字段，恰好是本条 finding 本身在批判的那个模式**：本仓反复出现过的判据
   「一个不与行为绑定的声明 = 带变量名的注释」（`ep-zero-severe...`/多条 memory 记录同一判据）
   直接适用于此——如果新增的 `provenance.json` 字段仅仅是"写了但没人读、没有测试断言它在
   disagreement 真实发生时确实非零"，那它并不能真正解决"事后无法区分模型没量 vs 量了但被
   标记仍照用"这个问题，只是把同一个"未绑定声明"的缺陷从工具结果字段搬到了账本字段——
   要让它真正有价值，至少需要一条断言"真实触发 disagreement 的 attempt，`provenance.json`
   里这个字段确实非零"的回归锁，这本身也不是一行能完成的。

### 4.4 结论与建议

**不动手**。核对派工单给的判据（"如果它需要动 `src/validator/` 或判卷的接线（>~20 行、或要
新增消费者）⇒ 停手只登记"）：本条改动虽然物理上可以避开 `src/validator/` 与判卷模块本身，
但（a）达到"这个字段值得信任"所需的扫描/解析逻辑 + 语义决策 + 测试覆盖，量级与本仓同类改动
（本任务第 3 部分的完整过程）相当，明显超出"一行"；（b）两个结构上"正确"的持久化位置
（`checks.json`／`RunManifestV2`）都是严格 schema、版本治理的模型，touching 它们就是直接
touching `src/validator/`／账本 schema；（c）不配"消费者"的新字段本身违反本仓自己反复申明的
判据，做了也可能是无效功。三条任一即够格触发"停手只登记"，三条同时成立。

**建议归属**：与 gate①/判卷对 `axis_calibration_disagreement`/`metric_confidence` 的正式消费
接线（MAJOR-1 主诉求里"三信号零消费者"的根治）合并成一个批次一起做——因为"把信号写进持久化
账本"与"决定谁读它、读到后 FLAG 还是 FAIL"是同一个设计问题的两半，分开做前一半只会再制造一个
新的"写了没人读"的字段。该批次天然属于 reading 判卷线（`AI_agent/plan.md`「reading 主线」
一节持续在跟踪的工作），不属于"开抽前最小修补"这类收尾摊的职责范围。

---

## 5. 全仓验收

`/opt/venv/bin/python -m pytest -n auto -q`（真实跑完，非估算）：

```
2835 passed, 14 xfailed, 212 warnings in 514.25s (0:08:34)
[exited with code 0]
```

- **基线 2834 passed / 14 xfailed / 0 failed → 现在 2835 passed / 14 xfailed / 0 failed**：
  恰好 `+1 passed`，与本摊唯一新增的一把锁
  （`test_resized_size_half_to_even_boundary_disagrees_with_half_up_rounding`）精确对应，
  **零新增红、xfailed 数量不变**，符合验收口径「不许多出任何红」。
- 212 条 warning 全部是 `tests/test_orchestrate_baseline.py` 走
  `scripts/tool_scripts/record_baseline.py` 时对 synthetic run 目录缺 `run_config.yaml`
  发出的 `RuntimeWarning`（已核对属该测试文件既有夹具行为，与本摊改动的四个文件
  ——`cv_toolbox.md`/`guide.md`/`test_f51_single_frame.py`/无 `src/` 改动——无关）。

---

## 6. 改动文件清单

- `skills/intake_pipeline/0_reading/cv_toolbox.md`（改，两处：第 9 行 Tools 清单一行 + 第 113 行
  Disciplines 最后一句）
- `skills/intake_pipeline/0_reading/guide.md`（改，一处：§6 自检清单 `scale_origin` 条目追加
  后果说明）
- `tests/test_f51_single_frame.py`（改，新增一个测试函数 + 对应 docstring）
- `backup/Skill_history/2026-08-17_prerun_patch/0_reading/cv_toolbox.md`（新增，编辑前快照）
- `backup/Skill_history/2026-08-17_prerun_patch/0_reading/guide.md`（新增，编辑前快照）
- `AI_agent/logs/reviews/execution/2026-08-17_prerun_minimum_patch_execution_log.md`（本文件）

`src/` 目录**零改动**（第 4 部分判定停手；第 3 部分的 `vision_resize.py` mutation 只存在于已
清理的临时 `git worktree` 里，从未落进仓库）。⛔ 未 commit，交主控统一处理。
