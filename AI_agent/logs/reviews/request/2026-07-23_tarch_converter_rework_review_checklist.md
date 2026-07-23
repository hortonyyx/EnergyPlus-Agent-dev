# 天正 DXF → GT v3 转换器返工：GLM 结构化核验清单

**日期**：2026-07-23  
**清单作者**：sol（只定义核验命题与红线，不作本轮裁决）  
**执行与裁决方**：GLM  
**被核验施工方**：terra  
**核验对象**：`src/agent/judge/tarch_normalize.py`、`src/agent/judge/tarch_converter_schema.py`、`tests/test_tarch_converter_p{0,1,2}_*.py`、sm24 转换产物及相关隔离守卫  
**权威顺序**：本任务 brief ＞ sol 2026-07-22 裁决书 ＞ terra 返工派工单；施工简报和施工方测试只算待验陈述

---

## 0. 执行纪律与回填格式

### C-00 独立证据纪律

- **验什么**：GLM 的反例期望必须独立于 terra 的测试夹具和硬编码期望。
- **怎么验**：
  1. 从仓库根目录执行全部命令：`cd /workspaces/EnergyPlus-Agent-dev`。
  2. 记录 `git rev-parse HEAD`、`git status --short`、Python/GEOS/Shapely/ezdxf/pytest 版本。
  3. 将 GLM 自建探针放在新的临时目录或新文件（建议 `/tmp/glm_tarch_rework_probe/`）；探针只可导入生产 API、schema 和通用库，不得导入 `tests/test_tarch_converter_*.py` 中 terra 的 helper/fixture。
  4. **场景 A、场景 B、G8 篡改、同墙丁字/十字配对、九门 neuter、hash 篡改、厚度无证据、S7 变厚几何必须由 GLM 按本清单坐标重新建模**；不得复制 terra 夹具对象、expected 数组、golden WKB 或先读取 terra 期望再反推断言。
  5. 对每项回填：实际命令、退出码、关键原始字段/数值、`成立/不成立/阻塞`。不得仅写“测试通过”。
- **成立**：GLM 探针中没有导入 terra 测试模块，关键坐标和期望来自本清单或 GLM 的独立手算；每项都有原始值和布尔结果。
- **不成立**：复用 terra fixture/helper/golden/expected，或只引用 terra 测试绿而没有独立活体探针；该项证据一律无效。

### C-01 核验环境与变更范围

- **验什么**：核验的是 terra 声明的同一提交，且返工没有借机修改禁区。
- **怎么验**：
  1. 从 terra 施工简报取得返工基线提交 `<BASE>` 与施工提交 `<HEAD>`。
  2. 执行：

     ```bash
     git rev-parse <BASE> <HEAD>
     git diff --stat <BASE>..<HEAD>
     git diff --name-only <BASE>..<HEAD>
     git status --short
     ```

  3. 单独检查 gate①、执行器、reading/correction、golden、`gt.json`、v3 提取器本体是否被改动。
- **成立**：实际 `HEAD` 与送审提交一致；禁区变更文件数为 `0`；工作树中的非施工改动被单列且未混入证据。
- **不成立**：提交不一致，或任一禁区文件被改动而无主控明确授权。

---

## 1. G8 真独立与同墙一致性门

### G8-01 逆向重建只消费持久化输出字段

- **验什么**：G8 必须仅由每条输出边的 `p1/p2 + basis + thickness` 重算法向和 offset，不得读取 S7 正向阶段保存的 `nx/ny/offset_native` 或等价派生缓存。
- **怎么验**：
  1. 静态读 `g8_reconstruct_wall_region` 及其调用链，列出读取的每个 edge 字段和调用的 helper。
  2. GLM 独立构造一个 6 m × 4 m 外框、四周 240 mm 外墙的单房，以及一个由 240 mm 内墙分开的双房；先以生产 gate assembly 跑到 G8 绿。
  3. 深拷贝输出边，保持 `p1/p2/basis/thickness` 不变，把 `nx`、`ny`、`offset_native` 删除、置 `None/NaN`，或替换为“一经读取即抛 `AssertionError`”的 trap 对象，再重新调用**生产 G8 与生产 gate assembly**。
  4. 比较挖空前后重建几何的 canonical WKB、面积和 G8 residual。
- **成立**：挖空/设 trap 后不触发读取异常；重建 WKB 相同，面积差 `≤ 1e-12 m²`，G8 residual 差 `≤ 1e-12 m²`，G8 仍 `passed=true`。
- **不成立**：G8 因缺少 `nx/ny/offset_native` 无法运行、读取 trap、结果变化超红线，或代码仍从这些字段/正向 helper 取得法向或 offset。
- **独立性要求**：几何必须由 GLM 按上述尺寸自建，不用 terra 的 G8 fixture 或 WKB。

### G8-02 `basis` 活体变异必须令 G8 变红

- **验什么**：改变 `basis`、保持 `p1/p2/thickness/offset_native` 完全不变时，G8 必须重新计算出不同墙带并变红。
- **怎么验**：
  1. 使用 G8-01 的独立双房绿色结果。
  2. 找一条 240 mm 内墙边，将 `basis="wall_axis"` 改为 `"outer_skin"`；显式断言变异前后 `offset_native` 字节/值相同。
  3. 重新跑生产 G8 gate；不得只手算 `symmetric_difference`。
- **成立**：绿色副本 G8 为 `true`；变异副本 G8 为 `false`，且 `symmetric_diff_m2 > 配置的 topo_area_m2`；其他未变输入字段逐字段相等。
- **不成立**：G8 仍绿、只出现测试侧手算失败而生产 gate 未红，或测试同时修改了 `offset_native`。
- **独立性要求**：不得复用 terra 的“flipped basis”测试或其期望。

### G8-03 `thickness` 活体变异必须令 G8 变红

