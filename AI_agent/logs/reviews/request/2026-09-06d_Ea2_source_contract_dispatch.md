# 派工单 · **E-a′：让洞口裁决改吃生产格式**（闸④ · ⛔ 取代 `2026-09-06c_Ea_wiring_dispatch.md`）

## 〇 状态与分工

- **施工方**：`gpt-6-astra`（整块交付）· **审**：**Claude 家族**（⛔ 不得 GPT = 施工方家族）
- **基点**：主线 HEAD `363844b3`（⭐ **必须用这个** —— 它含本单引用的 09-06 口径改写；用更早的基点你会读到已作废的题面）
- **工作目录**：`/tmp/ea2_astra`（`wt/09.06d_ea2_source_contract`）
- ⛔ **上一单（`2026-09-06c`）的题面已作废** —— 它写「本单是接线」，你上一轮 A 层停报是**对的**。本单是重出的题。

---

## 一 ⭐⭐⭐ 事实基线（主控 2026-09-06 只读实测，⛔ 非转引、⛔ 非推测）

### 1.1 你上一轮停报的实测**成立**，但停报单给的**题面错了**

你测出：没有平面产物同时被两边接受。**这条是对的。** 但那份单子把它定性成
「**两个不同的洞口全集**，需要拍哪套权威」——**主控重量后推翻了这个定性**：

```sh
# 两种格式的【面线】逐条同一
#   v0: wall_bands 23×2 个配对面 + unpaired_face_lines 3 条 = 49
#   v2: observations.face_lines                              = 49        差 0
#   逐条按 pos_px 匹配（<0.6 px）: 49/49        2F 同理 46/46
```

⇒ **它们是同一张图的同一次测量。** `51 vs 85` 是**粒度**差：v0 按「每堵墙」数洞口（配对**之后**），
v2 按「每条墙面线」数空档（配对**之前**），一堵墙两个面。
⭐ **ID 交集为空 ≠ 不同全集** —— 那只是两层各自的命名，不是两套答案。

> ⚠️ 主控自己在这上面栽过一次：第一次拿区间重叠去比，得出「438 个匹配」——
> 那是**跨不同面线直接比一维数值**，数已作废。**你若要复算，必须先确认两边同轴同线。**

### 1.2 ⭐⭐⭐ 真病根：**A-6 认了一个没有生产产出方的格式**

```sh
grep -n "only producer" src/agent/reading/vector_contract.py   # :75 自陈（⭐ 注释是英文）
#   "Historical as-drawn prototype values. ⚠️ Registered as LITERALS on purpose:
#    their only producer is the 2026-08-23 prototype under AI_agent/logs/experiments/,
#    which is not importable production code."

grep -rn '"wall_bands"' src/ --include=*.py | grep -v /tests/
#   tick_claim.py:319       ← 读
#   vector_contract.py:272  ← 认
#   ⇒ 零写入方。src/ 里没有任何代码【产出】 as_drawn_plan_v0。
```

而生产 reading 模块 [`as_drawn_v2.py`](../../../../src/agent/reading/as_drawn/as_drawn_v2.py)`:584` 产的是 `as_drawn_plan_v2`
（⭐ 该常量**定义在** `as_drawn/schema.py:112`、在 `as_drawn_v2.py:66` **转出**，⛔ 不是在 v2 里定义的 —— 引用时别写错处）。

**⇒ A-6 平面侧只认一个生产上已经不存在的格式。** 这不是接线缺一段，是源契约认错了对象。

### 1.3 ⭐ 生产格式是**严格超集**，你要的配对信息本来就在里面

sm25 1F 实测（`AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out/sm25_1f_v2.json`）：

| 生产格式里的东西 | 数量 | 它是什么 |
|---|---|---|
| `observations.face_lines` | 49 | 量出来的墙面线 |
| `hypotheses.pair_candidates` | 374 | **代码列的全部同轴线对，⛔ 无阈值** |
| `hypotheses.pairs` | 22 | **模型选出来的「这两条是一堵墙」** |
| `hypotheses.opening_candidates` | 85 | 每条面线上的空档，⛔ 无分类无阈值 |
| `non_wall_face_lines` / `unpaired_wall_faces` / `solid_band_walls` / `ambiguous_face_lines` | — | 四类兜底 |

代码自陈（`as_drawn_v2.py:301`）：**「⭐ 认 comes in from OUTSIDE」** —— 配对结论由外部感知件供入，
`select_pairs()`（:493）只做「从候选里按模型的选择挑出来 + 记账」。
⇒ **正是[指南 §一](../../../guides/reading_correction_split_guide.md)「哪两条线是一堵墙 = 配对，归模型」的形态。**

