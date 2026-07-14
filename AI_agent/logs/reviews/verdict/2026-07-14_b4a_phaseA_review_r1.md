# B4a Phase A 施工执行审判词 r1(2026-07-14)

- **审向**:Opus 次高档执行审(升一档交叉,GPT 侧 terra 施工 → Claude 侧审,谁写谁不批)→ 主控轻门。
- **需求基准**:`AI_agent/proposals/c2_b4a_detail_spec.md` v2(唯一合同;Phase A 相关节 §4.2/§5/§6/§7/§8.2–8.4/§13 Phase A 行/§14.1)+ 派单 `AI_agent/logs/reviews/request/2026-07-14_b4a_phaseA_construction_dispatch.md`。
- **审的产物**:新 `src/agent/judge/gt_schema.py`(669 行)、`src/agent/judge/gt_manifest.py`(247 行)、`src/configs/judge_gt.yaml`(11 行);改 `src/agent/judge/gt.py`(+101/-5)、A0(+7 行登记);新 `tests/test_gt_schema.py`(166 行/12 测)。
- **信任边界**:仅依据合同原文、代码/测试实体、本审自跑测试与探针输出;施工简报仅用于定位。

---

## 总裁决:REWORK

代码基座质量整体高——strict wire 与合同 §5.2 基本逐字对应、dual-read/loader 分层正确、canonical hash/原子写实现精确、零资产扰动、A0 七行登记齐——但三条 MAJOR 触发 REWORK:

1. **PA-C1**:§7.2.6 opening 语义校验块整体缺件(plan-source 必在、relevant elevation 集↔z-null 一致性重算、host-zone 正宽共线交重算),另加 §7.2.1 elevation view 方向/coverage 关系与 projection key 唯一性未查——合同"必做语义校验"的成块缺失。
2. **PA-C2**:§14.1 测试族大面积未落(12 测 vs 长矩阵;openings 拒族零测试、zone tiling 拒族零测试、default-root candidate 禁令零测试等),简报未逐条列明未竟——Va 批 VA-C2 同型前科。
3. **PA-C3**:candidate writer 保护门两个**实测坐实**的洞:`gt_sources` 根不受保护(`exists()` 过滤掉尚不存在的合同点名根)、非仓库 cwd 下全部保护失效(`Path.cwd()` 锚定)。

**severity 计数**:BLOCKER 0 · MAJOR 3 · MINOR 3 · NIT 1(束)。

---

## 必查焦点逐项结论

### 焦点 2 —— F1 loader 契约(施工者 review-ask):代码合规,测试锁空转

- `gt.py` import 面 = `json/pathlib/pydantic/gt_schema`,零 tooling config 读取、零 `gt_manifest` 引用、零 OmegaConf(本审 grep+读源核实)。
- L2 语义层固定 `validate_gt_v3(document, tolerances=document.generator.tolerances, ...)`(`gt.py:78,92`),Vg 重算用存档容差(`gt_schema.py:483`)。
- **本审实证探针**:构造存档 node_join=0.002(≠当前 judge_gt.yaml 的 0.001)的 verified v3,`load_gt_file` 正常通过并保留 0.002——旧 verified 在 profile 演进后按存档自验证,合同 §6.2 新定案成立。篡改存档 tolerance 不重算 hash → `gt_hash_content_mismatch` 拒,行为正确。
- 「与当轮 profile 相等」断言未出现在 loader:`validate_gt_v3:421` 的 `doc.generator.tolerances != tolerances` 是参数一致性守卫,loader 恒传存档值故恒空转,不构成读当前 profile;§10.8 build 断言留 Phase C,正确。
- **但**:随附的 monkeypatch 回归锁(`test_gt_schema.py:148-153`)patch 的是 `src.agent.judge.gt_manifest.load_gt_tooling_config`——gt.py **从不 import 该符号**,锁不锁任何东西(PA-C5);且合同 §14.1 要求的"存档≠当前 profile"fixture 未构造(PA-C2 表 9 行)。

### 焦点 3 —— §6.3 v2 回归门五条

