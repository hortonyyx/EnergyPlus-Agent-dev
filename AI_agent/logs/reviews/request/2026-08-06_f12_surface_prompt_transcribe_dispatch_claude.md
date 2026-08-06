# 施工单 · F-12：下游 surface 节点改为「逐字照抄内核顶点」

- **日期**：2026-08-06
- **派工方**：orchestrator（Opus 5）· **用户已拍板**（选项 A + 架构债立项 + 授权跑真实下游验证）
- **席位**：Claude 侧 Sonnet 子代理（施工档）· **主工作树**
- **基点**：分支 `6.15_ValidationArchM0toM4`，HEAD 应为 `dfbd62a`

---

## 0. 开工自检（不对就停）

```bash
git log --oneline -1     # 期望 dfbd62a
git status --short       # 4 个 case_tests 未跟踪目录 + 本单，属已知；⛔ 不要动它们
pwd                      # 期望 /workspaces/EnergyPlus-Agent-dev
```

---

## 1. 背景与**最新定性**（⚠️ 与昨天登记的不同，以本节为准）

几何由本项目侧的确定性内核算出，冻结成 `5_intakeoutput/output_coordinate_snapshot.json`。
之后交给下游 LangGraph 的 `surface` 节点（LLM react agent）去建 `BuildingSurface:Detailed`。

**病灶**：`src/agent/nodes/surface.py` 的 `SURFACE_SYSTEM_PROMPT` **逐字命令 LLM 用 `zone_specs` 的
`z_floor`/`ceiling_height` 自己重算墙顶点**（:29-33），并给了一段自相矛盾的 worked example（:40-53），
而 `surface_specs` **本来就已经给出每一面的完整绝对世界坐标顶点串**。
⇒ 提示词与数据打架，LLM 去"重新推导"而不是照抄。

**后果**：`_vertex_drift_issues`（`src/validator/output_coordinates.py:816-840`，逐位严格相等）
在 `run_2026-08-06_wall3_a_retest` 报 **44 条 `VERTEX_FRAME_DRIFT`**（24 个 exterior 墙全中 +
20 对 interzone 墙每对一个），validate 连拦 4 轮触发 `InterruptLoopBreakerError`，**永远到不了仿真**。

### ⭐ orchestrator 零成本回溯实测（本单新增，**这条改写了定性**）

拿 **07-02 那次真跑到 EnergyPlus 的 run**（`run_2026-07-02_sonnet_flow_e2e`，
有 `5_intakeoutput/intake_output.json` + `EP/temp_20260702_132413.idf`）做内核 vs 最终 IDF 逐面对账：

```
同名可比 100 面
  逐顶点完全一致 : 11
  不一致        : 89
    ├ 循环旋转（同一多边形、绕向不变、法向不变、EP 等价）: 89
    ├ 绕向反了（法向翻转）                              :  0
    └ 坐标真的不同                                      :  0
```

**⇒ 历史上下游的偏差是纯「起笔点不同」，不是坐标错、不是手性反。**
（那次几何其实是对的，EP `0 Severe` 名副其实。当时没有这把尺子：drift 门代码 07-14 才写，
`include_vertex_drift` 08-06 才接进链路，且全仓只有今天这个 run 带快照。）

**⇒ F-12 的定性从「下游把墙建错了」降级为「下游没有逐字转录，起笔点漂移，撞上新上线的严格门」。**
仍必须修（不修永远熔断），但你在施工时**不要假设坐标是错的**。

⚠️ **今天那 44 条的精确形态并未实测**（下游顶点未落盘）。上面是**强证据下的主假设，不是已证事实**。
本单的修法对「顺序漂移」和「坐标漂移」**两种都成立**，所以不依赖该假设。

---

## 2. ⛔ 硬边界（先读，违反即停）

- ⛔ **不许放宽 drift 门**：不改 `src/validator/output_coordinates.py`、不改容差、不加"循环旋转视为等价"的豁免。
  **门保持逐位严格是刻意的** —— 严格才抓得住真正有害的绕向反转（法向翻转 ⇒ 内外面反转、窗挂错房间）。
  修法**只在提示词侧**让下游忠实照抄，使严格门能真的归零。
