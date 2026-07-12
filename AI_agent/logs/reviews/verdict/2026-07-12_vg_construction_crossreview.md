# C2 Vg 施工交叉审判词（sol 次高档，2026-07-12）

**结论：REWORK —— 1 HIGH + 3 MAJOR + 2 MINOR。**

审查基准：commit `20da78a`；权威稿：`AI_agent/proposals/c2_vg_detail_spec.md` v2。本判词只根据细稿、当前 diff、源码与自跑测试；执行简报仅用于定位。

## Findings

- **VG-CR1（HIGH，writer 未 fail closed）** —— `src/agent/correction/feature_state.py:49-56` 只检查 segment 列表非空且 floor-id 集合覆盖，没有按权威 ring 重算并比对 wire；`src/agent/execution/stage_runner.py:175-181` 在 writer 边界也只重派生 claims。失败场景已独立复现：对真 finalize 结果用 `model_copy` 把首段 `depth` 改为 `99.0`，再以该 geom 重派生 claims 构造 `FinalizeResult`，writer 仍记录 `accepted=True, stage_version="3"`。这直接违反 §9.2“列表与重算不一致必须 INVARIANT”，会让被篡改的 populated facade wire 进入 accepted artifact。

- **VG-CR2（MAJOR，stage-version 中央策略被绕过，需回稿升审）** —— `src/agent/execution/stage_runner.py:201-213` 仅对 schema v3 调 `correction_stage_version(expected)`，v1 保留本地字面量 `"2"`。这与 §9.2/§11 的“所有 correction release 由单一显式 map 派生、StageRunner 不散落版本字面量、未知 helper 组合 fail closed”正面冲突。失败场景：legacy claims 日后多出任何 helper 时，该分支仍静默写 `"2"`，无法触发 release-map 的未知组合 INVARIANT。执行者指出的稿内矛盾成立：现有 map 对 `helper_versions=()` / `facade_segments="not_declared"` 没有定义，字面无条件调用会破坏 legacy。但这应回稿补中央策略，不应在 writer 现场收窄。建议稿件明确登记 `(): "2"` 并同步修订 version-2 状态校验（仅加 map 条目仍会被现有 `declared_unpopulated` 检查拒绝），或把 key 扩为能区分 legacy/B2 的集中策略。

- **VG-CR3（MAJOR，§12.2#21 穷举 oracle 未实现）** —— `tests/test_c2_vg_visibility.py:829-864` 的 `_enumerate_small_rectilinear_rings` 实际是固定种子随机尝试后只取 12 个 ring，函数 docstring 也明言“not exhaustive”；`tests/test_c2_vg_visibility.py:906-909` 还对所有 Vg invariant 直接 skip。失败场景：未被 12 个样本命中的稀有顶点排列、边界原子或拒绝门回归可以通过整组 property 测试。这不是“限顶点数穷举”的等价实现，必须改为受限闭世枚举并对每个合法 ring 审计计数/去重。

- **VG-CR4（MAJOR，§12/§13 关键验收证据不足）** —— `tests/test_c2_vg_visibility.py:258-265` 用被测 Vg 自身生成 L/U/Z/T 基础 expected，没有实现 §12.2#2 要求的“基础实例手写 expected intervals”；`tests/test_c2_b2_v3.py:315-327` 所谓双路 parity 只比较 finalize 内存中的 geom JSON/claims，没有产生两组 promoted artifacts，因而未验证 §13 要求的 feature sidecar hash parity。同类缺口还包括：§12.2#3 未对每个编码比较 materialized `model_dump_json()`/ids/最终排序；#13 未实际打乱 directions/candidates；#14 没有 spy 锁定 snapshot compare 仅在 materialize 前发生一次；#16 没有覆盖 001 accepted → 002 blocked 的 append-only/下游仍绑 001；#20 plan test 仅检查一个 dict 不含字段，未证明 visibility 不被调用。这些使“§12 全测试族通过”与“双路 parity”无法验收。

