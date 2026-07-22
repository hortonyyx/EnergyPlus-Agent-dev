# 天正 DXF → GT v3 转换器 P0–P2 独立复核裁决

**审阅对象**：`edf1477`（P0）/ `d5e57e3`（P1）/ `a0c2a6c`（P2）  
**审阅日期**：2026-07-22  
**审阅范围**：`src/agent/judge/tarch_converter_schema.py`、`src/agent/judge/tarch_normalize.py`、三份转换器测试、gt 隔离守卫及 sm24 晋升产物  
**权威依据**：`AI_agent/proposals/tarch_to_gtv3_converter_plan.md`、施工派单、opus 算法正文、SURVEY；施工交付说明仅作为待验断言  
**裁决**：**需返工（REWORK）**

## 1. 裁决摘要

sm24 当前样本的数值出口能够复现，且四个施工期 bug 中，真句柄、共线 jamb 清理、manifest 双缩放三项确实修到了已观察根因；全量测试也确为 `1508 passed, 9 xfailed`。这些是已验真的局部正确项。

但本批不能批准，原因是“绝不静默出错”的主保险尚未成立：

1. G8 虽然形式上只收 `zones`，实际不读取 `basis` 或 `thickness`，而是信任正向 S7 已算好的 `offset_native`，再做正向外扩的代数逆。独立构造的错误墙轴线和面积补偿反例均能让 G7、G8 同时为零残差。
2. 三道承重件中，近阈值清单只是 evidence，G8 可被上述反例绕过，G10 在无人签字、状态仍为 `candidate` 时就被标成 `passed=true`。因此施工方所称“三道承重闸门齐”不成立。
3. source-hash-bound 契约没有在运行时校验。把声明 SHA 改成 64 个 `0` 后，sm24 仍然全门绿并生成 `PASS` 报告。
4. S7 没有实现规格要求的“事件坐标精确计算”，而是用了 `1 native unit` 步进、`50000 native units` 上限、`1 native unit` 外环距离及依赖合法墙厚上限的探针 pad。变厚度反例会漏检或把 220 mm 处的变化定位到 477.5 mm。
5. 九门必红测试大部分没有绑定 gate。逐门强制放行后，G1/G2/G3/G4/G7/G8/G9 的 35 个 P1/P2 测试仍全部通过。

这些不是补文档即可结清的问题；需要改实现、补真正的门级变异测试并重跑出口门。

## 2. Findings（按严重度排序）

### BLOCKER B-01 — G8 是正向外扩的代数回放，不是由输出 `basis/thickness` 独立重建墙带，可对错误几何假绿

**缺陷陈述**：`g8_reconstruct_wall_region` 只使用 `z.polygon`、隐藏的边法向和正向阶段已计算的 `offset_native`；`basis`、`thickness_native` 完全未参与计算。反演腔体正是 S7 外扩的代数逆，再计算 `union(zones) - union(reconstructed_cavities)`。在 G7 已保证 `union(zones) == footprint` 时，它非常接近 `footprint - S5 cavities == S5 wall_region` 的恒等式。

**具体失败场景 A（错误墙轴线仍全绿）**：真实内墙面为 x=3880/4120，真实轴线 x=4000；故意把输出共享边放到 x=4060，左区记录 `wall_axis, thickness=360, offset=180`，右区记录 `wall_axis, thickness=120, offset=60`。输出轴线偏了 60 mm、同一道墙两侧厚度互相冲突，但两个区仍无缝铺满 footprint；反向减掉各自 offset 又恰好回到真实两腔体。因此实测得到：G7 对称差 `0.0`、重叠 `0.0`、G8 对称差 `0.0`。

**具体失败场景 B（裁决稿点名的面积补偿误差）**：在连续 10 m² 条带中，外部真值为 A=1.5 m² 小房间、B=2.5 m² 墙材、C=6.0 m² 房间，`A_room=2`。S5 会把 B、C 当作两个腔体而吞掉 A；数量仍是人声明的 2。实际跑 S5/S6/S7/G8 得到：G6 计数会过、G7 对称差/重叠均 `0.0`、G8 对称差 `0.0`、诊断为空。近阈值列表虽列出 A/B，却不阻断。

