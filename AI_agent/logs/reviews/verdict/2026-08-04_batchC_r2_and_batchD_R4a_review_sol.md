# 批 C r2 + 批 D/R4-a · sol 独立交叉对抗复核

> **状态：本文最终版**
>
> 日期：2026-08-04 · 复核席：sol（GPT 侧） · 被复核施工：Claude 侧

## 0. 总判定

**REWORK。** 核心检测在真实图像尺寸上对原始 `[360,450]` 坏载荷零信号，直接击穿 S-1/S-2；在修正判定基准、补真实尺寸锁并完成独立复核前，不应解除“不得发布识图分数/变好变坏结论”的硬约束。

| 严重级别 | 数量 | 条目 |
|---|---:|---|
| BLOCKER | 1 | B-1：可信 bounds 把源图 px 宽高直接当米制 reading 坐标上界，真实图幅放行原始坏载荷 |
| MAJOR | 2 | M-1：reading_mode 冻结晚于 reading、同 run 可 controlled→autonomous 改账，且独立记录 CLI 仍宽松；M-2：源图不可解码时 per-stem 静默 fallback、coverage 仍通过 |
| MINOR | 1 | m-1：Batch D 内部标签仍碰撞/截断且删除标签测试全绿 |
| NIT | 0 | — |

收口前至少需要：

1. 用量纲一致、被产品不可写的 meter-space 基准或独立 unit-anomaly 判据替换 px-as-meter bounds；测试必须覆盖仓库真实 790–3000 px 量级，而不是只用 `2×2 px`。
2. trusted 源图无法解码时 fail-closed，不得按 stem 静默退回产品自算。
3. 将 reading mode 的严格记录条件覆盖所有 baseline/score 记录入口，并把 lane 与实际 spawn/controller/provenance 证据绑定；历史与新 run 要有不可伪造的区分条件。
4. 修复 typed board 内部标签布局/完整文本，并补一条删除标签或制造碰撞即红的锁。

## 1. 复核范围与方法

- 被审对象：批 C r2（`58f9179` → `f7cc1ff`）及已合入当前历史的批 D/R4-a。
- 操作纪律：主树仅写本报告；mutation 只在 `/tmp` 的 `git clone --local --no-hardlinks` 克隆中执行，并显式 `export PYTHONPATH=$PWD`；不读取 `case_tests/test_baseline/gt/`；不在主树运行 `git status`。
- 判定证据：代码/测试 `文件:行`、实际命令、输出摘录与退出码；克隆环境基线红与 mutation 新增红分开记账。

## 2. S-1：可信画幅不能被被测方影响

**结论：不成立（BLOCKER B-1 + MAJOR M-2）。** 来源在正常生产调用中确实不受产品字段撑大，但这个来源本身把图像的 `px` 宽高直接当成 reading 米制坐标的上下界；真实图幅通常远大于坏载荷 `[360,450]`，故正常可信路径会把“像素当米”判为界内并放行。另有独立降级洞：源图 hash/manifest 都合法但图片不可解码时，resolver 静默按 stem 漏掉 trusted bounds，coverage 仍通过，产品字段即可接管基准。

### 2.1 静态调用链证据

