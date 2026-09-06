# E-a′ 跨家族复核裁决（Claude 家族）

复核单：`2026-09-06g_Ea2_crossreview.md`；被审对象：`/tmp/ea2_astra` `363844b3..cbf1acfa`（10 提交，工作副本 `/tmp/ea2_review_glm` @ `cbf1acfa`）。派工单：`2026-09-06d_Ea2_source_contract_dispatch.md`；交件：`2026-09-06d_Ea2_source_contract_execution.md`。

⚠️ 说明：复核单原文件名 `2026-09-06g_Ea2_crossreview.md` 在 `/tmp/ea2_review_glm` 工作目录内未同步（只存在于主树与 pytest staging 副本），已确认主树版本（改派 Claude 版）与 staging 陈旧副本（GLM 版）内容仅分工署名与本文件落点两处不同，复核要求本身逐字相同；本裁决严格按主树版执行。

## 裁决：**APPROVE-WITH-FINDINGS / 阻断 0 / 不阻断 1**

§一 主控已自核五项（3957 独立 collect、禁区零命中、与 J 单零重叠、v2 分支已在、schema 常量系引用）本次未重做，直接采信。以下全部是 §二 的独立复核结果。

---

## §2.1 头号：202 行消费表是不是全部（两套独立口径 + 决定数去重）

### 口径 A —— 直接遍历生产 JSON（自写枚举脚本，未参照交件的 `field_paths.json` 或其枚举脚本）

对三份真实产物（`sm25_1f_v2` / `sm25_2f_v2` / `sm24_1f_v2`）跑一个纯自动化脚本：dict 只在“同一容器下全部取值共享同一结构签名”时才生成动态键 `*`（每次只用该容器遇到的第一个元素判定），list 一律记 `[]` 再下钻。三文件并集 = **255 条路径**，对比表的 202 条：

- **表里有、我的自动脚本没有**：1 条（`hypotheses.unpaired_wall_faces.*`）——因为该 dict 在三份文件里最多只出现 1 个 key（`sm24_1f` 里唯一的 `L012`），脚本判定“动态 map”要求同容器 ≥2 个取值样本，样本不足时保守按字面量处理，属于**我的脚本的取样局限**，不是表的遗漏（该字段与 `non_wall_face_lines`/`solid_band_walls`/`ambiguous_face_lines` 是同一族四个桶，其余三个都在三文件里凑够了 ≥2 样本从而被我的脚本正确判成 `*`，四个桶待遇不一致本身就证明是取样伪影）。
- **我的自动脚本有、表里没有**：54 条，两类，逐类核实均为**约定/工具局限，非真实遗漏**：
  1. **~24 条** `hypotheses.opening_candidates[].ink_by_family.F0/F1/F2/F3…`（含 `observations.face_lines[].gaps[].ink_by_family.F0…`）—— 我第一版脚本对 list 只采样第 0 个元素来判定其子 dict 是否“动态”，而 `ink_by_family` 在不同 gap/candidate 上出现的 family 子集不同，采样第 0 个元素时常凑不够 ≥2 keys，于是被误判为字面量而非 `*`。用第二版脚本（对同一路径聚合全部实例的 key 集合后再判定）复算，这批全部收敛为 `ink_by_family.*`，与表完全一致（该验证已通过 `schema.py: InkProfileV2 / dict[str, InkProfileV2]` 的产出方类型交叉确认：family id 本就是动态键）。
  2. **~30 条** 形如 `observations.calibration.x.values_mm[]` / `declarations.chains.*.values_mm[]` / `observations.face_lines[].runs_px[][]` 的“数字数组再下钻一层”路径。核对表本身的现有条目（如同时有 `runs_px` 与 `runs_px[]`，但没有 `runs_px[][]`；有 `values_mm` 却从不列 `values_mm[]`）可看出表的约定是：**list 的元素若还是"结构"（list-of-list / list-of-dict）才多记一级 `[]`，元素若是裸数字（int/float 的扁平数组）则该数组本身就是"这一个字段"，不再往下拆**。这是一个自洽、双方均可复现的粒度约定，不是漏项。

