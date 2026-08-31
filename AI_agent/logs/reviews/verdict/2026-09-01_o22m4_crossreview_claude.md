# 跨家族审 · **②-2 模块 4 `wall_compiler`**

- **日期**：2026-09-01 · **施工方**：GLM 家族（`6a29e92`）· **复核方**：**Claude 家族 / orchestrator**（跨家族，恒升一档）
- **被审对象**：`6a29e92`（1419 行新模块 + 1045 行新测试 + 模块 3 的 pin 翻转 44/-16）
- **审阅方式**：⛔ **不看执行者自述**，只看 ① 原始派工单 ② `git show` diff ③ 测试输出 ④ **我自己跑的变异矩阵**
- **隔离**：三席在飞 ⇒ 变异**全部在独立 worktree** `58bb59f` 里做，**主树零改动**；
  已先证明 worktree 不串回主树（`src.__file__` 解析到 worktree 自身）

## 裁决：**REWORK**（阻断 **1** 条 · 不阻断 **2** 条）

⭐⭐⭐ **唯一那条阻断的根在派工方，不在施工方** —— 见 §四，记 **题错 #55**。
代码本身我没找到错误；**缺的是一个通道完全没有被任何锁量到**。

---

## 一、机械核对（验收表逐条）

| # | 验收项 | 结论 | 证据 |
|---|---|---|---|
| 7 | 零接线自证 | ✅ | `git diff 6637f38 6a29e92 -- src/agent/reading/vector_contract.py src/agent/pipeline.py src/agent/judge/` ⇒ **零输出** |
| 2 | 模块 3 的 pin 已翻且指向真实现 | ✅ | `test_tail_segmentation_is_pinned_to_module_4` → `test_tail_segmentation_is_delivered_by_module_4`，且**模块 3 那半负向锁保留**（bundle 对等长/不等长形状相同）|
| 8 | 测试全绿 | ✅ | `pytest -n 4` 三个模块文件 = **76 passed**（m4 22 + m3 21 + m2 33）|
| 1/3/4/5/6 | 见 §二 变异矩阵 | ✅ 有牙 | — |

## 二、⭐⭐⭐ 变异矩阵（复核方自己造的，⛔ 不是施工方挑的）

> 判据 = **每个变异 = 一种本项目历史缺陷的形状**；变异后必须至少红一条，否则该方向无牙。

| 变异 | 形状 | 结果 |
|---|---|---|
| **M1** 余段切分摘掉（fragments 恒空）| 换表示丢信息 | ✅ **2 红**（m4 余段锁 + m3 翻转后的 pin）|
| **M2** strict 不再因 ambiguous debt 阻断 | 静默放行 | ✅ **2 红** |
| **M3** 无条件切碎（等长也产 fragment）| 多切／反方向 | ✅ **2 红**（含 `test_equal_coverage_produces_no_fragment`）⇒ **双向都有牙** |
| **M4** 双面墙中线偷偷取 A 面而非中点 | 换个「合理的错答案」 | ✅ 1 红（但见 N2）|
| **M5** 观测间距直接当成事实性厚度 | F-78 病族「把观测量命名成事实性名字」 | ✅ 1 红（`test_three_thickness_names_separated_with_provenance`）|
| **M6** solid_band 中线取带边而非中分 | 同 M4 | ✅ 1 红 |
| **M7** ⛔ **单面墙多解【不再开项】，静默返回** | **设计稿 §6.1 明令禁止的「自动路径」** | ❌ **43 全绿 —— 完全看不见** |
| **M8** 余段 canonical 排序换成插入序倒序 | 规范化被摘 | ❌ 全绿（但见 N1，**未证明有害**）|

⭐ 另附：我在源码里插探针本身让 `test_midline_derived_only_here_and_nothing_written_back` 变红
⇒ **那条锁对源码面的改动是真有牙的**（顺带的正面证据）。

## 三、⛔ 阻断 1 · **`single_face` 通道存货 = 0，设计稿的承重不变量一条锁都没量到**

**⛔ 先排除「变异没跑」**（硬纪律 #5：变异没效果与变异没跑在产物上分不开）——
我做了**四通道存货普查**（每个 `_compile_*` 入口插命中探针，跑全部 43 条）：

```
_compile_paired        260 次
_compile_solid_band     16 次
_compile_single_face     0 次      ← 一次都没跑到
_compile_legacy_trace   35 次
```
且 `_compile_single_face` **只有一个出口**（`return wall, [item], []`），探针就在那唯一出口上。
`tests/test_o22m4_wall_compiler.py` 全文 `single_face` 只出现 **1 次**，还是**双面**那条测试的**名字**里
（`..._survives_as_single_face_fragment`）⇒ **模块 4 的测试里没有任何 `single_face` claim 夹具。**

