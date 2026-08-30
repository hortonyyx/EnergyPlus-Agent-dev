# 执行记录 · F-147：吸附阈值签字落地 + **新增角度门**

- **日期**：2026-08-30 · **席位**：Claude（施工） · **派工方**：orchestrator
- **派工单**：[2026-08-30_f147_angle_gate_dispatch.md](../request/2026-08-30_f147_angle_gate_dispatch.md)
- **基线 HEAD**：`37607dd`（派工单写的 `c7f97af` 是其父系；`37607dd` 只多了 CLAUDE.md/派工单，`src/` 逐字相同）
- **结论**：四项任务 R1–R4 全部落地；**六**条验收（派工单五条 + 我自加一条）全绿，**逐条有变红自证**；⛔ 未触发停下上报。

---

## 〇、开工自检（派工单 §一，三条）

| # | 检查项 | 派工单声称 | 实测 | 结论 |
|---|---|---|---|---|
| 1 | `AI_agent/CLAUDE.md` §0 有「科研项目 P0」「gt 铁律」 | 存在 | §0 抬头「本项目 = 科研项目。P0 = 快速迭代…」；gt 铁律在 §1.5#4 | ✅ 在对的树上 |
| 2 | `tarch_normalize.py:130` 常量值 | `0.006` | **`AXIS_SNAP_MAX_DEVIATION_M = 0.006`，正好在第 130 行** | ✅ 相符 |
| 3 | 493–505 行**只有毫米那一道门、角度门不存在** | 只有毫米门 | `if minor_leg <= tols.axis_snap_max_native:` … `else: tarch_wall_nonorthogonal + continue`；全文件 `atan2` / `degrees` 在吸附逻辑里**出现 0 次** | ✅ 相符 ⇒ **承重前提成立，本单确是加新门** |

---

## 一、⭐⭐ 派工单 §四要求【实测】的两件

### ① 几何产物逐字节不变 —— ✅ **成立**

探针 = 对 **三份图 × 全部 5 个 plan view** 跑 `run_p1_plan_view`，把几何载荷
（`wall_lines` / `wall_line_layers` / `jamb_caps` / `wall_bands` / `openings` /
`opening_fills` / `faces` WKT / `dangles` / `cuts` / `invalid` / `sum_area_m2` /
`footprint_area_m2` / `footprint_polygon` WKT / 诊断**码**清单）序列化后哈希。
⭐ 诊断的 `context` **刻意排除在几何摘要之外**（R3 就是要往那里加字段），但吸/拒 **码**在内，
所以任何一条线的吸/拒翻面都会被这把尺子看见。

```
                              改前                                 改后
GEOMETRY_DIGEST   57b9fc97d0adf9ed614b0d9a01fa250e75276cda34a437ea24f4c3cbc4d43ca1  ← 完全相同
  sm24_signed:plan-F1        f0ac7254bb8321ee…   f0ac7254bb8321ee…
  sm25_signed:plan-F1        97b757bfea96e846…   97b757bfea96e846…
  sm25_signed:plan-F2        4ed8082f1932b4e7…   4ed8082f1932b4e7…
  sm25_as_received:plan-F1   749dadf55ce1d23e…   749dadf55ce1d23e…
  sm25_as_received:plan-F2   4ed8082f1932b4e7…   4ed8082f1932b4e7…
```
`cmp` 逐字节对比两份 JSON 序列化：**IDENTICAL BYTE FOR BYTE**。

**吸/拒普查（全语料）**：`tarch_wall_axis_snapped` = 2（均在 sm25 as-received `plan-F1`）、
`tarch_wall_nonorthogonal` = **0**。改前改后同数、同 handle。两条的实测角度：

| handle | minor leg | major leg | **角度** | 毫米门 | 角度门 |
|---|---|---|---|---|---|
| 13AD | 5.808358 mm | 3639.904 mm | **0.09143°** | 5.81 < 10 ✅ | 0.091 < 1.0 ✅ |
| 13AE | 5.808663 mm | 3640.096 mm | **0.09143°** | ✅ | ✅ |

⇒ 与派工单推导一致（5.81 mm 两档都吸、0.091° 远在 1.0° 内）。**⛔ 无需停下上报。**