- `src/validator/checks/view_manifest.py:92,113-119`：生产聚合检查按 stem 取 `trusted_bounds_by_stem` 并传给每视图检查。
- `src/agent/execution/view_manifest.py:1334-1368`：resolver 从源图读取 `width,height`，原样返回 `(0.0, float(width), 0.0, float(height))`；没有 px→m 变换。
- `src/validator/checks/reading.py:386-439,442-472`：dimension/OCR 的 reading 坐标直接与上述 tuple 比较；只要 trusted bounds 非空，就完全采用它。
- 仓库 `case_data`（未读 GT）实测源图尺寸包括 `sm24 1f_view.png=(790,1111)`、`sm21 1f_view.png=(2133,1345)`、立面最高到 `(3000,1659)`；均足以吞掉 `[360,450]` 这个原始坏载荷。
- 实测命令（主树只读执行，synthetic case 的唯一源图为 `790×1111 px`，走 `build_view_manifest` → `check_reading_stage`，`run_profile=regression`）：

  ```text
  reading.view_manifest_coverage status=pass disposition=info evidence={"expected_output_ids": ["1f_view"]}
  1f_view.reading.ocr_anchors_in_bounds status=pass disposition=info evidence={"bounds": [0.0, 790.0, 0.0, 1111.0]}
  1f_view.reading.dimension_endpoints_in_bounds status=pass disposition=info evidence={"bounds": [0.0, 790.0, 0.0, 1111.0]}
  trusted_bounds= (0.0, 790.0, 0.0, 1111.0)
  blocking_ids= []
  report_passed= True
  ```

这给出了清单要求的具体产品输入与实测输出；不需要触发 fallback，正常生产传入的 trusted bounds 就已使越界检查失去原目标的分辨力。

### 2.2 降级路径对抗输入与实测

命令：在主树只读导入实现、所有 fixture 写入 `/tmp`，以 `manifest 缺失 / stem 错配 / 源图不可解码 / 指纹漂移` 四组输入调用实际 manifest builder/checker；`> /tmp/sol_s1_fallback_probe.log 2>&1; echo $?` ⇒ `FALLBACK_PROBE_EXIT=0`。

| 触发形态 | bounds 子检查 | coverage/总门 | 判定 |
|---|---|---|---|
| `manifest=None` + 产品 `image_bounds=[0,1000]²` | OCR/dimension 均 PASS，采用产品 bounds | coverage FAIL；总 report `passed=False` | 产品可改变子判据，但不能过总门 |
| 正常 manifest + 产品输出错 stem `evil_view` | 该 stem 无 trusted tuple，fallback 后两项 PASS | coverage 同时报 missing `1f_view` + extra `evil_view`；总门拒绝 | stem 绕过失败 |
| 正常 manifest + 源图文件名为 `.png` 但字节不可由 PIL 解码 | resolver 在 `view_manifest.py:1363-1366` 静默 `continue`；产品 extra 撑大后两项 PASS | **coverage PASS；`blocking=[]`; report `passed=True`** | 第二条正常生产 fallback 绕过；manifest 只验 hash、不验可解码图像 |
| provision 后改源图字节，造成 content fingerprint drift | flat-flow 等价路径为 manifest unavailable，产品 fallback 后两项 PASS | coverage FAIL；总门拒绝 | 指纹漂移绕过失败；isolation 更早 raise |

关键输出摘录：

```text
CASE wrong_stem
reading.view_manifest_coverage fail {'missing_expected_output_ids': ['1f_view'], 'extra_stems': ['evil_view']}
blocking=['reading.view_manifest_coverage'] passed=False

CASE undecodable_source_image
reading.view_manifest_coverage pass {'expected_output_ids': ['1f_view']}
1f_view.reading.ocr_anchors_in_bounds pass {'bounds': (0.0, 1000.0, 0.0, 1000.0)}
1f_view.reading.dimension_endpoints_in_bounds pass {'bounds': (0.0, 1000.0, 0.0, 1000.0)}
blocking=[] passed=True

PROVISION fingerprint_drift: ValueError view manifest drift: case_data ... changed after this run was provisioned
CASE fingerprint_drift_flat_equivalent
reading.view_manifest_coverage fail {}
blocking=['reading.view_manifest_coverage'] passed=False
```

因此，对用户特别点名的三种“由产品输出本身触发”尝试，manifest 缺失/错 stem/指纹漂移都被 coverage 或 isolation 外门兜住，证伪失败；但正常可信路径仍有两个实证放行：真实图片量级造成 px/m 误判，以及 manifest 可 hash 但源图不可解码时的 per-stem 静默 fallback。

## 3. S-2：像素化尺寸端点探测