- **VG-CR5（MINOR，配置默认取舍偏离稿意）** —— `src/agent/correction/config.py:60-61` 给两个新 `CoreTolerances` 字段加了 `1e-9` dataclass 默认，且 `tests/test_deterministic_core.py` 显式锁定省略时默认。YAML loader 确实是必填索引，故生产 shipped-config 路径不会降级；但任何直接构造 `CoreTolerances` 的调用者仍可在不知道新硬门的情况下静默取默认，与 §10.1/§11“不加默认降级”的收紧意图不符。若因现有越界 test helper 无法改为必填，应回稿扩文件授权或明文豁免，不应由执行者将豁免写成新合同。

- **VG-CR6（MINOR，§11 范围/简报完整性）** —— `AI_agent/guides/codex_execution_protocol.md:36` 相对 `20da78a` 有一处与 Vg 无关的流程政策修改，不在 §11 文件表，也未出现在执行简报改动清单。失败场景：若将当前工作树整体当作 Vg 批交付，会夹带未审权的流程规则变更。合并前必须将其归属到独立批次或从 Vg diff 中排除。

## 四项执行者判断裁决

1. **`stage_runner.py` 的 schema-v3 收窄：不接受，回稿升审。** 执行者对“无条件照稿会使 v1 新抛异常”的诊断正确，但现场收窄破坏了单一 release-map owner 与未知 helper fail-closed。方向上应把 legacy `()` 组合纳入集中策略，但仅补 `(): "2"` 不够：还必须修订 `"2"` 对 `facade_segments` 的状态校验，或扩充 map key 以区分 legacy 与历史 B2。这是稿件合同修订，不是可记档接受的实现偏离。
2. **“单段被遮成两 visible islands”拓扑论证：接受，未找到反例，不因此要求算法 REWORK。** 对固定观察方向，若一条更浅的同向 boundary edge 的投影严格内嵌于深 edge，它连回同一外环的边界路径必然继续暴露更浅的同向下包络，把遮挡投影连到该深 edge 的至少一个端点；因此不能在同一物理 edge 上留下左右两个分离可见分量。独立辅助验证穷举了 4×4 cell lattice 上 4,111 个无洞单 Polygon，四方向均无两岛反例。执行者的“双端遮挡 + `_merge_adjacent_atoms` 真 gap”是合理的机制替代覆盖；但 §12.2#5 仍有不可实现的字面验收项，应回稿删改后留档。
3. **legacy `helper_versions=()`：接受保持，不回填 `floor_footprint_v1`。** §9.2 明言 legacy 全部 `not_declared`；v1 也不声明 per-floor-footprint helper。应修的是集中 stage-version 策略对这个合法空 tuple 的定义，不是为迁就 map 伪造 helper claim。
4. **property oracle 用固定种子采样 12 环：不接受，必须按受限闭世穷举返工。** 固定种子只保证可重复，不保证穷举性或覆盖完备性，与 §12.2#21 的原文不等价。

## §13 验收清单对账

- **PASS** —— `src/agent/correction/schema.py` 相对 `20da78a` 零 diff，`FacadeSegment` wire 未改。
- **FAIL** —— §11 文件范围不干净；见 VG-CR6。
- **PASS（实现） / PARTIAL（测试哨兵）** —— Vg 模块 imports 仅 stdlib + facade/footprint/schema，人工 `rg` 未见 gt/judge/manifest/LLM/reading/I-O/config-loader 依赖；纯函数重复调用、禁 `open` 与输入不 mutation 测试通过。但 test 的 env 哨兵只删除一个 env key，未封锁所有 env 读取；源码检查补足了本次审查信心。
- **PASS** —— 未见 golden/gt/case-data 改动；新 Vg 测试文件无这些数据路径读取。
- **PASS** —— 执行简报已对 rectangle 四方向、Z partial、FULL_OCCLUDE、same-depth、half-open touch 五组结果逐值列出；对应精确断言在自跑聚焦组中通过。
- **FAIL** —— integrated/stepwise 仅做内存 finalize 结果 parity，未做 promoted artifact bytes 及 feature-sidecar hash parity；见 VG-CR4。
- **PASS** —— §9.1 v2 冻结顺序符合：`src/agent/correction/finalize.py:53-74` 为入口快照 → core → 立即快照复核 → materialize → wire 重算验证，materialize 后未再用入口空段快照比较。
- **PASS** —— shipped YAML 与 A0 的两名称、`1e-9` 值、半开/tie 语义一致；但 programmatic dataclass default 保留为 VG-CR5。
- **FAIL** —— §12 全测试族未按稿完整落地，且 writer 存在可复现的 wire-mismatch 接受缺口；见 VG-CR1/3/4。

