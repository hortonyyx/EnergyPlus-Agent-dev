# orchestrator 对抗审 · F-20 修法设计稿（sol 出稿）· **第二轮（收官）**

- **日期**：2026-08-10 · **审阅人**：orchestrator（Opus）
- **被审对象**：[`proposals/f20_validate_case_v3_proof_design.md`](../../../proposals/f20_validate_case_v3_proof_design.md)
- **本轮范围**：第一轮登记的全部未审项 —— **8 把锁 L1–L8** · §3 改动清单与 §2.2 状态表对账 ·
  §2.5 `--intake-from` · §2.7/§5 施工顺序与危险中间态 · §6 铁律 #6 复核 · sol 自陈的 5 条「没能确定」
- **裁决**：**APPROVE — 0 BLOCKER / 0 MAJOR / 2 NIT**
  ⇒ **可据本稿出施工单**（NIT 与下方两条结转写进派工单即可）

---

## 1. ⭐ 本轮第二处「躲开的雷」：新检查放哪一层，是必须不是整洁

设计稿把新检查 `correction.accepted_artifact_trust` 放进 **`1_correction`**，
并明确拒绝调查报告 Q4 建议的名字 `2_modelling.window_host_proof_unavailable`，
理由是「放 kernel report 会让既有 approval 全部变 stale」。

**orchestrator 独立复核 —— 理由成立，且后果比设计稿说的还硬**
（`src/agent/execution/approval.py:37-54`）：

```python
def geometry_checkpoint_digest(*, building_geometry, geometry_specs,
                               kernel_check_report, stage_version, check_version):
    return combined_digest([... hash_obj(kernel_check_report) ...])
```

**digest 直接哈希整份 kernel report** ⇒ 往 `2_modelling` 报告里加**任何**一行
（哪怕是 legacy run 上一条无害的 `NOT_APPLICABLE`）
⇒ **盘上每一个既有 run 的 digest 全部改变 ⇒ 所有历史几何批准一次性失效。**

⇒ **这是 sol 躲开的第二发**（第一发 = V1/V2 三态，见第一轮裁决）。
两发都出在**调查报告的建议**里，而调查与轻门都是 Claude 侧。

---

## 2. 8 把锁 L1–L8 逐把判读

**总评：结构合格，无 false lock 迹象，且正面回应了本项目最近三条最贵的教训。**

| 锁 | 锁什么 | 判读 |
|---|---|---|
| **L1** | v3 正向贯通三个消费口（有窗 + 零窗），digest 非空、`approve_geometry` 真能签发 | ✅ **这是本批的关键正向锁**。自证前提写得对：先分别断言「无 proof 直接 build 会抛」「correction 会出 blocker」「kernel 会出 blocker」，任一前提消失立即 fail |
| **L2** | accepted output 被改而 manifest hash 不改 ⇒ FAIL、不回退 | ✅ 变异前断言干净态 PASS + digest 非空；变异后**先断言 stage-root 未变**（防两边一起弄坏） |
| **L3** | 六件套缺件 ⇒ FAIL | ✅ 先断言六件与六个 manifest key 精确齐全再删一个；夹具将来不生成该文件会**在变异前**大声失败 |
| **L4** | v3 挂到非 B5 contract ⇒ FAIL | ✅ 变异后断言 wire **仍是可加载的 V2 manifest**，避免只测到「JSON 写坏了」 |
| **L5** | 只篡改 stage-root 非权威副本 ⇒ V2 仍以 accepted 为权威 | ✅ **方向锁**，与 L2 成对钉住「谁是权威」；前提断言两份 bytes 原本相同 |
| **L6** | 无账本 / V1 legacy 继续可审，digest 与修前**冻结值**相同 | ✅ 用**施工前冻结的**期望值比对，⛔ 明确禁止「修后临时算一个期望值」——这条自觉性很高 |
| **L7** | v3 夹在无账本 / V1 下 ⇒ FAIL | ✅ 与 L6 互为反向 |
| **L8** | 未知代码异常 ⇒ ERROR 而非 FAIL；哨兵异常**恰好触发一次**（零次或多次都 fail） | ✅ 调用计数断言防「patch 没生效也绿」 |

**三条最贵教训的兑现（逐条核对）**：

1. **「只有负向断言的门恒红不可观测」（08-10，F-19）** ⇒ §4 开篇即写死：
   **所有新负锁先在同一个干净夹具上断言 trust `PASS` 且 digest 非空，再做单一变异**；
   §2.3 另写「新检查必须同时有 `PASS` 行，否则永远失败的 trust gate 会让所有负锁永久假绿」。**正面回应。**
2. **「回归用例必须自证前提」（08-09）** ⇒ 8 把锁**每把都有独立的「自证前提怎么写」段**，
   且 L6 明确禁止把 legacy 半的天然绿伪报成「修前会红」。**正面回应。**
3. **「夹具自洽不算数」（F-5）** ⇒ 夹具走 `StageRunner.record(...)` 真实 accepted attempt，
   2/3 产物用 canonical serializer 生成而非手写坐标。**正面回应。**
   ⚠️ 但见 NIT-2：**本批刻意不把真实 run 纳入夹具**，sol 已如实声明（§8.2），不算隐瞒。

**⭐ 单独表扬一条**：L1 要求**零窗 v3 也必须正向通过**，理由是防施工写出
`if windows: load proof` 这种后门 —— 而 `build.py:208` 的报错原文正是
「v3 build requires VerifiedWindowHostProof, **including zero-window output**」。
**锁与被锁的契约逐字对上了。**