对照之下，v0 那 23 堵墙带着 `declared_thickness_candidates_mm: [240, 120]` ——
是**代码按声明厚度配的**，正是 2026-08-23 用户换掉的那个机制。
⭐ **代码配出 23、模型配出 22 —— 本来就不是同一个判断。**

---

## 二 ⭐⭐⭐ 本单的题 = **枚举这一类**，⛔ 不是「改一处读入口」

> **这么问的理由（上一轮的实证）**：A-6 返工 1 时，跨家族审**按症状**只找到 1 个洞；
> 返工单改问「`submit()` 每项检查、`consume()` 各自重做了没有？**逐项列表**」
> ⇒ 交回 17 项表，**另外 6 项从未重做**。**那张表本身就是交付物。**

### 2.1 交付物 ① —— 消费对照表（⛔ 缺它整单不合格）

**生产格式（`as_drawn_plan_v2`）里的每一样东西，洞口裁决这条链各自消费了没有？** 逐项列表，每行四列：

| 生产格式的字段 | 谁该消费它 | 现在消费了吗 | 若「结构上不必」——**被绕过后坏数据流到哪、谁接住** |
|---|---|---|---|

- **必须逐项，⛔ 不许只列你改动的那几项。** 至少覆盖 §1.3 表里的每一行，
  外加 `declarations.*`（厚度标注 / 尺寸链 / 图框）与 `observations.dimension_witnesses`。
- ⭐ **允许「结构上不必消费」这一档**，但那一档**每条都要写清最后一列**，⛔ 不许只写「不必」。
- ⚠️ **这张表的外延是你自己划的** ⇒ 复核方会用**两套互不依赖的口径**独立枚举来对它，
  所以**宁可多列**。漏项比误列贵得多。

### 2.2 交付物 ② —— 改完的读入口

让 `tick_claim` / `opening_adjudication` 的**平面侧**从 `as_drawn_plan_v2` 取数：
洞口来自 `hypotheses.opening_candidates`，配对来自 `hypotheses.pairs`（⛔ 不是自己重配）。

⛔⛔ **明令禁止：不许写「先把生产格式转成 v0 再喂进去」的转换层。**
理由（用户 2026-09-06 拍板时的原话口径）：转换层要替模型做「哪两条线是一堵墙」这个决定，
**等于把 08-23 换掉的机制请回来**；而且以后 reading 产物一改就得跟着改。
⭐ 这是本单最省事的实现路径，所以在这里堵死。**若你论证下来非转换层不可 ⇒ A 层停报，⛔ 不许自行采用。**

### 2.3 v0 怎么处置

- **本单不删 v0 分支**（历史实验件还要能读），但要让「它没有生产产出方」这件事**在代码里可见**：
  给 v0 分支加一条**明确的登记**（注释 + 一条锁），说明**唯一产出方是 08-23 实验原型**。
- ⭐ **若你发现 v0 分支删掉后全仓仍绿且无历史件依赖** ⇒ **不要顺手删**，写进交件让复核方判。
- ⚠️⚠️ **`vector_contract.py` 是本单唯一与 J 单重叠的文件**：J 单要**只读复用**它的分类器。
  ⇒ 你可以改它，但 ⛔ **不许改动分类器的公开行为**（现有契约的判定结果、返回类型、异常面）。
  改了公开行为 ⇒ **A 层停报**，由主控决定两单谁先合并。

---

## 三 硬验收（⛔ 缺一不合格；每条都要**当场证明它能变红**）

三条**逐字取自** `AI_agent/plan.md` 的 E-a 行（⛔ 非我转述）。来历：A-6 施工方按「指不到强制行就删句」
这条合法出口，删掉了三句**只能由接线方兑现**的承诺；跨家族审判定缺口是真的 ⇒ 登记成本单验收项。**你就是接线方。**

> **E-a-1**（原 C:11）`CorrectedGeometryV3` 装配消费洞口结果时**必须**走
> `OpeningReview.consume`/`scoreable_openings`，⛔ **不许把历史 JSON 当成当前有效批次**
> —— 验收 = **一条走真实入口的锁，喂一份过期 batch 必须红**。
>
> **E-a-2**（原 C:83）持久化时**必须**一起落 `TickPacket` 的两份源 bytes 与 `TickBatch.record`，
> ⛔ **不许只存预览坐标** —— 验收 = **从落盘件能逐字节重建 `batch_id`**。
>
> **E-a-3**（原 C:130）接线后**旧 B4 低层 dict API 必须没有生产调用者**
> —— 验收 = **一条 `grep` 锁**（同 F-107 的写法）。

**⭐ 本单新增两条：**

