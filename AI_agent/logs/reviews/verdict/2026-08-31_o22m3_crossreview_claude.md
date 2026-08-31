# 跨家族审裁决 · ②-2 **模块 3** correction 证据双 adapter（legacy / as-drawn）

- **裁决**：**APPROVE-WITH-FINDINGS**（阻断 **0** · 不阻断 **4**）
- **被审对象**（⛔ 未提交，在工作树）= `src/agent/correction/evidence_adapters.py`（新）+ `tests/test_o22m3_evidence_adapters.py`（新）
- **基线** = `31f873d` · **施工方** = GLM 家族 · **审阅方** = Claude 家族（只读席位 · 换人审 · 恒升一档）
- **派工单** → [../request/2026-08-31_o22m3_evidence_adapters_dispatch.md](../request/2026-08-31_o22m3_evidence_adapters_dispatch.md)（含 §六～§八 补充裁决）
- **执行档** → [../execution/2026-08-31_o22m3_evidence_adapters_execution.md](../execution/2026-08-31_o22m3_evidence_adapters_execution.md)
- **口径** → [2026-08-30_o22_evidence_contract_gpt_design.md](2026-08-30_o22_evidence_contract_gpt_design.md) §4.1/§4.2/§4.3/§5.1/§5.2/§5.2.1/§8.3/§9.1
- **上游模块 2** → [2026-08-31_o22m2_crossreview_claude.md](2026-08-31_o22m2_crossreview_claude.md)（阻断 0 / 不阻断 6；F-1/F-2 正被 GLM 返工补）
- **复核环境**：把被审两文件拷 `/tmp/o22m3_review/`，adapter 经 `importlib` 从 `/tmp` 副本加载，`from src...` 解析到主树；所有变异（neuter）只改 `/tmp` 副本，⛔ 未在主树跑变异 · ⛔ 未 `pip install -e .` · ⛔ 未 `git add`/`commit` · ⛔ 未改被审对象。跑真实套件 `-n 4`。
- **主控权威全量**：`31f873d` = 3471 passed / 13 xfailed / 0 failed（未复跑，采信主控读数）。

---

## 〇、总述

模块 3 是**两个生产 adapter**（吃冻结 bytes、出已过模块 2 不变量 1–8 的 bundle），零接线。我独立复核后确认施工方**没有虚报**：三份真实产物各自闭合、两份 legacy 全落 unknown、pin 的模块 3 一半接掉、零自造配对、切段改判正确。主控点名的四处**逐处亲手打过**、外加**我自造第五处**（pairs 非空路径的孤儿面闭合），全部站得住。真实套件我在主树 `-n 4` 复跑 **21 passed / 6.50s**。

判 **APPROVE-WITH-FINDINGS** 而非 REWORK 的依据：所有不阻断项**今天零流量**（as-drawn disposition 仍 `KNOWN_NOT_CONSUMED`，无人 import adapter），实害只在接线日；四条不阻断中两条是**记账/测试覆盖建议**、一条是**环境（工作树三席交织）**、一条是施工方**自报**的下游债缺口。给定零接线 + 权威全量 3471 绿，不构成阻断。

**四个主控点名 + 一个自造，逐条结论先行**：

| 打击点 | 结论 | 一句话 |
|---|---|---|
| ① legacy note 盲读（机械核） | ✅ **站得住** | 改写全部 note 为矛盾的「中线/外皮」，basis 全程 `unknown`、evidence_ref 全 None |
| ② 闭合表从产物重算 + sm24 78/98 | ✅ **闭合真实、无隐藏** | 三份独立重算全闭合；78 ambiguous 全在候选图里、各带一条 debt（记账见 F-2） |
| ③ 零自造配对 + 别的生墙路径 | ✅ **无别的路径** | 三处 claim 分别只来自 `pairs`/`solid_band_walls`/`unpaired_wall_faces` 桶；候选图循环只解引用 |
| ④ 切段改判 + 同形锁的牙 | ✅ **改判对 + 锁有牙** | 归模块 4 与设计稿 §5.1/§十/§9.1#4 一致；过 validate 的形态差被同形锁咬红 |
| ⑤（自造）孤儿面闭合 | ✅ **兜得住**（牙在模块 2 validate） | pairs 非空 + 孤儿面 → `FACE_WITHOUT_DISPOSITION`；记账见 F-1 |