**为什么这条承重**（设计稿三处逐字）：
- §4.1：`single_face` 是三种正向墙声明之一，**⛔ 不断言 side/thickness**；
- §5.2：「没有唯一 side/thickness 依据时**不得自动造中线**」；
- §6.1：`single_face` 的 side/thickness 多解 ⇒ **先**进入 `open_items`，
  「**即使后续筛成唯一或 Pareto 支配也仍需显式决定/再感知**」，且 `open_items` 是**状态边界**，
  不是能被隔壁自动表重新分类的展示列表。
- 模块 4 自己的 `OpenItemV1` docstring 也写着「⭐ There is ⛔ no auto path」。

⇒ **M7 把这条不变量整个摘掉，43 条测试一条都不红。**
⇒ ⭐⭐⭐ **而且它现在就承重**：GLM 正在施工的模块 5/6 消费的就是 `open_items`，
模块 6 的成功条件第一项是「无 blocking open item」——**一个静默不开项的 bug 会让它自动满足**。
同族 [[gate-teeth-direction-follows-fixture-inventory]]：⛔ 别问「有没有对照物」，
要问「**它声称覆盖的每种量各自有没有被量到**」。

**返工要求（小）**：
1. 加一份 **`single_face` claim 夹具**（`counterface_state` 两种取值各一份更好）；
2. 断言它**产出 `axis_offset_undetermined` 开项**、带候选、带 `IDENTITY_BAN` 排除项；
3. ⭐⭐ **当场证明这条锁能红**：把开项去掉 ⇒ 必须红（⛔ 只报「现在绿」不算交付）；
4. ⭐ 反方向也要一条：**候选被筛成唯一时【仍然】开项**（设计稿 §6.1 那句「即使筛成唯一也仍需显式决定」），
   ⛔ 否则「筛成唯一就自动执行」这条错路照样看不见。

## 四、⚠️ **这条阻断的责任在派工方 —— 题错 #55（累计 55，仍 55/55）**

我写的模块 4 派工单里，`single_face` 出现过 **3 次，全部**是在说**双面墙切出来的余段**
（`single_face_fragment`），**没有一次**是在说 `single_face` 这个 **claim 通道**。
验收表 8 项覆盖了余段/pin/ambiguous/solid_band/厚度/中线/零接线/跑测，
**唯独没有一项要求那个通道**。⇒ 施工方把它实现了，但**没有人要求它被量到**。

⭐ **这与 #52/#53/#54 是同一族**：不是三格对撞拦不住，是**我没有把设计稿里已经列名的东西逐条搬进验收表**。
⇒ **配套解（本轮起执行）**：派工单的验收表，必须与**设计稿里该模块被点名的每一个枚举值/通道**做一次机械对账
——⛔ 不是凭印象挑几条重点。

## 五、不阻断（2 条）

**N1 · 余段的 canonical 排序无锁，但⛔ 未证明有害。**
M8（`sorted` 换成 `reversed`）43 全绿，且探针证明该处**存货充足**（n 最大 21，不是没跑到）。
⚠️ **但我不把它记成缺陷**：`fragments` 由固定元组推导而来，倒序**同样是确定性的**，
`test_same_bundle_and_decisions_produce_byte_identical_resolved_artifact` 比的是**同代码两次跑** ⇒ 恒等类变异，
本来就该绿（[[neuter-proves-wiring-not-discriminating-power]]）。
**真正没被回答的问题**是：两份**不同输入**产生同一组 fragment 但插入序不同时，是否要求同一份 canonical 输出。
⇒ 登记为观察项，⛔ 本轮不要求做。

**N2 · 中线取值的分辨力是「顺带的」，不是有主的。**
M4（双面中线取 A 面）唯一红的那条叫 `test_paired_face_unshared_tail_survives_as_single_face_fragment`
—— 它的**主题是余段**，中线只是它顺带断言的一个值。M6（solid_band 中线）同理。
⇒ 今天有牙，但**这两个方向的牙都挂在别人的测试上**；那两条测试将来一旦重构掉中线断言，
中线方向就静默失去唯一的牙。⇒ 建议随下一次动这块时补一条**以中线为主题**的锁；⛔ 本轮不阻断。

## 六、给主控的一句话
代码我没找到错误，四条通道里三条的锁都经得起变异；**唯一的洞是第四条通道压根没被量到，而那是我派工单的漏项**。
返工量很小（一份夹具 + 三条断言 + 一次变红自证），但**必须在模块 5/6 送审之前补上** ——
因为模块 6 的成功条件正好架在 `open_items` 上。
