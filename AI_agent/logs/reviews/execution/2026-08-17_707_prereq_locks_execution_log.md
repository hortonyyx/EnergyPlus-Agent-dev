# 707 前置收尾 —— 两把锁入库 + 三处推翻断言改写 执行日志

- 日期：2026-08-17
- 分支：`6.15_ValidationArchM0toM4`
- 派工来源：本轮对话内派工（「707 前置收尾」施工席）
- 施工席位：执行档（Claude Sonnet 5 子代理）
- 背景改动（已合库，本摊不改动其一字节）：`723b5c6` Merge `707_prereq_wip`
  （父提交 `0ae4b93` 08.17_707repro_prereq_F51_singleframe_scaleorigin_crossaxis_exit +
  `805381e` 08.17_TestEngineeringFix_M1_M2_and_reading_scope_banner）——
  F-51 单帧化（`src/agent/execution/vision_resize.py` 新增 + `isolation.py` 接线）、
  `scale_origin` 从平面图必填挪走（3 文件）、跨轴校验补合法出口（`tools.py::px_m_calibrator`）。
- 本摊现成材料：`/tmp/.../scratchpad/lock_f51.py`（12 项检查，标准脚本）+
  `lock_c1.py`（11 项检查，标准脚本）——逻辑已由施工那摊验证过，未搬进 `tests/`。

---

## 0. 任务边界（原样引用派工，供审计对照）

两件事：① 把 `lock_f51.py` / `lock_c1.py` 的检查搬进 pytest、入库，**锁走真实入口**
（真 `build_isolation_workspace` + 子进程跑 staged wrapper，⛔ 不许退化成直接 import 工具函数）；
neuter ⛔ 绝不许覆写仓库真实文件（在 `tmp_path` 副本上做，样板 = `_neuter_into_fresh_staging`）；
⛔ 不许依赖 `backup/`（gitignored，换机器恒红）；官方 A4 自检
`resized_size(1075,1520) == (924,1307)` 必须入锁。
② 更新三处被本次改动**有意推翻**的旧断言（`test_cv_toolbox.py` 跨轴 raise 锁 /
`test_reading_schema.py` scale_origin 逐字锁 / `test_substrate_sweep_tools.py` numpy shape 锁），
每处必须①改成断言新应然语义②docstring 写清旧语义+为何推翻③执行日志逐条列出。
⛔ 不 commit（主控统一提交）。⛔ 不跑 `pip install -e`。真解释器 `/opt/venv/bin/python`。
`src/` 原则上不该动，若非动不可须停下上报。

---

## 1. 落的两把锁

### 1.1 `tests/test_f51_single_frame.py`（新文件，297 行）

覆盖 F-51 单帧化的全部检查面，锚点 case = `case_tests/e2e_tests/sm21_anchor`
（git 跟踪，非 `backup/`）：

| 测试函数 | 对应 lock_f51.py 检查项 | 断言内容 |
|---|---|---|
| `test_resized_size_matches_anthropic_doc_worked_example` | 检查 0（**派工硬要求的那一把**） | `resized_size(1075,1520)==(924,1307)`，官方文档自带样例，纯函数、不依赖真实入口 |
| `test_plan_view_staged_at_vision_resize_target_and_actually_shrunk`（parametrize ×2：1f/2f） | 检查 1+2 | 真 `build_isolation_workspace` 后，staged 图尺寸 **同时**核对①现算 `resized_size_for_tier(*orig_size)`②本锚点硬编码真值（1f: `(1377,868)`、2f: `(1400,846)`）③确实被缩小（≠ 原尺寸） |
| `test_elevation_round_trips_byte_identical_when_already_within_tier`（parametrize ×4：东南西北） | 检查 3 | 四张立面已在档位内 ⇒ staged 副本与原图逐字节相同（sha256 对比），零缩放非静默重编码 |
| `test_repo_original_case_data_untouched_by_staging_build` | 检查 4 | `git diff --stat -- case_tests/.../case_data/` 空，防「缩放误改了 src 而非 dest」这类一变量之差 |
| `test_manifest_records_hash_of_resized_bytes_not_a_stale_prefix_hash` | 检查 5 | `MANIFEST.json` 记的 sha256 = **缩放后**磁盘字节的哈希，非缩放前残留值 |
| `test_real_cv_probe_subprocess_sees_the_resized_frame_not_the_original` | 检查 6+7（**全锁的题眼**） | 真子进程跑 staged `tools/run_cv_probe.py`，sidecar 里 `source_image.width_px/height_px` = `(1377,868)`，不是原始 `(2133,1345)` |
| `test_neuter_cutting_the_resize_wiring_reproduces_the_original_frame_mismatch` | （原脚本没有，本摊新增） | neuter：monkeypatch 切断接线，确认 staged 尺寸与 cv_probe 看到的尺寸都回退到未缩放原值 |

