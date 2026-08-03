# R1 批 B · r1 返工派工单（施工 = GLM · 累计式自包含）

- **日期**：2026-08-03
- **派工方**：orchestrator（端到端主控）
- **施工席**：GLM（`scripts/glm_code.sh`），额度 15:36（北京时间）复位
- **前置状态**：批 B r0 = `627efac`（+ `2bb189e` 里的 S-2 核心）。全仓 **2068 绿 + 10 xfail 零红**（orchestrator 独立复跑确认）
- **性质**：**返工轮**。派工单 [批 B/C 原单](2026-08-03_reading_ruler_r1_batchBC_dispatch.md) 与
  [裁定](2026-08-03_reading_ruler_r1_batchBC_ruling.md) 的**全部边界与禁止清单继续有效**，本单只加不减。

---

## 0. 先说清楚：r0 做得不差，问题出在同一个形状上

r0 的 wire 设计（保哈希联合类型）、四态归一化、13 条锁的断言质量都是**高于近几批平均**的，
`if e.dimensioned` 那个 truthy bug 还是施工方**自己发现自己修**的。

**但两轮审（orchestrator 轻门 + sol 交叉对抗审）独立收敛到同一个判断**：

> **修好的是「机制存在」，没修好的是「机制在所有真实路径上都生效」。**

下面 **7 条全部由 orchestrator 独立核实属实**（sol 的报告只跑到一半就被其平台的内容策略中断，
其结论是**读码推断、未跑探针**；orchestrator 已逐条核实，**核实结论以本单为准**）。

---

## 1. ⛔ 必修（7 条，全部已核实）

### R1-1（MAJOR）`flow` / `run` 标准入口：声明严格档、实际跑宽松档

**病灶原样存活在最常走的那条路上。** orchestrator 实跑复现：
`run_config.yaml` 声明 `regression / orthogonal_polygon` ⇒ 实际 **`exploratory` / orthogonal_polygon**。

- `run_stage.py:1810-1813`、`:1987-1991`：`capability_profile` 取自 `run_config`，
  **`run_profile` 只取 `args.run_profile`** ⇒ **同一次调用两个字段一个认 config、一个不认**。
- `_manifest_for_attempts:121` 只 `provision_view_manifest`，**不冻结 policy** ⇒ 落不下 `_run/run_policy.json`。
- `_draw_reading:196-205` 于是永远 `legacy_defaulted=True`，回落那个 `exploratory`。

**要求**：两个字段走同一来源规则；新 run 在 `_manifest_for_attempts` 一并走 `provision_run` 事务。

### R1-2（MAJOR）⭐ 配置里把档位**拼错一个字母**，会静默降档

**这条是 orchestrator 在核 sol 的 F-3 时挖到的，比 sol 报的那条更硬。**

`run_config.yaml` 写 `run_profile: regresion`（拼错）⇒ `_parse_run_profile`
（`run_config.py:206-216`）只发一个 `RuntimeWarning` 然后**返回 `None`**
⇒ 落回 CLI 默认 `exploratory`。**一个拼写错误 = 严格档静默消失。**

⚠️ 而**原派工单 §2.1 #5 逐字要求**：「strict/golden 对**缺失 / 非法 / 漂移**的 policy **fail-closed**」。
**「非法」这一档实现成了 warn + ignore ⇒ 这不是判断取舍，是规格未实现。**

**要求**：非法值在**新 run provisioning** 时 fail-closed（历史 replay 仍可只读容忍，但必须标 legacy、不得冒充）。

### R1-3（MAJOR）`validate_case` 这条路把四态**折回 bool**，还把结构化声明整个丢掉

**直接违反裁定追加约束 #1（「不得在任何一层折回 bool」）。**

`validation_run.py:129-142` 调 `dimensioned_view_names(case_dir)`，而该函数
（`case_metadata.py:51-73`）的 `add()` 对**非字符串直接 return** ⇒ **结构化对象声明被静默丢弃**；
随后折成 `view_metadata={"dimensioned": vj.stem in dimensioned_views}` = **一个 bool**，
且**根本没传 `dimensioned_state`**。

⇒ 一个 `declared_true` 的结构化声明，在 `validate` / `record` 路径上会**退回 N/A**。
sol 另指出 `evidence_preflight.py:201-227` 有同型折叠，**一并修**。

### R1-4（MAJOR）fail-closed 落在两件冻结产物**写盘之后** ⇒ 不是 fail-closed

`provision_run`（`run_provision.py:84-93`）顺序 = 写 manifest → 写 policy → **才**校验 applicability。
strict 档失败时，磁盘上**已经有**一份可用的 manifest + policy；而 isolation build/merge **不调这道 gate**
⇒ 「跑一次 provision、无视报错、继续走 isolation」即可绕过。

**这是本项目「非 None ≠ 成功」那条教训的同族**：**raise ≠ 没落盘**。

**要求**：校验前置，或失败时**不留下可用产物**（事务化）。

### R1-5（MAJOR）冻结的政策只接到 reading checker，没成为整个 run 的政策

`cmd_run/cmd_flow` 之后的 correction / modelling / grade 仍消费局部 `policy`
（`run_stage.py:254-309, 612-627, 1303-1323`）；typed scoring 的严格拒绝也由局部 `run_profile` 决定
（`:1413-1420, 1455-1473`）；`record_baseline.py:485-503` **重新构造 `RunPolicy`** 且 capability 默认 `rectangular`。

