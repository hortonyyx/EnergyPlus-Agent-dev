# 一次性撞墙：新腿经 `flow` 从 0_reading 推到出分（2026-09-08，主控实测）

> **起因**：用户「行这么干吧，先一起撞出来吧」——⛔ 停止一轮修一堵墙的串行打法，
> 一次把剩下的墙全部撞出来列成清单，再一次派工。
> **打法**：用**真入口** `scripts/tool_scripts/run_stage.py run <case> <run> <stage>`
> 一段一段推，⛔ 不写绕过脚本；撞到墙就在本地（**不提交**）最小化绕过，继续往后撞。
> **树** = `/tmp/w1_flow_glm` @ 丁 落地后；**run** = `case_tests/e2e_tests/sm25-L_anchor/run_wallhunt`
> （从席位落库的 `run_w1_s7_probe` 复制，保持那一份原封不动）。

## 墙清单

### W#1 · `0_reading` —— gate① **过**（block=0）但 **24 条 FLAG**，其中一条直接是**出分为零**

四类 × 6 视图：

| 检查 | 原文 |
|---|---|
| ⭐ `reading.plan_scale_origin_usable` | 「plan view declares no scale_origin object; its local→world frame cannot be rebuilt and **the plan channel would score zero**」|
| `reading.dimensions_present` | 「dimensioned view has **empty dimensions[]**」|
| `reading.raw_field_presence` | raw reading JSON omitted uncaptured before schema/default migration |
| `reading.stroke_provenance_coverage` | structural strokes lack full provenance coverage |

⭐⭐⭐ **`dimensions_present` 这条是【假红】性质的**：as_drawn 产物**确实带尺寸链**
（`observations.calibration.{x,y}.cum_mm`，实测 1f/2f 的 x 链逐位相同、`overall_mm` 25000/20000、
`chain_closure_mm` 0），只是**不在 legacy 的 `dimensions[]` 字段里**。
⇒ **0_reading 的门在用 legacy 形状的检查去量 as_drawn 产物** ——
与席位在 `finalize.py:117` 撞到的「as_drawn 被 `ReadingView` 静默解析成空壳」**同一个病**。

⚠️ 而 `plan_scale_origin_usable` 那条不是假红，是真的：**出分会是零**。
⇒ 用户口径「首跑 = 跑通【并且】出分」在这一条上就已经挂了。

⚠️ 本 run 是 `run_profile: exploratory` ⇒ 这些都是 FLAG 不是 BLOCK，跑得下去。
**strict 下是什么行为没验**（登记为待验）。

### W#2 · `1_correction` —— **凭据取不到**（环境墙，非代码墙）

```
RuntimeError: correction_decision_r0: no api_key (set DEEPSEEK_API_KEY in .env).
```

病因 = `.env` 是 gitignored 的，**worktree 里没有**（只在主树 `/workspaces/EnergyPlus-Agent-dev/.env`）。
⭐ 与主控起 GLM 席位时撞的**同一个坑**（`scripts/glm_code.sh: /tmp/w1_flow_glm/.env: No such file`）。

⚠️ 这条对**代码**不是墙，但对总验收口径**「任何人照抄能重跑」是真墙** ——
交件里的命令序列如果不写清凭据从哪来，**在 worktree 里照抄必失败**。

**本轮绕过（⛔ 不提交）**：`set -a && . /workspaces/EnergyPlus-Agent-dev/.env && set +a` 后再跑。

### W#3 ⭐⭐⭐ · `1_correction` 归档 —— `writer_core_projection_drift`（**这是整条路的闸门**）

```
File "src/agent/execution/stage_runner.py", line 370, in record
    raise ValueError("writer_core_projection_drift")
```

⭐ **新腿整条都跑通了**（两层链跑完 → 吸附 → assemble → 窗输入 → finalize → gate①），
**只死在最后的归档**。归档时会**重放 legacy 确定性内核**
（`extract_authoritative_envelope` + `apply_deterministic_core`）再逐字段比，
而 as_drawn 腿的几何是经 `finalize_as_drawn_chain_geometry` 产出的 ⇒ 必然不等。

