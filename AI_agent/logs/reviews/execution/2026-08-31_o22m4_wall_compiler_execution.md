# 执行档 · ②-2 模块 4 `correction/wall_compiler.py`（ref resolve · 切段 · 中线/候选/厚度 IR）

- **日期**：2026-08-31 · **施工方**：GLM 家族（原席位续做，`85e95c7d`，中途 429 中断后按用户拍板原样还原续作）
- **派工单** → [../request/2026-08-31_o22m4_wall_compiler_dispatch.md](../request/2026-08-31_o22m4_wall_compiler_dispatch.md)（含 §七续做说明 / §八环境提示）
- **交付物**：`src/agent/correction/wall_compiler.py`（新，约 1420 行）· `tests/test_o22m4_wall_compiler.py`（新，22 个测试）·
  `tests/test_o22m3_evidence_adapters.py`（只翻了一条 pin + 同步它的头部 docstring，见验收 2）
- **⛔ 未提交**（禁令 7）；⛔ 未 `pip install -e .`；跑测全部 `-n 4`；⛔ 未动 `vector_contract.py` / `pipeline.py` / `judge/` / 已落库产物。

## 〇、§八要求的读数基线状态（先立此柱，下面全部读数取自它）

```
$ git diff --stat 6637f38 -- src/agent/correction/evidence_contract.py
 src/agent/correction/evidence_contract.py | 128 ++++++++++++++++
 1 file changed, 128 insertions(+)
$ sha256sum src/agent/correction/evidence_contract.py
 6d38db37f7b61dbb…（截断显示）
```

即：本单全部读数取在**我自己的模块 2 第二轮返工在途件**（+128 行：`zero_payload_channel` debt + 载荷闭合门 + 单源校验）之上，
模块 3 已收口件不变。`judge/` 相对基线 `6637f38` **当前整目录零 diff**（GPT 席位的 F-154 在本档落笔时点尚未落盘）。

---

## 一、§七两条点名红的真因与修法（⛔ 都不是我越过了边界，但一条暴露了锁本身量错了对象）

### 红 1 · `test_compiler_imports_neither_pipeline_nor_judge`（零接线锁）

**真因（机械追到链尾）**：judge 进 `sys.modules` 是 `correction` 包的**既有传递链**，与本模块无关：

```
任意 from src.agent.correction.X import …
  → 先执行包 init → window_sources.py:25 `from src.agent.reading import parse_reading_view`
  → src.agent.reading（大包）→ … → src.agent.execution.step_orchestrator
  → step_orchestrator.py:64 `from src.agent.judge.verdict import …`（模块级）
  → {judge, judge.executor, judge.retry, judge.verdict} 四件进 sys.modules
```

**实证**：干净子进程单独 import **模块 2 已收口过审的** `evidence_contract`（乃至 `window_sources` 本身），
judge 可达集与 import 本模块**逐字相同**：

```
$ python -c "import sys; import src.agent.correction.evidence_contract; print(sorted(m for m in sys.modules if m=='src.agent.pipeline' or m.startswith('src.agent.judge')))"
['src.agent.judge', 'src.agent.judge.executor', 'src.agent.judge.retry', 'src.agent.judge.verdict']
（对 wall_compiler / window_sources / evidence_adapters 四个目标，输出逐字相同）
```

⇒ 原判据「judge 不出现在 sys.modules」在这个包里**结构性不可能绿**——它量的是包的既有基座，不是本模块的接线
（[[instrument-blind-to-the-asked-quantity]]）。模块 3 当年的锁只查了 `pipeline`，所以这条既有链从未被暴露。

**修法（比原判据更强，不是放水）**：改成两把更硬的锁 `test_compiler_adds_no_pipeline_or_judge_edge_beyond_module_2`——
1. **差集判据**：import 本模块后的 pipeline∪judge 可达集，必须与 import 模块 2 契约后的**完全相等**（本模块零新增）；
2. **AST 判据**：解析本模块源码的全部非标准库 import，白名单只有
   `{evidence_contract, window_sources, pydantic}`（= 模块 2 自己的依赖面）——将来长出第三条 import 在 diff 上就红。

（执行中实犯一次：白名单首版漏了 `pydantic`，AST 锁当场咬红自己——锁在工作的证据，补上。）

### 红 2 · `test_selected_pair_values_are_recomputed_not_cached`（重算锁）

**真因：测试自己的前提选错了夹具，编译器无辜**。红的那行是前提断言：

```
> assert pair0["spacing_m"] != expected  # premise: cache really differs
E assert 0.2384 != 0.2384
```

sm25_1f 的 `pairs[0]`（L001/L002）缓存值恰好**等于**重算值；真有分歧的是 L005/L007 等另外几对
（缓存 `0.238` vs 重算 `0.2379…`，我在中断前的预计算输出里就把这行读错了列）。
编译路径本身没读缓存——断言行没红、红在前提行。

