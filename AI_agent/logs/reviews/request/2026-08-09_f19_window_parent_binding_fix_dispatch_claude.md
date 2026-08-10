# 派工单 · F-19：`kernel.window_parent_binding` 恒红（顶点顺序两套规范并存，第二次）

- **日期**：2026-08-09 · **席位**：Claude 侧 **Sonnet**（执行档）· 通道 = Agent 子代理
- **基点**：分支 `6.15_ValidationArchM0toM4`，**HEAD = `7315bc8`**，工作树无未提交的**代码**改动
  （有 64 个未跟踪项 = `.gitignore` 改规则后重新可见的历史痕迹，⛔ **不要动它们、不要清理**）
- **全仓基线**：`python -m pytest -p no:cacheprovider -q -n 8` ⇒ **2339 passed / 10 xfailed / 0 failed**
- **调查全档（先读）**：[`logs/experiments/2026-08-09_f19_window_parent_binding/README.md`](../../experiments/2026-08-09_f19_window_parent_binding/README.md)
  —— 根因**已由 orchestrator 实测坐实**，三个可复跑探针随报告入库。⛔ **不要重做调查**，直接施工。
- **备份已由 orchestrator 完成**：`backup/src_history/2026-08-09_f19_window_parent_binding_canonical_order/`

---

## ⛔ 0. 第一步：防假验证自检（在动任何代码之前做，做完把答案写进执行日志）

> 缘起 = 2026-08-07 那次派工，验收路径**根本不经过被改的代码**（冻结产物 + 跳段入口）
> ⇒ 数学上不可能体现修复效果。**派工方错误率 12/12，每次都是派工单的题错了。**

请先回答这三问，**答不上来就停下上报，不要开工**：

1. 我打算用来验收的那条路径，**真的会执行到 `src/validator/checks/kernel.py:362` 那一行吗**？
   （提示：`_window_parent_binding` 只在 `geometry_contract == "c2_b5_v1"` **且** proof 非空时才走到顶点比较。）
2. 我的锁的夹具，**`built.verts` 是不是真的经过了 `build_geometry` 的 `_canonicalize_bg_vertices`**？
   （如果夹具是手搓 `BuildingGeometry(...)` 直接塞顶点，那它**不经过**规范化 ⇒ 锁的是另一回事。）
3. 我怎么证明「不加我的修法，这条锁是红的」？（见 §3 的自证前提要求）

---

## 1. 缺陷事实（已实测，⛔ 不是推断）

`run_2026-08-09_f18_e2e_verify` 的 flow 退出码 20：

```
[2_modelling] deterministic_defect
   ⛔ kernel.window_parent_binding: 15 built window parent-binding defect(s)
   offenders 的 reason 全部是 built_vertices
```

**几何是对的**（逐窗机械归类）：15/15 **循环旋转**、位移恒为 3、法向全部保持、
**零绕向反、零坐标真不同**。

**根因**（决定性验证：两边过同一规范化后 **15/15 逐位相等**，直接比 **0/15**）：

| 侧 | 走不走规范化 |
|---|---|
| `built.verts` | ✅ 走 `src/agent/geometry/build.py:80-85` 的 `_canonicalize_bg_vertices`（F-13 于 08-06 `a3458cc` 加的，**对窗也做**）|
| `fresh_vertices` | ⛔ 不走，`src/validator/checks/kernel.py:344-358` 直调 `window_verts_on_line` 原始生成器 |

比较那一行：`src/validator/checks/kernel.py:362` `if built.verts != fresh_vertices:`

**⇒ 门生于 07-18（`2885a84`）一直是对的；08-06 的 F-13 修法把它打坏，潜伏 3 天**
（B 类潜伏：这 3 天没有 run 走到过 v3 契约 + 真实 proof 的 2_modelling）。

---

## 2. 修法（方向已定，⛔ 不许改方向；实现细节你定）

### 2.1 主修法 = 路线①，与 F-13 r1 同精神

让门的复算侧走**同一份**规范化 —— 即 `build.py:78/84` 用的那一个
`canonicalize_ring_vertices`（`src/validator/data_model.py`）。

