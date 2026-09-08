# 派工单 · 窗配对改双向 + W#7（GLM 施工 / Claude 审）

> **派工方** = orchestrator　**执行方** = GLM 席位（`glm-5.3`）
> **工作目录写死 `/tmp/w1_windows_claude`**，分支 `wt/09.08_windows`，基点 `802b689e`
> **题面** = `AI_agent/logs/reviews/verdict/2026-09-08g_window_landing_readout.md`

## 〇 · 当前状态（主控实测，⛔ 非转引）

✅ **31 个窗已进入真实归档**（`run_win_e2e/1_correction/attempts/001/output.json`），
全部绑段、全部有 `room`、`floor` 全部派生，`corrections=31`。
✅ 主控独立全量 **4085 passed / 0 failed**。
⛔ gate① 剩两条红：`window_position_evidence_shadow`（任务 A）与
`evidence_debt_coverage`（任务 B）。

## 一 · 任务 A：配对改成**互为最近**（主险）

```
21/31 window(s) failed the independent plan-authority vs elevation-corroborator
pairing decision (cross-check only — does not affect accept/reject)
reject_codes            : {position_evidence_pair_mismatch: 21}
max_legacy_span_delta_m : 0.0425 m       （在主控 60mm 容差内）
evaluated_conditions    : ambiguity_margin · claim_consistency · distance_within_tolerance
                          · scope_resolution · source_not_reused · ⭐ unique_mutual_nearest
```

**主控判断（⚠️ 是判断不是实测，⛔ 请你先自己验一遍再动手）**：
`src/agent/correction/as_drawn_windows.py` 的 `_plan_rows_for` 是**单向**最近
（每个立面洞口找最近的平面候选），而影子校验要求 **`unique_mutual_nearest`**——
A 的最近是 B **且** B 的最近也必须是 A。上下楼窗竖向对齐时单向极易配错。

**要做**：
1. 配对改**双向互为最近**；
2. 补上 `source_not_reused`（同一条平面观测不许被两个窗复用）
   与 `ambiguity_margin`（次优与最优的差距要够大，否则算歧义）；
3. ⛔ **别去读影子校验的实现来「对答案」** —— 那会变成照着它的实现写，
   而不是把配对做对。先按几何/证据本身把双向配对做对，再看它的读数。

⭐ **判据 = 该影子校验的 `rejected_window_ids` 降到 0**，⛔ **不是「窗数还是 31」**。

⚠️⚠️ **若改成互为最近后窗数下降**（某些立面洞口配不上唯一的平面候选）——
**那是真实信息，必须记进 `AsDrawnWindowAccount` 并在交件里写清是哪几个、为什么**，
⛔ **不许为了保住 31 这个数把判据放宽回单向**。
⇒ 31 是上一轮的读数，**⛔ 不是验收目标**。

⛔ **停下上报触发器**：若你实测发现主控上面那条病因判断**是错的**
（例如失败根因不是单双向、而是 `scope_resolution` 或 `claim_consistency`），
**停下报** —— 历史读数 74/74 全是派工方的题错。

## 二 · 任务 B：W#7 `evidence_debt_coverage`

```
⛔ 1 view/global evidence debt item(s) were not mentioned in correction audit
```

那条债是 `WINDOW_EVIDENCE_ON_CHAIN_NOT_ON_LEDGER`（主控在 S1 把它从 docstring
做成了真落盘的 `EvidenceDebt`）。消费对账门要求**每条落盘的债都要在 correction 审计里被认领**。

⚠️ **先问一句再动手**：补窗之后，as_drawn 腿的窗**已经走上了 ledger**
（96 行窗源目录 + 31 条 claim_links）。
⇒ **这条债本身可能已经该退休了**，而不是「补一条认领语句」。
⛔ **不要默认它还成立** —— 先实测「这条债现在描述的事实还存不存在」，再决定是**认领**还是**退休**。
（同型教训：主控上一轮就是照着一条**已被自己改动变假**的旧病因派了工。）

## 三 · 验收

1. 影子校验 `rejected_window_ids` **= 0**（或：不为 0 时，逐条给出为什么它是对的而校验是错的）；
2. `attempts/001/output.json` 的 `windows` 长度**有读数**（⛔ 不预设是 31）；
3. 主控独立全量 **0 failed**；
4. 跑测 ⛔ 禁 `uv run`：
   `cd /tmp/w1_windows_claude && PYTHONPATH=/tmp/w1_windows_claude /opt/venv/bin/python -m pytest -n 6 -q`
5. 跑 flow 要凭据：`set -a && . /workspaces/EnergyPlus-Agent-dev/.env && set +a`

## 四 ⭐⭐⭐ 分段提交：三个触发点（你上一轮 4 段全落零丢失，继续用）

**A** 开始下一段前 · **B** 跑全量前 · **C** 写交件前 —— 各先 commit。
⛔ 只 `git add` 明确路径，禁 `git add -A`；commit 前必看 `git diff --cached --numstat`。

## 五 · 交件

`AI_agent/logs/reviews/execution/2026-09-08h_pairing_execution.md`，末尾要有「我这次最薄弱的一处」。