- **验什么**：改变 `thickness`、保持 `p1/p2/basis/offset_native` 完全不变时，G8 必须变红。
- **怎么验**：在 G8-01 的独立双房中，把一条 240 mm `wall_axis` 边厚度改为 360 mm；保持该边 `offset_native` 原值不变；重新跑生产 G8 gate。
- **成立**：基线 G8 `true`；变异后 G8 `false` 且 residual `> topo_area_m2`。
- **不成立**：变异后仍绿，或测试同步重算/修改了 `offset_native`。
- **独立性要求**：不得复用 terra fixture/expected。

### SW-01 场景 A 必须由同墙一致性门抓红

- **验什么**：错误共享轴线与同墙两侧冲突厚度不得被 G7/G8 的面积自洽掩盖。
- **怎么验**：
  1. GLM 用 Shapely 独立建立矩形 footprint；真实内墙两腔体面分别为 `x=3880`、`x=4120`，真实墙轴为 `x=4000`。
  2. 故意令两个输出 zone 在 `x=4060` 相接：左侧边记录 `basis=wall_axis, thickness=360, offset=180`；右侧边记录 `basis=wall_axis, thickness=120, offset=60`。
  3. 真跑生产 G7、G8 和同墙一致性门，读取 gate id、`passed`、诊断码、冲突边 id/坐标和重叠子区间。
- **成立**：同墙一致性门 `passed=false`；发稳定 BLOCK（应为 `tarch_edge_thickness_inconsistent` 或返工契约中明确的等价码）；冲突证据同时列出 360、120 和相同物理墙配对。即使 G7/G8 数值为 0，也不得得到 PASS 或晋升 bundle。
- **不成立**：全门绿、只给 INFO/WARN、依赖 G8 偶然红但没有同墙冲突证据，或仍生成 PASS/晋升 bundle。
- **独立性要求**：必须照上述坐标重建，不得调用 terra 场景 A helper。

### SW-02 合法同墙不得误红

- **验什么**：两侧厚度/basis 一致的合法共享墙必须通过同墙一致性门。
- **怎么验**：独立建立同样 footprint，真实面 `x=3880/4120`，输出共享轴 `x=4000`；两侧均记录 `basis=wall_axis, thickness=240, offset=120`；真跑生产门。
- **成立**：同墙一致性门 `passed=true`；配对数恰为 `1`；没有 `tarch_edge_thickness_inconsistent`；G7 overlap 和 symmetric difference 均 `≤ topo_area_m2`。
- **不成立**：合法墙变红、没有形成配对、形成多余配对，或出现冲突诊断。
- **独立性要求**：GLM 自建。

### SW-03 basis 不一致必须红

- **验什么**：同一物理墙两侧 `basis` 不同必须阻断，即使厚度数值相同。
- **怎么验**：从 SW-02 深拷贝，只把一侧 `basis` 改为 `outer_skin`，保持 `p1/p2/thickness/offset_native` 不变；真跑同墙门。
- **成立**：同墙门 `false`，有可定位 BLOCK，报告非 PASS。
- **不成立**：同墙门仍绿或只改 evidence 不改 gate。
- **独立性要求**：不得使用 terra 变异夹具。

### SW-04 丁字接头的部分重叠配对

- **验什么**：同墙配对必须按重叠子区间拆分，不能假设整边一对一。
- **怎么验**：
  1. GLM 建立一条正向边 `E0: (5000,0)→(5000,10000)`；反向一侧因丁字支墙在 `y=4000` 分为 `E1: (5000,4000)→(5000,0)` 与 `E2: (5000,10000)→(5000,4000)`，并加入在 `y=4000` 接入的正交墙几何。
  2. 三段先都用 `wall_axis/240`，真跑配对门；再仅把 E2 厚度改为 120。
  3. 读取门 evidence 中实际配对区间。
- **成立**：绿色副本形成且仅形成 `[0,4000]`、`[4000,10000]` 两个重叠配对子区间并通过；变异副本只在 `[4000,10000]` 报冲突并令门红。
- **不成立**：E0 只与一条边配对、漏掉任一子区间、合法副本误红、或 E2 变异未红。
- **独立性要求**：坐标与 zone 边由 GLM 自建，不复用 terra 的 T fixture。

### SW-05 十字接头的部分重叠配对

- **验什么**：十字节点处被正交墙占据的中段不能导致两侧共线墙漏配、串配或误报。
- **怎么验**：
  1. 建立 `E0: (5000,0)→(5000,10000)`；对侧共线段为 `E1: (5000,4000)→(5000,0)`、`E2: (5000,10000)→(5000,6000)`；`y∈[4000,6000]` 为 2 m 宽正交交叉墙节点，并补齐正交边。
  2. 基线全部 `wall_axis/240`；再仅改 E2 为 360。
  3. 真跑配对门并读取区间证据。
- **成立**：基线只形成 `[0,4000]` 和 `[6000,10000]` 两个共线反向配对，不跨越中心节点、不误红；变异后仅第二段冲突并阻断。
- **不成立**：整边一对一、跨中心节点配对、漏配、合法基线红或变异未红。
- **独立性要求**：GLM 自建，不复用 terra cross fixture。

---

## 2. 近阈值承重、人核 G10 与 PASS 全门

### HR-01 场景 B 面积补偿不得静默 PASS

- **验什么**：面积阈值造成“小房间被吞成墙材、腔体数量仍恰好正确”的补偿错误必须进入人工确认，不得静默晋升。
- **怎么验**：
  1. GLM 独立建 10 m × 1 m 连续条带，沿 x 切成 A=`1.5 m²`、B=`2.5 m²`、C=`6.0 m²`；声明 `min_room_area_m2=2.0`、`expected_count=2`，语义真值为 A/C 两房、B 为墙材。
  2. 真跑 S5→S10，不提供近阈值 ack。
  3. 读取 near-threshold 列表（面积、坐标、face id）、相关 gate、G10、顶层 status 和晋升目录。
- **成立**：A 与 B 都在待核列表中且面积分别为 `1.5±1e-9`、`2.5±1e-9 m²`；未 ack 时至少一个承重门 `passed=false`，G10 不得为已签字状态，报告 `status != "PASS"`，晋升 bundle 不存在。
- **不成立**：因 cavity count=2、G7/G8 residual=0 而 PASS；near-threshold 只作 evidence 但不承重；待核项缺面积或可定位坐标。
- **独立性要求**：不得复用 terra 场景 B 夹具或 expected。