---

## 一、⛔ 阻断项：**无**

---

## 二、主控点名四处的复现与读数

### 点名 ① · legacy basis 只认结构化 `geometry.basis`、note 一个字不读（机械核实）
- **做法**：不读 docstring；拿 f9 与 sm22 两份**真实** legacy 产物，把**每一条** `pen=="wall"` 笔画的 `note` 改写成互相矛盾的强信号（偶数条写 `centerline 中线 THIS IS THE CENTERLINE`、奇数条写 `outer skin 外皮线 wall_face`），basis 结果必须不变。
- **复现命令与读数**（`/tmp/o22m3_review/`，in-memory 改写、不落盘）：
  ```
  == f9:   10 wall strokes, base bases=['unknown']
     after rewriting all notes to contradictory centerline/outer_skin:
     bases=['unknown'], evidence_refs=['None']
  == sm22: 10 wall strokes, base bases=['unknown']
     after rewriting all notes:  bases=['unknown'], evidence_refs=['None']
  PROBE1 PASS: notes never touched basis
  ```
- **判定**：**成立**。代码只在 `"basis" in geometry`（结构化键）时才升格（adapter L575），note 从不进入任何 basis / debt 措辞 / claim_id 路径。正控在套件里（`test_legacy_structured_basis_declaration_is_honoured`：合成 `geometry.basis="centerline"` 升格且带 evidence_ref；域外值 `"middle"` → `LEGACY_BASIS_DECLARATION_INVALID` 响亮）——即 `unknown` 是机械默认不是盲默认。设计稿 §8.3「禁解析自由 note」被逐字兑现。

### 点名 ② · 闭合表从产物重算（⛔ 不回读 adapter）+ sm24 78/98 比例判读
- **做法**：直接从三份原始 JSON 重算，把 paired 面按**集合**计数、并检查跨桶重叠与野键；⛔ 全程不碰 adapter 输出。
- **复现读数**：
  | 产物 | 面线 | claimed(面) | non_wall | ambiguous | 求和 | 跨桶重叠 | 野键 |
  |---|---|---|---|---|---|---|---|
  | sm25_1f | 49 | 44（22 pair×2）| 5 | 0 | **49 闭合** | 无 | 无 |
  | sm25_2f | 46 | 43（21 pair×2 + 1 unpaired）| 3 | 0 | **46 闭合** | 无 | 无 |
  | sm24_1f | 98 | 20（8 pair×2 + 4 solid）| 0 | 78 | **98 闭合** | 无 | 无 |
  - 与执行档 §二的逐份计数**完全吻合**，且我这份是独立重算（集合去重 + 重叠/野键双查）。
- **sm24 的 78/98 判读**（主控要我判「掩盖了什么」）：
  ```
  sm24: dispositions={claimed_wall:20, ambiguous:78}; ambiguous_face debts=78
  ambiguous faces that appear in pair_candidates: 78/78 (共 1185 候选)
  walls channel: present
  ```
  - **没有掩盖**：78 个 ambiguous 面**全部**出现在候选图里 —— 即模型**有**候选配对却**诚实弃权**（不是把配不上的塞进 ambiguous 装完整）；每个都落一条 `ambiguous_face` debt，validate 的 `AMBIGUOUS_WITHOUT_EVIDENCE_DEBT` 门逐条兑现。闭合是**真的**，adapter 未制造任何 ambiguous（逐字读 `hyp['ambiguous_face_lines']`）。
  - **⚠️ 但有一处解读风险（不阻断，见 F-2）**：闭合**算术**成立、`walls=present` **技术上**为真（20 面真被 12 堵墙认领），二者合起来容易被下游/审读成「sm24 墙已充分读」，而实际 **80% 的面线是未决 debt**。这是**诚实翻译**、不是 adapter 缺陷（设计稿 §7.2 把「ambiguous 可能改拓扑 ⇒ strict 阻断」交给模块 4+ profile）。

### 点名 ③ · 零自造配对 + 有没有别的路径从候选图生墙
- **复现读数**：
  ```
  Probe3a 清空 pairs(=None) -> PAIRS_SELECTION_ABSENT | remedy=reperception_required | candidates=303
  Probe3b 空选(pairs=[]) + 桶未覆盖 -> FACE_WITHOUT_DISPOSITION（响亮，未静默生墙）
  ```
