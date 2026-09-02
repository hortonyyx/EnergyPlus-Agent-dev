# 跨家族复核请求 · **F-156 第四轮 ＋ ②-1d 同修**

- **日期**：2026-09-02 · **请求方**：orchestrator · **复核方**：**GPT 家族**（⛔ 不得 Claude —— 施工方是 Claude 施工席；GLM 正在飞另一活）
- **被审 commit**：**`bbeab77`**（施工方原件 `e35cc1d`，`cherry-pick -x` 落到分支，**内容逐字相同**）
- **派工单**：[`2026-09-01i_f156r4_o21d_joint_rework_dispatch.md`](2026-09-01i_f156r4_o21d_joint_rework_dispatch.md)
- **施工方执行档**：[`2026-09-02_f156r4_o21d_joint_claude.md`](../execution/2026-09-02_f156r4_o21d_joint_claude.md)
- **被审 diff**：`src/agent/judge/answer_compiler.py` **+52/−1** · `tests/test_o21d_exclusion_gap.py` **+103** · `tests/test_f156_ring_from_intersection.py` **+67**
  （执行档 +167 不计）。⛔ **只看原始需求 + diff + 测试输出**，不必读施工方长篇自述。

---

## 一、请你重点打的两处（⭐ 这是请求方自己看出来的疑点，⛔ **不是结论，请证伪或证实**）

### 疑点 1 ⭐⭐⭐ **「exclusion 不得多于 pairing」这条 1:1 切分，是不是一个没人签字的领域参数？**

施工方的辩护是：**这不是照数据设的百分比，是「仪器自身定义」的结构切分 —— 例外不得变成常规**。
请求方认为这个辩护**有力但不充分**，理由：它等价于**把一个数设成 1.0**，而
「一个 view 里合法的豁免最多能占到验证数的几倍」**是领域问题，不是仪器定义**。

⇒ ⭐ **请你实测回答**：
1. 构造一份**诚实**的输入，其中某个 view 天然 `excluded > paired`（例如一个只有 1 条配对边、
   却有 2 个**按设计**低于面积阈值的管井腔的 view）—— **它会不会被判红？**
   若会 ⇒ 这是**真实假红**，且 [[invalidation-blast-radius-must-be-scoped]] 警告过：
   常态化的假红会掩护真正的静默。
2. 若不会，请说明**结构上为什么不可能**（⛔ 不是"目前 sm25 没有这种 view"这种现状陈述 ——
   那是拿现状当判据 [[acceptance-bar-must-not-be-written-from-the-result]]）。

### 疑点 2 ⭐ **① reason 准入表被判定为"不必加"，这个判定站得住吗？**

施工方实测 `AsMeasuredBoundaryRingLossV1.reason` 已是 `Literal[8]` ⇒ 任意字符串在 schema 处就被拒，
故在消费端再加一张表会**结构上不可观测**（schema-合法输入永远红不了它）。

⇒ ⭐ **请你判**：复核方（GLM）原话要的是「**哪些 reason 有资格豁免一个房间**」——
这问的是**闭集里的 8 个值是不是每一个都有资格**，⛔ 不是"reason 是不是闭集"。
**这两件事是不是被偷换了？** 若是，那张准入表仍然缺。

---

## 二、⛔ 请求方已自查出的两条（**已告知你，别当新发现重复记**）

| # | 内容 | 我的定性 |
|---|---|---|
| N-1 | **`_the_compiler` 是个假锚点** —— 它只出现在施工方**自己新写的两条注释里**（`answer_compiler.py:998` 与 `:1041`），全仓无此定义。真正的锚是 **`_project_span`（`:667`）** | **不阻断**，但必须改：引用标识符前先查它的定义 |
| N-2 | 源码注释里写了 `[[gate-teeth-direction-follows-fixture-inventory]]` 这种**记忆库 wiki 链接语法** | **不阻断**，风格问题 |

---

## 三、⚠️ 关于那条红：**是请求方的布置错误，⛔ 不是施工方的回归**

施工方报 `3634 passed / 13 xfailed / **1 failed**`，并判定为环境红。
⭐ **请求方独立追到了真机制（施工方的方向对、机制说错了）**：

```
tests/test_zone_agent.py  →  src/configs/llm.yaml:104  zone: provider=openai,
                             api_key=${oc.env:DEEPSEEK_API_KEY,null}
.env  在主树存在、被 .gitignore:173 忽略  ⇒  /tmp 的 worktree 里【没有】
⇒ DEEPSEEK_API_KEY 未设 ⇒ langchain_openai 报 "OPENAI_API_KEY not set"
```
⇒ **不是缺 OpenAI 的 key，是 worktree 里没有 `.env`** ⇒ **任何放在 `/tmp` worktree 的席位都会看到这一条红。**
**这是我建 worktree 时没处理凭据，与被审 diff 无关。**
⇒ ⛔ **判这一条不要记到施工方账上**；但**请你核实它确实与 diff 无关**（`test_zone_agent` 不 import `answer_compiler`）。

---

## 四、常规项

1. 派工单 §五 的六条验收（1 / 1b / 2 / 3 / 4 / 5），逐条**独立复跑**，⛔ 别采信执行档的读数。
2. ⭐ 指南 §五#2：**请你再找一种能骗过新判据的真实错误形态** —— 施工方自己造的那两种挑不出它自己的盲区。
3. 环境自证与 pytest 放**同一条命令**：
   `python -c "import src.agent.judge.answer_compiler as m; print(m.__file__)" && python -m pytest ...`
   ⛔ 不要用 `.pth` 哈希当判据（CLAUDE.md §5#8.6）。
4. 跑测 **`-n 6`**，⛔ 不用 `-n auto`（另有席位在飞）。
5. 裁决写进 `AI_agent/logs/reviews/verdict/2026-09-02b_f156r4_o21d_crossreview_gpt.md`，
   给 **APPROVE / APPROVE-WITH-FINDINGS / REWORK** + 阻断数 / 不阻断数。
