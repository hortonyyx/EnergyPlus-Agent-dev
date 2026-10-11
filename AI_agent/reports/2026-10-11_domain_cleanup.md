# 2026-10-11：当前 domain 整理与讨论沉淀

用户要求保存本轮共识、清理旧 0–5 阶段与 prompt/skill 表述，随后明确整理出当前干净的 domain。照片经生成 mesh 的路线与细度调整仍留待讨论。本轮只做组织、入口、资源和引用重构，不执行模型测试或实现未定方案。

## 当前入口

- [架构](../design/architecture.md)：runtime/domain 分工及当前能力边界。
- [源码导航](../../src/agent/README.md)：BIM rules、kernel、tools、methods、roles、guidance 的实际位置。
- [继承关系](../design/domain_lineage.md)：旧能力哪些复用、哪些转化、哪些后来新增。
- [模型与输入策略](../project/model_and_input_strategy.md)：已确定方向及照片/细度待讨论项。
- [运行说明](../workflow/run_case.md)：现行配置、预检、运行和报告入口。

## 实际变更

1. Work model 政策改为国模优先、允许组合；先稳定交付和时间可控，再降低成本、接近本地部署，不再以固定 27B/Flash/Sonnet 档位限制项目。GPT-6 Sol 标杆仍待确定案例、模式、配置与预算，没有启动。
2. 三条研究线统一解释为相对于目标的信息充分程度。内部按任务能力组织；图纸继续验证 harness，textured mesh 先原型收敛再整合与尝试混合。照片路线、一层一块和细度自适应没有变成默认策略。
3. `skills/intake_pipeline` 的 19 个文档移至 `src/agent/legacy/intake`，子目录按 reading/correction/modelling/split_pairing/mep/intakeoutput 命名。旧 `pipeline.py`、`graph.py` 移至同一 legacy 包，现有消费者直接更新引用，没有新增转发壳。
4. 资源定位集中于 `legacy/resources.py`。同步旧读图隔离副本、启动指针、校正/物性加载、诊断 rubric 和基线资源哈希。评判 rubric 仍不进入读图隔离区；不支持的 rubric 返回空值，避免生成不存在的路径。
5. 发布选择不再收顶层 skills，实际需要的 legacy 资源随 src 发布。当前产品入口不加载旧 graph；历史公共 `src.agent.build_graph` 显式请求仍可用。历史产物 stage ID、目录、provenance 字段及旧版本登记不追改。
6. 重写当前目标、模型约定、角色、运行说明、源 BIM 和评价说明，清理过时“下一步”和固定开发阶段含义。长篇历史原文保全到外部快照及 Git；当前入口不再指向旧运行 prompt。

共享几何、校验、旧 EnergyPlus 节点/工具和数据类型保留实际依赖；`reading/correction/execution` 的路径名不代表当前阶段流程。本轮没有为六类职责新增六层空包装，也没有重新设计工作模型提示、几何规则或动态调度器。

## 验证

| 范围 | 版本 | 结果 | 耗时 | 模型请求 |
|---|---|---|---|---|
| 10 个定向模块：产品入口/发布、两模式 guidance、基线、校正、旧管线消费与 runner | runtime v7 / domain v65 内容 | 68 通过，0 失败、0 跳过；12 条合成基线缺省警告 | 12.35 s | 0 |
| 2 个历史模块及 5 个隔离节点：intake、reading schema、资源白名单、示例/启动指针、写保护 | 同上 | 29 通过，0 失败、0 跳过 | 11.58 s | 0 |
| 实际旧校正/MEP prompt 构造和 rubric 加载 | 同上 | 两类 prompt、两个 rubric 均成功；未调用模型 | 约 3 s | 0 |
| 版本登记、文件核验和模型可见指纹 | runtime v7 / domain v65 | 仅 domain 变化；7 个模式的工具/guidance/任务模板指纹与 v64 全部相同 | 未单计 | 0 |
| Python 语法、变更 Markdown 链接、Git diff | 同上 | 72 个 Python 文件可解析；最终 50 页/176 个本地链接无缺失；diff 无错误 | 未单计 | 0 |

测试缓存分别为：

- `D:/Sim-BIM-Agent/cache/pytest/domain-cleanup-20261011/a1aab2dbd7ba/results.xml`
- `D:/Sim-BIM-Agent/cache/pytest/domain-cleanup-20261011/d6af3d0487b5/results.xml`

离线 egress gate 保持开启，未发生模型服务调用。资源加载探针初次使用空目录，被既有“无 reading JSON”检查拒绝；补上独立合成示例后通过，未为此放宽生产检查。版本登记覆盖 runtime 42 文件、domain 427 文件；旧版本记录不修改。

## 保全与边界

清理基准为 `3e917b8ecb0c3c8757edf590fcf9cc41a44c9999`。管理文档及阶段资源共 74 文件、720,489 字节已复制到 `D:/Sim-BIM-Agent/archive/architecture-cleanup-20261011-3e917b8e` 并逐项 SHA-256 核对，详见 [归档索引](archive-index.md)。没有删除历史案例、运行或 GT，也没有重写 Git 历史。

本轮验证说明资源迁移、调用边界和当前模型可见接口保持；不证明新模型更合适、sm25 质量恢复、照片/mesh 稳定生成或推断细度合理。未做新的真实 BIM 生成、仿真或模型研究。代码整理阶段尚未部署桌面；随后应用户追问补交付到 `Sim BIM Agent v65`，原 v64 目录保留，详见 [桌面发布记录](2026-10-11_desktop_domain65.md)。各安装的准确版本以自身 release-manifest 为准。

实现提交 `bcb40f194465704b9571910810d9ca38a7fe5f62` 已正常推送 origin/main；本报告的最终核验数字随后单独收尾。空的顶层 skills 目录已移除，没有删除未知文件。

下一步仍是讨论 GPT-6 Sol 独立标杆与候选模型实测方案，继续收敛图纸 domain 和 textured mesh 方法；照片/细度单独讨论。本轮不创建新工作树。收尾磁盘读数约 C 52.09 GiB、D 171.45 GiB，属于本轮时点快照。
