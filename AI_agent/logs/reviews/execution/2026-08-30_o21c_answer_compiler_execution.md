# 收工报告 · ②-1c：AnswerCompiler + 两种出模形式 + 依赖闭包

- **日期**：2026-08-30 · **施工席位**：GPT
- **派工单**：[2026-08-30_o21c_answer_compiler_dispatch.md](../request/2026-08-30_o21c_answer_compiler_dispatch.md)
- **开工分支 / HEAD**：`08.23_AsDrawnReading` / `88ea056d8d12ce3c8ccae377656e3709ee35d98f`
- **结论**：R1–R6 与 §六五项移交均已落地；验收 1a/1b、6a/6b/6c、B6 六条闭包、两形式变形关系、reading 同分与出口全检均有可执行锁。未触发 §七停报条件。

---

## 〇、开工自检与半成品处置

按用户要求，开工先完整阅读派工单、四份架构依据，并读取
`AI_agent/logs/experiments/2026-08-30_o21c_probe/README.md`。probe 目录只作线索；本次实现、论证、测试均在主树重新完成，没有把该目录当作验收证据，也没有提交其中内容。

### §1.6′ 承重数字

| 检查 | 要求 | 开工重测 |
|---|---:|---:|
| as-received `plan-F1.face_lines` | 224 | **224** |
| as-received `plan-F1.walls` | 55 | **55** |
| `s1_nonorthogonal_discarded_handles` | 0 | **0** |
| `rev-13ad.candidate_action` | `null` | **`null`** |
| `rev-13ae.candidate_action` | `null` | **`null`** |
| `rev-13af.candidate_action` | `null` | **`null`** |

四项承重前提全部相符，故继续施工。

### 对 probe 两处疑点的独立裁定

1. **`wall_bands` 不参与认墙、分母目标或投影。** live 分母改用生产几何的直接
   `cap_handles_v/cap_handles_h`；facts 侧仅在恢复历史审计项
   `would_be_excluded_by_converter_length_rule` 时，读取事实层中改名后的
   `jamb_cap_bands[].cap_handles`。理由不是“band 看起来像墙”，而是生产者
   `_build_wall_bands` 对 direct cap map 做分区，所有 band 的 handle 并集恰等于 direct map 人口。
   两栋真实建筑（sm24、sm25，各 plan view）已锁 `band union == direct map`；另有反事实锁：清空
   `jamb_cap_bands` 只让该历史审计数归零，`targets`、`allowed_not_required`、
   `opening_targets` 均逐位不变。故这条使用不会重开“33 条虚构墙”的认墙通道。
2. **F-126/R3 记账没有被删。** facts 适配器保留逐条
   `excluded_non_orthogonal_segments`，包含 handle、世界坐标端点和长度；明确只做 out-accounting，
   不推断吸附或替代几何。live 与 facts 共用同一 D1–D5 核心，避免两套算法漂移。

---

## 一、实现结果

### R1 / R5 / R6：一份事实的版本化派生器

新增 `src/agent/judge/answer_compiler.py`：

- `AnswerCompiler(profile)` 的 profile 只能是
  `form_a_axis` 或 `form_b_exterior_skin`；profile 是显式参数，证据和阈值不能替调用方选档。
- 形式 A：所有可解墙线投到中轴；形式 B：外墙投外皮、同层相邻房间墙投中轴。
- 编译器不读取事实层/S7 的任何 stored `basis`；它从 footprint、完整墙带和相邻 cavity 重新做射线判定。
  每条有效边记录 outward normal、exit point、判定结果；外墙另记录被穿过的 footprint ring/edge 及端点。
- 派生答案携带 `compiler_version=1`、`dependency_closure_version=1`、输入 facts/revisions/request 哈希和 profile。
- `clear_span_table()` 从 cavity 面积导出净空使用面积；`OutputProfile` 枚举中没有“净空”。
- `reproject()` 先验证传入形式确由同一 facts 派生，再从 facts 编译另一形式；A→B 与 B→A 两方向都锁定。
- NA ring 强制 `vertices=None`、`edges=[]`；Pydantic 模型自身拒绝“NA ring 带已投影边”。

### 头号验收 1a：真实行使已签 action 的合成台账

