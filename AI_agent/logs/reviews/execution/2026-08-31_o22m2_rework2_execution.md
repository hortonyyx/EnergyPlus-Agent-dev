# 第二轮返工执行档 · ②-2 模块 2（B-1 来源闭合 + B-2 无载体通道拒绝 present）

- **日期**：2026-08-31 · **施工**：GLM 家族 · **单**：`../request/2026-08-31_o22m2_rework2_glm.md`
- **裁决**：`../verdict/2026-08-31_o22m2_rework_crossreview_gpt.md`（REWORK / 阻断 2）
- **基线**：`6637f38`（`evidence_contract.py` 与送审基线 `bb91f77` 逐字节相同，
  `git diff bb91f77..HEAD -- src/agent/correction/evidence_contract.py` 为空，已核）
- **跑测**：一律 `-n 4`；未跑全量；未 `pip install -e .`；未 `git add`/`commit`

## 0. 改动路径（验收 7；⛔ 均未提交）

| 路径 | 性质 |
|---|---|
| `src/agent/correction/evidence_contract.py` | B-1/B-2 生产门（+128 行，零删除） |
| `tests/test_o22m2_evidence_contract.py` | 三条新测试 + helpers（+239 行）；**唯一删除行 = inv5 夹具的来源表一行**（见 §6 披露） |
| `AI_agent/logs/experiments/2026-08-31_o22m2_rework2_probe/probe_rework2.py` | 复现探针归档（过程痕迹，非证据自足——读数以本文为准） |

⛔ `AI_agent/plan.md` 的工作树改动**不是本单的**（开工时 `git status` 无已跟踪文件修改，
系并行席位/主控所写），本单未触碰。`vector_contract.py` / `pipeline.py` / `src/agent/judge/` /
`evidence_adapters.py` 均未触碰（`git status --short | grep -v "??"` 仅上表两文件 + plan.md）。

## 1. 复现（必停项核查：复核方三条复现全部复现得出，未触发停报）

独立探针（五形态：复核方 B-1×2 + B-2 + 验收 2 的两形态），在**改前树**上跑：

```bash
git archive HEAD | tar -x -C /tmp/o22m2_rework2_glm/old     # = bb91f77 的校验器
python /tmp/o22m2_rework2_glm/probe_rework2.py /tmp/o22m2_rework2_glm/old
```
```text
B1[walls]: VALIDATES            ← 复核方反例 1：声明来源=empty_plan，载荷全来自 tiny
B1[plan_openings]: VALIDATES    ← 复核方反例 2
B2[dimensions]: VALIDATES       ← 复核方反例 3：dimensions=present + zero_payload_channel(dimensions)
B1-reverse[unscoped]: VALIDATES      ← 声明 (empty_plan,tiny)、载荷仅 tiny、无 debt
B1-reverse[global-debt]: VALIDATES   ← 同上 + 一条 channel 粒度 zero debt（⛔ 不算过的那条）
```
（此读数同时是验收 4 的「改动前确实放行」硬证据：改前副本 + 同形输入。）

## 2. B-2 实现（无载体通道永远不可能 present）

改动点（`_assert_channel_payload_closure`，生产校验器内）：
1. `zero_payload_channel` debt 挂在 `dimensions`/`room_roles`/`elevation_openings` 上 ⇒
   **debt 本身拒收**（`ZERO_PAYLOAD_DEBT_WITHOUT_PAYLOAD_CARRIER`）——通行证不再发给
   没有载荷成员的通道；
2. `present` 豁免集合只收 `walls`/`plan_openings`（`_CHANNELS_WITH_PAYLOAD_MEMBERS`）；
3. 无 debt 的 present 仍走 F-1 原码 `PRESENT_CHANNEL_WITHOUT_PAYLOAD`
   （⛔ 既有断言 1336–1337 行期待该码，一字未动）。

## 3. B-1 实现（来源闭合，双向）

新生产函数 `_assert_channel_source_closure(bundle, frozen)`（接在 F-1 调用之后），
只作用于 **present 且有载荷成员** 的通道：
- **正向**：载荷来源（walls = 每个 claim 的全部 refs ∪ 每个 disposition 的 face_ref
  **与 reason_ref**；plan_openings = 每个 opening 的 source_ref）必须 ⊆
  `status.source_input_ids`，违者 `PAYLOAD_FROM_UNDECLARED_SOURCE`；
