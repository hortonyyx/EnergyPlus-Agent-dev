# 施工单 · F-13 正式修法：**内核产出「左上角起笔、逆时针」的规范顶点顺序**

- **日期**：2026-08-06 · **用户已拍板**（实证做满后重新拍的板，路线①）
- **派工方**：orchestrator（Opus 5）· **席位**：Claude 侧 Sonnet 子代理（施工档）
- **工作区**：**主工作树**，开工时 HEAD 应为 `709bc8f` 或更新

## 0. 开工自检

```bash
git log --oneline -1
git status --short     # case_tests/ 下 4 个未跟踪目录属已知，⛔ 不要碰、不要 add
pwd                    # /workspaces/EnergyPlus-Agent-dev
```

---

## 1. ⛔ 先读这条：前一版 F-13 修法**已被轻门否决**，⛔ 不要继承它

裁决书：[`verdict/2026-08-06_f13_orchestrator_lightgate.md`](../verdict/2026-08-06_f13_orchestrator_lightgate.md)
被否决的代码保全在分支 **`f13-wip-2026-08-06` @ `bc4f9d4`**（⛔ 标记 NOT_FOR_MERGE，**不要合并、不要 cherry-pick**）。

**为什么被否决**（一句话）：它让校验器停止「挪起笔点」，而 IDF 声明
`GlobalGeometryRules = UpperLeftCorner, Counterclockwise`，**EnergyPlus 信任这句声明**去推每面的
`~Width`/`~Height`（再喂外表面对流）⇒ 声明变谎话 ⇒ 76/79 个垂直面宽高被判错。

**实证**（本地 EnergyPlus，对账脚本自带「逐面面积与 EnergyPlus 一致」自校验，三次均 115/115）：

| IDF | 声明 | 垂直面 判对/判错 |
|---|---|---|
| 07-02 老件（校验器原样） | `UpperLeftCorner` | **79 / 0** ✅ |
| 前一版 F-13 之后 | 同上 | **3 / 76** 🔴 |

⇒ **校验器那段「挪起笔点」是对的、不能砍。** 主工作树上它**已经是原样未改**（WIP 已挪走），你不需要回滚任何东西。

---

## 2. 本单要做的（用户拍板的路线①）

> **让几何内核直接产出「左上角起笔、逆时针（从外部看）」的顶点顺序**，
> 使校验器那段规范化在内核产物上**变成恒等变换**。

一个动作同时解决三件事：① 严格漂移门自然归零（两层都归零）· ② IDF 声明仍然为真 ·
③ EnergyPlus 宽高正确。

### 2.1 ⭐ 规范的定义：**以现有实现为准，⛔ 不许自己发明**

「左上角」的确切定义**已经存在于代码里**且**已被实证是对的**（07-02 老件 79/0）：
`src/validator/data_model.py` 的 `_get_top_left_corner_from_normal` +
`_sort_vertices_clockwise` 的既有逻辑。

⇒ **把这套规范化提取成一个可被内核复用的纯函数**（放哪你定，但**必须单一实现、两处共用**，
⛔ 不许内核再手写一份"应该差不多"的算法 —— 那就是又造了第二套规范，正是本缺陷的根源）。

⚠️ **注意它做三件事**（前一版派工单只写了两件，是我的题漏了）：
① 保证绕向朝外 · ② 把乱序的点按质心角度排成环 · ③ 把起笔点挪到左上角。
**三件都要在内核侧复用**，不要只搬第三件。

### 2.2 落点

内核最终顶点的**单一出处**是 `BuildingGeometry`（`bg.surfaces[*].verts`），
`serialize_geometry`（`src/agent/geometry/specs.py`）与
`build_output_coordinate_snapshot`（`src/agent/output_coordinates.py:697-718`）**都从它取值**。
⇒ **在 `bg` 定稿处做一次规范化，两个下游自动一致。** 具体位置你自己定并在日志里说明理由。

### 2.3 ⭐ 加一个「校验器改动计数」（非行为改动，纯仪表）

在既有 `validate_points_sorting` 里加：**每当它真的改变了某个面的顶点列表（无论是重排、
换起笔点还是翻绕向），计数 + 记一条日志**（面名/类型/改了哪一类）。
- ⛔ **不改它的行为、不 raise。**
- 取数方式与前一版一致（类方法 + 可 grep 的日志标记均可，你定，日志里说明怎么取）。
- **修好之后这个计数在真链路上应当是 0** —— 它就是「内核与校验器规范是否已统一」的长期探测器。

### 2.4 ⛔ 硬边界

- ⛔ **不改 drift 门**（`src/validator/output_coordinates.py` 的比较逻辑）、不改任何容差、不加任何豁免。
- ⛔ **不改 `GlobalGeometryRules` 的声明值**（`UpperLeftCorner`/`Counterclockwise` 保持不变）。
- ⛔ **不改下游节点提示词**（F-12 刚改完）。
- ⛔ 不碰 `case_tests/` 下 4 个未跟踪目录。⛔ 不 push。⛔ 不许 `git add -A`，逐个文件 add。
- ✅ 改 `src/` 前先 `cp` 备份到 `backup/src_history/2026-08-06_f13_kernel_canonical_order/`。
- ⚠️ 若 `git commit` 撞 `index.lock`（IDE 后台在跑 `git status`）：**等释放再重试，⛔ 不许手动删锁。**