⇒ **同一个 run 内，检查、判卷、记账可以各认各的档。**
S-2 立项时写的是「让声明、发卷、合并、检查、落盘证明成为**同一个事务**」——现在只做到了「检查」这一环。

### R1-6（MAJOR）签字来源（provenance）记录了，但**没有任何校验**

`_structured_dimensioned_map`（`view_manifest.py:752-772`）**只校验 `source.reviewer` 非空**：
`image_sha256` / `date` / `basis` 一律不查，**`image_sha256` 从不与该 view 的真实图像 hash 比对**。
`source_hash = hash_obj(source)` 只能证明「这段声明后来没被改」，**证明不了它当初是真的**。
锁 fixture 用 `"0" * 64` 当图像 hash 并**期望通过**（`tests/test_reading_ruler_r1_batchB.py:61-71`）。

⇒ 一份伪造的「hortonyyx 已签字」声明可以畅通无阻。**而这正是 S-3 要建的那个东西。**

### R1-7（MINOR）配置与 CLI 冲突：实现是「静默取其一」，派工单要的是「直接报错」

`run_stage.py:2229-2233`。方向上选了更安全的一侧（config 赢），但属**未在执行日志披露的规格偏离**
（§5 只披露了 G4 那一处）。改成报错，或**写进执行日志**由 sol 挑战。

---

## 2. ⚠️ 需要你判断后回报的两条（**不许自行降级，也不许默默照做**）

### J-1 · G4 的 hash 收窄，现在证据指向「不安全」

sol 穷举了执行日志点名的四个 toggle，orchestrator 核实**其中两个成立**：

- `validation_scope=DOWNSTREAM_ONLY` ⇒ `validation_run.py:94-98` **整段跳过 0–4 的 gate① validators**（改变事实行集合）；
- `require_ep` ⇒ `:120-125` 增加一条 fail-closed 的 `downstream.build` ERROR（改变阻断面）。

⇒ 在**同一个 policy hash** 下，gate① 的事实与阻断可以变 ⇒ **P-1 命题不成立**。

**更要命的是那条兜底也没接**：`provision_run_policy` 接受 `context` 参数，
但**全仓唯一的生产调用者** `run_provision.py:85` **根本不传** ⇒
「其余 toggle 记录进 `run_policy.json` 作非哈希上下文」**从未发生**。
**这是本项目第 N 次「机制写了、没接线」。**

**你要回答**：hash 覆盖面回滚到 sol S-2 原文（含 validation/review 开关），还是保持收窄但把 `context` 真接上
并说明为何那两个 toggle 不需要 drift 保护？**给出理由，orchestrator 裁。**

### J-2 · 畸形输入被静默当 legacy

`dimensioned_views` 里**混合列表**（字符串 + 对象）在 `_structured_dimensioned_map`
（`view_manifest.py:736-741`）被**静默当 legacy**，对象声明被忽略，而不是拒绝畸形输入。
**你要回答**：拒绝，还是保留静默兼容？给理由。

---

## 3. 锁的要求（**这批 r0 的锁全部打在没出问题的那条路上，这次别再这样**）

r0 的 13 条锁**无一走 `cmd_run` / `cmd_flow`**，所以 R1-1 那条路今天在回归里是裸的。

每条 R1-x 都要有**摘掉即红、零连带**的锁，且：

1. **锁必须走真实入口**：R1-1、R1-2、R1-7 的锁**必须经过 argparse / CLI 命令函数**，
   ⛔ 不许像 r0 的 L-13 那样直接把 `None` 传给内部函数——**那条锁绕过了真实 CLI，所以它绿着而缺陷还在**。
2. **断言落在具体 check-id 行 + `checks.json` 头部字段**，⛔ 不得落在「返回值存在 / 总数变了」。
3. R1-4 的锁要断言**失败之后磁盘上没有可用产物**（不是只断言 raise）。
4. R1-6 的锁要断言**伪造的 `image_sha256` 被拒**（fixture 里那个 `"0"*64` 要么改真值、要么该被拒）。

---

## 4. 顺序与交付

**R1-1 → R1-2 → R1-3 → R1-4 → R1-6 → R1-7 → R1-5**（R1-5 最大、放最后，做不完就**停下上报**、不要硬塞）。
**J-1 / J-2 先回报再动手。**

- 执行日志续写 `AI_agent/logs/reviews/execution/2026-08-03_reading_ruler_r1_batchB_glm.md`
  的新 `## 6. r1 返工` 段（**别覆盖 r0 的记录**）。
- **做完一件存一件、先落骨架再补、每修完一条即本地 commit**（额度中断过两次，攒着写 = 白做）。
- 全仓 `pytest -q -n 6`（⛔ 不许 `-n auto`，⛔ 永远不许加 `-m`）。基线 **2068 passed + 10 xfailed 零红**。
- 每条锁做 neuter 自查并如实登记；⚠️「锁绿」≠「锁真绑」。
- **⛔ 不 push。⛔ 不碰 `gt/**` 与 sm24 `testdata_prompt.json` 任何字节。⛔ 不读 GT。**
- **批 C 在 r1 之后做**；你上次留的 28 行半截已 `git stash`（`batchC-wip-render-pixel-budget`），
  要用自己 `git stash show -p` 取。

**再遇欠规格边界，停下上报 —— 前两次你都做对了。**
