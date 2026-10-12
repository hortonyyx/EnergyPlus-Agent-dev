# sm25 同配置再跑一轮（2026-10-12）

本轮未完成整楼交付。180次请求用尽后自然结束，终态 `model_budget_exhausted`，`finalization.status=assembly_review_required`，`delivery=null`。四立面和两层平面都曾正式提交，第三次装配仍被跨层几何约束拒绝。确认了两个具体 harness 接口缺口，因此不能将本轮归因于代理，也不能继续沿用前次“无已知内部阻断”的结论。

## 范围与结果

用户授权“按同配置再跑一次”。使用当前已验证的 runtime v11/domain v68，新目录冷启动，不接续旧run、不复用旧模型稿。与前一完整运行 v10/v67 相比，模型/图像/任务/并发/预算相同，harness版本为之前已完成修复后的v11/v68；不能说两轮harness字节完全相同。

| 项目 | 本轮记录 |
|---|---|
| 冻结提交 | `7abd75ab8eb455cc097fec7a78f53e7ae49b4036` |
| 配置 | [run_high.json](run_high.json)，相对前轮只改 batch_id、case_id、output |
| 模型 | 协调与平面 GPT-6 Sol/high；立面 GPT-6 Luna/high；ChatGPT subscription |
| 输入/并发 | 原六张sm25 PNG；reader slots 6，实际请求峰值6 |
| 原预算 | 180模型请求、700工具、10800秒、max_candidates24；输出32000/请求；自动上下文、无总token机械上限 |
| 执行耗时 | **87分47.64秒**（5267.6392869587秒，root receipt） |
| 模型调用 | **180请求 / 169完整响应 / 11失败 / 0在途** |
| 失败分类 | 10 transport_error：9 ConnectError/connect、1 RemoteProtocolError/awaiting_response_headers；1 service_unavailable/server_is_overloaded |
| 重试 | 8次有界重试；唯一NO_MORE_RETRY未重发 |
| 工具 | 245次调用和执行；包括正常返回的业务失败 |
| 平面试建 | 41次：8通过、30试建失败、3在回执生成前因返工范围拒绝 |
| 提交/装配 | 4次平面＋5次立面提交被接受（含替换稿）；3次整楼装配均失败 |
| 交付 | 0成功整楼候选，0正式BIM/交付查看器；存在单层候选与预览，见下 |
| 新增离线/额外probe | 0 / 0；只读审计复核，不重复已有全量测试 |

CLI 收尾记录：`exit_code=1`；从启动到全部报告落盘共 **95分23.70秒**（5723.696秒），其中包含启动及终态后的报告处理。最终receipt补齐了角色统计，状态和运行耗时未改变；journal仍为2340事件。

运行中保持原 `127.0.0.1:10809` 代理，未切换/关闭代理；未换模型、降思考、改稿、补提示、手动派工、调预算、回退收费API或追加第二轮。协调器发起的返工属于原模型自主行为。512个冻结程序文件、runtime43/domain429指纹、配置、原六图及运行内六图哈希全部吻合；180条wire与169条响应模型身份匹配。

## 用量与结算

| 已报告项目 | 小计 |
|---|---:|
| input tokens | 8,198,762 |
| output tokens | 94,996 |
| total tokens | **8,293,758** |
| cached input（已含于input） | 2,521,728，占已知输入30.7574% |
| reasoning（已含于output） | 44,604 |
| 未知用量请求 | **11** |

180/180请求合法且唯一结算，0schema/settlement错误。上表仅已知小计，整案完整用量和费用未知，订阅不能换算成臆测API账单。receipt顶层 `usage_complete=true` 仅覆盖协调员27次，不能据此说整案完整。并行角色时间不能相加当作墙钟耗时。

## 原因与边界

