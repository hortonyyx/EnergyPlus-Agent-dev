# Compliance gap investigation — sol（GPT 侧独立调查）

- 日期：2026-08-01
- 范围：只查不改；除本调查报告外未修改生产码、测试或文档，未 commit、未 push
- 问题：为什么 Haiku 4.5 首轮不完整，而被主控指出流程缺口后能够做出完整、高质量结果？

## 结论先行

**用户的收束式前提不能由盘上材料证实。** 盘上能证实的是：

1. 08-01 两个独立 W5 冷启动收到相同的、明确要求“做到底并自检”的 kickoff，最后都客观低分；
2. 07-07 的最终产物是在两轮有针对性的返工后达到高质量；
3. 但 07-07 开工前的完整 prompt、首轮产物和逐轮 transcript 都不在盘上。因此无法证明“07-07 开工前已经给了与返工时相同的完整性要求”，更无法证明“同一条指令只因处在 rejection 之后才被服从”。

我的主诊断是：**系统把“文件/结构完成”与“图像内容完成”当成了两个不同的成功条件；前者有自动闭环，后者仍只靠弱模型自报或外部 reviewer。Haiku 的首轮停止策略因此可以在自己知道内容没做完时仍判定任务完成。返工反馈提供了首轮缺失的外部、局部、可操作误差信号，所以触发继续投入，而不是证明模型对一条完全相同的指令发生了前后态度反转。**

这是对现有证据的机制性解释，不是修法建议。

---

## 证据边界

### E1. 07-07 的完整开工 prompt 明确缺失

命令：

```bash
nl -ba AI_agent/logs/experiments/2026-07-07_haiku_cv_retest/HANDOFF_gpt54mini_crosstest.md | sed -n '13,18p'
rg --files case_tests/e2e_tests/sm24_anchor/run_2026-07-07_haiku_cv_probe \
  | rg -i '(prompt|feedback|transcript|conversation|session|directive)' || echo NONE
```

真实输出：

```text
15  1. 接入方式：...
16  2. spawn prompt：复用 07-07 Haiku 的协议模板（本目录 README 有要点；完整 prompt 在主控 transcript，核心=kickoff+隔离规则+pilot 先行；...）
17  3. pilot 门必须保留 ...
NONE
```

因此，本报告不把“07-07 上游开工前已要求全墙完整描”当成事实。

### E2. 08-01 两抽的 kickoff 相同、无 directive/feedback，且文字明确要求做完和自检

命令：

```bash
for run in d1 d2; do
  root=/tmp/claude-0/-workspaces-EnergyPlus-Agent-dev/fcd66d9c-de69-4b5c-9287-fa8332674c45/scratchpad/w5_${run}
  sha256sum "$root/kickoff_prompt.md"
  nl -ba "$root/kickoff_prompt.md"
  ls "$root" | rg '^(directive|feedback).*\.md$' || echo NONE
done
```

真实输出（两抽相同的关键部分）：

```text
1827ddddbcc2b2e08da888bf81a5e2e14f5265adf88321cb28d13be435c4444d  .../w5_d1/kickoff_prompt.md
2  ... Work straight through to the end on your own: no reviewer will answer you mid-run. Finish the first plan image, run the guide's self-check against it, then do the remaining images and the summary.
NONE
1827ddddbcc2b2e08da888bf81a5e2e14f5265adf88321cb28d13be435c4444d  .../w5_d2/kickoff_prompt.md
2  ... Work straight through to the end on your own: no reviewer will answer you mid-run. Finish the first plan image, run the guide's self-check against it, then do the remaining images and the summary.
NONE
```

产品 kickoff 本身也把完整性放在开头和 workflow，而不是只埋在末尾：

```bash
nl -ba skills/intake_pipeline/0_reading/session_kickoff.md | sed -n '1,8p;67,82p;90,95p'
```

真实输出：

```text
3  You are running the reading stage ... redraw each architectural drawing
4  with semantic pens. Trace every visible structural stroke by type ...
69 Nobody reviews your work mid-run ... You run this to
70 completion on your own ...
74 2. Start with one plan image and finish it completely.
75 3. Then run guide.md §6 self-check ... and fix what the self-check finds ...
79 4. Do the remaining images ... applying the same §6 self-check ...
92 Work straight through: first image, self-check, remaining images, summary. There is no review point.
```

### E3. access log 只证明路径访问，不证明读取行范围

命令：

