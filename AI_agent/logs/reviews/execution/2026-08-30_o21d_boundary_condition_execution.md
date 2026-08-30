# 收工报告 · ②-1d：edge `boundary_condition` 字段化与独立对账门

- **日期**：2026-08-30 · **施工席位**：GPT
- **派工单**：[2026-08-30_o21d_boundary_condition_dispatch.md](../request/2026-08-30_o21d_boundary_condition_dispatch.md)
- **开工分支 / HEAD**：`08.23_AsDrawnReading` / `54e3633a4f9f3e381359a8200dfc8593966b3c2a`
- **结论**：R1–R5 已落地。真实 sm25 对账 **100/100 配对，0 条不一致，0 个结构失败**；单边突变会只点名该边并使门转红。未触发派工单 §五停下上报条件。

---

## 〇、开工承重前提复核

开工先完整读取派工单及其指定上下文，再按 §一逐项独立复核：

1. `grep -n "basis: EdgeBasis"` 找到的实际锚点是
   `src/agent/judge/tarch_normalize.py:1804-1806`；F-121 登记中的旧行号没有被采用。
2. §一.3 四行对照逐行成立：
   - 转换器出射点是 `mid + normal × thickness_native`；②-1c 编译器是越过最远面 1 unit。
   - 转换器对 footprint exterior 做带 `node_join_native` 容差的距离判定；编译器用 footprint/wall-region 的零容差 `covers` 判定。
   - 转换器值域是 `outer_skin / wall_axis`；编译器值域是四档 boundary condition。
   - 只有编译器继续检查唯一相邻 cavity，并保留 `unclaimed_void`。
3. 两个 profile 的改前实测均为：已投影 edge `100`，其中
   `exterior=32 / interzone=68 / unclaimed_void=0 / unknown=0`，无 edge ring `4`。
4. 开工 `.pth` 路径、sha256、内容以及分支/HEAD 均与用户给出的读数相同；开工工作树干净。

承重前提全部成立，故继续施工。

## 一、实现结果

### R1 / R5：投影前的一等事实与独立重算

`src/agent/judge/as_measured.py` 新增：

- `AsMeasuredBoundaryEdgeV1`：保存逻辑 edge 身份、cavity、顺序、轴、未投影端点、墙/face-line 血缘以及四档 `boundary_condition`。
- `BoundaryConditionEvidenceV1`：保存 raw/opposite face、厚度、outward normal、exit point、footprint ring/edge、相邻 cavity，以及 cavity-side/far-side face-line handles。
- `derive_boundary_edges()`：在事实生产阶段、选择任何输出 profile 之前独立判定并落库；不读取转换器 `basis`。
- `refresh_boundary_edges()`：已签 face-line translation 后，`as_signed` 重新测量 face 常量、exit witness 与分类，避免复制过期的 `as_measured` 证据。

`AsMeasuredViewV1.boundary_edges` 采用空列表缺省，以保持旧事实文档可读。编译器现在优先读取该字段，但原 `_classify_boundary` 重算路径保留；两者同时存在时逐边核对，分歧抛出 `BoundaryConditionMismatchError`，并带具体 facts edge ID。

真实 sm25 的 `as_measured` 与 `as_signed` 都落有 100 条投影前记录，分布均为 32/68/0/0；事实记录中没有 converter `basis`。合成已签 translation 中，两条相关 edge 的 raw/opposite face 证据由 `49400/50600` 刷新为 `49402/50602`，分类仍为 `interzone`。

### R2：转换器 `basis` × facts `boundary_condition` 对账门

`src/agent/judge/answer_compiler.py` 新增 `reconcile_boundary_basis(as_signed, conversion_report)`。它返回完整审计对象，不会为了“变绿”改写任一列；调用方可先读取所有行与结构失败，再用 `audit.assert_consistent()` 响亮关门。

配对不读取 `boundary_condition`，只使用几何与血缘：

1. 对每个 ring 穷举 `forward/reverse × 全部 cyclic rotations`，即 n 边 ring 共 `2n` 个假设。
2. 几何列独立按 endpoint residual 选最优解。
3. 血缘列独立按 source-handle overlap、再以 residual 解平手。
4. 两列必须选择同一排列；选中解必须低于 5,000 units 硬上限；每个替代解必须严格更差。
5. 配对完成后才比较语义映射：`exterior ↔ outer_skin`、`interzone ↔ wall_axis`；另外两档没有被擅自折叠到 converter 二值域。

真实 sm25 逐边读数：

| facts `boundary_condition` | converter `basis` | 边数 |
|---|---|---:|
| `exterior` | `outer_skin` | 32 |
| `interzone` | `wall_axis` | 68 |
| 其它组合 | — | 0 |

```text
paired_edges        = 100
mismatch_count      = 0
mismatch_edge_ids   = []
structural_failures = []
pairing_proofs      = 25
```

25 个 ring 的几何解与血缘解全部逐位相同，所有替代方向均严格更差。跨全部 ring：

