# 派工单 · F-20 施工：`validate_case` 接通 v3 accepted proof

- **日期**：2026-08-10 · **席位**：Claude 侧 **Sonnet**（执行档）· 通道 = Agent 子代理
- **基点**：分支 `6.15_ValidationArchM0toM4`，**HEAD = `efb8080`**，工作树干净
- **全仓基线**：`python -m pytest -p no:cacheprovider -q -n 8` ⇒ **2345 passed / 10 xfailed / 0 failed**
  （⛔ 不要 `-n auto`：16 worker 实测在 ~98% 处**静默 OOM**，外观与「还在跑」难分）
- **用户已拍板的原则（2026-08-10）**：
  > **有正式记账（V2 run manifest）的 run，一律以账本指向的 accepted 产物为唯一权威；
  > 没有记账、或只有旧格式（V1）记账的老 run，保留今天的 stage-root 离线审计入口。**

---

## ⛔ 0. 第一步：防假验证自检（动任何代码之前做，答案写进执行日志）

> **派工方（orchestrator）自陈错误率 = 14/14** —— 迄今每一次执行席「停下上报」，
> 事后都证明是派工单的题错了。**最近一次就在本条链路上**：我把 F-20 的岔口写成
> 「有账本 / 无账本」二分，调查席照题作答、我自己做轻门也没看出，
> 最后由 sol 出稿时才发现**账本有 V1/V2 两种**（盘上 V1 十一份）。

先回答这四问，**答不上来就停下上报，不要开工**：

1. 我打算用来验收的那条路径，**真的会执行到 `validation_run.py` 里我改的那一段吗**？
   （⚠️ `--intake-from` / `DOWNSTREAM_ONLY` 在 `validation_run.py:94-97` **早退**，根本不走 0–4。
   拿冻结产物 + 跳段入口验收 = 天然的假验证温床。）
2. 我的锁的夹具，**`schema_version` 真的是 `"3"` 且 `artifact_contract` 真的是 B5 吗**？
   （若不是，`build_geometry` 走的是 legacy 分支 ⇒ 我锁的是另一回事。）
3. 我怎么证明「不加我的修法，每一把新锁都是红的」？（见 §3 自证前提的硬要求）
4. **NIT-2 那块砖我先验了吗？**（见 §2.0 —— 这是本单的第一个动作，不是最后一个）

---

## 1. 设计权威 = sol 的设计稿，⛔ 不要重新设计

**唯一设计权威**：[`proposals/f20_validate_case_v3_proof_design.md`](../../../proposals/f20_validate_case_v3_proof_design.md)
（`gpt-5.6-sol` / effort max 出稿，**orchestrator 对抗审两轮 ⇒ APPROVE，0 BLOCKER / 0 MAJOR / 2 NIT**）

**必读的配套三份**（读完再动手）：

| 文件 | 为什么必读 |
|---|---|
| 上面那份设计稿（355 行） | §2.2 的**11 行状态表**是实现规格 · §4 的 **8 把锁**是验收规格 · §5 的**危险中间态表**是施工顺序约束 |
| [`verdict/2026-08-10_f20_design_crossreview_orchestrator_round2.md`](../verdict/2026-08-10_f20_design_crossreview_orchestrator_round2.md) | 两条 **NIT 必须在本单落实**（见 §2） |
| [`experiments/2026-08-10_f20_validate_case_v3_proof/README.md`](../../experiments/2026-08-10_f20_validate_case_v3_proof/README.md) | 缺陷事实与 Q1–Q6 实测（⛔ **不要重做调查**） |

**⛔ 明确禁止的方向**（设计稿已定，本单不重开）：

1. ⛔ **不许走选项②**（把 `feature_states.json` / `window_resolver_inputs.json` / `window_hosts.json`
   镜像到 stage 根）。⛔ 不许改 `src/agent/execution/stage_runner.py`。
2. ⛔ **不许 fail-open**：V2 分支一旦开始，**任何**失败都不得回退 stage-root 便利副本。
   ⛔ 不许写 `except: use snapped`，⛔ 不许把 proof 置空后继续。
3. ⛔ **不许把新检查放进 `2_modelling` 报告**。
   理由已实测：`geometry_checkpoint_digest`（`approval.py:37-54`）**直接 `hash_obj(kernel_check_report)`**
   ⇒ 往那份报告加**任何**一行（哪怕 legacy run 上一条无害的 `NOT_APPLICABLE`）
   ⇒ **盘上每个既有 run 的 digest 全变、所有历史几何批准一次性失效。**
