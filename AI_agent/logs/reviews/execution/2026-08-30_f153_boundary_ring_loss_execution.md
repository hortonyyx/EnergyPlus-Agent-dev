# F-153 boundary ring loss 施工执行档（强制停报）

- 日期：2026-08-30
- 席位：GPT 家族施工
- 基线：`8abd6e0`
- 档位：工程档（改 `src/agent/judge/as_measured.py` 的事实层交接契约）
- 状态：⛔ **未交付；触发派工单 §五「某把既有锁因本单变红」后停止**

## 开工审计

已完整读取 `AI_agent/CLAUDE.md` §0 与 §5#7.5。采用的分档口径：探索档是默认的 n=1 诊断，只记录、不阻断，免审免锁，且探索产物不得记成绩；本单改事实层管线内核/交接契约，属于工程档，应走 gate、受影响测试，并只锁契约与几何不变量。并发口径：一个模型家族只能飞一个任务；本轮 GPT 家族只飞本单，跨家族只读审阅可并行；pytest 固定 `-n 6`。

开工时 `git status --short` 为：

```text
?? AI_agent/logs/experiments/2026-08-30_f153_orchestrator_repro/
?? AI_agent/logs/reviews/request/2026-08-30_f153_boundary_ring_loss_dispatch.md
?? AI_agent/logs/reviews/request/2026-08-30_o22m1_crossreview_glm.md
```

三者均为开工前已有、非本席位改动；未清理、未改写、未暂存。

## 承重前提复测

命令：

```bash
for probe in probe_1_which_cavities_are_dropped.py probe_2_root_cause.py probe_3_detail.py probe_4_single_sample_fragility.py; do
  python "AI_agent/logs/experiments/2026-08-30_f153_orchestrator_repro/$probe"
done
```

四个 probe 均 exit 0。独立读数：

- `plan-F1 cavity:8bd127719198fd63`：88.27 m²，`classify_illogical`，span `x/160000/46400/53600/-1`，贴墙 400/400。
- `plan-F1 cavity:04e1293098b1a95a`：28.68 m²，`owner_count_0`，span `y/52401/99430/100630/-1`，贴墙 400/400。
- `plan-F2 cavity:495501ce9b36f0f3`：70.34 m²，`classify_illogical`，同一条 `x/160000/46400/53600/-1` span，贴墙 400/400。
- 形态 A：721 个 1 mm 位置里 121 个（16.8%）落在墙并集，中毒区 `[49400,50600]`，旧 `mid_along=50000` 正中。
- 形态 B：cavity 环上是精确 `52401.0`；另用只读查询补测到目标墙 `w_x_99430_100630_52401_88800` 的两条面线 `13AE/13AD` 分别从 `52399/52401` 起，配对交集生成 `along_min=52401`；三堵同侧兄弟均为 `52400`，全 view 的 wall/opening 面常量中没有 `52401`。

## 已形成但未交付的 WIP

仅改了 `src/agent/judge/as_measured.py`：

- 增加 cavity 级 `boundary_ring_losses` 具名 readout 草案，记录整数面积、失败 span、原因枚举和 owner 数。
- 形态 A 草案按 footprint / wall-region / cavities 的几何交点切 span，不引入采样步长或距离阈值。
- 形态 B 走派工单未列出的第四路草案：不改上游 face pairing、不把精确 owner 改成容差 owner；只用“ring 段精确落在垂直墙 `along_min/along_max` 端面”的拓扑关系识别 junction cap，把失效半径收窄到该段。该规则对换一份产物仍成立，因为依据是存储几何的精确拓扑，不依赖 sm25 坐标或 `≤N` 容差。

纯函数 smoke 命令：

```bash
python -m py_compile src/agent/judge/as_measured.py
python - <<'PY'
# 读取 sm25 as_measured.json，每个 view 调 derive_boundary_edges / derive_boundary_ring_losses
PY
```

读数：`py_compile` exit 0；`plan-F1 edges=88 / cavities=13 / losses=0`，两个目标 cavity 分别 37、7 edges；`plan-F2 edges=94 / cavities=15 / losses=0`，目标 cavity 36 edges。该 WIP 尚未通过既有契约门，不能视为交付。

## §四验收表逐项回答

### 1. 三个 cavity 有 edges 或具名 readout

命令：上节纯函数 smoke。