**结论：不成立（与 B-1 同一根因，不重复计数）。** 新检查存在、profile disposition 也接通，但它仅能发现数值超过源图像素宽高的坏端点；原始 `[360,450]` 在正常大小源图上零信号且整个 regression report 通过。

- `src/validator/checks/reading.py:386-439`：检查逐个覆盖 `dimensions[].from/to`，具体 FAIL evidence 与 margin 均存在。
- `src/validator/checks/schema.py:76-84,194-201`：该 check-id 在 `golden/regression` 的 FAIL 会 BLOCK。
- 但上节生产路径实测结果为 `dimension_endpoints_in_bounds status=pass`、`blocking_ids=[]`、`report_passed=True`，已经满足 S-2 的证伪形式“坏坐标形态既不 raise、gate① 也不报”。
- 同一载荷送入现 renderer 的实测输出为 `renderer_size=(6373,7845), pixels=49,996,185, budget=50,000,000`：渲染器按新自适应策略成功返回而不 raise；结合 gate① 的 PASS，两个观测通道确实同时零信号。

## 4. S-3：R4-a 成绩分账

**结论：不成立（MAJOR M-1）。** 不仅独立 `record_baseline.py` CLI 仍宽松，`flow --record` 自己也能被同一 run 绕过：reading 执行时不冻结 mode，执行后把 `run_config` 从 controlled 改成 autonomous，再 record，会以退出码 0 正式记成 autonomous。历史兼容条件也没有可靠地与新 run 区分。

- 严格入口：`scripts/tool_scripts/run_stage.py:2546-2577` 的 `flow --record` 显式传 `require_reading_mode=True`；`tests/test_reading_mode.py:147-175` 走了这条真实入口并断言具体错误与零 baseline 写入。
- 宽松入口：`scripts/tool_scripts/record_baseline.py:485-513` 把同一开关默认成 `False`；其公开 CLI `main()` 在 `:904-928` 调用时没有覆盖默认值。模块头 `:13-16` 仍把该 CLI 作为记录 baseline 的公开 usage。
- `/tmp` 无硬链接克隆实测新建最小 case/run，仅有不含 `reading_mode` 的 `run_config.yaml`，执行：

  ```text
  export PYTHONPATH=$PWD
  python scripts/tool_scripts/record_baseline.py case run \
    --base-dir /tmp/energyplus-sol-review-20260804/tmp_probe_record_cli \
    --date 2026-08-04 --orchestrator sol \
    > .../record_cli_probe.log 2>&1; echo $?

  RECORD_CLI_EXIT=0
  wrote .../run/_run/baseline.json + .../run/report/REPORT.md (blocked=True, run_state=incomplete)
  baseline_exists= True
  reading_mode= {'status': 'legacy_unknown', 'record': None}
  report_exists= True
  ```

  fixture 因未补其他阶段而 `blocked=True`，但关键副作用已经发生：记录入口没有因“新 run 缺 reading_mode”而 fail-closed，且正式 baseline/report 均已落盘。
- 两 lane 的 schema 自洽性本身成立：`src/agent/execution/reading_mode.py:97-125` 拒绝 `autonomous + reading_agent` 与 `controlled + null`；`:233-271` 将只读缺失解析为 `legacy_unknown`，严格 consumer 才 raise。
- 报告标注本身成立：`scripts/tool_scripts/report_assembly.py:765-802` 显示 lane，`dev_function=true` 明示“**不作为正式成绩**”，legacy 不冒充任一 lane。
- **清单要求的具体绕过复现**（`/tmp` clone，真实 `cmd_flow` 两次，draw/check 仅以测试 harness 隔离外部 LLM）：第一次 `run_config` 明确 `lane=controlled` 且 `reading_agent.model=controller-present-during-reading`，完成 0_reading 但不 record；确认 `_run/reading_mode.json` 尚不存在。随后只改 `run_config` 为 `lane=autonomous, reading_agent=null`，同 run 执行 `flow --record`：

  ```text
  LATE_FREEZE_PROBE_EXIT=0
  reading_run_exit= 0
  reading_mode_frozen_after_reading= False
  record_exit= 0
  recorded_reading_mode= {'status': 'present', 'record': {
    'lane': 'autonomous', 'dev_function': False, 'reading_agent': None,
    'reading_worker_agent': {'model': 'worker', 'effort': 'high'}, ...}}
  ```

  这不是伪造内部函数返回，而是施工测试自己认定的真实 `cmd_flow` 入口；它直接证明“实际 controlled 配置下有 reading-agent 在场的执行，最后记成 autonomous”。根因见 `record_baseline.py:507-513`：mode 直到 record 时才 `provision_reading_mode`。