### HR-02 `candidate` 绝不等于 G10 通过

- **验什么**：`verification_status=="candidate"` 时 G10 必须红且不得晋升。
- **怎么验**：在任一几何机器门全绿的独立小例中只生成 overlay、不提供人工 ack；读取 G10、报告和 bundle/promote 状态。
- **成立**：G10 `passed=false`；evidence 明示 `candidate/pending`；报告非 PASS；无晋升 bundle。
- **不成立**：overlay 文件存在即令 G10 `true`，或报告/晋升仍 PASS。

### HR-03 真人 ack 必须可追溯且 hash-bound

- **验什么**：只有绑定本次 source/request/overlay 的有效真人签字才能令 G10 绿。
- **怎么验**：
  1. 检查 ack 契约至少含 reviewer 身份、签字时间、决策、`source_dxf_sha256`、`request_sha256`、`overlay_sha256`（或等强绑定）。
  2. 对同一绿色结果分别测试：无 ack、合法 ack、source hash 改 1 bit、request hash 改 1 bit、overlay 文件改 1 byte。
- **成立**：仅合法 ack 使 G10 `true`；其余四种均 G10 `false`、非 PASS、不晋升；失败 evidence 明确指出哪一 hash 不符。
- **不成立**：纯字符串“approved”可通过、ack 未绑三类 hash、任一篡改仍绿。

### HR-04 任一门红则 PASS 构造与生产晋升都失败

- **验什么**：`ConversionReport(status="PASS")` 与生产晋升都要求 G1–G10 全部 `passed=true`。
- **怎么验**：
  1. 从合法全门绿报告深拷贝，逐次把 G1…G10 中恰一门改为 `passed=false`，直接调用 Pydantic/model validator。
  2. 再在独立进程中对生产 gate assembly 逐次强制一门为 false，跑完整转换与晋升路径。
- **成立**：10/10 个模型构造都抛稳定 validation error；10/10 个生产运行都 `status != PASS` 且晋升 bundle 不存在。
- **不成立**：任一红门仍可构造 PASS，或生产报告虽非 PASS 仍被晋升。
- **独立性要求**：不得只运行 terra 的 PASS validator 单测；GLM 自行构造 10 份变异报告。

### HR-05 overlay 路径必须 bundle-relative 且 hash-bound

- **验什么**：报告中的 overlay 引用必须可迁移、不能指向绝对 staging 路径，并能检出文件篡改。
- **怎么验**：生成一份候选或已签字 bundle；读取报告 overlay 字段；将整个 bundle 复制到另一绝对目录后解析；再改 overlay 1 byte 验 hash。
- **成立**：路径为相对路径、不含原 workspace/staging 前缀；复制后仍能在 bundle 内解析；原文件 hash 相等，篡改后 G10/验证器变红。
- **不成立**：绝对路径、`..` 逃逸 bundle、复制后失效、或篡改不报警。

---

## 3. source/request/归属 hash gate

### H-01 source SHA 全零篡改

- **验什么**：请求声明的 source SHA 与实际 DXF 不符时，必须在读几何前 BLOCK，且不写几何。
- **怎么验**：
  1. GLM 把 sm24 source 复制到新临时 staging。
  2. 仅把 `source_dxf_sha256` 改成 64 个 `0`，再按契约重新计算合法 `request_sha256`。
  3. 真跑生产最高层转换入口；列出诊断、门、报告状态及 work dir 全部文件。
- **成立**：发 `tarch_input_source_hash_mismatch` 且 severity=BLOCK；报告非 PASS；不存在 `normalized.dxf`、manifest、source_map、zone 几何文件或晋升 bundle；hash 检查发生在 `ezdxf.readfile`/S1 几何处理前。
- **不成立**：继续跑几何、全门绿、PASS、只在报告中并列两个 hash 而不对账，或留下任一几何产物。
- **独立性要求**：GLM 自己复制 source、改值、重算 request hash，不用 terra hash fixture。

### H-02 request self-hash 篡改

- **验什么**：source SHA 正确但 `request_sha256` 错误时必须 fail-closed。
- **怎么验**：用真实 source SHA，把合法 request 的 self-hash 改 1 个十六进制位；真跑最高层入口并检查与 H-01 相同字段。
- **成立**：稳定 BLOCK；非 PASS；不读/写几何；无晋升。
- **不成立**：请求仍被执行或仅在报告中回显错误 self-hash。
- **独立性要求**：GLM 自建变异。

### H-03 plan_view/floor 归属篡改

- **验什么**：选定 plan view 不属于声明 floor/request，或 view/floor id 不可唯一解析时必须前置 BLOCK。
- **怎么验**：分别构造 view 指向不存在 floor、一个 view 被两个 floor 声明、入口参数 view 与 request 中同 id 内容不同三种请求；self-hash 均重算正确。
- **成立**：3/3 均稳定 BLOCK、非 PASS、不写几何；诊断给出冲突 floor/view id。
- **不成立**：默取首个 floor/view、继续转换或无可定位冲突集。

---

## 4. S7 事件坐标与厚度证据

### S7-01 单次变厚事件精确定位

- **验什么**：S7 必须按 WallRegion 事件坐标精确分段，不能采样猜变化点。
- **怎么验**：
  1. GLM 建 10,000 mm 长的水平墙边；`x∈[0,220]` 厚 300 mm，`x∈[220,10000]` 厚 100 mm；提供独立合法 cap/proof。
  2. 真调生产 S7/`_thickness_profile` 和完整相关 gate，记录有序 profile。
- **成立**：恰有 2 段；唯一断点满足 `|x-220| ≤ tau_node_native`；厚度分别满足 `|t-300| ≤ tau_node_native`、`|t-100| ≤ tau_node_native`；无 477.5 mm 等偏移断点。
- **不成立**：漏段、多段、断点超容差、整边报 100，或输出依赖步长。
- **独立性要求**：不得复用 terra thickness-change fixture/expected。

### S7-02 同边两次变化不得漏检