**核验方式**：用独立 Shapely 几何直接构造上述两组 `ZoneExpansion`/faces，不复用施工方测试期望；分别计算 G7 两项与 `g8_reconstruct_wall_region(...).symmetric_difference(measured_wall)`。另把边的 `basis/thickness` 任意改为 `outer_skin/9999` 和 `outer_skin/1`、保持 offset 不变，G8 WKB 字节完全不变且残差仍为 0，证明函数没有消费这两个契约字段。

**位置**：

- `src/agent/judge/tarch_normalize.py:1248-1282`（G8 只减 `offset_native`）
- `src/agent/judge/tarch_normalize.py:1392-1409`（只把上述结果与 WallRegion 比较）
- `src/agent/judge/tarch_normalize.py:1206-1232`（offset 由同一正向对象产生）
- `tests/test_tarch_converter_p2_geometry.py:373-401`（夹具同时改 basis 和 offset，且只手算 sd，不重新触发 G8 gate；也没有改 thickness）

**判定**：不满足“由输出 zone 边 + basis + thickness 独立重建墙带”及“逆向路径不与正向共享代码/派生量”。这是主保险失效，必须阻断合入。

### BLOCKER B-02 — 近阈值面和 G10 都不是承重门；未人核的 candidate 已被记成全门 PASS

**缺陷陈述**：近阈值面仅塞入 G6 evidence，不要求人工确认；G10 只检查 SVG 路径对象非空，随后直接 `passed=true`，同时 evidence 明写 `verification_status="candidate"`。报告状态只由 BLOCK 诊断决定，不检查所有 gates 都通过。

**具体失败场景**：B-01 的面积补偿例会通过全部机器几何门，真正剩下的保险只有人核；但当前仅创建 overlay 就让 G10 通过并允许 `status=PASS`。进一步把正常 sm24 的 `_outer_skin_gap_count` 临时替换为 `-1`，得到 G4 `passed=false`、BLOCK 诊断数 0、bundle 已写、最终报告仍为 `PASS`，实证“红门不必阻断落盘”。

**核验方式**：

- 运行真实 sm24，临时让 G4 helper 返回 `-1`；输出为 `{G4_passed:false, block_diag_count:0, bundle_written:true, report_status:"PASS"}`。
- 检查晋升报告：顶层 `status="PASS"`，G10 `passed=true`，但同一项 evidence 为 `candidate`。
- 目检 overlay：8 个彩色区和单一 L 形走廊可见，但 z5 的几何 centroid 落在自身多边形外，标签实际画到了相邻 z6 上；这进一步说明“文件存在”不能等同“人已核通过”。

**位置**：

- `src/agent/judge/tarch_normalize.py:1363-1372`（近阈值面仅作 evidence）
- `src/agent/judge/tarch_normalize.py:1723-1754`（是否落盘看诊断；G10 只看路径非空）
- `src/agent/judge/tarch_normalize.py:1831-1847`（报告 status 不看 gate）
- `src/agent/judge/tarch_converter_schema.py:920-931`（PASS validator 同样不检查 gate）
- `case_tests/test_baseline/gt_sources/sm24_anchor/conversion_report.json:3`
- `case_tests/test_baseline/gt_sources/sm24_anchor/conversion_report.json:2977-2983`
- `src/agent/judge/tarch_normalize.py:1671-1674`（凹多边形用 centroid 放标签）

**附带产物问题**：晋升报告的 `overlay_asset` 是绝对 staging 路径，而被提交的 overlay 在 `case_tests/.../sm24_anchor/overlay_plan.svg`；staging 文件未入 git。换工作区或 fresh clone 后 evidence 指针失效。位置：`src/agent/judge/tarch_normalize.py:1751-1754`、晋升报告 `:2981`。

### BLOCKER B-03 — source/request hash 绑定没有运行时校验，错误源可静默出 PASS

**缺陷陈述**：注册表有 `tarch_input_source_hash_mismatch`，但 S0–S9 从未比较输入文件 SHA 与 `request.source_dxf_sha256`，也未验证 `request.request_sha256 == compute_request_sha256(request)`。

