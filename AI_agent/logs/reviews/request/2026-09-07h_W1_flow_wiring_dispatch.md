# 派工单 · W-1：**让一个 case 能完整跑通端到端（零手搓）**

> **施工 = GLM**（`scripts/glm_code.sh`，默认 `glm-5.3`）· **复核 = Claude 家族 orchestrator**（用户 2026-09-07 指定）
> **档位 = 工程档**（碰 `src/agent/pipeline` 内核 + `scripts/`）⇒ gate① + **全量绿**是硬验收。

## 〇 与安全攻防无关的声明

本单是**建筑 CAD 图纸 → 能耗模型**管线的**命令行接线**工作。文中「锁 / 门 / 负样本 / 攻击」
是本项目对**单元测试判据**的固定叫法，⛔ 与网络安全、攻防、漏洞利用无关。

---

## 〇之二 ⭐⭐⭐ 本单的验收就是一句话（用户 2026-09-07 原话）

> **「修到可以完整跑端到端就行（整个架构通，别需要现手搓），别的风险欠债跑完一次再修。」**

⇒ **验收 = 拿一个 case，从 0_reading 一路走到出分，全程走【标准入口】，⛔ 不需要现场手写任何脚本。**
⛔ 本单**不是**「把 `flow` 接到新腿」这一处接线 —— 那只是**我已经找到的其中一个断点**。
**这条路上还有几处要手搓，是你要去找的。**

⚠️⚠️ **派工方的范围曾写窄过**：本单第一版只写了 correction 那一处接线，
被用户当场纠正为「整个架构通」。⇒ ⭐ **你要扫的是整条路，⛔ 不是我列的那几条。**

## 一 在哪、审什么

- **工作目录 `/tmp/w1_flow_glm`**（分支 `wt/09.07h_w1_flow`，从 `08.23_AsDrawnReading` 切）。
  ⛔ 不要动主树 `/workspaces/EnergyPlus-Agent-dev`。
- **必读（⛔ 主树绝对路径 —— 本单写在切树之后，按构造不在你树里）**：
  - 本单：`/workspaces/EnergyPlus-Agent-dev/AI_agent/logs/reviews/request/2026-09-07h_W1_flow_wiring_dispatch.md`
  - **通查对账档**（本单题面的来源）：`/workspaces/EnergyPlus-Agent-dev/AI_agent/logs/experiments/2026-09-07f_plan_reality_audit/README.md`
  - 09-02 那次真模型跑通的实验档：`/workspaces/EnergyPlus-Agent-dev/AI_agent/logs/experiments/2026-09-02b_m7_evidence_chain_run/README.md`

### 开工先自检

```sh
cd /tmp/w1_flow_glm
git log --oneline -1
python -c "import src.agent.pipeline as m; print(m.__file__)"   # 必须落在 /tmp/w1_flow_glm
```

⛔ 绝不许 `pip install -e .` 或任何写 `site-packages` 的命令。⛔ 跑测一律 `-n 6`。

---

## 二 ⭐⭐⭐ 派工方（主控）量过什么、⛔ 没量什么

**⛔ 别把「主控说的」当已核。右栏是你要盯的。**

| ✅ 主控 2026-09-07 实测（可证伪，⛔ 不必重做） | 证据 |
|---|---|
| **一体改本体已实现且真跑通过** | 09-02 用 **deepseek-v4-pro 真模型**端到端跑完 `run_correction_evidence_chain`，`response_source=model:correction_decision`（⛔ 非 fixed_responses），185.8 s / 2 轮 / success |
| **三个入口只有一个走新腿** | `pipeline.py:1692 run_multifloor_correction → evidence_chain=True` ✅ · `pipeline.py:2344 run_pipeline` ⛔ 不传 · `run_stage.py:457 run_correction(...)` ⛔ 不传 |
| **新腿生产零调用者** | `grep run_multifloor_correction` 唯一调用者 = `tests/test_b2_multifloor_assembly.py` |
| **`flow` 零路由感知** | `classify_vector_json` 在 `scripts/tool_scripts/run_stage.py` **零命中** |
| 适配器按**分类器判定**分派 | `pipeline.py:1090-1135`，⛔ 不按文件名 |