**修法**：前提不再锚定「pairs[0] 恰好有分歧」这种位置巧合，改为在产物里**实测找出第一对真分歧的 pair**
（`next(p for p in pairs if p["spacing_m"] != abs(Δpos))`），对它做缓存污染（spacing_m/spacing_px→999.0、overlap_px→-1），
断言编译读数纹丝不动。docstring 写明：若将来产物重生成导致缓存全一致，这条前提会红——那是换夹具的信号，不是删前提的信号。

---

## 二、八项验收逐条（命令 + 读数）

### 1 · ⭐ 余段保真双向 ✅

`tests/test_o22m4_wall_compiler.py::test_paired_face_unshared_tail_survives_as_single_face_fragment` +
`::test_equal_coverage_produces_no_fragment`（合成夹具，runs px→m 后 A=[1,10] / B=[1,4]）：

- 不等长：`double_face_intervals == ((1.0, 4.0),)`；**1 条 fragment**，`source_claim_id == 原 paired claim 的 claim_id`、
  `tail_of == "face_a"`、`along_interval_m == (4.0, 10.0)`；墙自身覆盖 = 并集 `((1.0, 10.0),)`；
  中线常量 = 两面 `pos_m` 的中点（1.0 与 1.12 → 1.06）。
- 等长：`unshared_tail_fragments == ()`、`double_face_intervals == ((1.0, 8.0),)`、全编译零 fragment
  ——「无条件切碎」在这个方向过不去。
- 真实产物读数（exploratory）：sm24 余段 **20** 条、sm25_1f 余段 **85** 条（与我从产物独立手算的区间算术结果一致）。

### 2 · ⭐ 模块 3 那条 pin 已翻 ✅

`tests/test_o22m3_evidence_adapters.py`：`test_tail_segmentation_is_pinned_to_module_4` **删除**，替换为
`test_tail_segmentation_is_delivered_by_module_4`——保留模块 3 边界半（bundle 对等长/不等长**形状相同**，
该层不算几何），新增模块 4 半（调 `compile_wall_ir`：不等长 → 1 条 fragment 回指原 claim；等长 → 0 条）。
头部 docstring 的第 4 条验收描述同步改写。这是对既有测试的**唯一**改动（禁令 5 的例外）。

```
$ git diff --stat 6637f38 -- tests/test_o22m3_evidence_adapters.py
 tests/test_o22m3_evidence_adapters.py | 60 ++++++++----   （pin 翻转 + docstring 同步，仅此）
```

### 3 · ⭐⭐ ambiguous debt 被消费（sm24 双 profile）✅

```
$ python -c "…sm24_1f_v2.json → adapt_as_drawn_plan → compile_wall_ir(art, profile=…)"
strict        -> AMBIGUOUS_DEBT_BLOCKS_STRICT_PROFILE: faces=78/98 ratio=0.7959 debts=78 remedy=wall_level_reperception
exploratory   -> completion=degraded walls=12 {solid_band:4, paired_faces:8} fragments=20
                 undecided=78/98 residual_debts=81 content_sha=74caed91be26
```

- **strict**：78 条 debt **逐条点名**（`debt_ids` 78 个）、未决比例 78/98、每面的候选图参与数（首例 L002 参与 14 条候选）。
  测试 `test_sm24_strict_blocks_on_ambiguous_debt_and_names_every_one` 里，参与数与**从产物独立重算**的计数逐面相等。
- **exploratory**：继续编译（12 墙不丢），`completion="degraded"`，`undecided = 78/98 = 0.7959…` 报在台账上，
  78 条 debt 全部保留在 `residual_debt_ids`，78 条逐面分析（`topology_exposure="candidate_graph"`）随行。
- ⛔ 没有静默跳过：strict 的阻断是运行时 raise（`WallCompilerError`），不是 docstring。

### 4 · 四堵 solid band 不丢 ✅

`test_sm24_four_solid_bands_become_walls_without_fake_faces`：4 条 `solid_band` claim → 恰好 4 面
`claim_kind="solid_band"` 的墙（总墙数 12 = 8 paired + 4 band，无新增）；每面墙 `source_refs` **恰好 1 条**
（没有给墨带伪造搭档面）；`observed_face_spacing_m` = 产物 `edges_m` 两边之差（独立重算，四条 = 0.2751/0.3025/0.3025/0.3026 m）；
中线常量 = 两 edge 中点；`observed_basis="ink_band_edges"`。

### 5 · 厚度活到 kernel：三个名字分开 + 每个的来源 ✅