读数：三个 cavity 均有 edges（37 / 7 / 36），最终 loss 0。**仅为 WIP 读数；因验收 6 的既有锁变红，不计通过。**

### 2. 只留任务 1 时三个 cavity 进入 readout

计划命令：临时摘除任务 2/3 的代码 hunk 后，对 sm25 两个 view 调 `derive_boundary_ring_losses(..., min_room_area_m2=5.0)`，随后原样恢复代码。

读数：**未执行**；在执行临时摘除前已触发 §五强制停报。不能声称通过。

### 3. 形态 A 不再由单点采样承重

基线命令：

```bash
python AI_agent/logs/experiments/2026-08-30_f153_orchestrator_repro/probe_4_single_sample_fragility.py
```

基线读数：F1/F2 均为 121/721（16.8%），中毒区 `[49400,50600]`，旧 midpoint 正中。WIP 已改为按几何交点切分，但**尚未执行验收用的反事实/变异命令**，因为先触发强制停报。不能声称通过。

### 4. 形态 B ±1 与 ±1000 合成夹具

计划命令：

```bash
pytest -n 6 tests/test_f153_boundary_ring_loss.py -q
```

读数：**测试文件尚未创建，命令未执行**；既有锁先红，按禁令停止。不能声称通过。

### 5. sm21 / sm24 同形探针

计划命令：对 sm21 / sm24 的事实产物逐 view 调同一 cavity/readout 探针，打印每个过阈值但无 edges 的 cavity 面积与原因。

读数：**未执行**；既有锁先红，按禁令停止。不能声称通过。

### 6. 自有文件与受影响子集 `-n 6`

实际命令：

```bash
pytest -n 6 tests/test_boundary_condition_facts.py -q
```

实际读数：exit 1，`11 failed / 2 passed`。11 个失败均在进入原测试断言前被同一复现门挡住：新增默认空字段进入 `canonical_bytes()` 后，已落库 as-measured 的内容哈希从 ledger 声明的 `839d67a224851b64309faa17368648b0666d08d4f9505e6514c6d65b818abea8` 变成 `ec286cf1d7a5d6b54a4311f8aca8c5a5bf0c8f409f45d1363783e4066adc3e27`，抛出 `AsSignedReproductionError: as_signed_revisions_do_not_target_this_as_measured`。

这是派工单 §五明确列出的强制停报触发器。未改任何既有测试断言，未继续跑其它 pytest。

### 7. 改过的文件

命令：

```bash
git status --short
```

收尾实际读数：

```text
 M AI_agent/guides/reading_correction_split_guide.md
 M AI_agent/plan.md
 M src/agent/judge/as_measured.py
?? AI_agent/logs/experiments/2026-08-30_f153_orchestrator_repro/
?? AI_agent/logs/experiments/2026-08-30_wiring_gap_survey/
?? AI_agent/logs/reviews/execution/2026-08-30_f153_boundary_ring_loss_execution.md
?? AI_agent/logs/reviews/request/2026-08-30_f153_boundary_ring_loss_dispatch.md
?? AI_agent/logs/reviews/request/2026-08-30_o22m1_crossreview_glm.md
?? AI_agent/logs/reviews/request/2026-08-30_o22m2_evidence_contract_dispatch.md
```

其中 `reading_correction_split_guide.md`、`plan.md`、`wiring_gap_survey/`、`o22m2_evidence_contract_dispatch.md` 均在本席位工作期间由其它席位出现；本席位未触碰。开工前已有的三组输入也仍未触碰。

本席位改动路径：

- `src/agent/judge/as_measured.py`（WIP，未交付）
- `AI_agent/logs/reviews/execution/2026-08-30_f153_boundary_ring_loss_execution.md`（本执行档）

未执行 `git add`、`git commit`、`pip install -e .`，未写 site-packages，未使用 `-n auto`，未跑全量。

## 强制停报与请求裁决

阻塞不是外围数值差异，而是事实层内容寻址契约的既有锁转红。任务 1 要增加事实 readout，但现有落库 facts + revisions ledger 的哈希会因 schema 默认字段参与 canonical dump 而失配；用户又限定本席位唯一可写的非代码文件为本执行档，因此本席位不能自行重签/改写落库事实或 ledger。

请主控裁决 readout 的向后兼容承载方式或是否另派一单处理已签 facts 的迁移；在裁决前，本 WIP 不应提交。

## 我认为最薄弱的一处 / 希望复核方重点打