- 全仓也没有可用于事后识别该漂移的独立运行证据：`src/agent/execution/isolation.py:444-469` 的实际 spawn 接受 `model` 与 per-run `directive`，但 `:854-878` 的 attempt provenance 只记 manifest/settings/guard/access-log hashes，不记 spawn model、directive 或 controller presence；读取侧没有与 `reading_mode` 交叉验证。

## 5. S-4：六 panel 判卷图

**结论：不成立（MINOR m-1）。** 六 panel、四档图例、缺失立面占位和“不读产品 mirror/local-x”均成立；但“标签不得互压/裁掉”没有完成，synthetic 四立面 fixture 的 plan claim rails 仍覆盖平面几何，segment id 还被代码主动截成末 10 字符。

- `scripts/tool_scripts/render_grade.py:1301-1313,1406-1417`：typed 路径固定绘制两行四个 N/S/E/W 立面 panel；`:1217-1231` 对缺失/空立面画 hatch + 显式英文占位；`:1164-1190` 绘制 complete/within-tolerance/miss/NA + GT truth 图例。
- `tests/test_batch_d_typed_grade.py:111-145,168-220,227-250` 对六区标题/实际开口色、缺立面占位与不缩 grid、全部图例色作具体像素区域断言；`:147-161` 断言添加产品 `mirrored/local_x_positive` 后整图逐像素相同。
- 主树目标子集实测：`pytest -q -n 4 tests/test_checks_reading_correction.py tests/test_reading_mode.py tests/test_batch_d_typed_grade.py tests/test_render_vector_to_png.py tests/test_reading_renders.py` ⇒ `129 passed, 28 warnings`，退出码 `0`。
- 自造四立面 fixture 实际 render：`size=(948,1292), audit_entries=32`；肉检 `/tmp/sol_batchd_board.png`，四个立面 panel 与标题清楚且互不覆盖，但 F1 plan 底部绿色 claim rails 覆盖 South 边界/标签。
- 这是可由坐标公式复核的确定事实：`render_grade.py:1380-1404` 把 rail 放在 `rail_y=oy+height-18`，每个 opening 只向上错开 20 px；本 fixture panel y=`[100,460]`、几何内区 y=`[136,424]`，四行 rail y=`[442,422,402,382]`，其中后三行直接落在几何内区。`:1378` 还以 `segment.id[-10:]` 主动截断完整标识，与派工单“文字超框换行或缩字号，⛔ 不许裁掉”相反。
- 测试缺口：现有 batch D 测试只检查 panel title 区、色块/线色和画布尺寸，没有检查内部 label 的完整文本或碰撞；后续 mutation 台账会验证删除这些内部标签时该文件是否仍全绿。

## 6. S-5：新增测试绑定核实

**结论：不成立。** 已声明的 X-1/X-2/X-3/X-5、R4-a L-R1…R4、Batch D L-D1…D3 与 mirror 边界大多能在 mutation 后精确变红；但 X-2 是“真绑在错误判据上”，Batch D 的内部标签完整性/防碰撞完全无锁，R4-a 既没锁“先 controlled 执行、后改 autonomous 再 record”的时序，也没锁 `record_baseline.py` 独立 CLI。

### 6.1 干净克隆基线