`test_three_thickness_names_separated_with_provenance` + `test_thickness_decision_produces_the_resolution_record`
+ `test_selected_pair_values_are_recomputed_not_cached` + `test_observed_spacing_and_resolved_thickness_survive_kernel_entry`
（sm25_1f 真实产物，声明 callouts = [240, 120]）：

| 名字 | 来源（provenance 字段机械区分） | 读数 |
|---|---|---|
| `observed_face_spacing_m` | `observed_spacing`（两面 pos_m / 墨带两 edge **重算**） | 例：L001/L002 = 0.2384；缓存污染成 999.0 后**不动** |
| `resolved_thickness_m` | 决定执行前恒 `None`；执行后 = 所选候选的值 | KEEP→观测值；SNAP(0.24)→0.24 |
| `thickness_resolution` | `source_values[].provenance ∈ {observed_spacing, declared_callout, declared_field, matched_label}` | KEEP→`["observed_spacing"]`；SNAP(240)→`["declared_callout","matched_label"]` |

- 候选枚举 = `{KEEP_OBSERVED_WIDTH} ∪ {SNAP_TO_DECLARATION(每个声明 callout)}`，即 sm25_1f 每面观测墙 3 个候选；
  **`matched_declared_mm` 只是标签**：SNAP 的值永远取自声明 callout，标签仅在同毫米数时作为额外语义 riding along（§5.3 逐字兑现）。
- ⛔ 观测量没有事实性名字：字段名是 `observed_face_spacing_m`，不是 `thickness_m`。

### 6 · ⭐ 中线只在本层派生 ✅

`test_midline_derived_only_here_and_nothing_written_back`（全部机械断言）：

- **(a)** 生产者类型（`AsDrawnPlanV2` 全部嵌套模型）字段名遍历：无任何 `*centerline*` / `*midline*` 字段；
- **(b)** bundle artifact 序列化后全键遍历：同上（模块 2 的「claim 零几何值」在编译入口再核一遍）；
- **(c) 正控**：编译后 `resolved_centerline` 有真实值（防止 (a)(b) 空转绿）；
- **(d) 零回写**：编译前后 bundle 序列化字节相同、`raw_bytes` 相同、**磁盘产物文件字节相同**；
  且编译产出的中线常量值不出现在 bundle 的任何浮点值里；
- **(e) 零文件 I/O**：模块源码 `grep` 无 `open(` / `read_bytes` / `Path(` / `write_bytes`（ref 全在冻结 bytes 内解析）。

### 7 · 零接线自证 ✅

```
$ git diff --stat 6637f38 -- src/agent/reading/vector_contract.py src/agent/pipeline.py
（空 —— 整文件零 diff）
$ git diff --stat 6637f38 -- src/agent/judge/
（空 —— 本档落笔时点整目录零 diff；GPT 席位 F-154 未落盘）
```

行为半 = `test_compiler_adds_no_pipeline_or_judge_edge_beyond_module_2`（差集 + AST 白名单，见 §一 红 1）。

### 8 · 跑测 + 改动路径 ✅

```
$ python -m pytest tests/test_o22m4_wall_compiler.py tests/test_o22m3_evidence_adapters.py -q -n 4
43 passed in 12.31s        （22 模块4 + 21 模块3）
$ python -m pytest tests/test_o22m1_as_drawn_producer_types.py tests/test_o22m2_evidence_contract.py \
    tests/test_o22m3_evidence_adapters.py tests/test_o22m4_wall_compiler.py -q -n 4
129 passed in 12.40s       （周边既有锁在模块 2 在途返工状态下全绿）
```

改动路径全清单（⛔ 未提交）：

| 路径 | 性质 |
|---|---|
| `src/agent/correction/wall_compiler.py` | **本单新建**（未跟踪） |
| `tests/test_o22m4_wall_compiler.py` | **本单新建**（未跟踪） |
| `tests/test_o22m3_evidence_adapters.py` | 本单改：翻 pin + 头部 docstring 同步（相对基线 60 行） |
| `src/agent/correction/evidence_contract.py`（+128）/ `tests/test_o22m2_evidence_contract.py`（+240） | ⚠️ **非本单**——是我此前交的模块 2 第二轮返工在途件，本单只依赖未再改 |

F-152（复核方同款判据 `grep -nE '"src/|'"'"'src/'`）：三个本单文件 **零命中**。

---

## 三、实现形态摘要（复核方用）

