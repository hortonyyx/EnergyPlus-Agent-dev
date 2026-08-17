# 交叉复审裁决 —— 707 复现前置三件（0ae4b93）+ 14 锁（e9e5d95）

**审方**：GLM 家族（glm-5.3），交叉复审席。**作者**：Claude 侧席位 + orchestrator（「谁写谁不批」）。
**请求书**：`AI_agent/logs/reviews/request/2026-08-17_707_prereq_crossreview_glm.md`
**被审**：`git diff 16b247b..e9e5d95`（vision_resize.py 新增 / isolation.py / cv_toolbox tools.py / 4 份 skill 文档 / 14 把锁 / 3 处有意推翻）
**方法**：全部结论基于实跑与独立 neuter（git worktree 到 `/tmp/neuter_707`，四向 neuter，⛔ 零仓库文件改动；结束时 `git worktree remove` 清理，仓库状态与审前一致）。

---

## 总裁决：**CHANGES REQUIRED（0 BLOCKER / 2 MAJOR / 2 MINOR）**

三件修法主体**全部成立**，14 把锁**全部真绑**（独立 neuter 复核，见附录）；三处推翻均为「断言新语义 + docstring 记旧语义 + 反向防回潮」，**无一处净放宽**。
两条 MAJOR 都不是「跑不出分」，而是**开抽后分数归因可信度**的缺口——恰好落在请求书 §1 的红线（「如果这三件里有错，下一次抽出来的分数无论好坏都不可信」）上：
- **MAJOR-1**：跨轴出口的三个信号零机器消费者（§2.2 怀疑**坐实**）；
- **MAJOR-2**：「留 null 不算自检失败」的文档与门已字面打架，且施工席的结转理由漏了更重的半边（v3 typed 判卷 null ⇒ plan 通道结构性零分，**与档位无关**）。

**开抽前最低修补建议**（我的建议，拍板权在 orchestrator/用户）：MAJOR-1 至少同步 `cv_toolbox.md:113` 那句 raise 时代的旧句 + 给 attempts/判卷侧车补一行 disagreement 聚合；MAJOR-2 至少把 guide.md 那句「not itself a self-check failure」改为如实描述门行为。两者都是文档/记账级小改，不动修法本体。

---

## §2.2 ⭐⭐⭐ 跨轴出口三信号的消费者 —— **MAJOR-1**

**事实（全仓 grep + 读码）**：
- `axis_calibration_disagreement`、`cross_axis_disagreement`、`metric_confidence` 在 `src/` 的引用**全部位于 `cv_toolbox/tools.py` 内部**（定义、置位、驱动 confidence 降级、写进 metric/summary）。
- `src/validator/`（gate①）对 `cv_evidence|metric_confidence|axis_calibration|cross_axis` **零引用**（实测 grep 空）。
- `src/agent/judge/`（判卷）同样零引用。
- merge 链路只搬运 **prescan** 的 cv_evidence（`isolation.py:782-787`），工具运行时证据不进 attempts 账本。
- **唯一真实的消费面 = 读图器自己**：`run_cv_probe.py` 在 rc=0 时把**完整 sidecar JSON（含 warnings guidance 全文、confidence、flag）打印到 stdout**（`isolation_templates/run_cv_probe.py:296-308`），读图器默认视野内。但这是**自愿性**消费——没有任何确定性机制强制它响应。

**与旧形态的实质对比**：旧 raise ⇒ F-54 捕获 ⇒ **rc=2 + stderr**——agent 无法忽略的失败信号（尽管旧形态同样没有机器消费者，它的「消费者」是读图器被迫看见失败）。新出口 rc=0 = 工具「成功」。本仓判据「一个不与行为绑定的声明 = 带变量名的注释」适用面：`axis_calibration_disagreement` flag 与 `metric_confidence="low"` 两个字段就是带变量名的注释——它们对产物、账本、判卷的任何路径都不可见。

