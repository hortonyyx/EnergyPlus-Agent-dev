# 交叉审裁决书 · F-19（`kernel.window_parent_binding` 恒红）· GLM-5.2

- **日期**：2026-08-10 · **审阅席**：**GLM-5.2**（跨家族验证性审阅）· **只读，零代码改动**
- **审阅对象**：单提交 **`d103c3e`**（分支 `6.15_ValidationArchM0toM4`，其上 HEAD=`74b0335`）
- **修法**：`src/validator/checks/kernel.py` `_window_parent_binding` 复算侧 `fresh_vertices` 加一次 `canonicalize_ring_vertices`（用其自身 Newell 法向），与 `build.py:_canonicalize_bg_vertices` 对 built 侧的处理同构；比较仍精确 `!=`。
- **为什么这一审**：本修法 = Claude 侧 Sonnet 施工 + Claude 侧 orchestrator 轻门（同家族自产自验）。本项目 08-09 刚实证：自验做满、外观合格，跨家族审仍抓出「headline 锁根本不是锁」。**本审防的是那一类。**

---

## 总裁决

# **APPROVE-WITH-CHANGES**

| 级别 | 计数 |
|---|---|
| BLOCKER | **0** |
| MAJOR | **0** |
| MINOR | **0** |
| NIT | **2** |

**结论**：修法方向正确（复算侧共用同一份 `canonicalize_ring_vertices`，未加容差、未加循环旋转豁免）；**4 把锁全部真绑目标门**（两向 neuter 精确命中、零 false lock、零过度连带）；**真实产物经我独立重跑确认通过**（15/15 正确放行、15/15 反转拦下）；C3 守卫经代码论证 + 三处实证确认**不是静默豁免口子**。未发现 08-09 那类「锁红但红错位置 / headline 锁不绑」的 false lock。两条 NIT 均为 commit message 已声明 / 请求书已知的卫生项，不阻塞。

---

## C1–C6 逐条（**全部成立**，附我自己的证据）

### C1 · 独立全量 **2345 passed / 10 xfailed / 0 failed** —— ✅ 成立

我自己跑，**未看任何他人日志**。命令与请求书 §5 逐字一致：

```
python -m pytest -p no:cacheprovider -q -n 8 > /tmp/f19_full.log 2>&1; echo $? > /tmp/f19_full.rc
```

- `/tmp/f19_full.rc` = `0`
- 汇总行：`2345 passed, 10 xfailed, 209 warnings in 525.76s (0:08:45)`
- 与声称的「基线 2339 + 6 = 2345，零回归」**逐字一致**。

### C2 · 4 把锁全部真绑 —— ✅ 成立（见下方逐锁 neuter 表）

本次补的 4 把锁 = `tests/test_c2_b5_parent_and_verts.py` 的 **7 个测试用例**：
`test_f19_l1_gate_passes_on_real_build_geometry_output[South/North/East/West]`（4）· `test_f19_l2_gate_would_fail_without_fresh_side_canonicalization`（1）· `test_kernel_fresh_recompute_rejects_built_vertex_tamper`（L-3，1）· `test_f19_l4_reversed_winding_still_caught`（1）。

**夹具合规性核实**（请求书 §3 形状3「夹具自洽不算数」的核心问）：
`_bundle()`（`tests/test_c2_b5_parent_and_verts.py:253`）**真的调 `build_geometry(...)`** ⇒ `bundle.bg.windows[*].verts` 确经 `_canonicalize_bg_vertices`（build.py:80-85）规范化，**不是手搓 `BuildingGeometry(...)` 塞顶点**。派工单 §0 Q2 满足。四朝面参数化经 `_plan_geometry(facade)`（:142）返回四套**真实不同**几何（South/North 落 y 边界、East/West 落 x 边界），覆盖 sign/axis。

### C3 · 比较仍精确 `!=`，守卫非静默豁免 —— ✅ 成立（守卫非豁免口子；详见专节）