**具体失败场景**：把 sm24 请求的 `source_dxf_sha256` 改为 64 个 `0`，重新计算请求自哈希，再对真实 sm24 文件运行 P1。结果：没有 hash mismatch 诊断、`has_block=false`、全部 P1 gates 通过、报告 `PASS`。因此一个绑定到 A 图的意图文件可以用于 B 图，答案仍被接受。

**核验方式**：实际复制 sm24 到临时 staging，构造错误声明 SHA 的合法 Pydantic 请求并运行 `run_p1_plan_view` + `build_p1_report`；同时用 AST 枚举 `_diag(...)` 调用，确认该码没有算法发射点。

**位置**：

- `src/agent/judge/tarch_converter_schema.py:242-246`（声明了 BLOCK 码）
- `src/agent/judge/tarch_normalize.py:678-718`（入口直接读文件，无 hash gate）
- `src/agent/judge/tarch_normalize.py:1837-1844`（报告分别写实际 hash 和请求 hash，但不对账）

### MAJOR M-01 — S7 用采样启发式代替规格要求的事件坐标精确求解，且合法墙厚上限直接改变输出数值

**缺陷陈述**：权威算法要求用 WallRegion 顶点投影的事件坐标精确分段、无采样参数；实现却使用 `step=1.0`、最大 march `50000.0`、外环距离 `<=1.0`，再用 `wall_thickness_range_m[1]/2 + tau_node` 作为探针 pad。合法性上限因而成为几何算法的数值来源，而非只作 sanity。

**具体失败场景**：同一条 10 m 墙，前 220 mm 厚 300 mm、其余厚 100 mm；两个合法范围 `[0.06,0.35]` 与 `[0.06,0.50]` 都包含真实厚度。前者输出两段但把真实 220 mm 变化点放到 477.5 mm，后者输出整边 100 mm、完全漏掉变化。另造中间 2 m 从 100→300→100 的墙，两端探针相同，整段被报告成 100 mm。

**核验方式**：直接对独立构造的 Shapely WallRegion 调 `_thickness_profile`，只改变合法上限；记录上述 profile。还以 native unit=`m` 构造 0.4 m 内墙，其远端距 footprint 外环 0.8 m，硬编码 `<=1.0` 把它错判成 `outer_skin`。

**位置**：

- `AI_agent/proposals/tarch_to_gtv3_converter_plan_opus.md:334-341`（事件坐标、无采样参数、失败诊断要求）
- `src/agent/judge/tarch_normalize.py:919-940`（1/50000/1 三个 native-unit 常量）
- `src/agent/judge/tarch_normalize.py:943-1024`（只看两端；相等即假定整段均匀；pad 级停止）
- `src/agent/judge/tarch_normalize.py:1699-1701`（合法墙厚上限进入 pad）
- `AI_agent/logs/reviews/execution/2026-07-22_tarch_converter_p2_glm.md:93`、`:111-120`（施工方已披露缺变厚夹具，但未披露算法会受 range 驱动）

**四 bug 中 #2 的判定**：新 pad 确实把 sm24 的 overlap 从 0.0109 m² 修到 0，修住了当前图的“角点擦墙”症状；但它没有触及“应按精确事件求交、不得采样/猜测”的根因，且制造了范围依赖与大幅错位，故只能判 **部分修复，根因未闭合**。

### MAJOR M-02 — 输出厚度没有绑定六类离散证据；zone/source_map 只有墙面句柄，没有 thickness proof

**缺陷陈述**：S7 的厚度直接从 S5 派生 WallRegion 射线距离取得，不与 P1 wall-band/cap evidence 对账。`_ZoneEdgeRec` 只存数值和普通墙线句柄；`ZoneEdgeReportV1` 没有 `ThicknessEvidenceV1`；实际 source_map 的 34 条记录中 `proof_ids` 全空。

**具体失败场景**：用一个 240 mm 墙环调用 S7，传 `wall_lines=[]`。函数仍输出四条 240 mm 边、无任何诊断，G8 残差为 0；所有 `source_handles` 为空。也就是说，算法可以在六类证据一项都没有时完成厚度推导和 G8 自证。生产路径随后可能因 Pydantic 的 `min_length=1` 直接崩溃，但不会得到规定的 `tarch_wall_thickness_unevidenced` / `tarch_provenance_incomplete` 定位诊断。

