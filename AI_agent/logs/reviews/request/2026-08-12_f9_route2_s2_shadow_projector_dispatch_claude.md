# 施工单 · 摊 B — F-9 路线② **S2：权威 projector + shadow position evidence**

- **日期**：2026-08-12 · **席位**：Claude 侧 Sonnet · **审**：GPT 侧（本单完工后另派）
- **前置**：S0（`21b4739`，合同/版本壳）+ S1（同提交，facade convention 单源）**均已落库**。
  稿子 §10 逐字写着 **S1 在施工上必须先于 S2**（避免 shadow 又造一份临时公式）—— 已满足。
- **⛔ 并行席位**：同一棵工作树上**另有一个席位（摊 C+D）在动
  `src/agent/correction/envelope_transform.py` + 报告/侧车产出点 + `tests/`**。
  **你的文件所有权** = `src/agent/correction/window_position.py`（及新建文件）+ `scripts/tool_scripts/run_stage.py`
  + `src/validator/checks/correction.py` + 你自己新建的测试文件。
  **⛔ 绝对不要执行 `git checkout` / `stash` / `clean` / `commit` / `reset`**（上一轮有席位执行 `git stash`
  波及了另一席位的未提交改动）。只读 git 命令随意。

---

## 第 0 步（**先做这个，不做完不许往下走**）· 防假验证自检

本项目最贵的一类派工错误是**验收路径根本不经过被改的代码**。

⇒ **动手前**：在你打算插入 shadow 逻辑的那个位置写**一句必抛异常**，
跑你打算用的验收命令（真实 `_draw_correction` 路径 + integrated pipeline），
**确认它真的抛了**。不抛 ⇒ 你的验收路径不经过那里 ⇒ **停下上报，不要继续**。

---

## 1. 唯一权威口径 = 设计稿

`AI_agent/proposals/f9_route2_evidence_citation_design.md`，**S2 的验收条件在 §10**，逐字如下：

> **S2｜权威 projector 与 shadow position evidence**
> 内容：实现 authoritative frame V2、统一 projection dispatcher、pairing decision；在现有 model-authored
> span 路径旁 shadow 运行。输出同时记录 plan authority、current-ring elevation projection、pair distance、
> legacy model span 差异；**不得覆盖 span、不得 block**。
> **可独立验收：是。** 真实 `_draw_correction` 与 integrated pipeline 都出现
> `correction.window_position_evidence_shadow` 明确 PASS/FAIL fact；shadow FAIL 固定为 cross-check/FLAG，
> 不得因启用观测而改变接受结果。**摘掉 projector 或改用 advisory frame，shadow 锁转红。
> 不可用 `None` 表示"跑过但没结果"。**

**另须读**：§6（唯一 facade convention 与 projector）· §7.1–§7.3（view datum / applicability scope 分离、
local-z datum 与 scope 唯一归属）· §1.3（**advisory 绝不能提权**）。

---

## 2. orchestrator 已核实的接线事实 —— **请当作待证伪的断言**

| 断言 | 我怎么测的 |
|---|---|
| `correction.window_position_evidence_shadow` 这个 check-id **全仓零命中** ⇒ 未被占用 | `grep -rn` over `src/` `tests/` |
| S0 的 `build_window_position_decision` / `materialize_raw_projection_context` **零生产调用点** ⇒ 确实未接 live（符合 S0「不接 live production」的设计）| `grep -rn` over `src/` `scripts/`，排除定义文件本身 |
| 真实入口 `_draw_correction` 在 `scripts/tool_scripts/run_stage.py:302` | `grep -n "def _draw_correction"` |
| correction 检查汇集入口 = `src/validator/checks/correction.py:89 check_correction` | 同上 |
| S1 的 `facade_convention.py` 已落且已接线 | ⚠️ **commit 说明写的是「6 个真实调用点」，我没独立数过** ⇒ **这个数字请自己数** |

**⭐ 尤其请证伪第 2 条**：如果 `build_window_position_decision` 其实已经被什么地方调用了，
那 S2 的「shadow 运行」就不是新增一条旁路，而是改动一条已承重的路 —— **性质完全不同，停下上报。**

---

## 3. 硬约束（稿子里的，逐条抄，⛔ 不许打折）

1. **⛔ 不得覆盖 span、⛔ 不得 block。** shadow 只观测。
2. **shadow FAIL 固定为 cross-check / FLAG** —— 不得因为启用了观测而改变任何接受结果。
   **判据：把 shadow 打开和关掉，所有现有 run 的接受/拒绝结果必须逐字节一致。**