这是 F-22 BLOCKER-1 的**防篡改锁**，⛔ 不能放宽 —— **要给 as_drawn 腿配一条对应的重放路**。

### W#4 · 成功重跑**没有清掉**上一次的失败记录

`1_correction/_run/evidence_chain_failure.json` 里记的仍是**第一次**（W#2 那次）的
`no api_key` 失败，而这次链跑成功了。⇒ **陈旧的失败记录留在盘上，会误导下一个读它的人。**
同型 memory [[exit-code-file-must-not-be-reused-across-runs]]。

### W#5 · `record` 抛异常时，**gate① 的报告一起丢了**

`1_correction/attempts/` 不存在 ⇒ gate① 说了什么**看不到**。
本档的 gate① 读数是主控**离线复现**出来的（`gate1_replay.py`），⛔ 不是从 run 里读到的。

### W#6 · gate① `correction.coverage` —— **2f 违反面积守恒**（吸附造成的）

离线复现（拿本次真跑的两份 `projection_envelope`）：

```
gate①: passed=False  blocking=1  results=18
  FAIL correction.coverage: floor '2f' violates coverage area conservation
```

⭐ 主控独立量过：每层**自己**完美守恒（差 0.0000 m²），而把 2f 的环换成 1f 的环 ⇒ **0.3806 m²**（阈值 0.05）。
⇒ **吸附是在破坏自洽去换取跨层相等。**根因见「§ 根因」一节。

### W#7 · gate① `correction.evidence_debt_coverage` —— **修好一个洞长出一个新洞**

```
FAIL correction.evidence_debt_coverage: 1 view/global evidence debt item(s)
     were not mentioned in correction audit
```

S1 为解 BLK-A 把 `WINDOW_EVIDENCE_ON_CHAIN_NOT_ON_LEDGER` **落盘**了（实测 `evidence_debt.json`
里 `disposition=flag`，⇒ BLK-A 在真跑上确认解除），而**落盘本身触发了消费对账门**：
每条债都必须在 correction 审计里被提及，新腿的审计不提它。
⭐ **这正是消费对账门该干的事**，⛔ 不是它错了。

### W#8 ⛔ **撤回** —— 那是主控探针的接线错误，不是生产的墙

我把 `res.window_host_claims`（`WindowHostClaimsV1`）直接塞进了要
`VerifiedWindowHostProof` 的参数，于是撞出
`'WindowHostClaimsV1' object has no attribute 'raw_output_bytes'`。
实测：`FinalizeResult.window_host_claims` 在 **legacy 和 as_drawn 两条腿上是同一个类型**，
而 `VerifiedWindowHostProof` 是在**下游** `geometry/build.py:192` 铸的。
⇒ **是我接错，⛔ 不是新腿缺件。**

---

## ⭐⭐⭐ 撞墙到此为止 —— 而且「底」是**设计出来的**

改传 `window_host_proof=None` 再试：

```
ValueError: v3 build requires VerifiedWindowHostProof, including zero-window output
```

`build_geometry` **硬要求**那份 proof，而它**只有归档成功才铸得出来** —— 也就是 **W#3 之后**。

⇒ **「播种绕过 blocker、一次把后面的墙全撞出来」在 1_correction 之后【结构上不可能】。**
这不是缺陷，是防篡改设计的有意结果：**没有真实归档的 proof，下游一步都走不了。**

⇒ 打法结论：**W#3 是闸门**。2/3/4/5 段的墙**在 W#3 修好之前根本看不见**。
⛔ 所以「一次撞全」这个目标本身只能做到 1_correction 为止 —— 这条读数本身就是本次撞墙最重要的产出。

## 本次一次性拿到的确认（顺带）

- **吸附账与主控独立测量吻合到 9 位有效数字**：`hausdorff=0.014433468 m`、
  `tolerance=0.020643492 m`、noise 支管事、`cap=0.06` ⇒ 主控此前的读数是对的。
- **BLK-A 在真跑上确认解除**：`evidence_debt.json` 里确有该条、`disposition=flag`。
- **丁（ladder 取声明刻度）在真跑上没有报错**，ladder 正常推出 2 级。
