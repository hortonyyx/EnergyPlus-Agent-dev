# 派工单 · ②-2 **模块 3**：`correction/evidence_adapters.py`（legacy / as-drawn 双 adapter）

- **日期**：2026-08-31 · **派工方**：orchestrator · **施工方**：**GLM 家族**（你刚写完模块 2，上下文最全）· **审**：**GPT 家族**
- **基线**：**`31f873d`**
- **口径（已过审设计稿）** → [../verdict/2026-08-30_o22_evidence_contract_gpt_design.md](../verdict/2026-08-30_o22_evidence_contract_gpt_design.md)
  的 **§4.1 表**（四种墙声明必带的原始引用）· **§4.2**（三种面线处置）· **§4.3**（`pair_candidates` 的地位）·
  **§5.2 / §5.2.1**（四种输入怎样派生 · `basis=unknown` 且有厚度）· **§8.3**（legacy basis 的迁移纪律）·
  **§9.1 第 3 步**：「建双 adapter：as-drawn → 四种 wall claim + disposition ledger；legacy → `legacy_wall_trace(basis=...)`。
  **验证同槽唯一、引用闭合、面线完整消费**」
- **上游**：模块 2 的类型层 `src/agent/correction/evidence_contract.py`（你自己写的，**⏳ 跨家族审在飞**）

---

## 〇、⛔⛔ 排程前提（同机三席在飞，三个家族各一）

| 席位 | 家族 | 写面 |
|---|---|---|
| F-153 第三轮 | GPT | `src/agent/judge/as_measured.py` + `case_tests/test_baseline/gt_staging/` |
| 模块 2 跨家族审 | Claude | **只读**（`/tmp` 副本）|
| **你（模块 3）** | **GLM** | **`src/agent/correction/evidence_adapters.py`（新）+ 它的测试（新）** |

⇒ **三条硬约束**：① ⛔ 不许 `git add`/`git commit`（提交归主控；`git status` 不干净是正常的，别清理别 checkout）
② ⛔ 不许 `pip install -e .` ③ ⛔ 跑测**只跑你自己那一个测试文件、`-n 4`**，⛔ 不许 `-n auto`、⛔ 不许跑全量。

### ⚠️ 你的上游正在被审 —— 这是**故意**的并行，但你要按这条走
模块 2 的跨家族审在飞。**若复核方判 REWORK，你这一层要跟着动。**
⇒ ⭐ **本单因此加一条纪律**：**凡你用到模块 2 的某个类型/校验器时，如果发现它不够用或不对，
⛔ 不许自己在模块 3 里绕过去补一个平行实现** —— 那会造出两套语义（本项目 [[free-correctness-evaporates-when-representation-changes]] 的形状）。
**停下上报**，我来协调。

---

## 一、本单要造什么

**唯一交付 = 两个 adapter + 它们的锁。⛔ 本单仍然不接线**（`vector_contract.py` 的 disposition 一个字不许动 ——
设计稿 §9.1 明写**只有到第 7 步**才改）。

| adapter | 输入 | 产出 |
|---|---|---|
| **as-drawn** | 模块 1 的 `AsDrawnPlanV2` 真实产物（三份）| 四种正向墙声明 + **三种面线处置的 ledger** |
| **legacy** | 旧 `ReadingView`（带 `strokes`）| `legacy_wall_trace(source_basis=...)` |

### ⭐⭐⭐ 三条设计稿明令，⛔ 别踩
1. **每条 as-drawn 面线必须【恰好一次】落入三种处置之一**（§4.2）——无桶、跨桶、重复墙 claim **全部响亮失败**。
2. ⛔ **`legacy` 的 `source_basis` 非 `unknown` 时必须有【结构化】证据** ——
   ⛔ **禁止解析自由文本 `note` 猜基准**。⭐ 承重反例（主控已复核）：两份**真实**历史产物、
   同一个 `pen=="wall"` 字段，**一份是外皮线、一份是中线，而且只写在 `note` 里**
   ⇒ 「旧 reading 给的是中线」**不成立**，绝大多数只能落 `unknown`。
