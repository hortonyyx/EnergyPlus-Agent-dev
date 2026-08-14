# 跨家族复审请求 —— 摊 A（设备段确定性渲染）+ 摊 B（IDD 通用字段对齐检查）

- **日期**：2026-08-14
- **审阅席位**：GPT 侧（跨家族。**摊 A = Claude 侧 Sonnet 施工 / 摊 B = GLM 施工** ⇒ 按「谁写谁不批」两摊都必须换人）
- **你的工作树**：`/workspaces/ep-wt-R`（独立 git worktree，分支 `wt/0814_R_review`）
- **被审**：主分支上的两笔合并 —— `41ddbcb`（摊 A）+ 其后摊 B 的合并笔。
  逐摊原始提交：摊 A `7aa18f2` · 摊 B `1472cfc`。
- **orchestrator 轻门**：
  [摊 B 轻门](../verdict/2026-08-14_seatB_idd_alignment_orchestrator_lightgate.md) ·
  摊 A 轻门结论见本文 §3。
- **席位执行报告**：
  [摊 A](../execution/2026-08-14_mep_hvac_deterministic_claude.md) ·
  [摊 B](../execution/2026-08-14_idd_field_alignment_glm.md)

---

## 0. ⭐ 停止规矩（分层）

1. **承重前提错**（§1 的事实、§2 的接缝）⇒ **停下上报**。
2. **外围论据错**（背景叙述/动机/类比）⇒ **记录后继续把主体审完**。

**派工方（orchestrator）历史错误率 19/19**，全是题错。**本日一天之内贡献四条**，如实列出供你校准：
- 「真实 run 的正向 `trusted` 从未拿到」——**盘上就有**（sol 第五轮纠正）；
- 「§5.14.1 硬约束均已照办」——**全仓还剩 11 处**（sol 纠正）；
- **给摊 B 指定的阻塞名单结构上恒绿**——发单前没核 IDD（orchestrator 自己轻门时发现）；
- 转达给摊 A 的一条失败诊断是**猜的**（说 A3 红是因为顺序没改，实际那处已改，真因是夹具缺 `construction_specs`）
  ——**施工席用可执行证据把我纠正了**。

⇒ **请主动证伪本请求书里的任何判断。**

---

## 1. 背景：这两摊在解决什么（事实部分已实测，⛔ 非推测）

08-13 验收连跑 3 次，第 3 次崩在 `4_mep` 并耗尽重抽预算 ⇒ `quarantined` ⇒ 退出码 20。
根因 = 4_mep 的 LLM 给 `ZoneControl:Thermostat` **只写 4 格、EnergyPlus 要 5 格**
⇒ 漏掉「控制类型时间表」那一格、其后全部前移 ⇒ `mep.hvac_schedule_refs` 按位置读到一个不存在的时间表名。
**14 个区每次全错、连错三次** ⇒ 整段重抽治不了系统性倾向。

**⭐ 两条当日实测查实的事实，会影响你怎么判危害等级**：
1. **`*_specs` 文本从不被贴进最终 IDF**：下游 `src/agent/nodes/hvac.py` 把它当**输入文本**喂给 ReAct agent，
   后者只能用**具名参数的 MCP 工具**建对象。**活证据**：`accept_B` 的设备段少写两格
   （`50` 落进排风节点名、`13` 落进进风节点名），而其最终 IDF 的最高送风温度就是 50、最低就是 13，**语义正确**。
   ⇒ **F-28 的真实危害是「链路被门拦死」（可靠性），⛔ 不是静默算错物理。**
2. 同一缺陷**留空就放行、填字就炸链**（`mep.hvac_schedule_refs` 的 `blank_reference_policy: pass`）
   ⇒ 08-09 与 post_blocker1 两次跑那一格是空的、一路跑到 EnergyPlus。

**预扫（发单前机械核实）**：[prescan](../../experiments/2026-08-14_mep_arity_gate_prescan/README.md)
—— 新对齐门若直接阻塞，**干净检出 20 份产物会红 14 份**，含 08-13 验收 A（EP `0 Severe`）与 08-09 首次到 EP 那份
⇒ **用户据此拍板「分档」**。