⛔ **不许另写一份"应该一致"的算法** —— 两份"应该一致"的规范各自漂，**正是 F-13 的成因**。
⛔ **不许改 `build.py` 去掉规范化** —— 那会推翻 F-13 r1（它在兑现 IDF 头部
`GlobalGeometryRules = UpperLeftCorner` 声明，砍掉会让 EnergyPlus 把 76/79 面墙的宽高判错）。

### 2.2 ⛔ 明确禁止的修法

**不许给门加「循环旋转视为等价」的豁免。**
严格才抓得住真正有害的**绕向反转**（法向翻转 ⇒ 内外面反转 ⇒ **窗挂错房间**）。
用户 2026-08-06 已就同一问题拍过一次板（F-12 施工单），本次同样适用。

### 2.3 顺带排查（用户 2026-08-09 拍板纳入本批）

F-13 那次给 `build_geometry` 的输出加了规范化。**F-19 只是第一个被真链路撞出来的受害者。**

⇒ **请机械排查：还有谁在拿【未规范化】的顶点形态与 `build_geometry` 的输出做比较/断言。**
- 至少覆盖 `src/validator/`、`src/agent/geometry/`、`src/agent/`（含 `output_coordinates.py` 的各条漂移门）与 `tests/`。
- 判据 = 「这一侧的顶点来自 `build_geometry` 输出（已规范化）吗？另一侧呢？两侧是否用 `==`/`!=`/逐位比？」
- **⛔ 结果要如实登记**（哪些查了、哪些是真命中、哪些看着像其实不是）。
  **查到 0 个也要写明"查了哪些、判据是什么"** —— ⛔ 不许用「没找到」当"不存在"的证据。
- 命中项**先登记、不要顺手全改**；改动范围超出 F-19 本身就**停下上报**。

---

## 3. 锁（⛔ 这一节是本单最重要的部分）

### 3.1 为什么现有 7 条测试全绿却没抓到（先理解这个，否则会补出同样没用的锁）

`tests/test_c2_b5_parent_and_verts.py` 覆盖了这道门，**7 处断言全部是 `fail`**：
695/705/713/722/729（无 proof / 契约不符 / 契约未知 / 载荷坏 / proof 类型不支持）· 554（删父面）·
**798（把 `windows[0].verts[0]` 改成 `(9,9,9)`，断言出现 `built_vertices`）**。

**没有任何一条断言这道门在正确产物上 `pass`。**

orchestrator 已在 `/tmp` 实测（⛔ 未动工作树）：拿该文件自己的 `_bundle()` 夹具、**零改动**跑这道门
⇒ `status=fail`, `reasons=['built_vertices']`。
**⇒ 798 那条把 mutation 整行删掉照样绿 = 假锁，已坐实。**

> ⭐ **新形态**：一道门如果只有「断言它 fail」的测试、没有「断言它 pass」的测试，
> 那么它**恒红**这件事结构上不可能被测试发现，而且所有 fail 断言会因此全部永远绿。

### 3.2 必须补的锁

**L-1（正向锁，最重要）**：断言这道门在**由 `build_geometry` 真实产出**的正确产物上 **`pass`**。
- ⛔ 夹具**必须**经过 `build_geometry`（因此经过 `_canonicalize_bg_vertices`）。
  手搓 `BuildingGeometry(...)` 塞顶点的夹具**不算**，它绕过了规范化 = 锁了另一回事。
- ⛔ 断言必须落在 `check_id == "kernel.window_parent_binding"` 的 `status == "pass"`，
  **不许**落在「report 非空」「results 数量」这类判据上。

**L-2（自证前提）**：⭐ **先断言「不加修法时这条会失败」**，再断言修法放行。
（08-09 新纪律：**回归用例必须自证前提**，前提破了要**大声报错**，⛔ 不许静默退化成空锁。
样板见 `tests/test_f18_window_host_float_tolerance.py` 的 `_round_trip_differs`。）
具体形态自定，但必须能机械回答：「把规范化那一步摘掉，这条锁会不会红」。

