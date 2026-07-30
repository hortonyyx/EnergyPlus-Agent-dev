# sm24 端到端跑测 — 过程发现（待并入 report/REPORT.md 的 AGENT 区 + 四桶建议）

## F-1 · prescan CLI 的 `--out-dir` 语义与手册口径打架（脚手架桶 · MINOR）
- 手册 [new_case_guide §2.1] 写落点 = `<RUN>/0_reading/cv_evidence/<stem>/prescan/`，
  读起来像是 `--out-dir` 就该传这个完整路径。
- 实际 `sidecar.py:24` = `Path(out_dir)/"cv_evidence"/<stem>`，工具**自己**追加两级 + label 一级。
- 照手册字面传 ⇒ 产出套娃路径 `.../prescan/cv_evidence/1f_view/prescan/`，且 `build` 的
  prescan 拷贝守卫只认 `run_*/0_reading/cv_evidence/<stem>/prescan/**` ⇒ 套娃件**不会**进 staging，
  子代理静默拿不到预扫。主控本轮实际踩中一次。
- 修法二选一：手册把 `--out-dir <RUN>/0_reading` 写死成命令行样例；或 CLI 加落点回显。

## F-2 · 硬隔离工作区缺 kickoff 强制要求的样例文件（机制桶 · MAJOR 候选）
- `session_kickoff.md` 明写「Read all three ... then follow the worked-example plan JSON's style」，
  并给出仓库内路径（另一个 case 的已接受识图产物）= **必读输入**。
- `isolation.py` 的 build **零处理**该文件（`grep worked|smalloffice` 无命中）⇒ 不进 staging；
  且 `guard.py` 的 `DENY_TOKENS` 含仓库目录名 ⇒ 子代理连按原路径尝试读取都会被拒。
- ⇒ 子代理被自己的 kickoff 指向一个隔离墙外、且必被守卫拦下的文件。
- 为何以前没暴露：2026-07-07 那次识图是 **prompt 级隔离**（能读全仓）；本轮是硬隔离机制
  （2026-07-08 落地）**第一次在真实 case 上跑**。同 prescan 一样属「机制建好但从未真跑过」。
- 风险定性：不是泄题面，是**脚手架缺件**。06-25 已实证「脚手架退化 = 墙退化主因且可恢复」，
  故缺件会直接压识图质量，且归因会被误算到模型头上。
- 本轮处置（主控裁定）：把同一文件按**不触禁词的路径** `reference/worked_example_plan.json`
  拷进 staging（sha256 与仓库源 `d3424c42…` 逐字节相同），并在 per-run directive 里显式改指。
  该文件是另一栋楼、不含本 case 任何信息 ⇒ 不构成污染。
- 遗留：手工拷入的件**不在 `MANIFEST.json` 内** ⇒ 本次 merge 的溯源清单会漏记它，已在此登记。
- 修法：build 应把样例按 guard 安全路径纳入 staging 并登记进 MANIFEST（顺带让 kickoff 指向该路径，
  或让 build 改写 kickoff 里的路径）。

## F-3 · （占位）E 效率批实测 — 预扫在真实 case 上是否被用上、有没有用
- 预扫候选数：平面 `1f_view` **803**；立面 North 227 / South 353 / East 323 / West 319。
- 平面 overlay 肉眼观感：墙线确被量到，但外圈尺寸标注/刻度、室内家具框大量入选 ⇒ 信噪比偏低。
- 待填：子代理实际采纳/否决比例与理由、probe 调用数、返工轮数、预扫是省了还是费了。

## F-4 · 隔离守卫的词法禁词扫**文件内容**，把必交产物变成写不出来（机制桶 · MAJOR 候选）
- `guard.py:_lexical_check` 对**整个序列化 tool input** 做词法扫描，Write/Edit 的 `content` 也在内。
- 后果（本轮活体）：子代理写 `reading_summary.md` 时用了「约等号 ~18 条候选」⇒ 命中 `"~" is forbidden`
  （规则本意是拦 home-relative 路径）⇒ **连拒三次、该文件最终没写出来**。
  而 `session_kickoff.md` §Workflow 第 5 步把 `reading_summary.md` 列为必交产物 ⇒ **产物被机制卡死**。
- 同族被拦（全是正常写法，非逃逸企图）：`python -c "…;…"` 里的分号判为复合命令 / `> /dev/null`
  判为越界绝对路径 / `find … | sort` 的管道 / 三点省略号与数值区间会命中 `".."`。
  另注：禁词表含 `grade` ⇒ 子代理若在散文里写 upgrade / degrade 也会被拒。