**核验方式**：对独立单房 Shapely fixture 实跑 `s7_expand_zones(..., wall_lines=[])` 和 G8；另检查晋升 `source_map.json`，34/34 项 `proof_ids=[]`。

**位置**：

- `src/agent/judge/tarch_converter_schema.py:176-195`（六类证据契约）
- `src/agent/judge/tarch_normalize.py:919-974`（实际厚度来源为 WallRegion march）
- `src/agent/judge/tarch_normalize.py:1041-1067`（仅匹配墙面 LINE handle）
- `src/agent/judge/tarch_converter_schema.py:870-878`（报告边无 evidence 字段）
- `src/agent/judge/tarch_normalize.py:1521-1537`（source_map 未写 proof_ids）

### MAJOR M-03 — 九门必红夹具大面积 false-lock；只有 G6 真正一对一绑定目标 gate

**缺陷陈述**：P1 多数负例只断言诊断码，P2 的 G4/G7/G8/G9 负例只直接调用 helper 或手算几何，没有在破坏输入后重新执行对应 gate。G8 测试还同时篡改了 offset，掩盖了 G8 不读取 basis/thickness 的事实。

**活体变异结果**：在独立 Python 进程中先调用原 gate assembly，再把指定 gate 的 `passed` 强制改成 `True`，对两份 P1/P2 测试完整跑 35 项：

| 被 neuter 的门 | 结果 | 判定 |
|---|---:|---|
| G1 | 35 passed | false-lock |
| G2 | 35 passed | false-lock |
| G3 | 35 passed | false-lock |
| G4 | 35 passed | false-lock |
| G5 | 2 failed / 33 passed | 仅两个重复 free-end 夹具绑定；面积子门未绑定 |
| G6 | 1 failed / 34 passed | 真正绑定目标门 |
| G7 | 35 passed | false-lock |
| G8 | 35 passed | false-lock |
| G9 | 35 passed | false-lock |

G10 无必红夹具，施工说明称“无真正 fail 模式”，与其作为人工签字流程门的规格相反。

**位置**：

- `tests/test_tarch_converter_p1_geometry.py:267-400`（多数只断言诊断/helper）
- `tests/test_tarch_converter_p2_geometry.py:373-474`（G4/G7/G8/G9 不重跑 gate）
- `tests/test_tarch_converter_p2_geometry.py:404-414`（G6 是唯一一对一门级夹具）
- `tests/test_tarch_converter_p1_geometry.py:387-400`（G5 面积夹具直接造不可能的 s4 dict）

**附带 G5 问题**：生产实现把 `footprint=unary_union(faces)`，再比较 `sum(face.area)` 与该 union 的 area；polygonize 产出的 faces 正常互斥时该面积式按构造成立。测试注释也承认“clean polygonize cannot mismatch”。因此 G5 的 200 m² 数字虽在 sm24 正确，却没有独立外包证人。位置：`src/agent/judge/tarch_normalize.py:582-595`、`:755-763`。

### MAJOR M-04 — fail-closed 并未全链保留：歧义会按优先级猜，非法几何会被 `buffer(0)` 静默修补

**具体失败场景 A**：dialect 同时声明 `window_block_names=["X_DOOR"]` 和 `door_block_prefixes=["X_"]`。`X_DOOR` 同时匹配门窗两类，实现固定返回 `window`，而不是 `tarch_opening_kind_ambiguous`。

**具体失败场景 B**：S7 外扩或 G8 反缩产生自交/非法多边形时，代码调用 `buffer(0)` 猜一个修复形状并继续；没有 BLOCK 诊断，也没有最小冲突集。这可能改变拓扑甚至从 Polygon 变为 MultiPolygon。

**具体失败场景 C**：opening 多解诊断只报告 `candidate_count`，`solutions` 没携带候选 cap handles，因而无法列派单要求的最小冲突集。