**L-3（修好 798 那条假锁）**：让它**真的**锁到「顶点被改坏」这件事 ——
即断言「不加 mutation ⇒ `pass`；加了 mutation ⇒ `fail` 且 reason 含 `built_vertices`」。

**L-4（防豁免倒退）**：**绕向反必须仍被拦下**。
造一个把窗顶点环**倒序**（法向翻转）的用例，断言门 `fail`。
⇒ 这把锁保证将来没人用「循环旋转豁免」的方式糊弄过去。

### 3.3 neuter 自查（⛔ 必做，结果进执行日志）

逐条摘掉对应修法，验证**恰好该条转红、零连带**：
- 摘掉复算侧的规范化 ⇒ L-1 / L-2 应转红；
- 恢复 798 原样（不加 mutation）⇒ L-3 应转红；
- 若给门加上"循环旋转等价"⇒ L-4 应转红。

⛔ **neuter 只在 `/tmp` 副本里做**，不许在工作树里改了再还原
（orchestrator/审阅方随时可能在跑门，工作树短暂被改会让双方数字互相打脸）。
⛔ **neuter 必须确认「改动真的落下去了」**（正则命中 0 处的空操作拿到"全绿"是实犯过的）。

---

## 4. 跑测纪律

- **中间轮**：`python scripts/tool_scripts/affected_tests.py --changed <你改的路径>...`
  按它给的命令跑子集，并把它输出的那行**跑测声明**贴进执行日志。
- **交付前**：跑一次全仓 `python -m pytest -p no:cacheprovider -q -n 8`
  （⛔ **不要 `-n auto`**，16 worker 实测会在 ~98% 处静默 OOM 中断）。
- ⛔ **输出直接重定向到文件，中间不接任何下游管道**：
  `... > run.log 2>&1; echo $? > run.exitcode`
  （实犯：`pytest | tee log | head -20` ⇒ `head` 关 stdin ⇒ `tee` 收 SIGPIPE ⇒ **连带打断 pytest**，
  而通知里的"退出码 0"**其实是 `head` 的**。）
- **以汇总行 + 退出码为准，不看进度条。**
- 全仓有红**先诊断再修**，⛔ **不改测试迁就实现**。

---

## 5. 交付

1. **执行日志** → `AI_agent/logs/reviews/execution/2026-08-09_f19_window_parent_binding_claude.md`，含：
   - §0 三问的答案
   - 改动清单（逐文件逐处，写清"为什么这么改"）
   - §2.3 排查结果（查了哪些、判据、命中/未命中，**0 命中也要写**）
   - L-1…L-4 的锁清单 + **neuter 自查表**（哪条摘了、恰好红哪条、有无连带）
   - 全仓原始输出（passed/xfailed/failed 汇总行 + 退出码）
   - **审阅需求（review-ask）**：你哪些处没把握 / 做了判断取舍 / 动了风险点或不变量。
     ⛔ 无则写明 "none — routine spec'd execution"，**不要过度自信**。
2. ⛔ **不要 `git add` / `commit` / `push`**（只有 orchestrator 提交）。
3. ⛔ **不要动 `AI_agent/` 下的管理文档**（CLAUDE.md / plan.md / decision_log.md）——那是 orchestrator 的。

---

## 6. ⛔ 合法退出口（请用它，不要硬凑）

**派工方（orchestrator）的历史错误率是 12/12** —— 每一次施工席「停下上报」，
事后核实都是**派工单的题出错了**，不是施工席能力问题。所以：

- 发现验收条件**互相冲突**、或**不可达**、或**根本不经过被改的代码** ⇒ **停下上报**。
- 发现本单的某条断言**在事实层面就不成立** ⇒ **停下上报**，附你的证据。
- 发现修法需要动的范围**超出 F-19**（例如必须改 `build.py` 或改 F-13 的规范化本身）⇒ **停下上报**。
- ⛔ **不要**为了让某条锁变绿而修改被测行为或放宽断言。

上报格式：写进执行日志 + 简报里明说「STOPPED: <一句话原因>」。
