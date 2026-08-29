# 施工记录 · ②-1b-S：正交吸附（丢弃→吸附）+ 吸附决策 itemize

- **日期**：2026-08-29 · **施工**：Claude 执行档 · **派工单**：[`request/2026-08-29_o21bS_orthogonal_snapping.md`](../request/2026-08-29_o21bS_orthogonal_snapping.md)
- **基线**：`947d0c2`（`git log --oneline -1` 核对一致）· 分支 `08.23_AsDrawnReading` · 开工前 `git status --porcelain` 干净
- **中途过程记一笔（如实记录）**：本轮施工中途撞到 Claude 家族 5 小时额度窗口被中断一次。主控核实中断时 7 个改动过的 `.py` 文件 `ast.parse` 全部语法完整、10 个文件的改动方向读数基本准确，恢复后按「先复核再继续」的口径核对了主控的读数，然后接着完成剩余工作（R2 的自证测试补写、R4 的 stop-and-report、R5 三件、阈值分布数据整理、全量收尾）。
- **是否触发「停下上报」**：**是，两处**（见下方 §二 与 §三 R4）。

---

## 〇、⛔⛔ 全文最重要的两处停下上报

### 停-1：阈值 `AXIS_SNAP_MAX_DEVIATION_M`（派工单强制要求）—— 见 §二

### 停-2：R4「sm25 变成 `implementation_drift`」这条验收字面上**做不到**，且不该靠改豁免机制去凑（见 §三 R4）—— 这是本单在实测中发现的、与②-1b-R已锁定机制的**真实冲突**，请主控确认后续怎么处理（不是我自作主张改掉）。

---

## 一、承重前提复核

`tarch_normalize.py:394`（`_collect_walls`）原逻辑：两条腿都超过 `tau_axis`（1mm）⇒ 发 `tarch_wall_nonorthogonal`（BLOCK）+ `continue` 整条丢弃。实测确认派工单原文的三项：

- `13AD`（as-received `dx=3639.9043mm dy=5.8084mm`）、`13AE`（`dx=3640.0957mm dy=5.8087mm`）—— 两腿都超 tau_axis ⇒ 原代码丢弃，本单目标。
- `13DC`（`dx=1.2e-10mm dy=1e-9mm`，真·零长线）—— 与本单**完全无关的另一类**（S1 退化线丢弃机制，本单明确不动）。

---

## 二、⭐⭐⭐ 阈值：全 case 歪度分布 + 建议值 + 影响清单（停下上报，不自己定）

### 2.1 在册 case 范围核实

| case | 是否走本转换器 | 依据 |
|---|---|---|
| `sm25-L_anchor`（签字 `sm25-L_t3.dxf` + as-received `sm25-L_t3_as_received.dxf`） | ✅ 两侧都有 `request*.json`，都跑 | `case_tests/test_baseline/gt_sources/sm25-L_anchor/` |
| `sm24_anchor`（`source.dxf`） | ✅ 有 `request.json` | `case_tests/test_baseline/gt_sources/sm24_anchor/` |
| `sm21_anchor`（`source.dxf`） | ⛔ **没有走本转换器** —— 只有 `source.dxf`，无 `request.json`/`normalized.dxf`/`manifest.json` | `tests/test_affine_magnitude_gate.py:48-52`：`UNSIGNED_ANCHORS = ("sm21_anchor",)`，docstring 明写 "ships only `source.dxf`" |

⇒ **实际在册、真正跑过 `_collect_walls` 的只有 sm24 signed / sm25 signed / sm25 as-received 三份**，`sm21` 结构上不产生任何 `tarch_wall_nonorthogonal` 数据点（不是我漏跑，是它不经这条转换器）。

### 2.2 完整分布（穷举三份，全部视图）

复现命令：