- **「别的路径」逐一排查**（代码 + 实测）：三处 claim 构造点的**唯一来源**——
  - `PairedFacesWallClaimV1` ← 只在 `for j, pair in enumerate(pairs)` 内（adapter L326）；
  - `SolidBandWallClaimV1` ← 只在 `solid_band_walls` 桶（L376）；
  - `SingleFaceWallClaimV1` ← 只在 `unpaired_wall_faces` 桶（L396）。
  候选图循环（L255–270）**只做两件事**：解引用 `face_a/face_b` 做完整性校验（`PAIR_CANDIDATE_REFERENCES_UNKNOWN_FACE`）+ 建 `candidate_at` 供**已选中** pair 找指针 `k`。**没有任何一条路径**让候选图生出 solid_band 或 single_face 或 paired。
- **判定**：**无别的生墙路径，成立**。派工单 §一.3「候选图不是第五种墙」被兑现。

### 点名 ④ · 切段改判归模块 4 是否对 + 同形锁（等长/不等长同形）的牙
- **改判判定**：**对**。设计稿三处一致把「切段」指派给模块 4 compiler——§5.1 编译管线第二步「segment evidence（保留双面共同段与单面余段）」、§十「模块 4 = ref resolve、**切段**、中线/候选/厚度 IR」、§9.1#4「验证**双面余段不丢**」。claim 类型层**零几何值**（模块 2 机械锁），「哪一段是余段」是计算结果、**本层无类型槽位**。主控 §六自我更正「把语义规则写在哪一节当成机制归哪个模块」我复核认同。pin 写法（`test_tail_segmentation_is_pinned_to_module_4`）**两半都接、无缝**，且模块 4 派工须带 §9.2 的 `test_paired_face_unshared_tail_survives_as_single_face_fragment`（主控 §七.3 已登记 plan.md）。⛔ 别改回原验收 4。
- **同形锁 neuter**（隔离锁的牙）：
  - 坏法 A（自然坏法：不等长→拆成两条 single_face）→ 被 adapter **出口的 `validate_evidence_bundle` 当场咬住**（`BUCKET_VALUE_NOT_PROSE`，因拆出的 single_face 的 hypothesis_ref 指向 `/hypotheses/pairs/0` 不是桶）。**即自然坏法更早一层就被模块 2 校验器拦下**。
  - 坏法 B（能过 validate 的形态差：不等长→交换 face_a/b）→ `shape(uneq)=[('paired_faces','F02')]` ≠ `shape(eq)=[('paired_faces','F01')]`，测试的同形锁 **RED**。
  - **判定**：同形锁**有牙**（过 validate 的形态差被咬红），且**双层防御**（拆碎类坏法被 validate 提前拦）。「本层不许算几何」这条边界被真正锁住。

---

## 三、我自造的第五处打击（主控令「别被我限住」）

### 自造 ⑤ · pairs 非空路径的闭合保证（acceptance-1 的盲区）
- **动机**：`test_acceptance_1` 的「闭合」只跑在**恰好闭合的真实产物**上；而 adapter 的 **pairs-非空**路径**没有**自己的孤儿面检查（它只在 pairs-缺失路径 L286–291 查 `unaccounted`），把闭合权**全部委托**给出口 `validate_evidence_bundle`。若这条委托断了，adapter 会**静默丢**孤儿面、而闭合测试因为真实产物碰巧闭合而永远看不见。
- **复现读数**（注入：pairs 非空 [F01/F02 配对]、F03 non_wall、**F04 既不在任何 pair 也不在任何桶**）：
  ```
  orphan face (pairs present) -> FACE_WITHOUT_DISPOSITION | {input_id:'orphan', observation_id:'F04'}
  ```
- **判定**：闭合保证**兜得住**——牙落在模块 2 validate 的 `FACE_WITHOUT_DISPOSITION`（模块 2 审已实证该门可 neuter、是真 validator 齿）。**非缺陷**。但见 **F-1** 的测试覆盖建议。
- **附带**：F-152 机械核 `grep -nE '"src/|'"'"src/'` 于两文件 → **零命中**（禁令 7 干净）。

---

## 四、不阻断项（按重要性排序）