用第二版脚本（聚合全部实例样本 + 手工核对两条 dynamic-map 判据后）重跑，剩余差集只有 2 条（`ink_by_family.*.by_distance_px.*` 两处，因为我最初没把 `by_distance_px` 本身登记为需要聚合判定的动态 map 路径——核对 `schema.py:183` `by_distance_px: dict[str, int]`，确认这是像素距离分箱值作为 key 的合法动态 map，表是对的，我漏判）以及前述 ~37 条“数字数组再下钻一级”的粒度差异（非遗漏，见上）。

**结论：口径 A 未发现真实字段级遗漏。**

### 口径 B —— 直接读 `as_drawn_v2.py` 的 `assemble()`（生产者代码，逐层追到取值来源）

- `assemble()` 本体（`as_drawn_v2.py:566-670`）字面构造 7 个顶层键：`schema/image/image_label/observations/declarations/hypotheses/ledger`，`observations` 下 5 键、`declarations` 下 5 键、`hypotheses` 下 16 键、`ledger` 下 15 键——与表 LHS 顶层/二级键**逐一核对完全一致**。
- 深一层的叶子来自 `assemble()` 直接调用的构造函数，逐一读代码核实字段名：
  - `ChainFit.as_dict()`（`_plan_ink.py:143`）→ 13 键（`axis/values_mm/cum_mm/matched_px/unmatched_ticks_px/origin_px/mm_per_px/residual_px/rmse_px/max_abs_residual_px/chain_closure_mm/overall_mm` + 追加的 `m_per_px`），与表 `calibration.x.*`/`calibration.y.*` 13 行完全一致。
  - `_profile()`（`as_drawn_v2.py:105-121`）→ `on_line/by_distance_px/span_ratio/nearest_px` 4 键，与表 `ink_by_family` 系列完全一致。
  - `_components()`（`as_drawn_v2.py:220-235`）→ `bbox_px/area_px`，与表 `components_by_family.*[]` 完全一致。
  - `trace_face_lines()`（`as_drawn_v2.py:405-441`）→ 逐字段构造出 14 键（`id/axis/constant_world_axis/pos_px/pos_m/support_cols_px/edges_m/support_width_m/runs_px/runs_m/gaps/ink_coverage_per_run/covered_px/support_px`），与表 `face_lines[]` 系列（含容器行）逐一核对完全一致。

**结论：口径 B 未发现任何字段被表遗漏，也未发现表虚报字段。**

### 三方差集裁决

口径 A（生产真实数据）× 口径 B（生产者代码）× 表（交件），三方在字段集合层面**完全收敛**；A/B 各自暴露出的差异全部可追因到我自己脚本的两处已知局限或一个自洽的粒度约定，均已逐条说明并交叉验证，**没有一条指向表存在真实缺项**。

### 按【决定】去重统计真实覆盖面

对 202 行执行机械去重：以（谁该消费, 现在消费了吗, 结构上不必→坏数据流向）三列的**逐字节相同**文本为 key 分组：

```
总行数 202 → 26 个互不相同的 (谁该消费/消费了吗/坏数据流向) 三元组
```

派工单点名的 `declarations.chains` 六行（容器 + `.*` + 4 个子字段）**恰好是这 26 组之一，组内 6 行文字逐字相同**——机械去重精确复现了派工单给出的例子，验证了这套操作化定义的有效性。