**核验方式**：实际构造重叠 dialect 规则，`_classify_block("X_DOOR", rules)` 返回 `window`；逐分支检查非法 polygon 路径和 opening ambiguity payload。

**位置**：

- `src/agent/judge/tarch_converter_schema.py:510-519`（dialect 无互斥校验）
- `src/agent/judge/tarch_normalize.py:465-471`（window 优先）
- `src/agent/judge/tarch_normalize.py:474-493`、`:541-547`（多解不保留冲突句柄）
- `src/agent/judge/tarch_normalize.py:1235-1239`、`:1276-1279`（静默 `buffer(0)`）

### MAJOR M-05 — “39 码全覆盖”只是枚举可实例化；17 个诊断码在算法体没有任何发射点

**缺陷陈述**：P0 测试只遍历 registry 构造对象，并不证明生产分支会发码。AST 核对 39 个 registry key 与全部 `_diag("literal")` 调用后，只有 22 码可由算法发出，17 码从未接线。

**具体失败场景**：输入源 hash 错误、厚度无证据、source_map provenance 不完整等契约违规均无法发出注册表承诺的专用 BLOCK 码；B-03 和 M-02 的活体反例已经分别让前两类路径静默通过或脱离诊断体系。

**未接线码**：`tarch_input_source_hash_mismatch`、`tarch_wall_thickness_unevidenced`、`tarch_wall_entity_unaccounted`、`tarch_opening_fill_conflict`、`tarch_opening_gap_unexplained`、`tarch_opening_evidence_unbound`、`tarch_opening_host_ambiguous`、`tarch_skin_gap_unattributed`、`tarch_cavity_multi_label`、`tarch_role_unmapped`、`tarch_zone_seed_near_boundary`、`tarch_zone_intent_split`、`tarch_edge_thickness_inconsistent`、`tarch_edge_far_side_ambiguous`、`tarch_profile_floor_footprint_unsupported`、`tarch_provenance_incomplete`、`tarch_nondeterministic_output`。

**核验方式**：Python AST 枚举生产模块 `_diag` 的字符串首参并与 `TARCH_DIAGNOSTIC_REGISTRY` 做集合差；结果 `registry=39 / emitted=22 / never_emitted=17`。

**位置**：

- `tests/test_tarch_converter_p0_schema.py:371-380`（只实例化 registry）
- `src/agent/judge/tarch_converter_schema.py:239-405`（静态码表）
- 代表性未接线规格：`src/agent/judge/tarch_converter_schema.py:279-283`、`:370-379`、`:395-403`

### MAJOR M-06 — P0 “契约冻结”被同版本加字段破坏，旧 P0 request hash 在当前模型下失效

**缺陷陈述**：P1/P2 分别向 `request_version=1` 增加 `wall_thickness_range_m` 和 `min_room_area_m2`，没有版本提升或迁移规则。默认值让旧 JSON 能加载，却会改变 canonical hash；由于 B-03 又不校验 hash，这个破坏被测试掩盖。

**具体失败场景**：按 edf1477 的字段集合计算一份 P0 风格 request hash，再用当前 v1 模型加载。模型自动插入 `[0.06,0.5]` 和 `2.0`，当前 `compute_request_sha256` 从 `49cb...` 变成 `5406...`，原 hash 不再成立。

**核验方式**：从当前最小 request 的 canonical payload 删除两个后加字段，按冻结算法计算旧 hash，再用当前模型 validate/re-hash；实测 `hash_still_valid=false`。`git show edf1477:...` 也确认 P0 schema 中没有这两个字段。

**位置**：

- `src/agent/judge/tarch_converter_schema.py:613-635`
- `src/agent/judge/tarch_converter_schema.py:667-669`
- `tests/test_tarch_converter_p0_schema.py:348-394`（只对当前模型往返，不覆盖跨提交 hash 兼容）

### MAJOR M-07 — 仍有写死的 mm/单层/方向假设，且“无烤死常量”测试只扫 schema 中三个变量名

**具体失败场景 A（单位）**：G4 用 `>1.0 native unit` 判缺口。native unit=`m` 时，真实 0.9 m 外皮开口被计为 0；`_march_thickness` 同样用外环距离 `<=1.0 native`，会把距外环 0.8 m 的内墙误判成外墙。P1 report 还固定除以 1000。