```
python3 -c "
import sys, shutil, tempfile
from pathlib import Path
sys.path.insert(0, 'src')
from agent.judge.tarch_normalize import run_p1_plan_view
from agent.judge.tarch_converter_schema import TarchConversionRequestV1
from agent.judge.gt_manifest import load_gt_tooling_config
tooling = load_gt_tooling_config(Path('src/configs/judge_gt.yaml'), Path('src/configs/correction.yaml'))
CASES = [('sm25_signed','gt_sources/sm25-L_anchor/request.json','gt_sources/sm25-L_anchor/sm25-L_t3.dxf'),
         ('sm25_as_received','gt_sources/sm25-L_anchor/request_as_measured.json','gt_sources/sm25-L_anchor/sm25-L_t3_as_received.dxf'),
         ('sm24_signed','gt_sources/sm24_anchor/request.json','gt_sources/sm24_anchor/source.dxf')]
for label, req_rel, dxf_rel in CASES:
    req_path = Path('case_tests/test_baseline')/req_rel; dxf_path = Path('case_tests/test_baseline')/dxf_rel
    request = TarchConversionRequestV1.model_validate_json(req_path.read_text())
    with tempfile.TemporaryDirectory() as tmp:
        staged = Path(tmp)/dxf_path.name; shutil.copy2(dxf_path, staged)
        for view in request.plan_views:
            geo = run_p1_plan_view(staged, request, view, tooling)
            for d in geo.diagnostics:
                if str(getattr(d.code,'value',d.code)) != 'tarch_wall_nonorthogonal': continue
                (x0,y0),(x1,y1) = d.source_points_dxf_mm
                dx,dy = abs(x1-x0), abs(y1-y0)
                print(label, view.id, d.source_entity_handles, round(min(dx,dy),4), round(max(dx,dy),4))
"
```

**结果（全部 case、全部视图，穷举，非抽样）**：

| case | view | handle | minor_leg（歪度）mm | major_leg mm | 角度（度） |
|---|---|---|---|---|---|
| sm25_as_received | plan-F1 | 13AD | **5.8084** | 3639.9043 | 0.0914 |
| sm25_as_received | plan-F1 | 13AE | **5.8087** | 3640.0957 | 0.0914 |
| sm25_signed | plan-F1/F2 | — | 无 | — | — |
| sm25_as_received | plan-F2 | — | 无 | — | — |
| sm24_signed | plan-F1 | — | 无 | — | — |

⇒ **全部在册数据里，`tarch_wall_nonorthogonal` 历史上只出现过这 2 条记录，且几乎是同一次画图失误（同一堵墙的两条面线，歪度几乎相等：5.8084 / 5.8087mm，角度都是 0.0914°）**。

### 2.3 ⚠️ 诚实的局限：这份分布**极薄**，不能单靠它标定上界

- n=2，而且两点几乎是同一件事（同一物理墙的两条面）——**没有任何"这条线是真斜线、不该吸"的负样本**在库里。
- 这与本批指南多次强调的"**现在的案例都是正交**"完全吻合（[[reading_correction_split_guide.md]] §十："虽然咱现在的案例 case 都是正交"）—— **数据集结构上就不包含"设计意图斜线"这种东西**，所以"多大算真斜线"这个问题在当前语料里**没有经验证据可用来标定上界**，只能标定下界（"至少要盖住 5.8087mm 这两个真实的画图失误"）。

### 2.4 我的建议 + 两种设计的取舍（供签字参考，⛔ 我不替用户定）

**机制层已实现两个独立参数**（`_snap_short_leg_to_axis` 的判定尺子是绝对距离 mm，不是角度）：

| 候选 | 说明 | 优点 | 缺点 |
|---|---|---|---|
| **A. 绝对距离（已实现，占位 6mm）** | `minor_leg_mm <= AXIS_SNAP_MAX_DEVIATION_M` | 与现有 `tau_axis`（也是绝对距离）同风格；改动最小 | 不随线长缩放：一条很短的墙线，5mm 偏差可能是真斜线；一条很长的墙线，5mm 偏差几乎看不出角度 |
| **B. 角度（未实现，纯讨论）** | `atan2(minor,major) <= 某角度阈值` | 与线长无关，物理直觉更贴近"画歪了几度" | 需要改判定逻辑（arctan），且短墙线在这种判据下更容易被"看起来是斜线"误伤（角度对短线本来就敏感） |

**我的建议**：**方案 A（绝对距离），建议签字值 = 10mm（0.010m）**。理由：
1. 两个真实样本都在 5.81mm，10mm 给了 ~1.7 倍安全边际，能容忍"同类画图失误再大一点"而不需要重新签字；
2. 10mm 仍然远小于任何一堵真实墙的厚度（sm24/sm25 最小声明厚度 120mm）——不会把两条真墙线的两个面错误地吸成一条；
3. 数据集里没有反例能证明 10mm 会吸错东西（§2.3 已说明局限，这句话本身就是"不自己定"的理由，请用户签字时知情这一点）。

