# 交叉复审请求 —— 707 复现前置三件 + 14 把新锁 + 三处推翻的旧断言

**收件**：GLM 家族（`glm-5.3`）。**作者 = Claude 侧席位 + orchestrator**，按「谁写谁不批」交你。
⚠️ 你**不是**本批作者（你今天审的是「基座修法批」，那是另一批；你自己写的 `grid_B` /
`test_substrate_sweep_policy.py` 不在本单范围内，那笔另找非 GLM 席位）。

**被审范围 = 两笔提交**：`0ae4b93`（三件修法，worktree 施工）+ `e9e5d95`（补锁 + 三处推翻 + plan）。
入手：`git show --stat 0ae4b93 e9e5d95` · `git diff 16b247b..HEAD -- <文件>`

- 修法：`src/agent/execution/vision_resize.py`（新）· `src/agent/execution/isolation.py` ·
  `src/agent/reading/cv_toolbox/tools.py` · `skills/intake_pipeline/0_reading/{guide,session_kickoff,pen_library,cv_toolbox}.md`
- 锁：`tests/test_f51_single_frame.py` · `tests/test_cross_axis_exit.py` · `tests/fixtures/cross_axis_exit/`
- 三处推翻：`tests/test_cv_toolbox.py` · `tests/test_reading_schema.py` · `tests/test_substrate_sweep_tools.py`
- 执行日志：`AI_agent/logs/reviews/execution/2026-08-17_707_repro_prereq_execution_log.md` +
  `..._707_prereq_locks_execution_log.md`

---

## 0. 「停下上报」分层

- **① 承重前提错 ⇒ 停下上报**（例如：预缩这条路根本行不通、或它打断了判卷链路）。
- **② 外围论据错 ⇒ 记录后继续审完**。
- **⛔ 派工方错误率 29/29**。本单里凡我写的数字、因果、判断都请当**待证伪对象**。
  今天已被证伪的两条示例：我给的验收判据 `-n4` 是**一道不会变红的门**（原始代码 6 轮 0 红）；
  行为清单「两份好 reading 都没有 `scale_origin`」**事实错**（两份都有）。

## 1. 背景与目标

目标（用户 08-17 重申两次）：**在现有基座上复现 07-07 那个识图模式，拿到接近满分就行。** 不是提分、不是重新设计。
本批是开抽前的最后三件前置。**这批过了就开抽**，所以复审的现实意义是：
**如果这三件里有错，下一次抽出来的分数无论好坏都不可信，而且会像 F-49 那样把错误归因到模型身上。**

## 2. ⭐ 请重点攻击这五处（按我最不放心的排序）

### 2.1 ⭐⭐⭐ 缩放档位与实际模型**没有绑定**

`resize` 分标准档（长边 1568 / 视觉 token 1568）与高分档（2576 / 4784）；
`build_isolation_workspace` 新增参数 `vision_resize_tier`，**默认标准档**。

**但读图器用哪个模型是别处配置的**（`run_config.yaml` / `llm.yaml` / spawn 参数）。
⇒ **我的怀疑：这两者之间没有任何一致性约束。** 后果：
- 若有人把读图模型换成 Claude 4.7+（高分档）而 staging 仍按标准档预缩 ⇒ 帧仍然一致（只是白丢分辨率）；
- 但若反过来配成高分档、实际跑标准档模型 ⇒ **API 会再缩一次 ⇒ 帧错位复活，而且没有任何门会红**。
**请核**：档位是从模型 id 推导的，还是自由参数？有没有锁钉住「档位 ≠ 实际模型档位」这种组合？
若确实无约束，这是**把 F-51 重新引入的一条路**，请按 BLOCKER/MAJOR 定级。

### 2.2 ⭐⭐⭐ 跨轴出口的信号**有没有消费者**

新出口 = `axis_calibration_disagreement=true` + `warnings[]` 追加 + `metric_confidence` 降 `"low"`，仍返回 `px_per_m`。
**请核：这三个信号有谁在读？**
- 有任何**确定性门**读 `axis_calibration_disagreement` 或 `metric_confidence` 吗？
- 读图器会看到它吗（侧车里有、且它有理由去看）？
- 判卷侧呢？

**本仓判据**：**一个不与行为绑定的声明 = 带变量名的注释**（同一形状本仓一天内现形三次）。
如果这三个信号**没有任何消费者**，那这个「合法出口」实质等于**悄悄放宽了那道门**
——原来 raise 至少会停下，现在返回一个错的数、没人拦。请据此定级。

### 2.3 F-51 的算法实现与官方规则是否逐格一致

`vision_resize.py` 是照 Anthropic 文档的参考实现重写的。**请逐项核**：
- 官方 A4 自检 `resized_size(1075,1520) == (924,1307)` 是否真在锁里且真跑；
- **短边 `round` 是否半数进偶**（文档明写 live API 在 `.5` 处向偶数取整，`Math.round` 那种进位会算出不同尺寸）；
- 两个上限（长边 / 视觉 token）**都**被检查了吗，还是只按长边缩（文档明确警告「按长边算会让每个坐标明显偏靶」）；
- `pad 到 28 倍数` 这件事我们**不做**（官方说别自己 pad）——实现里有没有误加。

### 2.4 预缩是否真的没打断别的链路

施工席声称 grep 遍 correction / judge / 渲染，**零处**依赖原图尺寸；且仓库原始 case 图未被动。
⚠️ **这是作者自证**。请独立核，特别是：
- MANIFEST 哈希是在缩放**之后**算的吗（否则哈希与盘上字节不符）；
- `merge` / attempt 归档 / `view_manifest` 有没有记着原图尺寸的地方；
- gt 判卷是米制，**但 `px_per_m` 变了 1.549 倍** —— 有没有任何地方缓存或硬编码了旧的 `px_per_m`。

### 2.5 `scale_origin`：确定性门被**故意留着**没动

施工席**未动** `src/validator/checks/reading.py::_plan_scale_origin`，理由是 `exploratory` 档不 block、够本批用，
golden/regression 档的风险结转专项。
**请核这个判断**：① 下一次抽实际会跑哪个 profile（去 `run_policy.json` / `run_config.yaml` 里看，别信我说的）；
② 若那个 profile 下这道门会 block，本批就是**没修完**；③ 文档说「留 `null` 不算自检失败」而门可能仍判 fail
—— **文档与门是否已经打架**？

## 3. 通用要求

- 每条 finding 给**可复现命令或具体反例**，能实跑最好；按 **BLOCKER / MAJOR / MINOR / NIT** 分级。
- 新锁请用 **neuter** 判是否真绑目标（**变红才算接线，代码审查不算**）。
  ⚠️ neuter 请在**临时副本**上做，⛔ 别覆写仓库真实文件（本仓今天刚因这个被判 MAJOR）。
- ⛔ **只审不改**：不要修改代码、不要 commit。
- 产物写到 `AI_agent/logs/reviews/verdict/2026-08-17_707_prereq_review_glm.md`，**边审边写**，⛔ 不要攒到最后。
