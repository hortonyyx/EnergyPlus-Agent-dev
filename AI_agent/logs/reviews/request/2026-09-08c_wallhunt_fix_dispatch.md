# 派工单 · 撞墙清单的修复（GLM 施工 / Claude 审）

> **派工方** = orchestrator（claude-opus-5）　**执行方** = GLM 席位（`glm-5.3`）
> **工作目录写死 `/tmp/w1_flow_glm`**，分支 `wt/09.07h_w1_flow`
> **题面** = `AI_agent/logs/experiments/2026-09-08b_wallhunt/README.md`（主控实测撞墙清单）

## 〇 ⭐ 先说清结构，免得你按错的模型施工

**用户的判断（已核实成立）**：correction 的**产物**是同一个类型，
**归档之后的每一段消费的都是已归档的产物、不在乎哪条腿。**

**唯一的例外是 `record` 本身**：它不只**存**产物，还要
**从 producer + 原始识图产物【重新推导一遍】再逐字段比**
（`stage_runner.py:311-370`，F-22 BLOCKER-1 防篡改锁），而重放走的是 **legacy 的推导路**
（`extract_authoritative_envelope` + `apply_deterministic_core`），**且无条件、没有按腿分派**。

⇒ 所以本单里的墙**分两类，⛔ 别混着修**：

| 类 | 是什么 | 含哪几堵 |
|---|---|---|
| **A 类·腿的溯源** | 只在 `record` 这一处，因为那里要重新推导 | **W#3** |
| **B 类·内容缺陷** | 与腿无关，换哪条腿产出这份几何都会红 | **W#6 · W#7** |
| **C 类·门/观测** | 门在用 legacy 形状量 as_drawn；或记录不干净 | **W#1 · W#4 · W#5** |
| **D 类·可重跑性** | 命令序列照抄跑不起来 | **W#2** |

## ⭐⭐⭐ 一 · 纪律不变：**每完成一段就提交**

上两轮这条都被实测证明有效（二次撞额度、基本零丢失）。⛔ 不许攒着。

## 二 · 分段任务（按此顺序）

### S-A · W#3 —— 让归档的重放**按腿分派**（闸门，先修）

```
stage_runner.py:370  raise ValueError("writer_core_projection_drift")
```

⛔ **不许放宽这条锁** —— 它防的是「producer/ring/cells 一起被改得内部自洽」那种篡改
（F-22 BLOCKER-1 的复现就是这个）。

**要做**：给 as_drawn 腿配一条**它自己的重放路**，与 legacy 那条**同等强度**。
as_drawn 腿本来就有自己的溯源链，⭐ **你自己在 S2 刚建过其中一环**：
- `chain_source_record.json`（链在 source_read 冻结处记的**实际消费字节** sha256）
- `projection_envelope.projection_sha256` / `source_resolved_sha256`

⛔ **停下上报触发器**：如果 as_drawn 腿的溯源链**不足以达到与 legacy 同等强度**
（例如某一环是产物自报、没有独立锚），**停下报** ——
⛔ 不许用「新腿就跳过这道锁」了事，那等于把防篡改门在新腿上关掉。

### S-B · W#6 —— 覆盖守恒破了，**修根因不是修症状**

```
gate①: FAIL correction.coverage: floor '2f' violates coverage area conservation
```

**主控实测的根因**（读数在撞墙档 + 裁决 `2026-09-07x`）：

- 每层**自己**完美守恒：ring 面积 == cells∪ 面积，差 **0.0000 m²**（两层都是）
- 把 2f 的环换成 1f 的环（吸附的做法）⇒ 差 **0.3806 m²**，阈值 0.05 ⇒ **吸附在破坏自洽**
- ⭐⭐⭐ **而两层本来就该一样**：两份平面产物**声明的尺寸链完全相同** ——
  x 的 `cum_mm` 逐位相同、`overall_mm` 都是 25000/20000、`chain_closure_mm` 都是 0
- 足迹真值可从声明推出：轴线框 = 声明外皮 ∓ 半个外墙厚（240/2=120）⇒ x `[120, 24880]`、y `[120, 19880]`，**两层相同**
- 实测八条边**七条落在各自噪声界内**（第八条 8.5mm vs 界 7.2mm，1.18×）

⇒ **那 14.4 mm 全是像素侧的拟合残差，正确答案图纸自己写着。**
⇒ 修法与你已经做过的 **丁**（ladder 取声明刻度）**同一形状**：**足迹取声明值**。
两层因声明相同而**按构造完全一致、零容差**；ring 和 cells 吸到同一网格 ⇒ **守恒保持**。
⇒ **吸附步 / 容差 / 整层变换全都不需要。**

唯一性余量（主控实测，与丁同一派生式 `mm_per_px × max|residual_px|`）：
1f x **36×** · 1f y **99×** · 2f x **42×** · 2f y **301×**。

⛔ **停下上报触发器（两条，⚠️ 主控明确没验过）**：
1. **内墙**位置能否同样唯一匹配到声明刻度？链只有 11/10/7 个刻度，而墙更多 ——
   **匹配不上的墙怎么处理，必须有说法**，⛔ 不许默默按最近刻度吸。
2. **2f 的 y 链只有 7 个刻度、1f 有 10 个** ⇒ 有些 1f 声明的位置 2f 根本没声明。
   这对「两层落到同一网格」意味着什么，要说清。