⭐ **第二把独立尺子**（不是我造的，是仓库自己的）：`as_measured` 事实文档逐叶对账，
改前改后**只有 3 片叶子不同**，且三片都是本单点名要产生的：
```
/converter_implementation_fingerprint                        2ca4e773… → d5825959…   （§四② 预期）
/views[0]/…/diagnostics[0]/context/angle_deg   <ABSENT> → 0.09142935778784271        （R3 新读数）
/views[0]/…/diagnostics[1]/context/angle_deg   <ABSENT> → 0.0914293577882342         （R3 新读数）
```
**几何字段差异 = 0 片。** 这条比我自己的探针更有说服力，因为它是既有生产代码的输出、不是我为验收写的。

### ② `converter_sha256()` 翻不翻 —— 分三段测，**派工单的推论对了一半**

| 读数 | 场景 | `converter_sha256()` | 翻了吗 |
|---|---|---|---|
| **A** | HEAD 基线 | `2ca4e773147aad302384f05d739ba18a8882e405f8e4cbff52f5558df027c569` | — |
| **B** | HEAD + **纯 `#` 注释**改动（插一整行注释） | `2ca4e773147aad302384f05d739ba18a8882e405f8e4cbff52f5558df027c569` | **❌ 不翻** ✅符合预期 |
| **C** | 本单工作树（常量值 + 角度门 + 文档串） | `d5825959b9f09c5909bb5c3f2bb46d18397526858d3495e800c01fd171cd81bb` | **✅ 翻** ✅符合预期 |
| **D** | HEAD + **纯 docstring** 改动（不动一行代码） | `21759d57876e013125eb143b01eae9447221ef859206c5705fcf359cafbd46c7` | **⚠️ 翻了** |

⚠️ **只记不停的更正一条**：派工单 §四② 把「纯注释 / **docstring** 改动」并列成「都不该翻」——
**docstring 会翻**。这不是缺陷，是 `_behavioural_source_digest` **自己的 docstring 已经写明**的性质
（`⚠️ NOT immune to docstring/string-literal edits -- those ARE Constant nodes`）：
`ast.dump` 丢的是 lineno 和 `#` 注释，而 docstring 是货真价实的 `Constant` 节点。
⇒ **两个读数写成 B 与 C 是对的**，但「纯注释」这四个字必须理解为**只有 `#` 注释**。
本单 R1 改写的占位标注里有 docstring，所以读数 C 里混着这一部分——D 就是把它单独量出来。

---

## 二、四项任务的落地

### R1 · 常量 6 mm → 10 mm + 占位标注改成签字记录

`AXIS_SNAP_MAX_DEVIATION_M = 0.006` → **`0.010`**（`tarch_normalize.py:127`）。

占位标注逐处核对，派工单列了 7 处，**实测 8 处**（只记不停）：

| # | 位置 | 原文 | 处置 |
|---|---|---|---|
| 1 | `tarch_normalize.py` 模块 docstring S1 段（原 15 行） | `⛔⛔ a PLACEHOLDER pending sign-off` | 改写为两道门 + 签字 |
| 2 | `tarch_normalize.py` 模块 docstring「no fabricated tolerance」第 4 条 | `it is an UNSIGNED placeholder` | 改写：**值已签、键仍不进 `judge_gt.yaml`**（理由是会作废已签 gt 的 content hash，与「签没签」无关）|
| 3 | `tarch_normalize.py` 常量块（原 96–130） | `⛔⛔ PLACEHOLDER, PENDING USER SIGN-OFF` | 整块重写为签字记录 + 风险记账 |
| 4 | `tarch_normalize.py` `_Tols.axis_snap_max_m` 字段注释 | `⛔ PLACEHOLDER, pending sign-off` | 改为签字指针 |
| 5 | `tarch_normalize.py` 判定点注释（原 489–490） | `EXPLICIT PLACEHOLDER PENDING USER SIGN-OFF` | 重写为两道门的说明 |
| 6 | `as_measured.py:331` 附近 `AsMeasuredAxisSnapV1` docstring | `⛔⛔ PLACEHOLDER, PENDING SIGN-OFF` | 改写为两道已签门 |
| 7 | `tests/test_as_measured_facts_layer.py:22` 与 `:533` | `placeholder, pending sign-off` ×2 | 改写并补上 0.091° 读数 |
| 8 | `tests/test_as_drawn_denominator_consistency_readout.py:134` | `the placeholder ...` | 同上 |
| **+1** | ⚠️ **派工单没列**：`as_measured.py:393` `axis_snapped_lines` 字段注释 | `(placeholder, pending-sign-off) snap threshold` | 一并改写 |