合成夹具有两间房与一堵 120 mm 内墙；台账中两条 revision 均为
`verdict=drawing_error`，且权威 `action=translate const +2`。`derive_as_signed` 后两条输入面线
从 `49400/50600` 变为 `49402/50602`，不是“答案碰巧等于 as_measured”。派生结果逐位为：

```text
形式 A left  = [(1200,58800),(50002,58800),(50002,1200),(1200,1200)]
形式 A right = [(50002,1200),(50002,58800),(98800,58800),(98800,1200)]
形式 B left  = [(0,60000),(50002,60000),(50002,0),(0,0)]
形式 B right = [(50002,0),(50002,60000),(100000,60000),(100000,0)]
```

### 头号验收 1b：真实 unsigned 必须响亮 NA

真实 sm25 形式 B 的实测：

```text
unresolved revisions = rev-13ac, rev-13ad, rev-13ae, rev-13af, rev-160a
plan-F1 = declared 14 / projected 11 / NA 3
plan-F2 = declared 15 / projected 14 / NA 1
```

- `rev-13ad/rev-13ae/rev-13af` 均以顶层具名
  `revision_has_no_signed_verdict` 出现，绝不把 as_measured 冒充签字值。
- 与 unresolved handles 相交的 wall group 产生 `unsigned_revision`，闭包传播到 incident ring；这些 ring
  均 `vertices=None / edges=[]`。测试同时要求至少存在真实 unsigned 作废 ring，防止只报名字却继续出坐标。
- 仍可投影的 **25 个** zone 全部按代表点唯一匹配现有 `gt.json` zone，且顶点集合逐位一致（F1 11 + F2 14）。
- 未签 revision 继续保持原样：五条 revision 相对开工 HEAD 逐对象相同；三条点名记录的
  `candidate_action` 仍为 `null`，五条 `verdict` 仍全为 `unsigned`，无真实重签。

### R2：6a / 6b / 6c

| 规则 | 正向实现 | 会红的反事实 |
|---|---|---|
| 6a | 相邻同 support line 合并，求交后再去重首尾/连续重复顶点 | 不去重时 fixture 明确产生相邻重复顶点和退化边 |
| 6b | support 以完整墙线为单位；同轴同 support 的连续片段合并 | 同一堵 240 mm 墙后半段按角色切到中轴，立即留下 120 mm support 台阶并不能合并 |
| 6c | 传播 support line，顶点由相邻正交 support 求交 | 内墙原 span 端点为 2400/57600，最终顶点为与外墙线相交所得 0/60000；原端点不进入结果 |

### R3：sol B6 六条依赖闭包

| # | 可执行夹具与结果 |
|---|---|
| 1 | 删除分隔墙：缺 segment 作废 incident rings；声明 2 个 zone 的分母仍是 2，不因缺失缩小 |
| 2 | 制造斜 footprint junction 并移除遮挡墙：junction 的 incident segments/rings 全作废，NA 无坐标 |
| 3 | 注入非轴保持 affine：view 坐标类结果全 NA，zone/area/opening 不泄漏坐标 |
| 4 | 注入 host 歧义 opening：只作废该 opening 与 opening metric；两个 zone 数和外轮廓继续 available |
| 5 | 强制 boundary=`unclaimed_void`：形式 A 仍可由 baseline/thickness 出模，形式 B 对相同 component/profile/metric NA |
| 6 | 缺 component 后 `coverage_expected` 保持 2，`available + NA == expected`；缺项保留为 NA slot |

metric 输出显式携带 required components、expected/available/NA coverage；模型验证器拒绝分母缩小或 status 与 coverage 不一致。

### R4：reading 题目册改从 facts 出

新增 `denominator_from_facts(view, request)`，live 与 facts 适配器共用 `_d1_d5_core`。
真实 sm25 `plan-F1/plan-F2` 上：

- `targets`、`allowed_not_required`、`opening_targets` 排序冻结后逐位相同；
- ledger 整体逐位相同；
- 对同一份 perfect reading，`scores` 和 `by_verdict` 逐位相同。

`AnswerCompiler.reading_exam()` 从同一 `as_signed + revisions + request` 派生所有 plan view 的题目册，并把 unresolved revision IDs 一并带到出口。

---