| 条 | 状态 |
|---|---|
| sm21 SHA 前后相同 | ✓ 本审直测 `a9be379b1735…f3f3f8a`,与简报/测试一致;git diff 零 gt 资产 |
| `load_gt("sm21_anchor")` 深等 raw | ✓ `test_dual_read…:128` 直接断言 |
| v2 render adapter 快照 | n/a Phase A(`gt_render_model.py` 属 Phase D,派单不放行) |
| legacy render 关键断言继续通过 | ✓ `test_gt_render.py` 5 passed(render_gt 走 load_gt→v2 路径不变) |
| 禁测试重写 sm21 | ✓ 无任何测试写 GT 根;writer 拒 GT 根(本审探针 True) |

### 焦点 4 —— §5.5 candidate writer

- ✓ `overwrite: Literal[False]` + 运行时 `overwrite is not False` 拒(`gt_schema.py:622-624`),无 `overwrite=True` 可调用实现;
- ✓ 只收 `status="candidate"`;`out.exists()` 拒;
- ✓ 原子写:同目录 mkstemp + fchmod 0o600 + flush/fsync + **写后重 typed load + validate + hash 复核** + `os.replace`,finally 清理零半文件(`:634-649`);
- ✓ implementation hashes preimage 逐文件 `relative_path + b"\0" + raw_bytes + b"\0"` 按相对 POSIX 路径排序,三组文件清单与 §5.5 逐字一致(`:652-669`);
- ✗ **保护根有洞**(PA-C3,实测):`_protected_candidate_path:619` 的 `if path.exists()` 把尚不存在的 `case_tests/test_baseline/gt_sources` 滤掉——本审探针 `gt_sources protected: False`,而后续 `out.parent.mkdir(parents=True)` 会直接创建并写入;非仓库 cwd 下三根全失效(探针 `from /tmp cwd: False`)。

### 焦点 5 —— §7 validator 完整性

**已落**(点名两项均在):结构层全;zone tiling 用 Shapely `within/intersection/unary_union.symmetric_difference` 对 `dxf_topology_area_tolerance_m2`(`:509-519`,§7.2.4 ✓);**§7.2.5 Vg 重算**用 `doc.generator.tolerances` 构造 `VisibilityTolerances` 四方向重跑 `vg_for_direction`,count 相等 + 逐 (family,p1,p2) 键 item-for-item 比 depth/visible intervals(`:483,522-555`)✓,普通几何字段/排序/fingerprint/hash 复算均在。
**缺件**(PA-C1):§7.2.6 opening 语义块三项 + §7.2.1 两项 + §7.2.3 一项,详见 findings。

### 焦点 6 —— 零资产扰动 / gt 铁律 / 形状开放

- ✓ git status:仅 A0+gt.py 改动与新文件,零 `gt.json`/DXF/PNG/golden 字节变化;sm21 SHA 实测不变;
- ✓ gt 铁律:新模块全在 `src/agent/judge/`;依赖方向 judge→correction(§3.2 允许),correction 未反向;`test_gt_discipline.py` 6 passed;
- ✓ 形状开放:v3 代码无 `range(4)`/固定四面板/固定两层/`_ROLES`/`PLAN_BAND_Y`;`boundary_segments` 仅 `min_length=4` 无上限(§5.2 原文);四方向 Vg 循环与 `FacadeFamily` Literal 属 §14.4 允许的几何 vocab。测试 fixture 只用矩形(>4 段无正例,归 PA-C2),但假设未烤入实现。

### A0 §8.4 登记

✓ 七行齐,name/value/unit/status(provisional)/profile(gt-v3/C2)/hard-warn/用途与合同表逐行一致;判为 judge② tooling only;两条 Vg epsilon 未重复登记(紧邻既有 `FACADE_VISIBILITY_*` 行交叉可见);实现代码中七个数值字面量只出现在 config 与测试(核实)。`judge_gt.yaml` 七值 + profile_version 与 §8.3 建议冻结值逐一相同,model 无默认(§8.3 ✓);`load_gt_tooling_config` 签名/OmegaConf/两 config 原始 bytes SHA/静态关系校验(tie eps < min(node,axis)、Vg eps < node join,落 `GtResolvedToolingTolerancesV1._relationships`)均合 §8.3。