3. **⛔ 不可用 `None` 表示「跑过但没结果」。** 每种「没算出来」的原因必须各自具名。
   （本项目刚在另一处栽过同型：一个空白同时代表三件不同的事，最该被看见的那档恰好不可见。）
4. **⛔ advisory frame 绝不能提权。** `_advisory_elevation_world_frame` 的 advisory 标记**有明确原因**——
   提交 `99d9521` 的说明里逐字写着「绝不进任何强制路径」，并当场登记了 `lo==0` 假设与 0.12 m 的实证代价。
   ⇒ **动它之前先读那条提交说明。**（本项目已经犯过两次「把某个标记当成『当初没人敢用』而砍掉」。）
5. **铁律 #6（建筑复杂度可扩展性）**：frame / datum / scope 的设计**不得把
   「共用 footprint / 每层满铺楼板 / 固定层高」这类当前简化假设烤死到无法松动**。
   稿子 §7.4 有逐项交代，请对照。
6. **z 轴 datum 不许靠「今天恰好相等」**：本产物 `local_z` 恰等于 world-z，
   而真实产物 East 立面有两扇窗**沿墙区间逐位相同、只有高度不同** ⇒ 它们的判定全压在 z datum 规则上。
   稿子 v2.1 已把「今天恰好相等不能充当声明」写进正文 —— 请落实成代码里的显式规则，不是隐式依赖。

---

## 4. 锁的要求

- **必须走真实入口**（真实 `_draw_correction` + integrated pipeline 两条都要出现该 fact），
  ⛔ 不许只在私有 helper / 夹具层断言。
- **每把锁自证前提**：先断言「没有这处改动时它确实是另一个结果」，前提破了要**大声报错**，
  ⛔ 不许静默退化成空锁。
- **稿子点名的两个 must-red neuter，逐个兑现并附实测**：
  ① **摘掉 projector** ⇒ shadow 锁转红；② **改用 advisory frame** ⇒ shadow 锁转红。
- **⛔ 恒等锁不算正确性锁**：不许只断言「非 None」「总数变了」「两边相等」。
  凡是「两边共用同一个函数所以一定相等」的断言，必须**另配一把断言等于手算值的锁**。
- **不变性锁**：shadow 开/关，既有接受结果逐字节不变（对应第 3.2 条）。
- **⚠️ 遮蔽自查**（F-20 换来的判别问法）：
  **「我这个夹具里，有没有第二条防线会先于目标门把这个变异拦下？」**
  凡发现遮蔽，必须横扫同批所有锁。

---

## 5. ⛔ 硬纪律

1. **⛔ 派工方错误率 13/13** —— 本单里凡是描述**岔口 / 分类 / 数量 / 位置**的句子
   （「零生产调用点」「6 个调用点」「§10 说可独立验收」「`run_stage.py:302`」），
   **都可能是错的前提**。**发现前提错请停下上报，不要照题作答。**
   过去 13 次「停下上报」**全部**是派工方的题错了。
2. **⛔ 不要 git 写操作**（并行席位共用工作树）。验锁的 neuter **只在 `/tmp` 做**，做完还原。
3. **neuter 必须覆盖「接线」不只「机制」**：判据 = **把共享实现中和掉，这个调用点会不会跟着变**。
   ⛔ **不许用 grep / 精确 AST 语法判「是否已接线」** —— 上一轮正是这条把 orchestrator 带沟里了
   （有个函数用**两次条件取反**等价实现了同一个 XOR，任何形状匹配都抓不到，而它并非死代码）。
4. 跑测：中间轮只跑受影响子集；**交付前跑一次全仓**，日志与退出码用**独立文件名**
   （⛔ 不与上一次跑复用文件名），判「跑完没有」**看 `N passed` 汇总行**、不看 `.rc` 存不存在。
   **当前基线 = 2470 passed / 10 xfailed / 0 failed。**
5. **改 `src/` / `tests/` / `scripts/` 前先备份**：`cp` 到 `backup/{src,scripts,tests}_history/2026-08-12_f9_s2/`。

## 6. 输出

执行记录落 `AI_agent/logs/reviews/execution/2026-08-12_f9_route2_s2_shadow_projector_claude.md`，含：
改了什么 / 每把锁绑的是什么 / **两个 must-red neuter 的实测结果（转红了没、有没有连带）** /
shadow 开关的不变性实测 / 全仓测试汇总行 /
**你未验证的项与你不确定的判断（如实列出，这比多写几把锁有价值）**。