- ⛔ **不改 `src/agent/geometry/`、`src/agent/intakeoutput.py`、`src/agent/correction/`**（内核与装配没坏，已实测）。
- ⛔ **不改 `_BASE_SIGN` / 方向约定**（用户已定案，与本单无关）。
- ⛔ **不碰 `case_tests/` 下 4 个未跟踪目录**（只读）。
- ⛔ **不 push**。commit 可以（见 §6）。

---

## 3. 施工内容

### 3.1 主项：`src/agent/nodes/surface.py` 的 `SURFACE_SYSTEM_PROMPT`

**目标**：把墙（及所有面）的顶点来源从「LLM 用 `zone_specs` 重算」改成「**逐字照抄 `surface_specs` 已给的顶点串，含顺序**」。

必须处理到的点：

1. **删掉 `## CRITICAL: per-floor z values come from zone_specs` 那整节的"重算"命令**（:18-38 区域），
   连同 :40-53 那段 worked example（它自己先写错再更正，是噪声源）。
2. **换成「照抄」指令**，语义须覆盖：
   - `surface_specs` 的每一面**已给出完整的绝对世界坐标顶点串**（该块开头即声明
     `Surfaces (vertices CCW from outside, absolute world coordinates in meters)`）；
   - **逐字转录，包括顶点的先后顺序与起笔点** —— ⛔ 不许重算、⛔ 不许重排、⛔ 不许四舍五入、⛔ 不许补齐或去重；
   - `zone_specs` **只用于 zone 名称与邻接/构造语义，⛔ 不作为顶点来源**。
3. **:63 那句** `using zone_specs' per-zone z_floor + ceiling_height for vertex z` 必须一并改掉，
   否则 Workflow 段会和新指令打架。
4. **:73 `Order counter-clockwise when viewed from OUTSIDE`** 与"照抄"冲突 ⇒ 改成
   「`surface_specs` 给的顺序已是 CCW-from-outside，照抄即可，⛔ 不要自己重排」。
5. §Rules 其余约束（名字 verbatim、boundary condition、surface_type、>=3 顶点等）**保留不动**。
6. ⚠️ **别把提示词写成需要模型做算术**。它唯一该做的是"抄"。

### 3.2 顺带项（同族潜伏隐患，低风险，**同批修**）

`src/agent/nodes/fenestration.py:42-43`：
```
- Typical window-to-wall ratio: 0.3-0.4 on facade walls; derive vertex
  coordinates from the parent wall's corners and the WWR.
```
这句**同样是命令 LLM 推导几何**，与 F-12 同族。它今天没发作是因为 `fenestration_specs` 给了裸顶点、
模型照抄了（窗零漂移）。⇒ 改成「照抄 `fenestration_specs` 给的顶点，⛔ 不要用 WWR 推导」。

⚠️ **窗目前是过的** ⇒ 验证时必须证明**窗仍然零漂移**（不能改坏它）。

### 3.3 备份与变更登记（CLAUDE.md §5#4 硬规矩，⛔ 别漏）

- 改前 `cp` 到 `backup/src_history/2026-08-06_f12_surface_prompt_transcribe/`。
- 在 [`AI_agent/logs/downstream_agent_changes.md`](../../logs/downstream_agent_changes.md) **记一条**
  （下游 subagent prompt 的维护权名义上归 §3 协作者，本地 hotfix 必须留痕）。

---

## 4. 锁（防回退）

写在 `tests/` 下（新文件或就近文件，你定），至少覆盖：

1. **`SURFACE_SYSTEM_PROMPT` 必须含"照抄顶点"语义的指令**，且 **⛔ 不得再含"用 `zone_specs` 的
   `z_floor`/`ceiling_height` 算顶点 z"这条命令**。断言要落在**可指认的具体字串/正则**上。
2. **`FENESTRATION_SYSTEM_PROMPT` 不得再含"用 WWR 推导顶点坐标"的指令。**
3. **⛔ 不许写成「长度变了 / 不是 None / 包含某个泛词」这种伪锁。**

### ⭐ neuter 自验（本项目硬纪律，8/8 教训）