---

## 逐条 findings

### PA-C1 —— MAJOR:§7 语义层成块缺件(opening 块 + source view 方向关系)

`src/agent/judge/gt_schema.py:556-573`(opening 循环)对照合同 §7.2.6,以下**必做**校验缺失:

1. **"opening 的 plan source 必须存在"**——source_refs 只走 `check_refs` 通用校验,不要求至少一条 `role="opening_plan"`;
2. **relevant elevation view 集重算**——"重算'key 命中且 coverage∩visible∩opening 正宽'的 relevant elevation view 集:非空时 z 必填且 `opening_elevation` ref 的 view-id 集必须与它精确相等;空集时 z 必须 null 且不得有 elevation ref"整段未实现。这是 sm26 plan-only `z_interval=null` 语义的**唯一诚实门**:现状下"z 该有而 null"“z 不该有而有”“elevation ref 悬空于无关 view"均静默通过;
3. **host-zone 共线交重算**——"host-zone 的 polygon boundary 与 opening 所在 segment 有正宽共线交……validator 重算"未实现,只查同层存在(`:567-569`),任意同层 zone 可当 host;
4. §7.2.6 "宽度大于 endpoint epsilon" 未查(wire 仅 lo<hi);
5. §7.2.1 "非空 projection surface key 均全局唯一" 未查(`:544-547` 容忍多 view 同 key);
6. §7.2.1 elevation source view "满足 §8.2 direction/coverage 关系"未查:`GtSourceViewV3._kind_contract`(`:83-94`)不锁 `building_axis→azimuth null`、`true_azimuth→azimuth 必填且 == (north_axis_deg+offset)%360`、`full→coverage null`/`partial→coverage 非空`(manifest 侧 `ElevationViewBindingV1` 有,GT 侧没有);
7. §7.2.3 "面积须大于 topology-area tolerance" 未查(sliver polygon 可过)。

已落部分(zone tiling、Vg 重算、hash/fingerprint/排序/verification/north)见焦点 5。缺失项全部是合同"必做语义校验"清单原文,且恰与 PA-C2 未测轴重合。

### PA-C2 —— MAJOR:§14.1 测试族大面积未落 + 未竟未列明

12 测 vs §14.1 矩阵,对账表见文末:**已落 1 行、部分 6 行、缺 3 行**(row 10 属 build 侧 n/a)。整轴缺失:openings 全部拒族(fixture 根本无 openings)、zone gap/overlap/fingerprint-mismatch 拒族、candidate 混 reviewer/verified 缺方法拒族、`gt_default_root_candidate_forbidden` 路径(测试只测了自定义根**接受** candidate,默认根拒线零覆盖)、落盘乱序 `gt_wire_noncanonical_order` 拒、存档≠当前 profile 场景、篡改存档不重算 hash 拒、z null/非空/>4 段/动态 surface 正例。派单原文"稿 §14.1 测试族全数落地;确有未竟逐条列明,不得静默";简报只报"12 passed"未列缺口。Va 批 VA-C2 前科同型:未测轴里恰藏 PA-C1 缺件。

### PA-C3 —— MAJOR:writer/L3 保护门 cwd 锚定 + gt_sources 洞(实测坐实)

`gt_schema.py:614-619 _protected_candidate_path`:
- `protected` 列表带 `if path.exists()` 过滤——`case_tests/test_baseline/gt_sources` **当前不在盘上**(§1.3 定义为未来根),本审探针返回 `gt_sources protected: False`;随后 `:632 out.parent.mkdir(parents=True)` 会创建该根并写入。合同 §5.5 明文三类根"必须先以稳定错误码拒绝",§14.2 亦要求"writer 拒 …gt-sources root";
- 三根全部锚定 `Path.cwd()`——本审探针:cwd=/tmp 时对**真实默认 GT 根**的绝对路径返回 False,保护全失效。`gt.py:93` 的 L3 默认根判等 `Path(gt_dir).resolve() == DEFAULT_GT_DIR.resolve()` 共享同一 cwd 脆弱性(非仓库 cwd + 绝对路径指向真默认根时 L3 被绕过)。修法:以仓库根锚定(如相对本模块 `__file__` 推导或显式 repo_root 参数),protected 判定不依赖 `exists()`。