3. ⛔ **`pair_candidates` 不是第五种墙**（§4.3）：adapter **不许**在 `pairs` 缺失时自己从候选图里重做配对
   ——那是把「认」从 reading 偷搬到 correction。`pairs_status=ABSENT_NO_MODEL_SELECTION` ⇒ 走 `reperception_required`。

### ⭐ 必须接住的一条 pin（模块 2 留给你的）
`test_nf4_5_unselected_dangling_candidate_passes_today_module3_4_pinned` ——
**未被选中的悬空候选**今天能通过，模块 2 把它 pin 给了**模块 3 与模块 4**。
⇒ **本单要把模块 3 那一半接掉**：adapter 遍历候选图时**必须解引用 `face_b`**，指向不存在的面要响亮失败。
⛔ 若你判定它其实归模块 4，**必须把 pin 改写成明确只归模块 4**，⛔ 不许两边都不接（**缝里没人派**是本项目老病）。

### ⭐ 保真规则（§4.1 末段，容易漏）
`paired_faces` **只在两张面实际共同覆盖的区间内**编译为双面墙；
**A 面独有 / B 面独有的余段必须切成仍引用原 claim 的 `single_face_fragment`**。
⛔ 不得「总体配过对就取交集把余段扔掉」，也⛔ 不得把并集全当双面。

## 二、⛔ 禁令
1. ⛔ 不许动 `vector_contract.py`（任何 disposition）· `pipeline.py` · `src/agent/judge/` 任何文件。
2. ⛔ 不许改 `evidence_contract.py` 的**已有**语义去迁就本单（要改就停下上报，见 §〇）。
3. ⛔ 不许解析自由文本 `note`/`reason` 去猜任何东西。
4. ⛔ 不许改既有测试断言；既有锁变红 ⇒ 停下上报。
5. ⛔ 不许改任何已落库产物 / 任何进 `canonical_bytes` 的面（**三格对撞第③格**，题错 #51 的教训）。
6. ⛔ 不许 `git add`/`commit`/`pip install -e .`/`-n auto`/跑全量。
7. ⛔ 不要在 `.py` 的字符串常量（docstring 也算）里写带仓库根前缀的生产文件路径（**F-152**）。

## 三、验收表（⭐ 已按三格对撞）

| # | 验收项 | 对撞检查 |
|---|---|---|
| 1 | 三份真实 as-drawn 产物**各自**过 adapter 出 bundle，且**每条面线恰好一个处置**（给三份的逐份计数：面线总数 = claimed + non_wall + ambiguous） | 与设计稿 §4.2 一致；⭐ **计数必须闭合**，差一条即红 |
| 2 | **legacy adapter**：拿那两份真实历史产物（`tests/fixtures/f9_window_host_crash/0_reading/1f_view.json` 与 `case_tests/e2e_tests/smalloffice_22/0_reading/1f_view.json`）跑通，**两份的 `source_basis` 都必须落 `unknown`** | ⛔ 与禁令 3 对撞：**若你解析了 `note`，这两份会给出不同 basis ⇒ 本条必然不通过** |
| 3 | ⭐ **模块 2 pin 接掉**：未被选中的悬空候选**从 PASS 变红**，或 pin 被改写成「只归模块 4」并给出理由 | 与 §一 那条 pin 一致；**两边都不接 ⇒ 不通过** |
| 4 | ⭐⭐ **余段保真**：造一份 A 面比 B 面长的合成夹具 ⇒ **余段必须出现为 `single_face_fragment` 且回指原 claim**；再造一份两面等长的 ⇒ **不得产生任何 fragment** | ⭐ 双向：只测前者会让「无条件切碎」也通过 |
| 5 | ⭐ **`pairs` 缺失时不得自造配对**：把某产物的 `pairs` 清空 ⇒ 必须走 `reperception_required`，⛔ 不许从候选图补 | 与 §一.3 对撞 |
| 6 | **零接线自证**：`vector_contract.py` / `pipeline.py` / `judge/` 相对基线**整文件零 diff** | 与禁令 1 对撞 |
| 7 | `pytest -n 4 <你的测试文件>` 全绿 + 列全改动路径（⛔ 不提交） | 与禁令 6 一致 |

