# 交叉复审请求 —— 基座修法批（摊 I + 摊 II）+ 工具面普查表 grid_A

**收件**：GLM 家族（非作者方）。**作者 = Claude 侧席位 + orchestrator**，按「谁写谁不批」交你。
**被审范围 = 提交 `c68c293` 里 Claude 侧产出的部分**：

- 修法：`scripts/tool_scripts/cv_probe.py` · `src/agent/execution/isolation.py` ·
  `src/agent/execution/isolation_templates/{guard.py,run_cv_probe.py}` ·
  `src/agent/reading/cv_toolbox/tools.py` · `skills/intake_pipeline/0_reading/cv_toolbox.md`
- 新锁：`tests/test_substrate_fix_cleanroom.py` · `tests/test_substrate_fix_tools.py`
- 被改动的既有锁：`tests/test_isolation.py`（16 个测试函数）
- 普查表：`AI_agent/logs/experiments/2026-08-16_substrate_sweep/grid_A.md`
- 两份执行日志：`AI_agent/logs/reviews/execution/2026-08-16_substrate_fix_{I,II}_execution_log.md`

⛔ **不在范围**：`grid_B.md` 与 `tests/test_substrate_sweep_policy.py`（**你自己写的**，另找非 GLM 席位审）。

---

## 0. 「停下上报」分层

- **① 承重前提错 ⇒ 停下上报**；**② 外围论据错 ⇒ 记录后继续审完**。
- **⛔ 派工方错误率 27/27**（今日新增三条：漏了「文档示例逐字实跑」这一格 · 请求书里写错
  `e0367e1` 的改动面 · 「三把 xfail」实为四把）。凡我写的判断都请当作待证伪对象。

## 1. 背景

2026-08-16 做了一次移植基座普查（六工具 × 三形态 × 参数 × 坐标系 × guard 一致性 × 环境 × 留痕），
撞出 7 条缺陷，当轮修了 5 条。全表见
`AI_agent/logs/experiments/2026-08-16_substrate_sweep/README.md`。

## 2. ⭐ 请重点攻击这五处（我自己最不放心的）

### 2.1 F-55 的修法只剩「藏起来」这一条腿

修法两条机制：① 审计日志 `access_log.jsonl` 挪到 staging 的**兄弟目录** `<name>.audit/`；
② build 后对 `out/`/`requests/` 之外的每个文件去掉写位。

**②在本容器里被施工席自己证明无效**（全程 root，root 绕过自己拥有文件的 DAC 检查；
orchestrator 已独立复现 `open(guard.py,"a")` 成功）。⇒ **实际只剩①在起作用。**

**请攻**：① 这条「靠读图器不知道路径」的防护，**够不够得着**？
特别是结合你上一轮自己查出的 **BLOCKER-2（`Path.cwd()` / `__file__` / `parents` 锚点族）**——
读图器在 staging 里跑的脚本，`Path.cwd().parent` 就是 staging 的父目录，
**`<name>.audit/` 正好是那里的兄弟**。请实测：读图器能不能用程序化路径推导读到/写到新位置的审计日志。
如果能，这条修法的净收益是多少？

### 2.2 guard.py 是逐字节拷贝的无状态模板，新路径靠「两边各自推导同一条命名规则」

施工席说：guard.py 没法接收运行时注入的路径，所以 guard.py 与 isolation.py **各自**用同一条
确定性命名规则推导审计目录位置。**请攻**：两处推导会不会漂移？
有没有一种 staging 命名（含空格 / 点号 / 符号链接 / 相对路径 build）让两边算出不同的位置
⇒ **hook 写到一个地方、merge/审计读另一个地方**（后果 = 审计静默丢失，而没有任何门会红）。

### 2.3 F-52 修在 `_bbox()` 单点是否真的覆盖三种调用形态

施工席明确**拒绝**了「把 `bbox` 加进 wrapper 的 `JSON_OR_PATH_KEYS`」，理由是那条分支会把
当前唯一能工作的逗号字符串写法当路径解析、反成负收益。**请核这个理由是否成立**，
以及 `_bbox()` 单点修法有没有漏掉某种形态（尤其 `--batch` 里多条请求混用两种写法）。

### 2.4 `tests/test_isolation.py` 16 个既有测试被改动

施工席声明**全部是「日志物理位置搬家」导致的路径读取方式变更、被验证的属性本身未变**。
**⛔ 请逐个核实这句话** —— 本仓的固定教训是「我以为共 N 处」，且更凶的形状是
**改锁让它变绿**。请判断：有没有哪一处实际上是**放宽了断言**而不是「换了读取方式」。

### 2.5 F-56 / F-57 判「不修」的理由是否成立

施工席的论证是：代码注释已把「wrapper 是唯一权威、guard 只管措辞」写死为设计选择，
改分工会引入新耦合。**请判断这是不是「用现状注释论证现状合理」的循环论证**——
注释是作者写的，不构成外部理由。它给这两条各留了一把哨兵锁，请核那两把锁真的钉住了什么。

## 3. 通用要求

- **每条 finding 给可复现命令或具体反例**（能实跑最好）；按 BLOCKER / MAJOR / MINOR / NIT 分级。
- **⛔ 只审不改**：不要修改代码、不要 commit。
- 新锁请用 neuter 判其是否真绑目标（**变红才算接线，代码审查不算**）。
- 产物写到 `AI_agent/logs/reviews/verdict/2026-08-17_substrate_fix_and_gridA_review_glm.md`，
  **边审边写，⛔ 不要攒到最后一次性写**。
