# D1l 执行报告（2026-10-08，完成待 Opus 复核）

派工人：Opus；执行方：Astra。基准提交 `875a3ba3`，工作树 `D:\EnergyPlus-Agent-worktrees\d1l`，分支 `dev/astra-d1l-20261008`；开工工作区干净，Q1、Q2、V1 已在基准中。

已完成 [派工单](brief.md) A–G 的实现与离线验证，未提交。**迭代范围：domain（methods、guidance、tools），只影响分工模式的平面读图员与调度员。** runtime、几何内核、共享工具源码、单模型交给模型的内容及正式版本登记表均未改。真实速度与质量保持由 Opus 合入、正式登记后按原安排在 GLM medium 上实测。

## A–G 结果

- **A：** 方法改为整图一次 → `view_plan_blocks({})` 一次拿全层分块 → 外轮廓总尺寸与内部尺寸链 → 墙、门窗、种子一起试建 → 只按差异、硬约束和回叠修正 → 提交。目标小于 10 cm，10–30 cm 不额外量测，剖面只用于试建指出但回叠仍不清楚的差异。保留 Q1 硬约束与空间、开口、连接保真要求。五张实际输入已验证完整覆盖、真 3 倍输出及视图记录回读。
- **B：** 尚未试建时第 **6** 次及以后每次观察追加一句提醒，不阻断、不改其他内容。整批分块计 1 次；排除 `inputs`、格式参考和提交，计入看图、剖面、区域、坐标及尺寸链换算。统计保存在可恢复 sidecar；读图员 `receipt.json` 的 `plan_reader_progress` 记录次数、逐工具计数、首次试建 epoch、距任务开始秒数，根角色汇总也包含这些值。结构性无效参数未执行试建，不计首次；真正进入试建后即停止提醒，不要求成功。
- **C：** 调度员只为实质错误或超过 30 cm 的偏差返工／修改；10–30 cm 留说明。Q2 待决项仍需显式 `keep_plan` 与理由，超过 30 cm 保留双方原图证据要求。同一候选、检查参数和证据未变时，门窗检查返回“与上次相同”、上次概要及完整回执指针，不重算报告。源几何、祖先 proposal/application、原图、claims、视图／剖面、标定、立面计数、装配记录或观察历史变化均失效；失败不缓存。回执保存参数与依赖哈希，指针明确相对角色输出根目录；完整文件供落盘审计，模型直接得到概要。交付与 Q2 guard 保持。
- **D：** 直接调用单模型同一个 `room_types_reference()`，包含完整 **62 项**（含 unknown）代码、中文与颜色表；删除 7 项示例及错误提示中的子集偏置。
- **E：** 首次有效派读图时补齐已知平面与四向立面，统一排队并行，等全部结束再返回新增清单。保留显式任务说明与原点，自动任务继承本批共同原点，无可用原点才用西南外角默认值。平面来自 `floor_plan_images`，立面识别现有四向 `_view.png` 约定；未知图片不猜类型，可由调度员显式派出。已有读图记录后不再补齐；首次仅立面、后续重派均覆盖。
- **F：** 说明超过 400 字符报任务名、超量、可省且只写事实／问题。接受 `plan.openings`、`openings`、`openings:ID`，未知目标给三个例子；集合范围只扩为修改前后真实开口 ID，能补新窗但不能改未指向的隔墙、种子等。[历史原参数重放](dispatch_replay.json)：事件 35 的 plan_f1 超 25，事件 1309 的 plan_f1_r3 超 3，事件 1284 的 `plan.openings` 正常规范化。
- **G：** 当前覆盖的 **116 个不同测试最新结果全部通过**，含三例离线管线、断点恢复、单模型字节对照。最终 439 个 runtime/domain 文件哈希与验证快照一致；四种 single_model 指纹、立面读图员指纹及 runtime 不变。真实 work model／Paratera／DeepSeek 请求均为 **0**。[验证汇总](validation_summary.json)。

## 分块与提醒的取值

优先选 4、6、8 块中能让含重叠长边接近 552 原像素的最少块数；同数量选择长边更小的行列方向，支持极长图的单行／单列。内部边界各外扩核心宽高的 4%，核心格完整覆盖原图；约 552 保持标杆每块约 500 原像素的可读粒度。

初版复用共享 `view_image`，实图核验发现其 1600 像素上限使 sm21/sm25 只有约 2 倍，因此替换为平面角色专用渲染：从同一份准入哈希已核验的原图裁切，复用共享坐标网格函数，实际 3 倍输出，共享工具本身不改。最终 PNG 才分配新的不可变 `view_NNNN`，记录源／返图哈希、bbox、倍率、网格，不覆盖旧视图。极端块超过 4096 长边时才降低倍率并明示，始终完整覆盖。

| 实际图 | 块数与布局 | 已验证实际倍率 |
| --- | --- | --- |
| sm24 一层 | 6，2×3 | 全部 3× |
| sm21 两层 | 各 8，4×2 | 全部 3× |
| sm25 两层 | 各 8，4×2 | 全部 3× |

[五张图的逐块回执](block_layout_evidence.json)包含坐标框、尺寸及倍率；全部通过共享视图记录回读。另目视核查了 sm25 一层分块的原像素网格与尺寸文字。[复现脚本](verify_block_views.py)只读历史输入，在本树临时目录出图，不调用模型。