- **验什么**：中段 `100→300→100` 的两次变化必须全部检出，即使两端厚度相同。
- **怎么验**：GLM 建 10,000 mm 墙；`[0,4000]=100`、`[4000,6000]=300`、`[6000,10000]=100`；提供合法 proof；真跑生产 profile/gate。
- **成立**：恰有 3 段，断点在 `4000±tau_node_native`、`6000±tau_node_native`，厚度序列严格为 `[100,300,100]`（各自误差 `≤tau_node_native`）。
- **不成立**：因两端探针相同而输出单段、漏任一事件或断点漂移超容差。
- **独立性要求**：GLM 自建。

### S7-03 合法厚度上限只能作 sanity

- **验什么**：在真实厚度均合法时，只改 `wall_thickness_range_m` 上限不得改变任何测得几何/profile。
- **怎么验**：对 S7-01、S7-02 分别用 `[0.06,0.35]` 与 `[0.06,0.50]` 跑两次；canonicalize profile 和 zone polygon 后比较。
- **成立**：两组断点、厚度、basis、zone polygon、G7/G8 数值逐项相同，世界坐标差 `≤1e-12 m`、面积差 `≤1e-12 m²`；仅合法性配置回显可不同。
- **不成立**：段数、断点、厚度、basis 或几何随合法上限变化。
- **独立性要求**：不得用 terra 的 range-invariance 期望。

### S7-04 native m/mm 同变

- **验什么**：同一物理几何用 native mm 与 native m 表达时，世界坐标、事件和 gate 结果必须相同。
- **怎么验**：把 S7-02 的所有 native 坐标/厚度除以 1000，分别设 `metres_per_unit=0.001` 与 `1.0`；两次均真跑生产链并转到 world metres 比较。
- **成立**：profile 事件/厚度、zone 顶点、G4/G7/G8 evidence 的世界量差分别 `≤1e-12 m`/`≤1e-12 m²`，所有 gate 布尔相同。
- **不成立**：出现 1000 倍差、分类变化、门结果变化或 native literal 驱动差异。
- **独立性要求**：GLM 自建双单位几何。

### TE-01 每条输出厚度必须绑定六类证据之一

- **验什么**：每一条带厚度的 zone edge 都必须绑定契约允许的六类离散证据，不能只由 WallRegion 射线/面积反推后自证。
- **怎么验**：
  1. 读取 schema 中 `ThicknessEvidence` 枚举和生产 evidence resolver，建立规范六类映射：窗块短边、墙端 cap、`PUB_DIM` 显式标注、`PUB_HATCH` 外墙局部证据、另段精确复现、人审 override。
  2. GLM 为每类各建一个最小正例（共 6 个），真跑 thickness resolver→S7→report/source_map。
  3. 每个正例再删掉该唯一 proof，形成 6 个负例。
- **成立**：6/6 正例的数值与 proof 一致，edge evidence `proof_ids` 非空且可解析到真实 handle/签字记录；6/6 删除 proof 后均 BLOCK，不输出该未经证明厚度。
- **不成立**：任一类无法走生产分支、proof id 悬空、证据值与厚度不一致，或删 proof 后仍静默出厚度。
- **独立性要求**：六组最小几何和证据均由 GLM 新建，不复用 terra proof fixture。

### TE-02 `wall_lines=[]` / 全证据空必须 fail-closed

- **验什么**：没有任何厚度证据时不得生成一组数值厚度并让 G8 自证。
- **怎么验**：GLM 建外框 6000×4000 mm、四周墙环 240 mm 的单房；向生产 S7 传 `wall_lines=[]`，并将 cap/dimension/hatch/reproduction/override 六类 evidence 集合全部置空；真跑至报告。
- **成立**：发 `tarch_wall_thickness_unevidenced` 和/或 `tarch_provenance_incomplete` 的 BLOCK；未经证明的四条 240 mm edge 不得进入 PASS report；G8 不得绿；无晋升。
- **不成立**：仍输出四条 240 mm 边、诊断为空、Pydantic 裸异常代替稳定诊断、或 G8/PASS 仍绿。
- **独立性要求**：不得复用 terra 单房 fixture。

### TE-03 report/source_map proof 闭环

- **验什么**：report edge、wall ribbon、source_map 之间的厚度 proof 必须非空、可解析、一致且 hash-bound。
- **怎么验**：对独立正例和 sm24 枚举所有带厚度边；对每个 `proof_id` 查唯一 proof 对象、source handle/人审 ack；再把一个 proof id 改成不存在值并重验 schema/bundle。
- **成立**：带厚度边的空 `proof_ids` 数为 `0`；悬空/多义 proof 数为 `0`；edge 厚度与 proof 值差 `≤tau_node`；篡改后验证失败且非 PASS。
- **不成立**：任一空 proof、悬空 proof、值不一致或篡改不报警。

---

## 5. G1–G10 逐门 neuter（“九门”沿用原任务称谓）

### MUT-00 变异执行法

- **验什么**：每个编号门都必须有一个从触发输入真跑生产 gate assembly 的一对一必红夹具。
- **怎么验**：
  1. GLM 自建下列 G1–G10 十个 canonical 负例；每个先在未变异进程确认**目标门红**。
  2. 每次只 neuter 一个门：在新的 Python 进程中让该目标门的最终 `passed` 强制为 `true`，或删除该门唯一拦截；不得改诊断生成、其他门或测试断言。
  3. 每次运行十个 canonical 必红测试，记录 pytest node id 差集。建议命令形态：

     ```bash
     python -m pytest -q /tmp/glm_tarch_rework_probe/test_gate_mutations.py
     GLM_NEUTER_GATE=G1 python -m pytest -q /tmp/glm_tarch_rework_probe/test_gate_mutations.py
     # 依次 G2 ... G10；每次必须是全新进程
     ```

- **成立**：未变异为 `10 passed`；neuter Gk 后恰有且仅有 `test_gk_must_red` 失败，失败数严格为 `1`；其余 9 个 canonical 测试结果不变。
- **不成立**：neuter 后全绿（false-lock）、失败集合含其他门、测试只断言 helper/诊断而未读取生产 gate，或测试通过同步篡改 offset 等方式制造红。
- **独立性要求**：十个负例均由 GLM 自建；terra 的 mutation tests 只能在 GLM 探针之后作为补充证据。

