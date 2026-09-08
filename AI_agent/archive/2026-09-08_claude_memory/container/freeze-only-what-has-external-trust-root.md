---
name: freeze-only-what-has-external-trust-root
description: 配不配被冻结看两道题（有没有第二处记载 / 那处记载是否事先固定且被评判方写不了）；在册的根只有两个，新增须用户拍板；命令行旋钮一律来自当次调用
metadata: 
  node_type: memory
  type: project
  originSessionId: 5a80e074-a34a-4dc3-8172-b86cf9afd3e3
  modified: 2026-08-12T15:59:18.484Z
---

**2026-08-04 orchestrator 裁定（R1 批 B r2-4），起因是施工席 GLM 停下上报「(a)/(b) 两个方案都无解」。**

**判据（2026-08-04 用户拍板最终版；初版「只有 run_config.yaml 才算」被交叉审 Q-8 证明当时就与仓库现状不符 ⇒ 作废）**：
> 一个设置值不值得被**冻结**并纳入防漂移，看两道题：
> **① 除冻结记录本身外，是否存在第二处记载**说明它本该是什么？
> **② 那处记载是否先于本次运行就已固定**（进 git / 有人签字 / 绑真实文件指纹）**且被评判的一方写不了**？
> 两题皆是 ⇒ 可冻结；任一为否 ⇒ **不冻结、不据以判定**，至多留**显式标注非权威**的审计快照。

**在册的第二处记载（⛔ 新增须用户拍板 + 登记 decision_log §5.14）**：
① `run_config.yaml` 的档位声明（`run_profile`/`capability_profile`）；
② case 身份（`case_data/testdata_prompt.json` 考卷声明 + 真人签字 + 与真实图像核对的 `image_sha256`）。

**Why**：`_run/run_policy.json` 的 `content_sha256` 与 `policy_hash` 都是 **payload 自身的哈希、可自行重算**
⇒ 把一个 CLI 来源的开关「纳入哈希」**挡不住任何篡改**（它根本没有第二处记载可对账）。
两方独立实跑证实：改 `context.require_ep` 再重算哈希 ⇒ 校验与漂移复核照常通过、baseline 静默漏记阻断行。
⇒ 我 r2 派工单给的选项 (a)「纳入哈希」**从一开始就不成立，是出题方的错**。
本判据其实是 terra 在 R1-5 自己划的那条线（「draw budget / reread availability 属运行期旋钮不是档位政策」）
的另一侧，我在 r1 轻门已批准过 ⇒ **统一成一条，不再逐个字段拍脑袋**。

**How to apply**：
- 新增字段要进冻结记录前先过那两道题（有没有第二处记载 / 它是否事先固定且被评判方写不了）；过不了 ⇒ 不进判定面，最多做**显式标注为非权威**的审计快照；
- ⛔ 审计快照必须在字段名/注释上写死 "never authoritative, never consumed for decisions"——
  否则就是 [[reading-supervision-contamination]] 那族「记录了就以为守住了」的第二类假锁；
- ⛔ 别再用「把它也塞进哈希」当安全措施回答篡改类问题。
- ⛔ 新增冻结维度走 `RUN_POLICY_SCHEMA_VERSION` 升版，不要往 `_run_policy_hash` 加位置参数（会让所有历史冻结件当场失效）。

---

**⭐⭐⭐ 2026-08-12 最强实证（sol 第三轮复审的 BLOCKER）—— 同一条判据换了个壳又被违反一次。**

修 F-22 时给确定性核加了一个**无条件印章**（`deterministic_core_stamp`），判卷改为验印章。
印章的写入端做对了（唯一 return 前无条件覆盖写、伪值也会被盖掉、条件盖章的 mutant 能让锁转红）。
**但印章存在【产品自己携带的字段】里** ⇒ **它不是 provenance，只是「对象声称核跑过」**。

**sol 的两级反例（orchestrator 已核实）**：
1. 往 F-17 翻转前的真实产物里**手加一行** `"deterministic_core_stamp": {"version": "1"}`
   ⇒ `trusted=False` **变成** `trusted=True`，两层 boundary 都变 `4/4`。
2. **更狠**：伪造一个 `[0,4]²` producer 重签成 `[0.12,3.88]²` 的**内部自洽**候选
   （重物化 Vg、重算 feature/host/candidate identity/evidence），
   **真实 `StageRunner.record` 接受并持久化了这份伪造几何**。
   根因 = writer 从 embedded producer 重放了 core，**但只拿 replayed windows 去核 audit/host，
   从不比较 replayed footprint/floors/cells 与候选**。

> ⭐ **判别问法（本条的可执行形式）：「这个字段，被评判的一方能不能自己写？」
> 能写 ⇒ 它最多叫 `declared`，绝不能叫 `trusted`。**

**⛔ 连带教训**：施工席的锁 `test_neuter_restoring_stamp_flips_judge_back_to_accept`
**把这个 bug 写成了正向预期** —— 锁越完备，越会把错误的语义固化下来。
⇒ 与 [[whoever-writes-cannot-review-blind-spot]] 同源：**作者的锁只能证明实现符合作者的理解。**

**✅ 正确修法方向（sol 给、可直接施工）**：writer 重放后对 **core-owned projection** 做规范化等价/哈希比较
（footprint / 每层 ring・cells / core 后 window span・floor / corrections・conflicts・unsupported / stamp）
→ 由 **writer 在重放成功后签发** `deterministic_core_proof{core_version,input_hash,core_projection_hash}`
并绑进 accepted manifest → **scorer 只认 manifest 上的 proof，不认候选自带的 stamp**
→ 补一把真实 `StageRunner.record` 锁（内部自洽但与 replay 不同的候选必须在 accepted 指针移动前失败）。

相关：[[lock-must-exercise-real-entry-point]]（同夜第三次「声称在守其实没守」）· [[controller-must-stay-out-of-product]]
· [[version-number-is-not-behavior-attestation]]（08-12 同日、同一条链的上一环）
· [[absence-conflates-causes-in-observables]]