⇒ 全仓 `grep -i "placeholder\|pending sign-off"` 在吸附语境下**零残留**。

### R2 · ⭐⭐⭐ 新增角度门（本单本体）

新增具名常量 **`AXIS_SNAP_MAX_ANGLE_DEG = 1.0`**（`tarch_normalize.py:161`），⛔ 不是埋在表达式里的字面量。

**可注入，与 `axis_snap_max_m` 同构**（派工单 §二 R2 的硬要求）：
- `_Tols` 新字段 `axis_snap_max_angle_deg`（`:181`）
- `_tols_from(...)` 新关键字参数 `axis_snap_max_angle_deg`（`:210`）

⭐ 角度**天然无量纲**：`minor/major` 两边都是 native 单位 ⇒ **不存在漏做 `metres_per_unit` 换算的通道**。
故刻意**不给它加 `_native` 姊妹属性**（毫米门那个才需要），并在字段注释里写明理由。

判定改为两道门 AND：
```python
minor_leg = min(dx_raw, dy_raw)
major_leg = max(dx_raw, dy_raw)
angle_deg = math.degrees(math.atan2(minor_leg, major_leg))
mm_gate_ok    = minor_leg <= tols.axis_snap_max_native
angle_gate_ok = angle_deg <= tols.axis_snap_max_angle_deg
if mm_gate_ok and angle_gate_ok:   # 吸
else:                              # 拒，并记名是哪道门拒的
```

### R3 · 拒绝/吸附原因可观测

- `tarch_wall_axis_snapped` 的 `context` 增加 **`angle_deg`**（与既有 `minor_leg_mm` 并列）。
- `tarch_wall_nonorthogonal` **此前 `context` 是空的**（两种拒绝原因被压成同一个空白）。现在带：
  `refused_by`（`["deviation_mm"]` / `["angle_deg"]` / 两者）· `minor_leg_mm` · `major_leg_mm` ·
  `angle_deg` · `axis_snap_max_native` · `axis_snap_max_angle_deg`
  ⇒ ⭐ 门槛值一并写进记录，读的人不必回去翻当时的常量是几。

### R4 · 验收夹具

全部落在 `tests/test_tarch_converter_p1_geometry.py`，**通过 `_tols_from`/`_Tols` 的注入口驱动**，
⛔ **零 monkeypatch 模块属性**（派工单点名的 `from X import Y` 走父包属性那个坑）。

---

## 三、⭐⭐⭐ 六条验收 + 「不加这处改动本来是绿的」自证

### 3.1 实测结果

| # | 测试 | 输入 | 期望 | 实测 |
|---|---|---|---|---|
| ① | `..._acceptance_1_real_tremor_13ad_is_admitted_by_both_gates` | **真实** as-received `13AD`/`13AE`（真 DXF 走 `run_p1_plan_view`）| 吸 | ✅ 两条都吸，0 条拒；`angle_deg` 实测 **0.0914°**、`minor_leg_mm` **5.8084 mm** |
| **①b** | ⭐ **我自加**：`..._acceptance_1b_the_signed_10mm_deviation_value_has_teeth` | 2000 mm 长歪 8 mm（0.229°）| 吸（10 mm 下）· 拒（6 mm 下）| ✅ 见 3.3 说明 |
| ② | `..._acceptance_2_short_slant_passes_the_mm_gate_and_the_angle_gate_stops_it` | 60 mm 长歪 5 mm | 拒 | ✅ 拒；`angle_deg` **4.7636°**（派工单写 4.764°，吻合）；⭐ 断言里显式钉住 `minor_leg_mm <= axis_snap_max_native`（**毫米门确实放行了**）且 `refused_by == ["angle_deg"]` |
| ③ | `..._acceptance_3_forty_five_degrees_is_refused_by_both_gates` | 45° | 拒 | ✅ `refused_by == ["deviation_mm", "angle_deg"]` |
| ④ | `test_f147_signed_1deg_admits_the_0p39deg_slanted_wall_KNOWN_SIGNED_RISK` | 0.39° 缓斜墙两面、800 mm、各歪 5.5 mm、间距 120 mm | **会被吸**（签字风险）| ✅ 两面都吸（0.3939°）；⭐ 并断言**两条吸后中线仍相距 120 mm** —— 把「虚构墙怎么造出来的」这个机制写进断言，不只是「被吸了」 |
| ⑤a | `..._acceptance_5a_widening_only_the_angle_gate_flips_a_case` | 同 ② | 只放宽角度门 ⇒ 翻面 | ✅ 1.0° 拒 / 10.0° 吸，**毫米门全程不动** |
| ⑤b | `..._acceptance_5b_widening_only_the_deviation_gate_flips_a_different_case` | 2000 mm 长歪 20 mm（0.573°）| 只放宽毫米门 ⇒ 翻面 | ✅ 10 mm 拒 / 30 mm 吸，**角度门全程不动**；⭐ 断言 `angle_deg <= axis_snap_max_angle_deg`（**角度门确实放行了**）且 `refused_by == ["deviation_mm"]` |

