# R1 批 B · r1 返工 · orchestrator 对 J-1 / J-2 的裁定

- **日期**：2026-08-03
- **上游**：[r1 返工派工单](2026-08-03_reading_ruler_r1_batchB_rework_dispatch.md) §2 ·
  施工席回报见执行日志 `## 6. r1 返工`（commit `91ac2ea`）
- **性质**：裁定。与派工单冲突处以本文为准；其余部分不变。

---

## 0. 先记一句：这次回报的形态是对的

施工席**先回报、再动手**，并把「依赖裁定的」与「不依赖裁定的」明确切开
（R1-1 的 context 接线暂传 `None` 标 TODO、**不默默照做**），其余六条照常推进。
**这正是派工单要的形态，记正分。**

---

## 1. J-1（G4 hash 收窄）：**采纳 (b) 保持收窄 + 把 `context` 真接上**，但附一条改判

### 1.1 施工席的反驳成立

它主张：`validation_scope` / `require_ep` 只在 `validate_case` 这条路上改变事实，
而该路径**不读 `run_policy.json`、不 stamp policy hash**，不属生产 gate① 口径。

**orchestrator 独立核实 ⇒ 成立，且仓库里本来就有制度化证据**：
`tests/test_check_parity.py:24` 的注释逐字写着该文件的存在意义是
*"between inline production gates and validate_case's offline audit surface"*
—— **本项目早就把 `validate_case` 当作与 inline 生产门并列的「离线审计面」在单独管**。

⇒ 把 `validation_scope` / `require_ep` 塞进 gate① 的 policy hash，会把离线审计面的开关
耦合进生产冻结事务，产生无意义的 drift 拒绝。**sol 的 P-1 证伪路径在技术上正确，
但它证伪的是「这些 toggle 能改变某个 checks 产物」，不是「能改变被 hash 保护的那个事务」。**

### 1.2 但兜底必须真接上（这条不打折）

`provision_run_policy` 接受 `context`，**全仓唯一生产调用者 `run_provision.py:85` 从不传**
⇒ 「其余 toggle 记录进 `run_policy.json` 作非哈希上下文」**从未发生**。
**收窄的正当性完全建立在「其余项有记录、只是不参与 drift 判定」之上；记录不存在，收窄就成了单纯的丢信息。**

**⇒ 要求**：`context` 真接上（至少含 `validation_scope` / `require_ep` /
`confirmation_policy` / `judge_enabled` 的实际取值 + 来源），并有一条锁断言它落盘且**不进 hash**。

### 1.3 ⭐ 改判：核 J-1 时发现的更硬的一条 —— 并入 R1-5

施工席说「`validate_case` 从调用方拿 policy」是对的。**问题在于那些调用方传了什么**：

| 调用方 | 传的 policy | 后果 |
|---|---|---|
| `step_orchestrator.py:478` `confirm_geometry` | **`RunPolicy()` 全默认** | 人工几何确认门恒按 `exploratory` + `rectangular` 跑 |
| `step_orchestrator.py:493` `geometry_is_approved` | **`RunPolicy()` 全默认** | 同上 |
| `record_baseline.py:498` | `RunPolicy(require_ep=…, run_profile=…)`，`run_profile` 默认 `"exploratory"`、capability 缺省 | 记账按另一个档 |

⇒ **人工几何确认这道门，无论该 run 声明什么档位，永远在最宽松档上判。**
这比 sol 报的 R1-5 更靠前 —— 它落在**人要签字的那道门**上。

**⇒ 并入 R1-5，且 R1-5 的优先级从「最后、做不完可停」上调为「必须做」**：
`confirm_geometry` / `geometry_is_approved` / `record_baseline` 必须消费**冻结的**政策，
不得自造 `RunPolicy()`。**⛔ 若做不完，停下上报，不得静默留着。**

---

## 2. J-2（混合列表静默当 legacy）：**采纳「拒绝（raise）」**

理由与施工席一致，orchestrator 补一条：这与 **R1-2「非法 ⇒ fail-closed」是同一条规格**
（原派工单 §2.1 #5），不是两件事。**畸形输入被静默降级 = 声明被丢掉而无人知道**，
正是本批要根除的形状。

**⇒ 要求**：混合列表 raise；错误信息要指出**哪一项**不合形态。有锁。

---

## 3. 对 r1 剩余排期的影响

- **R1-1 context 接线**：按 §1.2 接上（不再是 TODO）。
- **R1-5**：范围扩大 + 优先级上调（§1.3），**不再是「做不完可以停」的那一条**。
- 其余（R1-2 / R1-3 / R1-4 / R1-6 / R1-7）不变。

⚠️ **R1-3 的定性同步说明（免得与 §1.1 打架）**：`validate_case` 属离线审计面，
**但「离线」不等于「可以把四态折回 bool」** —— R1-3 修的是**信息保真**（结构化声明被整个丢掉），
不是档位口径。两者不冲突，**R1-3 维持 MAJOR、照修**。
