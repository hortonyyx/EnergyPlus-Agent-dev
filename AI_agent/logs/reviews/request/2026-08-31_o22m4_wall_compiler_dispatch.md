# 派工单 · ②-2 **模块 4**：`correction/wall_compiler.py`（ref resolve · 切段 · 中线/候选/厚度 IR）

- **日期**：2026-08-31 · **派工方**：orchestrator · **施工方**：**GLM 家族**（⭐ **原席位、原会话续做** `85e95c7d` —— 中途撞 5 小时限额，见 §七）· **审**：**GPT 家族**
- **基线**：**`6637f38`** · **权威全量**：**3494 passed / 13 xfailed / 0 failed**（四项哨兵全干净）
- **口径（已过审设计稿）** → [../verdict/2026-08-30_o22_evidence_contract_gpt_design.md](../verdict/2026-08-30_o22_evidence_contract_gpt_design.md)
  的 **§5.1**（转换位置与职责）· **§5.2 / §5.2.1**（四种输入怎样派生 · `basis=unknown` 且有厚度）·
  **§5.3**（厚度的三个名字必须分开）· **§5.4**（内核入口必须携带墙 IR）· **§9.1 第 4 步** · **§十**
- **上游**：模块 2（✅ 收口 + 返工在审）· 模块 3（✅ 收口）

---

## 〇、⛔ 排程（同机三席，家族各一）
**GPT = F-154**（写 `src/agent/judge/as_measured.py`）· **Claude = 待派** · **你 = 本单，写 `correction/wall_compiler.py` + 它的测试**。
⚠️ **你自己的模块 2 第二轮返工已交件**（`evidence_contract.py` 在树上有你的在途改动）—— 那是你自己的，本单可以依赖它。
⇒ ⛔ 不许 `git add`/`commit`/`pip install -e .`/`-n auto`/跑全量；跑测 **`-n 4`**；⛔ 不许动 `src/agent/judge/`；`git status` 不干净是正常的。

---

## 一、⭐⭐⭐ 本单**必须携带**的两条（上两轮跨家族审点名交办，⛔ 不许掉进缝里）

### 携带 ① · **余段切分**（模块 3 判归本单，主控已裁决确认）
模块 3 留了 pin `test_tail_segmentation_is_pinned_to_module_4`。设计稿 **§9.1 第 4 步**的验收原文 =
「验证**双面余段不丢**、四堵 solid band 不丢、厚度活到 kernel」；**§9.2 测试表**点名
`test_paired_face_unshared_tail_survives_as_single_face_fragment`。
⇒ **`paired_faces` 只在两面实际共同覆盖的区间编译为双面墙；A 面独有 / B 面独有的余段必须切成
仍引用原 claim 的 `single_face_fragment`。⛔ 不得取交集把余段扔掉，也⛔ 不得把并集全当双面。**
⭐ **并且要把模块 3 那条 pin 翻掉**（它今天断言「切段不在模块 3」；本单落地后应改成指向本单的实现）。

### 携带 ② · **`ambiguous` debt 必须被消费**（模块 3 审的 F-2 点名）
复核方实测：**sm24 `walls=present` 而 98 条面线里 78 条是未决 `ambiguous` debt**
（78/78 全在候选图里、各带一条 debt ⇒ 翻译是诚实的）。
⚠️ **但「闭合通过 + present」极易被读成「墙已充分读」**，而实际 **80% 未决**。
⇒ **本单必须让这些 debt 被消费**：设计稿 §7.2 的口径是「ambiguous **可能改拓扑** ⇒ strict 阻断」。
⛔ **不许静默跳过**，⛔ 不许只在 docstring 里写一句。

---

## 二、其余任务项（⛔ 以设计稿原文为准，本单不重述业务语义）

| 要造的 | 设计稿出处 |
|---|---|
| **ref resolve**：在**被 hash 绑定的冻结 bytes** 内解析每个 ref，⛔ 不重读工作目录 | §3.2 末段 |
| **切段** → `ResolvedWallV1` IR（含 `resolved_along_intervals`） | §5.1 / §5.4 |
| **中线 / 候选**：⭐ **中线只允许在这里由代码派生**，⛔ 不回写 reading、⛔ 不覆盖面线 | 指南「三之一」 |
| **厚度的三个名字必须分开** | §5.3 |
| **`basis=unknown` 且有厚度**这个同形输入 | §5.2.1 |

---

## 三、⛔ 禁令
1. ⛔ **不许动 `vector_contract.py` 的任何 disposition**（闸门必须**最后**做，设计稿 §9.1 第 7 步）· ⛔ 不许动 `pipeline.py`。
2. ⛔ **不许动 `src/agent/judge/` 任何文件**（Claude 席位正在写 `as_measured.py`）。
3. ⛔ **不许改模块 2 / 模块 3 的已有语义**去迁就本单 —— **停下上报**（同模块 3 那条纪律，防两套语义）。
4. ⛔ 不许解析自由文本 `note`/`reason`。
5. ⛔ 不许改既有测试断言；既有锁变红 ⇒ 停下上报。⭐ **例外**：模块 3 那条 pin 是**要你翻的**（见携带 ①），翻它要写明。
6. ⛔ 不许改任何已落库产物 / 进 `canonical_bytes` 的面。
7. ⛔ 不许 `git add`/`commit`/`pip install -e .`/`-n auto`/跑全量。
8. ⛔ 不要在 `.py` 字符串常量（docstring 也算）里写带仓库根前缀的生产文件路径（F-152）。