```text
最差的选中 max endpoint residual = 3394.1125496954282 units = 0.339411 m
最近的替代 max endpoint residual = 19547.889911701466 units = 1.954789 m
```

将第一条 exterior facts edge 人为改成 interzone 后，配对仍是 100、结构失败仍是 0，但门只列出：

```text
boundary-edge:5bde04aed676a863
```

`BoundaryBasisMismatchError` 与编译器内部的 `BoundaryConditionMismatchError` 都只点名这一条，证明门有牙且失败半径没有扩散。

### R3：选择 ②，给两档可论证的合成供货

本单明确选择 **② 造可论证的合成供货**，没有改写真实 sm25 的零存货读数，也不把 monkeypatch 当作“量到”：

- `unclaimed_void`：墙面向一个低于 `min_room_area_m2`、因此未进入 room-cavity population 的小型管井/设备空腔；exit 位于 footprint 内、墙体外、且不属于任何已认领 cavity。
- `unknown`：轴对齐房间墙面向斜切/倒角 footprint；exit 已离开 footprint，但射线找不到可作 witness 的轴对齐 footprint edge。

测试直接调用 facts 侧真实分类谓词并将结果装入生产同款 `AsMeasuredBoundaryEdgeV1`，分别量得 `unclaimed_void` 与 `unknown`。因此 schema 四档均有谓词级供货，但真实 sm25 仍只行使其中两档。

### R4 / F-150：用语义反事实替换词法 scrub 锁

已删除旧的 `test_compiler_does_not_read_any_stored_basis_shaped_value`。删除理由：真实三件套没有键名含 `basis` 的载体，该锁只 scrub 自己注入的 blob，证明不了“任意名字的判断载体均不被消费”。

新锁做两层检查：

1. 清空 converter 的全部判断性 readouts（diagnostics、gates、unresolved opening carriers、split-const groups、missing-face-line bands、axis-snap rows），form B 输出与 baseline bit-equal。
2. 经派工单预裁的唯一自由 dict 通道 `diagnostics[].context` 注入
   `classification_hint="interzone"`；键名不含 `basis`，生产编译仍 bit-equal。再用 counterfactual monkeypatch 让 lookup 真正消费该换名载体，facts-vs-recompute 门立即抛错；清空后的文档仍绿。

因此新锁检查的是“判断结论有没有从 converter readout 泄入”，而非字段名字。没有发现第二条自由 dict 通道。

## 二、§三十条验收逐项对照

| # | 自查结果 | 对应失败条件如何被锁住 |
|---:|---|---|
| 1 | **通过**：100 条逐边行；不一致 0，具体列表 `[]` | 不只报布尔结论；audit 保留全行、mismatch IDs 与 structural failures |
| 2 | **通过**：突变 `boundary-edge:5bde04aed676a863` 后只红该边 | 配对不吃 condition，故语义突变不会扩大配对失败半径 |
| 3 | **通过**：25 个 ring 均穷举正反方向与全 rotation；几何/血缘同解；所有替代残差严格更差 | 测试断言假设集合正好等于 `forward/reverse × range(n)`，并检查 5,000-unit 硬上限 |
| 4 | **通过**：明确选择 R3 ② | 两档均由真实 facts 谓词量得，并说明对应图纸形态 |
| 5 | **通过**：从所有 view 删除 `boundary_edges` 后，两 profile 的分类、counts、vertices 与有字段时相同 | schema 空列表缺省 + 编译器独立重算路径同时受测 |
| 6 | **通过**：两 profile 改动前后均为 `100 / 32 / 68 / 0 / 0 / NA 4` | 真实数据测试冻结逐档计数和无坐标 ring 数 |
| 7 | **本席位职责内通过**：受影响子集 157 passed；`.pth` 前后相同 | 用户明确“全量归主控”，故权威全量仍须主控执行，本报告不虚报全量绿 |
| 8 | **通过**：`case_tests/test_baseline/gt/` 状态为空 | 只重生成 `gt_staging` 候选，没有重签答案 |
| 9 | **通过**：换名 `classification_hint` 生产路径不读；counterfactual 一旦消费，新锁立即红 | 锁语义依赖，不按 `basis` 字样 scrub |
| 10 | **通过**：旧 scrub 锁已删除 | 没有保留两把职责重叠、强弱不明的锁 |

## 三、staging 重生成边界

用仓库既有生产脚本
`AI_agent/logs/experiments/2026-08-29_o21b_facts_ledger/build_sm25_facts_staging.py`
重生成 sm25 候选。只改 `gt_staging/sm25-L_anchor/facts/` 三件套；答案根零改动，五个 revision 对象逐对象不变。

相对开工 HEAD 的语义 diff：

```text
as_measured.json
  views[0].boundary_edges: absent -> 44 rows
  views[1].boundary_edges: absent -> 56 rows

revisions.json
  as_measured_content_sha256:
    37f6103541f27c6799cd12baf068afeeb37a7fb7d5b820242dfb0a790a64eb0e
    -> 839d67a224851b64309faa17368648b0666d08d4f9505e6514c6d65b818abea8

as_signed.json
  views[0].boundary_edges: absent -> 44 rows
  views[1].boundary_edges: absent -> 56 rows
  derivation.as_measured_content_sha256: 同上
  derivation.revisions_content_sha256:
    6d576756f7b55a457239ed4a27e6bbe172a930a5649f4d161ca80f618ae4f362
    -> 622ce7c0fa009e2a4836ead3825236209a80b8ed52ff964b0e04000b87e3c39a
  derivation.deriver_version: 1 -> 2
```