### C4 · 真实产物走真实入口重跑 ⇒ `deterministic_pass` —— ✅ 成立

我用**官方入口** `materialize_kernel_geometry → check_kernel`（即 `run_stage.py:_draw_modelling` 同款逻辑）对真实产物 `run_2026-08-09_f18_e2e_verify` **独立重跑**（materialize 写到 `/tmp`，未污染真实 run 目录）：

```
manifest=RunManifestV2, accepted(1_correction)=attempt 001, artifact_contract=correction_b5_v1
geom=CorrectedGeometryV3, proof=VerifiedWindowHostProof
bg.windows=15, bg.surfaces=100, geometry_contract 走 c2_b5_v1
[C4] 正确绕向 window_parent_binding = pass  (offenders=0)
```

落盘产物亦一致：`2_modelling/attempts/001/checks.json` = `window_parent_binding=fail offenders=15`（修法前）→ `attempts/002/checks.json` = `pass`（修法后）；`kernel_gate_report.json` 的 `gate_issues=[]`、`build_notes=[]`（零 block 零 flag）。

### C5 · 真实 15 窗：正确 15/15 放行、反转 15/15 拦下 —— ✅ 成立

在同一真实产物上量（15 窗来自 07-07 sm21 识图 → correction → 真实几何，**非夹具自洽**）：

```
[C5] 正确绕向: offenders=0                       ← 15/15 放行
[C5] 全反转绕向: status=fail offenders=15        ← 15/15 拦下
[C5] 逐窗反转: 15/15 个窗反转后门 fail (offenders=1)
[C5 sanity] 不反转基线 offenders=0
```

⇒ 「窗挂错房间」防线未被削弱（反转 ⇒ 法向翻转 ⇒ 内外面翻 ⇒ built 绕向反 ≠ fresh 正确绕向，被精确 `!=` 抓住）。

### C6 · 同族排查 0 新命中，调用点清单完整 —— ✅ 成立（我独立数）

`grep -rn` 全 `src/`（排除定义/import/注释/`.pyc`）：

**`window_verts_on_line` 的 4 个消费点**（与声称一致）：
| # | 位置 | 角色 | F-19 同类风险？ |
|---|---|---|---|
| 1 | `src/agent/geometry/modelling.py:819` | `build_geometry` 内部生成 verts | ❌ 之后被 `_canonicalize_bg_vertices` 规范化；不比较 |
| 2 | `src/agent/correction/window_host.py:638` | correction 阶段 `fresh` vs `declared`（带容差 `_same_resolution_representation_close`） | ❌ 两侧都不经 build 规范化；不与 build 输出比（实为 F-18 修复点） |
| 3 | `src/agent/correction/window_host.py:955` | correction 生产方生成 `clamped_vertices` | ❌ 生产方，不比较 |
| 4 | `src/validator/checks/kernel.py:354` | **本次修法处**（fresh vs built） | ✅ 唯一"拿 fresh 与 build 规范化输出比较"处，**已修** |

**`canonicalize_ring_vertices` 的 4 个调用点**（与声称一致）：`build.py:78`（surface）、`build.py:84`（window）、`kernel.py:398`（本次修法）、`data_model.py:1338`（`GeometrySchema` 内部委托 = gate① validator 自己的规范化，与 build 用同一函数 ⇒ F-13 r1 设计目标"build 输出过 gate① 成恒等"）。

⇒ **0 个新同类风险**（4 个消费点里仅 kernel:354 与 build 输出比较，已修）。

---

## 逐锁 neuter 结果表（**均在 `/tmp/f19_neuter` 副本，未动工作树**）

副本 = `cp -a src tests pyproject.toml /tmp/f19_neuter/`（**不含 `case_tests/`，未碰 gt**）。每次跑前 `find ... -name __pycache__ -exec rm -rf`。命令行 `-n0 -o addopts=""` 覆盖默认 `-n auto`。