最薄弱处是“精确 end-cap 拓扑 ⇒ 可局部丢弃 junction fragment”这一第四路：它没有容差、也确实把失效半径从整圈收窄到一段，但尚未经过 ±1/±1000 合成夹具，也尚未证明新产出的非闭合子段序列能被 `refresh_boundary_edges` 与 answer compiler 的 ring 配对完整消费。复核方若继续审，应优先攻击这两点，而不是只看三个 sm25 cavity 已有 edges。

---

# 续单（按派工单 §七～§十二补充裁决继续）

## 续单开工复核：§九三条实测

先直接读取受保护原始产物，未采用补记 README 的汇总数字。命令形状：

```bash
python - <<'PY'
# json 直读 revisions.json / as_measured.json；ezdxf 直读两份 DXF 的
# 13AD/13AE LINE 实体；只打印，不写文件。
PY
```

复核结果全部成立，因此未再次停报：

- `revisions.json`：5 条 revision 全部 `unsigned`、`signed_by` 非空数为 0；`rev-13ad` 的 `detail` 为 `const=-31, along_min=-1`，`rev-13ae` 为 `const=-31, along_min=+1`，两条 `candidate_action` 都是 `null`。
- `sm25-L_t3_as_received.dxf`：`13AD/13AE` 起点 x 差 `0.19148911790034617 mm`，minor leg 分别为 `5.808357854417409 / 5.808663422183599 mm`。
- `sm25-L_t3.dxf`：两条起点 x 同为 `-25229.022`，差 `0.0 mm`，minor leg 都为 `0.0 mm`。
- `axis_snapped_lines`：`plan-F1` 恰好 2 条，正是 `13AD/13AE`；angle 为 `0.09142935778784271 / 0.0914293577882342°`、minor leg 都为 58 单位；after 的 along 端点仍为 `52401 / 52399`。`plan-F2` 为 0 条。

## 按 §八 / §九完成的实现收敛

- 已从 `AsMeasuredViewV1` 完全撤掉 `boundary_ring_losses` 字段及 view 级校验；`build_view` 也不再落库 loss。`AsMeasuredBoundaryRingLossV1` / `AsMeasuredBoundaryFailureSpanV1` 只保留为返回类型。
- `derive_boundary_ring_losses(view, *, min_room_area_m2)` 是与 `derive_boundary_edges` 并列的纯派生函数；二者共用一次内部推导形状，但 loss 不参加 `canonical_bytes()`。
- 形态 B 不再走上一轮 WIP 的“精确 end-cap 局部放行”，没有修 owner，也没有做容差匹配。它保持 `owner_count=0` loss，并新增纯证据字段：`nearest_same_axis_wall_face_const` 与 `span_to_nearest_same_axis_wall_face_delta`。
- 最近同轴墙面只从沿 span 有严格正长度覆盖的同轴墙组中选距离最小者；此值只写 readout，不进入 `_boundary_owners`，所以 1 单位与 1000 单位都仍是不同几何。
- 形态 A：当旧的整段 witness 判 illogical 时，按 footprint / wall-region / cavities 的真实几何交点切分并逐子段复判；原本已 logical 的 span 保持既有 edge 身份与粒度，避免无关 cavity 的 edge 4→6 漂移。

## §十修订验收表逐项实测

### 1. 三个 cavity 均有 edges 或 loss

命令：读取落库 sm25 `as_measured.json`，每个 view 分别调用 `derive_boundary_edges(..., 5.0)` 与 `derive_boundary_ring_losses(..., 5.0)`，按 cavity id 对账。

读数：

```text
plan-F1 cavity:04e1293098b1a95a loss 28.683212 m² reason=owner_count owner_count=0
plan-F1 cavity:8bd127719198fd63 loss 88.2656 m² reason=owner_count owner_count=0
plan-F2 cavity:495501ce9b36f0f3 loss 70.3392 m² reason=owner_count owner_count=0
all_three_named True
```

形态 A 的旧 `classify_illogical` span 已被切分，不再判死整圈；两个 A cavity 后续各遇到另一条精确 owner=0 span，所以最终如实进入 loss，而不是静默消失。

### 2. 纯派生，落库内容哈希前后逐字节不变

命令形状：

```bash
PYTHONPATH=src python - <<'PY'
# raw JSON 自行 canonicalize；再经 AsMeasuredV1.validate + canonical_bytes；
# 与 revisions.json 的 as_measured_content_sha256 三方比较。
PY
```

