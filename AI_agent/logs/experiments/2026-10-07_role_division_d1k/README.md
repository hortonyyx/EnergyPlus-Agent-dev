# D1k：平面读图员少写字

状态：实现与离线验收完成，待 Opus 接收合并；长说明样本的 1,000 字符目标未全部达到，临时目录因策略拒绝暂留。执行方 Astra；基准 `f73fbbc8`，工作树 `d1k`。按 [派工单](brief.md) 与验收 A–H 交付。本包不调用 work model，不派子代理；Paratera、DeepSeek 均为 0。沙箱内不提交。

## 设计与边界

- A：从通过试建且校验身份的平面对象生成原图像素定位，继续输出现有逐对象依据结构；自动定位只表示声明来自原图的哪一处，不将推断升级为观测。保留假设、未决项和显式依据。
- B：外轮廓默认外皮、隔墙默认中线；允许显式覆盖，并保留对应说明和原图定位。
- C：有已通过或继承的基准稿时支持整稿与操作；首次通过前，已解析成数值的失败草稿也可接操作。字段/像素引用尚不能解析且没有其他基准稿时，需要完整稿。后续失败不覆盖已通过的基准稿。说明字段不计入几何修改，但实体变更与返工范围继续核对。
- D：提交引用最近通过的试建或哈希，可选填写说明；楼层、目标、拓扑决定、镜像依据与试建身份校验保持。
- E：只读历史运行，离线重放 run3、run6、run7、sm21 run1、sm25 run1；另核 run5 无基准操作与 run3 说明字段拒收，记录参数与 schema 字符数。
- F：替换平面读图员指引及工具说明，登记改前改后长度；不改调度员或立面读图员段落。
- G：相关角色检查（显式 `-n 2`）、三例离线贯通、中断恢复与单模型逐字节对照；登记新 Agent 版本并保留旧版本。不跑全量。
- H：证据与报告仅在本实验目录，临时产物在 `AI_agent/archive/local_backup/d1k/`；文本 LF。交付前核对文件归属与临时目录，给出建议提交分组。

如评价或覆盖要求必须改共用代码，或需触及 D1j 文件，则停止该部分并记录最小改法，交 Opus 协调。当前尚未发现此类阻塞。

## 开工核对

已完整读取 Agent.md、产品目标、当前任务、工作方式、会话设置与 10-07 最新交接。初始工作树干净；相邻 d1j 与 runs-cmp3 使用中。已读取验收 A–H、名词规范第二节、提速分类与第三次审查对应条目。后续仅按本包文件范围实施。

## 验证与交付

### A：自动依据与原图追溯

提交从校验过哈希的数值稿生成锚点、外轮廓、隔墙、空间种子和开口的依据框，沿用 `plan/evidence/unresolved` 交付结构。线段/多段线取范围、点加 2 像素边距，边距可裁到图片边缘，声明本身越界仍拒收。像素 profile 引用先由既有试建解析，依据不从引用字典猜坐标。逐对象 source_refs、开口 assumptions、全稿 basis/assumptions/unresolved 保留；附加 notes 明确分为 assumption/inferred/unresolved。

自动框表示“该声明在原图的位置”，不宣称该对象已被正确观测。锚点只有一个像素轴，自动生成的是坐标带，不能凭空定位尺寸文字。依据文字明确标注此边界。旧调用仍可交显式依据：保留并核验已交行，缺少的行自动补齐；新工具 schema 不再要求整表。

既有评价桥接和覆盖核对无需修改。成功提交重放逐个检查对象覆盖、平面原稿不变、未决说明不丢失，并经原评价桥接对比 neutral answer 完全相同。几何内核、共用评价代码均未改。

### B：墙线默认值

外轮廓默认 `outer_face`，隔墙默认 `centerline`。默认记录写明这是建模约定，自动框定位的是声明墙线，不是假装观测到尺寸线；默认值不移动任何几何。可只覆盖一类墙，填写 convention/basis；可补 bbox 和 dimension_basis，显式冲突仍拒收。三例离线旧方案保留 `explicit_face` 覆盖，不把历史参考线重新解释成默认值。

### C：整稿和操作统一处理

两种写法先得到完整声明，再按实际变化核对返工范围。basis、assumptions、unresolved、source_refs 单列为说明变化，不授权改墙、开口、种子、用途或楼层。无数值稿的格式错误仍不形成可编辑基准；有通过稿时，失败修订仍回到最后通过稿。跨任务继承仍只能继承通过稿。修复了内存读取直接返回原字典的问题，调用方不能通过改返回值篡改基准稿。