真正的 clone 基线命令（注意本轮在 clone 工作目录显式核对 import）：

```text
pwd
# /tmp/energyplus-sol-review-20260804
export PYTHONPATH=$PWD
python -c 'import src; print(src.__file__)'
# /tmp/energyplus-sol-review-20260804/src/__init__.py
pytest -q -n 4 > clone_baseline_true.log 2>&1; rc=$?; echo $rc
# CLONE_BASELINE_TRUE_EXIT=1
# 4 failed, 2136 passed, 8 skipped, 10 xfailed, 205 warnings in 352.90s
```

四条 clone 固有环境红：缺未跟踪 restore reading、缺未跟踪 sm21 reading score 输入、缺 EP end-state 输入、缺 `OPENAI_API_KEY` 的真实网络测试。下表只把相对 clean subset 新增的失败算 mutation 红。

### 6.2 逐锁 mutation 台账

每轮统一命令形态：`export PYTHONPATH=$PWD; pytest -q -n 4 <target file/nodes> > mutation_<id>.log 2>&1; rc=$?; echo MUTATION_<ID>_EXIT=$rc`；实现用 `apply_patch` 精确摘除，记录输出后再用反向 `apply_patch` 恢复。mutation 克隆最终 `git diff --check` 与 `git diff --stat` 均零输出。

| 编号 | 摘掉/改回的实现 | 目标测试 | 相对干净基线新增失败 | 绑定结论 |
|---|---|---|---|---|
| N-1 | 删除 `check_reading_view` 中 `_dimension_endpoints_in_bounds(...)` 调用 | 4 个 X-1 cases（acceptance 参数化×2、lenient、margin） | clean subset 的 1 环境红之外新增 4 红；`5 failed,85 passed`，exit 1 | 真绑；独立复现轻门 |
| N-2 | `trusted_bounds_by_stem=resolve...` → `{}` | `test_trusted_bounds_from_case_data_survive_all_three_inflation_tricks` | 1 环境红之外新增该 1 红；`2 failed,88 passed`，exit 1 | 真绑调用，但 fixture `2×2 px` 绑错判据 |
| N-3 | structural metre guard 改回共用 `MAX_CANVAS_SIDE_PX` | widening/shrinking 两锁 | 2 红，exit 1 | 真绑、具体行为 |
| N-4 | `_fit_scale` 删除 `total_fit` | large-square pixel budget | 1 红；实际图 `8191×8191 > 50M`，exit 1 | 真绑、具体像素字段 |
| N-5 | corrupt render manifest `unavailable` 改回 `missing` | X-5b corrupt-manifest lock | 1 红，status 精确从 unavailable→missing，exit 1 | 真绑 |
| N-6 | 删除 top-level manifest `error` reason surface | X-5a distinctive-marker lock | 1 红，实际 message 回落 generic reason，exit 1 | 真绑 |
| N-7 | `flow --record` 改回 `require_reading_mode=False` | L-R2 real flow entry | 1 红，exit 1 | 真绑这一个入口；未覆盖独立 CLI |
| N-8 | 报告 lane 固定为 controlled | L-R1 controlled/autonomous 对照 | 1 红，autonomous 文本缺失，exit 1 | 真绑、非装饰 |
| N-9 | legacy report 冒充 autonomous | L-R3 report | 1 红，`legacy_unknown` 具体断言失败，exit 1 | 真绑 |
| N-10 | 删除 dev_function 警示 | L-R4 report | 1 红，“不作为正式成绩”缺失，exit 1 | 真绑 |
| N-11 | 删除 lane↔reading_agent 两个 schema 约束 | 两个 contract tests | 2 红，均 DID NOT RAISE，exit 1 | 真绑 schema 自洽性 |
| N-12 | 删除 typed 四立面循环 | Batch D 文件 | L-D1 + L-D2 共 2 红、其余 3 绿，exit 1 | D1 真绑；与 placeholder 有合理共享牵连 |
| N-13 | 缺立面分支改为空白 return | L-D2 | 1 红、其余 4 绿，exit 1 | 真绑明确占位 |
| N-14 | `_typed_legend` 直接 return | L-D3 | 1 红、其余 4 绿，exit 1 | 真绑全部具体色块 |
| N-15 | payload `mirrored=true` 时反转 floor 顺序（模拟读取禁区字段） | mirror/local-x 边界 | 1 红，逐像素 equality 失败，exit 1 | 真绑“不读取产品声明” |
| N-16 | 删除 polygon/segment/opening/floor-count 五类内部标签绘制 | Batch D 全文件 | **5 passed**，exit 0 | **未绑定：标签完整性/可读性为假锁缺口** |