- 代价实测：第一轮 8 次拒绝里 **7 次是与守卫搏斗**、零安全价值，纯烧弱模型预算。
- 定性：不是安全洞（fail-safe 方向），是**可用性缺陷**，且会被误读成「模型不会写总结」。
- 修法建议：路径类禁词只作用于**被识别为路径的参数**（已有 `_looks_like_path`），不扫散文内容；
  或对 Write/Edit 的 `content` 只做「不得含绝对路径/越界路径」的检查，去掉裸字符黑名单。
- 本轮处置：不动守卫（不在跑测中削弱安全机制），改为在 per-run directive 里加 §7「工作区书写约束」
  显式告知子代理避开这些字符 —— 治标，根因登记待修。
- **实例升级（本轮活体第二处，更有说服力）**：禁词 `grade` 命中的是子代理写立面 JSON 时的
  **"grade line"（室外地坪线）** —— 立面图最基本的建筑术语之一，也正是本项目 07-25 用户
  亲自裁定过的语义（「地面线 = 室内地面 ±0.000」）。⇒ 守卫在**本领域的核心词汇**上误伤，
  不是边缘情况。合并 F-4 的修法建议：内容扫描必须去掉领域词黑名单。

## F-5 · merge 要聚合件、kickoff 让子代理产分图件（脚手架桶 · MINOR）
- `merge_isolated_output` 硬要求 `{"views": {<expected_output_id>: <ReadingView>}}` 单一聚合文件；
  `session_kickoff.md` 却明令子代理「每张图一个 JSON 落 `0_reading/<name>_view.json`」。
- 两边没人负责拼装 ⇒ 主控本轮手工按 view_manifest 的 `expected_output_id` 机械组装（零内容改动）。
- 修法：build 在 kickoff 里要求同时写聚合件，或 merge 支持目录形态自行聚合。

## F-6 · ⛔ 阻断本轮：v3 判卷层对 **reading 阶段**没有生产投影，也没有能力守卫（机制桶 · BLOCKER）
**症状**：flow 一进 J0 即崩 —— `ScoreContractError: score_product_identity_invalid at scoring.input_identity`
（`normalize_typed_elevation_observations` → `elevation_observations_not_list`），未被捕获，整个 flow 挂掉。

**根因（主控读码定位，两处叠加）**：
1. **能力判定对 reading 零守卫**（`score_schema.py:decide_score_capability`）：
   correction 阶段有两道守卫（`product_schema` 必须是 v3、`artifact_contract` 必须是 B5 两契约之一），
   不满足即 `path="not_applicable"`；**reading 阶段一道都没有**，直落 `path="c2_v3"`。
2. **reading 没有生产投影层**（`score_service.py:score_typed_attempt`）：
   `if stage == "correction"` 走真生产提取器 `extract_correction_plan_segments(geometry)`；
   **else 分支直接 `product_payload.get("segments", ())` + 要求顶层 `elevation_observations`** ——
   而识图产物的形态是 `{"views": {…}}`（`strokes`/`dimensions`），**全仓无任何生产代码产出该形态**
   （`grep elevation_observations` 仅命中测试与一个审计脚本，即测试全靠手搓 payload）。
⇒ **任何 v3 答案的 case，识图阶段必崩**。sm24 是史上第一个 v3 签字答案 case ⇒ 从未被触发。
   与管理文档「v3 判卷层此前从未在任何真实 case 上跑过」完全对应。

**与既有教训同族**：07-20 的 M2（判卷循环撞 `ScoreContractError` 全链无捕获 → flow 崩）是同一失败形状，
但那次在非 accepted attempt 上、本次在 **accepted attempt 上且无条件必崩**。
另违 R-4 口径：「量不量得了」的权威在判卷、且**只许说 unsupported 不许崩**——现状是既没说 unsupported 也没说 broken，是直接崩。

**附带小缺陷（同处）**：`payload.get("elevation_observations", ())` 默认值是**元组**、校验却要求 **list**
⇒ 「键不存在」被报成 `elevation_observations_not_list`，错误文案指向错误方向（主控初查时被误导一次）。

**修法是设计决策、不是一行补丁**（故必须走派工，主控不自行拍）：
- 出口 A = 判定「识图不做 v3 类型化判卷」⇒ reading 在 v3 答案下走 `not_applicable`（响亮给理由）或回落 legacy
  `score_reading_vs_gt`，J0 靠 renders + legacy 分数判。**代价**：识图与签字答案之间少一把坐标级尺子。
- 出口 B = 判定「识图要做」⇒ 需在生产侧写 reading views → `{segments, elevation_observations}` 的投影层。
  **代价**：识图是 image-local、答案是 building-axis 世界系，投影需要标定与朝向绑定，是真几何活，非小改。
- 无论选哪个，都应补上 reading 侧能力守卫，让不支持组合以 `not_applicable` 收口而不是抛异常崩 flow。
