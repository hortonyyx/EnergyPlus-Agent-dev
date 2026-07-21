# GLM 家族接入 + 能力回溯测（2026-07-21）

> ⚠️ **本文含考题答案**，放在主仓库；考场 `/workspaces/glm_exam` 是独立目录 + 独立 git 仓库，
> 被考模型物理访问不到本文件。若要重考，**不得**把本目录拷进考场。

## 1. 背景与目的

用户新增 GLM（智谱）订阅，项目自此有四个模型家族：Claude / GPT / GLM / DeepSeek。
本轮目标：① 把 GLM 接进来；② 用一道**有标准答案的回溯题**定它的档位。

## 2. 外部能力盘面（2026-07 联网核实）

同一榜（SWE-bench Pro）才可比：

| 模型 | SWE-bench Pro | 备注 |
|---|---|---|
| Claude Fable 5 | 80% | 断层第一 |
| Claude Opus 4.8 | ~69% | |
| GPT-5.6 Sol | 64.6% | 2026-07-09 发布，`sol/terra/luna` = 5.6 三档 |
| **GLM-5.2** | **62.1%** | 开源第一，离 Sol 仅 2.5 分 |

- **GLM-5.2 无图像输入**（纯文本，1M 上下文，128K 输出，MIT 开源）。
- 视觉走独立分支：**GLM-5V-Turbo**（200K，2026-04，原生多模态 coding 基座）/ **GLM-4.6V**（128K，¥1/M 输入，原生多模态 tool calling）。
- DeepSeek-V4-Pro 自 2026-04 起原生多模态、1M 上下文；管线内在役，**本轮不动**（换模型代价 = 重录 baseline）。

## 3. 接入（已落地）

| 用途 | 协议 | 端点 | 计费 | 状态 |
|---|---|---|---|---|
| 开发席位（Claude Code） | Anthropic | `https://open.bigmodel.cn/api/anthropic` | 订阅额度 | ✅ 实测通 |
| 管线内 / 实验 | OpenAI | `https://open.bigmodel.cn/api/coding/paas/v4` | 订阅额度 | ✅ 实测通 |
| 管线内 / 实验 | OpenAI | `https://open.bigmodel.cn/api/paas/v4` | **账户余额** | ✅ 实测通（不吃订阅额度） |

- 凭据在 `.env`（gitignored）：`GLM_API_KEY` / `GLM_BASE_URL` / `GLM_ANTHROPIC_BASE_URL`。
- 席位启动器 [`scripts/glm_code.sh`](../../../../scripts/glm_code.sh)：凭据**只注入子进程**。
  ⚠️ 绝不可把 `ANTHROPIC_BASE_URL` 设为全局 —— 会静默劫持主控 Claude Code 会话。
- 管线内接入**零代码改动**：`llm.py` 走 `init_chat_model` + OpenAI 协议，加一个 `llm.yaml` section 即可。

## 4. 考题（答案，勿泄）

**来源**：07-20 C2 体检修复批。Fable r1 REWORK 新抓的 **M2**。

**缺陷**：`_grade_typed_attempt_artifacts`（`scripts/tool_scripts/run_stage.py:1345` 附近）缺少
`stage == "1_correction" and accepted_record is None` 的静默早退 →
`_render_all_typed_attempt_grades` 遍历**所有** attempt 时，非 accepted 的 v3 correction attempt
撞 scorer 六件套/capability 门 → `ScoreContractError: score_unsupported_combination`（`score_service.py:131`）
→ run_stage **全链无捕获** → flow 崩。sm25-L 照 SOP 跑必踩（首抽 block 重抽 / enrichment 后 base 变非 accepted）。

**难度基准**：sol（GPT 侧最高档）施工时漏；主控 Opus 预扫 diff 漏；**只有 Fable 5 靠活体探针抓到**。
单元测试全绿，靠跑测试抓不到 —— 必须读懂三层调用链或主动写探针跑真实路径。

**同时摘除的另两条锁**（次要采分点）：
- M1 `test_real_draw_reading_archive_is_accepted_by_correction_guard`（缺 happy-path 正例锁）
- m1 `test_cmd_run_config_capability_profile_overrides_only_when_present`（cmd_run 接线无锁）

## 5. 考场构造

`/workspaces/glm_exam`，**独立 git 仓库**（非 worktree），单条 `baseline` 提交 = 施工前状态，
工作区未提交改动 = 待审施工产物（9 改 + 1 新增），已摘除上述 3 处修复。

**验收**：`PYTHONPATH=/workspaces/glm_exam pytest tests/ -q` → **1452 passed + 9 xfailed**
（= 主线 1456 − 4 个被摘 test items）；把摘掉的锁放回去立刻红在 `ScoreContractError` = 答案在位。

### 泄题渠道（五条，全堵）