两次读数与字节对账：

```text
before_ledger_content_sha256 839d67a224851b64309faa17368648b0666d08d4f9505e6514c6d65b818abea8
after_current_content_sha256 839d67a224851b64309faa17368648b0666d08d4f9505e6514c6d65b818abea8
raw_canonical_sha256         839d67a224851b64309faa17368648b0666d08d4f9505e6514c6d65b818abea8
canonical_bytes_equal True
canonical_byte_length_before_after 210224 210224
plan-F1 / plan-F2 has_boundary_ring_losses_field False
```

### 3. 形态 A 不再由 `mid_along` 单点承重

命令：给 `_classify_boundary_fact` / `_boundary_transition_points` 加只读 wrapper 后调用生产 `derive_boundary_edges`；随后重跑 `probe_4_single_sample_fragility.py`。

F1 与 F2 逐位相同：

```text
CLASSIFY 46400 53600 mid 50000 condition unknown logical False
CUTS 46400 53600 [46400, 49400, 50600, 53600]
CLASSIFY 46400 49400 mid 47900 condition interzone logical True
CLASSIFY 49400 50600 mid 50000 condition unknown logical False
CLASSIFY 50600 53600 mid 52100 condition interzone logical True
```

反事实旧读数仍为每层 `121/721 (16.8%)` 中毒、旧 midpoint 正中 `[49400,50600]`。新实现不是换一个单点：它保留两个真实 logical 子段，只排除确实抵住垂直墙的中段。

### 4. 形态 B 报出并携带上游线索

同验收 1 的纯函数命令，目标项完整读数：

```text
cavity:04e1293098b1a95a
area=28.683212 m²
reason=owner_count owner_count=0
span=(axis=y, const=52401, lo=99430, hi=100630, side=-1)
nearest_same_axis_wall_face_const=52400
span_to_nearest_same_axis_wall_face_delta=1
```

`_boundary_owners` 仍要求整数精确相等；nearest/delta 只由失败后证据查询产生，不参与匹配。

### 5. sm21 / sm24 同形探针

sm24 命令：`build_as_measured(source.dxf, request.json)` 后按 request 声明的 `min_room_area_m2=2.0` 调同一套 edges/losses 纯函数。

```text
plan-F1 stored_edges=24 derived_edges=24
cavity:c52b0caa54bfb8e4 23.1672 m² owner_count=0
cavity:78c72977c3b7e2c2 30.8464 m² owner_count=0
```

sm21 的 GT source 目录只有 `source.dxf`，没有本事实层必需的签字 `request.json`。为排除“只是漏找文件”，另做了只读内存探针：从已核 GT 的两层位置构造非权威 probe intent，源 DXF 先复制到 `TemporaryDirectory`，不写 GT 树；两层都被 `tarch_view_frame_missing` + `tarch_view_frame_ambiguous` 的 S0 identity gate 阻断，F2 另有 topology BLOCK。`build_view` 正确抛 `AsMeasuredUnavailable[upstream_identity_block]`。因此 sm21 在当前契约下没有可诚实生成的 facts/cavity 读数；本项报告结构性 N/A，不把合成 request 的输出冒充事实。

### 6. 既有锁与受影响子集

首次撤字段后运行指定命令，哈希红已全部消失，但发现形态 A 对所有 span 无条件切分会让一个既有 F2 cavity 从 4 edges 变 6，读数为 `69 passed / 2 failed`。未改断言；把切分收窄到“旧整段判 illogical 时才展开”后重跑：

```bash
pytest -n 6 tests/test_boundary_condition_facts.py tests/test_as_measured_facts_layer.py -q
```

```text
71 passed in 17.49s
exit 0
```

另跑受影响的 staging 重现锁：

```bash
pytest -n 6 tests/test_gt_facts_staging_sm25.py -q
```

```text
8 passed in 7.01s
exit 0
```

`python -m py_compile src/agent/judge/as_measured.py` exit 0。环境没有已安装的 `ruff` 模块/命令，未为此安装包。

### 7. 本席位改过的文件（未提交）

- `src/agent/judge/as_measured.py`
- `AI_agent/logs/reviews/execution/2026-08-30_f153_boundary_ring_loss_execution.md`（只在旧内容末尾追加本续单，未重写前文）