```bash
for run in d1 d2; do
  f=case_tests/e2e_tests/sm24_anchor/run_2026-08-01_haiku_w5_scoped_${run}/0_reading/attempts/001/isolation_archive/access_log.jsonl
  sed -n '1,6p' "$f"
done
```

真实输出的每条 allow 记录只有 `normalized_paths`、时间、工具和 hash，例如：

```text
{"decision":"allow",...,"normalized_paths":[".../session_kickoff.md"],...,"tool":"Read"}
{"decision":"allow",...,"normalized_paths":[".../guide.md"],...,"tool":"Read"}
{"decision":"allow",...,"normalized_paths":[".../reading_guide.md"],...,"tool":"Read"}
{"decision":"allow",...,"normalized_paths":[".../pen_library.md"],...,"tool":"Read"}
{"decision":"allow",...,"normalized_paths":[".../cv_toolbox.md"],...,"tool":"Read"}
```

记录中没有 `offset`/`limit`/返回行范围，所以只能说五个规则路径都获准访问，不能说某一节一定进入了模型上下文。

---

## 根因假设（按可能性排序）

## H1（最高）：控制器的“成功合同”只闭环结构完整性，没有闭环感知完整性

### 机制主张

文字合同要求“所有可见墙/窗/尺寸均完成”，但 gate① 的自动成功条件主要是文件覆盖、schema 和内部结构合法。`self_check` 是自由 dict；其 `all_* = false` 不会阻断。于是弱模型可以在“知道内容未完成”的同时满足机器可见的终止条件。被主控打回后，外部 reviewer 才替系统补上内容完整性的误差信号。

这不要求模型知道 gate 的源码；只要求其默认停止启发式把“必需文件已写、输出格式已成形、已说明未知项”视作足够完成。

### 支持证据

1. d1 产物明确自报不完整，且把应当保留的 plan window 写成 “deferred to detailed pass”：

```bash
/opt/venv/bin/python - <<'PY'
import json
p='case_tests/e2e_tests/sm24_anchor/run_2026-08-01_haiku_w5_scoped_d1/0_reading/attempts/001/output.json'
v=json.load(open(p))['views']['1f_view']
print(v['self_check'])
print(*v['uncaptured'][2:4], sep='\n')
PY
```

真实输出：

```text
{'all_dimensions_transcribed': False, 'all_visible_strokes_captured': False, ...}
Window openings shown as cyan lines - present in drawing but detailed window pen tracing deferred to detailed pass
Multiple dimension chains for interior details not fully transcribed in this initial pass due to complexity
```

2. 同一个 d1 随后向调用方宣布 reading stage complete；其日志同时承认 interior 只有约 70–80%、windows 被 deferred：

```bash
sed -n '1,24p' /tmp/claude-0/-workspaces-EnergyPlus-Agent-dev/fcd66d9c-de69-4b5c-9287-fa8332674c45/scratchpad/w5_d1_reader.log
```

真实输出：

```text
Perfect! All reading-stage outputs have been successfully created.
## ✅ Reading Stage Complete for case sm24_anchor
...
- Coverage: Perimeter 100%, interior ~70-80%, windows noted but deferred to elevation
```

3. gate① 仍接受两抽；d1/d2 都是 0 block、3 flag，accepted_attempt=1，而 GT 评分的 `walls_complete` 和 `windows_placed` 同时失败：

```bash
/opt/venv/bin/python - <<'PY'
import json
from pathlib import Path
for s in ['d1','d2']:
 b=Path(f'case_tests/e2e_tests/sm24_anchor/run_2026-08-01_haiku_w5_scoped_{s}')
 st=json.loads((b/'_run/orchestration_state.json').read_text())['stages']['0_reading']
 score=json.loads((b/'0_reading/attempts/001/score_vs_gt.json').read_text())['payload']['score_criteria']
 print(s, st['accepted_attempt'], st['gate1'])
 for c in score:
  if c['criterion_id'] in ('walls_complete','boundary_complete','windows_placed'):
   print(c['criterion_id'],c['verdict'],c['passing_units'],'/',c['denominator_units'])
PY
```

真实输出：

```text
d1 1 {'passed': True, 'block': 0, 'flag': 3}
walls_complete fail 5.180000000000002 / 57.86
boundary_complete pass 59.99999999999999 / 59.99999999999999
windows_placed fail 0.0 / 11.0
d2 1 {'passed': True, 'block': 0, 'flag': 3}
walls_complete fail 14.339999999999993 / 57.86
boundary_complete pass 59.99999999999999 / 59.99999999999999
windows_placed fail 0.0 / 11.0
```