## 自跑与独立探针

- 聚焦 pytest：`tests/test_c2_vg_visibility.py + tests/test_c2_b2_v3.py + tests/test_deterministic_core.py` → **161 passed, 1 warning in 3.36s**。
- writer 篡改负例：**1/1 被错误接受**（`depth=99.0`，`accepted=True`，`stage_version="3"`）。
- 两 visible islands 独立格点探针：4×4 cell lattice 上 **4,111** 个连通、无洞、单 Polygon × 4 directions，**0** 个单段两岛反例。

本轮未跑全量 suite，按委托由主控独立完成。

---

## r2 返工复验（2026-07-12）

**结论：APPROVE-WITH-CHANGES —— CR1/CR2/CR3/CR5/CR6 已闭合，CR4 部分闭合；剩 1 MINOR 测试证据缺口，无新产品代码 finding。**

本轮以升审后的 `AI_agent/proposals/c2_vg_detail_spec.md` v3 为权威稿，仅信当前代码、diff 与自跑输出。

### r1 六条 findings closure

1. **VG-CR1（CLOSED）—— writer 已 fail closed。** `src/agent/execution/stage_runner.py:184-208` 在 claims 重派生/核对后、audit 与 feature sidecar 写出前，对所有 v3 `FinalizeResult` 从 shipped config 构造显式 `VisibilityTolerances`，并调用 `validate_materialized_facade_segments` 从权威 floor ring 重算逐项比对。原样重放 r1 攻击：真 finalize → 首段 `model_copy(depth=99.0)` → 对篡改 geom 重派生 claims → 新 `FinalizeResult` → `StageRunner.record()`；实际抛 `FacadeVisibilityInvariantError: visibility_wire_mismatch`，manifest accepted pointer 仍为 `None`，`feature_states.json` 未写出。`tests/test_c2_b2_v3.py:447-477` 已将该攻击锁为负例。

2. **VG-CR2（CLOSED）—— correction release 已收口到完整状态中央表。** `src/agent/correction/feature_state.py:82-118` 的 `ReleaseKey` 覆盖 schema、canonical helpers 及四个 feature state，显式登记 legacy v1 / 历史 B2 v3 / Vg v3 三行；未登记组合统一 INVARIANT。`src/agent/execution/stage_runner.py:222-237` 对每个 accepted `FinalizeResult` 无条件调 `correction_stage_version(expected)`，无 schema 收窄、无 correction `"2"/"3"` 赋值字面量。legacy `helper_versions=()` 与四项 `not_declared` 保持真实，不再伪填 helper。

3. **VG-CR3（CLOSED）—— property oracle 已从采样改为受限闭世穷举。** `tests/test_c2_vg_visibility.py:1036-1158` 遍历 3×3 unit-cell 格的全部 `2^9-1=511` 个非空子集，独立做 4-连通、边抵消、单环追踪、简单多边形复核与去重，当前实产 213 个合法 ring；`tests/test_c2_vg_visibility.py:1194-1226` 对 213 ring × 4 directions 直接调 Vg，无 invariant catch/skip。本轮额外计数：2,188 个 atom sample 全部有 ray hit 且全部找到 Vg winner，`oracle_hit != None and winner is None` 的宽松备用分支实际命中 **0** 次。