4. ⛔ 不许改 `load_verified_accepted_correction` / `VerifiedWindowHostProof` / `build_geometry` 的合同。
5. ⛔ 不许把 `DOWNSTREAM_ONLY` early return 挪位置，⛔ 不许为「统一初始化」把 manifest/proof 加载提到函数顶部。
6. ⛔ 不许删 snapped required-artifact guard、两条历史注释（`validation_run.py:304-306` / `:324-326`）、
   或 `validation_manifest.json` 的独立文件名。

---

## 2. 本单额外要求的两件（对抗审的两条 NIT，⛔ 设计稿里没写全）

### 2.0 NIT-2 —— **这是本单的第一个动作**

设计稿 §4 的 **L1 要求「零窗 v3 也必须正向通过」**（防施工写出 `if windows: load proof` 这种后门 ——
`build.py:208` 的报错原文逐字写着 "including **zero-window** output"）。

**但现有夹具砖的签名是**：

```python
# tests/test_c2_b5_artifact_trust.py:39
def _accepted(tmp_path: Path, *, include_elevation: bool = False):
```

**没有零窗开关。** 设计稿说「小幅扩展」，**但可行性未经演示**。

⇒ **开工第一件事：验这块砖能不能造出一份零窗的 v3 accepted attempt。**
- 能 ⇒ 照做，继续。
- **不能 ⇒ 停下上报**（说明卡在哪），
  **⛔ 绝对不许把 L1 的零窗那一格悄悄删掉当作没这回事。**

### 2.1 NIT-1 —— 补一条设计稿伪代码里没画出来的分支

设计稿 §2.2 状态表**第 4 行**要求：
「manifest 文件存在但 JSON / 版本 / schema **无法解析** ⇒ `FAIL`，不回退 stage root」。

但 §3.1 的伪代码只写了「查看 manifest 文件状态并用版本 dispatcher 解析」，
**没有显式画出解析失败这条分支**。

⇒ **本单必须显式实现该分支并配一把锁。**
⚠️ 这条最容易被实现成 `except: 当作无账本` —— **那正是 fail-open**，撞 §1 禁令第 2 条。

---

## 3. 锁的硬要求（本项目最近三条最贵教训，逐条必须兑现）

1. **⭐ 必须有正向锁，且所有负锁挂在正向对照后面。**
   设计稿 §4 开篇已写死：**所有 F-20 新负锁先在同一个干净夹具上断言 trust `PASS` 且 digest 非空，
   再做单一变异。** ⛔ 不许写出「只有断言 fail 的测试」——
   08-10 F-19 的教训：**一道门若只有负向断言，它【恒红】结构上不可能被测试发现，
   且所有 fail 断言会因此全部永远绿。**
2. **⭐ 每把锁必须自证前提**：先断言「不加修法，这把锁在这个夹具上确实会红」，
   **前提破了要大声报错**，⛔ 不许静默退化成空锁。
   设计稿 §4 每把锁都写了「自证前提怎么写」，**照做**。
   ⚠️ 特别注意 **L6**：legacy 那一半修前本来就绿，
   ⛔ **不许把它伪报成「修前会红」**，也⛔ 不许只靠「新 check_id 尚不存在」制造形式红。
3. **⭐ 夹具自洽不算数**（F-5）：夹具必须走 `StageRunner.record(...)` 造**真实** accepted attempt，
   2/3 产物用 canonical serializer（`building_geometry_json` / `serialize_geometry` /
   `geometry_specs_markdown`）生成，⛔ 不许手写方盒坐标期望。

---

## 4. 施工顺序（设计稿 §5，⛔ 不许拆）

1. 先加 fixture assertion 与 F-20 锁，**确认定向红**。
2. 加入三态 resolver、稳定 check_id/status/reason、`test_check_parity.py` 的**具名**豁免
   （⛔ 不许用前缀或整 stage 批量豁免；现有 `_EXCLUDED_VALIDATE_CHECKS` 是逐条具名的，照那个格式）。