提醒阈值 6 依据旧轨迹：sm24 首次试建前 20 次观察（13 次剖面）；sm21 一层 35 次、二层 32 次（各 19 次剖面）。新方法先用整图和分块两次，再留三次补看，第六次起提示先试建，不设硬限额。[原事件哈希、次数与时刻](observation_evidence.json)已保存。阈值是否减少 GLM 请求仍需实测。

## 方法原文与字数

[完整改前／改后原文](guidance_comparison.md)来自实际导入的指引，改前固定于 `875a3ba3`。旧版虽已有早试建提示，仍拼入共享细看段；本次替换方法而非再加一层提示。关键原文摘录：

| 环节 | 改前 | 改后 |
| --- | --- | --- |
| 看图 | `View the supplied plan in full.`，随后共享细看段 | `View the whole plan once with view_image`；`Call view_plan_blocks once` |
| 定标 | `For each overall chain add a dimension_chains row` | `Calibrate from overall exterior dimensions; send internal chains in the first trial.` |
| 初稿 | `Once the overall dimension chains and divider lines are read, call trial_plan_bim with a complete plan` | `Submit ALL floor walls, openings and room seeds together to trial_plan_bim, using approximate original pixels.` |
| 修正 | `drawing differences still need original-image review` | `Review ONLY trial drawing_differences, hard-rule failures and the overlay.`；`accept 10-30cm and record the discrepancy without extra measuring.` |
| 提交 | `Deliver through submit_plan_reading with {"trial_id":"latest"}` | `submit_plan_reading({"trial_id":"latest"}) or latest passed trial_id/plan_sha256.` |

字符数按 Python `len`，含空白；工具说明为实际公开目录各顶层 description 的和，不含参数 schema。[完整目录与哈希](surface_comparison.json)。

| 角色 | 指引改前 → 改后 | 工具说明改前 → 改后 |
| --- | ---: | ---: |
| 调度员 | 2,482 → 2,342 | 5,126 → 5,314 |
| 平面读图员 | 9,628 → 9,145 | 4,908 → 5,050 |
| 立面读图员 | 5,187 → 5,187 | 4,453 → 4,453 |

指引共减少 623 字符；连同工具说明总计 **31,784 → 31,491，减少 293**。四种 single_model 模式指纹完全一致，变动只在 `role_division/coordinator` 与 `role_division/plan_reader`。

## 检查过程与边界

- 初次局部 22 项通过；集成首轮 88 通过、11 失败。9 项由未登记改动触发 V1 校验，未进入验证主体；另 2 项分别是集合展开把普通试建的 `None` 变成空白允许范围，以及旧断言仍拒绝 `plan.openings`。已修复前者并替换失效断言，未削弱返工范围检查。
- 沿用 Q1/Q2 的 `BIM_AGENT_REGISTRY_PATH` 建立本树临时验证快照，保持文件／目录校验生效，不改正式登记表。[集成快照](integration_snapshot.json)下 38 项复核全部通过，包括 sm21/sm24/sm25 完整脚本管线、恢复、单模型真实首请求字节对照。脚本适配器不是模型服务。
- 随后只改分块渲染及缓存依赖／回执，局部 27 项、最终 22 项均通过，另五张真实输入渲染回读通过。[最终快照](verification_snapshot.json)核验 439 个文件、正式登记表原字节不变。按同代码同范围复用管线结果，没有再重复三例整套。
- 缓存独立复核补入影响楼层图映射的装配记录；检查验证其变化触发重算，并覆盖参数／源／标定变化、回读及失败不缓存。
- pytest 均显式 `-n 2 -p no:cacheprovider --basetemp AI_agent/archive/local_backup/d1l/pytest`，未跑仓库全量。首次 `uv sync --frozen --offline --python 3.12` 被共享 uv 缓存中的只读 `.git` 拦下；本树已有 `.venv` 可用，激活后确认 Python 与 `src.agent.__file__` 均来自本树，未绕过权限。
- 变更仅在角色代码、相关测试、本实验目录；文本 LF，`git diff --check` 通过。自建测试、快照与分块临时文件清理见 [cleanup.json](cleanup.json)。未操作 `runs-q`、未写 `.git`、未提交／push、未登记发布版本；模型与思考档配置未改。

## 分工与建议提交分组

Astra 负责方法／用途表、观察统计、缓存、集成与报告；两个 `gpt-5.6-sol` / high 子代理分别负责分块工具、派工接口，符合本派工优先 5.6 的偏好，边界明确便于验证。派工接口子代理另只读复核缓存，发现并修复装配记录依赖遗漏。

建议 Opus 复核后分两组提交，本树不提交：

1. **domain：分工读图与调度完整能力包。** 角色目录下 guidance、readers、plan_views、plan_format、session、trial、accounting、feedback、opening_checks 及对应行为测试；影响平面读图员／调度员，不影响单模型。共享接线保持同一实现提交，避免中间缺工具／缺导入状态。
2. **执行证据与交接。** 本目录报告、原文／工具目录对照、历史回放、验证脚本与结果。正式 runtime/domain 版本登记由 Opus 合并后统一处理。

当前只证明离线行为与兼容性，不能据此宣称 sm24 ≤10、sm21 ≤15、sm25 ≤30 分钟已达到，也不能宣称真实模型出模质量已保持。下一步是 Opus 原定的 GLM medium 实测与质量验收。
