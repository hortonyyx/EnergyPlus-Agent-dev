# 派工单 · W-1 的 T3 **续做**（GLM 施工 / Claude 审）

> **派工方** = orchestrator（claude-opus-5）　**执行方** = GLM 席位（`glm-5.3`，`scripts/glm_code.sh`）
> **基点** = `dcffb4f8`，分支 `wt/09.07h_w1_flow`，**工作目录写死 `/tmp/w1_flow_glm`**
> **这不是重做** —— 你上一轮撞额度被打断，半成品已抢救落库（`9d79dfe7`）并**已复核**。
> ⛔ **不要重写已经对的部分**，接着往下做。

## 〇 开工前必读（都已在你树内，⛔ 不用去主树找）

| 文件 | 是什么 |
|---|---|
| `AI_agent/logs/reviews/request/2026-09-07h_W1_flow_wiring_dispatch.md` | 原单（⭐ **已是改宽版**，基点问题已修）|
| `AI_agent/logs/reviews/verdict/2026-09-07i_W1_T2_ratification.md` | T2 拍板书，放行条件在 §四 |
| `AI_agent/logs/reviews/verdict/2026-09-07l_W1_T3_wip_review.md` | ⭐ **本轮题面**：正文 4 阻断 2 不阻断 + 附录 A（全量 3 红查因 + 主控两处自更正 + BLK-E）|
| `AI_agent/logs/reviews/execution/2026-09-07h_W1_flow_wiring_execution.md` | 你自己的 T1/T2 交件 |

⚠️ **基点说明**：你上一轮的树基于 `59b6b102`，**早于**改宽后的单子和拍板书。
已由主控 `git merge` 补齐（`dcffb4f8`）⇒ **现在树里的每一份文档都是最新的**。

## ⭐⭐⭐ 一 · 本轮第一纪律：**每完成一段就提交**

上一轮你在 T1 段执行了分段提交、**T3 段没有** ⇒ 撞额度时 **4 个文件 634 行全在工作区**，
是主控替你 `git status` 抢救才没丢。本轮**每一段（S1…S7）做完立刻 `git commit`**，
⛔ 不许攒着。段内没做完也要在**撞任何异常之前**先落一笔 WIP。

⛔ 提交只 `git add <明确路径>`，**禁 `git add -A`**；`git commit` 前必看 `git diff --cached --numstat`。

## 二 · 分段任务（按此顺序，每段一提交）

### S1 · BLK-A ⭐⭐⭐ —— **把「缺席」真的变成信号**

**题面**：拍板书 §二 T2-⑤ 之所以通过、用户之所以拍板接受「新腿上那条 legacy 窗证据门暂时没牙」，
理由**原文**是「显式登记 `WINDOW_EVIDENCE_ON_CHAIN_NOT_ON_LEDGER` ⇒ 把缺席变成了信号」。
实测：该标识符**只在 `window_sources.py` 的两处 docstring 里，代码里零处** ⇒ **接受前提当前为假**。

**要做**：走**既有** `EvidenceDebt` 机制（`pipeline.py` 已 import `EvidenceDebt` /
`write_evidence_debt` / `project_evidence_debt`）把这条债登记出来，
**exploratory 出 FLAG、strict 挡住**。

**锁**（≥2 条）：① 新腿路径上产出的债里**确实含这条 id**；② strict profile 下**确实被挡**。

⛔ **停下上报触发器**：如果 `EvidenceDebt` 的既有形状**装不下**这条债
（例如它的 id 空间是从 reading 侧投影来的、没给 wiring 侧留位置），
**停下报** —— ⛔ 不许自己发明第二套债机制。

### S2 · BLK-E + RED-1 —— **容差不许从「第二次读盘」派生**

**题面**：`pipeline.py:1727` 在链跑完**之后**按 `vector_dir / product_filename`
**重新读一遍**产物来派生容差；而链自己已记录 `projection_envelope.source_resolved_sha256`。
⇒ 同一份产物读两次、**无任何对账** ⇒ 位移几何的授权建立在一份**没被验证是同一份**的声明上。

**要做**：让容差的派生输入 = **链真正消费的那份字节**。我看到至少两条路：
- (a) 让链把它解析出来的产物/声明**回传**给 wiring；
- (b) 保留重读，但把重读字节的 hash 与 `source_resolved_sha256` **对账，不一致具名红**。

⛔ **我不预设哪条对**，但你**必须写明你选的那条为什么比另一条好**。
⭐ **如果两条都不成立、而有第三条严格更优，走第三条并说明** ——
选项清单本身就是个没签字的前提，⛔ 别被我这两条框住。

**锁**：① 造一个**字节不一致**的夹具 ⇒ 具名红；② RED-1 转绿。
⚠️ **RED-1 转绿不能当本段验收** —— 那条测试只要不读盘就会绿，
**绿了不代表对账在**（它是 [[gate-with-only-negative-assertions-is-unobservable]] 的反面陷阱）。

### S3 · BLK-B —— **把 `build_verified_window_inputs_as_drawn` 接上**

**题面**：该函数**全仓外部引用 0 处** ⇒ 死代码。而它正是 T1 撞出的 B2 阻断
（`finalize.py:117` 对 V3 强制要 `verified_window_inputs`）的修法 ⇒ **端到端仍然过不去**。

⭐ **你自己在 T1 交件的「最薄弱的一处」里点名了这件事**：
> 「我对『新腿 gate① 可走空集 window inputs』的判断是读码+离线 adapter 实测推出的，
> **没有真正把一个 assembled V3 喂进 `check_correction` 跑过**……T3 开工第一件事就是拿探针产物实测这条路。」