1. **确定的domain回执缺口。** `read_plan_draft` 对 `plan`、`regularization`、`regularization_inputs` 全量返回，绕过已有report分页。7次大读取（含最高2,900,321字节纯文本）造成5个F2返工任务本地 `context_recovery_required`。巨型回执尚未发给后续模型即被guard拒绝；不是服务端超窗或代理断连。源码入口为 `src/agent/runtime_roles/trial.py:889–896`。尚未验证审计数据膨胀根因及分词估计误差，不将估算器单独定性为bug。
2. **确定的失败草稿继承缺口。** event-001255 对继承稿合法 `report:/building_precision` 读取被拒。`inherit_failed_reference`（trial.py:1001–1020）未绑定 `_reference_report`，passed继承有绑定。这是独立检索缺口；109字节拒绝本身不是上下文停止的直接原因。
3. **模型返工未收敛。** 单层成功不等于跨层一致。第一次装配有4项未解决高程覆盖和5项硬几何拒绝；第二次高程覆盖通过但5项几何拒绝仍在；第三次降到2项。最终F1 `y=14.0`、F2 `y=13.9` 相差0.1m，且F1 middle-office-north ceiling 与F2 circulation floor产生0.1×3.9m（0.39㎡）窄接触。三次 `assemble_from_readers` 均execution succeeded但业务build_failed，`geometry_applied=false`、`created_candidates=[]`。DN3/DS4越范围拒绝、断头、非正交和开口宿主反馈不能直接当成harness缺陷；DS4涉及继承元数据的疑点仍未证实。
4. **外部链路仍有失败。** 10次传输错误和1次明确服务过载独立统计；既有日志不能进一步归因代理或上游。没有因此新增连接层、重试架构或恢复框架。

此前成功大回执压缩、通过未提交稿接续和缺usage结算修复获得真实覆盖：F2原任务试建通过后遇服务过载，后续 `plan_f2_restore` 接续通过稿并提交；新F1/F2也能在成功试建后读报告和看图。它们并不覆盖本轮发现的任意草稿字段全量回读。

建议下一步仅处理上述两个已证实接口缺口，配小范围离线回归；不要为尚未归因的传输波动扩建。修复和下一次真实整案未在本轮执行，不承诺两处修复必然解决跨层几何。

## 逐角色复盘

协调员Sol 27/27；平面Sol 130/121（8传输＋1过载）；立面Luna 23/21（2传输）。共20个任务。表中“试建”依次为通过/失败/范围拒绝，“提交”为接受/拒绝；任务重派不代表额外人工批次。

| 任务 | 请求/完整响应 | 试建 | 提交 | 停止原因 |
|---|---:|---:|---:|---|
| `coordinator` | 27/27 | — | 0/0 | `model_budget_exhausted` |
| `elev_s` | 4/4 | — | 1/0 | `completed` |
| `elev_w` | 4/4 | — | 1/0 | `completed` |
| `elev_e` | 4/4 | — | 1/0 | `completed` |
| `elev_n` | 4/4 | — | 1/0 | `completed` |
| `plan_f1` | 12/12 | 1/2/0 | 1/1 | `completed` |
| `plan_f2` | 8/6 | 1/2/0 | 0/0 | `service_unavailable` |
| `plan_f2_retry` | 6/3 | — | 0/0 | `model_retries_exhausted:transport_error` |
| `plan_f2_restore` | 4/4 | 1/0/0 | 1/0 | `completed` |
| `elev_s_levels` | 7/5 | — | 1/1 | `completed` |
| `plan_f2_align` | 10/10 | 0/6/1 | 0/0 | `context_recovery_required` |
| `plan_f2_align_fix` | 5/5 | — | 0/0 | `context_recovery_required` |
| `plan_f1_align` | 12/8 | 0/2/0 | 0/1 | `model_retries_exhausted:transport_error` |
| `plan_f2_repair2` | 3/3 | — | 0/0 | `context_recovery_required` |
| `plan_f2_precise` | 14/14 | 0/8/1 | 0/0 | `answer_validation_failed` |
| `plan_f2_dn3` | 8/8 | 0/1/1 | 0/0 | `context_recovery_required` |
| `plan_f2_doors` | 3/3 | — | 0/0 | `context_recovery_required` |
| `plan_f2_fresh` | 23/23 | 3/6/0 | 1/1 | `completed` |
| `plan_f1_fresh` | 21/21 | 2/3/0 | 1/1 | `completed` |
| `plan_f1_step_fix` | 1/1 | — | 0/0 | `root_model_budget_exhausted` |

## 局部产物和未覆盖项

以下是最后正式提交的**单层局部候选**，只做文件及source identity核对，未实际浏览器验收：