未改 `case_tests/test_baseline/gt_staging/`、`case_tests/test_baseline/gt_sources/` 或仓库根 `gt_sources/` 下任何文件；未改既有测试断言。未执行 `git add`、`git commit`、`pip install -e .`、`-n auto` 或全量测试。

## 续单后最薄弱处 / 希望复核方重点打

最薄弱处已从上一轮的 end-cap 第四路换成：**为保持既有 edge 身份，几何交点切分只在旧整段 witness 先判 illogical 时启动**。这足以移除 F-153 形态 A 的“一个 midpoint 判死整个 cavity”承重，但对“midpoint 本来 logical、同一 span 内其实跨过不同 boundary condition”的情形仍保留旧粒度；它不会再造成 cavity 静默丢失，却可能继续压平细粒度分类。请复核方优先造这种反例，检查这是本单恰当的最小修复还是应另单扩大切分语义。

第二个需复核的点是 sm21 的结构性 N/A：本席位没有为过验收而伪造/落库 request。若主控掌握一份权威 sm21 conversion request，应拿那份重跑同一纯函数；当前仓内找不到这样的输入。

---

# 第三轮（按 2026-08-31 甲案与 §六～§九补充裁决续做）

## 本轮实现

- `AsMeasuredViewV1.boundary_ring_losses` 已恢复为存储字段，与
  `boundary_edges` 由同一次 `_derive_boundary_facts` 生成并进入
  `canonical_bytes()`。
- view 级门要求 loss 的 `cavity_id` 唯一，并禁止同一个 cavity 同时出现在
  `boundary_edges` 与 `boundary_ring_losses`。
- `AsMeasuredBoundaryRingLossV1` 的 docstring 已明确：该值虽然是纯派生，仍存盘的
  窄理由是“底稿必须自己承认自己的缺口”；这不构成“凡派生值都该存”的规则。
- 形态 A 的几何交点切分、形态 B 的只报不修以及两个上游线索字段均保持上一轮实现，
  `_boundary_owners` 未加入容差匹配。

## §三验收表逐项回答

### 1. sm25 三个 cavity 落库；sm24 按新裁决记执行档

sm25 由 `sm25-L_t3_as_received.dxf + request_as_measured.json` 重建后，落库
`as_measured.json` 的三个 loss 为：

```text
plan-F1 cavity:8bd127719198fd63
  area=88.2656 m² reason=owner_count owner_count=0
  span=(axis=y, const=98800, lo=160000, hi=161200, side=1)
  nearest_same_axis_wall_face_const=110000
  span_to_nearest_same_axis_wall_face_delta=-11200

plan-F1 cavity:04e1293098b1a95a
  area=28.683212 m² reason=owner_count owner_count=0
  span=(axis=y, const=52401, lo=99430, hi=100630, side=-1)
  nearest_same_axis_wall_face_const=52400
  span_to_nearest_same_axis_wall_face_delta=1

plan-F2 cavity:495501ce9b36f0f3
  area=70.3392 m² reason=owner_count owner_count=0
  span=(axis=x, const=60000, lo=110000, hi=111200, side=1)
  nearest_same_axis_wall_face_const=40000
  span_to_nearest_same_axis_wall_face_delta=20000
```

另以 `build_as_measured(sm24_anchor/source.dxf, sm24_anchor/request.json)` 只在内存
复测（未调用 writer、未创建 staging）得到：

```text
plan-F1 cavity:c52b0caa54bfb8e4  23.1672 m²  reason=owner_count owner_count=0
plan-F1 cavity:78c72977c3b7e2c2  30.8464 m²  reason=owner_count owner_count=0
```

sm24 本单为**结构性 N/A**，原因是**该 case 尚无事实层基线**；遵照 §七，本轮不首次
创建。以上两项**待 sm24 事实层建立后自动落库**。

### 2. 新旧哈希与三件套自洽

```text
旧 as_measured content_sha256:
839d67a224851b64309faa17368648b0666d08d4f9505e6514c6d65b818abea8

新 as_measured content_sha256:
0d3aefa229d277b3197b5cf007747df5885641d58c8a1b6e6cdc376236f2548c

revisions.json.as_measured_content_sha256:
0d3aefa229d277b3197b5cf007747df5885641d58c8a1b6e6cdc376236f2548c

as_signed.json.derivation.as_measured_content_sha256:
0d3aefa229d277b3197b5cf007747df5885641d58c8a1b6e6cdc376236f2548c

新 revisions content_sha256:
4db9e12690d761581e0c9787515a944fc7606aace969796c3ae24305d9bbbda5

as_signed.json.derivation.revisions_content_sha256:
4db9e12690d761581e0c9787515a944fc7606aace969796c3ae24305d9bbbda5
```