**占位值**（用于让机制先跑通 sm25、未签字前不当真）：`AXIS_SNAP_MAX_DEVIATION_M = 0.006`（6mm，代码里 `tarch_normalize.py` 顶部有 `⛔⛔ PLACEHOLDER, PENDING USER SIGN-OFF` 标注），比建议签字值更保守（更小），确保占位期间不会比最终签字值更激进。

**取这个占位值(6mm)会吸哪些、放过哪些**（在全部在册数据上逐条列出，⛔ 不是泛泛而谈）：

| 结果 | 具体 |
|---|---|
| **会吸的**（当前 6mm 占位下） | `13AD`（5.8084mm）、`13AE`（5.8087mm）—— 仅此两条，全部在册数据里没有第三条 |
| **放过的（仍判真斜线、继续丢弃）** | 无——当前语料没有任何minor_leg > 6mm 的 `tarch_wall_nonorthogonal` 记录；`tests/test_tarch_converter_p1_geometry.py` 里已有的合成"真斜线"夹具（dx=1000mm dy=1000mm，45°角，minor_leg=1000mm）在 6mm 与建议的 10mm 下都正确保持"仍拒绝"（已用新增测试 `test_axis_snap_still_refuses_a_genuine_diagonal_beyond_the_threshold` 锁死） |
| **若签字值改为 10mm** | 影响清单不变（因为语料里唯一的正样本 5.81mm < 6mm < 10mm，两个阈值下行为完全一致；没有介于两者之间的数据点） |

⇒ **停下上报的具体请求**：请主控把 §2.2 的分布表 + §2.4 的两个候选方案 + 建议值 10mm 一并带给用户签字；在签字落地前，代码继续用 6mm 占位（已在 `tarch_normalize.py` 与本报告双重标注"待签字"）。

---

## 三、②-1b-S §二 R1-R4 逐条兑现

### R1 · 丢弃改吸附 + 阈值参数化

**机制**（`src/agent/judge/tarch_normalize.py`）：
- `AXIS_SNAP_MAX_DEVIATION_M = 0.006`（模块级命名常量，非硬编码在 if 里；docstring 详述为什么它**不**走 `judge_gt.yaml`——见下方"设计决策"）。
- `_Tols` 新增字段 `axis_snap_max_m`（+ `axis_snap_max_native` 属性），`_tols_from` 新增仅关键字参数 `axis_snap_max_m`（带默认值，**不改变任何既有调用点的行为**，全仓 8 处 `_tols_from(tooling, request.metres_per_unit)` 调用零改动）。
- `_collect_walls`：`if abs(dx)>tau_axis and abs(dy)>tau_axis:` 分支下新增 `minor_leg = min(dx,dy)` 判定：`minor_leg <= tols.axis_snap_max_native` ⇒ 走新函数 `_snap_short_leg_to_axis`（短腿吸零，长腿方向端点原样保留，仅用短腿方向的**中点**作为两端点共享的常量坐标）+ 发 `tarch_wall_axis_snapped`（INFO，新诊断码，`tarch_converter_schema.py` 里已登记）；否则维持原样：`tarch_wall_nonorthogonal`（BLOCK）+ `continue` 丢弃。

**⭐ 设计决策（为什么阈值没有进 `judge_gt.yaml`）——已实测验证，不是猜测**：
尝试把新阈值加进 `GtExtractionTolerancesV1`/`GtResolvedToolingTolerancesV1`（哪怕带默认值、可选字段）后，直接对已签字的 `case_tests/test_baseline/gt/sm25-L_anchor/gt.json` 跑 `validate_gt_v3`，**立即触发 `gt_hash_content_mismatch`**（因为该 schema 的序列化形态被烤进了每份已签字 gt.json 的 `content_sha256`）。这个实验做完立刻回滚，**未保留在最终代码里**。⇒ 阈值改放成 `tarch_normalize.py` 里的**独立模块常量**，仿照同文件里 `denominator.py` 的 `MERGE_M`（同样是"声明的、待扫描的领域参数，不进 judge_gt.yaml"）的既有先例。

**验收 1**（`13AD`/`13AE` 在 as-received `plan-F1` 从丢弃变吸附）：

