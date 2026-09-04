# 裁决 · **B4 返工 1** 跨家族审（Claude 家族复核席）

- **日期**：2026-09-03（第三程）· **复核方**：Claude · **施工方**：GLM
- **审对象**：`git diff 4ea103d..HEAD` = `5b1b0c4`(B-1) + `b15ee62`(B-2) + `1999687`(执行档)
- **改动面**：`src/agent/correction/opening_synthesis.py`（+328/-43）· `tests/test_b4_opening_synthesis.py`（+321/-21）
- **环境**：`__file__` 前后哨兵均落 `/tmp/b4rw_review_claude/src/...`（本工作目录）；全量 `-n 6`

## 裁决：**APPROVE** · **阻断 0 / 不阻断 3**

上一轮两条阻断，我**逐条独立重造了那两个反例**（⛔ 不信任被审的测试文件，自己在 scratchpad 用真实字节 + 运行时 monkeypatch 跑），**两条都已关闭**。全量 `3778 passed / 2 skipped / 13 xfailed / 0 failed`（585s，summary 行在，与自报一致，逐位闭合 `3756 + 22 = 3778`）。

---

## 一、逐条复核上一轮两条阻断（均**已复现并确认关闭**）

### B-1 「注册表 handler 不承重」→ **CLOSED**
上轮把 span 前缀指向语义不相干但存在的 `grid_units` ⇒ `WRONG_HANDLER_ACCEPTED / 债照销`。
**我把同一变异运行时重放**（`mut_b1.py`，直接改全局 `DEBT_REDEMPTION_REGISTRY`）：

| 攻击 | 上轮 | 本轮实测 |
|---|---|---|
| runtime：`gate=grid_units` 跑 `synthesize_openings`（带真实 span 债 + South 身份）| 债照销 | **响亮失败 `DEBT_GATE_CALL_FAILED` gate=grid_units，产物不存在 ⇒ 零销账** ✅ |
| import-time：同变异后调 `_assert_registry_well_formed()` | —— | **响亮失败 `DEBT_REGISTRY_GATE_SIGNATURE_MISMATCH`** ✅ |

**病根已修在结构上**：`synthesize_openings` 不再硬调门，而是 `redemption_row_for_premise(前提)` 查表取 gate **再经表调用**（`opening_synthesis.py:822-848`）。gate 列真承重——指向错的现有 callable，import 齿（签名 bind）先红、真调用点再红。「名字存在且 callable」这条上轮的放行路径已堵死。

> ⚠️ 见 §不阻断-1：门是**签名齿**不是**语义齿**，仍有一个我实测证明的盲区，但不构成阻断（下详）。

### B-2 「销账没绑定源实例」→ **CLOSED**
上轮用 East/West 真实字节各产一张债、只跑 South 的门 ⇒ **两张真实债一起被销**。
**我用 B3 adapter 从三张真实字节独立重造**（`mut_b2.py`，`adapt_as_drawn_elevation` 出真 sha）：

```
east : ref.input_id=input_east  sha=6efa55b7c697
west : ref.input_id=input_west  sha=d7089513cfec
south: ref.input_id=input_south sha=0e76a5c29f47   ← 三个 sha 互异
```

| 场景 | 实测 |
|---|---|
| 三张真实债进 **South** run，声明 South 身份 | `retired = (…input_south,)` —— **只销 South，East/West 保留** ✅ |
| 交叉：声明 **East** 身份，只喂 South 债 | `retired = ()` —— **身份不符零销** ✅ |

**绑定锚在 `affected_refs` 的 `source_output_sha256` 上，不在 `debt_id` 后缀**（`ElevationSourceIdentity.binds`，`opening_synthesis.py:410-418`）。而 sha 逐 facade 互异（实测），故它足以区分「哪一个源实例」。上轮的 prefix-only 击穿路径已关。

---

## 二、⭐⭐ 派工方那次签字：**签得对，⛔ 不该翻，不必升 schema**

> 问：`affected_refs` 够不够承担「绑定到本次核过的那一个源实例」？