## 2. 两摊各做了什么 + 硬接缝

### 摊 A（`7aa18f2`）
`run_mep`（`src/agent/pipeline.py`）在模型返回并通过 pydantic 校验之后、写盘之前，
**无条件**用代码渲染覆盖 `hvac_specs`：`HVACTemplate:Thermostat` ×1 + 每区一个
`HVACTemplate:Zone:IdealLoadsAirSystem`，区名来自**有序** `zone_names`；
并把渲染引用的 3 张时间表确定性并入 `schedule_specs`。
接缝改动：`run_stage.py:_geometry_zone_meta` 的 `zone_names` 由 `set(...)` 改 `list(...)`（保序）。

### 摊 B（`1472cfc`）
新增 `mep.idd_field_alignment`（check 数 18→19）。判据 ①缺必填格 ②超字段数（extensible 豁免）。
分档：**阻塞名单 = 摊 A 生成的那两类**，其余只报告。
另给 `load_to_schedule` / `hvac_schedule_refs` 的 offender 加 `disease_ref` 交叉引用（报病因不报症状）。

### 接缝
摊 B 的阻塞名单**就是**摊 A 的输出形态。两摊已合并，接缝已由 orchestrator 集成实测（见 §3）。

## 3. orchestrator 轻门已做的（**⛔ 请不要重复，除非你怀疑结论**）

| 项 | 方法（均走真实入口，⛔ 非形状匹配） | 结果 |
|---|---|---|
| 摊 A **无条件覆盖** | **换方向 neuter**（席位测「喂坏文本」，我测「喂**完全合法**的文本」）：stub `_call_json_llm` 返回一段合法 `HVACTemplate` 文本，真跑 `run_mep` | 模型文本**零残留**；渲染内容在；**模型没写过的 `ZONE_B` 也出现了** ✅ |
| 摊 A **引用闭合** | 用仓里唯一 parser `parse_idf_text` 独立验（⛔ 不走席位 helper） | 引用的 3 张时间表 ⊆ `schedule_specs` ✅ |
| 摊 A 接缝 | 查 diff | `set(...)`→`list(...)` **确在 diff 内** ✅ |
| 摊 B **零回归** | 20 份真实产物，基线树 vs 摊 B 树各跑 `check_mep`，比**阻断集合** | **20/20 逐份不变** ✅ |
| 摊 B **预扫复现** | 同上 | 红 14 / 绿 6，与预扫逐份吻合 ✅ |
| **A+B 集成** | 合并后，用 14 区真实量级跑 `run_mep`→`check_mep` | 新门 `pass` · `hvac_schedule_refs` `pass` · **阻断集合空** ✅；且 `accept_C` **旧存档仍如实报 fail**（⛔ 没有靠放宽门来「修好」）✅ |

## 4. ⛔ 已知未闭合项 —— **已登记，请不要当新发现重复报**（但欢迎推翻）

1. **摊 B 的阻塞档结构上恒绿**（orchestrator 轻门发现，**是派工方题错，不记施工席的账**）：
   查 IDD 坐实 `HVACTemplate:Thermostat` 共 5 格、`\required-field` **只有 `Name`**；
   `HVACTemplate:Zone:IdealLoadsAirSystem` 共 30 格、**只有 `Zone Name`**
   ⇒ 判据①对这两类只在「连第一格都不写」时才触发；判据②又是死代码（见下）
   ⇒ **该门今天净效果 = 纯报告**。修法方向已登记 plan.md「二之四」（改成「渲染器给期望形状、门做往返断言」）。
   **⇒ 请你裁：这个形态可不可以先合、下轮再补？还是必须本轮补齐？**
2. **判据②在真实解析路径上是死代码**（摊 B 席位自陈、orchestrator 认同）：
   eppy 对超字段对象**静默截断或 crash** ⇒ `authored > idd` 对任何能解析成功的对象恒不成立。
   连带登记 **F-29**：eppy 静默吃字段且无人报警。