### PA-C4 —— MINOR:L3 自定义根 candidate 准入与合同文字冲突

`gt.py:91-94` 只在默认根拒 candidate;`test_gt_schema.py:135` 显式断言自定义根 `load_gt_document` **接受** candidate。合同 §6.2 L3 行原文"自定义根不因此成为 candidate 入口"与后文"调用者若要读 candidate 应明确用 file API"支持更严读法(typed case API 任何根拒 candidate);同段"默认 GT 根中的 v3 还要求 human_verified"又限定于默认根。两句张力,施工采取宽读法并用测试固化。裁决:归主控定夺——或收紧实现为任何根拒 candidate,或在合同/A0 留痕明示宽读法;现状不得默认成立。

### PA-C5 —— MINOR:monkeypatch 回归锁空转

`test_gt_schema.py:152` patch `src.agent.judge.gt_manifest.load_gt_tooling_config`,而 `gt.py` 源内零 `gt_manifest` 引用(本审核实)——该锁对"load 路径读 tooling config"零拦截力,任何回归(如未来 gt.py 直接 `OmegaConf.load('src/configs/judge_gt.yaml')`)不会被抓。合同 §14.1 要求"测试以 monkeypatch 证明 load 路径未读 tooling config"。修法:patch `omegaconf.OmegaConf.load`/文件 open 于两个 config 路径为 raise,再走 `load_gt_file`+`load_gt_document` 双入口,配合"存档≠当前 profile"fixture(本审探针已证行为正确,缺的是锁)。

### PA-C6 —— MINOR:manifest §8.2 wire 自查缺件

`gt_manifest.py`:①`manifest_sha256` 的 canonical 置零重算自查未实现(§8.2 "manifest hash 的 canonical 规则与 GT 相同,hash 字段置零后计算"——现在任意 64hex 都过);②"floor/view/opening/evidence ID 与 elevation projection_surface_key 各自在文档内唯一"只查了 floor/view,opening_id/evidence_id/projection_surface_key 跨 view 唯一性未查;③raster overlay 的 `view_id` 存在性未查(north_axis 的查了)。§8.2 属派单 Phase A 放行面。

### PA-C7 —— NIT(束)

①`Point2`/`outward_normal` 用 `list` 替代合同 `tuple`(`gt_schema.py:37` 有注释说明 strict tuple 拒 JSON array;dump 字节等价,理由成立,留痕即可);②`GtSourceViewV3` 六个 nullable 字段与 `wall_thickness_m` 加了合同 §5.2 没有的 `= None` 默认——缺字段会被静默接受,偏离"除显式 nullable/default 外没有隐藏字段"的 wire 严格性(canonical dump 仍显式写 null,round-trip 无损);③`validate_gt_v3:445` methods canonical 检查在 436/438 之后不可达(死代码);④`compute_gt_implementation_hashes` 在 Phase A 恒 fail(extractor 组含尚不存在的 `gt_extraction.py`),fail-closed 合理但零测试;⑤§5.4 segment ID 截断碰撞校验未进 validator(生成侧职责,Phase C 落地时须记得);⑥`load_gt_tooling_config:229` 的 correction.yaml 判等同样 cwd 锚定(并入 PA-C3 修法)。

---

## §14.1 测试族对账表(合同行 → 落点/缺失)

