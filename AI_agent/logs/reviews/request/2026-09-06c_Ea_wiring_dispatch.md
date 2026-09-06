# 派工单 · **E-a：把 A-6 那条链接进生产路径**（闸④ 端到端接线）

## 〇 状态与分工

- **施工方**：`gpt-6-astra`（整块交付）· **审**：**Claude 家族**（⛔ 不得 GPT = 施工方家族）
- **基点**：主线 HEAD `f4ee52da`（A-11 与 A-6 均已合并，权威全量 `3907 passed / 0 failed`）
- **工作目录**：`/tmp/ea_wiring_astra`（`wt/09.06c_ea_wiring`）
- ⚠️ **本单是【接线】，⛔ 不是重写 B4、⛔ 不是改 reading、⛔ 不是动判分器。**

## 一 ⭐⭐⭐ 事实基线（主控 2026-09-06 只读实测，⛔ 非转引、⛔ 非推测）

> ⚠️ **09-05 起草的那份 E-a 草稿的承重前提已作废** —— 它写的是「B4 配对模块今天零生产调用者 ⇒ 本单是接线」。
> **A-6b 今天合并时已经把 B4 接上了。** 本节是重量后的基线。

```sh
# ① B4 配对现在【有】调用者了
grep -rn 'synthesize_openings' src/ scripts/ --include=*.py | grep -v 'opening_synthesis.py'
#   src/agent/correction/opening_adjudication.py:19   (import)
#   src/agent/correction/opening_adjudication.py:198  (调用)

# ② 但链条断在更靠前：pipeline 完全不知道 A-6 存在
grep -c 'opening_adjudication\|tick_claim\|OpeningReview\|TickSession' src/agent/pipeline.py
#   0

# ③ CorrectedGeometryV3 的【真实构造点是 2 个】
grep -rn 'CorrectedGeometryV3(' src/ scripts/ --include=*.py
#   src/agent/correction/multifloor.py:583
#   src/agent/correction/projection_bridge.py:845
#   ⚠️ schema.py:446 是【类定义本身】，⛔ 不是构造点（⭐ 别把 grep 命中数当构造点数）
```

**⇒ 链条现状：**

```
pipeline.py ──✗ 断在这里 ── OpeningReview ──✅ A-6b 已接 ──> synthesize_openings (B4)
             grep = 0 命中
```

`pipeline.py`（2754 行）已经 import 了十几个 `src.agent.correction.*` 模块，
**但没有一个是 A-6 的**（`tick_claim` / `opening_adjudication`）。**本单要接的就是这一段。**

## 二 本单的三条硬验收（逐字取自 `AI_agent/plan.md` 的 E-a 行，⛔ 非我转述）

这三条的来历要知道：A-6 施工方按「**指不到强制行就把那句删掉**」这条合法出口，
从契约里删掉了三句**只能由接线方兑现**的承诺。跨家族审判定「缺口是真的、删句没消除它、
只是让它从文档里消失」⇒ 主控把它们登记成本单的验收项。**你就是那个接线方。**

> **E-a-1**（原 C:11）`CorrectedGeometryV3` 装配消费洞口结果时**必须**走
> `OpeningReview.consume`/`scoreable_openings`，⛔ **不许把历史 JSON 当成当前有效批次**
> —— 验收 = **一条走真实入口的锁，喂一份过期 batch 必须红**。
>
> **E-a-2**（原 C:83）持久化时**必须**一起落 `TickPacket` 的两份源 bytes 与 `TickBatch.record`，
> ⛔ **不许只存预览坐标** —— 验收 = **从落盘件能逐字节重建 `batch_id`**。
>
> **E-a-3**（原 C:130）接线后**旧 B4 低层 dict API 必须没有生产调用者**
> —— 验收 = **一条 `grep` 锁**（同 F-107 的写法）。

⚠️ 这三条今天**零流量**（新 API 尚未接线）—— 接完线它们才第一次有真实流量。
⛔ **别把「锁写好了」当成「验过了」**：每条锁都要**当场证明它能变红**。

## 三 ⭐⭐⭐ 必须先量、再决定怎么做的一个开放问题

2026-09-03 B4 执行档的原文读数（逐字）：

> **T3「区间相等」在真实数据上的读数**：立面 `x_range_m` 是**像素标定外推**
> （真实四立面 `mm_per_px ≈ 13.6 mm/px`），平面是 0.1 mm 网格 ⇒ 真实四立面
> 配对 = **0 对、全部进 unmatched**（两侧差 1–3 个网格单位）。**这是 reading
> 侧精度现状的读数，不是配对判据的缺陷**；判据按验收 #3 零容差「拒绝不猜」。
> 锁只锁完备性（配对+拒绝 == 全部，双侧），⛔ 不锁「必须 0 对」——钉住缺陷
> 本身的存在是反模式（reading 精度提升后那把锁会假红）。

