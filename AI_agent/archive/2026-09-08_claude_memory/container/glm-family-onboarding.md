---
name: glm-family-onboarding
description: 2026-07-21 GLM 接入⇒四模型家族；GLM=执行档主力+次高档备用（只做复核不出稿）；08-16 席位默认升 glm-5.3 + DeepSeek 加席位启动器（按量扣余额）
metadata: 
  node_type: memory
  type: project
  originSessionId: 99ae6db8-8b89-4013-acf7-44566c1298df
  modified: 2026-08-16T08:11:39.627Z
---

**2026-07-21 用户拍板**：GLM 订阅接入 ⇒ 项目**四模型家族** = Claude / GPT / **GLM** / DeepSeek。

## ⭐ 2026-08-16 家族全量核对（用户拍板两条改动，实调 API 得证）
- **GLM 席位默认 5.2 → `glm-5.3`**（`scripts/glm_code.sh`，行为验证过：headless 实跑 `modelUsage: glm-5.3`）。
  5.3 = 08-13 发布、同基座纯后训练，官方称编程较 5.2 **+50%**；**thinking 强制常开**
  （`thinking:{disabled}` 接口收下但静默忽略、照计 reasoning_tokens），`reasoning_effort` 默认 `max`。
  **⚠️ 档位定级不动**：07-21 那份「验证性审阅=Fable 级 / 探索性=不及格」画像是 **5.2 的**，5.3 我方零实测。
- **DeepSeek 新增席位启动器 `scripts/deepseek_code.sh`**（Anthropic 兼容端点 `https://api.deepseek.com/anthropic` 实测可用）
  ⇒ 改动了下面「DeepSeek 退出日常开发选项」那条。**⛔ 但它是按量扣账户余额、与管线共用同一个余额**
  （余额见 `/user/balance`，核对当天 ¥50.02）⇒ **席位烧穿余额会连带打断 e2e**，长批次前必查。
- **DeepSeek V4 转正 = 零改动**：`/models` 只有 `deepseek-v4-pro`/`deepseek-v4-flash`，**旧 key 直接落 GA**、
  preview 名已被接口拒绝。**⛔ 陷阱：`deepseek-chat`/`deepseek-reasoner` 现静默解析到 v4-flash（不是 pro）。**
- **⛔ 席位里的 `total_cost_usd` 是假数字**（Claude Code 拿 Anthropic 价目表套 GLM/DeepSeek，一句 "reply OK" 报 $0.14）；
  `contextWindow` 也一律按 200K 报（GLM-5.3 实际 1M）。真实消耗只看余额接口 / 订阅窗口。
- 视觉侧不变：`glm-5v-turbo` 仍可用（**不在 `/models` 列表里但能调**），**无 `glm-5.3v`/`glm-5v`**。
- 家族版图权威表 = `AI_agent/guides/codex_execution_protocol.md` §1（08-16 已重写为四家族）。

## 定级（用户拍板，硬口径）
- **GLM 主力 = 执行档（施工）**；**可坐次高档备用位，但主要做复核类工作、一般不单独出稿**。
  适合接「返工轮复核」（验证施工者补的锁是否真绑目标门），为最高档腾额度专攻首轮对抗审；**不得**替代首轮对抗审与规划出稿。
- **派工表须把 GLM 算进候选，仍用户拍板再放**（排工拍板制不变，见 [[codex-execution-protocol]]）。
- ~~**DeepSeek 非订阅制（按量）⇒ 不作日常开发选项**~~ **⇒ 2026-08-16 用户改口：加席位启动器**（见上节）；
  按量性质与余额风险不变，**管线内角色不变**（correction/mep/9 subagent 有 baseline 沉淀不轻动）。
- **在册主力仅两个**：`glm-5.3`（文本，**08-16 起，替代 5.2**）+ `glm-5v-turbo`（多模态 200K）。
  其余（5.2/5-turbo/4.7/4.5-air/4.6v）**不专门指定即不用**。

## 能力画像（回溯测实证，非外部榜单）
考题 = 07-20 批 Fable 抓的判卷循环必崩缺陷（sol 漏 + 主控漏 + 单测全绿抓不到）。结果 **APPROVE（错，应 REWORK）**：
- **验证性审阅 = Fable 级**：7 条锁全做 neuter、每条验「只红对应测试零连带」、零漏判**零误报**、操作纪律满分（21 次探针手动还原零残留）。
- **探索性审阅 = 不及格**：它写出了那条判卷调用链、**看见了循环却没追问「遍历非 accepted attempt 会怎样」**；活体探针全部用于验证已知 finding，无一自由探索。
- 命中 M1/m1（M1 分析比 Fable 更深）+ 独立发现 3 条 Fable 未提的真 finding（已登记 plan.md）。

## 接入事实
- 三端点：Anthropic 兼容 `/api/anthropic`（订阅额度）· OpenAI 兼容 `/api/coding/paas/v4`（订阅额度）· **`/api/paas/v4`（账户余额，订阅 429 时仍可用）**。
- 席位启动器 `scripts/glm_code.sh`；**凭据只可注入子进程——全局 `ANTHROPIC_BASE_URL` 会静默劫持主控 Claude Code 会话**。
- 管线内接入**零代码改动**（`llm.py` 走 OpenAI 协议，加 `llm.yaml` section）。
- **识图实验臂唯一候选 = `glm-5v-turbo`**；`glm-4.6v` 把图纸毫米标注当像素坐标**出局**。两者带图 tool calling 均可用 ⇒ CV 工具箱前提成立（印证 [[reading-cv-toolkit-methodology]]）。V 系 thinking 默认开且吃 token 凶，`max_tokens` 给小会**只思考不输出**。
- **额度**：一场深度对抗审 ≈ 烧穿一个 5h 订阅窗口；高峰 14:00–18:00 (UTC+8) **3x** 扣 ⇒ 长批次避开下午。
  **⛔⛔ 2026-08-03 实测坐实（orchestrator 排期失误，代价一个窗口）：15:38 派出的施工席
  只跑了 35 分钟就烧穿整个 5h 窗口。** 非高峰 2x ⇒ 同窗口可干量差 1.5 倍以上。
  **⇒ 长批次一律排 18:00 之后或上午；派工前先 `TZ=Asia/Shanghai date` 看钟。**
  额度耗尽的报错形态 = `429 · [1308][已达到 5 小时的使用上限。您的限额将在 <时间> 重置]`，
  **该时间是北京时间**，可直接据此排下一次定时启动。

## 副产：隔离考场构造两坑（同类实验必读）
① `git apply --index` 使产物同时进 index → 只清工作区无用，被考模型 `git show :<path>` 直接读出答案（**index/HEAD 同属泄题面**，不能只 `ls`/`grep` 工作区）；
② baseline 定版后用 `git add -A` + `commit --amend` 会把已铺产物一起提交、`git diff` 变空 ⇒ **只用显式路径 `git add -- <paths>`**。
首场考试因①作废重建。另需清 `~/.claude/projects/-<考场路径>/` 旧会话轨迹防 resume 泄题、禁用 `.mcp.json` 防被考模型反调其它家族。

详档：`AI_agent/logs/experiments/2026-07-21_glm_capability_exam/README.md`（含考题答案，勿拷进考场）· CLAUDE §5#8/#10 · decision_log §A 顶条。