**具体后果**：一份用了 disagreement 标定的 reading，blend 出的 px_per_m 原样进产物、进分数。开抽后若分数差，**账面上无法区分「模型没量」vs「量了、被工具明确标了 low confidence、仍用了那个值」**——F-49 式错误归因（把工程缺口记到模型头上）的温床，且这次连「事后查侧车」都查不到全貌（证据不进 attempts）。

**减轻项（如实记录）**：guidance 文本醒目且含具体 next-step（"re-crop and re-measure…recalibrate"）；修法动机（F-34：raise ⇒ 模型放弃标定退回目测）成立且是本仓已确立的判据（立规则不给合法出口 ⇒ 发明出口）；0.3% 判据本身仍在计算、仍可见。

**定级理由**：非 BLOCKER——修法是有意决策、非静默撤门（旧门也从未有机器消费者）；但「两个结构化信号 + 判卷/provenance 零接线 + skill 文档仍教旧 raise 语义」三件事叠加，使这道门从「强制可见的失败」退化为「寄望于 VLM 自觉的提示」，且在「这批过了就开抽」的语境下直接威胁归因可信度。

**附带（并入本条修法）**：`skills/intake_pipeline/0_reading/cv_toolbox.md:113` 仍写着 *"A cross-axis disagreement **error** means … do not average or reuse that result"*——此句来自 `421c9d3`（07-31 raise 时代），**本批改掉 raise 时未同步**。文档教读图器认识一个不再存在的 error，且「do not average」与实现「把 blend 值作为主返回」直接矛盾。读图器唯一的上游说明书与工具行为脱节。

**可复现**：
```bash
grep -rn "axis_calibration_disagreement\|cross_axis_disagreement" --include="*.py" src/ | grep -v "cv_toolbox/tools.py"   # 空
grep -rn "cv_evidence\|metric_confidence\|axis_calibration\|cross_axis" --include="*.py" src/validator/                    # 空
git log -1 --format="%h %s" -S "A cross-axis disagreement error means" -- skills/intake_pipeline/0_reading/cv_toolbox.md   # 421c9d3
```

---

## §2.5 ⭐⭐⭐ scale_origin —— **MAJOR-2**（文档与门已打架 + 结转理由不完整）

**① 下一抽实际跑哪个 profile（实测，非采信请求书）**：最近 9 个 reading 复现 run（`run_2026-08-15_reading_restart_A1..D1`、`run_2026-08-16_B1_pilotgate_G1/G2`、`run_2026-08-16_reading_restart_E1_uncapped`）的 `_run/run_policy.json` **全部 `run_profile: exploratory`**；`G1/run_config.yaml` 确认读图模型 = `claude-haiku-4-5-20251001`、judge off、判卷单独做。07-07 复现开抽走同形态 ⇒ **exploratory**。

**② 该档下门会不会 block**：不会。`_plan_scale_origin` 对 null 记 **FAIL fact**（`reading.py:1025-1039`），`disposition()` 对 plan_frame 检查在 `_PLAN_FRAME_PERMISSIVE_PROFILES = {"exploratory","dev"}` 下判 **FLAG**（`schema.py:79,255-258`）⇒ 施工席「exploratory 档不 block、够本批用」**在 sm21 复现场景成立**。且我核实 **sm21（v2 gt）走 legacy 判卷，`reading_score.py`/`correction_score.py`/`elevation_score.py` 对 scale_origin 零读取** ⇒ null 对 sm21 的分数零影响。

**③ 但文档与门已经打架（本批内事实，非结转）**：guide.md 自检清单新句 *"omitting it is not itself a self-check failure"* vs gate① 对同一行为记 **FAIL**（exploratory 下降为 FLAG，但 `checks.json` 里它是一条 FAIL fact，judge/汇报侧看到的就是 FAIL）。「不算失败」与「门记 FAIL」字面矛盾——且在 golden/regression 档下该 FAIL 直接 **BLOCK**：文档在教读者走一条 acceptance 档必死的路。

