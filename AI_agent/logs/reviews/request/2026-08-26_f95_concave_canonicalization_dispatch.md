# 派工单 · F-95 顶点规范化毁凹多边形（C2「非方形」本体）

- **日期**：2026-08-26　**施工席位**：**GPT 家族**（`gpt-5.6-sol`，⚠️ **新开会话**，⛔ 不续用 F-90 那条）
- **审阅席位**：**GLM 家族**（`scripts/glm_code.sh`）—— ⛔ 谁写谁不批
- **档位**：工程档（碰 `src/validator/` + `src/agent/geometry/`）⇒ **审恒升一档**
- **起点 commit**：`840ffc3`（分支 `08.23_AsDrawnReading`）
- ⚠️⚠️ **必须在独立 worktree 里做**：主树上另有一轮 GLM 复核在跑（审的是 `src/agent/judge/`）。
  ⛔ **不许在 `/workspaces/EnergyPlus-Agent-dev` 改任何文件、不许在主树跑全量。**

## 〇、这件事在盘面上的位置（读懂再动手）

用户 2026-08-26 定的四步：**① 把判分修好 → ② 按新方案改造 reading+correction 的 harness →
③ 产出新产物 → ④ 一步步验证**。当前在 **①**。
用户对 ① 的界定：「**correction 产物不变**，判分的形式和 grade 都有了，
**只是现在要能适配多层 C2 非方形**」。
⇒ 多层那半 = F-90 五项（已交待审）；**非方形那半 = 本单**。

⛔ **本单与任何具体产物无关** —— 它是实现缺陷，有纯离线夹具可证，⛔ 不要去跑任何 case、不要碰 gt。

## 一、缺陷（已实测，⛔ 但请你独立复现一遍再动手）