---

## 3. 锁 + neuter

1. **⭐ 恒等锁（零成本，最强的一条）**：内核产出的顶点，喂过 `validate_points_sorting`
   （走真实生产入口 `SurfaceConverter.validate` / `FenestrationConverter.validate`）
   **逐面逐顶点不变**，且 §2.3 的改动计数 **= 0**。
   ⛔ 断言落到具体面名 + 具体顶点，⛔ 不许「长度没变 / 不是 None」。
2. **规范本身的锁**：给若干个已知形状（垂直墙 / 水平楼板 / 天花 / 窗），断言规范化后
   **首顶点确实是左上角、绕向朝外**。
3. **改动计数锁**：喂一个非规范输入（起笔点不对），断言计数 +1 且顶点被改回规范形。
4. **neuter 自验**：把**内核侧的规范化撤掉**（病灶本体），确认第 1 条锁**真的变红**，再逐字节复原。
   ⛔ 只在函数内部包一层 = 假锁。日志写清红了几条、红在哪条断言。

---

## 4. 验收

### 4.1 确定性（零成本，必须先做完）

- 三条锁全绿、neuter 红得对。
- **全仓零回归**：主工作树基线 = **2247 passed / 10 xfailed / 0 failed**。
  ⚠️ **预期会有既有测试因内核顶点顺序变化而红**（快照/序列化/坐标类）。
  ⇒ **逐条在日志里说明：这条原本断言什么、为什么新顺序才是对的、你怎么改的。**
  **⛔ 不许为了让新行为过就直接删旧断言。** 拿不准就停下上报。

### 4.2 真链路（用户已授权烧 DeepSeek 按量费）

用与前次相同的中间产物跑下游
（`case_tests/e2e_tests/sm21_anchor/run_2026-08-06_wall3_a_retest/5_intakeoutput/intake_output.json`，
输出目录另起一个，⛔ 不要覆盖 `EP_f13_verify`）：

⚠️ **防假绿**：跑之前先确认冻结快照真的喂进去了 ——
`load_intake_bundle(...).validation_context.raw_snapshot_bytes` **非 None**（上次实测 49416 bytes）。
拿不到快照时漂移门整段跳过，那样的"绿"是假的。

**四个数字，逐条给证据**：
1. **A 层漂移 = 0**（ConfigState vs 快照）。
2. **B 层 = 0** —— 判据是管线末行**不出现**
   `Pre-EnergyPlus gate failed: N issue(s) (... output-coordinate)`。
   ⚠️ **`VERTEX_FRAME_DRIFT` 这个字串不出现在管线 stdout 里**，⛔ 别用 grep 它的方式量（会得到假的 0）。
3. **⭐ 宽高对账 79 判对 / 0 判错**：
   `python3 /tmp/claude-0/-workspaces-EnergyPlus-Agent-dev/77f172f3-9153-4e80-b6fc-d05994bb60b8/scratchpad/wh_audit2.py <idf> <eio>`
   —— **必须先看到脚本自带的「面积与 EnergyPlus 一致 115/115 ✅」才采信结果**。
   拿 eio 需要在 IDF 末尾追加 `Output:Surfaces:List, Details;` 后本地跑一次 EnergyPlus
   （`-x -w data/weather/Shenzhen.epw`，**必须带 `-x`**，否则 HVACTemplate 会 Fatal）。**本地 EP 不烧任何 LLM 额度。**
4. **§2.3 的校验器改动计数 = 0**。
5. **EnergyPlus 跑通 `0 severe`**。

若在更后面撞到**新的**墙：**不算你的锅**，如实登记现象 + 定性，**⛔ 不要顺手修**。

---

## 5. 交付

- 执行日志 `AI_agent/logs/reviews/execution/2026-08-06_f13_kernel_canonical_order_claude.md`。
- 可 `git commit`（message 仿 `08.06_f13_kernel_canonical_vertex_order`，body 含 ①改动 ②为何此刻 ③影响）。⛔ 不 push。
- 最终回复 TL;DR：① 规范化提取到哪、内核在哪调 ② 三条锁各断言什么 ③ **neuter 红了几条红在哪**
  ④ 既有测试红了几条、逐条怎么处理 ⑤ **真链路五个数字** ⑥ 全仓数字 ⑦ commit SHA ⑧ 新墙（若有）。

## 6. 停下上报（**记功不记过**）

本轮 **10 次「停下上报」，10 次全是派工方（我）的题错了**；
**另有两次是施工席没上报、由 orchestrator 轻门查出的框架性错误**（其中一次就是前一版 F-13）。
⇒ 本单事实与你看到的不符、或验收条件之间打架、或你认为路线①本身有问题
⇒ **立刻停下如实上报，⛔ 不要硬凑。**

**特别地**：如果你发现「把校验器那套规范化搬到内核」在结构上做不到（比如内核那层拿不到判定"朝外"
所需的 interior points），**⛔ 不要自己发明一套近似的**——停下上报，这正是本缺陷的成因。