3. **worktree 环境假红 3 条**（**F-30**，已登记）：`test_gt_from_dxf` / `test_inspect_dxf`（CLI 子进程
   跨树导入 editable 安装 ⇒ `REPO_ROOT` 指向主树）+ `test_zone_agent`（`.env` 被 gitignore ⇒ 无 API key）。
   **⛔ 你若在 worktree 里跑全仓看到这三条红，那是环境不是回归**；权威全量由 orchestrator 在主树跑（数字见 §6）。
4. 摊 B 去重口径 = 「不复述诊断」而非「不报 offender」⇒ 同一错位 People 仍出现在两个 check 的 offender 里。**请裁。**

## 5. 两个席位自陈的未验证项（原样转达，请重点看）

**摊 A**：下游 `hvac_agent` 真实 LLM 调用是否吃得下新形态 **未验** · 真实 EnergyPlus 仿真 **未跑** ·
提示词更新后孤儿时间表是否趋零 **未验** · 零区边界 **未固化成锁** · `regression`/`golden` profile **未端到端跑**。
**摊 B**：判据②真实链路 **零实测**（仅 monkeypatch 夹具）· `smalloffice_23` 不在 CI 回归。

## 6. 权威全量（orchestrator 在**主树**跑，⛔ 不要重复）

- 合并前基线（`a413e66`）：`rc=0` · `2603 passed / 10 xfailed / 0 failed`
- **合并后（含摊 B 返工）：`rc=0` · `2629 passed / 10 xfailed / 0 failed`**
- **对账逐位闭合**：`2603（基线）+ 15（摊 A 新增）+ 11（摊 B 新增）= 2629` ✅ **零回归、零红。**

### 6.1 中途出过一条真红（已修，说明白免得你困惑）

首次合并后权威全量是 `1 failed / 2628 passed`，红的是摊 B 新写的
`test_b2_prescan_reproduction`：它**枚举文件系统**并对任何不在 20 条固定表里的产物硬失败，
而**主树开发机上存在一个未跟踪的产物**（`smalloffice_23/4_mep/`，被 `.gitignore:320` 排除）
⇒ **该断言测的是「开发者工作目录里有哪些未跟踪文件」，不是「这个提交的性质」**（F-23 同族、极性相反）。
**已由 GLM 返工修掉**（`fb171ec`，枚举口径改 `git ls-files`；未跟踪产物 `warn` + skip 并**点名记原因**；
已跟踪但不在表里的仍硬失败）。orchestrator 在**真考场**（主树、该未跟踪产物真实存在）复验：
`11 passed` 且 warning 里点名了文件与理由，**非静默通过**。

## 6.2 ⛔⛔ 你的环境纪律（本日刚被踩，硬要求）

1. **⛔ 绝对不许跑 `pip install -e .` / 任何 editable 安装。**
   本日实测：一个席位在自己 worktree 里跑了一次，**共享 venv 的 `.pth` 被改成指向那棵 worktree**
   ⇒ 此后**连主树**的脚本式启动都跨树导入到那棵树 ⇒ orchestrator 的权威全量会失去权威性
   （**新登记 F-31**）。已修复并复验，请勿再触发。
2. **你的 worktree 里会看到 3 条环境假红**，⛔ 不要修、不要当回归：
   `test_gt_from_dxf` / `test_inspect_dxf`（CLI 子进程跨树导入 editable 安装 ⇒ `REPO_ROOT` 指向主树）
   + `test_zone_agent`（`.env` 被 gitignore ⇒ 无 `OPENAI_API_KEY`）。**已登记 F-30。**
3. 跑测优先跑定向用例；⛔ 不要重复 §6 的权威全量。

## 7. 请在裁决书里明确给出

1. 摊 A、摊 B **各自能否签收**（可分开裁）；不能则给**最小闭合口径**。
2. §4.1 阻塞档恒绿：**本轮补齐 还是 下轮补**。
3. §5 两席自陈未验证项里，**哪几条是你认为必须在进验收路径前补掉的**。
4. 你**实际跑了什么**（命令 + 输出），以及**你没验证的部分**。