**够。正面回答：够，且是当前无 schema 改动下能做到的最强绑定。** 理由：
1. `ArtifactPointerV1` **已带** `source_output_sha256`，而这个 sha 在 **B3 adapter 处是 `hashlib.sha256(raw).hexdigest()` 真从冻结字节算出**（`evidence_adapters.py:649`）。它就是**源实例的身份**。
2. 三张真实 facade 债的 sha **实测互异**（上表）⇒ 用 sha 比对即可把 South 与 East/West 分开，`binds` 正是逐字段比 `input_id + contract + sha256`。
3. 因此「绑定到本次核过的那一个源实例」这件事，**`affected_refs` 已经承担得起**，无需 T4-a 的结构化 obligation/owner 字段。T4-a 解决的是**另一个**问题（把 owner/义务从 `debt_id` 前缀 + 自由文本升格为一等字段），与「源实例绑定」正交 ⇒ 升 schema 不但没必要、也修不到本条要害。

**⇒ 你的签字成立。零 schema 改动、零哈希扰动、把 T4-a 留给用户拍板，三条理由都对。**

⚠️ 一个**必须点明的边界**（不推翻签字，只是把它的射程说准）：`binds` 证明的是
「**债自报的源 sha == 本 run 自报的源 sha**」，**两者都是调用方声明**的。它证明「债与本 run 指的是同一个被声明的源」，**不证明「这个声明就是真字节」**——那是 §三 的信任边界，与「够不够绑定实例」是两件事，且**同样不是升 schema 能解的**。

---

## 三、施工方自报最薄弱：`elevation_source` 信任边界

> 自报：「dict 无字节可重哈希，身份无法机械重算。」

### ① 本轮可接受吗？——**可接受，且命名诚实**
B4 收到的是 `elevation_doc: dict`（已解析、无字节），它**本就无法**重算 sha ⇒ 这不是缺陷、是事实。而它依赖的 sha **在上游 B3 adapter 处是真字节 hash**，`binds` 的比对**内部自洽**（债 ref 的 sha 必须等于声明源的 sha）。这是**不重算字节前提下能达到的最强形态**。科研档 P0 下，接受。

### ② 它给的出路够不够？——**方向对、必要，但目前是散文，不是门**
出路「B5 接线单写死：身份从 `source_artifacts[0]` 提取，⛔ 不许手拼」**成立且必要**——因为 `source_artifacts[0].source_output_sha256` 正是那个真字节 hash（`evidence_adapters.py:651-654`）。测试 `test_b3s_real_span_debt_is_redeemed_on_real_bytes` 就是这么做的（`raw → adapt → meta=source_artifacts[0]`，`elevation_doc=json.loads(raw)`，同一份 raw）。
**但**：这条纪律现在**只是一句 prose**。若 B5 手拼、或传入的 `elevation_doc` 与被 hash 的字节**不是同一份**，B4 里**没有任何门**会红。这正是本项目反复交的学费——**prompt / 注释不是防线**。

### ③ 现在要不要补门？——**本轮不补（越界 + 无活消费者），但 B5 接线单必须把它变成门**
- **本轮不补**：要机械重算就得让入口收**字节而非 dict**（`elevation_doc: dict → raw: bytes`），这是**改本体/接口**，越 §四 红线；且当前没有 B5 接线在消费它，属「不做也能跑能读」（§0.1）。
- **B5 接线单必须做**：把「防手拼」从散文升成**类型层不可表示**——例如给 B4 加一个 `from_frozen_bytes(raw, …)` 构造入口，**用同一份 raw 的同一个 hash 同时产出 `elevation_doc` 与 `elevation_source`**，让「doc 与身份不一致」这个状态**根本构造不出来**（对齐条目 [gate-measures-right-but-carrier-gets-swapped]：有效解是让那条路在类型层不存在，不是加词法门）。⇒ 记为随 B5 travel 的显式要求。

---

## 四、越界核查（§四）——**未越界**
- `git diff --exit-code 4ea103d..HEAD -- src/agent/correction/evidence_contract.py` **为空** ✅（schema 一字节未动）
- `evidence_adapters.py` 亦 **UNCHANGED**；本轮源码**只**改 `opening_synthesis.py` 一个文件。
- 未见「0 对」加对齐/吸附/阈值；未见重做本体（等式门/逐边厚度/区间配对/前提命名均沿用上轮已过审形态）。

