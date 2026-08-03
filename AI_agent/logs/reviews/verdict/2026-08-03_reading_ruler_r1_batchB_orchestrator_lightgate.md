# R1 批 B · orchestrator 轻门（独立全量 + 亲核 diff + 独立复现）

- **日期**：2026-08-03
- **被审对象**：`627efac` `8.03_ReadingRulerR1BatchB_S2Freeze_S3Applicability`（施工 = GLM-5.2）
  + 其前置半截 `2bb189e`（S-2 核心 `run_policy_freeze.py`，同为 GLM 产出、由 orchestrator 代为保命提交）
- **执行日志**：[2026-08-03_reading_ruler_r1_batchB_glm.md](../execution/2026-08-03_reading_ruler_r1_batchB_glm.md)
- **性质**：orchestrator 轻门 = **唯一权威门**（`AI_agent/CLAUDE.md` §5#8）。本文不替代 GPT 侧（sol）交叉对抗审。

---

> **⚠️ 本文写于 sol 交叉审出结果之前。判定已升级为 REWORK（6 MAJOR + 1 MINOR）**
> —— sol 的报告跑到一半被其平台内容策略中断，但已交出 5 条候选 MAJOR；
> orchestrator 逐条独立核实**全部属实**，并在核实过程中另挖到一条更硬的（配置里档位拼错一个字母 ⇒ 静默降档）。
> **合并后的完整必修清单与裁定见
> [r1 返工派工单](../request/2026-08-03_reading_ruler_r1_batchB_rework_dispatch.md)**（本文 §1/§2 为其中两条）。

## 0. 总判定（初版）：**REWORK（1 MAJOR）** —— 机制正确、锁质量高，但**没有关上被点名的那条病灶在标准 SOP 路径上的出口**

施工质量整体**高于近几批平均**：wire 形态的保哈希设计干净、`unknown`/`declared_false`/`legacy_default`
四态不折叠贯彻到位、13 条锁的断言全部落在具体 check-id 行上（没有再犯「断言落在返回值存在性上」的老毛病）、
缺口登记诚实（§5 四条，其中第 4 条正是本轮 MAJOR 的自曝）。

**但**：批 B 的立项理由是「**声明的严格档从未真正执行**」。本轮修复关上了 isolation 路径与显式
`provision` 路径，**没有关上 `flow` / `run` 这条标准 SOP 路径** —— 而 `flow` 正是本项目
（`CLAUDE.md` §5 跑测铁律）规定的唯一入口。**⇒ 病灶在最常走的那条路上仍然可复现。**

---

## 1. ⛔ MAJOR-1 · `flow` / `run` 新建 run 仍然「声明 regression、执行 exploratory」

### 1.1 复现（orchestrator 独立实跑，非读码推断）

构造一个只有 `run_config.yaml` 的 run 目录，声明 `run_profile: regression` + `capability_profile: orthogonal_polygon`，
然后**逐字复刻 `cmd_flow` 的策略构造**（`scripts/tool_scripts/run_stage.py:1983,1987-1991`）：

```
run_config.yaml declares : regression / orthogonal_polygon
flat-flow policy         : exploratory / orthogonal_polygon      ← run_profile 掉了
frozen policy record     : legacy_defaulted= True
=> value reaching check_reading_stage: exploratory
```

### 1.2 机制（三段，逐段可核）

1. **`cmd_run` / `cmd_flow` 根本没读结构化 `run_profile`**
   （`run_stage.py:1810-1813`、`:1987-1991`）：
   ```python
   run_config = load_run_config(run_dir)
   policy = _make_policy(
       run_profile=args.run_profile,                                    # ← 只认 CLI
       capability_profile=(run_config.capability_profile or args...),   # ← 却认了 config
   )
   ```
   **同一次调用里两个 profile 一个认 config、一个不认** —— 这个不对称本身就是缺陷的指纹。
   `--run-profile` 的 argparse 默认值是 `"exploratory"`（`:2255-2260`），**不是 None**
   ⇒ 操作者不显式传参，声明的 regression 就被静默丢弃。
2. **新 run 不冻结 policy**：`_manifest_for_attempts`（`:121`，`run`/`flow`/`resample` 的建 attempt 入口）
   只 `provision_view_manifest`，**不调 `provision_run_policy`** ⇒ 落不下 `_run/run_policy.json`。
3. **于是 resolver 走 legacy 兜底**：`_draw_reading`（`:196-205`）拿到
   `legacy_defaulted=True` ⇒ 回落 `policy.run_profile` = 上面那个 `exploratory`。

### 1.3 为什么这条是 MAJOR 而不是登记债

- 派工单 §2.1 #3 逐字要求「**flat-flow 也调用同一个 resolver，不再各自拼默认值**」。
  本轮只做了**读**的一半（`_draw_reading` 调 resolver），**写**的一半（新 run 冻结 policy）没做
  ⇒ resolver 每次都返回 legacy 兜底，等于没接。
- 施工方在执行日志 §5 #4 已诚实登记此缺口，但结论写的是「isolation + cmd_provision 两条路径已足以**验证 S-2 契约**」。
  **验证契约成立 ≠ 病灶被关上**。批 B 的验收标准是后者。
- **零锁覆盖**：13 条锁全部打在 isolation 路径与 provisioning 上，**没有任何一条锁走 `cmd_run`/`cmd_flow`**
  ⇒ 这条路今天回归里是裸的，改坏了不会红。