| ⛔ 主控**没有**量的（= 你的主战场） |
|---|
| ① **`flow` 今天到底怎么确定层序**（新腿要求 `plan_runs[i]` 对应自下而上第 i 级）—— 我没查 |
| ② `flow` 现在跑的 case 里，reading 产物**是新格式还是 legacy**、两种混着的有没有 |
| ③ 接上新腿后**旧 case 会不会行为改变** —— 这是本单最大的风险，我没量 |
| ④ `CorrectionEvidenceBundleArtifactV1` 在 `flow` 的上下文里**从哪来**（今天 flow 不产它） |

---

## 三 任务

### T1 · ⭐⭐⭐ 端到端【手搓点普查】，⛔ 不要先动手

**试着用标准入口把一个 case 从头走到尾**（`case_tests/` 里已有数据，建议 sm25），
**每撞到一处「必须现场手写脚本/手拷文件/手填参数才能往下走」的地方就记一条**。

产出一张**手搓点清单**（写进交件），每条给：**在哪一段 · 撞到什么 · 今天只能怎么绕 · 最小修法**。

⭐ **派工方已经找到的三条（起点，⛔ 不是全集）**：

| # | 段 | 现状（主控实测） |
|---|---|---|
| A | **0_reading** | `flow` 的 0_reading 是 **MANUAL**（`run_stage.py:340` 逐字：「validate the already-produced view JSONs (no LLM)」）⇒ 产物要先在外面产好。⭐ **标准产出器是有的**：`scripts/tool_scripts/reading_toolbox.py build <cfg> <out>` 会落盘。⚠️ **但缺「给一个 case 产齐所有视图」的编排**，且那个 `cfg` 从哪来我没查。<br>⚠️ 09-02 那次用的产物是**从实验目录逐字节拷贝**的（`logs/experiments/2026-08-23_as_drawn_reading_prototype/out/`，该档明写「**全程探索档：未改 `src/`**」）—— **那就是一次手搓。** |
| B | **1_correction** | `flow` 不走新腿：`run_stage.py:457 run_correction(...)` **不传 `evidence_chain`** ⇒ 走 legacy。新腿 `run_multifloor_correction` **生产零调用者**（唯一调用者是测试）。 |
| C | **下游** | `CorrectedGeometryV3` **确实被 `output_coordinates.py` 消费**（`:311` `model_validate_json`）⇒ 这一段**可能是通的**，⚠️ 但**我没有真跑过**，你要验。 |

⇒ **⛔ 别停在这三条。** gt 侧（`gt_from_dxf` → `gt_review_build` → `gt_review_sign` → `gt_promote`）、
判分与出报告（`flow --record`）、`4_mep`、`5_intakeoutput` 都要走一遍，**撞到就记**。

⭐ 顺带记下**今天的行为基线**（legacy 路径跑现有 case 的读数），T3 之后要对账。

⚠️ `run_multifloor_correction` 要的两样东西，请在清单里单列它们在 `flow` 上下文的来源：
`elevation_evidence: CorrectionEvidenceBundleArtifactV1`（**带冻结字节的封装载体**）·
`plan_runs: Sequence[MultiFloorPlanRun]`（**自下而上排序**，`plan_runs[i]` → 第 i 级）。

### T2 · ⭐⭐⭐ 出方案，交主控拍板后再施工

**⛔ 不要直接改代码。** 针对 T1 清单里的**每一条手搓点**给最小修法，并至少覆盖：

- **怎么选腿**：⭐ 本仓库的既有口径是「**路由由分类器判定，⛔ 永不按文件名**」
  （`pipeline.py:1049` 逐字写着）。你的方案要**沿用同一口径**，⛔ 不要引入 `--new-leg` 这类开关，
  除非你能论证为什么这里必须例外。
- **⚠️⚠️ 层序从哪来（本单最硬的一处）**：新腿要求 `plan_runs` **自下而上**。
  ⛔ **从文件名解析 `1f`/`2f` 与「不按文件名路由」直接冲突** ——
  ⭐ 请找出**产物自己声明层序**的路径（若不存在，**这就是一个真缺口，停下上报**）。
- **旧腿怎么办**：legacy 产物必须**照旧走旧腿、行为逐位不变**。
- **失败形态**：混合产物、层数与立面推出的级数不符（`FLOOR_PLAN_COUNT_MISMATCH`）、
  缺立面证据包 —— 各自**响亮失败**，⛔ 不许静默回退到旧腿
  （⛔ 静默回退 = 新腿永远不会被发现没通电）。