> **E-a-4** 喂一份 `hypotheses.pairs` 为**空**（或 `pairs_status != "SELECTED"`）的生产产物，
> **必须响亮失败**，⛔ **不许静默当成「这层没有墙」**。
> 理由：配对是模型那一拍，模型可能没做、做失败、或只做了一半 —— **缺席不等于零**。
>
> **E-a-5** 喂一份 `schema` 是注册值、但**缺 `hypotheses` 键**的文件，必须走**已命名的**拒绝路径，
> ⛔ 不许因为"能 parse"就放行（= `vector_contract.py` 文件头 #5 的 BLK-A 形态，F-97 的老病）。

⚠️ E-a-1/2/3 今天**零流量**（新入口尚未有真实数据走过）⇒ ⛔ **别把「锁写好了」当成「验过了」**。

---

## 四 硬约束（都来自已经咬过人的坑）

- ⛔ **可见性判定不许用 bbox 极值抄近路**（B4 docstring 点名）；给一条锁证明没退化成 bbox 极值。
- **朝向必须来自签字过的 `facade_convention`**，⛔ 不许在调用点现编。
- ⭐ 必须保住「**不声明 `elevation_source` 就退不了债**」这条性质（B4 返工 1 花一轮买回来的，接线时最容易被顺手绕过）。
- **交 judge 必须以 strict 进入**；**身份从 bundle 的 `source_artifacts[0]` 提取**，⛔ 不许手拼。
- ⭐ **A-6-d1 若你恰好动到 `_elevation_document()`**：顺手补上 PLAN 侧已有、ELEVATION 侧缺的那层
  `lo<hi` 对称拦截（plan.md A-6-d1，原话「下次触碰时补」）。⛔ 不触碰就别动。
- ⛔ **不碰**：`src/agent/judge/score_service.py` · `reading_grade.py` · `denominator.py`（**这三个是同期在飞的 J 单的活**）·
  旧层 `gt/*/gt.json`（答案根）· `src/agent/judge/as_measured.py`（A-11 刚落）。

---

## 五 跑测与纪律

```sh
cd /tmp/ea2_astra && \
python -c "import src.agent.correction.tick_claim as t; print(t.__file__); \
import src.agent.correction.opening_adjudication as o; print(o.__file__)" && \
python -m pytest -q -n 6 -p no:cacheprovider
```

- ⭐⭐⭐ 两条 `m.__file__` **必须落在 `/tmp/ea2_astra` 里**（承重不变量，⛔ 不是 `.pth` 哈希）。
- ⛔ **一律 `-n 6`** —— **本单与 J 单同期在飞**，同机三路各跑 `-n auto` 会把全量跑崩（无 summary 行的假红）。
- **判跑完看汇总行**，⛔ 不看退出码文件、⛔ 不用 `nohup`。
- **基线 `3907`**（主树权威全量，逐位闭合 `3907+2+13=3922` 差额 0）。逐位闭合**你自己数**，差一条都要说明差在哪。
- ⛔ `pip install -e .` 或任何写 `site-packages` 的命令（venv 全机器共享）。
- ⛔ `git add -A`；逐路径 add，commit 前看 **`git diff --cached --numstat`**（⛔ `git show` 不接 `--cached`）。
- ⚠️ `.gitignore:258` 有 `*.txt`，新增 txt 证据必须 `git add -f`，否则**静默丢件**。
- ⭐⭐⭐ **必须分段提交**（每完成一个能独立成立的小步就 commit）—— 09-05 你在 A-6 那单里**三次**撞
  `Selected model is at capacity`，**三次都在活干完之后**，靠分段提交才一行代码没丢。
  ⭐ **容量 ≠ 额度**：探针当场 `PROBE_OK` 就能续，⛔ 别当额度耗尽自行改派。

---

## 六 交件

`AI_agent/logs/reviews/execution/2026-09-06d_Ea2_source_contract_execution.md`，必须含：

- **§2.1 那张消费对照表**（⭐ 头号交付物）
- **E-a-1..E-a-5 五条各自的锁在哪一行 + 当场证明它能变红的命令与原文输出**
- **改动点清单**：读入口改在哪几处、`pairs` 从哪取、v0 分支怎么登记的
- **完整全量汇总行 + 逐位闭合**（自己数）
- **最薄弱一处**（⛔ 不许写「无」）
- ⭐ **自设两条同形路径**：说出两条「本单的防线可能被绕过」的路子，并各给一条实测

⛔ 不许留占位符。

---

## 七 ⭐ 停下上报（分层）

- **A 层（停）**：① 本单的承重前提你发现是错的（⭐ **含 §1.3 那张表**：若生产格式里**并没有**你需要的某样东西）
  ② 非写转换层不可 ③ 要动 §四 禁令 ④ 会改到已落库产物的哈希或已签字基线。
- **B 层（记一条继续）**：行号 / 措辞 / 外围数值不一致。

> 本项目至今 **70/70** 次「停下上报」全部是**派工方的题出错** —— **包括你上一轮那次**。
> ⇒ 该停就停，⛔ 不要自行绕路。