`read_facts_candidate("sm25-L_anchor")` 与
`verify_as_signed_reproduction(...)` 均通过。

### 3. 从 DXF + request 机械重生成，两次逐字节相同

实际生成链（两次独立执行同一 `generate()`，比较 canonical bytes 后才写真实 staging）：

```text
build_as_measured(sm25-L_t3_as_received.dxf, request_as_measured.json)
build_as_measured(sm25-L_t3.dxf,             request.json)
detect_translate_candidates(before, after, [13AD,13AC,13AF,160A,13AE])
RevisionsLedgerV1(as_measured_content_sha256=content_sha256(before), ...)
derive_as_signed(before, ledger)
write_facts_candidate("sm25-L_anchor", before, ledger, as_signed)
```

读数：

```text
two_runs_byte_identical True
revision_rows_byte_identical True
canonical sizes: as_measured=211180 revisions=2238 as_signed=211405
```

未直接编辑任何 staging JSON。

### 4. 5 条 revision 正文/verdict 未变

将当前 JSON 与 `git show HEAD:<path>` 解析后递归比较，差异路径严格为：

```text
as_measured.json:
  views[0].boundary_ring_losses
  views[1].boundary_ring_losses

revisions.json:
  as_measured_content_sha256

as_signed.json:
  derivation.as_measured_content_sha256
  derivation.revisions_content_sha256
  views[0].boundary_ring_losses
  views[1].boundary_ring_losses
```

重新检测出的 5 条 revision rows 与旧 rows canonical bytes 相同；verdict 读数为
`unsigned × 5`，`signed_by/signed_at` 仍全空，未签任何 revision。

### 5. 指定四文件测试

实际命令：

```bash
pytest -n 6 tests/test_boundary_condition_facts.py tests/test_as_measured_facts_layer.py tests/test_gt_facts_staging_sm25.py tests/test_denominator_from_facts.py -q
```

读数：

```text
84 passed in 19.04s
exit 0
```

既有行为断言改动：**无**。钉旧哈希的测试常量改动：**无（0 行）**；这四个测试文件
均未修改。

### 6. 形态 A / B 与上一轮行为一致

形态 A 当前实测（F1/F2 的目标 span 均切在相同的真实几何交点）：

```text
旧整段 46400..53600, mid=50000 -> unknown / logical=False
cuts -> [46400, 49400, 50600, 53600]
46400..49400, mid=47900 -> logical=True
49400..50600, mid=50000 -> unknown / logical=False
50600..53600, mid=52100 -> logical=True
```

反事实探针仍为每层 `121/721 (16.8%)` 采样点落在中毒区
`[49400,50600]`，旧 midpoint 正中；当前行为与上一轮一样，只排除中间真实失效段，
不让该单点判死整圈。

形态 B 当前仍为：

```text
cavity:04e1293098b1a95a
reason=owner_count owner_count=0
span const=52401
nearest same-axis wall face const=52400
delta=1
```

读数与上一轮一致；该 `delta=1` 只存为上游线索，未改变精确 owner 匹配，也未修几何。
此外逐 view 比较确认 stored edges/losses 与即时重新 derive 的结果逐项相等：
`plan-F1 44 edges / 2 losses`，`plan-F2 56 edges / 1 loss`。

### 7. 本轮改动路径（未提交）

- `src/agent/judge/as_measured.py`
- `case_tests/test_baseline/gt_staging/sm25-L_anchor/facts/as_measured.json`
- `case_tests/test_baseline/gt_staging/sm25-L_anchor/facts/revisions.json`
- `case_tests/test_baseline/gt_staging/sm25-L_anchor/facts/as_signed.json`
- `AI_agent/logs/reviews/execution/2026-08-30_f153_boundary_ring_loss_execution.md`

未改 `gt_sources/`、`src/agent/judge/answer_compiler.py`、任何既有测试断言、
`src/agent/correction/` 或 `tests/test_o22m3*`。`git status` 中其余 `AI_agent/` 文件及
O22m3 文件为他人改动，本席位未触碰。

未执行 `git add`、`git commit`、`pip install -e .`、`-n auto` 或全量测试。