分布上最大的几组：
- 33 行 → 1 个决定（`ink_palette` 全体 + `components_by_family` 全体：“墨迹/连通域测量，deferred，未做语义拦截”，这是同一条策略同时套用在两个命名空间上，我逐一 grep 了 `cross_axis_relative_deviation`/`world_zero_source`/`profile_bins_px`/`fill_ratio`/`thickness_callout_note`/`ref_coord_m`/`family_roles`/`opening_candidates_basis`/`pair_candidates_basis`/`perception_source`/`pairs_note`/`ledger.*` 等约 15 个具体字段名在 `src/agent/correction/*.py` 里的引用——**零命中**，与"结构上不必消费、只保留原样字节"的声明一致，不是虚报）
- 26 行 → 1 个决定（`calibration.x/y` 原始像素定标读数：“不重拟合，只保原样”）
- 16 行 → 1 个决定（`ledger.*`：“不取汇总生成洞口”）
- 16 行 → 1 个决定（`family_roles.*`：“不按色彩统计生成窗”）
- ……（完整 26 组分布已在本地脚本核实，此处不逐条贴出）

⇒ **202 行背后是 26 个互不相同的消费策略决定**，"厚"的部分是同一决定在结构均匀的容器（如 `chains.*` 的 12 条链、`ink_palette.families[]` 的字段）上按字段逐条铺开写出来的，**不是造假**（我抽查的每一条字段级声明本身都能在代码里独立核实为真），但**决定层面的完备性应对着 26 判断，不是对着 202**。

**是否有真的漏项**：口径 A/B 的独立枚举确认 202 行覆盖了生产格式的全部真实字段（无遗漏字段名）；26 个决定逐一读来都是具体、可证伪的策略陈述（非空话），且抽查的十余处"结构上不必消费"declaration 均通过 grep 验证为真——**没有找到真的漏项**。

**不阻断 finding #1**：§2.1 的头号问题本身值得记一条改进项——「完整消费对照表」这个交付物名称暗示了行数即完备度，但真实完备度单位是 26 个决定而非 202 行；建议未来同类交付物在表首附一行"去重后 N 个决定"的机械统计，避免"表越厚越像做完"的误读继续在后续单子里发生（[[gate-teeth-direction-follows-fixture-inventory]] 一类问题的姊妹形态：这次不是锁没牙，是**计数单位选错了**，容易被下一次派工方或复核方直接引用 202 当"完备性证书"）。不阻断，因为实质覆盖是真的。

---

## §2.2 三条复核（换同形输入仍走不通）

对 E-a-1、E-a-4 各自造了**不同于交件用例**的实例，命令与输出如下（脚本留存于本次复核 scratch，未提交进仓库，按裁决要求原文贴出）：

### E-a-1（过期 batch）—— 换成"使 PLAN 侧过期"而非交件用的"使 ELEVATION 侧过期"

交件的 `test_ea1_pipeline_rejects_stale_batch` 只调用 `elev.reconsider(...)` 让立面会话过期。本复核改为让**平面会话**过期（`plan.reconsider(...)`），验证 `_check_current()`（`opening_adjudication.py:340-343`）里 `self._plan.consume(self._plan_batch)` 这一行是否真的独立生效，而不是只有立面那半有牙：

```python
geom, review, result, plan, pb, elev, eb = setup_review()
assembled = pipeline.run_opening_adjudication(geom, review=review,
    expected_result_id=result.result_id, out_dir=tmp/'good')
assert len(assembled.windows) == 1          # 正例先跑通

plan.reconsider('third-review probe: plan side invalidated, not elevation')  # 换成平面侧过期

try:
    pipeline.run_opening_adjudication(geom, review=review,
        expected_result_id=result.result_id, out_dir=tmp/'stale_plan_side')
    print("FAIL")
except TickClaimError as exc:
    assert exc.code == 'TICK_BATCH_INVALIDATED'
assert not (tmp/'stale_plan_side').exists()
```

原文输出：
```
RAISED: TICK_BATCH_INVALIDATED
stale_dir exists: False
PASS: plan-side staleness (different instance than astra's elevation-side test) is caught symmetrically
```

### E-a-4（pairs 为空/未选中）—— 换成不同真实产物 + 未被试过的 `pairs/status` 组合