| neuter | 改动（副本 kernel.py） | 转红 | 连带 | 该红没红 |
|---|---|---|---|---|
| **基线** | （修法后原样） | — | 8 passed（7 锁 + 1 既有 `test_correction_validator_fresh_recompute_passes_and_missing_proof_blocks`） | — |
| **neuter1**：摘掉 fresh 侧规范化块（`fresh_normal`/`canonicalize_ring_vertices` 整块删除，只留 `if built.verts != fresh_vertices:`） | 还原缺陷形态 | **L-1 ×4 + L-2 + L-3 + L-4 = 7 全红**；既有 1 仍绿（不测本门顶点比较） | 无过度连带 | 无 |
| **neuter2**：精确 `!=` 改 `sorted(built.verts) != sorted(fresh_vertices)`（模拟「集合/循环旋转等价」过度豁免） | 模拟派工单 §2.2 禁止的豁免 | **只 L-4 红** | 零（L-1×4/L-2/L-3 保持绿） | 无 |

**neuter1 各锁红点位置**（防 08-09 那类「锁红但红错位置」）：
- **L-2** 红在**最终断言** `assert gate.status.value == "pass"`（`'fail' == 'pass'`）；**前提 `raw_fresh_vertices != built_vertices` 不红** ⇒ 精确符合"自证前提"设计（前提独立重构旧行为，不调修法代码）。
- **L-3** 红在 **premise** `assert clean_gate.status.value == "pass"`，报错文案 `"premise broken: the unmutated bundle already fails"` ⇒ 精确符合"修复假锁"设计。
- **L-4** 红在 **premise**（`assert clean_gate.status.value == "pass"`）。
- **L-1** 无 premise，红在主断言 `gate.status.value == "pass"`。

**判读**：4 把锁全部真绑修法；**无 false lock**（没有任何一把"摘掉修法仍绿"）；neuter2 证明 L-4 精确锁住"过度豁免"且仅锁这一条。这是本审最关键的结论 —— **08-09 sol 抓的「headline 锁用变换前宿主线」那类 false lock，本批不存在**。

---

## C3 守卫判定（请求书特别点名）

**守卫**（`kernel.py:394-401`）：
```python
fresh_normal = _newell(fresh_vertices)
if float(np.linalg.norm(fresh_normal)) >= 1e-9:
    fresh_vertices = [... canonicalize_ring_vertices(np.asarray(fresh_vertices, dtype=float), fresh_normal) ...]
if built.verts != fresh_vertices:
    issues.append({**prefix, "reason": "built_vertices"})
```

**问题**：法向退化（norm < 1e-9）时 `fresh_vertices` 保持未规范化、走回旧行为。这条分支有没有锁？是不是静默豁免口子？

### 判定：**不是静默豁免口子**（代码论证 + 三处实证）

**① 与 build.py 逐字对称**：`build.py:_canonicalize_bg_vertices:76/82` 对 built 侧的退化守卫是 `if float(np.linalg.norm(normal)) < 1e-9: continue`（退化跳过规范化）。kernel 侧 `>= 1e-9` 才规范化 ⇒ **两侧在退化时都不规范化**，退化窗仍走精确 `!=` 比较。对称，不构成"一边豁免"。

**② 实证：真实 15 窗 `fresh_normal` norm 全部 = 1.000000**（min=max=1.0；脚本 `/tmp/f19_c3.py`）⇒ **守卫对真实窗从不触发退化分支**（15/15 ≥ 1e-9，全走规范化）。退化分支对真实产物是完全惰性的。

**③ 实证：退化攻击不静默放过**。把窗0 的 `built.verts` 替换成共线退化（Newell norm=0），门仍 `status=fail`（offenders=1，reason=`built_vertices`）—— fresh 非退化（norm=1）走规范化、与退化 built 不等 ⇒ fail。**没有"两边都退化 ⇒ 原始相等 ⇒ 静默 pass"的逃逸**（fresh 来自 `window_verts_on_line`，恒为单位化矩形 norm=1，不会退化）。