⭐ **但 A-6 之后，立面 `x_range_m` 的来源变了** —— `_elevation_document()` 是从
`TickSession` 的**链档 mm 值**出的，⛔ 不再是像素标定外推。

⇒ **本单第一步：接线后在真实四立面上量一次配对数。**
- ⛔ **不许假设它变了，也不许假设它没变** —— 量。
- 交出**每张立面的配对数 + 未配对的具名原因**，⛔ **不许只报总数**。
- ⭐ 如果**仍是 0 对**且你论证下来病根**不在接线** ⇒ **A 层停报**。
  那是 reading 侧精度的事，⛔ **别在接线单里改 B4、改 reading、或加容差**
  （上面那段原文已经写明：**不锁「必须 0 对」**，因为钉住缺陷本身是反模式）。

## 四 硬约束（都来自已经咬过人的坑）

- ⛔ **可见性判定不许用 bbox 极值抄近路** —— B4 的 docstring 点名了这条捷径；
  哪些平面洞口是这张立面的候选，归 `facade_visibility` 管。**给一条锁证明没有退化成 bbox 极值。**
- **朝向必须来自签字过的 `facade_convention`**，⛔ **不许在调用点现编**
  （B4 原文：`mirrored`/`local_x_positive` "resolved fail-closed through the signed convention；
  本函数 ⛔ 从不猜方向"）。
- ⭐ **必须有一条锁证明「不声明 `elevation_source` 就退不了债」** ——
  债只在 `affected_refs` **恰好点名这一个实例**时退役（South 只退 South 的债）。
  **那是 B4 返工 1 花一轮才买回来的性质，接线时最容易被顺手绕过。**
- **交 judge 必须以 strict 进入**（plan.md 闸④ 早有记录）。
- **身份从 bundle 的 `source_artifacts[0]` 提取**，⛔ **不许手拼**。
- ⛔ **不碰**：`src/agent/judge/score_service.py`（判分线，那是 J 的活）· 旧层 `gt/*/gt.json`（答案根）·
  `src/agent/judge/as_measured.py`（A-11 刚落）· `reading_grade.py` / `denominator.py`（J 的活）。

## 五 跑测与纪律

```sh
cd /tmp/ea_wiring_astra && \
python -c "import src.agent.pipeline as p; print(p.__file__); import src.agent.correction.opening_adjudication as o; print(o.__file__)" && \
python -m pytest -q -n 6 -p no:cacheprovider
```

- ⭐⭐⭐ 两条 `m.__file__` **必须落在 `/tmp/ea_wiring_astra` 里**（承重不变量，⛔ 不是 `.pth` 哈希）。
- ⛔ 一律 `-n 6`。**判跑完看汇总行**，⛔ 不看退出码文件、⛔ 不用 `nohup`。
- **基线是 `3907`**（主树权威全量，逐位闭合 `3907+2+13=3922` 差额 0）。
  逐位闭合**你自己数**：`3907 + 你新增的条数 = 新读数`，差一条都要说明差在哪。
- ⛔ `pip install -e .` 或任何写 `site-packages` 的命令。
- ⛔ `git add -A`；逐路径 add，commit 前看 `git show --cached --numstat`。
- ⚠️ `.gitignore:258` 有 `*.txt`，新增 txt 证据必须 `git add -f`，否则**静默丢件**。
- ⭐⭐⭐ **必须分段提交** —— 09-05 你在 A-6 那单里**三次**撞 provider 容量退出，
  **三次都在活干完之后**，靠分段提交才一行代码没丢。

## 六 交件

`AI_agent/logs/reviews/execution/2026-09-06c_Ea_wiring_execution.md`，必须含：

- **§三 那次测量**：每张立面的配对数 + 未配对的具名原因（原文输出）
- **E-a-1/2/3 三条各自的锁在哪一行、以及【当场证明它能变红】的命令与输出**
- **接线点清单**：你在 `pipeline.py` 的哪几处接的、`CorrectedGeometryV3` 的两个构造点各怎么处理
- **完整全量汇总行 + 逐位闭合**（自己数）
- **最薄弱一处**（⛔ 不许写「无」）

⛔ 不许留占位符。

## 七 ⭐ 停下上报（分层）

- **A 层（停）**：① 真实四立面配对**仍为 0 对**且你论证下来**病根不在接线**
  （⭐ 先穷尽再下结论，写出穷尽过程）② 本单的承重前提你发现是错的
  ③ 要动 §四/§五 禁令 ④ 会改到已落库产物的哈希或已签字基线。
- **B 层（记一条继续）**：行号 / 措辞 / 外围数值不一致。

> 本项目至今 **69/69** 次「停下上报」全部是**派工方的题出错** ⇒ 该停就停，⛔ 不要自行绕路。