### 6.3 断言分辨力审查

- X-1 的四条锁都断言具体 check-id/status/offender/field/reason 或 margin，不是“返回值存在”；但它们走 `check_reading_view` fallback、没有真实源图尺寸，因此无法暴露 B-1。
- X-2 单测走了 production checker 与真实 manifest/case_dir，路径选择正确；失真点在 fixture：`tests/test_checks_reading_correction.py:1237-1252,1272` 构造 `2×2 px` 源图，使 `[360,450]` 被人为保证越界。真实 case_data 是 790–3000 px 量级，所以 mutation 红只证明“代码用了该 tuple”，不证明 tuple 有分辨力。
- R4-a 的 L-R1/L-R3/L-R4 报告断言落在具体 lane/警示文案；L-R2 断言真实 flow 退出码、具体 error、两个禁止写入文件，质量合格。缺口不止另一个公开 CLI：它没有先执行 controlled reading、后改 autonomous 再 record 的时序锁，因此完全没约束“冻结必须早于被记账的活动”。
- Batch D 的标题/占位/legend/mirror 测试均落具体像素区域/颜色或逐像素 equality；但“label 不互压/不截断”完全没有对应断言。N-16 证明删掉内部标签仍全绿。

## 7. S-6：边界合规

**结论：成立。** 未发现施工越界。

- `git show --format= --name-only` 对 `32db683 7de68cb 066fff4 f7cc1ff 794b47a 8336bd5 b8ff69f` 的逐 commit 文件清单中，没有 `case_tests/test_baseline/gt/**`、sm24 `testdata_prompt.json`、历史 `_run/manifest.json` 或 `attempts/**`。
- 对上述禁区执行各施工范围的 `git diff --numstat ... -- <forbidden paths>`，`FORBIDDEN_DIFF_BEGIN` 与 `FORBIDDEN_DIFF_END` 之间为空；仅核文件元数据/路径，未读取 GT 内容。
- `git branch -r --contains <commit>` 对七个施工 commit 均无输出：在本地可见 remote refs 中没有已 push 证据。
- `src/validator/checks/schema.py:44-53,209-217` 的硬门集合不含 `reading.stroke_dimension_consistency`；该检查由 `src/validator/checks/reading.py:1028-1136` 继续作为 CROSS_CHECK 发射。目标测试中 `tests/test_checks_reading_correction.py:265-278` 也实际断言 `rep.passed` 同时该项仅 flagged。
- 施工 commit 文件清单不含 R1.5/R2 实现，也没有原地历史 manifest/attempt 产物。
- 本复核自身遵守边界：主树未运行 `git status`；未读 `case_tests/test_baseline/gt/`；所有 mutation 与记录入口探针均在 `/tmp/energyplus-sol-review-20260804*` 无硬链接克隆，且每个 pytest 进程前显式 `PYTHONPATH=$PWD`。

## 8. S-7：复杂度可扩展性

**结论：部分不成立（不另计 finding；B-1 的架构影响）。** 判卷图的几何接缝大体可扩展；可信画幅的 px=米假设必须推翻而非简单加槽位；reading mode 对“一个 run 内 lane 恒定”的假设也需要在允许 mixed-attempt 实验前重新审视。