### F-1 · pairs-非空路径的闭合**测试覆盖**缺一条合成孤儿面锁（测试建议，非缺陷）
- **现象**：closure 的算术保证在 pairs-非空路径**没有 adapter 级检查**，全靠出口 validate。`test_acceptance_1` 只在三份**碰巧闭合**的真实产物上验闭合；没有任何合成用例注入「pairs 非空 + 孤儿面」去直接锁 **adapter↔validate 的闭合边**。
- **复现**：见自造 ⑤（`FACE_WITHOUT_DISPOSITION` 兜住）。今天**保证成立**，无实害。
- **影响**：若将来 validate 的 `FACE_WITHOUT_DISPOSITION` 回归、或 adapter 重构时误在 pairs-非空路径加了「只处置认领面」的捷径，孤儿面会静默丢而现有测试全绿看不见（[[gate-teeth-direction-follows-fixture-inventory]]：夹具全是闭合产物 ⇒ 这个方向零存货）。
- **建议方向**：模块 3 补一条合成锁——pairs 非空 + 一个不在任何 pair/桶的面 → 断言 adapter 出口红 `FACE_WITHOUT_DISPOSITION`。让闭合保证不再只依赖「真实产物碰巧闭合」+「validate 不回归」两个隐含前提。

### F-2 · 记账：sm24 `walls=present` 但 80% 面线是未决 debt，present/absent 二值反映不了「已决程度」
- **现象**：sm24 `walls=present` 仅凭 20/98 面被认领；78/98 是 ambiguous debt。设计上**诚实**（每条 debt 都在），但 present/absent 是二值、不承载「已决比例」；「闭合 + present」易被读成「已充分读」。这正是施工方**自报最薄弱处**（present 通道的 debt 在本层无消费门）与模块 2 **F-1**（present 载荷闭合）同一病族（[[gate-measures-right-but-carrier-gets-swapped]]）。
- **复现**：见点名 ②（78/78 在候选图、各带 debt、walls=present）。
- **影响**：接线日若模块 4/pipeline 的 strict profile **不消费**这 78 条 ambiguous debt，一份 80% 未决的 sm24 会以「walls present + 闭合通过」姿态混成完整成功。**今天零流量、零实害**。
- **建议方向**：本层不需改（翻译诚实）。但**必须**在**模块 4 / pipeline strict profile 的派工单**里把「ambiguous debt 必须被消费（可能改拓扑 ⇒ 阻断或墙级再感知）」写成硬验收——⛔ 别让它像模块 2 F-1 那样留在 execution 档散文里（[[stop-and-report-catches-dispatcher-errors]] 第三格：已落库/下游承诺）。

### F-3 · 环境：工作树三席交织，我的实验跑在**返工后**的模块 2 上（记账，供提交方留意）
- **现象**：被审对象声明基线 `31f873d`，但当前工作树上 `evidence_contract.py` **已被 GLM 的模块 2 F-1/F-2 返工改动**（+111 行：新增 `zero_payload_channel` debt 种类 + `_assert_channel_payload_closure` + 单源校验），`as_measured.py` **已被 GPT 的 F-153 改动**（+25 行）。adapter 的出口 `validate_evidence_bundle` 调用的是**返工后**的 validate ⇒ 我全部探针读数反映的是**返工后**模块 2。
- **复现命令与读数**：
  ```
  git diff --stat 31f873d -- src/agent/correction/evidence_contract.py  # 112 行改（GLM 模块2返工）
  git diff --stat 31f873d -- src/agent/judge/as_measured.py            # 26 行改（GPT F-153）
  git diff --stat 31f873d -- src/agent/reading/vector_contract.py src/agent/pipeline.py  # 空
  as_drawn disposition = Disposition.KNOWN_NOT_CONSUMED                 # 未翻
  pytest tests/test_o22m3_evidence_adapters.py -n 4  → 21 passed        # 兼容返工后模块2
  ```