**④ 施工席结转理由漏了更重的半边**：其理由只写了「exploratory 不 block / golden-regression 结转」。但 `_plan_scale_origin` docstring 与 `reading_typed_adapter.py:431-460` 实测：**v3 typed 判卷**（sm24/sm25 及未来 case）对 null scale_origin ⇒ `reason="plan_frame_unavailable", denominator_disposition="retain_as_miss"` ⇒ **plan 通道整体按 miss 计，与 run_profile 无关**。「拿不准留 null」在 v3 case 上是**合法地考结构性零分**——比「golden 档会 block」更容易被忽视，因为它永远不炸、分数直接归零。若后续复现/回归扩展到 sm24（07-07 的 8/8 也在 sm24），本批文档直接埋掉 plan 通道。

**可复现**：
```bash
for d in case_tests/e2e_tests/sm21_anchor/run_2026-08-1[56]*/_run/run_policy.json; do python -c "import json;print(json.load(open('$d'))['run_profile'])"; done   # 全部 exploratory
sed -n '431,460p' src/agent/judge/reading_typed_adapter.py        # null → plan_frame_unavailable → retain_as_miss
grep -n "omitting it is not itself a self-check failure" skills/intake_pipeline/0_reading/guide.md
```

**定级**：MAJOR（非 BLOCKER：sm21+exploratory 的开抽路径真实无害；修法方向本身——把「必填+跨层内角推理」这个从未被测过、且与同文档「no world placement」总则矛盾的语义撤掉——是**对的**，向 07-07 实际行为对齐）。要求：文档句如实化（说明 null 在 gate① 的真实待遇 + v3 判卷后果），结转登记补 typed 判卷半边。

---

## §2.1 ⭐⭐⭐ 缩放档位与模型的一致性 —— **MINOR-1**（怀疑的「无约束」坐实；「配错即复活」在当前代码形态下不成立）

**事实**：
- `VISION_RESIZE_TIERS`（standard 1568/1568 · high_res 2576/4784）与档位选择**不从 model id 推导**；`build_isolation_workspace(vision_resize_tier=None→standard)`。
- **tier 没有任何入口**：`spawn_isolated_reader.py` 的 `build` 子命令**不暴露** `--vision-resize-tier`；`llm.yaml`/`run_config.yaml` 无 vision 字段（grep 实测）。全仓唯一调用方 = `isolation.py` 内部。
- `spawn_command` 的 `--model` 是自由参数，与 build 时的 tier **零耦合**——build（定帧）与 spawn（定模型）是两个独立子命令，无一致性检查、无锁。请求书问「档位是从模型 id 推导的，还是自由参数」——**两者都不是：是一个无入口的内部默认**。

**方向分析（对请求书 BLOCKER/MAJOR 预判的证伪）**：
- 模型升 4.7+（high_res 档模型）+ 默认 standard 预缩：预缩后 1377×868 已在 high_res 双上限内 ⇒ API **不再缩** ⇒ 帧一致，仅丢分辨率。**无害**（此方向自动可达）。
- tier 配 high_res + standard 档模型（帧错位复活方向）：需要有人改代码/加参数才能把 tier 传成 high_res ⇒ **当前结构上不可达**。
- 非 Anthropic 读图器（codex 侧 gpt-5.4-mini 等）：API 无此缩放，模型看到的 = 盘上预缩帧 ⇒ 帧一致。

**定级理由**：无锁、无绑定属实（请求书怀疑的核心成立）；但「配错方向会让帧错位复活且无门会红」的前提「可配错」在当前入口面不成立，故降为 MINOR。`vision_resize.py` 注释自陈 "a caller selects a tier by name" ⇒ 未来接线（spawn 加 `--vision-resize-tier`）是设计内预期，届时错配复活。**建议**：spawn/build 时把 tier 写进 staging binding，spawn_command 按 model id 前缀断言档位一致（claude-4.7+/claude-fable/claude-opus-5 ⇒ high_res，其余 ⇒ standard），配一把锁。