⭐ ⑤a 与 ⑤b **被不同的门拒**（②靠角度、⑤b 靠毫米）⇒ **两道门不冗余，删掉任何一道都会放进其中一条**。

### 3.2 ⛔ 验收④ 的写法（派工单 §三的硬要求）

测试名带 **`_KNOWN_SIGNED_RISK`**；docstring 第一句即
`⛔⛔ THIS TEST PINS A COST THE USER KNOWINGLY ACCEPTED. ⛔ It does NOT assert that the behaviour is correct`。
正文写明：0.25° 会拒（**并在同一测试里实测断言了这个反事实**，`refused_by == ["angle_deg"]`）·
可选区间 `(0.091°, 0.394°)` · 主控建议过 0.25°/0.3° · 用户复述后仍选 1.0°、原话「签，角度调到 1 度吧」·
兑现代价 = walls 55→56 的虚构墙、与本项目 33 条虚构墙同一病族 · 补偿控制 = 人签 `revisions` 时逐条过目 `axis_snapped_lines`。
⛔ 全文无「正确 / 预期正确行为」字样。

### 3.3 ⭐⭐⭐ 变红自证：源码变异矩阵

⛔ **不写文件、全内存**（同机 GLM 在飞，不许动共享树）：把变异后的 `tarch_normalize` 源码
`exec` 成模块，同时装进 `sys.modules` **和父包属性** `src.agent.judge.tarch_normalize`
（⭐ 后者才是 `from src.agent.judge import tarch_normalize as tn` 真正读的地方，
只补前者会静默打空——本项目栽过这个），再断言 `test_module.tn is mutant` 才开跑。

| 变异（= 回到本单动手前的形态） | ①b 10mm | ① 13AD | ② 短斜 | ③ 45° | ④ 签字风险 | ⑤a | ⑤b |
|---|---|---|---|---|---|---|---|
| **M0** 未变异（理智检查） | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| **M1** 角度门不存在（R2 前） | PASS | PASS | **RED** | **RED** | **RED** | **RED** | PASS |
| **M2** 常量退回 6 mm（R1 前） | **RED** | PASS | PASS | PASS | PASS | PASS | PASS |
| **M3** 拒绝原因不记录（R3a 前） | **RED** | PASS | **RED** | **RED** | **RED** | **RED** | **RED** |
| **M4** 吸附不记角度（R3b 前） | **RED** | **RED** | PASS | PASS | **RED** | **RED** | PASS |
| **M5 = 完整的动手前形态** | **RED** | **RED** | **RED** | **RED** | **RED** | **RED** | **RED** |

⇒ **M5 一整行全红**：六条验收**没有一条**是「不加这处改动本来也是绿的」。
且 R1 / R2 / R3a / R3b **各自**至少有一条测试单独把它钉住（M1–M4 每行都有红）。