### MUT-G1 输入预检门

- **验什么**：G1 必须绑定输入预检失败。
- **怎么验**：独立最小 DXF 中放一个生产契约禁止的 proxy/unsupported entity，其他输入合法；真跑入口并断言 G1。
- **成立**：未 neuter 时仅目标预检条件令 G1 `false`；neuter G1 后 canonical G1 测试失败。
- **不成立**：只检查诊断码、不检查 G1，或 neuter 后测试仍绿。

### MUT-G2 量化守恒门

- **验什么**：G2 必须绑定真实量化冲突。
- **怎么验**：从运行时容差取得 `tau_q/tau_node`，独立造一组会被节点合并但不能守恒回放的墙端点/短 cap，真跑 S1/S2 和 G2；记录冲突点。
- **成立**：有 `tarch_quantization_conflict`，G2 `false`；neuter G2 后只失败 canonical G2 测试。
- **不成立**：手工把 `g2_ok=false` 代替触发几何，或 neuter 后无测试失败。

### MUT-G3 opening 双证据门

- **验什么**：G3 必须绑定 opening 无解/多解/类型歧义。
- **怎么验**：独立建一个 INSERT，使其同时满足 window 与 door dialect 规则，且配好最小墙几何；真跑 opening resolver 和 G3。
- **成立**：G3 `false`，发 `tarch_opening_kind_ambiguous` BLOCK；neuter G3 后只失败 canonical G3 测试。
- **不成立**：固定猜 window/door，或测试未读 G3。

### MUT-G4 外皮开口守恒门

- **验什么**：G4 必须绑定“外皮 gap 数 ≠ exterior opening 数”。
- **怎么验**：独立矩形 footprint 的一边由两条 LINE 覆盖，留下 `[4000,4100]` 共 100 mm 的唯一 gap，声明 exterior opening 数为 0；真跑完整 G4 assembly。
- **成立**：evidence 为 `outer_skin_gaps=1`、`exterior_openings=0`，G4 `false`；neuter 后只失败 canonical G4 测试。
- **不成立**：只直接调用 `_outer_skin_gap_count` 而未重跑 G4，或 neuter 后测试仍绿。

### MUT-G5 拓扑闭合与面积守恒门

- **验什么**：G5 必须绑定真实拓扑残差，且面积子门有独立于 `unary_union(faces)` 的外包证人。
- **怎么验**：
  1. canonical 变异用合法闭环外另加一根 1 m dangling stub，真跑 polygonize/G5。
  2. 另由原始闭合 footprint ring 手算/解析面积 `A_external`，与 faces 面积和比较；不得用 `unary_union(faces).area` 同源作 footprint witness。
- **成立**：stub 例 `dangles>0` 且 G5 `false`；neuter G5 后只失败 canonical G5 测试；面积负例中 `|sum_faces-A_external|>topo_area_m2` 时 G5 必红。
- **不成立**：只构造不可能的内部 dict、面积 witness 仍来自 faces union，或 neuter 后 false-lock。

### MUT-G6 腔体声明与数量门

- **验什么**：G6 必须绑定 cavity 数/claim 数与人工声明不一致。
- **怎么验**：独立建两个合法 cavity，只声明 `expected_count=1` 和一个 intent entry；真跑 S5/S6/G6。
- **成立**：evidence `cavity_count=2, expected_count=1`，G6 `false`；neuter 后只失败 canonical G6 测试。
- **不成立**：只修改 gate 对象而未从几何跑 cavity，或 neuter 后测试仍绿。

### MUT-G7 无缝铺砌门

- **验什么**：G7 必须同时绑定 footprint 对称差和 pairwise overlap。
- **怎么验**：独立用两个 zone 覆盖矩形 footprint，再将左 zone 向右扩 100 mm，令 union 仍覆盖 footprint但产生正面积 overlap；真跑 G7。
- **成立**：`pairwise_overlap_m2 > topo_area_m2`、G7 `false`；neuter 后只失败 canonical G7 测试。另删去 100 mm 条带时 symmetric difference 子门也必须红。
- **不成立**：只在测试侧手算 overlap、生产 G7 未重跑，或任一子门未绑定。

### MUT-G8 独立重建门

- **验什么**：G8 必须绑定 `basis/thickness` 变异。
- **怎么验**：使用 G8-02 的独立几何，保持 `offset_native` 不变，只翻一条 basis；真跑 G8。
- **成立**：未 neuter G8 红；neuter 后只失败 canonical G8 测试。
- **不成立**：同步改 offset、只手算 residual，或 neuter 后测试仍绿。

### MUT-G9 v3 preflight 门

- **验什么**：G9 必须绑定真实 v3 preflight 拒绝。
- **怎么验**：独立生成可过 preflight 的最小 bundle，再把 manifest footprint handle 改为不存在的 `DEADBE`，调用生产 v3 preflight 与完整 G9。
- **成立**：preflight `ok=false` 且有稳定 code，G9 `false`；neuter 后只失败 canonical G9 测试。
- **不成立**：只测 helper 返回值而未装配 G9，或 G9 false 不阻断 PASS。

### MUT-G10 真人签字门

- **验什么**：G10 必须有真正 fail 模式并绑定有效 ack。
- **怎么验**：独立绿色 bundle 仅生成 overlay、不提供 ack；真跑 G10。
- **成立**：G10 `false`；neuter 后只失败 canonical G10 测试。
- **不成立**：文件存在即绿、声称 G10 无 fail 模式，或 neuter 后无对应失败。

---

## 6. 强制几何矩阵与 fail-closed

### MX-01 L/丁字/十字/自由端/厚度变化矩阵完整