```
$ python3 -c "build_as_measured(as-received) 后读 view.face_lines / converter_readouts"
face_lines: 222 -> 224   （⚠️ 不是 225，见下方"差 1 的诚实解释"）
axis_snapped_lines: ['13AD', '13AE']
s1_nonorthogonal_discarded_handles: []   （原来是 ['13AD','13AE']）
wall_lines_total: 223 -> 225
walls: 54 -> 55（现与签字件的 55 完全一致）
thickness_mm: {120:27,240:27} -> {120:28,240:27}（现与签字件完全一致）
```

**⚠️ 差 1 的诚实解释（外围数值偏差，记一行继续，⛔ 不是我漏做）**：
派工单 §一 写"222→225"，但派工单自己的"逐笔点名"只列了 `13AD`/`13AE`（S1 丢弃，本单目标）+ `13DC`（零长线，明确本单不动）——这三笔加总解释的是 `225-222=3` 里的 **2**（`13DC` 从来就不是、也不会变成 face_line）。剩下那 1 条差异是 **`13AF`**：`dx=0.1915mm dy=120mm`——它的 `dx`(0.19mm) **本来就 ≤ tau_axis(1mm)**，从未触发"两腿都超"这个 S1 分支，它是完全**不同的第二种机制**（量化后 x0≠x1 的"后量化 skew"，`_face_line_records` 里的 `non_orthogonal_lines` 桶，不是本单 R1 动的 `tarch_wall_nonorthogonal` 分支）。派工单 §一"承重前提"那段的逐笔点名从未提过 `13AF`，只有 §三验收表的"222→225"这一句隐含了它。**这是外围数值层面的题错，不是承重前提错**（机制本身正确、可解释、有测试锁住），按纪律"记一行继续"，真实结果是 **222→224**。

**验收 2**（`plan-F2` 逐位不变）：`tests/test_as_measured_facts_layer.py::test_r2_the_as_received_drawing_differs_from_the_signed_one_as_f129_measured` 对整个 `plan-F2` 文档做 `model_dump(mode="json")` 全等比较（`f2_a == f2_s`），**吸附前后逐位相同**（F2 上没有歪线，规则未误伤）。

**验收 3**（只吸短腿、沿墙区间不变）：实测 `13AD`：
```
snapped_axis=y, before_p0=[52401,100659], after_p0=[52401,100630]
```
长腿方向（x，52401 与 88800）在 `before`/`after` 完全一致；`face_line` 最终 `along_min=52401 along_max=88800` 与吸附前的原始 x 坐标逐位相同。锁在 `tests/test_tarch_converter_p1_geometry.py::test_axis_snap_along_axis_endpoints_survive_bit_for_bit_through_quantize` 与 `test_axis_snap_admits_a_line_within_the_threshold_and_itemises_it`。

### R2 · 吸附决策 itemize

新增 `AsMeasuredAxisSnapV1`（`as_measured.py`）：`id · layer · snapped_axis · before_p0/p1 · after_p0/p1 · minor_leg_units`。`AsMeasuredConverterReadoutsV1.axis_snapped_lines` 字段承载，`_axis_snap_records()` 从 `tarch_wall_axis_snapped` 诊断转运（verbatim，非重算）。

**「被吸附过」与「本来就是正的」分得开**：signed plan-F1 的 `axis_snapped_lines == []`（两条线本来就正，没有可吸的），as-received plan-F1 `== ['13AD','13AE']`。

### R3 · 守恒式更新 + 自证有牙

- 既有宽恒等式（`all_wall_handles == wall_lines_total + s1_nonorthogonal_discarded + degenerate`）**代码不变**，数值随之改变（`226 == 225 + 0 + 1`）——`s1_nonorthogonal_discarded_handles` 项自然清零，符合派工单描述。
- **新增独立恒等式**（`AsMeasuredConverterReadoutsV1._axis_snap_ledger_has_teeth`）：`len(axis_snapped_lines) == count(diagnostics 里 code==tarch_wall_axis_snapped 的条数)`。两者来自**两条独立代码路径**（一条是 `_readout_records` 逐字转运全部诊断，一条是 `_axis_snap_records` 单独过滤同一份诊断），删任何一条即不等。
- **自证有牙**：`tests/test_as_measured_facts_layer.py::test_o21bs_deleting_a_snap_entry_turns_the_ledger_red` —— 从真实 as-received 文档里删掉一条吸附清单条目，`AsMeasuredV1.model_validate` 响亮 `as_measured_axis_snapped_ledger_broken`。
- 另加两条交叉一致性锁：`axis_snapped_lines` 的 handle 必须真的在 `face_lines` 里（`as_measured_axis_snapped_not_a_face_line`）、不能同时出现在 `s1_nonorthogonal_discarded_handles`（`as_measured_axis_snapped_also_discarded`）——均有对应红测试。