## 四、验收表（⭐ 已按三格对撞）

| # | 验收项 | 对撞检查 |
|---|---|---|
| 1 | ⭐ **余段保真双向**：A 面比 B 面长 ⇒ 余段出现为 `single_face_fragment` **且回指原 claim**；**两面等长 ⇒ 不得产生任何 fragment** | ⭐ 双向：只测前者会让「无条件切碎」也通过 |
| 2 | ⭐ **模块 3 那条 pin 已翻**，且新断言指向本单实现 | 与禁令 5 的例外一致；**若 pin 原样留着 ⇒ 不通过** |
| 3 | ⭐⭐ **`ambiguous` debt 被消费**：拿 **sm24**（78 条 ambiguous）跑 strict ⇒ **必须阻断并点名**；跑 exploratory ⇒ 可继续但**必须在报告里报出未决比例** | ⛔ 与「不许静默跳过」对撞：**若 strict 也放行，本条必然不通过** |
| 4 | **四堵 solid band 不丢**（sm24 实测有 4 条 solid_band claim） | 设计稿 §9.1 第 4 步原文 |
| 5 | **厚度活到 kernel**：三个名字分开，且给出**每一个**的来源（观测量 / 声明 / 匹配结果） | §5.3；⛔ 别把观测量命名成事实性名字 |
| 6 | ⭐ **中线只在本层派生**：给出机械断言证明 reading 侧产物与模块 2/3 的 bundle **没有中线字段被写回** | 指南硬纪律 |
| 7 | **零接线自证**：`vector_contract.py` / `pipeline.py` / `judge/` 相对基线**整文件零 diff** | 与禁令 1/2 对撞 |
| 8 | `pytest -n 4 <你的测试文件> tests/test_o22m3_evidence_adapters.py` 全绿 + 列全改动路径（⛔ 不提交） | 模块 3 也要跑，因为你要翻它一条 pin |

## 五、停下上报（分层）
**必停**：模块 2/3 的类型不够用（⛔ 不许补平行实现）· 设计稿某条与本单禁令自相矛盾 · 既有锁变红（pin 除外）· sm24 的 strict 阻断做不出来且原因是设计稿盖不住。
**只记不停**：字段命名 · IR 结构细节 · 本单范围外的缺陷。
**⭐ 累计 53 次停报，53 次都是派工方的题错 —— 放心停。**

## 六、交付
`src/agent/correction/wall_compiler.py`（新）+ 测试（新）· 执行档
`AI_agent/logs/reviews/execution/2026-08-31_o22m4_wall_compiler_execution.md`，逐条命令+读数、最薄弱处、希望复核方打哪里。


---

# ⭐ 续做说明（2026-08-31 · 用户拍板「原会话续作，免得重新开始」）

## 七、你是**原席位、原会话续做**，⛔ 不是重新实现

你上一轮在本单上写到一半撞了 5 小时限额（`429`）。中断时你已写出
`src/agent/correction/wall_compiler.py`（**1419 行**）+ `tests/test_o22m4_wall_compiler.py`（**965 行**）。

**处置沿革（请知悉，因为你会看到痕迹）**：主控最初按「孤儿件」纪律把它们移出 `src/` 隔离；
⭐ **随后用户拍板「GLM 已恢复，原会话续作，免得重新开始」** ⇒ **已原样还原回原路径**，
中断快照留在 [`../../experiments/2026-08-31_o22m4_orphan_wip/`](../../experiments/2026-08-31_o22m4_orphan_wip/) 供事后对账。
⇒ **接着你自己的工作往下做即可。**

## ⛔ 但有一条不因「原作者续做」而豁免：**它当时没有自验通过**

主控在中断后跑了一次你自己的测试：**2 failed / 20 passed**。
⇒ **本单验收之前，这两条必须弄绿，或者给出「为什么它们该红」的解释**：

| 红掉的 | 为什么要紧（⛔ 主控只点名，未代判真因，请你自己查）|
|---|---|
| `test_compiler_imports_neither_pipeline_nor_judge` | 这是**零接线**锁 —— 它红意味着**可能已越过本单的接线边界**（禁令 1/2）。请查清到底 import 了什么 |
| `test_selected_pair_values_are_recomputed_not_cached` | 设计稿 §4.1 明写 `spacing_m` **只作缓存审计、必须从两面重算** ⇒ 红意味着**可能在读缓存值** |

## 八、⚠️ 环境提示
- `src/agent/correction/evidence_contract.py` 上有**你自己**刚交的模块 2 第二轮返工改动（未提交）——
  本单可以依赖它；⭐ **执行档里请写明你的读数是在它的哪个状态下取的**（给 `git diff --stat` 或文件哈希）。
  ⚠️ 立此条的依据：上一轮模块 3 的复核方点名「并行派工让复核基线变模糊」。
- **GPT 席位正在写 `src/agent/judge/as_measured.py`** ⇒ ⛔ 别碰 `src/agent/judge/`。
- `AI_agent/` 下的改动是主控的，⛔ 别碰。