| 楼层 | 平面 | 原图回叠 | 局部BIM | 局部查看器 |
|---|---|---|---|---|
| F1 | [平面](D:/Sim-BIM-Agent/runs/sm25-gpt-same-config-rerun-20261012-high/tasks/85c3267eb23b42a403e6a40cd0e88f81f83c77cba0fca07b6b86bf7501350278/bim/trial_workspace/candidate_02/plan_F1.png) | [回叠](D:/Sim-BIM-Agent/runs/sm25-gpt-same-config-rerun-20261012-high/tasks/85c3267eb23b42a403e6a40cd0e88f81f83c77cba0fca07b6b86bf7501350278/bim/trial_workspace/image_overlays/overlay_002.png) | [source_model](D:/Sim-BIM-Agent/runs/sm25-gpt-same-config-rerun-20261012-high/tasks/85c3267eb23b42a403e6a40cd0e88f81f83c77cba0fca07b6b86bf7501350278/bim/trial_workspace/candidate_02/source_model.json) | [viewer](D:/Sim-BIM-Agent/runs/sm25-gpt-same-config-rerun-20261012-high/tasks/85c3267eb23b42a403e6a40cd0e88f81f83c77cba0fca07b6b86bf7501350278/bim/trial_workspace/candidate_02/viewer.html) |
| F2 | [平面](D:/Sim-BIM-Agent/runs/sm25-gpt-same-config-rerun-20261012-high/tasks/ed271a699753e9d9176c0fdd5b1acb4e4154d2bd99000e2e20d8bc2624b4a3bb/bim/trial_workspace/candidate_03/plan_F1.png) | [回叠](D:/Sim-BIM-Agent/runs/sm25-gpt-same-config-rerun-20261012-high/tasks/ed271a699753e9d9176c0fdd5b1acb4e4154d2bd99000e2e20d8bc2624b4a3bb/bim/trial_workspace/image_overlays/overlay_003.png) | [source_model](D:/Sim-BIM-Agent/runs/sm25-gpt-same-config-rerun-20261012-high/tasks/ed271a699753e9d9176c0fdd5b1acb4e4154d2bd99000e2e20d8bc2624b4a3bb/bim/trial_workspace/candidate_03/source_model.json) | [viewer](D:/Sim-BIM-Agent/runs/sm25-gpt-same-config-rerun-20261012-high/tasks/ed271a699753e9d9176c0fdd5b1acb4e4154d2bd99000e2e20d8bc2624b4a3bb/bim/trial_workspace/candidate_03/viewer.html) |

F2局部编译沿用文件名 `plan_F1.png`，对应任务和source身份已核对。根bim的candidate_01..05也是装配准备过程中导入/定高的单层产物，最新F1=05、F2=04；root finalization指向candidate_05，require_all=true的最终检查明确报missing_required_floor F2，不能当作成功整楼。

GT未读；空间划分、门窗宿主、连接关系的独立图纸质量和5/10/30cm分档均**未评**。本轮domain接受与局部试建通过不等于独立质量通过。无正式整楼BIM/查看器入口；桌面产品未更新。

## 证据与交接

- [运行目录](D:/Sim-BIM-Agent/runs/sm25-gpt-same-config-rerun-20261012-high)；[最终回执](D:/Sim-BIM-Agent/runs/sm25-gpt-same-config-rerun-20261012-high/receipt.json)；[请求与结算独立审计](D:/Sim-BIM-Agent/cache/sm25-gpt-same-config-rerun-20261012/request-audit-final.json)。
- [行为、装配和产物审计](D:/Sim-BIM-Agent/cache/sm25-gpt-same-config-rerun-20261012/final-candidate-audit-terminal-2340.json)；[大回执原始审计](D:/Sim-BIM-Agent/cache/sm25-gpt-same-config-rerun-20261012/f2-context-stops-summary.json)；[增量缺口证据](D:/Sim-BIM-Agent/cache/sm25-gpt-same-config-rerun-20261012/f2-late-context-summary-event-001666.json)。
- [机器摘要及证据SHA256](results.json)。journal共2340事件，SHA256 `553b8887426456d4f3b7b0a98c28b5cdcc614579a82b56362bb9f202e3fa1936`；不将全部大日志搬入Git。
- [角色用量](D:/Sim-BIM-Agent/runs/sm25-gpt-same-config-rerun-20261012-high/role_accounting.json)、[BIM终态摘要](D:/Sim-BIM-Agent/runs/sm25-gpt-same-config-rerun-20261012-high/bim/summary.json)、[行为时间线](D:/Sim-BIM-Agent/runs/sm25-gpt-same-config-rerun-20261012-high/behaviour/timeline.md)、[CLI终态](D:/Sim-BIM-Agent/cache/sm25-gpt-same-config-rerun-20261012/terminal.json)均已生成。
- 收尾磁盘快照：C盘51.08GiB、D盘155.07GiB可用；未清理运行证据或更新桌面。