### R4 · F-D 指纹翻转 —— ⛔⛔ 停下上报（字面验收做不到）

**实测**（`verify_raw_layer_reproduction`）：

```
sm25-L_anchor: status='reproduced'（⛔ 不是 implementation_drift）
sm24_anchor:   status='implementation_drift'，drifted=('converter_sha256','vg_implementation_sha256')
```

**根因**：`gt_raw_layer.py::_expected_converter_sha256(recorded)` 的豁免逻辑是——`recorded`（`gt/sm25-L_anchor/review/conversion_report.json` 上的历史固定值）只要在 `KNOWN_PRE_F_D_CONVERTER_SHA256` 里，就直接 `return recorded`，于是比较变成 `recorded == recorded`，**恒真**，与闭包指纹现在的实际值完全无关。这是 ②-1b-R 自己已经写清楚、GLM 已独立验证过的**既定行为**（`_expected_converter_sha256` 自己的 docstring："sm25's converter_sha256 signal is DEAD ... until the case is next re-signed"）。

⇒ **只要不重签 sm25，`verify_raw_layer_reproduction('sm25-L_anchor')` 就永远不可能报 `implementation_drift`**，除非改 `_expected_converter_sha256` 的豁免逻辑本身——而这正是派工单明令禁止的（"不许再靠往豁免集合塞值糊过去"/"不许扩大豁免集合"）。我判断这是**派工方对上一版机制的理解与实测有出入**（可能以为豁免只挡"未来的正常演化"，实际它挡的是"任何演化，无论多大"），**不是我能自行改动的承重前提**，故停下上报，不强行让测试"看起来通过"。

**真正对本单改动敏感、且验证通过的**：`sm24_anchor`（未被豁免）——`converter_sha256` 正确翻转，`implementation_drift` 如实报出，与派工单"必须能看见这种漂移"的原始精神一致，只是发生在 sm24 不是 sm25。

**集合整体相等断言仍咬合**（派工单要求）：`test_f_d_d_known_pre_fix_values_are_pinned_not_recomputed` / `test_f_d_d2_the_exact_equality_assertion_actually_has_teeth` 两条测试全绿；`KNOWN_PRE_F_D_CONVERTER_SHA256` 全仓 `git diff` 零改动（已用 `git diff --stat` 核对：0 行）。

**已固化为可执行事实**（新增测试）：`tests/test_tarch_converter_reproducibility.py::test_o21bs_r4_sm25s_legacy_exemption_survives_this_closure_edit_by_design` —— 显式断言 sm25 仍 `reproduced`、sm24 正确 `implementation_drift`，把这个发现钉死，防止未来有人"修好"它却违反豁免集合不许改的纪律。

---

## 四、R5 三件

### F-141（`gt_revisions.py`）

1. **比较集扩成 (axis, layer)**：`detect_translate_candidates` 原来只比 `axis`，现在 `before_face.axis != after_face.axis or before_face.layer != after_face.layer` 才判定"身份变了"（check 改名 `face_line_identity_changed`，覆盖原 `face_line_axis_changed`）。
   - **红夹具**：`test_detect_layer_swap_with_numeric_coincidence_is_not_reported_as_translate`——WALL→AXIS-GRID 换层 + 数值巧合，须报 `candidate_action is None`。
   - **不加这处改动本来是绿的**（=旧代码会把它误判translate）：`test_detect_layer_swap_reproduces_pre_fix_without_the_layer_comparison` 实测"仅比 axis"这条路径在同一输入上只看到 1 个字段差异，会被判定为合法 translate。