**具体失败场景 B（实体方向）**：同一个闭合矩形的四条墙线全部反转端点，G4 gap count 从 0 变成 4，因为过滤条件在 `min/max` 前使用原始 x0/x1、y0/y1。CAD LINE 方向本不应影响语义。

**具体失败场景 C（单层）**：manifest 无条件选 `request.floors[0]`，只写一个 floor 和一个 view；这与 P0 声称“从 v1 不烤死单层/逐层 footprint”不一致。

**核验方式**：分别以 native metre 构造 0.9 m opening、0.4 m 内墙；对同一矩形正向/反向 LINE 调 `_outer_skin_gap_count`；读 manifest 构造代码。

**位置**：

- `src/agent/judge/tarch_normalize.py:925-940`、`:1323-1329`（native-unit 常量）
- `src/agent/judge/tarch_normalize.py:1310-1315`（方向相关过滤）
- `src/agent/judge/tarch_normalize.py:784-795`（固定 `/1000.0`）
- `src/agent/judge/tarch_normalize.py:1574-1612`（`floors[0]` + 单 view）
- `tests/test_tarch_converter_p0_schema.py:315-334`（只扫 schema、只禁三个精确变量名，完全不扫算法体与数值常量）

### MAJOR M-08 — 强制接头/负例矩阵和失败 overlay 未交付，跟进债披露不完整

**缺陷陈述**：派单要求 L/丁字/十字/自由端/厚度变化五类“每类正例 + 负例”。实际只有 L/T/十字正例、自由端阻断负例；没有 L/T/十字负例、没有证明式 non-zoning 自由端正例、没有厚度变化正/负例。测试文件头却声称包含 thickness-change。失败路径也不产 `overlay_diagnostics`，只有成功且已有 zones 时才写 plan SVG。

**具体失败场景**：墙在中段变厚时，M-01 已证明实现会漏掉事件，但测试矩阵没有夹具可报警；若输入因自由端或接头歧义进入 BLOCK，用户又拿不到一张标出失败位置的诊断 overlay 来闭环人工核对。

**核验方式**：逐个枚举 P2 的 14 个 test 函数及 `_write_overlay_svg` 唯一调用点；在 BLOCK 分支确认 G9/G10 直接置红而没有诊断 overlay。对照 P2 交付 §8，只披露“厚度夹具未单造 / PNG 未做 / G10 无 fail 模式”，未披露其余矩阵缺口、失败 overlay、门级 false-lock、17 码未接线和未签字 G10。

**位置**：

- `tests/test_tarch_converter_p2_geometry.py:1-22`（头部声称有 thickness-change）
- `tests/test_tarch_converter_p2_geometry.py:198-276`、`:335-366`（实际矩阵）
- `src/agent/judge/tarch_normalize.py:1729-1765`（BLOCK 时不写任何诊断 overlay）
- `AI_agent/logs/reviews/execution/2026-07-22_tarch_converter_p2_glm.md:107-122`（披露清单）

### MINOR N-01 — staging 约束只禁止受保护 input，不保证 input/work_dir 真在 staging

**缺陷陈述**：`assert_staging_input` 的语义只是“不在 gt/gt_sources/case_data”；任意其他路径都通过。`run_p2_conversion` 对 `work_dir` 不做任何保护检查，直接 `mkdir` 和写 `normalized.dxf`。因此调用者可把输出目录指向受保护目录，绕过“转换器从不在受保护区内运行/写入”的架构承诺。

**具体失败场景**：给合法 staging DXF，但把 `work_dir` 指到 `case_tests/test_baseline/gt_sources/...`；入口不会拒绝，并会在该受保护树创建/覆盖转换产物。

**核验方式**：沿 `run_p2_conversion` 的写路径做只读控制流核对：只有输入路径调用 `assert_staging_input`，`work_dir.mkdir(...)` 前没有同类 guard。为避免污染权威资产，未实际执行受保护目录写入。

**位置**：`src/agent/judge/tarch_converter_schema.py:131-160`、`src/agent/judge/tarch_normalize.py:1691-1700`。