| 渠道 | 处理 |
|---|---|
| git 历史 | 全新仓库，只有一条 baseline，看不到写着答案的 commit message |
| **git index** | index = baseline 树；泄题文档从未进过 index |
| 工作区文档 | `AI_agent/{CLAUDE,plan,decision_log}.md` + **两处** `logs/reviews/`（`AI_agent/` 下**和仓库根下**）全铲 |
| 会话记忆 | `~/.claude/projects/-workspaces-glm-exam/` 清除，杜绝 resume 读回；memory 按项目路径天然隔离 |
| MCP | `.mcp.json` 禁用（否则被考模型能反过来调 codex 问 GPT） |
| 需求文件 | `REVIEW_DISPATCH.md` 中审阅者身份匿名化（"Fable" → "交叉审阅者"），信息量不变 |

### ⚠️ 构造踩过的两个坑（重考必读）

1. **`git apply --index` 把产物同时写进 index** → 后续 `rm` 只清工作区，`git show :<path>` 仍能读出
   施工简报（含 M1/M2/m1 答案）。被考模型确实读到了，且据此把工作树恢复 → 考场与答案两头俱毁。
   **教训**：隔离实验必须把 **index 和 HEAD 一并当作泄题面**核查，不能只看工作区 `ls`/`grep`。
2. **`git add -A` + `commit --amend`**（为清根目录 `logs/reviews`）把已铺上的施工产物一起提交进
   baseline → `git diff` 变空、考场结构失效。**教训**：baseline 定版后，只用**显式路径** `git add -- <paths>`。

## 6. 定级标准（2026-07-21 用户拍板）

**上限硬约束：GLM 即使满分也不升 Fable 档。** Fable 档（规划出稿 + 最高档对抗审）是质量生命线，
不靠一次考试授予。GLM 的定位是**第三备用 + 施工档**。

| 表现 | 定级 | 用法 |
|---|---|---|
| 抓到 M2 | 次高档（sol/Opus）**下位替代**，第三备用位 | 应急顶替 + 多视角参考审 |
| 抓到 M1/m1 或其它真 finding、漏 M2 | **施工档**（主预期） | 派施工批次；复核当第三视角 |
| 只报表面问题 / 误报 | 机械批量档 | 词汇批、格式批 |

## 7. 运维发现（影响定位，重要）

- **一场深度对抗审 ≈ 烧穿一个 5 小时订阅窗口**：首场（作废那次）跑 30+ 分钟、290+ 轮工具调用即触发
  `429 [1308] 已达到 5 小时的使用上限`。⇒ GLM 坐"次高档备用审"实用性打折（应急顶一次可以，
  连续多轮返工审顶不住）；**派施工批次（单次任务更短）性价比更高**。
- **高峰期倍率**：每日 14:00–18:00 (UTC+8) 额度按 **3x** 扣，非高峰 2x（促销期至 2026-09 降 1x）。
  ⇒ 长批次务必避开下午。
- 订阅额度耗尽时，**按量端点 `/api/paas/v4` 仍可用**（走账户余额），管线内实验不受订阅 429 影响。
- Coding Plan 条款仍写「限官方编码工具内交互式使用」；用户 2026-07-21 确认当前用法（手工逐次触发、
  低频低量）可接受，不做批量自动化调用。

## 8. GLM 视觉分支冒烟（2026-07-21，走按量端点，不吃订阅额度）

**素材**：`sm24_anchor/case_data/1f_view.png`（790×1111，**仓库无 sm24 gt** → 零污染顾虑）。
**真相**（主控读图核对）：外轮廓 **矩形 10000×20000**（L 形在中间走廊、不在外轮廓）；6–7 个房间 + 走廊。

| 检查项 | glm-4.6v | glm-5v-turbo |
|---|---|---|
| 图像输入 | ✅ | ✅ |
| 外轮廓形状 | ✅ 矩形 | ✅ 矩形 |
| 总尺寸 | ✅ 10000×20000 | ✅ 10000×20000 |
| 房间数 | 6 | 7（含门厅） |
| **tool calling（带图）** | ✅ 会调 | ✅ 会调 |
| **坐标质量** | ❌ `(0,10000)→(10000,10000)` = **把图纸毫米标注当像素坐标**（图仅 790×1111），坐标系混淆 | ⚠️ `(321,138)→(777,138)` 真像素系、水平线，但建筑主体实际在 x≈245–610，**右端偏到尺寸线外**：量级对、精度不足 |

**结论**：
1. **CV 工具箱前提成立** —— 两者带图时都能正确发起 function call，这是"量而非看"迁移到 GLM 的必要条件。
2. **reading 实验臂唯一候选 = GLM-5V-Turbo**；**glm-4.6v 出局**（坐标系混淆，属项目最忌讳的失效模式）。
3. 冒烟正面印证 [[reading-cv-toolkit-methodology]]：VLM 自"看"坐标不可靠（5V-Turbo 也偏），
   价值在于**能正确发起工具调用**、精度交由确定性工具补。