## 二、§六五项移交

1. **F-146 出口全检：已办。** `read_facts_for_compilation(case)` 若答案根
   `gt/<case>/facts/` 存在，则三件套每次读取均 parse + `verify_as_signed_reproduction`；入口外写入的
   schema-valid 篡改会红。目录存在但三件套不完整时响亮失败，绝不静默回退 staging。答案根 facts 尚不存在时，才调用既有 gated staging reader。
2. **NF-1：已裁定 writer 回 `None`。** `write_facts_candidate(...)->None`，docstring 同步；调用脚本与测试不再依赖返回 Path。
3. **NF-2：保持已知边界。** 本单没有引入 staging 并发写或 retry，TOCTOU 前提未改变。
4. **NF-3：未触发修复条件。** 本单没有并发 writer；未改 `.tmp` 清扫策略。
5. **NF-4 / F-148：已办。** `__all__` 锁改为“导出集合是允许集子集 + 两个必需函数存在”；
   `AsMeasuredAxisSnapV1.angle_deg` 为必填有限数 `[0,90]`，transport 从同 handle diagnostic 搬运，validator
   锁定 row handle 集合/唯一性/角度逐位一致。`tarch_normalize.py` 只改 `#` 记账注释，未改阈值、AND 或取中点。

NF-2/NF-3 没有被“顺手修”；这与派工单裁定一致，也避免在共享 staging 上新增未授权并发语义。

---

## 三、staging 重生成边界与逐字段 diff

F-148 新必填字段使既有 staging 必须用仓库原生产脚本重生成。答案根
`case_tests/test_baseline/gt/` 的 `git status` 为空；本次只刷新 staging 候选，**重新生成不等于重签**。

相对开工 HEAD 的递归 JSON diff：

```text
as_measured.json (2 leaves)
  views[0].converter_readouts.axis_snapped_lines[0].angle_deg: absent -> 0.09142935778784271
  views[0].converter_readouts.axis_snapped_lines[1].angle_deg: absent -> 0.0914293577882342

revisions.json (1 leaf)
  as_measured_content_sha256:
    5591a8c3265a7a311b47e795ebfe9385e69acb0588aa55ea01bdd7b405b61a3a
    -> 37f6103541f27c6799cd12baf068afeeb37a7fb7d5b820242dfb0a790a64eb0e

as_signed.json (4 leaves)
  derivation.as_measured_content_sha256: 同上
  derivation.revisions_content_sha256:
    09e92a7e4812283e847aed0afe86624b463afe982c5a2d7a381aa3ad367923ca
    -> 6d576756f7b55a457239ed4a27e6bbe172a930a5649f4d161ca80f618ae4f362
  两条 axis_snapped_lines[].angle_deg: 同 as_measured
```

五个 revision 对象逐对象相同。转换器指纹也前后完全相同：

```text
d5825959b9f09c5909bb5c3f2bb46d18397526858d3495e800c01fd171cd81bb
```

---

## 四、测试与环境哨兵

### affected_tests.py 判定

以全部改动的一等 Python 路径调用 `scripts/tool_scripts/affected_tests.py --changed ...`，结果
`SCOPE: SUBSET`，选中 23 个测试文件：

```text
test_affected_tests_map.py
test_answer_compiler_closure.py
test_answer_compiler_exit_gate.py
test_answer_compiler_profiles.py
test_as_drawn_denominator_consistency_readout.py
test_as_drawn_denominator_f126.py
test_as_measured_facts_layer.py
test_denominator_from_facts.py
test_gt_facts_staging_case_admission.py
test_gt_facts_staging_gate.py
test_gt_facts_staging_sm25.py
test_gt_from_dxf.py
test_gt_multifloor_world_snap.py
test_gt_overlay.py
test_gt_promotion_path.py
test_gt_raw_layer.py
test_gt_revisions_and_as_signed.py
test_tarch_converter_gate_mutations.py
test_tarch_converter_p1_geometry.py
test_tarch_converter_p2_geometry.py
test_tarch_converter_reproducibility.py
test_tarch_elevation_must_red.py
test_tarch_opening_carriers.py
```

全程前台、统一 `-n 6`、没有后台等待器：