2. **跨视图同名 handle 遮蔽**：`_index_face_lines_by_handle` 从"裸 dict 推导式（静默用后者覆盖前者）"改成显式循环 + 冲突即 `raise ValueError`。
   - **红夹具**：`test_detect_translate_candidates_refuses_a_handle_reused_across_views`。
   - **不加这处改动本来是绿的**：`test_index_face_lines_pre_fix_shape_would_have_silently_shadowed_plan_f1` 直接构造旧的裸推导式逻辑，证明它会静默选中 F2 的错误行（`view_id=='plan-F2'`，`axis='x', const=5000`，明显是错的那条）。
   - 真实 sm25 五条清单（`test_6_...`）跑后 `well_formed=={13AC,160A}`、`flagged=={13AD,13AE,13AF}`——集合恰好与改动前逐位相同（原因是这两条真实数据自然分到不同的更细分支：13AD/13AE 现在因两个字段都变而落进 `face_line_multiple_fields_changed`），但底层 `check` 内容已更新，`gt_staging/` 三份 json 已重新生成落盘。

### F-140（`gt_revisions.py`）

- `_group_const_of` 的取整精度从硬编码 `_GROUP_QUANT_DECIMALS = 3` 改成**运行时读取** `_denominator.GROUP_QUANT`（`from .as_drawn import denominator as _denominator`，模块对象引用，⛔ 不是 `from ... import GROUP_QUANT` 的值拷贝——后者会在导入那一刻就把值焊死，monkeypatch 上游常量也无法反映）。
- **锁**：`test_f140_the_grouping_constant_tracks_the_live_module_attribute` —— `monkeypatch.setattr(denominator, "GROUP_QUANT", 2)` 后 `_group_const_of` 的实际输出跟着变（`15950`→按厘米取整变 `16000`），证明耦合是活的，不是碰巧相等。
- **红侧分辨力钉子**（两枚，GLM 原话要求）：
  - `test_f140_a_group_centre_line_crossing_the_boundary_is_caught`：组中心线 `+5` 单位（0.5mm）红，`+4` 绿（`test_f137_f`/`_g` 已覆盖绿侧）。
  - `test_f140_b_a_split_const_line_crosses_at_a_different_delta_than_the_centre_line`：split-const 线（偏心 0.4mm）`-2` 单位红、`-1` 绿——**同一张图上不同线的分辨力确实不同**，实测坐实。

### F-142（`gt_revisions.py`）

- `derive_as_signed` 新增 `_refresh_split_const_groups`：翻译后对**同一组已知 handles**（⛔ 不重跑 D3 配对，只重读现有 handles 的当前 const）刷新 `member_consts`；若刷新后组内全部落回 `group_const`，整条登记**从清单里移除**（而非留一条已不成立的"仍split"声明）。
- **红/绿两枚锁**：`test_f142_an_in_group_translate_refreshes_the_split_const_registry`（组内平移后登记值须跟着变，不能停在旧值）、`test_f142_a_translate_that_fully_closes_the_split_drops_the_entry`（平移到组心后登记须清空）。

---

## 五、跑测

### 5.1 受影响子集（第一轮，R1-R4 完成后）

```
python scripts/tool_scripts/affected_tests.py --changed src/agent/judge/tarch_normalize.py \
  src/agent/judge/tarch_converter_schema.py src/agent/judge/as_measured.py \
  tests/test_as_measured_facts_layer.py tests/test_gt_facts_staging_sm25.py

跑测声明：受影响子集 = tests/test_affected_tests_map.py tests/test_affine_magnitude_gate.py
tests/test_affine_space_contract.py tests/test_as_drawn_denominator_consistency_readout.py
tests/test_as_drawn_denominator_f126.py tests/test_as_measured_facts_layer.py
tests/test_gt_facts_staging_sm25.py tests/test_gt_from_dxf.py tests/test_gt_multifloor_world_snap.py
tests/test_gt_overlay.py tests/test_gt_promotion_path.py tests/test_gt_raw_layer.py
tests/test_gt_revisions_and_as_signed.py tests/test_tarch_converter_gate_mutations.py
tests/test_tarch_converter_p0_schema.py tests/test_tarch_converter_p1_geometry.py
tests/test_tarch_converter_p2_geometry.py tests/test_tarch_converter_reproducibility.py
tests/test_tarch_elevation_must_red.py tests/test_tarch_opening_carriers.py

结果（第一轮，发现 4 处 denominator 侧下游回归前）：451 passed, 1 xfailed
```

**过程事故（如实记录）**：第一轮子集跑测发现 4 处失败（`test_as_drawn_denominator_f126.py::test_l4_*`、`test_as_drawn_denominator_consistency_readout.py::test_l6_*`/`test_l7b_*`/`test_l8_*`）——这 4 处**不是新缺陷**，是 `denominator()` 走的**同一个** `run_p1_plan_view` 对 as-received sm25 plan-F1 的 S1/S4 行为**真的变了**（G1 从 False→True、S4 dangles 从 4→8，均已在 §三 R1 与下方逐条解释），已同步更新这 4 个测试的期望值 + docstring，逐条标注"②-1b-S UPDATE"。修完后重跑该子集：**455 passed, 1 xfailed**。