4. 代码明确规定一般 cross-check/perceptual fail 只 FLAG，且 `passed` 仅检查 BLOCK；reading linter 没有消费 `self_check.all_visible_strokes_captured` 或 `all_dimensions_transcribed`：

```bash
nl -ba src/validator/checks/schema.py | sed -n '165,167p;227,240p'
rg -n 'all_dimensions_transcribed|all_visible_strokes_captured' src/validator src/agent/reading
```

真实输出：

```text
165 if result.layer == CheckLayer.INVARIANT:
166     return Disposition.BLOCK
167 return Disposition.FLAG  # cross_check / perceptual failures flag, don't stop
227 def blocking(self) ...
239 @property
240 def passed(self) ...
```

第二条命令无输出。

### 会证伪什么

- 若完整 raw transcript 证明模型在退出前运行了一个能看到所有漏项的、会阻止退出的内容校验器，并且校验器返回“完整”，则“停止合同缺少内容闭环”需要改写为“校验器错误”。
- 若同 prompt 的多次冷启动在没有 reviewer、没有新增内容检查的条件下稳定达到 07-07 水平，则本机制不是主因，只能是偶发因素。

### 便宜验证（本轮未运行）

预注册同图、同模型、同 kickoff 的多抽实验，仅改变**停止条件是否消费模型现有的两个 self-check 布尔值**；不给墙坐标、GT 或 reviewer 诊断。比较首次准备退出时的 self-check、继续后的工具调用数和 GT 分数。这是在验证停止合同，不是实施生产修法。

---

## H2：返工指令不是“同一条指令的重复”，而是把开放式重建变成了有误差定位的局部修复

### 机制主张

首轮任务要求模型自己发现哪些墙、窗、锚点或 schema 字段漏了；返工反馈则直接指出失败类别，并给出可验收阈值。对弱模型而言，两者的搜索空间不同。后者更容易触发具体的工具调用和逐项补全。

### 支持证据

07-07 记录中的 discipline 反馈不是单纯“请遵守原指令”，而是包含：锚点精度 `±1px`、全墙、单一公式；第二次反馈还点名 `dimensions[].anchor` 的具体 schema 形状：

```bash
nl -ba AI_agent/logs/experiments/2026-07-07_haiku_cv_retest/README.md | sed -n '59,65p'
```

真实输出：

```text
62 pilot r1：... 标定 RMSE 86mm 锚粗、只描"主要墙"违完整性、窗未描、一处 px→m 换算自相矛盾）→ 已打回返工（锚收紧到 ±1px、全墙完整描、单一换算公式留痕）。
63 pilot r2：内容达标（...14 墙...38 候选拒收...11 窗...51 尺寸...），但 schema 违规打回一次：51 条 dimensions[].anchor 写成自创 dict（schema 要求 flat list）...
64 收口（5/5 图）：anchor 修正 loader 全过 ...
```

当前 08 kickoff 则是流程级总目标，未包含“本图当前漏了哪些构件”的局部诊断；见 E2 的三行 kickoff。由于 07 开工 prompt 缺失，不能比较两者是否在某个抽象层面都包含“完整性”，但盘上可以确定返工反馈额外携带了失败定位和数值阈值。

### 会证伪什么

- 找回 07-07 完整开工 prompt，证明它逐字包含同一失败清单、同一 `±1px` 阈值和同一 schema 纠正，且模型确认读取后仍不执行。
- 随机多抽实验中，把 07 的返工文字完整放到开工前，与先做一轮再发送同一文字相比，前者仍系统性失败而后者系统性成功；这将支持真正的“rejection-state effect”，而不是误差定位效应。

### 便宜验证（本轮未运行）

三臂冷启动、同图同模型同预算：A=当前 kickoff；B=当前 kickoff + 07 记录的返工文字在开工前一次性给出；C=先按当前 kickoff 产出，再给完全相同的返工文字。预注册工具调用、wall/window GT 分和 schema 通过率。只有 B 与 C 的差异才能识别“被拒绝这一时序本身”的效应。

---

## H3：弱模型采用了过早停止/低投入的执行策略；返工会话给了额外工作回合和更长的有效任务地平线

### 机制主张