**可复现**：
```bash
grep -rn "vision_resize_tier\|vision_resize" --include="*.py" src/ scripts/ | grep -v "src/agent/execution/vision_resize.py\|src/agent/execution/isolation.py"   # 空
sed -n '20,30p' scripts/tool_scripts/spawn_isolated_reader.py    # build 无 tier 参数
```

---

## §2.3 F-51 算法与官方规则逐格一致性 —— **MINOR-2**（实现逐格正确；半数进偶无锁）

逐项核验结果：
- **A4 自检**：`tests/test_f51_single_frame.py::test_resized_size_matches_anthropic_doc_worked_example` 真跑；我独立复算 `resized_size(1075,1520) == (924,1307)` ✓（含递归转置处理 height>width 的正确性）。
- **双上限**：`fits()` 同时检查长边 pad-to-28 ≤ max_edge、短边 pad-to-28 ≤ max_edge、`count_image_tokens ≤ max_tokens` ⇒ **两个上限都查**，binary search 沿长边找最大可行尺寸 ✓（非「只按长边缩」）。
- **无 pad**：`resize_image_file_to_tier` 只 resize 不 pad，返回 pre-pad 尺寸，docstring 明确「convert using the RESIZED size, never the padded size」✓。tier 内图 byte-for-byte no-op（LANCZOS 仅在真缩时用；P 模式先转 RGB 的处理与 cv_toolbox 既有惯例一致）✓。
- **半数进偶**：实现用 Python `round()`（banker's，half-to-even）= 文档口径，**实现正确**。但 **A4 例的短边 924.36 不经过 `.5`**，1f/2f 目标（1377×868/1400×846）也不经过 ⇒ **`.5` 边界零锁**。N4 实测（见附录）：把 round 换成 half-up（`Math.round` 式"修复"）后 **全部现有锁零红**（3 passed），而存在真实可区分案例——`(408,289)@max_tokens=160`：banker's `(396,280)` vs half-up `(395,280)`，长边差 1px ⇒ 帧错位 1px 且无门。**建议补一把该形状的边界锁**（用 `resized_size(w,h,max_edge=…,max_tokens=…)` 直接构造即可，无需新夹具）。

---

## §2.4 预缩是否打断别的链路 —— **PASS**（施工席声称独立复核全部属实）

| 声称 | 独立核实 |
|---|---|
| MANIFEST 哈希在缩放后算 | ✓ `_copy_case_data_image`：copy2 → resize → `_add_manifest_entry`，而 `_add_manifest_entry` 算 `hash_file(dest)`；锁 4 断言 = 盘上字节重算的 sha256 |
| merge/attempt 归档不记原图尺寸 | ✓ `merge_isolated_output` 只搬产物 JSON + 身份对账（run_id/view_manifest_sha256/case_metadata，均绑**仓库原图**） |
| 渲染链无原图尺寸依赖 | ✓ `render_vector_to_png.py` 等全是白纸矢量渲染，固定 `SCALE=45 px/m`，不叠底图、不读图尺寸 |
| 无缓存/硬编码旧 px_per_m | ✓ `px_per_m` 在 `src/` 除 cv_toolbox 外零引用；cv_toolbox 内每次调用现算，无跨调用状态 |
| 仓库原始 case 图未动 | ✓ 锁 3（git diff --stat 对 case_data）+ 我跑测试前后 status 一致 |
| view_manifest / 判卷哈希不受影响 | ✓ 判卷与 exam-scope 守卫绑 base manifest（仓库原图哈希），原图未动 ⇒ 不变 |

唯一记录帧的地方 = 工具 sidecar 的 `width_px/height_px` = staging 缩后帧——这正是修法目的（模型/磁盘/cv_probe 同帧）。`_copy_case_data` 对 `testdata_prompt.json` 走不缩的 `_copy_file`（非图像）✓。

---

## 三处有意推翻 + 14 锁的质量核验