⭐⭐⭐ **①b 是这张矩阵自己抓出来的**：最初按派工单写完五条后跑矩阵，**M2 那一行七格全绿**
—— 即 **R1 的 6 mm→10 mm 落地时是没有任何锁的**。
病根是「夹具有没有存货」那条：**全语料在 6–10 mm 这个带里一条线都没有**
（只有 5.81 mm 那两条，两档都吸；20 mm 那条，两档都拒）⇒ 现有夹具在这个方向上**结构性无牙**。
修法 = **让夹具自己供一条**（2000 mm 长歪 8 mm，角度 0.229° 使角度门在两档下都放行 ⇒ 判决只由毫米值决定），
且**主张跑在生产默认值上**（不传关键字）⇒ 有人把常量改回去就红。

---

## 四、跑测

**受影响子集**（`affected_tests.py --changed` 判定，`-n 6` 前台，⛔ 无后台等待器）：
```
tests/test_affected_tests_map.py test_as_drawn_denominator_consistency_readout.py
test_as_drawn_denominator_f126.py test_as_measured_facts_layer.py
test_gt_facts_staging_case_admission.py test_gt_facts_staging_gate.py test_gt_facts_staging_sm25.py
test_gt_from_dxf.py test_gt_multifloor_world_snap.py test_gt_overlay.py test_gt_promotion_path.py
test_gt_raw_layer.py test_gt_revisions_and_as_signed.py test_tarch_converter_gate_mutations.py
test_tarch_converter_p1_geometry.py test_tarch_converter_p2_geometry.py
test_tarch_converter_reproducibility.py test_tarch_elevation_must_red.py test_tarch_opening_carriers.py
```
- **第一次**：`1 failed, 447 passed, 1 xfailed`（272.57s）
  —— 唯一红 = `test_gt_facts_staging_sm25.py::test_1_as_measured_matches_the_as_received_build_bit_for_bit`
- 处置见 §五
- **第二次（当前）**：**`448 passed, 1 xfailed`（280.12s）exit 0**

⛔ 全量归主控，本席位未跑全仓。⛔ 未跑 `pip install -e .` 或任何写 `site-packages` 的命令。

---

## 五、指纹翻了之后的处置（派工单 §五）

那条红的归因链已逐叶查清（见 §一①）：`as_measured.json` 落盘候选与新鲜重建差
**3 片叶子 = 1 个指纹 + 2 个新增 `angle_deg` 读数，几何字段 0 片**。

按 §五 的合法路径处置：
- ✅ 重新生成 **`gt_staging/`** 候选，用的是仓库既有的一次性生产脚本
  `AI_agent/logs/experiments/2026-08-29_o21b_facts_ledger/build_sm25_facts_staging.py`
  （⛔ **没有改 `src/agent/judge/gt_facts_staging.py` 一个字节** —— 那是**运行**它，不是编辑它）
- ⛔ **`case_tests/test_baseline/gt/`（答案根）零改动** —— `git status --porcelain case_tests/test_baseline/gt/` **输出为空**
- ⛔ **没有**扩 `KNOWN_PRE_F_D_CONVERTER_SHA256` 或任何「已知漂移清单」

⭐ **重新生成 ≠ 重签**，实证：`revisions.json` 的 diff **只有 `as_measured_content_sha256` 这一个反向引用变了**，
五条 revision 的 `finding` / `candidate_action` / `target` 全部逐字未动，
`verdict` 五条**依旧全是 `unsigned`**、`signed_by`/`signed_at` 依旧全 `null`。
（生产脚本自身也带断言 `all(r.verdict == "unsigned")`，会在任何试图签字的路径上炸。）

### ⚠️ 必须上报主控的一条（外围，不构成停报）

GLM 席位的 ②-1b-T-R 复核单
（`AI_agent/logs/reviews/verdict/2026-08-30_o21bTR_crossreview_glm.md`，当前**未跟踪**、⛔ 本单不提交它）
§〇 记了一条「环境干扰声明」：它在主树上撞到了**我这个 WIP 造成的**那条红，
并点名 `重建哈希 5591a8c3… ≠ 落盘 74b22e66…`、请主控知会 F-147 席位。

⇒ **两件事要报**：
1. **GLM 的读数没有被污染** —— 它自己发现了、正确归因了，并改用 `git archive e52d1ad` 的 `/tmp` 干净副本重跑，
   本审全部读数取自那份副本。⭐ 这正是「跑测途中树被第三方改掉」那条事故口径**第一次被下游当场接住**。