---

## 五、验收六条（照返工单 §五逐条）

| # | 项 | 结论 | 证据 |
|---|---|---|---|
| 1 | 处理器那一栏真承重 | ✅ | `mut_b1`：`gate=grid_units` ⇒ `DEBT_GATE_CALL_FAILED`（runtime）+ `..._SIGNATURE_MISMATCH`（import），零销账 |
| 2 | 销账绑定源实例 | ✅ | `mut_b2`：三真债进 South，只销 South；跨身份零销；锚在 sha 且三 sha 互异 |
| 3 | 两条都有常驻锁且有牙 | ✅ | `test_registry_rows_are_wiring_not_decoration` + `test_retirement_binds_to_the_source_instance_real_bytes` 均绿；我独立重放同样红/绿 |
| 4 | schema 一字节没动 | ✅ | `evidence_contract.py` diff 空 |
| 5 | 上轮过审五项不退化 | ✅ | 等式门/逐边厚度/区间配对/前提命名对应测试全绿；B4 文件 22/22 passed |
| 6 | 全量绿逐位闭合 | ✅ | `3778 passed / 0 failed`，summary 行在；`3756 + 22 = 3778` 逐位闭合；`-n 6`、前后 `__file__` 均本树 |

**附**（§三 ⚠️）：返工单 + 上轮裁决两份管理文件由**首笔 `5b1b0c4` 带入、范围内无任何后续提交再改**。⚠️ 我**无主控预置副本**做字节级比对，故「一字未动 vs 预置版」这一句**未能机械复现**；能确认的是范围内它们是一次性 add、之后零编辑。

---

## 六、不阻断 findings（3 条）

### 不阻断-1 · ⚠️ B-1 的门是**签名齿**不是**语义齿**（我实测证明的盲区）
`_assert_registry_well_formed` 只校验 gate 是「本模块具名函数 + 能 bind 三关键字」，**不校验它就是 `span_equality_gate`**。我枚举过：**当前模块内唯一能 bind `(chain_total_mm, skin_lo_u, skin_hi_u)` 的函数就是 `span_equality_gate`** ⇒ 上轮那把变异（`grid_units`）必被签名齿挡住，**今天不可达**。
但 `mut_b1` 攻击3 实测：若**新增**一个同签名但语义全错的模块级函数（`def fake_gate(*, chain_total_mm, skin_lo_u, skin_hi_u): return 999999`）当载体，**import 齿放行、等式从不执行、债照销**（`retired=(…input_south,)`，`chain_total_u=999999`）。
**定性**：这是「量得准但载体能被换掉」病族的一个残余面——不过换载体需要**有人往本模块写一个同签名的错门并接线**，门槛远高于上轮「任意现有 callable 都放行」。**当前零可达实例，故不阻断。** 建议：将来往注册表加第二个门时，要么让门**自证语义**，要么把「合法 gate 集」显式声明成 allowlist，别只靠「签名唯一」这个巧合承重。

### 不阻断-2 · ⚠️ 信任边界在 B5 仍是散文（见 §三②③）
`elevation_source` 的一致性目前无门。**B5 接线单必须**把「身份从 `source_artifacts[0]` 提取」升成类型层约束（`from_frozen_bytes(raw)` 单入口，doc 与 identity 同源同 hash），否则「doc 与声明身份不一致」永远无人拦。**归入随 bundle travel 的显式债。**

### 不阻断-3 · ℹ️ 绑定的射程要在文档里说准（见 §二 ⚠️）
`binds` 证明「债自报源 == run 自报源」，两侧皆调用方声明。产物 docstring（`opening_synthesis.py:403`「a trust boundary the caller signs」）已诚实标注，**无需改**；此条仅提醒下游消费者别把它读成「已机械验证源真伪」。

---

## 复现物（scratchpad，非仓库）
- `mut_b1.py` —— B-1 三攻击（grid_units runtime / import + fake_gate 同签名替身）
- `mut_b2.py` —— B-2 三真债 + 跨身份 + 伪造 ref

**签署**：Claude 家族复核席 · 2026-09-03am