| # | §14.1 要求 | 落点 | 裁定 |
|---|---|---|---|
| 1 | 接受 candidate/verified、north null/非空、z null/非空、>4 segment、动态 surface;拒 candidate 混 reviewer/method、verified 缺四法 | `test_v3_candidate_and_verified`(candidate+verified+north 两态 ✓) | **部分**:z null/非空、>4 段、动态 surface 正例缺(fixture 无 openings、矩形四段、零 elevation view);两拒例零测试 |
| 2 | 拒 extra field、string number/bool、NaN/Inf、闭环重复首点、CW/nonorth/self-touch/hole/multipolygon | `test_v3_strict_wire_rejects_bad_shapes`(extra ✓、"3" 版本+"3" 高度 ✓、闭环 ✓) | **部分**:bool/NaN-Inf/CW/nonorth/self-touch/hole 拒例缺(实现有码,shipped-untested) |
| 3 | 拒 zone gap/overlap、fingerprint/hash mismatch | —— | **缺**(hash mismatch 仅经 writer 间接;零直接拒例) |
| 4 | 拒 segment family/normal/p1 顺序/along/depth/visibility/fingerprint 漂移 | `test_validator_rejects_hash_ring_and_segment_drift`(depth ✓) | **部分**:其余六类漂移零测试 |
| 5 | 拒 opening cross-floor/ref missing/out-of-span/ambiguous host/z 越层 | —— | **缺**(整轴零测试;PA-C1 缺件藏此) |
| 6 | schema 2/3 integer only;v2 fixture read;缺版本/v1/未知版本 fail | `test_unknown_version…`(None/1/4/"2"/True/2.0 ✓)+ `test_dual_read`(sm21 ✓) | **已落** |
| 7 | extractor 乱序 hash 不变(Phase B/C);落盘乱序 `gt_wire_noncanonical_order` 拒;坐标变 hash 变 | 坐标变 hash 弱断言 ✓(json dumps 对比) | **部分**:落盘乱序拒零测试(validator 有码) |
| 8 | load_gt missing→None、v2 raw、v3 typed gate;file 接 candidate;default-root 拒 candidate 接 verified;bad JSON/traversal | v2 raw ✓、v3 gate ✓、file candidate ✓(writer round-trip)、traversal ✓ | **部分**:missing→None、default-root 拒 candidate(`gt_default_root_candidate_forbidden` 零覆盖)、bad JSON 缺 |
| 9 | 存档≠当前 profile 的旧 verified 仍过 + monkeypatch 证明不读 config + 篡改存档不重算 hash 拒 | `test_loader_uses_archived…`(monkeypatch 空转,PA-C5) | **部分→缺**:存档≠当前 fixture 未构造、tamper 拒零测试(本审探针证明两行为均正确,缺的是测试) |
| 10 | build 单字段差异 writer 前 fail;断言不入 loader | n/a(Phase A 无 build 入口) | **n/a**:核实断言确未入 loader(validate 的参数一致性守卫在 load 侧恒空转) |

小结:已落 1 / 部分 6 / 缺 3 / n-a 1。

---

## 定向测试组结果(本审自跑)

`pytest tests/test_gt_schema.py tests/test_gt_discipline.py tests/test_gt_render.py tests/test_reading_score.py tests/test_elevation_score.py tests/test_judge_harness.py -q` → **74 passed**(gt_schema 12 + discipline 6 + render 5 + reading_score 17 + elevation_score 16 + judge_harness 18),与简报逐组一致。全量 pytest 归主控轻门。

本审探针(scratchpad,未入仓):①protected-path 谓词:gt 根 True / **gt_sources False** / case_data True / **非仓库 cwd 全 False**;②存档≠当前 profile verified 正常 load 且保留存档值;③篡改存档 tolerance 不重算 hash → `gt_hash_content_mismatch` 拒;④sm21 SHA `a9be379b…` 不变;⑤gt.py 源零 `gt_manifest` 引用。

---

## 返工清单(主控裁决后下发)

