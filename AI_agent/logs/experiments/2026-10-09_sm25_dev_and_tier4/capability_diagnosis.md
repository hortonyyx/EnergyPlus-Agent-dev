# sm25 两阶段能力诊断

两阶段都完成整案。第一轮 Sol 用时 22:33、无实质拓扑问题；第二轮重工后的 candidate_10 为 29/29 spaces、61/61 openings/hosts、30/30 connections、34/34 heights，边界分档 20/2/7/0、沿墙 57/4/0/0。严格位置阈值的 3 项 false 已核实为内墙横向偏差约 14 cm，宿主与连接正确。第一轮可写 Python/脚本，第二轮 reader 受限，模型、权限和组织方式同时变化，不能据此直接比较档位。

| 层面 | 证据与判断 |
|---|---|
| 机械能力 | kernel 已有 pixel→world、ink/dimension alignment、junction regularization 与严格编译；坐标、吸附、宿主和连通检查较稳定，但不能判断原图对象是否漏读。 |
| 模型能力 | F1 在第 6 次提醒已存在时仍做 48 次 profile 才试建；F2 首次误用相对 z；东立面读出 0.19 m 门底后又被落地假设覆盖。观察收敛、坐标语义和证据优先级仍依赖模型。 |
| 接口/干预 | 三个 plan 任务均有 `notes.item` 错误，F1 重工另有 add-operation 字段错误。assembler 抓到漏门；bounded rework 只加 D15、只改东门 D1，说明定向机制有效，也说明最终质量包含人工发现问题的贡献。 |

源码确认第 6 次观察提醒、`trial_id=latest`、自动 evidence、像素规整和限定 `rework_targets` 均已存在，不再重复增加同类提示、角色或默认硬锁。

后续优先实验：

1. **同权限对照**：同一模型、图片、预算、工具白名单及脚本权限，只改变单体/分工；比较首 trial 时间、profile 数、返工和共同评价。
2. **简化接口**：工具返回可选 canonical object refs，并给 add-operation 单一合法模板或在 admission 归一化冗余字段；A/B 比较格式重试与 token，不改几何规则。
3. **减少人工依赖**：将现有跨立面 opening mismatch 和“观测值被假设覆盖”检查前置到 reader 提交后，自动生成现有 bounded-rework issue；比较人工注入数、局部改动范围和最终误差，不新增 reader。