### MINOR N-02 — sm24 overlay 凹区标签落在区外，且不是规格所述原平面 PNG 底图

**缺陷陈述**：z5 是凹多边形，其 centroid 在区外；代码用 centroid 放 `r5`，实际覆盖到 z6。overlay 背景只画 WALL 灰线，不含原平面 PNG/完整 CAD 语义。它仍能看出八区铺砌和 L 走廊，但不足以据此宣称“人核通过”。

**核验方式**：将已晋升 SVG 机械渲染后目检；用 Shapely 验证 `z5.polygon.contains(z5.centroid) == false`，而 `representative_point` 在区内。

**位置**：`src/agent/judge/tarch_normalize.py:1638-1685`、`case_tests/test_baseline/gt_sources/sm24_anchor/overlay_plan.svg:145-150`。

## 3. 九个核验点逐条结论

| # | 核验点 | 结论 | 活体验证摘要 |
|---|---|---|---|
| 1 | G8 只依赖输出且够强 | **不成立** | 形式上函数只收 zones；实质依赖隐藏 offset，不读 basis/thickness。错误轴线与面积补偿两反例均让 G7/G8=0；neuter G8 后 35 测全绿。 |
| 2 | 四个 bug 真修根因 | **部分成立** | #1/#3/#4 在 sm24 上触及根因；#2 只修当前角点擦墙症状，变厚/范围反例仍错。 |
| 3 | 九门必红真绑 gate | **不成立** | G1/2/3/4/7/8/9 neuter 后无测试失败；G5 仅 free-end 两重复夹具；G6 唯一一对一。G10 无必红。 |
| 4 | 三道承重闸门齐且承重 | **不成立** | 近阈值仅 evidence；G8 可绕；G10 candidate 即 pass。补偿误差可通过 G6/G7/G8 且无诊断。 |
| 5 | fail-closed / 不猜 | **不成立** | hash mismatch 静默 PASS；门窗规则重叠固定猜 window；非法 polygon `buffer(0)`；PASS 不强制全门绿。 |
| 6 | 不烤死简化；两字段只作 sanity | **不成立** | wall range 上限控制 S7 pad 和输出；A_room 直接决定 cavity；S7 厚度无六类 proof；另有 1/50000/1、/1000、floors[0]。 |
| 7 | gt 隔离 | **成立** | `tests/test_gt_discipline.py` 11/11；独立 rg 检查 gate①、pipeline/execution/correction/reading 无 converter import、无 Tianzheng token 渗透。 |
| 8 | 退出门数字可复现 | **成立（仅 sm24 当前实现）** | 8 区、G7≈1.46e-13/overlap=0、G8≈8.27e-13、14=14、v3 PASS，独立 extract 得 1 floor/8 zones。注意 G8 数字只证明当前弱公式自洽。 |
| 9 | 跟进债披露完整 | **不成立** | 厚度夹具/PNG/G8 未抓 overlap 的披露属实；但遗漏门级 false-lock、G10 未签字、诊断 overlay、17 未接线码、全矩阵缺口、hash gate 与范围驱动。 |

## 4. 四个施工期 bug 的独立复核

| bug | 独立结论 | 核验结果 |
|---|---|---|
| #1 `source_handles` 写层名 | **已修到已观察根因** | 晋升 report 的 72 个 zone-edge source refs 全都存在于原 source.dxf、全在 WALL 层；其源线到输出边的距离与记录 offset 最大差 0.0336 mm（小于 1 mm node tol）。normalized 的 34 个新增实体与 source_map 34 entries 一一对应。仍缺 thickness proof，见 M-02。 |
| #2 march pad=2 导致 8000 mm | **仅症状修复** | sm24 overlap 确为 0；但 pad 来自合法上限且影响输出，事件点错位/漏检反例成立，未触及精确事件根因。 |
| #3 footprint 共线 jamb 顶点 | **已修到根因** | normalized footprint 恰 1 条闭合 LWPOLYLINE、4 顶点、面积 200,000,000 native²；G9 无 `dxf_short_edge`。 |
| #4 manifest 双缩放 | **已修到根因（sm24/一般线性 affine 语义正确）** | manifest 线性部为 identity、`metres_per_unit=0.001`；独立跑真实 v3 preflight PASS，extract 为 1 floor/8 zones。单层写死另见 M-07。 |

