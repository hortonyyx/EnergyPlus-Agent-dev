# G1 执行报告

> **10-08 晚 Codex 接手修订（验证进行中）：** 原实现与证据已保全。通道终止墙存在多种几何解释时改为保宽，不按距离或编号替用户选择；用户明确要求 **>30 cm 的位置分歧先确认再交付**，原第 4 节的默认放行已撤销。双原图查看、2 px 余量、10–30 cm 自动保留平面与复核继承继续有效。下文保留上午执行方原始记录；其中 D1l“4 次即交付”和原指引统计仅适用于当时的宽松规则，不能用于声称当前版本通过。最新验证及归档见 [Codex 接手记录](../../worklog/2026-10-08_codex_takeover_close.md) 与 `takeover_historical_replay.json`。

基准：`9eb61857`，工作树 `D:\EnergyPlus-Agent-worktrees\g1`，分支 `dev/astra-g1-20261008`。执行依据为本目录 [brief.md](brief.md)。已完整阅读开工规定文档及路线所指的最新收工记录，并核对工作树干净。

## 范围与边界

- domain：BIM rules／kernel 的跨层对齐（两种模式）；roles、tools、guidance 的分工装配复核、高度依据、位置裁决和交付。
- runtime 与版本登记表不改，版本由 Codex 集成后登记。
- `.git` 及主树和 `runs-d` 的已结束运行只读；不提交、不跑全量、不调用 work model，Paratera／DeepSeek 请求均为 0。
- 对齐失败策略做开关，默认保留拒绝装配；不替用户决定默认策略。

共用对齐影响单模型与分工；其余关口及指引修改针对分工。未改全局目标、路线或交接。两份历史产物均已离线交付，最终代码的定向验证完成；唯一未通过项是本机进程终止权限限制，详见验证段。

## 1. 跨层对齐与失败策略

数值等同性采用绝对 **1e-7 m** 容差，原 `8.7e-8 m` 残差不再被当作墙偏移。原两对墙 `0.149833913 m`、`0.282799642 m` 均自动对齐，房间、开口、宿主与连接检查通过。墙上的门窗和相接隔墙端点联动。

父复核发现首版只移动一个开口端点，虽过拓扑检查却缩窄实体门，已撤销该做法。最终实体门沿原宿主整体平移：D3 数值计划中的宽度保持 `0.715563506 m`，导出六位小数坐标有微米级舍入。

原 D-ns 开敞通道随两侧墙距规整，净宽 **1.987899741 → 1.838065828 m**；两端相对侧墙的偏移分别保持 `+0.070205563 m`、`-0.061728608 m`。净宽变化明确入审计，不能表述成所有开口尺寸均不变。历史兼容同时要求：`door/open` 类型、`state=open`、已保存的结构化 gap 支持、完整跨宿主同侧的两条终止边界、没有硬宽度依据。不读取 ID 含义或 `source_refs` 文字；通道识别以显式推断记入审计，不改变源开口类型。缺少条件则保宽，再交严格编译／关系检查。普通打开的门、缺边界、硬宽度、窗、两边界分处宿主两侧的负例均已覆盖。

| 输入清单开关 `cross_storey_alignment_failure_policy` | 行为 |
| --- | --- |
| `reject_assembly`（默认） | 对齐不能安全完成时拒绝整次装配；默认未改 |
| `skip_failed_pair` | 回滚该对，保留原几何并记录原因，随后续新稿写入 JSON／HTML 交付说明 |

两档均贯通工具链 `assemble → revise(use) → finish`。跳过只豁免当前几何仍对应的该对偏差；父稿哈希、当前对象／坐标仍需匹配，其他硬错误继续拒绝。证据：[cross_floor_replay.json](cross_floor_replay.json)。

## 2. 确定性规整与真正几何变化分开

装配比较读取哈希绑定的单层、整栋规整收据，按实际顺序处理坐标变化。开口只接受审计中精确的世界坐标 `before → after`，没有任意单端裁剪候选；缺字段、哈希变化、审计与源几何不符均不能豁免。

N1 的重复墙带先合并、随后跨层移动，现按该顺序处理零宽折返，不再误报 S-e4。整栋统一复核发生在用途／高度写入之前。复核身份只取读图绑定、实际变化、阻断项；候选编号、源哈希和诊断统计变化不会独自重开确认。真正的房间、开口、相邻关系变化及返工后的新读图版本仍受检查。

## 3. 高度引用与 located_count

一步建楼保留读图员原图框、原高度及对象绑定。手工高度可用 `reader_evidence={task_id,sha256,opening_id}`，无需重登视图；真实不可变产物、正确哈希、相同数值和当前 BIM 对象唯一匹配缺一不可。