**与原脚本的差异**：① `REPO` 路径改用 `Path(__file__).resolve().parents[1]`（本仓路径，不再指向
`/workspaces/ep_707_prereq` 那个平行 worktree）；② `tempfile.mkdtemp` 换成 pytest 的
`tmp_path_factory`/`tmp_path`（自动清理、天然在仓外）；③ 每个 `check()` 展开成独立
`assert` + parametrize，失败时 pytest 报告更精确；④ 逐个 PLAN_VIEW 尺寸**同时**核对现算值与硬编码值
（脚本原文只核对现算值），见 §3 关于「硬编码 ground truth」的说明。

### 1.2 `tests/test_cross_axis_exit.py`（新文件，237 行）

覆盖 C1 跨轴合法出口的全部检查面，同一锚点 case：

| 测试函数 | 对应 lock_c1.py 检查项 | 断言内容 |
|---|---|---|
| `test_disagreeing_anchors_get_a_legal_exit_not_a_crash` | 检查 1（**题眼**） | 真子进程跑不一致锚点，returncode==0（非 raise）；`axis_calibration_disagreement=True`；
`metric.confidence=="low"`；`warnings[]` 含 `cross_axis_disagreement` 且 guidance 文本含
"re-crop and re-measure" + "recalibrate"；`px_per_m` 仍是正的有限数；`axis_px_per_m` 双轴俱全 |
| `test_agreeing_anchors_are_unaffected_by_the_cross_axis_exit` | 检查 2（反向对照） | 一致锚点下行为与改动前完全一样：flag False / confidence high / 无 warnings |
| `test_neuter_reverting_the_legal_exit_reproduces_the_original_raise` | （原脚本没有，本摊新增） | neuter：把 staged 副本的 `tools.py` 换回改动前内容，确认原始 raise 重现 |

**与原脚本的差异**：同 §1.1 的路径/tmp_path 调整；另外 `_run_calibrator` 改为每次分配唯一
`out/c1_<label>_<NNNN>` 目录（原脚本硬编码 `out/c1_lock` + 两个不同 sidecar-name），
避免与本仓默认 `-n auto` 并行时的目录复用假象。

### 1.3 配套 git 跟踪 fixture：`tests/fixtures/cross_axis_exit/`

C1 的 neuter 需要「改动前」的 `tools.py` 全文内容。**没有走 `backup/`**（那是 gitignored、
换机器恒红的路——`tests/fixtures/substrate_fix_II/README.md` 已记录过这个坑），
而是直接从 git 历史取：

```
git show 16b247b:src/agent/reading/cv_toolbox/tools.py > tools_pre_fix.py
```

`16b247b` 是 `0ae4b93`（引入 C1 的提交）的直接父提交（`git show 0ae4b93 --no-patch --format="%P"`
核实），`git diff 16b247b HEAD -- src/agent/reading/cv_toolbox/tools.py` 即此 fixture 逆转的
完整、准确的 diff。`README.md` 记录了取值命令与理由。

---

## 2. 三处推翻断言的改写

### 2.1 `tests/test_cv_toolbox.py::test_px_m_calibrator_rejects_cross_axis_anisotropy_before_blending`

**旧语义**：跨轴相对偏差超过 0.3% ⇒ `px_m_calibrator` 必须 `raise ValueError("cross-axis
calibration disagreement...")`，在 blend 之前抛出，无合法出口。

**为何推翻**：本仓判据「立规则不给合法出口 ⇒ 模型自己发明出口」——
`AI_agent/logs/experiments/2026-08-16_707_repro/behavioral_change_inventory.md` §C1
记录了这条硬 raise 的真实后果 F-34：读图器放弃像素标定、退回目测，比一个降置信度的数字更差。