历史原始调用以真实 frozen MCP 在本树单独执行，非模拟回执：

| 历史调用 | 新结果 | 核对 |
|---|---|---|
| run5 `event-000769`，草稿未出几何时交操作 | 通过 | 原草稿仍先失败；退出并重开试建会话后，原始两操作成功；实际只改 `D_recep` 与 `wall_confE` |
| run3 `event-000642`，返工同时改 y_anchors/unresolved | 通过 | 原始两操作成功；几何修改只有 y_anchors，unresolved 留在说明审计 |

证据见 [replay_results.json](replay_results.json) 的 `rejected_operations`。这两次编译和 run5 的失败基稿共 3 次真实本地 `build_plan_bim` 调用，没有模型请求。

### D：按引用提交与原有检查

通常参数为 `{"trial_id":"latest"}`；也接受最近通过稿的 `trial_00N` 或 `plan_sha256`。只读该稿并保留原哈希。失败稿、过期成功稿、错误楼层、错误目标、缺失拓扑决定、镜像缺失指北针依据以及稿/数值产物/原图被改仍拒收。补充说明不改原稿，提交后的不可变性和中断恢复继续保留。

### E：历史量化与手续拒收

字符口径：`json.dumps(..., ensure_ascii=False)` 默认分隔符，计 Unicode 字符，不冒充 token。下面逐字保留历史提交中尚未包含在原稿的未决说明，仅省去逐对象依据、重复默认墙线、空字段及普通朝向不需要的指北针。**不靠删未决项凑 1,000 字符。**

| 历史最终提交 | 原参数字符 | 新参数字符 | 新结果 |
|---|---:|---:|---|
| run3 F1 初稿 | 9,450 | 1,118 | 镜像缺指北针依据，保持拒收，见下 |
| run3 F1 返工 | 10,356 | 697 | 通过 |
| run6 F1 | 8,751 | 1,039 | 通过 |
| run7 F1 | 9,163 | 803 | 通过 |
| sm21 F2 | 6,873 | 814 | 通过 |
| sm21 F1 | 6,610 | 675 | 通过 |
| sm25 F2 | 12,883 | 1,584 | 通过 |
| sm25 F1 | 13,868 | 1,264 | 通过 |
| 补充：run5 F1 | 9,786 | 459 | 通过 |

不补新说明且无额外核查项时，引用本身 22 字符；压紧空白是 21。指定 8 份历史最终提交中，4 份逐字保留额外说明后小于 1,000；其余 4 份为 1,039–1,584。接口目标已具备，但不能宣称这批长说明样本全部达到 1,000 字符目标。实际耗时、token 或质量收益未测，留待后续获批的 work model 测试。

31 份历史试建产物中：10 份通过稿全部重新确定性编译通过；16 份数值稿重新编译仍失败；5 份格式/解析失败稿不当成几何稿。12 次历史提交均重放，包括三个首交拒收；179 个原始文件重放前后哈希相同。

- run6 首交：普通朝向无需指北针，按新接口省去多余且越界的框后通过；若显式保留该坏框，仍拒收。
- run7 首交：使用墙线默认值，省去冗余的 dimension_basis 自由文本后通过；没有放松显式转换冲突检查。
- run3 首交：无警告却自造 topology issue_id，仍拒收；随后那份历史“已通过”稿的坐标为镜像而没有指北针，开工基线与新版本都拒收。这是现有朝向检查与更早历史行为不同，不是本包新增回退。未伪造箭头来强行通过，后续真实返工稿正常通过。

详细数值与新参数见 [replay_results.json](replay_results.json)，开工基线原代码重放见 [dispatch_baseline_replay.json](dispatch_baseline_replay.json)。重放脚本 [replay.py](replay.py) 只读主树，真实工具产物只在本树临时目录。

### F：替换指引与工具文本

| 文本 | 改前 | 改后 |
|---|---:|---:|
| 平面提交参数 schema | 2,452 | 2,361 |
| 同一 schema 紧凑 JSON | 2,236 | 2,154 |
| 平面读图员完整指引 | 9,084 | 9,045 |
| 试建工具说明 | 396 | 343 |
| 提交工具说明 | 280 | 364 |