- **反向**：通道有载荷、但声明来源中某来源本次零载荷 ⇒ 该来源必须被一条
  `zero_payload_channel` debt 以 `affected_refs` **定域豁免**，违者
  `CHANNEL_SOURCE_WITHOUT_PAYLOAD_OR_SCOPED_DEBT`。⛔ channel 粒度全局 debt 不进豁免表。
- **豁免不可伪造**：scoped debt 的每个 ref 必须按**身份三元组**
  （input_id / contract / sha256）与 frozen 来源一致，违者
  `SCOPED_ZERO_PAYLOAD_DEBT_REF_UNKNOWN`。

⭐ **设计裁决（自定口径，供复核方核对）**：整通道零载荷（如 `_empty_artifact` 的
walls）**保留** F-1 的全局 debt 出口——此时该 debt 的陈述「本通道本次零载荷」为真；
「部分来源空跑」时同一句陈述为假，必须定域。这是验收 2（全局 debt 不算过）与既有
断言 / 验收 3 双向（`walls=present + zero_payload_channel(walls)` 须放行）能同时成立的
唯一分界。scoped 的载体用**既有字段** `affected_refs`，未加 schema 字段、未动
canonical 面。

## 4. 改后读数（同一探针、主树）

```bash
python /tmp/o22m2_rework2_glm/probe_rework2.py .
```
```text
B1[walls]:            REJECTS PAYLOAD_FROM_UNDECLARED_SOURCE {'channel':'walls','payload_input_ids':['tiny'],'declared_input_ids':['empty_plan']}
B1[plan_openings]:    REJECTS PAYLOAD_FROM_UNDECLARED_SOURCE {…'channel':'plan_openings'…}
B2[dimensions]:       REJECTS ZERO_PAYLOAD_DEBT_WITHOUT_PAYLOAD_CARRIER {'debt_id':'debt_zero_dimensions','channel':'dimensions'}
B1-reverse[unscoped]:     REJECTS CHANNEL_SOURCE_WITHOUT_PAYLOAD_OR_SCOPED_DEBT {'channel':'walls','input_ids':['empty_plan']}
B1-reverse[global-debt]:  REJECTS CHANNEL_SOURCE_WITHOUT_PAYLOAD_OR_SCOPED_DEBT（⛔ 全局 debt 未豁免）
```

## 5. 验收逐条（§四 表）

| # | 验收项 | 命令 | 读数 |
|---|---|---|---|
| 1 | B-1 两反例响亮 + 正常产物仍绿 | 新测试 `test_b1_payload_must_come_from_the_channels_declared_source`；正例段循环 `_built(name)` × 3 + tiny + legacy | 两通道红 + 五个正例全绿（54 passed 内） |
| 2 | 反向：零载荷来源需**定域** debt | `test_b1_declared_source_without_payload_needs_a_scoped_debt` | 无 debt 红 / **全局 debt 仍红** / scoped 放行 / 伪造 sha 红 |
| 3 | B-2 响亮 + 合法出口仍放行 | `test_b2_a_channel_without_payload_carrier_can_never_be_present` | debt 门红；naked present 走旧码 `PRESENT_CHANNEL_WITHOUT_PAYLOAD`；`walls=present + zero(walls)` 真零载荷**放行** |
| 4 | 先绿后红 | 每条新测试 BEFORE 段 `monkeypatch.setattr(evidence_contract, <新门>, no-op)` 后 validate ⇒ 放行；另 §1 改前副本探针 | BEFORE 全放行（红只能来自新门）+ 改前树五形态 VALIDATES |
| 5 | neuter 对撞 13→涨 | 见 §5.1 | **16 failed / 17 passed**，名单 = 原 13 原样 + 新 3 |
| 6 | 两文件 -n 4 全绿 | `python -m pytest tests/test_o22m2_evidence_contract.py tests/test_o22m3_evidence_adapters.py -n 4 -q` | **54 passed**（m2 33 = 30 旧 + 3 新；m3 21） |
| 7 | 列全改动路径 | §0 | — |