---

## 3. §3 改动清单 vs §2.2 状态表逐行对账

**11 行状态表逐行比对：10 行在伪代码里有对应分支，1 行没有。**

- ⚠️ **NIT-1**：状态表第 4 行「manifest 文件存在但 JSON／版本／schema 无法解析 ⇒ FAIL」，
  §3.1 伪代码只写了「查看 manifest 文件状态并用版本 dispatcher 解析」，
  **没有显式画出解析失败这条分支**。稿子性质是伪代码、状态表已覆盖，
  但**施工单必须点名要求这条分支落地并配锁**（否则最容易被实现成 `except: 当作无账本` = fail-open）。

其余对账无异常。另核实三条「明确不改」（`stage_runner.py` / 信任根算法 / `build.py` 的 v3 强制 proof 门）
与 §5 危险中间态表**互不冲突**。

## 4. §2.5 / §6 复核

- **`--intake-from` / `DOWNSTREAM_ONLY`**：✅ 属实。early return 在 `validation_run.py:94-97`，
  确在 required-artifact guard 与 0–4 逻辑之前。设计稿要求 resolver 留在该 return **之后**、
  ⛔ 不许为「统一初始化」提到函数顶部 —— 这条约束是对的。
- **铁律 #6**：✅ 通过。resolver 只分辨 manifest version / artifact contract / schema version，
  **不读也不推断 footprint、每层满铺、层高、cardinal facade**；锁只断言身份与状态，
  ⛔ 不冻结「一个方形、3 米层高、固定窗数」。最小方形夹具只作接线载体。
  ⇒ 未烤死非方形／退台／挑空／中庭。**（这正是 sol 08-09 用来否掉 F-9 稿的那条，本稿自己过了。）**

---

## 5. ⭐ orchestrator 关掉了 sol 自陈的第 4 条「没能确定」

sol §8.4：「没有枚举所有 V2 legacy run 的 accepted output 是否与 stage-root convenience copy 一致」。

**orchestrator 机械测量（全仓 22 份 V2 账本逐个比 sha256）**：

```
有 1_correction accepted 记录的 V2 run = 4 个
  SAME  schema_v=None   run_2026-08-05_probe_a_legacy_snapped
  SAME  schema_v=None   run_2026-08-06_wall3_a_retest
  SAME  schema_v=None   run_2026-08-07_f13_e2e_verify
  SAME  schema_v=3      run_2026-08-09_f18_e2e_verify
  DIFF  = 0
其余 17 个无 1_correction stage 记录、1 个缺件
```

⇒ **把权威切到 accepted attempt，对盘上现有 V2 legacy run 的行为变化 = 0（实测）。**

⚠️ **口径必须说准**：这测的是**今天这份盘上语料**，**不是**「代码保证两者恒等」的不变量证明。
镜像与 accept 写在同一段代码里（`stage_runner.py:560-563`，紧跟 `manifest.accept`），是**强相关**，
**不是已证不变量**。⇒ sol §8.4 要求的「施工时 targeted replay 若发现差异应停下上报」**保留**。

---

## 6. ⛔ 两条 NIT + 一条新登记

- **NIT-1**（见 §3）：伪代码缺「manifest 存在但解析失败」分支 ⇒ 施工单点名要求落地 + 配锁。
- **NIT-2**：现有夹具砖签名是 `_accepted(tmp_path, *, include_elevation=False)`
  （`tests/test_c2_b5_artifact_trust.py:39`），**没有零窗开关**；
  L1 要求的「零窗 v3 正向通过」需要**真正扩展夹具**，可行性未经演示。
  ⇒ **施工单第一步就该验这块砖能不能造出零窗 v3 accepted attempt**；造不出就停下上报，⛔ 不许把零窗那格悄悄删掉。

- **⛔ 新登记 F-21 候选（与 F-20 无关的结构缺口，本轮顺手撞出）**：
  `approve_geometry`（`step_orchestrator.py:486-488`）**只看 `res.geometry_digest is None`**，
  **不看 `res.blocked`** ⇒ **1_correction 仍在阻断时，只要 2_modelling 出了 digest，几何批准照样签得出来。**
  sol 在 §5 把它写成「分步施工的最危险中间态」，但 orchestrator 复核后认为
  **它是今天就存在的常态缺口，不是只在中间态出现**。
  ⚠️ **未定性**：实际严重性取决于 flow 是否在别处拦住（`res.blocked` 仍为 True），**需独立调查**。
  ⛔ **不并入 F-20 施工**。

---

## 7. 裁决与记账

**APPROVE（0 BLOCKER / 0 MAJOR / 2 NIT）⇒ 可据本稿出施工单。**

**需要用户拍板的只有一条**，sol 已用白话写在 §7：
**是否接受「有正式记账的新 run 一律信记账、没记账的老 run 保留旧入口」这条原则。**

**⭐ 记账**：本稿是**跨家族出稿的第二例实证**，且**两发雷都躲在同家族两道工序（调查 + 轻门）的盲区里** ——
① 账本不是二值（V1/V2 三态，11 个 V1 run 会被二分法废掉）；
② 新检查放 kernel report 会让所有历史批准失效。
⇒ **「设计稿不该由 orchestrator 亲手出、必须跨家族」这条纪律，本轮价值兑现得比 08-09 那次更直接**
（那次是我的稿被判 REWORK，这次是我的题被出稿方纠正）。**派工方错误率 14/14 维持。**