1. **[PA-C1]** 补 §7.2.6 opening 语义块(plan-source 必在、relevant elevation view 集重算↔z-null/elevation-ref 精确一致、host-zone 正宽共线交重算、宽度>endpoint epsilon)+ §7.2.1 projection key 全局唯一 + elevation view §8.2 方向/coverage 关系 + §7.2.3 面积>tolerance。
2. **[PA-C3]** `_protected_candidate_path` 去 `exists()` 过滤、以仓库根(非 cwd)锚定三保护根;`load_gt_document` L3 判等与 `load_gt_tooling_config` 的 correction.yaml 判等同改。
3. **[PA-C2]** 按对账表补齐:openings 拒族(顺带成为 PA-C1 的回归抓手)、zone gap/overlap/fingerprint 拒、verification 混合拒、default-root candidate 拒、落盘乱序拒、存档≠当前 profile fixture、tamper-hash 拒、z/段数/动态 surface 正例;确属后续 phase 的逐条列明。
4. **[PA-C5]** monkeypatch 锁改为拦真实读取面(OmegaConf.load/config open)并覆盖两个 typed 入口。
5. **[PA-C4]** L3 自定义根 candidate 准入交主控裁决后按裁决收紧或留痕。
6. **[PA-C6]** manifest_sha256 自查 + opening/evidence/projection-key 唯一性 + raster view_id 存在性。
7. **[PA-C7]** 酌情:去死代码、`= None` 默认对齐 §5.2、implementation-hash 函数补测(可 xfail 至 Phase B 文件到位)。

核 wire/loader/canonical 基座扎实,返工有界:一块语义校验、一处保护锚定、一批测试。

---

# r2 复审(2026-07-14)

同审向、同基准,对象=返工后工作树(gt_schema.py 669→734、gt_manifest.py 247→277、gt.py 138→140、test_gt_schema.py 166→353/12→36 测)。工作树复核:仍仅 A0(+7,与 r1 相同)+gt.py 改动与新文件,零资产扰动,sm21 SHA 断言在测试内继续通过。

## r1 findings 逐条闭合