## 四、停下上报（分层）
**必停**：模块 2 的类型不够用 / 不对（见 §〇）· 设计稿某条与本单禁令自相矛盾 · 既有锁变红 ·
三份真实产物里有一份**过不了 adapter 且原因是设计稿盖不住它**（那是设计层缺口）。
**只记不停**：字段命名 · 三份产物的字段差异 · 本单范围外的其它缺陷。
**⭐ 累计 51 次停报，51 次都是派工方的题错 —— 请放心停。**

## 五、交付物
`src/agent/correction/evidence_adapters.py`（新）+ 测试（新）· 执行档
`AI_agent/logs/reviews/execution/2026-08-31_o22m3_evidence_adapters_execution.md`，
逐条给命令 + 读数、**你自己认为最薄弱的一处**、希望复核方重点打哪里。

---

# ⭐ 补充裁决（2026-08-31 · 回应施工方就验收 4 的停报）

## 六、⚠️ **停报成立，派工方题错 #53（累计 53，仍 53/53）**

**施工方报的**：验收 4 的字面（「余段必须出现为 `single_face_fragment`」）**在本层做不了**，
因为模块 2 的 claim 上**零几何值**（那是模块 2 验收 4 的机械锁），
「哪一段是余段」是**计算结果**，只能落在 compiler 的派生 IR。

**主控核实（对着设计稿原文，⛔ 未转引）**：
- **§十** 模块 4 职责 = 「ref resolve、**切段**、中线/候选/厚度 IR」——**切段写在模块 4 名下**；
- **§9.1 第 4 步**（模块 4 的验收）= 「验证**双面余段不丢**、四堵 solid band 不丢」；
- §5.1 编译管线亦把切段列为 compiler 的第二步。
⇒ **成立。**

⭐ **我错在哪**：设计稿 **§4.1 末段**确实写了那条保真规则，但那段是在讲**墙声明的语义边界**，
**不是在指派实现层**；同一份文档在 §十/§9.1 把**机制**给了模块 4。
**我把「语义规则写在哪一节」当成了「机制归哪个模块」。**
⚠️ 三格对撞拦不住这一类（不是矛盾，是我对文档结构的**归属判断**错了）
⇒ 与题错 #52 同批：**派工前把「这条要求的机制在设计稿里被指派给谁」单独查一遍**。

## 七、✅ 裁决：**确认改判 —— 切段归模块 4，你的处理是对的**

1. ✅ **确认** `test_tail_segmentation_is_pinned_to_module_4` 这条 pin 的写法。
2. ⭐ **你接住的模块 3 那一半我认为选得准**：
   「等长 / 不等长两种输入产出的 bundle **形态相同**」——
   ⭐⭐ **这条比原验收 4 更好**，因为它锁的是「**本层不许算几何**」这个真正的边界，
   而原验收 4 锁的是一个本层根本不该有的产物。**⛔ 别改回去。**
3. ⭐ **已登记**：模块 4 的派工单**必须携带**
   `test_paired_face_unshared_tail_survives_as_single_face_fragment`（设计稿 §9.2 测试表）
   作为硬验收。已写进 plan.md，⛔ 不会掉进缝里。
4. **验收 4 就此改写为**：「不等长 / 等长两份夹具产出的 bundle **形态相同**（⛔ 本层不算几何），
   且不等长那份的两面 witness 在冻结 bytes 里**原样可解**」——**= 你已交付的那两条锁。**

## 八、⛔ 其余不变
验收 1/2/3/5/6/7 与全部禁令照旧。**本单其余部分继续按已交付的走，等跨家族审。**