- **影响/判定**：**对模块 3 的结论无害，反而更相关**（adapter 将与返工后模块 2 同批落地）。adapter 单源/单 sha per call ⇒ F-2 单源门对它平凡通过；adapter 只在 `if claims:`/`if openings:` 才发 present ⇒ F-1 载荷闭合门对它平凡通过（这就是 21 passed 的原因）。**模块 3 自身零接线完好**（vector_contract + pipeline 零 diff；`judge/` 的 as_measured.py diff 是 GPT 席位、**不属本单**，execution 档 §验收6 当时读到的空是当时的树）。
- **建议方向**：给**提交方**一句——这个待提交面**混装三席**（模块 3 新文件 + 模块 2 返工 + F-153），回滚/挑拣时按路径分开（[[wrapup-commit-sweeps-other-seats-wip]]）。⛔ 我未动树。

### F-4 · 记账：hybrid 单文件被 `ADAPTER_CONTRACT_MISMATCH` 收编，「歧义」这个更精确的事实被降格（施工方自报次弱）
- **现象**：`_require_contract` 用 `classify_vector_json`；单文件双契约命中时 classifier 返回 `CONTRACT_UNKNOWN` + reason 含 `AMBIGUOUS`，adapter 因 `detected != expected` 抛 `ADAPTER_CONTRACT_MISMATCH`，而非专属的 `AMBIGUOUS_CONTRACT_MATCH`。
- **复现**：`test_adapter_refuses_the_other_contract` 绿（错配一律响亮）；读 adapter L151 分支确认无 return/pass 出口、只降精度不降拦截。
- **影响/判定**：**非阻断**。与模块 2 **F-3** 同族——词法/分类只影响**精度**、不影响**是否拦截**（[[lexical-guard-cannot-be-completed]] 的致命面是静默漏过，这里是响亮但代号不够精确）。下游若按 error code 分流会把 hybrid 当普通错配。
- **建议方向**：接线日让 classifier 出结构化 `match_kind`（模块 2 F-3 的同一建议），adapter 据结构字段分 `AMBIGUOUS_CONTRACT_MATCH` vs `ADAPTER_CONTRACT_MISMATCH`。本批不必做。

---

## 五、两个是非题

1. **「零接线」对模块 3 是真的吗？** —— **是**。`git diff --stat 31f873d -- src/agent/reading/vector_contract.py src/agent/pipeline.py` = **空**；as-drawn disposition 仍 `KNOWN_NOT_CONSUMED`；`test_the_adapters_import_no_pipeline`（干净子进程只 import adapter ⇒ `src.agent.pipeline` 不在 sys.modules）复跑绿。`judge/` 的非空 diff 是 GPT 的 F-153 席位、不属本单（F-3）。✓
2. **有没有碰进 `canonical_bytes` 的面 / 已落库产物？** —— **模块 3 侧没有**。adapter + 测试**零写盘**（纯函数 + in-memory 夹具 + 只读真实产物）；`grep -nE 'open\(|\.write|gt_staging|canonical_bytes'` 于两文件仅命中 `canonical_json_bytes`（测试里的**读**用途、determinism 断言）。三格对撞第③格（已落库承诺）不涉及。✓

---

## 六、给用户的一句白话

施工方交的是两个「翻译器」：把识图结果译成校正阶段要吃的统一证据包，还没接到任何实际流程上，所以今天不会出事。我逐条核过——他没虚报：三份真实图纸都能过检且账目对得上（我自己独立数了一遍，49/46/98 条线一条不差地各归其位），旧图纸的「墙是外皮还是中线」这种只写在批注里的话他一个字都没读（我把所有批注改成互相矛盾的强暗示，结果纹丝不动），也没有任何偷偷把「猜配对」这件本该识图做的事搬过来的后门。我还自己造了一个刁钻输入（一条谁都不认领的线）去撞，它响亮地拒绝了、没有蒙混。**主控把「切一堵墙的多余尾巴」这件事改判给下一个模块做，我核实这个改判是对的**——因为这一层的数据结构里根本没有放几何坐标的格子。发现四个小事项，**没有一个今天咬人**：一个是建议补一条合成测试别只靠真图碰巧完整；一个是提醒下一个模块必须认真处理 sm24 那 80% 被识图「拿不准」的线，别让「通道说有货」盖过「其实八成没定」；一个是提醒提交时这堆改动混了三个人的活、要分开；一个是错误代号可以更精确。判**通过带整改项**，不阻断。

---

*复核人：Claude 家族跨家族审席位 · 2026-08-31 · `/tmp/o22m3_review/` 副本 + neuter 脚本（会话内临时件）· 真实套件主树 `-n 4` 复跑 21 passed*