- AnswerCompiler/迁移项定向集：**87 passed**。
- 首轮完整子集：`470 passed, 1 failed, 1 xfailed`；唯一失败是 `answer_compiler` 新引用使
  `reading_grade.py` 已真实进入测试可达图，而旧 uncovered allowlist 仍声称它无覆盖。
- 删除这一条已经说谎的 allowlist 记账后，映射测试 **15 passed**。
- 最终完整受影响子集：**471 passed, 1 xfailed, 28 warnings，exit 0，248.71s**。
- 加强验收 1b 的“真实 unsigned ring 必须零坐标”断言后，profiles 文件再跑：**8 passed**。

`ruff` 不在现有环境中；未安装它、未写共享 venv。`affected_tests.py` 已成功 AST 解析全仓一等 Python 文件，`git diff --check` 为空。按派工单，全量归主控，本席位未跑全仓。

### `.pth` / HEAD 前后原文

```text
BEFORE HEAD   88ea056d8d12ce3c8ccae377656e3709ee35d98f
AFTER  HEAD   88ea056d8d12ce3c8ccae377656e3709ee35d98f

BEFORE MODULE /workspaces/EnergyPlus-Agent-dev/src/agent/judge/as_measured.py
AFTER  MODULE /workspaces/EnergyPlus-Agent-dev/src/agent/judge/as_measured.py

BEFORE PTH /opt/venv/lib/python3.12/site-packages/_editable_impl_energyplus_agent.pth
  sha256 58f547fa9433af6eca0e8f362652b78916b13a21fbeab4ef06f1e07e46744e43
  bytes  '/workspaces/EnergyPlus-Agent-dev'
AFTER  PTH 同路径、同 sha256、同 bytes
```

### 已签 request 前后原文

| 文件 | file sha256（前 = 后） | stored = recomputed `compute_request_sha256`（前 = 后） |
|---|---|---|
| sm24 `request.json` | `34b7d74959e8a8c644d7082d952fddcf9a16bb9407c620ad1dfa303cff1e23b9` | `ae0fec087ef2a04814f3dbffc31553b25ea8e1c1d98eedf0b4ae383a7d4ac8a2` |
| sm25 `request.json` | `e635ab116e21407734a093d2dc07194899a901d801d3d57624b3fa908d9396df` | `d738d0ac230f21ae20f477b1cc084549f1308bff295a3f6de8956da98d25a135` |

---

## 五、范围与禁令核对

- 没有建 worktree、没有切分支；一直在用户指定主树。
- 没有 `pip install -e .`，没有任何写 `site-packages` 的命令。
- 没有改 correction / geometry 判定逻辑、`promote_gt_v3`、F-128、F-132 或答案根。
- 没有实现 `boundary_condition` 字段化；编译器只做本单获准的独立重判与证据留痕。
- 没有把净空加入 profile 枚举，没有引入 staging 并发或 retry。
- 派工单 §四三处预裁张力均按裁定执行：1a 只用 synthetic 签字；真实五条仍 unsigned；F-148 只改落库形态/注释；采用 `#` 注释避免转换器指纹翻转。

## 六、改动路径

```text
AI_agent/logs/experiments/2026-08-29_o21b_facts_ledger/build_sm25_facts_staging.py
AI_agent/logs/reviews/execution/2026-08-30_o21c_answer_compiler_execution.md
case_tests/test_baseline/gt_staging/sm25-L_anchor/facts/as_measured.json
case_tests/test_baseline/gt_staging/sm25-L_anchor/facts/revisions.json
case_tests/test_baseline/gt_staging/sm25-L_anchor/facts/as_signed.json
scripts/tool_scripts/affected_tests_rules.yaml
src/agent/judge/answer_compiler.py
src/agent/judge/as_drawn/denominator.py
src/agent/judge/as_measured.py
src/agent/judge/gt_facts_staging.py
src/agent/judge/tarch_normalize.py
tests/answer_compiler_fixtures.py
tests/test_answer_compiler_closure.py
tests/test_answer_compiler_exit_gate.py
tests/test_answer_compiler_profiles.py
tests/test_as_measured_facts_layer.py
tests/test_denominator_from_facts.py
tests/test_gt_facts_staging_gate.py
```

提交只会 `git add` 上述明确路径，不使用 `git add -A`。