未变哨兵：source hash `4a949224...`，request-as-measured hash `ae272a73...`，converter fingerprint `d5825959...`。两个已签 request 文件的 file sha256 与 stored/recomputed request hash 也逐位未变：

| 文件 | file sha256 | stored = recomputed request sha256 |
|---|---|---|
| `request.json` | `e635ab116e21407734a093d2dc07194899a901d801d3d57624b3fa908d9396df` | `d738d0ac230f21ae20f477b1cc084549f1308bff295a3f6de8956da98d25a135` |
| `request_as_measured.json` | `55305752145f3f44cf5c895956d5095c9ee0784f373c7380545e66685d0a7796` | `ae272a73...` |

## 四、测试与环境哨兵

以全部受影响的一等 Python 路径调用 `scripts/tool_scripts/affected_tests.py --changed ...`，工具判定 `SCOPE: SUBSET`，选中 10 个文件：

```text
tests/test_answer_compiler_closure.py
tests/test_answer_compiler_exit_gate.py
tests/test_answer_compiler_profiles.py
tests/test_as_measured_facts_layer.py
tests/test_boundary_condition_facts.py
tests/test_denominator_from_facts.py
tests/test_gt_facts_staging_case_admission.py
tests/test_gt_facts_staging_gate.py
tests/test_gt_facts_staging_sm25.py
tests/test_gt_revisions_and_as_signed.py
```

最终命令使用 `-n auto`，结果：**157 passed in 31.52s，exit 0**。另外，受影响 Python 文件 `compileall` 成功，`git diff --check` 为空。现有环境没有 `ruff`，本席位没有安装或写共享 venv。按用户明确分工，本席位没有跑全仓；权威全量留给主控。

收工哨兵：

```text
HEAD before = HEAD after
            = 54e3633a4f9f3e381359a8200dfc8593966b3c2a

.pth before = .pth after
路径    = /opt/venv/lib/python3.12/site-packages/_editable_impl_energyplus_agent.pth
sha256  = 58f547fa9433af6eca0e8f362652b78916b13a21fbeab4ef06f1e07e46744e43
内容    = /workspaces/EnergyPlus-Agent-dev

答案根 case_tests/test_baseline/gt/ = 零改动
```

施工期间主树出现两个非本席位创建的未跟踪派工文件：
`2026-08-30_o22_design_rework_crossreview_glm.md` 与
`2026-08-30_o22m1_as_drawn_producer_types_dispatch.md`。它们未被读取、改动或纳入本单；HEAD 和本单承重代码未移动。

## 五、范围与改动路径

- 没有建 worktree、没有切分支；没有运行 `pip install -e .` 或任何写 site-packages 的命令。
- 没有改 correction、`promote_gt_v3`、正交吸附、两种 profile 定义、转换器 `basis` 判据或答案根。
- 没有让 facts condition 服从 converter basis，也没有反向改写；门只观测、列举并可响亮失败。
- 未发现真实 mismatch，故没有登记虚构缺陷。

本单改动路径：

```text
AI_agent/logs/reviews/execution/2026-08-30_o21d_boundary_condition_execution.md
case_tests/test_baseline/gt_staging/sm25-L_anchor/facts/as_measured.json
case_tests/test_baseline/gt_staging/sm25-L_anchor/facts/as_signed.json
case_tests/test_baseline/gt_staging/sm25-L_anchor/facts/revisions.json
src/agent/judge/answer_compiler.py
src/agent/judge/as_measured.py
src/agent/judge/gt_revisions.py
tests/answer_compiler_fixtures.py
tests/test_answer_compiler_closure.py
tests/test_answer_compiler_profiles.py
tests/test_as_measured_facts_layer.py
tests/test_boundary_condition_facts.py
```

## 六、最薄弱处与复核请求

**我认为最薄弱的一处是跨表示配对的适用域，而不是当前 sm25 的结论。** 当前实现已用全方向穷举、独立血缘解和 0.5 m 硬上限把 sm25 锁得很紧，但真实供货仍只有一个 case，且主要是轴对齐矩形 cavity；5,000-unit 上限也是当前批次的明确安全栏，不是已证明适用于未来所有图纸方言的普适常数。

希望复核方重点攻击：长短边高度不均、重复/缺失 source handles、近似对称 ring、非矩形或边数变化时，几何最优与血缘最优是否仍唯一同解；同时检查 0.5 m 上限在新方言中应当继续拒绝，还是需要经新的真实数据重新签定。其次可打 facts 侧“墙内 junction fragment 不落成逻辑 boundary edge”的边界，确认它不会在新图形中误吞本应为 `unknown` 的边。