- 08-02 那次事故的两个字段里，**`capability_profile` 这一半已经被修好了**（config 生效），
  `run_profile` 这一半没有 ⇒ 同一份 `run_config.yaml` 现在会产出「orthogonal_polygon + exploratory」
  这种**半生效**状态，比全不生效更难被发现。

### 1.4 要求（r1 返工，派施工席，⛔ orchestrator 不亲手改）

1. `cmd_run` / `cmd_flow` 的 `run_profile` 与 `capability_profile` **走同一条来源规则**。
2. 新 run 在 `_manifest_for_attempts` 里**一并冻结 run policy**（与 `cmd_provision` 同一 `provision_run` 事务），
   使 resolver 真的有东西可解。
3. **补一条锁**：`run_config.yaml` 声明 regression ⇒ 不传 CLI 参数走 `flow` ⇒
   `checks.json` 头部**必须**是 `regression` 且 blocker 恰为四条 closure。
   断言落在 **check-id 行 + 头部字段**上，⛔ 不得落在「返回值存在」。
4. **顺带裁一条本轮发现的规格偏离（见 MINOR-1），一并处理。**

---

## 2. ⚠️ MINOR-1 · 配置与 CLI 冲突是「静默取其一」，派工单要的是「直接报错」

`cmd_provision`（`run_stage.py:2229-2233`）实现为「config 优先、CLI 兜底」。
派工单 §2.1 #1 逐字写的是「**配置与 CLI 冲突直接报错，不得静默取其一**」。

方向上施工方选了更安全的一侧（config 赢），**但这是规格偏离，未在执行日志披露**
（§5 只披露了 G4 那一处偏离）。r1 一并处理：要么按派工单报错，要么把偏离**写进执行日志**由 sol 挑战。

---

## 3. ✅ 已独立核实成立的部分

| 项 | 核实方式 | 结论 |
|---|---|---|
| **保哈希铁律** | `test_real_manifests_byte_identical` 钉死 sm24 `459513f1…`（= GT 侧车 `base_view_manifest_sha256`）与 sm21 `f52ca79c…` | ✅ 有锁、且锁的是**真实件**不是 fixture |
| **联合类型分支** | 读 `_structured_dimensioned_map`：absent / 茎字符串 ⇒ 返回 `None` ⇒ 走原 bool；仅 list-of-objects 激活结构化 | ✅ 真实 case 走不进对象分支 |
| **四态不折叠** | `dimensioned_state()` 把 bool `False` 归一到 **`legacy_default`** 而非 `declared_false`；`_evidence_meta` 带到 `checks.json` | ✅ 裁定追加约束 #1/#2 都落到位 |
| **truthy bug** | 施工方**主动发现并修正** `if e.dimensioned` 对 `DimensionedApplicability` 对象恒真（结构化 `declared_false` 会被误判成 dimensioned） | ✅ 这是清单外自主发现，记正分 |
| **gt / testdata 零触碰** | `git show --stat 627efac`：7 个文件，无 `gt/**`、无 `testdata_prompt.json` | ✅ |
| **未 push** | 分支未推 origin | ✅ |
| **neuter 自查** | 8 条，其中 L-12/L-20/L-22 零连带即红；L-10/L-11、L-21、L-23 的连带均落在**共享同一实现**上，说明成立 | ✅ 待独立复跑（见 §5） |

### 3.1 关于 L-13 「neuter 单层不红」

施工方如实登记：`run_profile=None` 被三层挡（显式 raise / `_build_record` 白名单 / pydantic `Literal` 类型），
摘掉第一层仍绿。**我接受这个解释**——摘单层不红是因为**类型系统本身就是那道门**，
这比单点 raise 更强，属于「多层冗余」不是「假锁」。
⚠️ 但 sol 审时应验证第三层真的挡得住（构造 `run_profile='bogus'` 与 `None` 两种输入）。

---

## 4. 独立全量测试

`pytest -q -n 8`（orchestrator 独立复跑，⛔ 无 `-m` 过滤，工作树 = `627efac` 干净态，
批 C 半截改动已 stash）：

```
2068 passed, 10 xfailed, 150 warnings in 403.06s (0:06:43)
```

**⇒ 与施工方自报（`-n 6` ⇒ 2068 passed + 10 xfailed 零红）逐数字一致。**
基线 2055 + 本批 13 条新锁 = 2068，**零回归**。

---

## 5. 尚未做完的轻门动作（登记，不当已完成汇报）

1. **独立复跑每一条 neuter**（派工单 §6 要求）—— 本轮尚未做，待 r1 之后连同新锁一起做。
2. **批 C 未开工**：施工席在 `render_vector_to_png.py` 上留了 28 行半截改动（像素预算），
   已 `git stash`（`batchC-wip-render-pixel-budget`）+ 补丁副本存 scratchpad，未评估。

---

## 6. 运维记录

施工席 **GLM 撞 5 小时额度上限退出**（`API Error: 429 · 已达到 5 小时的使用上限，2026-08-03 15:36:10 重置`），
批 B 已提交、批 C 刚起头。**「做完一件存一件」这条纪律这次生效了**：
上一轮同样的中断造成零交付，这轮中断只损失了批 C 的 28 行。