旧写法已替换。提交工具说明新增自动依据、墙线默认和保留的例外检查，故单条说明增加 84 字符；这里不把每项都包装成缩短。单模型指引 9,670、调度员 1,930、立面读图员 5,770 的字符数与内容哈希完全不变。见 [before_metrics.json](before_metrics.json) 和 [after_metrics.json](after_metrics.json)。

### G：版本与检查

已登记 `t1-20261007-d1k.1`，旧版本逐项原样保留；没有新增需登记的运行模块。修改只在本包负责的 5 个角色源码、对应检查与版本登记文件。没有改 D1j 文件，也没有改单模型/内核/runtime 实现。

已通过针对本包的 37 项检查；明确失败草稿可编辑后的相关 18 项复查通过。完整角色检查使用 `test_role_*.py`、显式 `-n 2`、本包 basetemp：首轮 195 通过 / 2 失败，用时 420.21 秒。两项均为旧设计断言（恢复后禁止整稿、锁定旧错误文案）；改成“整稿引用复用原回执且不重编译”和“非法参数在调用试建前拒绝”的行为检查后，仅复查两项及其关联提交检查，共 9 项全过，用时 26.79 秒。合并有效结果为 **197 个不同检查都有通过证据**，没有为报告好看重跑整套。

sm21/sm24/sm25 三例真实 frozen MCP 离线贯通、四项单模型逐字节对照、四处中断恢复均首轮通过。已知的 checkpoint 恢复偶发失败本轮未出现。原始结果见 [role_tests.xml](role_tests.xml)、[role_recheck.xml](role_recheck.xml)，汇总见 [validation_summary.json](validation_summary.json)。脚本适配器提供预设响应，不产生真实 work model 请求。

开发中发现旧设计的 4 个断言仍要求“通过后禁止整稿/必须手写全部依据”，按验收要求删除或替换。新增检查发现一个内存引用篡改漏洞，已修复并通过。重放脚本首次因编译器要求 image_size 是 tuple、首次真实工具因尚未登记新版本而停止，修正运行条件后重放完成，未绕过版本核验。

### H：交付、分组与限制

建议由 Opus 在可写 Git 环境提交两组：

1. 平面接口与保护检查：5 个运行文件、对应角色检查、三例 fixture 改为引用提交、Agent 版本登记。
2. 本目录报告、指标、重放脚本与证据。

`guidance.py` 只改平面段和其专用 import。合并 D1j 后应登记包含两包的新版本，不能将本树版本哈希宣称覆盖邻树代码。`.git` 只读，本包无 commit/push/stage；没有动并行对照运行。

本包临时目录 `AI_agent/archive/local_backup/d1k/{pytest,replay}` 暂留，共 102 个文件、6,608,734 字节（约 6.30 MiB）。已尝试在解析路径并确认位于本树后用 PowerShell 删除本包未完成的临时子目录，工具自动审批以 `blocked by policy` 拒绝；未换办法绕过。pytest 在正常复查时自行重建其 basetemp，旧检查输出因此已自动替换，未作为绕过手段调用。所有提交候选文本已规范为 LF；`git diff --check` 通过，新版本 84 个登记文件核验通过。没有必须触及 D1j 文件或共用评价代码的阻塞。

主要验证命令（工作树根目录、先运行 `. .\scripts\activate_windows.ps1`）：

```powershell
python -m src.agent_runtime.agent_registry register --root . --version t1-20261007-d1k.1
python AI_agent/logs/experiments/2026-10-07_role_division_d1k/replay.py
$roleTests = @(rg --files tests -g 'test_role_*.py')
python -m pytest -n 2 --basetemp AI_agent/archive/local_backup/d1k/pytest @roleTests -q --junitxml AI_agent/logs/experiments/2026-10-07_role_division_d1k/role_tests.xml
python -m pytest -n 2 --basetemp AI_agent/archive/local_backup/d1k/pytest tests/test_role_trial.py::test_trial_persists_images_and_resume_reuses_verified_receipt tests/test_role_review_regressions.py::test_trial_bad_schema_and_nested_business_name_return_repairable_envelopes tests/test_role_submission.py -q --junitxml AI_agent/logs/experiments/2026-10-07_role_division_d1k/role_recheck.xml
```

命令清单是本轮执行记录，不是要求合并时重复全跑；复用同代码同范围的有效结果。重放脚本的真实工具部分要求独立空临时目录，已有产物时会拒绝覆盖；版本登记不可重复使用同一版本号。登记在真实工具成功运行前完成。