| 核对范围 | 已定位／外部开口 | 新 view |
| --- | ---: | ---: |
| D1l 旧 candidate_11 原参数严格回读 | 26／33 | 0 |
| 原产物的原框、原高度、显式引用重放 | 33／33 | 0 |
| 最终 D1l 一步建楼安全自动匹配 | 23／33 | 0 |
| 最终 N1 一步建楼安全自动匹配 | 32／33 | 0 |

33 项专项中，32 项高度值完全相同；`F1:D-east-double` 改回产物原高度，最大差 `4.150943 mm`。不能宣称旧手填参数原样就有 33 项已定位。自动匹配剩余 D1l 10 项、N1 1 项仍标记缺少安全匹配。旧 candidate_15 重建后无保留高度绑定，严格回读仍为 0／33。证据：[summary.json](height_replay_output/summary.json)、[replay_height_evidence.py](replay_height_evidence.py)。

## 4. 超过 30 cm 的位置分歧先裁决再交付（10-08 接管修正）

10–30 cm 自动保留平面值并记录理由。超过 30 cm 的待裁决项和要求重读的项均阻断 `finish_bim`；停止／预算耗尽的 fallback 走同一关口。交付写入不再生成默认 `delivery_resolution`，汇总中的 `delivery_defaults` 保留为空数组以兼容既有结构。

`role_state(position_decision_id=...)` 一次调度员调用返回两张真实原图局部和两个已保存 `view_id`，底层使用现有 `view_image` 两次。覆盖双方证据框允许每边 **2 px** 舍入余量；只有查看双方证据并明确选择保留平面或采用立面后才可交付。选择重读后，直到新读图产物重新装配并完成裁决前持续阻断。主动选择立面值、候选位置被改或宿主／连接改变仍受相应检查。

## 5. 说明、用途、高度不重开复核

只改说明、用途、高度时，已确认的几何变化沿用原确认；`finish_bim` 不因新候选编号或诊断字段变化再次阻断。真实位置修改、新读图几何仍需复核；陈旧或未验证的读图谱系不能靠确认绕过。

## 6. 历史重放与三例贯通

计数统一从首次 `assemble_from_readers` 起，不把已经完成的读图算进新重放。各核对 40 个原始输入文件哈希，均未改变。

| 运行 | 原调度员调用 | 最终离线调用 | 装配调用 | 复核调用 | 人工位置裁决 | 新 view | 交付 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| D1l | 121，未交付 | 4 | 1 | 0 | 0 | 0 | 旧规则下成功；现规则须先裁决 11 项 |
| N1 | 13，已交付 | 6 | 2 | 1 | 0 | 0 | 成功 |

D1l 的 4 次为 assemble／check／inspect／finish 各一次。N1 多一次 `review_role_assembly` 和一次续接 assemble；内部真正整栋 assemble 仍只有一次。两份重放底层 frozen 工具调用均为 8 次。

N1 唯一确认是 WLONG：旧重叠墙带删除后，空间归属从 S-e4 变为 S-corr-s；水平跨度及宽度保持，y 随审计外墙从 `5.997819` 移到 `5.980498 m`。这是真实关系变化，保留一次显式开发复核；后续用途／高度写入和 finish 沿用该确认，没有循环。旧重放曾把 D1l 的 11 项超过 30 cm 分歧按平面默认交付；该结果已被 10-08 用户决定废止。N1 没有未选择的位置项。两份装配仍提示未安全匹配的高度，应区别于交付阻断错误。

这只是既有读图产物重放，**不是新冷启动，也不证明工作模型提速或质量**。完整本地输出位于 `AI_agent/archive/local_backup/g1/historical_replay_final_verified/`。证据：[historical_replay.json](historical_replay.json)、[replay.py](replay.py)。

三例 sm21／sm24／sm25 曾在旧规则冻结代码下均交付：一次 assemble 后 check／inspect／finish；连输入与委派计入，每例共 6 次调用，无装配复核和人工位置裁决。sm24 记录了 3 个默认位置决定，按现规则应阻断，旧交付结论不能复用；sm21、sm25 没有默认位置项，预期不受本次语义变化影响，但仍由 Codex 重放确认。精简旧证据见 [scripted_cases.json](scripted_cases.json)。

当前语义会使两类旧断言失效，重放时须由 Codex 更新：

1. [replay.py](replay.py) 末尾“D1l、N1 均已交付”的断言不再成立；D1l 应先证明 11 项待裁决会阻断，或在脚本中逐项完成双图查看和明确裁决后再期待交付。
2. [historical_replay.json](historical_replay.json) 中 D1l 的 11 项 `delivery_defaults`／交付成功，以及 [scripted_cases.json](scripted_cases.json) 中 sm24 的 `delivery_defaults: 3`／无裁决成功交付，都是旧规则证据；新的期望不得再生成 pending 项的 `delivery_resolution`。