- **验什么**：五类几何每类至少一正一负，且测试声称与实际函数一致。
- **怎么验**：用 AST/pytest collection 列出对应 10 个以上 test node id；逐个读 fixture 并真跑：
  - L：合法外角；非法自交/冲突外角。
  - 丁字：合法部分重叠配对；一段厚度或 basis 冲突。
  - 十字：合法分段配对；一段厚度或 basis 冲突。
  - 自由端：有 proof 的 non-zoning 端点正例；无 proof dangling stub 负例。
  - 厚度变化：S7-01 正例；无证据/远端多解负例。
- **成立**：五类 `5/5` 均有正负例，合计至少 10 个；每个负例真跑生产 gate 且产生预期 BLOCK；文件头没有虚假声称。
- **不成立**：任一类缺正或负、只测 helper、或头部声称存在但 collection 中没有。
- **独立性要求**：GLM 至少独立复现 SW-04、SW-05、S7-01，不把 terra 矩阵本身当唯一证据。

### FC-01 dialect 重叠不得猜

- **验什么**：同一 block 同时匹配 window/door 时必须 BLOCK，不得按固定优先级返回 window。
- **怎么验**：规则设 `window_block_names=["X_DOOR"]`、`door_block_prefixes=["X_"]`，对 `X_DOOR` 真跑生产 classifier/resolver。
- **成立**：发 `tarch_opening_kind_ambiguous` BLOCK；候选集合恰含 window、door；无 opening 被静默归类。
- **不成立**：返回 window/door 单值、只给 INFO、或继续 PASS。

### FC-02 非法 polygon 不得 `buffer(0)` 猜修

- **验什么**：S7 外扩或 G8 反缩产生自交/非法 polygon 时必须阻断并给最小冲突集。
- **怎么验**：
  1. 独立构造 bow-tie/凹角过度 offset 使结果 `is_valid=false`。
  2. 真跑 S7、G8；搜索相关调用链：

     ```bash
     rg -n 'buffer\\(0(?:\\.0)?\\)' src/agent/judge/tarch_normalize.py
     ```

- **成立**：S7/G8 均不以 `buffer(0)` 修形继续；发 BLOCK，列出造成冲突的边 id/handle/坐标；不写几何。
- **不成立**：修成 Polygon/MultiPolygon 后继续、无诊断、冲突集为空，或相关分支仍调用 `buffer(0)`。
- **独立性要求**：GLM 自建非法几何。

### FC-03 opening 多解必须带最小 cap 冲突集

- **验什么**：opening 多解诊断不能只报 `candidate_count`。
- **怎么验**：独立建一个 opening INSERT 与两组等价 jamb/cap 候选；真跑 resolver，读取 diagnostic `solutions`。
- **成立**：BLOCK；`solutions` 恰列两组候选且每组 cap handle 非空，集合等于实际两组候选；没有任意择一。
- **不成立**：只有数量、缺 handle、列出无关实体或继续转换。

### FC-04 空 provenance、远端/厚度歧义均 fail-closed

- **验什么**：空 provenance、far-side 多解、厚度证据互相冲突必须各自走稳定 BLOCK。
- **怎么验**：分别建三例：有数值边但无 source/proof；一条近侧边对应两个等距远侧面；两个合法 proof 给 120/240 mm 冲突值。真跑生产链。
- **成立**：三例分别发 `tarch_provenance_incomplete`、`tarch_edge_far_side_ambiguous`、`tarch_edge_thickness_inconsistent`（或 registry 中明确等价稳定码），均非 PASS、不写/不晋升几何，并带最小冲突集。
- **不成立**：任选一远端/厚度、裸异常、INFO、或仍 PASS。

---

## 7. 诊断 registry 与契约版本

### D-01 registry 与生产 `_diag` 发射点集合相等

- **验什么**：原 17 个未接线码必须接实或从上线 registry 移除，不能继续只测“可实例化”。
- **怎么验**：
  1. 用 Python AST 枚举 `tarch_normalize.py` 及实际生产 converter 模块所有 `_diag(...)` 的字符串首参。
  2. 与 `TARCH_DIAGNOSTIC_REGISTRY.keys()` 和 `DiagCode` Literal 做集合差，打印三个集合及数量。
  3. 特别逐项记录原 17 码：
     `tarch_input_source_hash_mismatch`、`tarch_wall_thickness_unevidenced`、
     `tarch_wall_entity_unaccounted`、`tarch_opening_fill_conflict`、
     `tarch_opening_gap_unexplained`、`tarch_opening_evidence_unbound`、
     `tarch_opening_host_ambiguous`、`tarch_skin_gap_unattributed`、
     `tarch_cavity_multi_label`、`tarch_role_unmapped`、
     `tarch_zone_seed_near_boundary`、`tarch_zone_intent_split`、
     `tarch_edge_thickness_inconsistent`、`tarch_edge_far_side_ambiguous`、
     `tarch_profile_floor_footprint_unsupported`、`tarch_provenance_incomplete`、
     `tarch_nondeterministic_output`。
- **成立**：`registry - literal = []`、`literal - registry = []`、`registry - emitted_literal = []`；原 17 码每项要么同时不在 registry/Literal，要么有生产发射点。
- **不成立**：任一集合差非空、动态/死代码占位冒充可达发射点、或码只存在测试。

### D-02 留在 registry 的码必须有活体触发

- **验什么**：AST 有调用点还不够；原 17 码中仍保留者必须真实可达。
- **怎么验**：要求提供并执行 `code → pytest node id → 触发输入 → 实际 diagnostic` 映射；GLM 抽查全部原 17 码（不是抽样）。被移除者确认 registry/Literal/生产引用均消失。
- **成立**：保留码 `100%` 有生产路径活体负例，实际 code/severity/stage 与 registry 完全一致；移除码无悬挂引用。
- **不成立**：只实例化 `ConversionDiagnosticV1`、monkeypatch 直接调用 `_diag`、不可达分支或 severity/stage 不符。

### V-01 P0 后增字段必须提升 request 版本

- **验什么**：`wall_thickness_range_m`、`min_room_area_m2` 等 P0 后加字段不能继续冒充冻结的 request v1。
- **怎么验**：
  1. 执行 `git show edf1477:src/agent/judge/tarch_converter_schema.py` 取得 P0 v1 字段集。
  2. 与当前各 request version 模型字段做集合差。
  3. 检查显式 migrator/version dispatch。