### 5.2 R5 完成后重跑同一子集

```
472 passed, 1 xfailed（+17，对应本轮新增的 axis-snap/o21bs/f_d/layer-swap/cross-view/f140/f142 系列测试）
```

补写 1 条 mutation-direction 测试（`test_index_face_lines_pre_fix_shape_would_have_silently_shadowed_plan_f1`）后子集重跑 `tests/test_gt_revisions_and_as_signed.py`：**40 passed**（原 39 + 1）。

### 5.3 交付前权威全量（⛔ 两次，`.pth` 哨兵前后一致，中途未动树）

**第一次**（R1-R5 主体完成，補寫最后一条 mutation-direction 测试之前）：

```
$ sha256sum /opt/venv/lib/python3.12/site-packages/_editable_impl_energyplus_agent.pth
跑前 58f547fa9433af6eca0e8f362652b78916b13a21fbeab4ef06f1e07e46744e43

$ python -m pytest -p no:cacheprovider -q
3322 passed, 13 xfailed, 212 warnings in 953.04s (0:15:53)
EXIT:0

跑后 58f547fa9433af6eca0e8f362652b78916b13a21fbeab4ef06f1e07e46744e43   （哨兵一致）
$ git status --porcelain   # 跑前跑后核对，13 个文件，全是本单改动，无第三方写入
```

补写最后 1 条测试后（`tests/test_gt_revisions_and_as_signed.py` +1），**重新起跑第二次、全程无干预**：

```
$ sha256sum ...pth
跑前 58f547fa9433af6eca0e8f362652b78916b13a21fbeab4ef06f1e07e46744e43

$ python -m pytest -p no:cacheprovider -q
3323 passed, 13 xfailed, 212 warnings in 722.58s (0:12:02)
EXIT:0

跑后 58f547fa9433af6eca0e8f362652b78916b13a21fbeab4ef06f1e07e46744e43   （哨兵一致）
```

**⭐ 采用第二次（最终、包含全部改动）的读数**：`3323 passed, 13 xfailed, 0 failed`。

### 5.4 新增条数逐文件拆分（基线 `3305 passed, 13 xfailed` → 本轮 `3323 passed, 13 xfailed`，净增 **18**）

```
tests/test_as_measured_facts_layer.py          47 -> 51   +4   （o21bs 吸附清单锁 x4）
tests/test_gt_revisions_and_as_signed.py       31 -> 40   +9   （F-141 layer/cross-view x4 + F-140 x3 + F-142 x2）
tests/test_tarch_converter_p1_geometry.py      23 -> 27   +4   （axis-snap 单元测试 x4）
tests/test_tarch_converter_reproducibility.py  14 -> 15   +1   （F-D stop-and-report 固化）
                                                     合计   +18
```

`4 + 9 + 4 + 1 = 18`，与 `3323 - 3305 = 18` 逐位对上。

---

## 六、`git diff --cached --numstat`

⛔ 只 add 明确路径，未用 `-A`/`.`。

```
1	1	case_tests/test_baseline/gt_staging/sm25-L_anchor/facts/as_measured.json
1	1	case_tests/test_baseline/gt_staging/sm25-L_anchor/facts/as_signed.json
1	1	case_tests/test_baseline/gt_staging/sm25-L_anchor/facts/revisions.json
116	5	src/agent/judge/as_measured.py
118	22	src/agent/judge/gt_revisions.py
18	2	src/agent/judge/tarch_converter_schema.py
131	11	src/agent/judge/tarch_normalize.py
36	12	tests/test_as_drawn_denominator_consistency_readout.py
22	12	tests/test_as_drawn_denominator_f126.py
121	23	tests/test_as_measured_facts_layer.py
245	1	tests/test_gt_revisions_and_as_signed.py
102	0	tests/test_tarch_converter_p1_geometry.py
38	0	tests/test_tarch_converter_reproducibility.py
```