## 5. 已验证确实正确的部分

1. **测试基线可复现**：
   - 转换器三文件：`51 passed in 16.52s`。
   - 全仓：`1508 passed, 9 xfailed, 146 warnings in 481.61s`；9 个 xfail 与既有 baseline 一致。
   - gt 隔离：`11 passed`。
2. **sm24 当前样本的 P1/P2 数字可复现**：21 openings（11 window/10 door）、14 exterior/7 interior、51 faces、dangles/cuts/invalid=0、面积约 200 m²、8 cavities/8 zones、G7 overlap=0。
3. **S3 门块开启扇排除在当前图上正确**：AC3 解出的法向厚度为 240 mm，不采用 780 mm swing bbox。
4. **S9 产物内部 hash 正确**：manifest hash 和 source_map hash 均可用当前 schema 重算一致；report 的 converter hash与当前 `tarch_normalize.py` 字节 hash 一致。
5. **原始句柄保留**：source modelspace 的 384 个句柄在 normalized 中 384/384 全保留，另新增 34 个实体；34 个新增实体全部有 source_map entry，无 phantom/unmapped generated handle。
6. **当前 sm24 的数值墙厚**：report zone edges 只出现 0.12/0.24 m，与 SURVEY 的内/外墙事实相符；但证据链未绑定，不能据此推导泛化正确。
7. **gt 隔离边界保持**：三提交没有让 converter 被 gate①、执行器、reading/correction import，也没有修改 golden、gt.json 或 v3 提取器本体。

## 6. 返工出口（缺一不可）

1. **重写 G8**：从可持久化的 zone edge `p1/p2 + basis + thickness` 独立重算 offset/法向并重建实体墙带；不得读取正向 `offset_native`。增加同墙两侧 basis/thickness/轴线一致性检查。B-01 两个反例必须红在 G8 或更早的专门 gate。
2. **让三承重件真正承重**：近阈值面必须有明确人工裁决/ack；G10 未签字时不得 pass/晋升；`ConversionReportV1(status=PASS)` 必须验证所有要求 gates 都 `passed=true`。报告内 overlay 路径改为 bundle-relative、hash-bound。
3. **接 source/request hash gate**：入口在读几何前核实际 source SHA、request self-hash、plan_view/floor 归属；不符发稳定 BLOCK 码并不写几何。
4. **按事件坐标实现 S7**：移除 1/50000/1 native-unit 常量和 range-derived sampling pad；对 WallRegion 事件投影精确分段，所有测厚必须对账六类离散 evidence，超 range 只作 fail sanity。厚度 proof 写入 report/source_map。
5. **补真 gate mutation tests**：逐门删/放宽 gate 后，恰有对应必红夹具失败；测试必须从触发输入重新跑 gate，不得手算 helper 代替。G5 面积证人需独立于 `unary_union(faces)`。
6. **完成强制矩阵**：L/T/十字/自由端/厚度变化每类正负例；至少含“同边两次变化”“合法上限变化不改变已测几何”“LINE 端点反转不变”“native units m/mm 同变”。
7. **恢复 fail-closed**：dialect 规则重叠、非法外扩 polygon、空 provenance、远端/厚度歧义均须 BLOCK + 最小冲突集；不得 `buffer(0)` 猜修。把未接线码接实或从已上线 registry 移除。
8. **修契约版本与复杂度接缝**：对 P0 后增字段提升/迁移 request 版本并加跨版本 hash 测试；移除 `/1000` 和 `floors[0]` 单位/单层假设，或在当前 profile 明确前置 BLOCK 而不是静默只取首层。
9. **补失败人核件**：BLOCK 路径生成 `overlay_diagnostics`；凹区标签用 `representative_point`；完成一次可追溯的真实人工签字再声称 G10 通过。

在以上返工完成前，sm24 的当前全绿只能证明该单一样本被当前正反同源公式接受，不能作为答案生成器具备 fail-closed 泛化能力的证据。