`canonicalize_ring_vertices`（[`src/validator/data_model.py:1047`](../../../../src/validator/data_model.py#L1047)）
用**绕质心极角排序**重排多边形环。对凸多边形能还原原形；**对某些凹多边形会还原成另一个形状**。

**现成的离线夹具矩阵**（不需 gt / LLM / 跑抽）：
[`logs/experiments/2026-08-25_kernel_probe_from_gt/tools/concave_canonicalization_matrix.py`](../../experiments/2026-08-25_kernel_probe_from_gt/tools/concave_canonicalization_matrix.py)

已测结果：矩形 **OK** · 单凹角 L 形 84.000→84.000 **OK** · **U 形 8 顶点 76.000→70.000 坏** ·
Z 形 8 顶点 68.000→68.000 **OK** · **梳形 12 顶点 66.000→59.000 坏** ·
**sm25 走廊 14 顶点 97.731→226.457 坏**。

⭐⭐ **判据不是「有没有凹角」** —— Z 形有 2 个凹角却无损，而单凹角 L 形也无损。
真正的判据是「**顶点绕质心的极角是否单调**」，凹是**必要非充分**条件。
⇒ ⛔ **按「有没有凹角」挑回归夹具会挑出假绿的那一半。**

**打击面已清点**（`grep` 出的全部调用点）：
- 生产侧：[`build.py:78`](../../../../src/agent/geometry/build.py#L78) 对**每个面**、
  [`build.py:84`](../../../../src/agent/geometry/build.py#L84) 对**每扇窗**各跑一次。
- 校验侧：[`data_model.py:1338`](../../../../src/validator/data_model.py#L1338) 与
  [`checks/kernel.py:398`](../../../../src/validator/checks/kernel.py#L398) **用同一个函数**。

⭐ **实际受害面收窄**：墙面与窗都是矩形（凸）⇒ 规范化对它们无损；
**受害的只有凹多边形 zone 的 Floor / Ceiling / Roof**。这与实测自洽：报错的是
`kernel.zone_closure` 的 `floor_area` / `top_area`，⛔ 没有一条 wall 告警。

⚠️ **两条要特别当心的**：
1. **规范化后的环仍 `is_valid=True`** ⇒ 任何「多边形有效性」检查都放行，**只有面积对账抓得住**。
2. kernel 与 validator **刻意共用**这一实现（`build.py` 注释：避免 F-13 两套算法分歧）
   ⇒ ⛔ **不许为了修它而拆成两套** —— 那会把 F-13 放回来。修必须是**同一个实现被换掉**。

## 二、要做什么

1. **换掉排序式规范化**，改成不依赖「极角单调」假设的实现，使**任意简单多边形**（凹/凸）
   在规范化后**与输入是同一个形状**（面积、顶点集合、边集合都不变），
   同时仍满足原有两条契约：① 环的绕向与给定 `normal_vector` 一致；
   ② 起点是 `GlobalGeometryRules = UpperLeftCorner` 那个顶点。
   ⭐ 提示（**只是提示，不是指定方案**）：输入本来就是一个有序环，
   规范化需要的只有「**必要时整体反向** + **旋转起点**」两种操作，⛔ 都不需要重新排序。
   若你认为存在严格更优的第三条路，**停下上报**（见 §五）。
2. **保持 kernel 与 validator 共用同一实现**（⛔ 不许拆两套）。
3. **补锁**（见 §三判据 2）。

## 三、验收判据

1. **夹具矩阵全绿**：上面那六个形状（矩形 / L / U / Z / 梳形 / sm25 走廊 14 顶点）
   规范化前后**面积逐个相等**、**顶点集合相同**。⭐ 请**扩充**该矩阵，至少再加：
   自交前的乱序输入 · 顺时针与逆时针两种输入绕向 · 起点在不同顶点的同一个环 ·
   一个「极角单调但凹」的形状 · 一个「极角非单调但凸」的形状（若存在，没有请说明为什么不存在）。
2. **锁必须有分辨力**（⭐ 本项目的老账：**有锁 ≠ 有分辨力**）：
   现有的 `test_lshape_polygon_clean` 断言的正是那个**恰好无损**的单凹角 L 形 ⇒ 它一直是绿的、抓不住本缺陷。
   ⛔ **不许只加同型的锁**。新锁必须：**摘掉你的修复 ⇒ 变红**，并请说明**变红方向对不对**。
3. **全量绿**：`python -m pytest -n auto`（⭐ **在你自己的 worktree 里跑**）。
   已知环境坑：`tests/test_zone_agent.py` 缺 `OPENAI_API_KEY`/`DEEPSEEK_API_KEY` 会红，**非回归**。
4. **两条既有契约不许破**：绕向与 `normal_vector` 一致 · 起点是 UpperLeftCorner。
   请各给一个**独立**的实测证明（⛔ 不要只靠「全量绿」代过）。

## 四、范围

**允许碰**：`src/validator/data_model.py` · `src/validator/checks/kernel.py` ·
`src/agent/geometry/build.py` · `tests/**` ·
`AI_agent/logs/experiments/2026-08-25_kernel_probe_from_gt/tools/concave_canonicalization_matrix.py`（扩充夹具矩阵）。

⛔ **不许碰**：`src/agent/judge/**`（⚠️ 另一轮复核正在审它）· `src/agent/pipeline*` · `state.py` ·
`src/agent/correction/` · `case_tests/test_baseline/gt/**`（**gt 铁律**）· 任何 `src/configs/*.yaml` 的容差。

⛔ **不许 `pip install -e`**；⛔ **不许动 `/opt/venv/**`**（所有席位共用）；
⛔ **不 commit / 不 push**（orchestrator 审后提交）。

## 五、⚠️ 停下上报触发器（本项目累计 **33/33** 全是派工方题错，本单大概率也有）

遇到下面任何一种，**立刻停下写上报，⛔ 不要自行扩大范围、也不要选个次优的将就**：

1. 「保持同一个实现、同时满足两条既有契约」**做不到**；
2. 我给的那条提示（反向 + 旋转起点）**是错的或不完整**；
3. 存在**严格更优的第三条路**，而我上面只给了一条 ——
   ⭐ 本项目上一单就栽在这里（派工方预设了「只有这两条」，施工方找到了更优的第三条）；
4. 你发现**受害面不止凹 zone 的 Floor/Ceiling/Roof**（我上面那句收窄结论可能是错的）；
5. 判据本身把你逼进「绕过 vs 扩范围」的二选一 —— **报上来，别自己解决**。

## 六、产出

1. worktree 里的 diff（⛔ 不提交），并明确告诉我 worktree 路径。
2. 报告落 `AI_agent/logs/reviews/execution/2026-08-26_f95_concave_canonicalization_construction_report.md`
   —— ⚠️ **这是唯一允许你写进 `AI_agent/**` 的文件**。含：
   缺陷的独立复现 · 扩充后的夹具矩阵全表 · 每把新锁的红/绿对照 + 变红方向 ·
   两条既有契约各自的独立证明 · 全量输出 ·
   **「本单派工方错在哪里」**（⛔ 不许写「无」）。