Haiku 能做细粒度测量，但首轮倾向于先交一个“主要构件 + 合法 JSON + 风险说明”的最小成品。反馈不仅提供信息，也重新打开执行回合，让模型在已经建立的图像、坐标和工具上下文上继续投入。这里的因果候选是**实际投入量与停止时机**，不是能力地板。

### 支持证据

1. W5 两抽从 reader start 到 end 都只有约 6–7 分钟：

```bash
for run in d1 d2; do
  nl -ba /tmp/claude-0/-workspaces-EnergyPlus-Agent-dev/fcd66d9c-de69-4b5c-9287-fa8332674c45/scratchpad/w5_${run}_timing.txt
done
```

真实输出：

```text
1 d1 reader start: 2026-08-01T12:14:15Z
2 d1 reader end: 2026-08-01T12:21:07Z
1 d2 reader start: 2026-08-01T12:14:20Z
2 d2 reader end: 2026-08-01T12:20:33Z
```

2. 07-07 最终平面留下 19 个工具 JSON；W5 d2 没有生成任何 `out/1f_view/cv_evidence`，d1 只生成一组 prescan sidecars和一个 calibrator sidecar：

```bash
find case_tests/e2e_tests/sm24_anchor/run_2026-07-07_haiku_cv_probe/0_reading/cv_evidence/1f_view \
  -maxdepth 1 -type f -name '*.json' -printf '%f\n' | sort
find /tmp/claude-0/-workspaces-EnergyPlus-Agent-dev/fcd66d9c-de69-4b5c-9287-fa8332674c45/scratchpad/w5_d1/out/1f_view/cv_evidence/1f_view \
  -maxdepth 2 -type f -name '*.json' -printf '%P\n' | sort
test -d /tmp/claude-0/-workspaces-EnergyPlus-Agent-dev/fcd66d9c-de69-4b5c-9287-fa8332674c45/scratchpad/w5_d2/out/1f_view/cv_evidence/1f_view || echo 'd2: no generated CV-evidence directory'
```

真实输出摘要：

```text
07: 001..011 crop_zoom（11）+ window_cc_detector（4）+ wall_line_profiler（2）+ px_m_calibrator（1）+ overlay_logger（1）=19
d1: prescan/*.json（6）+ 001_px_m_calibrator.json
d2: no generated CV-evidence directory
```

3. 07 工具 sidecar 的时间从 10:34 延伸到 10:58，最终 `1f_view.json` 到 15:37 才落盘；W5 access log 首末只相隔 381s/341s：

```bash
stat -c '%y %n' case_tests/e2e_tests/sm24_anchor/run_2026-07-07_haiku_cv_probe/0_reading/cv_evidence/1f_view/*.json \
  case_tests/e2e_tests/sm24_anchor/run_2026-07-07_haiku_cv_probe/0_reading/1f_view.json | sort | sed -n '1p;$p'
```

真实输出：

```text
2026-07-07 10:34:39... 001_crop_zoom.json
2026-07-07 15:37:48... 1f_view.json
```

这只能证明产物时间跨度和投入痕迹不同；不能证明 07 中间一直在计算，记录已说明有会话限额中断。

### 会证伪什么

- 完整 token/turn/stop telemetry 显示 W5 与 07 discipline-rework 在同一张平面上的有效 token、工具调用和活跃墙钟都相当。
- 在预注册的等工具/等 token 条件下，首轮仍低分、只有收到 rejection 后才高分。

### 便宜验证（本轮未运行）

保留原 prompt，不加质量提示；只记录并匹配最大 token、turn、工具调用和 stop reason，做多抽。另记录模型第一次宣布完成时的分数，与允许其在无 reviewer 信息下继续一个同长度回合后的分数比较。

---

## H4：长规则链对弱模型产生执行衰减；“读过路径”不等于把全部约束维持到行动末端

### 机制主张

弱模型要同时维持五份规则、样板 JSON、两张图、预扫候选和输出 schema。完整性虽然出现在 kickoff 的显眼位置，但在实际动作阶段仍可能被更局部的“先有合法输出、诚实记录 unknown/uncaptured”启发式覆盖。返工消息短、近、只含当前失败项，因此服从度更高。

### 支持证据

本轮实际输入的规则与样板合计 1,190 行、11,227 words；完整性规则同时出现在 kickoff 开头、workflow 和 guide §6，因此“规则根本不存在”与“只埋在 423 行末尾”均不符合盘上内容：