### 5.1 验收 5 的 neuter 机械对撞（复核方同法：副本 + docstring 后插 `return None`）

```bash
tar -C <主树> --exclude=.git --exclude=__pycache__ … -cf - . | tar -xf - -C /tmp/o22m2_rework2_glm/new
# 在副本 validate_evidence_bundle 的 docstring 后插入 "    return None"，然后：
cd /tmp/o22m2_rework2_glm/new && PYTHONPATH=$PWD \
  python -m pytest tests/test_o22m2_evidence_contract.py -n 4 -q --tb=no -ra
# 16 failed, 17 passed in 3.60s   （未摘同副本先跑：33 passed，环境自证）
```
16 条 = 裁决书原 13 条**逐条原样**（inv1/inv2/inv3/inv4/inv5/inv6/inv7/inv8、n1、
observed_unclaimed、nf4_4、f1、f2）+ 新 3 条：
`test_b1_payload_must_come_from_the_channels_declared_source` ·
`test_b1_declared_source_without_payload_needs_a_scoped_debt` ·
`test_b2_a_channel_without_payload_carrier_can_never_be_present`。
⇒ 三个新门都在生产校验器里，不是测试工厂造红。

## 6. ⭐ 最需要复核方看的一处：`test_inv5` 绿前提夹具的来源表如实化

新门在主树上首次跑时**唯一**被误伤的既有锁是 `test_inv5_one_source_per_semantic_slot`
的绿前提（883 行 `validate_evidence_bundle(art)`）：该前提把 tiny（9f）与 legacy（8f）
两份 bundle 的 wall_claims **合并**，但 `channel_status` 直接复用 tiny 的——walls 来源表
只写 `("tiny",)`，却携带 `legacy_plan` 的 claims。**这恰是 B-1 的反例形状**（载荷来自
未声明的来源），只是作为夹具 incidental 构造、旧契约下无人查。处置：
- **被测断言一字未动**（923 行 `_expect_error(art2, "DUPLICATE_SEMANTIC_INPUT")` 原样，
  且 inv5 检查在 validate 里先于新门，art2 读数不变）；
- 只把夹具的 walls 来源表补成如实的 `("tiny", "legacy_plan")`（唯一删除行），
  绿前提的语义「不同楼层来源可共存」保留。
- ⚠️ 这是本单对既有测试文件的唯一非新增改动；若复核方判这属于「改既有断言去迁就
  新门」而非「夹具疏漏被新门暴露」，此为返工点而非争议点——请按前一种读法处理。

## 7. 其余核查

- **nf4_1 / nf4_2 语义未动**：两测试无改动（diff 无其行）。
- **消费方**：`evidence_contract` 的消费方全集 = `evidence_adapters.py`（未动）+
  两个测试文件；m3 的 21 条（两个 adapter 的出口都调 validate）全绿 ⇒ 新门未误杀
  模块 3（其 walls/plan_openings 均「有载荷才 present、来源=自身 input_id」）。
- **F-152**：`git diff -- src/ tests/ | grep '^+' | grep '"\(src/\|tests/\|AI_agent/\|…\)'`
  ⇒ 无命中（新代码无仓库根前缀路径字符串）。
- **禁改面**：`vector_contract.py` / `pipeline.py` / `src/agent/judge/` /
  `evidence_adapters.py` / 已落库产物 / `canonical_bytes` 均零改动；
  `EvidenceDebtV1` 等类型**未加字段**。

## 8. 最薄弱处（自报）

1. **scoped 豁免是超集语义**：一条 scoped debt 的 `affected_refs` 列出谁就豁免谁——
   豁免一个**本次其实有载荷**的来源会静默通过（多豁免不洗绿任何未声明载荷，实害有界，
   但「豁免恰好 = 零载荷来源集」这格没锁）。
2. **`absent` + 带载荷**（如 walls 标 absent 却有 claims）至今无门——同族（状态与载荷
   不一致）的第三个方向，本单任务项未点名，未实施、未登记缺陷号，留派工方定夺。
3. `reason_ref` 计入 walls 载荷来源是本单自定口径（裁决书字面只说「face disposition 的
   来源」）；将来若模块 3/4 合法产出跨源 reason_ref 会被此门卡住——当前两个 adapter
   全同源，无实害。