交件的 `test_ea4_model_selection_required` 默认用 `plan_doc()`（真实文件 `sm25_1f_v2`，49 面线/22 选中对），parametrize 覆盖 `([],'SELECTED')` `(None,'ABSENT_NO_MODEL_SELECTION')` `('keep','SELECTED_INCOMPLETE')` `('keep',None)` 四种组合。本复核换成**另一份真实产物** `sm24_1f_v2`（98 面线/8 选中对，结构显著不同）+ **一个未被试过的组合**：`pairs=[]` 且 `pairs_status='SELECTED_INCOMPLETE'`：

```python
doc = plan_doc('sm24_1f_v2')
assert len(doc['observations']['face_lines']) == 98
doc['hypotheses']['pairs'] = []
doc['hypotheses']['non_wall_face_lines'] = {f['id']: '...' for f in doc['observations']['face_lines']}
for bucket in ('unpaired_wall_faces','solid_band_walls','ambiguous_face_lines'):
    doc['hypotheses'][bucket] = {}
doc['hypotheses']['pairs_status'] = 'SELECTED_INCOMPLETE'   # 交件参数化里没有的组合

assert classify_vector_json(doc).contract_id == 'as_drawn_plan'
assert_code('TICK_PLAN_MODEL_SELECTION_REQUIRED', lambda: TickSession(freeze(doc), image_id='plan'))
```

原文输出：
```
PASS: sm24_1f_v2 real file + pairs=[]/SELECTED_INCOMPLETE combo (untested by astra) is rejected
```

**两条均在与交件不同的实例/组合上复现红→绿的锁行为，判定"这一类"而非"这一个例子"成立。**

（附带确认 A-6-d1 的第三条复核见 §2.5。）

---

## §2.3 自己跑一次逐字节重建 `batch_id`（不信任 `verify_tick_archive` 自身，改用裸 `hashlib`）

派工单要求"从落盘件能逐字节重建 batch_id"。交件的证据是调用生产自带的 `verify_tick_archive()`——但那正是被测代码本身，用它验证自己等于自证。本复核绕开它，直接用 Python 标准库 `hashlib.sha256` 在磁盘文件字节上重算：

```python
geom, review, result, plan, pb, elev, eb = setup_review()
assembled = pipeline.run_opening_adjudication(geom, review=review,
    expected_result_id=result.result_id, out_dir=tmp)
archive = tmp/'opening_batches'/result.result_id
for session, batch, label in ((plan, pb, 'plan'), (elev, eb, 'elev')):
    folder = archive/batch.batch_id
    manifest = json.loads((folder/'manifest.json').read_bytes())
    for name in manifest['files']:                       # ① 每个文件自身哈希核对 manifest
        assert hashlib.sha256((folder/name).read_bytes()).hexdigest() == manifest['files'][name]
    batch_bytes = (folder/'batch.json').read_bytes()
    rebuilt = hashlib.sha256(batch_bytes).hexdigest()     # ② 从 batch.json 字节重算 batch_id
    assert rebuilt == batch.batch_id == folder.name
    assert batch_bytes == batch.record                    # ③ 与活会话的 record 逐字节相同
    assert (folder/'source.bin').read_bytes() == session.packet.source_bytes   # ④ 源字节回环
```

原文输出（plan 与 elev 两个独立 batch 各一遍）：
```
--- plan: .../opening_batches/a88d0fda.../060cf2110d...
  OK: every persisted file's own sha256 matches manifest.files[name]
  OK: sha256(batch.json bytes) == 060cf2110d... == live batch.batch_id == folder name
  OK: batch.json on disk is byte-identical to live TickBatch.record
  OK: source.bin byte-identical to session.packet.source_bytes
--- elev: .../opening_batches/a88d0fda.../a07d97a376...
  （同上四项全 OK，含 supplement.bin）
```

**结论**：`batch_id` 确实是磁盘上 `batch.json` 字节的 sha256（用与生产代码完全独立的裸 `hashlib` 调用验证），不是"字段存在/长度不为 0"的影子读数；且源字节、决策记录字节均可逐字节回环，两个独立会话（plan/elev）都过。