| r1 finding | 状态 | 闭合证据 |
|---|---|---|
| PA-C1(MAJOR 语义缺件) | **CLOSED** | 全部缺件落地且**实现正确**(review-ask #1 逐条对照 §7.2.6/§7.2.1 原文核过):①plan-source 必在(`gt_schema.py:595-598`,`gt_opening_plan_source_missing`);②relevant elevation view 集重算(`:602-617`)——对 segment 每个 projection key 取 view,`coverage = world_along_coverage or segment full interval`(full view null coverage 按 §10.7 处理 ✓),opening∩visible∩coverage 三重正宽判定,非空⇒z 必填且 `opening_elevation` ref 的 view-id 集精确相等,空⇒z null 且零 elevation ref——与 §7.2.6 原文逐句对应;③host-zone 正宽共线交重算(`:618-631`)——逐 zone 边与 segment 同线正宽重叠,重算结果必须恰为 `[host_zone_id]`(恰一 zone,合 §10.6 唯一性);④宽度>vg_endpoint_epsilon(`:589`);⑤projection key 全局唯一(`:463-468`);⑥elevation view 方向/coverage 关系(`:469-478`)——building_axis⇒azimuth null、true_azimuth⇒`azimuth == (north_axis_deg+offset)%360` 精确等式(offset N0/E90/S180/W270 合 §8.2)且 north 非空、full⇒coverage null/partial⇒非空;⑦footprint/zone 面积>topology tolerance(`:530-534`)。本审另跑 4 条 repo 未测方向的行为探针:plan-only+z 非空→`gt_opening_plan_only_evidence_mismatch`、无 relevant view+悬空 elevation ref→同 code、重复 projection key→`gt_source_duplicate_projection_surface_key`、双 zone 共享 segment→`gt_opening_host_zone_boundary_mismatch`,全部按合同 fail-closed。 |
| PA-C2(MAJOR 测试族) | **CLOSED(实质)** | 12→36 测;对账表重录见下:已落 7 / 部分 2 / n-a 1。r1 三条整缺轴全落:openings 拒族 5 例(cross-floor/host null/越 span/z 越层/无 plan ref)+relevance 3 例;zone gap/overlap/fingerprint/hash-tamper 4 例;candidate 混 reviewer+verified 缺方法 2 例;default-root 禁令双测(自定义根翻转+monkeypatch 默认根);落盘乱序拒;存档 0.002≠当前 0.001 fixture+真 monkeypatch;z null/非空正例、L 形 6 段(>4)、动态 surface 正例齐。 |
| PA-C3(MAJOR 保护门) | **CLOSED** | `REPO_ROOT = Path(__file__).resolve().parents[3]`(`gt_schema.py:38`)替代 cwd;`_protected_candidate_path`(`:672-684`)去 `exists()` 过滤、gt_sources 无条件入表、最近存在父目录逐级上溯+`resolve(strict=True)` 解 symlink 后重拼未建后缀。**r1 两个攻击探针复跑全拦**:gt_sources(未建)True、/tmp cwd 下三根全 True;symlink 逃逸探针(指向 gt 根/未建 gt_sources)全 True;测试 `test_candidate_writer_rejects_protected_roots_cwd_and_symlink_escape` 覆盖四类且断言 gt_sources 前后均未被误建(review-ask #2 裁决:symlink 负例真拦)。`DEFAULT_GT_DIR`(gt.py:29)与 `load_gt_tooling_config` 的 correction.yaml 判等(gt_manifest.py:259)同步改 REPO_ROOT 锚定,后者有专测 `test_config_root_is_not_cwd_anchored`。 |
| PA-C4(MINOR L3 宽读法) | **CLOSED(按主控裁决收紧)** | `gt.py:93-96`:`load_gt_document` 无论 gt_dir 一律要求 v3 `human_verified`,candidate 只走 `load_gt_file`;r1 固化宽读法的测试已翻转(`test_dual_read…:162-164` 现断言自定义根 candidate → `gt_default_root_candidate_forbidden`)+默认根专测(`:305-313`)。 |
| PA-C5(MINOR monkeypatch 空转) | **CLOSED** | 锁改为 patch `pathlib.Path.read_bytes` 对两个 config 绝对路径 raise(`test_gt_schema.py:183-189`),接真实读取面;双 typed 入口(`load_gt_file`+`load_gt_document`)均在锁下用存档 0.002≠当前 0.001 的 verified 走通;`test_tampered_archived_tolerance…` 补上篡改不重算 hash→`gt_hash_content_mismatch` 拒。残留:锁不拦假想的直接 `OmegaConf.load`(其用 `open()` 非 `Path.read_bytes`),但拦住最现实回归面(误调 `load_gt_tooling_config`→`_raw_sha256` 走 read_bytes)——记 NIT。 |
| PA-C6(MINOR manifest 自查) | **CLOSED** | `manifest_sha256` 置零 canonical(同 GT 规则:sort_keys/compact/ensure_ascii=False/allow_nan=False/末尾换行)重算自查(`gt_manifest.py:223-224,228-246`)+坏 hash 拒测试;opening/evidence/projection-key 文档级唯一(`:215-220`);raster overlay view_id 存在性(`:221-222`)+拒测试。 |
| PA-C7(NIT 束) | 部分闭合 | ②`GtSourceViewV3` 六字段的 `= None` 默认已删(缺字段现拒)✓;⑥config cwd 锚定已修 ✓;①Point2 list(留痕理由成立)、③`:446` 死代码、④implementation-hash 函数 Phase A 恒 fail 且零测试、⑤segment ID 截断碰撞归 extractor——维持 NIT,另见 r2 残留清单。 |

## §14.1 对账表(r2 重录)

| # | r2 状态 | 落点/残留 |
|---|---|---|
| 1 | **已落** | candidate/verified/north 双态/z null+非空(`_opening_payload` 两态)/L 形 6 段>4/动态 surface(elev view+key)正例全;candidate 混 reviewer 拒+verified 缺方法拒 |
| 2 | 部分 | extra/string number/闭环 ✓;bool、NaN/Inf、CW、nonorth、self-touch、hole、multipolygon 拒例仍缺(实现有码,本审 r1 已核 `_ring_vertices`/holes 门存在) |
| 3 | **已落** | zone gap(tiling_mismatch)/overlap/fingerprint 漂移/hash 篡改四拒例 |
| 4 | **已落** | family/normal/p1/along/visibility/fingerprint 六参数化 + depth(r1)七类漂移全 |
| 5 | **已落** | cross-floor/host null/越 span/z 越层/无 plan ref 五例 + relevance 三例;残留:双 zone 歧义 host 无 repo 测例(本审探针已证 fail 正确) |
| 6 | **已落** | 不变 |
| 7 | **已落** | 落盘乱序→`gt_wire_noncanonical_order` ✓;坐标变 hash ✓;extractor 乱序归 Phase B/C |
| 8 | 部分 | v2 raw/v3 gate/file candidate/任意根拒 candidate/接 verified/traversal 全 ✓;`load_gt` missing→None 与 bad JSON(非法 JSON 文本)两小口仍无测 |
| 9 | **已落** | 存档≠当前 fixture ✓ + 真 monkeypatch ✓ + tamper 拒 ✓(OmegaConf 面局限记 NIT) |
| 10 | n/a | build 侧,Phase C;断言未入 loader(维持 r1 核实) |

已落 7 / 部分 2 / n-a 1(r1:已落 1 / 部分 6 / 缺 3)。

## 残留 findings

### PA-R1 —— MINOR:未来 e2e case 目录不受写保护

`gt_schema.py:683` 用 `(REPO_ROOT / "case_tests/e2e_tests").glob("*/case_data")` 枚举保护根——glob 只见既有 case 目录。本审探针:`case_tests/e2e_tests/brand_new_case/case_data/x.json`(case 目录未建)返回 False,writer 会创建整条链写入。合同 §5.5 "任何 `case_tests/e2e_tests/*/case_data`" 按字面含未来 case。影响窄(既有 case_data 全保护;新建目录在 git status 显眼;§14.4 diff 门兜底),修法小:对 resolved 相对路径做 `parts` 模式匹配(`('case_tests','e2e_tests',*,'case_data')` 前缀)替代 glob。

### PA-R2 —— NIT(束)

①§14.1 row 2 剩余拒例(bool/NaN-Inf/CW/nonorth/self-touch/hole/multipolygon)与 row 8 两小口(missing→None、bad JSON)仍无测;②双 zone 歧义 host、重复 projection key、plan-only 两向 mismatch 已由实现覆盖且本审探针证实,建议 Phase B/C 补 repo 测例固化;③monkeypatch 锁不拦直接 `OmegaConf.load`(可加 `omegaconf.OmegaConf.load` 联合 patch);④`wall_thickness_m` 仍带合同外 `= None` 默认;⑤`:446` methods canonical 死代码、`:465` 生产 `assert`(-O 可剥离,宜改显式 raise);⑥`compute_gt_implementation_hashes` Phase A 恒 fail(gt_extraction.py 未建)且零测试;⑦`gt_default_root_candidate_forbidden` 错误码现用于任意 case 根,名称与语义略偏(稳定码不改,留痕即可)。

## 定向测试组结果(r2 自跑)

六组:**98 passed**(gt_schema 36 + discipline 6 + render 5 + reading_score 17 + elevation_score 16 + judge_harness 18)。
本审探针(scratchpad,未入仓):①r1 两攻击探针复跑=gt_sources(未建)/非仓库 cwd 三根全拦;②symlink 逃逸(gt 根/未建 gt_sources)全拦,gt_sources 未被误建;③四条未测语义路径 fail-closed 正确;④残留=未来 e2e case 目录 False(PA-R1)。

## r2 总裁决:APPROVE-WITH-CHANGES

r1 六条全闭(PA-C4 按主控裁决收紧且测试翻转);两项新 review-ask 均裁决通过(opening/elevation 语义门实现与合同逐句一致+四路探针 fail-closed 正确;repo 锚定+symlink 负例真拦)。残留 1 MINOR(PA-R1 未来 e2e case 目录,修法一行级)+ 1 NIT 束(PA-R2),无正确性缺陷,不需再开返工轮:PA-R1 可随本批小补丁或明示挂账 Phase B,由主控裁决;全量 suite 权威门归主控轻门。