- typed grade 的正面证据：`render_grade.py:1321-1345` 按实际 `len(floors)` 动态扩展 plan 行宽；`:1359-1373` 每层独立从 `footprint_exterior/zone_polygons` 求 scale 和绘多边形，不依赖共底面矩形；`:1217-1298` 从 GT-authored `elevation_surfaces` 聚合多层 surface、partial coverage 与开口 z，退台/多层并非必须推翻布局入口。固定四个 cardinal panel 对当前正交世界轴 schema 合理。
- 可信画幅的负面证据：`resolve_view_pixel_bounds` 只有源图 `(width_px,height_px)`，没有 meter-per-pixel、crop/viewport 或 image→reading frame；非方形/退台/中庭不是直接障碍，但任何不同缩放/裁切的读图输入都会继续暴露同一单位错误。修复需要引入可信坐标变换或与米制结构独立的量纲合理性判据，不能保留“图像 px 边界就是米制边界”的核心假设。
- reading mode 的负面边界：`reading_mode.py:65-69,178-230` 每 run 只冻结一份记录且禁止 drift；这适合 lane 在 run 创建前固定、所有 attempt 同模式的当前流程，也天然支持多 case/多 run。但若未来同一 run 比较 autonomous attempt 与 controlled rework attempt，accepted score 无法按 attempt 归因，必须拆 run 或升级 provenance 粒度。

## 9. 清单外自主发现

1. **B-1（BLOCKER）正常 trusted 路径 px/m 单位混用。** 这是本复核最高价值发现：轻门与 X-2 mutation 只验证了“来源被使用”，未验证来源的量纲/分辨力；真实 case_data 直接复现整道 regression gate 放行原始坏载荷。
2. **M-1（MAJOR）R4-a 只封住 `flow --record`，公开的 `record_baseline.py` CLI 仍宽松。** 新 run 可退出 0 并写出 legacy_unknown baseline/report；而真实 isolation provenance 又不记录 spawn model/directive/controller presence，声明 autonomous 无法与实际介入交叉核对。
3. **M-2（MAJOR）trusted source 不可解码时 per-stem 静默 fallback。** `build_view_manifest`/coverage 可接受任意 hashable `.png` 字节；PIL 打不开只 `continue`，产品 `image_bounds` 随即成为基准且整门通过。应与“无 manifest 的 legacy fallback”区分，后者有 coverage BLOCK，前者没有。
4. **m-1（MINOR）Batch D 内部标签需求未落、未锁。** 固定 rail 与 geometry 重叠、ID 主动截断；删除五类内部标签，新增 Batch D 测试仍 `5 passed`。

## 10. 证伪失败的尝试

- **产品用缺 manifest 触发 fallback：失败。** bounds 子检查会采用产品 extra 并 PASS，但 `reading.view_manifest_coverage` 为 INVARIANT FAIL，总 report 不通过。
- **产品用错 stem 触发 per-stem fallback：失败。** 子检查确实回落自算；coverage 同时报 required stem missing + evil stem extra，总门拒绝。
- **产品靠改源图/指纹漂移触发 fallback：失败。** flat-flow manifest provision 失败后 coverage 阻断；isolation merge 在 checker 前直接 raise。说明这两条生产外门有效。
- **产品以三种撑大手法绕过一个可解码、极小 `2×2 px` 的可信源图：失败。** dimension/stroke/extra 均不改变 trusted tuple；这反向证明 wiring 生效，但也暴露测试只覆盖了不真实尺寸。
- **合法米制 endpoints/anchor 的误伤尝试：失败。** 现有 production/直接检查的 in-bounds 与 1.5 m margin fixtures 均 PASS；目标子集 129 绿。当前问题是严重假阴性，不是假阳性。
- **S-1 探针第一次取 disposition：探针失败、作废。** 错把 `disposition_of` 当成 `CheckReport` 方法，得到 `AttributeError`；改用公开纯函数 `disposition(...)` 后重跑得 B-1 输出。
- **第一次 clone 全量：环境定位失败、作废。** clone 后未 `cd`，pytest 实际在主树跑；随后在 clone 内用 `pwd` 与 `import src; print(src.__file__)` 双重钉死后重跑，得到真实 4 条环境红基线。
- **X-5b mutation 第一次 node id 拼错：探针失败、作废。** pytest exit `5` / `no tests ran`；用 `rg '^def test_.*corrupt'` 找到真实函数名后重跑，精确 1 红。
- **L-D1 mutation 第一次命中 legacy 同名循环：探针失败、作废。** `git diff` 显示改到 line 994 而非 typed line 1409，Batch D 五测全绿；恢复后精确改 typed 循环，L-D1/L-D2 两红。该错误轮不能证明假锁。