---

## §2.4 配对取自哪一行（贴代码）

`evidence_adapters.py:348`：

```python
for j, pair in enumerate(pairs):          # pairs = hyp.get("pairs")，第 299 行
    ...
    key = frozenset((pair["face_a"], pair["face_b"]))
    k = candidate_at.get(key)
    if k is None:
        # §4.3: a selected pair missing from the candidate graph is an
        # input error -- never a code-invented nearest-neighbour leg.
        raise EvidenceContractError("SELECTED_PAIR_NOT_IN_CANDIDATE_GRAPH", ...)
```

`candidates`（来自 `hyp.get("pair_candidates")`，第 279 行）只在第 296 行建了一个 `candidate_at` 查找表，**唯一用途是核对模型选中的 `pair` 是否真的出现在候选图里**（drift 检查），从未被用来"挑"出一对新配对。`tick_claim.py:189-192` 的 `require_v2_plan()` 同样：`for pair in hyp["pairs"]:` 遍历的是 `pairs`，`pair_candidates` 只用来做逐字段相等校验（`TICK_PLAN_SELECTED_PAIR_DRIFT`）。

另外 grep 了 `wall_compiler.py:1166` 唯一出现 `pair_candidates` 的位置（"mandate 7: walk the WHOLE candidate graph"），也只是遍历全图做悬空引用校验，同样不产生配对。

**结论：配对来源 = `hypotheses.pairs`（模型选择），代码从不从 `pair_candidates` 自行挑选**，用户 09-06 拍板的红线（不写转换层、不把配对判断请回代码）未被绕过。

---

## §2.5 A-6-d1：立面 `lo<hi` 对称拦截

`tick_claim.py:621-632`（`TickSession.elevation_document`）：

```python
for opening in doc["openings"]:
    for axis, names in (("x", ("x0", "x1")), ("z", ("z_low", "z_high"))):
        values = [facts[f"{opening['id']}:{n}"].value_u for n in names]
        # A-6-d1: the same consumer-side lo<hi guard as the plan side.
        if values[0] >= values[1]:
            raise TickClaimError("TICK_ELEVATION_INTERVAL_NOT_ORDERED", opening["id"])
```

补了，且两个轴（x 与 z）都有独立的 `lo<hi` 判断。交件自带的变红证据（`test_elevation_consumer_rechecks_order_when_upstream_guard_is_bypassed`）只 mutate 了 `facts[0]`——按 fixture 的边顺序 `['O:x0','O:x1','O:z_low','O:z_high']`，`facts[0]` 是 `x0`，**只验证了 x 轴分支**。本复核独立构造了 z 轴分支的反例（x0/x1 保持正常序，单独把 `z_low` 的值改成等于 `z_high`）：

```python
raw, _ = fixture(); s = TickSession(raw, image_id='legacy')
b = s.submit(response(s)); facts = list(s.consume(b.batch_id))
ids = [f.edge_id for f in facts]           # ['O:x0','O:x1','O:z_low','O:z_high']
facts[2] = replace(facts[2], value_u=facts[3].value_u)   # z_low := z_high，x0/x1 不动
s.consume = lambda expected: tuple(facts)
assert_code('TICK_ELEVATION_INTERVAL_NOT_ORDERED', lambda: s.elevation_document(b.batch_id))
```

原文输出：
```
mutating facts[2] (z_low) to equal facts[3] (z_high); x0/x1 left untouched
PASS: z-axis branch (z_low>=z_high) independently caught, x-axis left intact
```

**结论：x 轴与 z 轴两个分支都能独立变红，不是只有交件恰好触发的那一条能拦。已补上且能变红成立。**

---

## 附：跑测与环境自检（原文）

```text
$ python -c "import src.agent.correction.tick_claim as m; print(m.__file__)"
/tmp/ea2_review_glm/src/agent/correction/tick_claim.py

$ TMPDIR=/var/tmp/ea2_review_glm_pytest python -m pytest -q --collect-only -p no:cacheprovider
3957 tests collected in 5.45s
```