2. **它撞到的那条红现在已经关掉了**（§五的 staging 重生成，第二次子集跑 448 passed）。
3. ⚠️ 但**责任在我**：我在它审阅期间动了主树。派工单 §八没写「GLM 在跑，别动树」，
   而本项目 memory 里「送审后到裁决前不许动被审对象」「席位跑全量时连文档提交都不做」已同型三犯。
   ⇒ **建议主控把「同机有席位在飞时，施工席位动 `src/` 前先对一次表」写进下一版派工单模板**，
   本单靠 GLM 自己够细才没出事，⛔ 这不是防线。

---

## 六、⛔ 明确不做（派工单 §六）逐条核

| 禁令 | 核对 |
|---|---|
| `src/agent/judge/gt_facts_staging.py` 一个字节都不许动 | ✅ 不在 `git status` 里，**零改动** |
| `promote_gt_v3` · F-128 · F-132 · 出口全检 | ✅ 未碰 |
| `AnswerCompiler` / 出模两种形式 / edge `boundary_condition` / B1 外部指纹锚 | ✅ 未碰 |
| correction 侧任何改动 | ✅ `src/agent/correction/` 零改动 |
| 重签任何答案（答案根 `gt/`）| ✅ `git status case_tests/test_baseline/gt/` 输出为空 |
| ⛔ 不许「优化」`_snap_short_leg_to_axis` 取中点那条 | ✅ 该函数**逐字未动** |

---

## 七、`git diff --cached --numstat` 原文

```
301	0	AI_agent/logs/reviews/execution/2026-08-30_f147_angle_gate_execution.md
1	1	case_tests/test_baseline/gt_staging/sm25-L_anchor/facts/as_measured.json
1	1	case_tests/test_baseline/gt_staging/sm25-L_anchor/facts/as_signed.json
1	1	case_tests/test_baseline/gt_staging/sm25-L_anchor/facts/revisions.json
9	7	src/agent/judge/as_measured.py
129	50	src/agent/judge/tarch_normalize.py
3	1	tests/test_as_drawn_denominator_consistency_readout.py
7	4	tests/test_as_measured_facts_layer.py
264	2	tests/test_tarch_converter_p1_geometry.py
```

---

## 八、⭐ 我自己认为最薄弱的一处

**验收④ 的 0.39° 夹具是【合成】的，不是复核方那个真实的端到端负样本。**

派工单 §四 R4-④ 描述的原始负样本是在**真实 as-received 副本上端到端造出来的**
（两面各自吸到中点 ⇒ 配对出一堵虚构墙，**walls 55→56**）。
我的夹具在**单元层**复刻了这个机制的**前半段**：两面都被吸、吸后中线仍相距 120 mm ——
即「配对器会看到一堵完全正常的 120 mm 墙」这个**前提**被钉住了。

⛔ **但 `55→56` 那一步我没有实测。** 从「两条中线相距 120 mm」到「配对器真的多产出一堵墙」
之间还隔着 `_pair_face_lines_into_walls` 的准入条件五条，
⇒ 严格说我证明的是**「签字阈值确实放这个形状进来了」**，
⛔ 不是**「放进来之后一定会多出一堵墙」**。后者我是**引述派工单的实测**，不是自己量的。

**为什么没做到那一步**：真正端到端要在 as-received 副本上**改 DXF 造这堵墙**，
而本单跑在 GLM 复核的同一棵树上、且 §四① 要求我证明「几何产物逐字节不变」——
在同一轮里既造负样本又证不变，容易把两件事的产物搞混。**我选择了不冒这个险**。

⇒ **建议**：把「0.39° 负样本端到端复现 walls 55→56」单独登记一笔，
⭐ 且**它应该由跨家族的审方来跑**，而不是我 —— 因为这条恰恰是我这一单**唯一一处引述而非实测**的事实，
「谁写谁不批」在这里正好咬得住。

**次弱一处**：验收② 的 4.764° 与 ④ 的 0.39° 都是**我按派工单的描述合成**的输入。
其中 ② 我实测得 4.7636°、④ 实测 0.3939°，与派工单写的数吻合到 3 位小数，
但**它们证明的是「门在这些角度上的行为」，⛔ 不是「真实图纸上存在这些角度」**——
除 ①/①b 外，其余夹具都不是真实语料的存货（真实语料在 0.091° 与 45° 之间**完全没有存货**，这也是①b 的由来）。