### T3 · 施工（主控拍板后）

按拍板的方案接线。**⭐ 每完成一段就 commit。**

### ⛔ 本单【不做】的事（用户 2026-09-07 定的次序）

用户口径：**「修到完整做一个 case（gt+pipeline），然后跑一次，再修这些别的欠债。」**

⇒ ⛔ **本单只做接线，做到「`flow` 能把一个 case 走完新腿」为止。**
以下**明确不做**，⛔ 不许顺手带上：
- **W-2**（经 `_grade_typed_attempt_artifacts` 真入口的端到端判分锁）—— 排在 case 跑通之后；
- **F-137 / F-131 / F-134 / G-g / F-149** 等欠债 —— 同上；
- 任何「顺便把这块也整理一下」的重构。

⭐ 判别法则（本项目 §0.1）：**「不做这件事，这个 case 能不能跑完、结果能不能读？」**
能 ⇒ 登记进 `plan.md` 不做。

---

## 四 硬验收

1. ⭐⭐⭐ **一条命令序列，从 0_reading 走到出分，全程标准入口、零现场手写脚本** ——
   把那串命令**逐字**写进交件，任何人照抄能重跑。**这是本单唯一的总验收。**
2. ⭐⭐⭐ **旧 case 行为逐位不变** —— 用 T1 记下的基线对账，⛔ 不许「差不多」。
3. **新腿真的通电**：给出一条**经 `flow` CLI**（⛔ 不是手搭调用）跑到 `run_correction_evidence_chain` 的证据。
4. **全量 0 failed**（`-n 6`），跑前跑后各核一次 `python -c "import src.agent.pipeline as m; print(m.__file__)"`。
   ⭐ **主控参照基线 = `4009 passed / 0 failed / 2 skipped / 13 xfailed`**（主树 `60cbda94`）。
5. 静默回退**不存在**：构造一个「该走新腿但缺立面证据」的输入，确认它**响亮失败**、⛔ 不是悄悄走旧腿。

---

## 五 硬纪律

1. ⭐⭐⭐ **分段提交**：每完成一个 T 就 commit（本项目连续两个席位撞额度，这条是唯一让活不丢的）。
2. ⛔ **禁 `git add -A`**；只 add 明确路径，commit 前必看 `git diff --cached --numstat`。
3. ⛔ 禁 force push / `reset --hard` / 跳 hook / 动 `git config`。
4. ⭐ **改→量→写不许换序**：写进交件的每个数字必须是你**跑出来**的。
5. ⛔ 不要在 `.py` 的字符串常量（docstring 也算）里写带仓库根前缀的生产文件路径。

---

## 六 停下上报（分层）

**本项目 70/70 的「停下上报」全是派工方的题错，记功不记过。**

**A 类 · 承重前提错 ⇒ 立刻停**：
1. 自检 `__file__` 落点不对。
2. **产物里找不到「层序」的自声明来源**（§三 T2）—— 那说明本单缺一个前置。
3. **你判定「零手搓端到端」在本单范围内结构上做不到**（例如缺的东西远超接线量级）—— ⭐ 这正是要停下报的，⛔ 别硬做。
4. 你发现**接新腿必然改变旧 case 行为**（即验收 2 结构上做不到）。
5. 主控 §二 左栏那五条读数里，**有任何一条你复现不出**。
6. 你认为本单**题面**就不对。

**B 类 · 外围错 ⇒ 记录并继续**：行号/数字对不上 · 你对某个细节的判断与我不同。

⚠️ **一次跑出来的红不是证据** —— 同树重跑至少 2 次。

---

## 七 交件

写到 `/workspaces/EnergyPlus-Agent-dev/AI_agent/logs/reviews/execution/2026-09-07h_W1_flow_wiring_execution.md`：

1. **T1 手搓点清单**（每条：在哪一段 · 撞到什么 · 今天只能怎么绕 · 最小修法）+ 今天的行为基线。
2. **T2 方案** —— ⭐ **写完就停下等主控拍板**，⛔ 不要直接进 T3。
3. T3 的改动 + 每条验收的原始命令与输出。
4. **最薄弱的一处**：你自己最没把握的判断是什么、它错了会怎样。