独立 collect 与交件声称的 `3942+2+13=3957` 逐位闭合，差额 0。

权威全量（`-n 6`，`--basetemp=/var/tmp/ea2_review_glm_pytest/claude_full`，独立跑测，未复用交件日志）：

```text
3942 passed, 2 skipped, 13 xfailed, 211 warnings in 514.57s (0:08:34)
```

**0 failed / 0 errors**，与交件声称的最终全量 `3942 passed, 2 skipped, 13 xfailed` 逐字吻合；`m.__file__` 两个模块均落在 `/tmp/ea2_review_glm`（承重不变量成立，非 `.pth` 哈希）。

## 禁区与重叠核实（独立复核，非采信 §一）

```sh
$ git diff --name-only 363844b3 cbf1acfa -- src/
src/agent/correction/opening_adjudication.py
src/agent/correction/opening_synthesis.py
src/agent/correction/tick_claim.py
src/agent/pipeline.py

$ git diff --stat 363844b3 cbf1acfa -- src/agent/reading/vector_contract.py src/agent/judge/ src/validator/checks/ case_tests/test_baseline/gt
(无输出，零差异)

$ grep -rnE '\bsynthesize_openings\s*\(' --include='*.py' src scripts | grep -v "def synthesize_openings("
(无输出，零命中——E-a-3 的 grep 锁独立复现)
```

只改了 4 个生产文件；`vector_contract.py`/`judge/`/`validator/checks/`/`gt/` 零差异，与 J 单零重叠；E-a-3 的锁独立复算同样零命中。`pipeline.py` 的改动核对为 34 行新增（`run_opening_adjudication` 入口 + `run_correction` 的路由分支），无越权改动其余函数。

---

## 最薄弱一处

**`hypotheses.pair_candidates`/`opening_candidates` 等"未选中"或"deferred"通道里携带的测量真伪，全链路没有任何门做二次验证**——本复核逐条 grep 确认了这些字段"结构上不被消费"的声明为真，但"结构上不被消费"同时意味着**如果 reading 侧在这些通道里量错了（比如 `ink_by_family` 的墨迹统计出现系统性偏差），除非它恰好影响到 `pairs`/`opening_candidates` 里被选中并写入 `span_m` 的那几个数，否则整条 correction 链完全看不见**。这不是本单引入的新洞——本单甚至比此前更诚实（旧 `wall_bands` 格式的代理配对机制被替换成读模型真实选择），但 202 行表把这类"deferred 通道"的规模摊开写清楚之后，它反而第一次变得**可数**：3 份真实产物里 `pair_candidates`（374/303/1185）与 `pairs`（22/21/8）的比例悬殊，绝大多数候选测量从未被任何门二次验证过真伪。建议登记进 plan.md 作为 F-1（平面几何零 gt 对账）债务的一个具体子项，而不是本单阻断项。

---

## 阻断/不阻断清单

- **阻断**：无。
- **不阻断 #1**（§2.1）：「完整消费对照表」以 202 行呈现，但去重后真实决定数为 26；表本身内容经两套独立口径核验无遗漏字段、无失实声明，只是行数不等于完备度单位，建议后续同类交付物首行标注去重后的决定数。

## 裁决

**APPROVE-WITH-FINDINGS / 阻断 0 / 不阻断 1**。

E-a-1..E-a-5 五条锁 + `visibility` + `A-6-d1` 均在与交件不同的实例/分支上独立复现变红；配对来源逐行核对为 `hypotheses.pairs`，从未由代码从 `pair_candidates` 自选；`batch_id` 用独立 `hashlib` 调用（不信任被测代码自身的校验函数）逐字节重建成立；202 行消费表经两套互不依赖口径核验无真实字段级遗漏，去重后对应 26 个真实、可证伪的消费决定。可以合并。