`compile_wall_ir(artifact, *, profile="strict", decisions=()) -> WallCompilationV1`，纯函数、确定性
（同一冻结 bytes + 同一决定 → `content_sha256` 相同 + 序列化字节相同，有测试）。八条 mandate 的落点写在模块
docstring（ref 只在冻结 bytes 内解析 · 余段双向保真 · 中线仅本层 · 三名字 · identity 在**类型层**不存在——
`SymbolicOperation` 枚举里没有它，候选想携带都构造不出来 · ambiguous 双 profile · 候选图全量走查（含
unselected 悬挂 face 的 NF-4 #5 模块 4 半，用手搭 bundle 测的——adapter 会拒的形状绕过 adapter 直达本层）·
solid band 不造搭档面）。

**决定应用**：`FixedDecisionV1(item_id, candidate_id)` 是唯一能关掉 open item 的东西（§9.1 第 4 步「固定决定夹具」的
最小形态；packet/response schema 归模块 5）。未知 item / 未知候选 / 重复决定一律响亮。OFFSET 候选的预览与执行
共用同一锚点（`_Ctx.anchor` 在编译时登记，执行时复用）——预览与落地不可能分叉。

**有意不做**（docstring 有声明）：openings 的 host 协议、`boundary_role`（恒 `None`，拓扑阶段的事）、
cost vector / packet / response（模块 5）、执行器回环与 ambiguous 之外的 profile 门（模块 6）、签名 sidecar（模块 3
已登记接线日事项）。

---

## 四、我自己认为最薄弱的一处

**未决比例与 degraded 状态在 compilation 层之上今天没有任何消费者。** `undecided=78/98`、`completion="degraded"`、
strict 的阻断——这些牙齿都长在 `compile_wall_ir` 的出口上，而 pipeline 不接线（本单禁令如此）、模块 5/6 未建、
模块 7 的 disposition 未翻。也就是说：**「strict 必须阻断」这条验收今天只能由我的测试来行使，还没有任何生产路径
会被它拦住**。这与模块 3 裁决 F-2 指出的病族（`walls=present` 的二值读数掩盖 80% 未决）只隔一层——我把比例和
degraded 造出来了，但「接线日会不会有人真的以 strict 调它、attempt/report 会不会把 degraded 面上的裸 geometry
拿去判卷」，锁在 §5.4 projection envelope / 模块 5/6 身上，本单锁不到。若那一层漏接，本单的消费机制等于没接。

次弱一条（如实报）：**ambiguous 的 strict 阻断是「存在即阻断」的一刀切**——设计稿 §7.2 写的是「可能改拓扑 ⇒ 阻断」，
我做的解释是：undecided 的 wall-ness 本身就可能改拓扑（哪怕该面在候选图里零参与，它仍可能是 single face 墙），
所以不按参与数分层放行。参与数算出来了、报在分析里，但**不参与阻断判定**。这是我对设计稿的保守化解释，
不是设计稿原文，请复核方裁。

## 五、希望复核方重点打哪里

（施工中我已按「回归用例必须自证前提」先自己打掉两条，留档如下；余两条仍请复核方打。）

1. **打「一刀切断法」**（§四次弱条）：拿一条**零候选参与**的 ambiguous 面（合成夹具即可），看 strict 是否也阻断；
   若你认为它不该阻断，这是口径分歧，请在裁决里给出分层判据——参与数已经在 `ambiguous_analysis` 里，改判定不改机制。
2. ~~打预览/执行漂移缝~~ → **已自己打掉并补锁**：SNAP/KEEP 的 `preview_delta_m`（候选构造处算）与执行后的
   `delta_m`（决定应用处另算）确实是两处独立计算——施工中实测变异（preview 偏 +1 mm）当时**全绿放行**，
   坐实了缝。已在 `test_thickness_decision_produces_the_resolution_record` 补**对账锁**
   （执行 delta/thickness 必须等于所选候选的 preview，两处独立来源互为对账），重放同一变异 → **1 failed**，
   恢复 → 22 passed。OFFSET 无此缝（预览与执行共用 `_Ctx.anchor` 同一锚点）。
3. **打「回指完整性」的反向**：把一条 fragment 的 `source_claim_id` 换成另一面墙的 claim id，看测试会不会红
   （fragment 与 claim 的绑定只锁了「等于本墙 claim」，没锁「不能指向别的墙」——后者由 wall_id 哈希唯一性隐含保证，
   但没有专门的变异锁；fragment 由代码生成、id 是算出来的，这条变异只能在编译输出上做，故留给复核方）。
4. ~~验证差集判据不是恒等式~~ → **已自验**：把 probe 目标换成模块 3 的 `evidence_adapters`，其 pipeline∪judge
   可达集与模块 2 **仍相等**——判据量的是「correction 子模块共同基座之上的零新增」（有失败方向：本模块若
   import 了任何直接拉进 pipeline 的东西，`mine - baseline` 非空即红），不是「模块各不相同」的恒真式。
   仍请复核方打 AST 白名单的方向：往 `wall_compiler.py` 塞一条白名单外 import，AST 锁应红。