4. **VG-CR4（PARTIAL）—— 主要证据缺口已补，但 §12.2#3/#13 仍有一处字面残余。** 已亲核通过：`HAND_EXPECTED` 是 L/U/Z/T × 4 directions 的手写结果表，等变 expected 不再由被测 Vg 自产；双路分别经 `StageRunner.record()` 落盘，比较 `output.json`/`feature_states.json` 字节及两个 manifest hash；快照 spy 精确得到 `snapshot,snapshot,materialize`；001 accepted → 002 blocked 保留 accepted pointer 与 001 hash；plan seam 将四个 Vg 入口 monkeypatch 为“调用即失败”并成功跑完。

   **残余 VG-CR4-R2（MINOR）**：`tests/test_c2_vg_visibility.py:413-434` 的 materialized dump/id/order 编码不变性只参数化 `Z/U`，未按 §12.2#3 的“每实例”将 L/T/FULL_OCCLUDE 也锁到 dump 层。`tests/test_c2_vg_visibility.py:801-836` 确实遍历了四 family 的 24 种访问顺序，但它在测试中手工 `recombined.sort(...)` 后与 materializer 比较，没有让生产 materializer 真正接收被打乱的 direction/candidate 结果；同时 `_canonicalize_ring` 会把 cyclic-start/CW 编码先归一化，所以“全编码遍历已打乱内部 candidate discovery order”的注释不成立。失败场景：materializer 若日后误依赖 Vg 返回顺序，现有“打乱”测试仍可绿。闭合方式：将 dump 层编码测试扩到全 fixture，并在 materializer 调用路径上 monkeypatch family 访问顺序及每方向 Vg 返回 tuple 顺序，直接断言最终 strict-wire bytes 不变。

5. **VG-CR5（CLOSED）—— 两 epsilon 默认已删除。** `src/agent/correction/config.py:59-67` 的两字段为无默认必填字段，且放在既有默认字段之前；`tests/test_c2_b1_cell_polygon.py`、`tests/test_kernel_guards.py`、`tests/test_deterministic_core.py` 三个越界 helper 均显式传入两值。新负例锁定省略任一字段即 `TypeError`，YAML loader 仍为必填 key 读取。

6. **VG-CR6（CLOSED）—— guide 改动已与 Vg 工作树分离。** `AI_agent/guides/codex_execution_protocol.md` 当前无 uncommitted diff；该政策改动已由主控以独立 commit `20509e6` 归属，本轮 Sonnet 返工未触碰 `AI_agent/guides/`。

### 三条 review-ask 裁决

1. **3×3 / 213 合法环规模：接受，对 §12.2#21 充分。** 细稿要求是“小整数格 + 限顶点数控时”，没有冻结 4×4 为最低尺寸；3×3 cell 子集域是有限、闭世、无采样的完整枚举，并与手写 L/U/Z/T、全遮挡、编码/旋转/镜像组合覆盖互补。r1 判词的 4×4 / 4,111 是为裁决“两 visible islands”做的额外独立探针，不是 property oracle 的强制最低门。若未来扩大到 4×4，属覆盖加固而非本批 blocker。

2. **release map 三行：覆盖全部现役生产组合，接受。** 当前 `correction_target()` 仅有 `rectangular → schema 1` 与 `orthogonal_polygon → schema 3`；前者派生 legacy 全 `not_declared`，后者现行 finalize 必经 Vg，派生 `floor_footprint_v1 + facade_visibility_v1`/facade populated。中间 B2 v3 行为历史已发布血统保留。未来 typed-north-axis 或其他 helper 上线前必须新登记，当前 fail-closed 正是预期行为，不属缺行。

3. **writer 重复重算代价：可接受，保留信任边界复核。** 对 Z 类 8 顶点 footprint 的本地微基准：1 floor/8 segments 平均 **0.332 ms**，10 floors/80 segments **3.526 ms**，50 floors/400 segments **16.494 ms**，近似线性；这相对 correction 整体执行与 artifact I/O 可忽略。该重算是为防止 finalize 后、writer 前的嵌套对象篡改，不应为避免这一次线性计算而删除。

### r2 自跑计数

- 聚焦五文件：`test_c2_vg_visibility.py + test_c2_b2_v3.py + test_deterministic_core.py + test_c2_b1_cell_polygon.py + test_kernel_guards.py` → **209 passed, 1 warning in 5.70s**。
- r1 `depth=99` 攻击原样独立重放：**1/1 rejected**，错误码 `visibility_wire_mismatch`，accepted pointer 为空，sidecar 未写。
- 闭世 oracle 独立计数：**511** 子集全访问，**213** 合法 ring，**2,188** atom samples，**0** 个 hit-without-winner。
- 本轮未跑全量 suite，按委托由主控独立完成。