**④ 反转绕不开守卫**：反转窗的 Newell norm 不带符号、不变（仍=1.0），仍 ≥ 1e-9 走规范化 ⇒ 被 C5 的 15/15 反转拦下覆盖。

⇒ 守卫不是豁免口子。它只在 fresh 真退化（共线/零面积）时跳过规范化，与 build.py 对称；而 fresh 恒不退化（生成器产出单位化矩形）。

### 关于"要不要补锁"

退化分支**无专门锁**。逻辑正确、与 build.py 对称、实证安全，但按本项目"无锁的静默分支值得标注"的纪律，列为 **NIT-2**（建议补一个退化窗行为锁以防阈值漂移；与 build.py 同款对称缺口同级）。**不阻塞**。

---

## NIT（2 条，均不阻塞）

- **NIT-1（commit message 已声明）**：正向锁 L-1 / L-2 / L-4 走私有 helper `_window_parent_gate`（`tests:295`，直接构造 `CheckReport` 调 `_window_parent_binding`），**不走真实入口 `check_kernel`**；仅 L-3 走 `check_kernel`。helper 调的是门函数本身（门逻辑完整），差别只是不经 `check_kernel` 的分发/前置，对正向锁结论无影响。建议未来把正向锁也走 `check_kernel`，以防 helper 与真实入口将来漂移。
- **NIT-2（见 C3 守卫节）**：`kernel.py:395` 的 `>= 1e-9` 退化分支无专门行为锁。当前实证安全，建议补。

---

## 我**没能**完全验证的部分（如实列出，⛔ 未用推理填）

1. **§2.3 全表穷举未独立复现**：派工单 §2.3 要求"机械排查所有拿【未规范化】顶点与 `build_geometry` 输出比较/断言的地方"，覆盖 `src/validator/`、`src/agent/geometry/`、`src/agent/`（含 `output_coordinates.py` 漂移门）、`tests/`。我**只独立验证了 `window_verts_on_line` 的 4 个消费点 + `canonicalize_ring_vertices` 的 4 个调用点**（结论：0 新同类风险）。`output_coordinates.py` 的 `_live_idf_vertex_drift_issues` 等**其余顶点比较路径未独立穷举** —— 该理论缺口 commit message 已如实标注"未证实、不计入命中"，且请求书明示"需独立调查才能坐实或排除 —— 不是本单任务"，故本审未展开。
2. **未用 `run_stage.py` CLI 跑整条 flow**：我用 `materialize_kernel_geometry → check_kernel` 重跑了 2_modelling 的核心 build+check（这是 F-19 门所在段，对 F-19 验收充分），未端到端跑 0→5 全 flow。整 flow 的下游段（3/4/5）不在 F-19 射程内。
3. **执行日志未读**：`d103c3e` 含的执行日志 `2026-08-09_f19_window_parent_binding_claude.md`（248 行）我**未采信其自陈**作为证据；所有结论均来自我自跑的命令输出 / 文件行号 / `/tmp` 副本 neuter。

---

## 方法论备注（供 orchestrator 参考）

- **neuter 隔离方式**：`cp -a` 副本（非 `git worktree`，避免任何 git 状态变化），副本不含 `case_tests/`（从结构上不可能碰 gt）。
- **观测通道纪律**：所有 pytest 输出直接重定向到文件、退出码单独落 `.rc`、中间零管道（遵请求书 §5 与 08-09 教训）。
- **判别问法的兑现**：每把锁都答了"把修法那一行还原成缺陷形态，这把锁红不红"（neuter1）+ "把比较放宽，这把锁红不红"（neuter2），并核对了红点位置（防"红错位置"）。
- 本审工作树**零改动**、零 `git add/commit`、未碰 65 个未跟踪项、未读 `case_tests/test_baseline/gt/`。