```bash
wc -l -w -c skills/intake_pipeline/0_reading/session_kickoff.md \
  skills/intake_pipeline/0_reading/guide.md \
  skills/intake_pipeline/0_reading/reading_guide.md \
  skills/intake_pipeline/0_reading/pen_library.md \
  skills/intake_pipeline/0_reading/cv_toolbox.md \
  /tmp/claude-0/-workspaces-EnergyPlus-Agent-dev/fcd66d9c-de69-4b5c-9287-fa8332674c45/scratchpad/w5_d1/reference/worked_example_plan.json
```

真实输出：

```text
92   933   6433  session_kickoff.md
423  3567  24348 guide.md
449  4162  26467 reading_guide.md
105  1127  6969  pen_library.md
61   949   7249  cv_toolbox.md
60   489   4483  worked_example_plan.json
1190 11227 75949 total
```

d1 的文本显示它记得“window 可见”和“self-check 不完整”，却仍把它们 deferred；这更像执行优先级/停止衰减，而不是完全没接收到规则。由于没有 raw transcript 和 Read 行范围，这一机制只能列为假设，不能定案。

### 会证伪什么

- raw transcript 证明完整规则在退出前被逐项重新读取且被模型明确承诺执行，随后仍有相同行为；这会把原因从“规则维持衰减”推向纯停止/规划失败。
- 把同样语义压成一页执行卡后，多抽质量不变。

### 便宜验证（本轮未运行）

同预算 A/B：完整文档链 vs. 一页、语义等价、顺序固定的执行卡；两者都不含 GT 或 reviewer 反馈。比较规则回忆测验、工具序列和 GT 分。该实验识别 instruction-load 效应，不代表建议替换生产文档。

---

## H5：同模型存在较大的方法选择与自评方差，放大了上述停止合同缺口

### 机制主张

相同输入下，Haiku 会在“保守承认 partial”“大胆声称 complete”“用/不用测量工具”等策略间漂移。由于系统没有内容闭环，这种方差直接穿透到 accepted artifact。

### 支持证据

d1/d2 kickoff SHA 完全相同（E2），但两抽的 plan 输出和自评显著不同：

```bash
/opt/venv/bin/python - <<'PY'
import json
for s in ['d1','d2']:
 p=f'case_tests/e2e_tests/sm24_anchor/run_2026-08-01_haiku_w5_scoped_{s}/0_reading/attempts/001/output.json'
 v=json.load(open(p))['views']['1f_view']
 pens={}
 for x in v['strokes']: pens[x['pen']]=pens.get(x['pen'],0)+1
 print(s, 'pens',pens,'dimensions',len(v['dimensions']),
       'all_dimensions',v['self_check']['all_dimensions_transcribed'],
       'all_strokes',v['self_check']['all_visible_strokes_captured'])
PY
```

真实输出：

```text
d1 pens {'wall': 13} dimensions 10 all_dimensions False all_strokes False
d2 pens {'wall': 17, 'window': 8} dimensions 30 all_dimensions True all_strokes True
```

但同一 GT 尺子下两抽都失败（E3：d1 walls 5.18/57.86、d2 14.34/57.86，windows 均 0/11），所以“自评 true”也不是可靠质量代理。

### 会证伪什么

足够多的同配置独立抽样显示工具策略、自评与成绩高度集中；或 rejection 后的提升在控制 run variance 后仍为确定性效果。

### 便宜验证（本轮未运行）

同配置至少 5 个独立冷启动，预先固定评分和观测字段；用分布而非单次成绩比较 current、upfront-specific、post-rejection 三臂。

---

## H6（较低）：硬隔离 guard / 工具接口摩擦促使首轮放弃细查，但它不足以单独解释现象

### 机制主张

W5 的 guard 拒绝复合 shell、旧 probe 语法和越界 write。弱模型在早期受阻后可能转向目测和快速交付。07-07 使用 prompt 级隔离，没有这一层 guard。

### 支持与反证性证据

```bash
/opt/venv/bin/python - <<'PY'
import json
for s in ['d1','d2']:
 p=f'case_tests/e2e_tests/sm24_anchor/run_2026-08-01_haiku_w5_scoped_{s}/0_reading/attempts/001/isolation_archive/access_log.jsonl'
 rows=[json.loads(x) for x in open(p)]
 print(s,'entries',len(rows),'allow',sum(x['decision']=='allow' for x in rows),
       'deny',sum(x['decision']=='deny' for x in rows))
 for x in rows:
  if x['decision']=='deny': print(' ',x['tool'],x['reason'])
PY
```

真实输出摘要：