## 7. 指引与工具说明替换

| 内容 | 修改前 | 修改后 | 差值 |
| --- | ---: | ---: | ---: |
| 调度员指引 | 2342 | 2270 | −72 |
| 六项调度员工具说明合计 | 2053 | 1954 | −99 |

统计为 Python `len(str)` 的 Unicode 字符数，含空格／换行，不是 token。单模型、平面读图员、立面读图员指引哈希未变；新行为替换旧要求，没有在末尾叠加提醒。证据：[guidance_comparison.json](guidance_comparison.json)。

## 验证与交接

按派工执行指定 80 个测试文件（`test_bim_*`、`test_plan_*`、`test_role_*`），没有跑全仓。第一轮 762 项中 755 通过、7 失败；6 项旧规则断言已更新，随后 48 项定向全部通过。开口保宽边界再修正后，最终 kernel 五文件 **100 项通过**；最终六个角色文件 **52 项通过**，包括三例真实本地 MCP 贯通、写入恢复和读图恢复。

以最后一次完整文件范围的结果覆盖旧结果，去掉两项已被新行为替换的旧用例，合计 **782 个不同有效用例：781 通过、1 项环境限制失败**。不将重复成功累加，也不将曾经通过的单端裁剪检查算作最终证据。范围、原始 JUnit 哈希、最终 Python 文件哈希与清理状态见 [validation.json](validation.json)。

另 1 项 `test_terminate_subscription_stops_parent_and_nested_session_child` 因本机 `taskkill /T /F` 返回 `ERROR: Access denied` 失败。相关函数与基线逐字相同，无害子进程探针复现权限限制；未绕过沙箱、未改无关 runtime，该项不能算通过。证据：[platform_check.json](platform_check.json)。

10-08 接管修正后，仅按派工重跑 `tests/test_role_position_review.py` 与 `tests/test_role_guidance.py`：显式 `PYTHONPATH`、`PYTHONUTF8=1`、`-n 2 -p no:cacheprovider`，**16 项全部通过（8.98 秒）**。覆盖超过 30 cm pending 阻断、双图后明确选择可交付、重读继续阻断、10–30 cm 自动保留平面和 2 px 覆盖容差。JUnit 与日志保存在 `AI_agent/archive/local_backup/g1_takeover_position/`。第一次同范围运行未设 `PYTHONUTF8`，两项候选写入用例在 Git 文件枚举处触发本机 GBK 解码失败；原始失败 JUnit／日志已并列保留，设定 UTF-8 后未改代码即全过。

pytest 均显式 `-n 2 -p no:cacheprovider`，临时目录位于本工作树 `AI_agent/archive/local_backup/g1/`。已保存精简证据，清理前逐个验证解析后的目标位于本工作树，再用 Python `shutil.rmtree` 删除本包 pytest 目录；历史运行保留。

MCP 验证使用 ignored 目录内临时代码哈希快照，仅供测试，不是正式发布登记。正式 `src/agent_runtime/agent_versions.json` SHA-256 保持 `c400fbef87db14d9893425e790b6a7af435fc501c31bc7718927cf07797541e2`。见 [prepare_test_registry.py](prepare_test_registry.py)、[test_registry_evidence.json](test_registry_evidence.json)。

建议 Codex 分三组提交：

1. **domain · BIM rules／kernel／共用 tools**：跨层容差、墙／开口／端点随动、失败策略和交付审计继承，及对应几何／工具检查；影响单模型和分工。
2. **domain · roles／tools／guidance**：装配确认继承、超过 30 cm 先裁决／双图查看、高度产物引用，以及角色检查和三例夹具；影响分工。
3. **G1 执行证据**：本目录报告、原输入哈希、历史／高度重放脚本、指引对照与验证汇总。

执行方未提交，Codex 集成后统一登记版本。失败策略默认值仍待用户选择，本包未切换。合并复核重点之一是历史通道的窄识别条件及已记录净宽变化。

开发分工采用三位 `gpt-5.6-sol`／high 子代理，分别负责 kernel、装配与位置关口、高度证据；遵循派工单优先 5.6 的安排，将边界明确的实现与证据核对分开，父代理负责集成和历史贯通。这里的子代理是 dev model；work model／外部模型 API／Paratera／DeepSeek 请求均为 0。

环境说明：`uv sync --frozen --offline --python 3.12` 因 C 盘 UV 缓存 `.git` 无读取权限失败，未绕过；现有工作树 `.venv` 的 Python 3.12.10／pytest 9.0.3 与本树 `src.agent.__file__` 已确认。测试使用 ignored 目录中的临时代码哈希快照，正式登记表保持原字节，版本仍由 Opus 合并后统一登记。