- **成立**：旧字段集仍由 v1 精确定义；新增字段只在提升后的版本（应 `>=2`）出现；有显式、确定性的 v1→新版本迁移。
- **不成立**：当前仍只有 `request_version: Literal[1]` 却加入新字段，或靠默认值暗迁移。

### V-02 跨版本 hash 兼容

- **验什么**：历史 v1 request 的 canonical hash 在当前代码中仍可验证，新版本迁移后也有独立有效 self-hash。
- **怎么验**：
  1. 用 `edf1477` 字段集独立造 v1 payload 并按旧 canonical 算法求 `h1`。
  2. 当前代码先以 v1 canonicalizer 验 `h1`，再显式迁移为 v2+ 并求 `h2`；重复迁移两次。
  3. 改一个新增字段，确认只改变新版本 hash。
- **成立**：旧 hash 验证 `true`；迁移确定性 `h2_run1 == h2_run2`；`h1` 不因当前默认值改变；改新字段后 `h2` 必变而 `h1` 历史验证仍成立。
- **不成立**：加载旧 JSON 自动插字段导致 h1 失效、无 migrator、或跨版本共享同一错误 canonical payload。
- **独立性要求**：GLM 自己从 P0 commit 提取字段，不复用 terra 的旧 hash 常量。

---

## 8. 去写死、方向/多层与安全写入

### HC-01 禁止 native-unit 算法常量驱动输出

- **验什么**：原 `1/50000/1` native 常量和 range-derived pad 必须离开几何决策；单位/合法上限只承担换算或 sanity。
- **怎么验**：
  1. 静态检查 `_march_thickness`、`_thickness_profile`、G4、outer-skin 分类及调用链，列出所有数值 literal 的单位和用途。
  2. 跑 S7-03、S7-04。
  3. 另以 native metre 建 0.4 m 内墙，其远端距 footprint 外环 0.8 m，真跑 basis 分类。
- **成立**：没有以 `1 native unit`、`50000 native units` 或合法厚度上限作 march/pad/外墙距离判据；0.4 m 内墙被判 `wall_axis` 而非 `outer_skin`；S7-03/04 成立。
- **不成立**：算法体仍出现等价硬编码并影响行为，或 metre 例误判。

### HC-02 `/1000` 必须由 `metres_per_unit` 取代

- **验什么**：report/manifest/overlay/proof 的单位换算不得假定 native=mm。
- **怎么验**：搜索生产模块中 `/1000`、`*0.001`；逐处证明是固定 schema 单位而非 native 换算；结合 S7-04 比较全部产物。
- **成立**：native 换算路径统一使用 affine/`metres_per_unit`；m/mm 双表达产物世界坐标和厚度满足 S7-04 红线。
- **不成立**：任何 native 值固定除 1000，或行为测试出现 1000 倍差。

### HC-03 LINE 端点反转不变

- **验什么**：CAD LINE 端点顺序不得改变 gap、墙带、门或最终几何。
- **怎么验**：GLM 建一个有恰 1 个外皮 gap 的闭合矩形 DXF，跑一次；再把全部 LINE `(start,end)` 对调，其他字节语义保持一致，重跑完整 P1/P2。
- **成立**：两次 gap count 都严格为 `1`；opening/face/cavity/zone 数相同；G1–G10 布尔相同；世界几何对称差 `≤topo_area_m2`。
- **不成立**：原向/反向出现如 0→4 的差异，或任一门改变。
- **独立性要求**：不得用 terra reversal fixture。

### HC-04 多层不得静默 `floors[0]`

- **验什么**：多层请求必须完整逐层处理，或在当前 profile 明确前置 BLOCK；不得只输出首层。
- **怎么验**：独立建含 F1/F2 两层、各一个 plan view 的请求，两层 source 几何故意不同；真跑最高层入口。
- **成立**：二选一且只能二选一：  
  A. 输出严格 2 floors/2 views，id/几何分别对应 F1/F2；  
  B. 在任何几何写入前发 `tarch_profile_floor_footprint_unsupported` BLOCK，输出 0 个晋升 floor/view。  
- **不成立**：只输出 F1、默取首 view、混层，或无稳定诊断。
- **独立性要求**：GLM 自建两层请求。

### SAFE-01 `work_dir` 必须受 staging guard

- **验什么**：合法 staging input 不能搭配受保护 answer root 的 `work_dir` 进行写入。
- **怎么验**：
  1. 静态追踪 `run_p2_conversion` 在首次 `mkdir/write` 前的 guard。
  2. 测试时 monkeypatch 首个写函数为记录器，传入解析后位于 `case_tests/test_baseline/gt_sources/` 下的虚拟 work_dir；禁止真的污染该目录。
- **成立**：在任何 `mkdir/write` 调用前抛稳定保护错误；写调用计数严格为 `0`。
- **不成立**：先 mkdir/写再报错，或完全不拒绝。

---

## 9. 失败人核件

### OV-01 BLOCK 路径必须生成可定位诊断 overlay

- **验什么**：几何阶段 BLOCK 时必须有 `overlay_diagnostics`，并标出实际失败位置。
- **怎么验**：用独立 dangling stub 或 opening 多解触发 BLOCK；读取 overlay 引用和 hash；解析 SVG/等价产物中诊断 marker 坐标。
- **成立**：失败 overlay 存在、bundle-relative、hash 正确；至少一个 marker 与 diagnostic point 距离 `≤tau_node`；图中包含对应 code/实体 handle；报告仍非 PASS。
- **不成立**：BLOCK 时没有 overlay、只有成功 plan overlay、marker 不在诊断位置或路径为绝对 staging。

### OV-02 凹区标签必须位于自身 polygon 内

- **验什么**：凹多边形标签不得使用可能落在区外的普通 centroid。
- **怎么验**：独立建 L 形 zone，生成 overlay；解析标签坐标为 Shapely Point，检查 `polygon.covers(point)`；同时确认与 `representative_point()` 的生产策略一致。
- **成立**：所有 zone 标签 `covers=true`；L 形例标签不落入邻区。
- **不成立**：任一标签在自身 polygon 外或覆盖相邻 zone。
- **独立性要求**：GLM 自建 L 形，不以 sm24 肉眼截图为唯一证据。