**改成什么**：改名为 `test_px_m_calibrator_flags_cross_axis_disagreement_with_a_legal_exit_not_a_raise`，
断言：一致锚点（accepted）分支完全不变（含新增的 `axis_calibration_disagreement is False` /
`confidence=="high"` / `warnings==[]` 三条，把「新行为对旧路径零副作用」也钉进锁里）；
不一致锚点分支不再 `pytest.raises`，改为断言 `axis_calibration_disagreement is True` +
`confidence=="low"` + `warnings[]` 含 `cross_axis_disagreement` 且 guidance 文本可操作 +
`px_per_m` 仍返回正数。docstring 完整写明旧语义/新语义/推翻理由/与
`tests/test_cross_axis_exit.py`（真实入口版）的关系。

**实跑**：`pytest tests/test_cv_toolbox.py -k cross_axis -q` → `1 passed`。

### 2.2 `tests/test_reading_schema.py::test_plan_scale_origin_is_a_locked_reader_instruction_contract`

**旧语义**（逐字节锁死的多行字符串）：`guide.md` 必须含
`'Every plan view\n    **must** declare `scale_origin`'`，且该字段值须为「整栋跨层投影最大边界
的 **内** 角」（隐含要求判墙厚 + 判跨层投影），`pen_library.md` 必须写「mandatory container
action」+「all floors share that datum」。

**为何推翻**：该旧要求本身与 `guide.md` §1 的治理原则「reading 阶段 does NO world placement」
直接矛盾（判「内角」需要先判墙厚——本项目「标注/墙厚/出模」专项**尚未解决**的题；判「整栋跨层投影
最大边界」需要跨图聚合，属越界的世界坐标落位）。`behavioral_change_inventory.md` §A1 核实：
该旧要求 07-07/07-08 两份已知好产物均未出现过（好产物压根没有这个字段），且在改动引入之前**从来
不是文档规则**——是 707 复现改动本身新加的短命状态。

**改成什么，及为什么锁语义不锁字面（派工特别要求给理由的一处）**：

改名为 `test_plan_scale_origin_is_an_optional_not_mandatory_reader_instruction_contract`。
判断标准：**锁「scale_origin 不是必填」这个语义，而不是锁新句子的字面写法**——理由是旧锁的
真正缺陷从来不是「用子串/精确文本核对文档散文」这个技术手段本身（这是本仓文档契约锁的常规做法，
例如 `tests/test_substrate_fix_tools.py` 的 F-53 段落也这么做），而是**锁错了内容**：锁死了
一句话的精确措辞，这句话恰好编码了一个本身就错误的要求；未来一次单纯的措辞润色（比如把
"SHOULD" 改写成 "may"）就能在契约毫无变化的情况下打破这把旧锁，反过来一次真正的语义回归
（重新要求 must + 跨层判墙厚，只是换了个新句子表达）却能完全绕过一把只认那一句老话的锁。

因此新锁的每条断言都是短的、语义承重的标记词/短语（存在性证明新不变量成立；不存在性证明旧的
错误不变量没有悄悄回潮），而不是整句逐字诗——这样一次保持契约的编辑（改语气词、调段落顺序）
仍然通过，一次破坏契约的编辑（不管用什么新措辞表达"必填"或"跨层判内角"）都会失败。同时把覆盖面
从原来的 `guide.md`+`pen_library.md` 两个文件扩到三个（新增 `session_kickoff.md`）——这不是
范围蔓延，是这次改动本身实际动过的三个文件之一，原锁漏掉了它。

具体断言（`guide = guide.md`，`pens = pen_library.md`，`kickoff = session_kickoff.md`）：

- 字段仍存在（未被误删）：`'"scale_origin"' in guide`，`world_x_m`/`world_y_m`/`world_z_m` 均出现。
- 正向：`"scale_origin: OPTIONAL for every plan" in guide`；
  `re.search(r"plan view SHOULD\s+also declare \`scale_origin\`", guide)`（SHOULD 非 MUST）；
  `"leave \`scale_origin\` \`null\` rather than guess" in guide`；
  `"omitting it is not itself a self-check failure" in guide`；
  `"optional container action" in pens`；`"never guess the field — omit it" in pens`；
  `"is not an exception to that" in kickoff`；`"a plan MAY state" in kickoff`。