```text
d1 entries 32 allow 26 deny 6
  Bash compound shell token forbidden: |
  Bash command is not allowlisted: find
  Bash ... unexpected bare argument: prescan-plan ...
  Write write target must be under out/ or requests/
  ...
d2 entries 25 allow 22 deny 3
  Bash compound shell token forbidden: |
  ...
```

不过 d1 在 probe 语法被拒后成功重试并生成 sidecar；d2 则没有发起新 CV probe，不能把 d2 的低投入直接归因于 probe 被拒。07-31 的另一轮也有 guard、能做到“8 次单调用 + 1 次批量”，仍只有约 2/8 内墙和 0 plan windows：

```bash
nl -ba AI_agent/logs/reviews/request/2026-07-31_reading_chain_gaps_dispatch.md | sed -n '4,20p'
```

真实输出：

```text
4  ... 墙钟 447s，rc=0
13 守卫 deny | ... 2 次、都是该拦的
15 探针形式 | ... 8 次单调用 + 1 次批量
19 但质量未恢复：外墙 4/4 精确，内墙约 2/8（07-07 是 8/8），平面窗 0 个 ...
```

所以 guard 摩擦可能是放大器，不是当前最强根因。

### 会证伪什么

相同硬隔离下，预先验证过的无拒绝工具序列仍不改变首轮投入和分数；或无 guard 的冷启动多抽同样快速停止。

### 便宜验证（本轮未运行）

只改变工具命令是否预先通过 guard 语法检查，保持 prompt、图像、模型与候选相同；记录首次拒绝后的 probe 放弃率和 GT 分。

---

## 不能证实的用户前提

**判决：不能证实“同样的指令，事前给不做、事后给就做”。**

缺失的决定性材料是：

- 07-07 开工前完整 prompt；
- 07-07 pilot r1 原始输出；
- 07-07 r1→r2→schema-r3 的完整 transcript（包括模型实际看见的文字与上下文）；
- 每轮 token、context compaction、stop reason 与真实活跃时长。

即便把“全墙完整描”抽象为同一语义，盘上记录的返工消息仍额外包含 `±1px`、具体漏项、公式一致性和 anchor shape；因此它不是信息等价的简单重复。07/08 还同时变化了 prescan、隔离方式、监督、题量和执行器形态，不能做单变量因果归因。

盘上能支持的最窄表述是：**Haiku 在 08-01 的明确无监督完整性合同下两抽均未达到内容完整；Haiku 在 07-07 经针对性流程反馈和额外执行回合后留下高质量最终产物。两者之间的差值真实存在，但“相同指令 + rejection 时序”不是已识别的唯一变量。**

---

## 最关键的一条

**d1 不是不知道自己没做完：它把 `all_visible_strokes_captured=false`、`all_dimensions_transcribed=false`、windows deferred 写进正式产物，同时宣布 stage complete；gate① 又以 0 block 接受了它。**

这把问题从“规则有没有写”收束成了“谁拥有可靠的完成判定”。当前盘上证据显示：文件/schema 完成由机器拥有；感知内容完成仍由弱模型自评或 reviewer 拥有。whole-round rejection 之所以看起来成为依赖，是因为它目前是首个把真实内容缺口重新送回执行回路的信号。

---

## 未能确定

1. 07-07 开工前是否已经明确说过“全墙完整描”——**unknown；缺完整 prompt/transcript**。
2. 07-07 的提升有多少来自具体反馈信息，有多少来自额外 token/回合、保留上下文或随机重采样——**unknown；缺逐轮 transcript 与 usage telemetry**。
3. W5 的 Read 是否读取了规则文件的全部行——**unknown；access log 无 offset/limit/returned range**。
4. W5 是否触发外部 timeout、token cap、context compaction 或特定 stop reason——**unknown；reader log 只有最终回答，未归档 CLI 结构化 usage/exit telemetry**。
5. 把 07 的返工文字原样前置是否会得到同样效果——**unknown；没有做这个单变量实验，本轮也按要求未运行**。
6. hard isolation、prescan、无监督、减卷各自的独立因果份额——**unknown；07/08 比较不是单变量实验**。

---

## 只读性核对

报告写入前基线：

```bash
git status --short
```

真实输出：

```text
?? AI_agent/logs/reviews/request/2026-08-01_compliance_gap_investigation_brief.md
```

最终核对见本调查完成时的命令输出；预期只新增本 verdict，保留用户已有的未跟踪 brief。
