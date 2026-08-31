# 微单 · **NF-1**：空骨架产物仍被认成合法 as-drawn 计划

- **日期**：2026-08-30 · **派工方**：orchestrator · **施工方**：⏳ **待排**（Claude 家族撞额度，等 GLM/GPT 腾出）· **审**：与施工方不同家族
- **来源**：模块 1 跨家族审的 **NF-1**（不阻断）→ [裁决](../verdict/2026-08-30_o22m1_crossreview_glm.md)
- ⭐⭐⭐ **复核方已在 `/tmp` 副本上把这条路整个走通了，读数可直接当施工依据** —— 本单不是探索，是**照着做**。

---

## 一、要修什么（复核方 B1/B2/B3 的实测结论）

**缺键形态** `{"schema":"as_drawn_plan_v2","observations":{},"declarations":{},"hypotheses":{}}`
今天被认成**合法** `as_drawn_plan`。而 `assemble()` **无条件**产出 `face_lines` 键
（`as_drawn_v2.py:599`）⇒ **缺键产物生产者根本造不出来**，只可能是手造或损坏。

⭐⭐⭐ **必须分清两种形态，答案相反**（复核方 B2 的裁定，⛔ 别合并）：

| 形态 | 该怎么判 | 为什么 |
|---|---|---|
| **缺键** `{"observations": {}}` | ⇒ **响亮 UNKNOWN** | 生产者造不出来 ⇒ 这一层该管 |
| **空列表** `{"face_lines": []}` | ⇒ ✅ **仍然路由成 `as_drawn_plan`**（账面记「as-drawn 计划、零面线」）| 诚实读图在一张空图上就会产出它。⛔ **在类型层拒它 = 把结构校验冒充内容判断**，会把「诚实的零测量」判成「不合法」。「量到零」归**判分（0 分）**与 zero-wall 门 |

## 二、怎么做（复核方已代跑通，⛔ 别再自己设计）

1. `schema.py` 的 `face_lines: list[FaceLineV2] = Field(default_factory=list)` 改为**必填无默认**
   （**键必须在；空列表仍合法**）；
2. `tests/test_f97_vector_contract.py` 里 **8 处** `"observations": {}` 注入**一条 14 字段的最小真实面线**
   （含 `gaps: []`、两条 run、区间钉长度 2）。
   ⚠️ 其中 **`:629` / `:630` 两处是故意残缺的 malformed 夹具** —— 它们因缺 `declarations`/`hypotheses` **依旧残缺**，
   ⛔ 别把它们「修好」。
3. 翻自钉的 **1 条 pin**（`test_the_declared_skeleton_is_still_recognised`）。

**复核方在 `/tmp` 上的读数**（你必须自己复跑一遍，⛔ 不许转引）：
> 跑两个文件：**79 条 F-97 全绿（130 passed）**；唯二红 = 自钉的两条 pin，**都是「翻 pin」的预期红，不是撞锁**。
> 裸骨架 → **响亮 UNKNOWN**，reason = "declares schema='as_drawn_plan_v2' but no registered contract has that value with a matching key set"。

⚠️ **复核方并纠正了施工方的计数**：施工方报「三处」，**实测 = `test_f97` 里 6 处 + 模块 1 自建 2 处**。

## 三、⛔ 禁令

1. ⛔ **不许改 F-97 的任何断言** —— 本单只改**夹具载荷**。（复核方实测：断言零变动即可通过。）
2. ⛔ **不许把「空列表」也拒掉** —— 见 §一 表，那是**另一半、且方向相反**。
3. ⛔ **不许动 `:629`/`:630` 两处故意残缺的夹具**。
4. ⛔ 不许 `git add`/`git commit`/`pip install -e .`/`-n auto`/跑全量。
5. ⛔ 不许改任何已落库产物或任何进 `canonical_bytes` 的 schema 面（**三格对撞第 ③ 格**，题错 #51 的教训）。

## 四、验收（4 项）

| # | 验收项 | 对撞检查 |
|---|---|---|
| 1 | 缺键骨架 ⇒ **UNKNOWN 且 reason 响亮**；**空列表 ⇒ 仍是 `as_drawn_plan`** | 与禁令 2 对撞：**若你把空列表也拒了，本条必然不通过** |
| 2 | `pytest -n 4 tests/test_f97_vector_contract.py tests/test_o22m1_as_drawn_producer_types.py` ⇒ **F-97 侧全绿**，翻完 pin 后应全绿 | 与禁令 1 对撞：F-97 断言零变动 |
| 3 | 给出 `git diff --numstat`，证明 **F-97 文件里没有一行是断言改动** | 同上，机械可查 |
| 4 | 列全改动路径（⛔ 不提交）| 与禁令 4 一致 |

## 五、停下上报（分层）
**必停**：复核方那三条读数**复现不出来**（79 全绿 / 唯二红是 pin / 裸骨架响亮 UNKNOWN）；或既有锁变红。
**只记不停**：夹具字段命名分歧 · 8 处的具体行号与裁决书有出入。