- 正向（参照点仅限本图）：`"drawn in THIS SAME image" in guide` 与 `in pens`；
  `re.search(r"never a cross-image or\s+cross-floor judgment", kickoff)`；
  `"never guessed, never a cross-floor judgment" in kickoff`。
- 反向（旧错误要求不得回潮）：`"must** declare \`scale_origin\`" not in guide`；
  `"mandatory container action" not in pens`；
  `"overall projected maximum building boundary" not in guide`；
  `"SW inner corner" not in guide`；`"all floors share that datum" not in pens`。

未沿用的两条旧断言（`'"world_x_m": 0.00' in guide` / `'"world_y_m": 0.00' in guide`）：
它们现在字面仍然为真（§2 schema 示例里那两行还在），但特意不再纳入——它们钉住的是一个
「常见情形」的示例值，从未证明过必填性的存在与否，锁它们对本契约的核心问题（必填 vs 可选）
没有任何鉴别力。

**实跑**：`pytest tests/test_reading_schema.py -k scale_origin -q` → `1 passed`；
整文件 `pytest tests/test_reading_schema.py -q` → `10 passed`。

### 2.3 `tests/test_substrate_sweep_tools.py::test_doc_example_python_dash_c_executes_in_staging`

**旧语义**：doc 里那行 `python -c 'import numpy...Image.open("case_data/1f_view.png")...shape'`
在 staging 里真跑，输出必须是 `(1345, 2133)`（`1f_view.png` 原始 2133×1345 W×H，numpy shape 是
H×W 转置）。

**为何推翻**：不是这条检查的目的变了，是它检查的对象本身的正确值变了——F-51 单帧化让每次
staging 构建都会先把超尺寸的 `case_data/` PNG 缩到视觉 API 自己的目标尺寸，`1f_view.png`
真实尺寸缩放路径是 2133×1345 → 1377×868，所以这个 doc 示例现在**如实**报告的 numpy shape
是 `(868, 1377)`。断言仍是精确相等（不是放宽成「不崩就行」）——只是这个精确值现在是正确值。

**改成什么**：`assert proc.stdout.strip() == "(868, 1377)"`，docstring 补充一段写清旧值/新值/
换算关系（1377×868 是 W×H，numpy shape 是 H×W 故为 `(868, 1377)`）及触发机制指针
（`src/agent/execution/vision_resize.py` + `isolation.py::_copy_case_data_image`，并指向
`tests/test_f51_single_frame.py` 作为该机制的专项锁）。

**实跑**：`pytest tests/test_substrate_sweep_tools.py -q` → `47 passed`。

---

## 3. neuter 自证

两把新锁各自内建了一个 `test_neuter_*` 测试（§1.1/§1.2 表格已列），全部只在 `monkeypatch`
（纯内存属性替换，pytest teardown 自动撤销，从不落盘）或 `tmp_path` 下的 staging 副本
（复制的是新建的 git 跟踪 fixture `tests/fixtures/cross_axis_exit/tools_pre_fix.py`，真实仓库
文件从未被写过）上操作，符合「⛔ 绝不许覆写仓库真实文件」的硬要求。这两把在本轮正常跑（§4）里
本身就是绿的（因为它们的断言本来就是"中和后应重现旧行为"）。

为了不止依赖"锁内部逻辑自洽"，额外做了一轮更直接的验证：把两把正向锁自己断言的**期望值**直接
放到被中和的场景下求值，观察它们是否真的翻红（而不是仅仅相信 neuter 测试内部的对照逻辑）。
脚本 `/tmp/.../scratchpad/neuter_self_cert.py`（不在仓库内，纯验证工具）：

- F-51：monkeypatch `src.agent.execution.isolation.resize_image_file_to_tier` 为一个只读
  `Image.open(path).size`、不做任何缩放的直通函数（等价于 F-51 这行接线从未存在过），
  然后跑真 `build_isolation_workspace` + 真子进程 cv_probe 调用。
- C1：把新建的 `tmp_path` staging 里 `tools.py` 的**副本**换成
  `tests/fixtures/cross_axis_exit/tools_pre_fix.py` 的内容（真实仓库文件全程未碰），
  跑真子进程 `px_m_calibrator` 调用。