## 11. 独立全量测试

命令（主树；无管道判退出码）：

```bash
pytest -q -n 4 > /tmp/sol_main_full_20260804.log 2>&1
rc=$?
echo MAIN_FULL_EXIT=$rc
tail -n 35 /tmp/sol_main_full_20260804.log
```

退出码：`MAIN_FULL_EXIT=0`。

尾部原文：

```text
tests/test_run_stage_flow.py::test_flow_judge_block_auto_invalidates_and_force_resamples
  /workspaces/EnergyPlus-Agent-dev/scripts/tool_scripts/run_stage.py:2366: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-6379/popen-gw0/test_flow_judge_block_auto_inv0/case/run; using flow defaults
    run_config = load_run_config(run_dir)

tests/test_run_stage_flow.py::test_flow_terminal_stop_returns_20
  /workspaces/EnergyPlus-Agent-dev/scripts/tool_scripts/run_stage.py:2366: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-6379/popen-gw0/test_flow_terminal_stop_return0/case/run; using flow defaults
    run_config = load_run_config(run_dir)

tests/test_run_stage_flow.py::test_flow_geometry_auto_records_auto_policy
  /workspaces/EnergyPlus-Agent-dev/scripts/tool_scripts/run_stage.py:2366: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-6379/popen-gw0/test_flow_geometry_auto_record0/case/run; using flow defaults
    run_config = load_run_config(run_dir)

tests/test_run_stage_flow.py::test_cmd_run_refuses_persisted_v1_run
  /workspaces/EnergyPlus-Agent-dev/scripts/tool_scripts/run_stage.py:2141: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-6379/popen-gw0/test_cmd_run_refuses_persisted0/case/run; using flow defaults
    run_config = load_run_config(run_dir)

tests/test_run_stage_flow.py::test_cmd_flow_refuses_persisted_v1_run
  /workspaces/EnergyPlus-Agent-dev/scripts/tool_scripts/run_stage.py:2366: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-6379/popen-gw0/test_cmd_flow_refuses_persiste0/case/run; using flow defaults
    run_config = load_run_config(run_dir)

tests/test_run_stage_flow.py::test_cmd_resample_refuses_persisted_v1_before_any_write
  /workspaces/EnergyPlus-Agent-dev/scripts/tool_scripts/run_stage.py:2214: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-6379/popen-gw0/test_cmd_resample_refuses_pers0/case/run; using flow defaults
    run_config = load_run_config(run_dir)

tests/test_run_stage_flow.py::test_new_run_flow_smoke_produces_v2_base_v2_records
  /workspaces/EnergyPlus-Agent-dev/scripts/tool_scripts/run_stage.py:2366: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-6379/popen-gw0/test_new_run_flow_smoke_produc0/case/run; using flow defaults
    run_config = load_run_config(run_dir)

tests/test_run_stage_flow.py::test_v1_run_resumable_after_explicit_migration
  /workspaces/EnergyPlus-Agent-dev/scripts/tool_scripts/run_stage.py:2141: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-6379/popen-gw0/test_v1_run_resumable_after_ex0/case/run; using flow defaults
    run_config = load_run_config(run_dir)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
2148 passed, 10 xfailed, 205 warnings in 501.70s (0:08:21)
```