锁写完后**你自己先 neuter 一次**：把提示词**改回缺陷形态**（把重算指令加回去），确认**锁真的变红**；
再恢复。**判别问法 = 「把病灶改回原样，锁红不红？」** —— 只做"函数内部 neuter"而不动病灶本体 = **假锁**。
在交付日志里写清楚 neuter 做了什么、红了几条、红在哪条断言。

---

## 5. ⭐ 验收（用户已授权烧 DeepSeek 的钱，约十几分钟）

**主验收 = 真链路，⛔ 夹具自洽不算数**（F-5 教训：测试绿、真链路崩是这一族缺陷的定义）。

```bash
# 用现成的中间产物跑下游，省掉 0–4 段的钱
python scripts/run_full_pipeline.py --intake-from \
  case_tests/e2e_tests/sm21_anchor/run_2026-08-06_wall3_a_retest/5_intakeoutput/intake_output.json \
  ...   # 具体参数你自己看 scripts/run_full_pipeline.py 的 argparse 定；
        # ⚠️ 必须让 output_coordinate_contract.json + output_coordinate_snapshot.json 一起进去，
        # 否则 drift 门会因为拿不到快照而整段跳过（output_coordinates.py:669-670）——
        # 那样的"绿"是假的，等于没验。这一条务必先确认再跑。
```

**验收条件（逐条给证据，⛔ 不接受「我看了」）**：

1. **`VERTEX_FRAME_DRIFT` 归零**（此前 44 条）。给 `grep -c` 数字 + 日志路径。
2. **窗仍然零漂移**（此前就是 0，不能改坏）。
3. **不再触发 `InterruptLoopBreakerError`**，链路走过 validate。
4. **跑到 EnergyPlus 且 `0 Severe`** —— 若在更后面撞到**新的**墙（很可能，F-11/F-12 之后还没人到过那儿），
   **不算你的锅**：如实登记新缺陷编号候选 + 现象 + 你的定性，**⛔ 不要顺手修**（越界）。
5. **全仓零回归**：`pytest -n auto`，基线 **2234 绿 / 10 xfail / 0 红**。给完整尾部输出。
6. 日志落 `AI_agent/logs/experiments/2026-08-06_f12_transcribe_verify/`（跑测日志 + 对账脚本输出）。

**⭐ 顺带闭合 Q1**：如果拿得到下游建出来的顶点（比如跑到 IDF 落盘了），
用与 orchestrator 同法做一次**内核 vs 最终 IDF** 的分层对账
（逐顶点一致 / 循环旋转 / 绕向反 / 坐标不同），把今天的形态钉死。
参考脚本思路见本单 §1 的回溯结果；⛔ 别去读 orchestrator 的临时脚本，自己写一份放 `/tmp`。

---

## 6. 交付

- 执行日志落 `AI_agent/logs/reviews/execution/2026-08-06_f12_surface_prompt_transcribe_claude.md`：
  改了什么 / 为什么这么改 / 锁在哪几条 / **neuter 做了什么红了几条** / 真链路验收逐条证据 / 全仓数字 /
  遇到的新墙（若有）。
- **可以 `git commit`**（message 仿 `08.06_f12_surface_prompt_transcribe`，body 含 ①改动 ②为何此刻 ③影响）。
  ⛔ **不 push**。⛔ **不许 `git add -A`** —— 逐个文件 add，`case_tests/` 下 4 个未跟踪目录**不得进提交**
  （历史实犯：`git add -A` 把别的席位的半成品扫进提交）。

---

## 7. 停下上报（**记功不记过**）

本轮至今 **8 次「停下上报」，8 次全是派工方（orchestrator）的题错了**。

⇒ 本单陈述的事实与你看到的不符（比如 :29-33 的行号对不上、`surface_specs` 其实没给顶点、
验收条件互相冲突、`--intake-from` 根本喂不进快照）⇒ **立刻停下如实上报，⛔ 不要硬凑一个符合本单框架的答案。**

另两条 orchestrator 自检失败史，供你反向核我：
- 写行为锁前先读代码问「这个差异我指得出是哪一行产生的吗」；
- 验收条件之间必须互不冲突。
