# 派工单 · **模块 2 第三方向**：通道声明 `absent`，包里却**带着这条通道的载荷**

- **日期**：2026-09-01 · **派工方**：orchestrator · **施工方**：⏳ **待排**（⛔ 与写 `evidence_contract.py` 的席位不得并行）· **审**：与施工方不同家族
- **基线**：**`58bb59f`** · **权威全量**：**3519 passed / 13 xfailed / 0 failed**
- **来源**：模块 2 二轮返工时**施工方自己点名**「第三方向至今无门、未登记，留你定夺」；
  主控已**独立复现**（下面 §一 的读数是主控自己跑的，⛔ 不是转引）→
  [裁决](../verdict/2026-09-01_o22m2_rework2_crossreview_claude.md) §二

---

## 一、承重前提（**主控亲手量的**，⛔ 请自己复核，不符就停下上报）

在 `58bb59f` 的独立 worktree 里，用测试自己的 `_tiny_artifact()` 构造：

```
基线正常 bundle 通过 ✅   wall_claims=2  face_dispositions=4  opening_claims=1
  channel_status = [dimensions:absent, elevation_openings:absent,
                    plan_openings:present(tiny), room_roles:absent, walls:present(tiny)]

① walls      改成 absent + missing_channel debt，而 2 条 wall claim / 4 条 disposition 照旧在包里 ⇒ ❌ 放行
② plan_openings 改成 absent + missing_channel debt，而 1 条 opening claim 照旧在包里            ⇒ ❌ 放行
```

**机制（机械可查）**：`evidence_contract.py` 里那两道新门
（`_assert_channel_payload_closure` 与 `_assert_channel_source_closure`）
**都以 `if status.state != "present": continue` 开头** ⇒ **声明成 `absent`，两道门一起让路。**

⭐⭐⭐ **这是同一病族的第三个载体**：
| 轮次 | 载体 | 状态 |
|---|---|---|
| 一轮 | **全局空载荷**（说 present 却什么都没有）| ✅ 已堵 |
| 二轮 | **错误来源的载荷**（说来自 A，其实来自 B）| ✅ 已堵 |
| **三轮 = 本单** | **`absent` 却带着载荷**（干脆不声明，门就不看了）| ❌ **无门** |

⇒ [[gate-measures-right-but-carrier-gets-swapped]]：⛔ **别只把门的阈值加严** ——
前两轮都不是「门算错了」，是**它量的那个东西被换掉了**。本轮请直接问：
**「`state` 这个字段本身，是不是又一个可以被换掉的载体？」**

## 二、任务

**让「声明」与「载荷」在两个方向上都必须一致**，⛔ 而不是只在 `present` 这一侧检查：
- `present` ⇒ 必须有载荷（已做）+ 载荷来源必须在声明里（已做）；
- **`absent` ⇒ 包里必须【没有】这条通道的载荷** ——
  有载荷却声明 absent ⇒ **响亮失败**（⛔ 不是记 debt 放行）。

⭐⭐⭐ **派工方的方向（推荐但不指定）**：与其在 `absent` 分支再加一道对称的门，
不如问**有没有一个量能一次覆盖两侧** —— 例如让「通道 → 载荷成员」成为**一张显式的映射**，
校验器对**每条通道**（不分 state）各算一次「实际载荷集合」，再与 `state` 对账：
非空 ⇔ `present`、空 ⇔ `absent`（`zero_payload_channel` 是 `present` 侧唯一的合法例外）。
⇒ 这样 `state` 就**不再是一个能单独被换掉的载体**，而是一个被推导出来的对账结果。
⛔ **明确不许**：① 只加一个 `if state == "absent"` 的镜像分支就交（那是第四次等着被换载体）；
② 用词法/命名匹配来判断「这条通道有没有载荷」。

⭐ **第三条路很可能存在而我没想到**（[[dispatch-options-list-is-itself-a-hidden-premise]]）：
若你找到严格更优的做法，**直接走它并说明**。

## 三、⛔ 禁令
1. ⛔ 不许改任何既有断言去迁就新门；既有 **33 条**锁必须仍全绿。
2. ⛔ 不许动 `evidence_adapters.py`（模块 3 已收口）/ `wall_compiler.py`（模块 4 送审中）/
   `decision_schema.py` / `decision_executor.py`（模块 5/6 施工中）。不够用 ⇒ **停下上报**。
3. ⛔ 不许动 `vector_contract.py` / `pipeline.py` / `src/agent/judge/`。
4. ⛔ 不许改已落库产物 / 进 `canonical_bytes` 的面 ——
   ⚠️ **第三格对撞**：若你的改动会改 bundle 的 `content_sha256`，**停下上报**（题错 #51/#54 的教训）。
5. ⛔ 不许 `git add`/`commit`/`pip install -e .`/`-n auto`/跑全量。
6. ⛔ 不要在 `.py` 字符串常量里写带仓库根前缀的生产文件路径（F-152）。

## 四、验收表（⭐ 已按**三格**对撞）

| # | 验收项 | 对撞检查 |
|---|---|---|
| 1 | ⭐ **§一 的两个反例从放行变响亮**（walls / plan_openings 各一），且**先绿后红自证**（先断言改动前确实放行）| 本项目口径：只有负向断言的门恒红、不可观测 |
| 2 | ⭐⭐ **反方向不许误杀**：真正没有载荷的 `absent` 通道（`dimensions` / `room_roles` / `elevation_openings` 三条，以及 walls 真空跑）**必须仍然放行** | ⛔ 与任务对撞：**只做前者会把正常的 absent 全判红** |
| 3 | ⭐⭐⭐ **合法出口保留**：`walls=present + zero_payload_channel(walls)` **仍须放行** | ⛔ 与模块 2 一轮已收口的语义对撞 |
| 4 | ⭐⭐⭐ **neuter 对撞**：摘掉 `validate_evidence_bundle` 后红的条数应从 **16** 再涨，名单 = 原 16 条**逐条原样** + 你新加的每一条 | ⛔ 与禁令 1 对撞：**若你把新门写进测试工厂而不是校验器，这条必然对不上** |
| 5 | ⭐⭐ **换同形输入自证**：你自己再想**一种**「声明与载荷不一致」的形态（⛔ 不许是 §一 那两个），实测它现在走不通 | ⭐ 本项目返工审的第三条：①② 只证明这个例子修好了，⑤ 才证明这类修好了 |
| 6 | **bundle 的 `content_sha256` 没变**（给出改动前后读数）| ⭐ 第三格对撞：与禁令 4 一致；**若必然要变 ⇒ 停下上报** |
| 7 | `pytest -n 4 tests/test_o22m2_evidence_contract.py tests/test_o22m3_evidence_adapters.py tests/test_o22m4_wall_compiler.py` 全绿 | 下游三个模块都吃它的出口 |
| 8 | 列全改动路径（⛔ 不提交）| 与禁令 5 一致 |

## 五、停下上报（分层）
**必停**：§一 的两条实测复现不出来 · 修法必然改 `content_sha256` · 既有锁变红 ·
需要动模块 3/4/5/6 任何一个 · 任务项与禁令自相矛盾。
**只记不停**：错误码取名 · 测试条数 · 「映射表放哪个文件」的分歧。

⭐⭐⭐ **累计 55 次停报，55 次都是派工方的题错 —— 放心停。**

## 六、交付
代码（⛔ 不提交）+ 执行档 `AI_agent/logs/reviews/execution/<日期>_o22m2_absent_with_payload_execution.md`，
逐条给命令+读数、**你自己认为最薄弱的一处**、希望复核方重点打哪里。