实测输出（4/4 全部翻红）：

```
RED (expected)  : F-51 positive: staged 1f_view.png size == resized target (1377, 868)
                  -> staged_size=(2133, 1345) != (1377, 868) [neutered]
RED (expected)  : F-51 positive: real cv_probe subprocess reports resized frame (1377, 868)
                  -> got=(2133, 1345) != (1377, 868) [neutered]
RED (expected)  : C1 positive: disagreeing-anchor subprocess exits 0 (legal exit)
                  -> returncode=2 stderr='run_cv_probe.py: error: cross-axis calibration
                     disagreement: x=37.5 px/m, y=40.9 px/m, relative_deviation=8.673469%
                     exceeds 0.300000%; verify dimension extension-line intersections\n'
                     [neutered]
RED (expected)  : C1 positive: a sidecar with axis_calibration_disagreement=True was written
                  -> no sidecar written at all -- the raise fired first [neutered], stderr=...
4/4 positive checks correctly went RED under neuter.
```

**一处意外但正确的细节**（写进了 `tests/test_cross_axis_exit.py` 的 neuter 测试 docstring）：
单独中和 C1（把 `tools.py` 换回旧版）后，重现的**不是**裸 traceback，而是干净的 `exit code 2`
+ 原始 raise 消息文本——因为同批改动里独立、未被本摊中和的 F-54 修复（`run_cv_probe.py` 的
`try/except (ValueError, OSError)` 兜底）仍然在场，而 `px_m_calibrator` 的旧 raise 恰好是
`ValueError`，落在 F-54 的捕获类型里。这与 `tests/test_substrate_fix_tools.py` 的
`test_f58_neuter_...`（`AttributeError` 不被 F-54 捕获，裸 traceback 重现）恰好是相反的对照，
两者合起来证明 F-54 的兜底是按异常类型选择性生效、不是全兜底——如实记录，不是我的猜测，是
`neuter_self_cert.py` 实跑观察到的。

**还原确认**：`neuter_self_cert.py` 运行前后 `git status --short` / `git diff --stat`
完全一致（只有 §0 列出的 6 项预期改动，`src/`、`skills/`、`scripts/` 零改动）——因为该脚本
自身从不写任何仓库路径（monkeypatch 是内存操作，C1 那半用的是独立 `tempfile.mkdtemp`，运行
后 `shutil.rmtree` 清理），没有"覆写后再还原"这一步的必要，天然零残留。

---

## 4. 新文件连跑 3 轮（默认并行，不加 `-n` 参数）

```
$ /opt/venv/bin/python -m pytest tests/test_f51_single_frame.py tests/test_cross_axis_exit.py -q
=== ROUND 1 === ..............  [100%]  14 passed in 20.65s
=== ROUND 2 === ..............  [100%]  14 passed in 20.79s
=== ROUND 3 === ..............  [100%]  14 passed in 18.19s
```

三轮零红，走的是 `pyproject.toml` 的 `addopts = ["-n", "auto", "--dist", "load"]` 默认并行形态
（未额外传 `-n4` 或任何覆盖——派工特别提醒过 `-n4` 在本机撞不出竞态、是一道不会变红的门，
本仓默认 `-n auto` 才是唯一权威并发形态）。

---

## 5. 全仓数字

**改动前基线**（本摊开工前、任何编辑之前跑的独立全量，674.62s）：

```
FAILED tests/test_cv_toolbox.py::test_px_m_calibrator_rejects_cross_axis_anisotropy_before_blending
FAILED tests/test_mep_idd_field_alignment.py::test_b2_prescan_reproduction
FAILED tests/test_substrate_sweep_tools.py::test_doc_example_python_dash_c_executes_in_staging
FAILED tests/test_reading_schema.py::test_plan_scale_origin_is_a_locked_reader_instruction_contract
4 failed, 2816 passed, 14 xfailed, 212 warnings in 674.62s
```

与派工单描述的「全量现在 4 failed」「passed 数应比 2816 更高」的起点数字逐字吻合，未发现偏差。

**本摊改动范围的组合验证**（三处改写文件 + 两把新锁文件 + 唯一应保留的旧债文件 +
`_neuter_into_fresh_staging` 样板参照文件，一并跑）：