**三处推翻**：全部为「断言新语义 + docstring 完整记录旧语义与推翻理由 + 反向断言防回潮」：
1. `test_cv_toolbox.py`：raise 锁 → 合法出口锁（双向：agreeing→high/无 warning；disagreeing→flag/low/warning/px_per_m>0）；
2. `test_reading_schema.py`：逐字锁 → 语义锁（正向 8 + 反向 6，覆盖 guide/pens/kickoff 三文件；旧断言中两条示例字面量被有意不保留，理由成立——它们本来就不承重）；
3. `test_substrate_sweep_tools.py`：`(1345,2133)→(868,1377)`，仍是精确 pin，docstring 讲明 numpy H×W 转置。**无一处净放宽。**

**执行日志对账**：作者自陈「neuter 自证 4/4 + 独立脚本核实 + 还原确认」——与本席四向独立 neuter 结果一致，无夸大。夹具取自 `git show 16b247b:` 入库（不依赖 gitignored backup/）✓。

---

## 附录：四向独立 neuter（worktree `/tmp/neuter_707` @ e9e5d95，已清理）

| # | neuter（改 /tmp 副本，仓库零改动） | 结果 | 判定 |
|---|---|---|---|
| N1 | 摘掉 `isolation.py::_copy_case_data_image` 的 `resize_image_file_to_tier` 调用点（复原缺陷本尊：只 copy 不缩） | **恰好红 3**（平面图锁×2 + 真子进程帧锁），A4/立面/原图/MANIFEST 锁仍绿，零连带 | F-51 接线真绑 ✓（MANIFEST 锁不红是**正确**的：no-resize 形态下哈希与盘上仍一致——它锁「哈希不陈旧」的顺序错误，非「必须缩」） |
| N2b | `tools.py` 的 `axis_calibration_disagreement = True` → `pass`（保留 0.3% 检测、保留 warnings 种子、保留 blend 返回——「检测仍在、信号半静默」退化） | **恰好红 2**（库层锁 + 真入口正例锁），agreeing 对照绿，零连带 | 出口信号真绑 ✓——锁锁的是信号，不只是「不炸」 |
| N3 | guide.md 的 `SHOULD` → `MUST`（旧语义回潮） | **恰好红 1**（语义锁），其余 9 绿 | 防回潮锁真绑 ✓ |
| N4 | `vision_resize.py` 三处 round → half-up（`Math.round` 式误"修复"） | **零红（3 passed）**；区分案例 (408,289)@160 下 banker (396,280) vs half-up (395,280) | **锁网盲区坐实** ⇒ MINOR-2 |

测试实跑：`tests/test_f51_single_frame.py + tests/test_cross_axis_exit.py` = 14 passed；`test_cv_toolbox + test_reading_schema + test_substrate_sweep_tools` = 86 passed。

---

## 派工方证伪记录（请求书错误率 29/29 → 本单新增 1 条实锤 + 1 条部分）

1. **§2.1 部分证伪**：「配错方向会让帧错位复活且无门会红」——「无绑定、无锁」属实；但**危险方向（tier=high_res + 标准档模型）当前从任何入口不可达**（tier 无 CLI/config 面），自动可达的唯一错配（模型升 4.7+）是丢分辨率、帧仍一致。按实测定 MINOR，非 BLOCKER/MAJOR。
2. **§2.2 坐实**：三信号零机器消费者（本单 MAJOR-1）。
3. **§2.3 四子问**：A4 真跑 ✓；半数进偶实现正确**但请求书点出的这条边界确实无锁**（本单 MINOR-2，新增 half-up 零红的实证）；双上限都查 ✓；无 pad ✓。
4. **§2.4**：施工席「作者自证」本次**未被证伪**——独立复核六项全部属实。
5. **§2.5①②**：「下一抽跑哪个 profile 别信我说的」——实测 exploratory、不 block，施工席判断成立；**③「文档与门是否打架」——请求书预判正确**，且实际比请求书写的更重（typed 判卷半边，见 MAJOR-2④）。
6. 请求书其余数字核验：14 把锁 ✓（11+3，实测 14 passed）；「作者 grep 零处依赖原图尺寸」✓ 独立成立。