这两条任何一条不成立 ⇒ **停下报**，⛔ 不许自己填容差糊过去。

### S-C · W#7 —— 落盘的债要被审计**认领**

```
gate①: FAIL correction.evidence_debt_coverage: 1 view/global evidence debt item(s)
       were not mentioned in correction audit
```

你 S1 为解 BLK-A 把 `WINDOW_EVIDENCE_ON_CHAIN_NOT_ON_LEDGER` 落盘了（**实测已生效**，
真跑的 `evidence_debt.json` 里 `disposition=flag`），而**落盘本身触发了消费对账门**。
⭐ **门没错** —— 是新腿的 correction 审计要**认领**这条债。

### S-D · W#1 —— reading 的门在用 legacy 形状量 as_drawn

24 条 FLAG，两类要分开处理：

1. ⭐ **真的**：`reading.plan_scale_origin_usable` —— 原文「**the plan channel would score zero**」。
   ⇒ 用户口径「首跑 = 跑通**并且**出分」在这一条上直接挂。**必须修。**
2. ⛔ **假红**：`reading.dimensions_present` 说「dimensioned view has empty `dimensions[]`」，
   而 as_drawn 产物**确实带尺寸链**（`observations.calibration.{x,y}.cum_mm`，主控实测）——
   只是**不在 legacy 的 `dimensions[]` 字段里**。
   ⇒ 与 `finalize.py:117` 那个「as_drawn 被 `ReadingView` 静默解析成空壳」**同一个病**。

⭐ **并且：回头枚举这一类**（S3b 的教训）——
**还有哪些门在用 legacy 形状量 as_drawn 产物？把对照表写进交件，表本身就是交付物。**

### S-E · W#4 / W#5 —— 观测

- **W#4**：成功重跑**没清掉**上一次的 `_run/evidence_chain_failure.json`
  ⇒ 陈旧失败记录留在盘上误导人（同型 [[exit-code-file-must-not-be-reused-across-runs]]）。
- **W#5**：`record` 抛异常时 **gate① 的报告一起丢**（`attempts/` 不存在）
  ⇒ 撞墙时看不到门说了什么。本次 gate① 读数是主控**离线复现**出来的。

### S-F · W#2 —— 凭据与可重跑性

`.env` 是 gitignored 的、**worktree 里没有** ⇒ 在 worktree 里跑 `flow` 必然
`no api_key`。对代码不是墙，但对总验收口径**「任何人照抄能重跑」是真墙**。
⇒ **命令序列里必须写清凭据从哪来**（主控本轮用的是
`set -a && . /workspaces/EnergyPlus-Agent-dev/.env && set +a`）。

## 三 · 总验收

1. **全量回到 `0 failed`**：`cd /tmp/w1_flow_glm && PYTHONPATH=/tmp/w1_flow_glm /opt/venv/bin/python -m pytest -n 6 -q`
   ⛔ **勘误（2026-09-08，GPT 席位停报翻出，主控确认题错）**：本单原写 `uv run pytest`，
   而 `uv run` **本身会重新同步共享 `/opt/venv`**（实测输出 `Uninstalled 1 package` /
   `Installed 1 package`）⇒ **与本单 §五「禁任何写 `site-packages` 的命令」自相矛盾**，
   且这是并行 worktree 之间 `.pth` 反复互踢的**根因**。改用 `/opt/venv/bin/python -m pytest`：
   实测解析正确、**零安装输出、`.pth` 跑完未被改**。一次性脚本同理（`uv run python -c` 也会同步）。
   （开跑前自检 `src.agent.__file__` 落在本树）
2. ⭐⭐⭐ **端到端**：`0_reading` → 出分，全程标准入口、**零现场手写脚本**，
   命令序列逐字写进交件、任何人照抄能重跑。
   ⚠️ `judge.mode` 不能是 `off` —— 口径是「首跑 = 跑通**并且**出分」。
3. ⭐ **W#3 修好之后，2/3/4/5 段的墙才会露出来**（主控实测：`build_geometry` 硬要求
   `VerifiedWindowHostProof`，而那份 proof 只有归档成功才铸得出）
   ⇒ **预期还会撞到新墙，那是正常的**；撞到就按同样的方式记账 + 分段提交，
   ⛔ 不要因为「单子没写」就绕过去。

## 四 ⛔ 明确不做（不变）

**W-2 · F-137 · F-131 · F-134 · G-g · F-149**；
另 **run 级 `evidence_chain_route.json` 多层 last-writer-wins**（你 S2 量出的那条）也不修。

## 五 · 运行纪律（不变）

⛔ 禁 `pip install -e .` / 写 `site-packages` ⛔ 禁 force push / `reset --hard` / 跳 hook / 改 `git config`
⛔ 禁 `git add -A`（只 add 明确路径，commit 前看 `git diff --cached --numstat`）· 跑测 `-n 6` · **每段一提交**

## 六 · 停下上报

⭐ 历史读数 **71/71 全是派工方的题错**。你上一轮那条 B 类停报又对了一次。
⇒ 觉得单子哪里不对，**大概率真是我错了**，⛔ 别绕过去。

⚠️ 本单里主控**明确标注没验过**的：S-B 的两条触发器。那两条我是**推的不是量的**。