4. 两模型 thinking 默认开且吃 token 凶（纯读图 reasoning_tokens ≈ 1000–1300）；
   `max_tokens` 给小会导致**只思考、不输出**（800 token 全烧在 reasoning、content 为空）。
   接管线时 `max_tokens` 需给足或显式关 thinking。

⇒ 待正式实验：GLM-5V-Turbo + 项目 CV 工具箱 + clean-room 隔离，对 sm21 跑单变量 A/B
（对标 Haiku+工具箱 = Sonnet5 满分那条基线）。**须走 `spawn_isolated_reader`，不得手工 spawn。**

## 9. 考试结果（2026-07-21 19:58–20:48 CST，50 分钟，382 轮工具调用）

报告原件：`/workspaces/glm_exam/GLM_REVIEW.md`（14.8KB）。**总裁决 = APPROVE（错，正确答案是 REWORK）**。

### 对答案

| 标准答案（Fable 当初抓的） | GLM | 说明 |
|---|---|---|
| **M2 判卷循环必崩** | ❌ **漏** | 关键失手：放行了会让 sm25-L 跑崩的缺陷 |
| M1 F2-1 缺正例锁 | ✅ 命中（列 MINOR-1） | **分析比 Fable 更深**：指出根因是守卫重建字节隐含依赖 `_draw_reading` 同序 `sorted(glob)`，多视图 run 会被静默 false-reject；并实跑 5 场景活体探针（单视图/多视图/篡改/standalone/键序变体）可直接转正为测试 |
| m1 cmd_run 接线无锁 | ✅ 命中（列 NIT-4） | |

**GLM 独立发现（Fable 未提，主控已逐条核实）**：
- **NIT-3 属实** — `run_stage.py:1845`（cmd_judge）仍纯 CLI `getattr`，未跟上 F1-2 的 run_config 覆盖（1748 cmd_run / 1931 cmd_flow 都读了）。**两场考试独立发现同一处**（首场作废轮亦命中），非偶然。
- **NIT-1 属实** — F1-1 再入回归测试用 `SimpleNamespace` mock，未走真实 `load_verified_accepted_correction → resolve → finalize` 链，未独立复现派工单所述下游 `ValueError`。
- **NIT-2** — F4-1 golden/regression 缺 bindings 时是裸 `RuntimeError` 冒泡而非 graded `ERROR` verdict；属 fail-closed 合规，语义可优化。

**误报 0 条**（主控核实的三条全属实）。MINOR-1 / NIT-4 对应的洞**主线已由 sol 返工 r1 补上**（M1 正例锁跑真实 sm21 多视图产物），不再登记。

### 操作纪律：满分

21 次 neuter 探针全部**手动**改回、全程未用 `git checkout/stash/restore`、自做指纹比对自证零残留。主控复验：`git diff` 逐字节回到 405 插入/21 删除、考题未破坏、全量仍 1452 绿。

### 能力画像（本次考试的核心产出）

| 维度 | 表现 |
|---|---|
| **验证性审阅**（给定 finding 清单，验锁真绑 / 防 false-lock） | **Fable 级** — 7 条锁 7 条全做 neuter，每条都验「只红对应测试、零连带」，零漏判零误报 |
| **探索性审阅**（无线索处主动构造真实场景找未知缺陷） | **不及格** — 报告 §F4-1 完整写出了 `_render_all_typed_attempt_grades → _grade_typed_attempt_artifacts` 调用链，**它看见了那个循环**，却未追问「遍历所有 attempt 时非 accepted 的会怎样」。其活体探针**全部**用于验证已知 finding，无一用于自由探索 |

**根因**：Fable 抓 M2 靠的是 P7x —— 真跑一个两 attempt 的 run 让循环自己崩；GLM 没做这类"无靶心探针"。

## 10. 定级（2026-07-21 用户拍板）

**GLM-5.2 主力定位 = 执行档（施工）；可坐次高档备用位，但主要做复核类工作，一般不单独出稿。**
依据：验证性审阅达 Fable 级 ⇒ 适合接「返工轮复核」（验证施工者补的锁是否真绑目标门，如 Fable r2 那类任务），
可为最高档腾出额度专攻首轮对抗审；探索性审阅不及格 ⇒ **不得**替代首轮对抗审与规划出稿。

## 11. 状态

- 首场考试 **作废**（考场泄题，见 §5 坑 1）。
- 第二场 **未开跑**即撞 429。考场已修正并复验通过，`_run_exam.sh` 挂在 19:58 CST（非高峰）自动开跑，
  报告落 `/workspaces/glm_exam/GLM_REVIEW.md`，运行日志 `_exam_runner.log` / `_glm_session.log`。
- **主仓库零影响已实测**：HEAD `7d5a9c1` 未动、工作区仅 `scripts/glm_code.sh` 一个新文件、
  全量 **1456 passed + 9 xfailed**（与里程碑一致）。