---

## 10. gt 隔离

### ISO-01 隔离守卫与反向依赖扫描

- **验什么**：converter 只能调用既有 v3 preflight，不得被 gate①、执行器、reading/correction 或 v3 提取器反向 import，也不得渗入 Tianzheng 特例。
- **怎么验**：

  ```bash
  python -m pytest -q tests/test_gt_discipline.py
  rg -n '(^|\\s)(from|import)\\s+.*tarch_(normalize|converter_schema)|Tianzheng|天正' \
    src/agent/pipeline.py src/agent/execution src/agent/correction \
    src/agent/judge/reading_score.py src/agent/judge/correction_score.py \
    src/agent/judge/gt_extraction.py src/agent/nodes/validate.py
  ```

  再用 Python AST 建 import graph，确认允许方向是 converter→v3 preflight，禁止方向是上述模块→converter。
- **成立**：`test_gt_discipline.py` 严格 `11 passed`；禁止反向 import 数为 `0`；gt 通用模块中的 Tianzheng/天正特例数为 `0`。
- **不成立**：测试少于 11、任一失败、发现反向 import/条件分支/魔法 token，或为让 converter 通过而修改通用 gt 语义。

---

## 11. sm24 真端到端与全仓回归

### E2E-01 sm24 独立数值重算

- **验什么**：sm24 仍得到 8 区、无缝铺砌、独立墙带重建和 v3 preflight 通过，但这些数值必须来自返工后的真门。
- **怎么验**：
  1. 将 `case_tests/test_baseline/gt_sources/sm24_anchor/source.dxf` 复制到新 staging；从实际字节独立计算 source SHA；使用有效 request 和本次有效真人 ack。
  2. 跑最高层转换入口。
  3. GLM 不信 report 自报值：从生成的 zone polygon 独立用 Shapely 重算 `union(zones) △ footprint`、全部 pairwise overlap；从持久化 `p1/p2+basis+thickness` 独立重建墙带；调用真实 `inspect_extraction_inputs`/`extract_plan_geometry` 或 `extract_gt_v3`。
  4. 补跑：

     ```bash
     python -m pytest -q tests/test_tarch_converter_p2_geometry.py -k sm24
     ```

- **成立**：
  - zone 数严格 `8`；
  - 独立重算 symmetric difference `≤1e-9 m²`，pairwise overlap 严格 `0.0 m²`（或 GEOS 数值噪声 `≤1e-12 m²`）；
  - G8 独立 residual `≤topo_area_m2`；
  - G1–G10 十门全部 `passed=true`，G10 ack hash 全部匹配；
  - report `status="PASS"`，v3 preflight `ok=true`，独立 extraction 为 `1 floor / 8 zones`；
  - source_map 所有带厚度 edge 的 `proof_ids` 非空。
- **不成立**：只引用 report 数值/terra 测试，区数非 8，任一面积超红线、任一门红/缺失、G10 仍 candidate、v3 拒绝或 proof 为空。
- **独立性要求**：面积与重建必须由 GLM 新脚本读取产物重算，不复用 terra expected。

### E2E-02 sm24 产物 provenance 与确定性

- **验什么**：返工不得破坏原句柄、产物 hash 或确定性。
- **怎么验**：同一 source/request/ack 在两个不同临时绝对目录各跑一次；canonicalize 排除合法相对路径差后比较 report/manifest/source_map/normalized 几何；核原 source handles 与新增 handles。
- **成立**：两次 gate/evidence/zone/proof/hash 相同；原 source modelspace handles 保留率 `100%`；每个新增 generated handle 恰有 1 个 source_map entry；phantom/unmapped 数均 `0`。
- **不成立**：同输入输出漂移、原句柄丢失、生成实体无 map、hash 与实际字节不符。

### REG-01 转换器定向测试与全仓测试

- **验什么**：返工测试、全仓和既有 xfail 基线无回归。
- **怎么验**：

  ```bash
  python -m pytest -q \
    tests/test_tarch_converter_p0_schema.py \
    tests/test_tarch_converter_p1_geometry.py \
    tests/test_tarch_converter_p2_geometry.py \
    tests/test_gt_discipline.py
  python -m pytest -q
  ```

  保存完整 stdout、退出码和 pytest summary；与返工前 `1508 passed, 9 xfailed` 对照。
- **成立**：两条命令退出码均 `0`；定向测试 0 fail/0 error；全仓 passed 数不得少于 1508（新增测试应使数量增加）；xfail 仅为既有已登记项，数量不得新增，既有 9 项若减少必须因真实修复并给 node id。
- **不成立**：任一 fail/error、新增或无说明 xfail、passed 数异常减少，或通过 deselect/跳过隐藏失败。

---

## 12. GLM 裁决前的机械完备性检查

### END-01 下限项不得漏项

- **验什么**：GLM verdict 必须逐项覆盖本清单，而不是只给总体测试结果。
- **怎么验**：在 verdict 中建立 `命题 id → 命令/探针 → 实测值 → 成立/不成立/阻塞` 表；机械检查以下 id 至少各出现一次：

  `G8-01..03`、`SW-01..05`、`HR-01..05`、`H-01..03`、`S7-01..04`、
  `TE-01..03`、`MUT-G1..G10`、`MX-01`、`FC-01..04`、`D-01..02`、
  `V-01..02`、`HC-01..04`、`SAFE-01`、`OV-01..02`、`ISO-01`、
  `E2E-01..02`、`REG-01`。
- **成立**：上述 id 覆盖率严格 `100%`；每项都有原始实测字段和明确布尔判定。
- **不成立**：任一 id 缺失、只写“见 terra 测试”、使用“看起来合理/大致/应该”等无红线措辞，或把未执行项默认为通过。

> 本文件只定义 GLM 应执行的命题与判据；最终通过、返工或阻断结论由 GLM 在其 verdict 中依据实测结果作出。