**本段就做那件事**，⛔ 别跳过。探针产物在
`AI_agent/logs/experiments/2026-09-07h_w1_t1_probe/newleg_probe/floor_{1,2}/projection_envelope.json`
（含 `geometry`，主控已验可离线加载）。

⛔ **停下上报触发器**：如果空 proof 真的在 gate① 的某条不变量上红 ⇒ **停下报**。
那意味着 T2-⑤ 的方案 3 要改成「新腿用独立 check 入口」，**改动深度变了，需要主控重新拍**。

### S4 · BLK-C —— **生产入口接线（这是 W-1 的正题）**

```
pipeline.py:2383  run_pipeline → run_correction(...)      ⛔ 仍不传 evidence_chain
scripts/tool_scripts/run_stage.py:457  flow → run_correction(...)  ⛔ 仍是 legacy 参数表（本轮零改动）
```

**选腿 = 分类器判定**（拍板书 T2-① 已通过：混合 / 缺立面 / unknown **各自响亮失败**）。
⛔ **静默回退一律禁止** —— 静默回退会让新腿永远不会被发现没通电。

### S5 · RED-2 —— 执行侧注释不许点名 gt 侧模块

`multifloor.py:444` 注释里写了 `tarch_normalize._axis_snap_cap_native`，
撞 `test_executors_do_not_reference_gt`（执行侧不许引用 gt，**连注释都不行**）。
⚠️ 这条**有派工方责任**：BLK-1 要你「引用同日阶梯先例」，你就把模块名抄进了执行侧。
**修法 = 描述那条先例的语义**（「半个最薄声明墙厚」），⛔ 不点名 gt 侧模块。

### S6 · RED-3 —— 新增的被跟踪产物要登记入账

T1（`67d4bdd0`）把 `case_tests/e2e_tests/sm25-L_anchor/run_t1_legacy_full/` 提交进了版本库，
而 `test_b2_prescan_reproduction` 要求**每份被跟踪的 `4_mep` 产物都在 prescan 表里有分类**
（`_PRESCAN_GREEN` / `_PRESCAN_OBJECT_LEVEL`，在 `tests/test_mep_idd_field_alignment.py`）。
⇒ **锁按设计工作了。补登记，⛔ 不许放宽锁。**
⚠️ 登记进哪一档要**按实测**（跑一下看它是 PASS 还是 FAIL），⛔ 不许猜。

### S7 · 总验收（见 §四）

## 三 · 随手要改的两条（不阻断，可并进任一段）

- **N-1**：`multifloor.py` 用「两环顶点数不同（94 vs 86）」论证必须用 Hausdorff，
  但**同一笔提交**的 `_corner_only_ring` 已把环降成 **8 角点**（主控两层都实测：
  94→8 / 86→8，周长浮点完全相等）⇒ **做法仍对，理由已不成立**。
  改成按现状陈述（「环已在上游降为角点环；Hausdorff 是为了不依赖顶点数相等这个上游可能变化的性质」）。
  ⛔ 别留一个会被后人当事实引用的过期读数。
- **N-2**：`_check_direction_facts_as_drawn` 的 `raw_reading_artifacts` 是**死参数**
  （只在签名里）⇒ 会让人以为这条腿也消费了产物。删掉，或显式改名并写明理由。

## 四 · 验收

1. **全量必须回到 `0 failed`**（当前分支上是 **3 failed / 4006 passed**；主线基线 4009 全绿）。
   跑法：`cd /tmp/w1_flow_glm && PYTHONPATH=/tmp/w1_flow_glm uv run pytest -n 6 -q`
   ⭐ 开跑前先自检 `src.agent.__file__` 落在 `/tmp/w1_flow_glm` 内。
2. **⭐⭐⭐ 总验收 = 一串命令序列，从 `0_reading` 到出分，全程标准入口、零现场手写脚本，
   逐字写进交件、任何人照抄能重跑。** 这是用户的原话口径：
   「**就是修到可以完整跑端到端就行（整个架构通，别需要现手搓），别的风险欠债跑完一次再修**」。
3. 交件写进 `AI_agent/logs/reviews/execution/2026-09-07p_W1_T3_rework_execution.md`，
   ⭐ 末尾必须有一节「**我这次最薄弱的一处**」（上一轮你这一节写得很好、而且正是它点出了 S3）。

## 五 ⛔ 明确不做（扩范围即阻断）

**W-2 · F-137 · F-131 · F-134 · G-g · F-149 全部不做。**
用户口径是「别的风险欠债**跑完一次再修**」。

## 六 · 运行纪律（硬约束）

- ⛔ **禁 `pip install -e .` 或任何写 `site-packages` 的命令**（venv 全机共享，会打断别人）。
- ⛔ 禁 `--force` push · `git reset --hard` · 跳 hook · 改 `git config`。
- ⛔ 禁 `git add -A`；只 add 明确路径，commit 前必看 `git diff --cached --numstat`。
- 跑测用 `-n 6`（机器有别的席位可能在用）。
- ⭐ **每完成一段就提交**（见 §一）。

## 七 · 停下上报触发器（分层）

| 层 | 触发条件 | 动作 |
|---|---|---|
| **A 类（题错）** | S1 的债机制装不下 · S3 的空 proof 在 gate① 红 · 发现本单里某个前提与代码矛盾 | **立刻停，写清「你以为是 X，实际是 Y，证据是……」** |
| **B 类（要拍板）** | S2 三条路都有实质代价、需要主控选 · 接线时发现选腿判据有第三种输入形态 | 停下写清选项与代价 |
| **C 类（自己决）** | 命名 · 文件位置 · 测试组织方式 | 自己决，交件里说一句 |

⭐ 历史读数：**「停下上报」至今 70/70 全是派工方的题错**。
⇒ 你觉得单子哪里不对，**大概率真是我错了**，⛔ 别自己绕过去。