3. **⭐ 一个原子改动同时线程化三个消费口**（`check_correction` / `build_geometry` / `check_kernel`），
   并在 trust BLOCK 时**完全跳过 kernel**。**这一步不许拆。**
   ⚠️ 设计稿 §5 标为**最危险**的中间态就是「只给 build+kernel、没给 correction」
   ⇒ 2_modelling 可能通过并产生 digest，而 correction 仍 FAIL。
4. 跑验收（见 §5）。

---

## 5. 验收（⛔ 缺一不可，每项的原始输出都要落进执行日志）

1. **独立全量**：`python -m pytest -p no:cacheprovider -q -n 8 > /tmp/f20_full.log 2>&1; echo $? > /tmp/f20_full.rc`
   ⚠️ **观测通道纪律**：输出**直接重定向到文件**、**退出码单独落一个只属于该命令的文件**、
   ⛔ **中间不接任何下游管道**（`pytest | tee log | head` 会因 `head` 关 stdin ⇒ `tee` 收 SIGPIPE
   ⇒ **连带打断 pytest**，而你看到的「退出码 0」其实是 `head` 的）。
   **以汇总行 + 退出码为准，不看进度条。**
2. **逐把锁 neuter**：把修法还原成缺陷形态，**恰好哪几条转红？有无连带？有无该红没红？**
   逐把给结果，⛔ 不许只说「neuter 通过」。
3. **⭐ 真实产物验收（F-5 教训，⛔ 不可省）**：拿
   `case_tests/e2e_tests/sm21_anchor/run_2026-08-09_f18_e2e_verify`
   （**全项目唯一一份 v3 产物**）跑 `validate_case`，断言：
   `2_modelling` 不再是 `kernel build failed` · `geometry_digest` **非空** ·
   `approve_geometry` **真能签发检查点**。
   ⛔ **只读跑或跑在 `/tmp` 副本上**，不要污染那份真实 run。
4. **⭐ legacy 不回归（本单最容易踩的坑）**：
   - 两个 **golden 正基线**（`sm20_anchor/run_2026-06-15_baseline`、
     `sm21_anchor/run_2026-06-16_opus_e2e`，**两者都没有 `_run/run_manifest.json`**）
     ⇒ 断言**没有新增 blocker**，且 **geometry digest 与修前一致**。
   - **V1 账本 run**（盘上 11 份）⇒ 断言走 legacy 分支、不抛。
5. **V2 legacy targeted replay**（sol §8.4 保留项）：
   orchestrator 已机械测量「盘上有 accepted 记录的 4 个 V2 run，stage 根与 accepted 产物
   **逐字节全同、DIFF=0**」⇒ 权威切换**预期零行为变化**。
   ⚠️ **但那测的是今天的语料，不是不变量证明** ⇒
   **若你的 replay 发现任何一个历史 V2 run 的几何结果发生变化，停下上报差异与影响，
   ⛔ 不许悄悄回退 convenience copy。**

---

## 6. ⛔ 边界

1. ⛔ 不许读 `case_tests/test_baseline/gt/`。
2. neuter 实验**只在 `/tmp` 副本里做**，⛔ 不许动工作树。
3. ⛔ 不许 `git add` / `commit` / 切分支（由 orchestrator 提交）。
4. **备份**：动 `src/` 前先 `cp` 到 `backup/src_history/2026-08-10_f20_validate_case_v3_proof/`。
5. ⛔ **F-21 候选不在本单射程**（`approve_geometry` 只看 digest、不看 `res.blocked`）——
   **看到了也不要顺手改**，它需要独立调查定性。

---

## 7. 合法退出口（⚠️ 请务必使用）

**以下任一情况，请立刻停下如实上报，不要硬做：**

- **§2.0 那块砖造不出零窗 v3**（这是最可能发生的一条）；
- 设计稿某条状态表行**在现有代码里无法实现**，或与另一条要求冲突；
- 验收路径与本单某条要求互相冲突；
- §5#4 的 legacy 断言红了（**那说明设计或实现有真问题，不是让你去调断言**）；
- §5#5 的 replay 发现历史 V2 run 结果变化；
- 撞额度窗中断 ⇒ 停在哪里如实说。
  ⚠️ **纪律**：施工席中断后的自述**不可信**（已两次实证），orchestrator 一律以 `git diff` 复核 ——
  **如实说反而对你有利，不必也不要粉饰。**

**⛔ 派工方错误率 14/14。顶住不照做、如实上报，是本单期望的行为，不是失败。**