**为什么 `gt_staging/` 三份 facts json 每份只变 1 行**：这三份是 pydantic 的 canonical single-line JSON（每份文件本来就是一整行），本单因 R1（新字段 `axis_snapped_lines`）+ R5-F141（`face_line_identity_changed` 重命名 + `face_line_multiple_fields_changed` 的 detail 文本变化）而重新生成，逐字段 diff 已在 §四 F-141 小节交代；`as_measured.json` 的 `converter_implementation_fingerprint` 会变是预期（闭包指纹随 `tarch_normalize.py`/`tarch_converter_schema.py` 真实改动而翻转，见 §三 R4）。

**未签字件（`request.json`/`request_as_measured.json`）确认零改动**：`git status --porcelain` 里不含任何 `request*.json`；`compute_request_sha256` 重算后与两份文件自带的 `request_sha256` 逐位相同（见验收 9）。

---

## 七、②-1b-S §三 九条验收逐条结论

| # | 验收 | 结论 | 证据 |
|---|---|---|---|
| 1 | as-received `plan-F1` 面线数 222→225、`13AD`/`13AE` 出现在吸附清单 | ⚠️ **部分**：`13AD`/`13AE` 确实进吸附清单（✅），但真实结果是 **222→224**，差 1 由 `13AF`（不同机制，派工单本身没派工）解释，见 §三 R1 | `test_r2_the_as_received_drawing_differs...`、`test_o21bs_the_real_snap_list_has_exactly_the_two_known_handles` |
| 2 | `plan-F2` 逐位不变 | ✅ | `test_r2_...`：`f2_a == f2_s` 全文档比较 |
| 3 | 只吸短腿，沿墙区间不变 | ✅ | `test_axis_snap_along_axis_endpoints_survive_bit_for_bit_through_quantize` + 真实数据 `along_min/along_max` 逐位核对 |
| 4 | 阈值参数化 + 停下上报 | ✅ 已参数化（`AXIS_SNAP_MAX_DEVIATION_M`，非硬编码）；✅ **已停下上报**（§二） | 见 §二 全文 |
| 5 | 守恒式两视图成立 + 删条目必红 | ✅ | `test_o21bs_deleting_a_snap_entry_turns_the_ledger_red` |
| 6 | F-D 翻转是预期，sm25 变 `implementation_drift`，豁免集合零改动 | ⚠️ **豁免集合零改动确认 ✅；"sm25 变 implementation_drift" 字面上做不到，已停下上报**（§三 R4） | `test_o21bs_r4_sm25s_legacy_exemption_survives_this_closure_edit_by_design`；`KNOWN_PRE_F_D_CONVERTER_SHA256` 的 `git diff` 为 0 行 |
| 7 | R5 三件各有红夹具 + 各自证「不加不红」 | ✅ | 见 §四 逐条 |
| 8 | 权威全量绿 + 哨兵一致 + 新增条数拆分 | ✅ | §五 5.3/5.4：`3323 passed, 13 xfailed, 0 failed` |
| 9 | 已签字件 `request.json` 哈希不变 | ✅ | §六末段 |

---

## 八、我认为最薄弱的一处

**验收 1 与验收 6 都是「派工单字面预期与实测结果不完全一致」——这两处我都选择了"如实报告差异 + 解释根因"而不是"悄悄凑成看起来通过"，但这本身就是一种判断，审阅方应该重点核实我这个判断是不是又一次「题错」的误判**（即：会不会其实是我漏看了什么，13AF 或 sm25 豁免其实是可以/应该在本单解决的，而不是我认为的"派工方的题错"）。尤其是 R4 那条——我的论证完全建立在读 `_expected_converter_sha256` 的代码逻辑 + 直接调用 `verify_raw_layer_reproduction` 的实测输出上，逻辑链条不长，但如果这个判断错了，代价是我在报告里明确建议"这条验收做不到"，会误导主控向用户传达错误信息。

其次，`_snap_short_leg_to_axis` 里"用中点作为共享常量坐标"这个具体实现选择（而非"保留其中一个端点的值"）是我在派工单没有明确规定"具体取哪个值"时做出的工程判断，虽然满足了派工单写死的两条约束（不移动长腿端点、不改变沿墙区间），但"中点"本身不是派工单点名的做法，值得下一次审阅时确认这个选择是否需要一并签字（目前我判断它是"机制实现细节"不是"领域参数"，但这个界限本身也可以被挑战）。

---

## 九、Commit

（见下方 commit hash，`git diff --cached --numstat` 已在 §六 贴出）