```
$ pytest -q tests/test_cv_toolbox.py tests/test_reading_schema.py \
  tests/test_substrate_sweep_tools.py tests/test_f51_single_frame.py \
  tests/test_cross_axis_exit.py tests/test_mep_idd_field_alignment.py \
  tests/test_substrate_fix_tools.py
1 failed, 133 passed, 1 warning in 48.95s
FAILED tests/test_mep_idd_field_alignment.py::test_b2_prescan_reproduction
```

唯一失败即 F-36 旧债（`test_b2_prescan_reproduction`），派工明令不动，本摊全程未碰
`test_mep_idd_field_alignment.py` 及其依赖的任何生产代码。

**⛔ 全仓 `-n auto` 权威跑测**：本摊未再跑（主控已声明在跑权威全量，避免重复烧算力/竞态）。
基于「改动前基线 4 failed」+「本摊组合验证仅剩 F-36 一处失败、其余全新增/全翻绿」这两组独立证据，
预期全仓权威结果为 **1 failed（仅 F-36）/ passed 数 = 2816 − 3（三处旧失败翻绿不增加 passed 计数，
它们本来就在 2816 之外的 failed 里）+ 3（三处翻绿转入 passed）+ 14（本摊新增锁：F-51 11 项 +
C1 3 项）= 2833 passed / 14 xfailed**。此为推算值，最终以主控独立全量为准。

---

## 6. 证伪掉的派工前提

逐条核对派工单里可核验的具体断言/数字，如实登记：

1. **「全量现在 4 failed」「passed 数应比 2816 更高」**——核实**成立**，改动前独立全量精确复现
   `4 failed, 2816 passed, 14 xfailed`，与派工描述逐字一致，未证伪。
2. **「官方 A4 自检 `resized_size(1075,1520) == (924,1307)` 必须是其中一把锁」**——已落实为
   `test_resized_size_matches_anthropic_doc_worked_example`，成立、已执行，未证伪。
3. **「锁『scale_origin 不是必填』这个语义，比锁新措辞的字面更耐用，给理由」**——核实这条判断
   本身经得住推敲（§2.2 已详细论证），采纳、未证伪；唯一补充是把覆盖文件从判断里暗示的
   guide.md+pen_library.md 两个扩到三个（session_kickoff.md 也是这次改动动过的文件），
   这是对派工意图的忠实执行、不是对其判断的证伪。
4. **F-54 与 C1 的交互（本摊自行发现，非派工前提，但值得单独指出）**：C1 单独 neuter 后不会
   重现裸 traceback，而是 F-54 兜底接住后的干净 `exit 2`——这不是派工单断言的内容（派工单没有
   对此下过判断），是施工过程中通过 `neuter_self_cert.py` 实跑发现、并据此把
   `tests/test_cross_axis_exit.py` 的 neuter 测试期望值写对（若未实跑、凭直觉写成"应重现裸
   traceback"会是一把从第一次运行就失败的假锁）。

未发现派工单中的其余具体数字/路径/技术判断有误——64 段任务描述中可核验的部分均属实。

---

## 7. 涉及文件清单（均为绝对路径）

新增：
- `/workspaces/EnergyPlus-Agent-dev/tests/test_f51_single_frame.py`
- `/workspaces/EnergyPlus-Agent-dev/tests/test_cross_axis_exit.py`
- `/workspaces/EnergyPlus-Agent-dev/tests/fixtures/cross_axis_exit/tools_pre_fix.py`
- `/workspaces/EnergyPlus-Agent-dev/tests/fixtures/cross_axis_exit/README.md`
- `/workspaces/EnergyPlus-Agent-dev/AI_agent/logs/reviews/execution/2026-08-17_707_prereq_locks_execution_log.md`（本文件）

修改：
- `/workspaces/EnergyPlus-Agent-dev/tests/test_cv_toolbox.py`
- `/workspaces/EnergyPlus-Agent-dev/tests/test_reading_schema.py`
- `/workspaces/EnergyPlus-Agent-dev/tests/test_substrate_sweep_tools.py`

未改动（`src/`、`skills/`、`scripts/` 全程零 diff，逐次 `git diff --stat` 核实）。

未 commit（遵纪律，交主控统一提交）。
