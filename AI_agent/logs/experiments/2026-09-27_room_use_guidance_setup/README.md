# 用途提醒组织方式：增量修订与待批准四次回归

状态：生产修订、局部检查、历史重放、实际MCP对照与运行入口已准备，**尚未批准或启动新的模型回归**。本节点是当前能力上的增量优化，不是恢复468d83f7旧运行时。名称、合理用途选择、图证与编辑能力继续保留。

## 具体改动与假设

修改前基点a591ef4d。此前每次保存楼层、装配或修订候选，room_use_review都会追加一段检查房间用途的操作指令；常驻GUIDE也详细重复用途复核步骤。本次只调整提醒组织：

- 常驻用途段缩短，保留实体空间/隔墙/门窗优先、合理表内用途、标明推断、unknown后备、交付前复核及既有操作入口。详细规则继续由room_types/edits按需提供。完整GUIDE字符数18607→17736，减少871字符；不是模型token数。
- 自动保存候选继续返回用途统计、缺项ID、未知ID及解释，只省略next_action。显式inspect_candidate、finish_bim/交付和续查拿到的完整用途反馈保持原样。没有新增阶段状态机、自动改用途或硬性建模顺序，也未改坐标/几何/额度。

假设是减少局部几何修订过程中反复出现的次要行动指令，同时保留交付前用途补全。本次没有证明原提醒造成退步，更未证明缩短后能提高质量。先前仅缩短新增GUIDE段落的run72失败仍有效；本次控制的是当前用途提醒组织这一组增量，不能拆分“常驻文字”和“自动回执行动建议”的独立贡献。

## 离线验证

- 18项不同建模/用途/交付压缩/高度确认/续查相关检查通过。真实stdio验证自动保存无行动段，但缺项统计保持，显式查看/交付有完整行动；用途编辑后物理几何和命名保持。
- 15份真实历史源模型：完整用途反馈与冻结修前函数逐项相同；自动保存反馈只少next_action，减少82或386个JSON字符（取决于是否仍有缺项）。原文件哈希保持，不把离线重放当自主恢复。
- 两种条件真实MCP注册均为相同39工具，输入schema/说明/按需参考完全相同；同一合成输入产出的完整源BIM精确相同，显式查看/交付反馈精确相同。实际激活GUIDE/函数哈希已核。
- 4个拟运行条件均执行到真实输入冻结、40生产文件和实验文件快照保存处，在订阅边界主动停止；Popen被拦截，0模型调用，退出恢复入口和GUIDE。
- 实际回执解析器以run69/71–74归档只读验证。仅统计可解析的用途反馈，不能把未解析/错误/截断的回执当作“没有送达”；报告同时列无法核明的调用，使用数是已核明下界。
- 新离线节点报告另补运行目录/记录提交不应被误当生成条件差异的检查；14项报告检查通过。此修改不进入生成器或本次40文件生产快照。

对应定向检查命令：

```bash
python -m pytest -q -n 0 tests/test_bim_agent_tools.py tests/test_bim_delivery_reply.py tests/test_proposal_edits.py tests/test_source_proposal.py tests/test_bim_claim_state.py tests/test_bim_continuation.py -k 'room_use or role or use_edit or large_nested_evidence or extreme_notes or continuation'
python -m pytest -q -n 0 tests/test_bim_regression_report.py
```

证据：[预检](preflight.json)、[实际历史回执解析](historical_exposure_check.json)、[冻结提案](proposed_batch.json)。没有新模型用量；未改渲染代码，不重复浏览器全量。后续真实新交付仍检查浏览器。

## 提请的回归范围

**sm21、sm24各修改前/后1次，共4次Claude订阅Sonnet/medium主调用。** 每次六/五原PNG冷启动，3000秒、24候选、0续查、0子模型、0自动重试。最多两路并行；每次时限50分钟，四次时限之和200分钟，不等于实际墙钟耗时。沿用各例旧任务、原参照/原容差，生成侧无旧BIM、量测、GT、数量/坐标/高度答案或中途提示。

| 案例 | before：本次修前提醒 | after：本次修后提醒 |
| --- | --- | --- |
| sm21双层 | run75 | run76 |
| sm24单层非矩形空间 | run77 | run78 |

before仅使用冻结a591ef4d的GUIDE与旧room_use_review反馈函数；after使用当前GUIDE与按调用位置决定是否附行动段的反馈。其他能力和图像、方法、工具、模型档位、额度相同。不是把整个Agent退回旧版，也不是删掉用途功能。每组一次仅作初步跨例筛查；不宣称稳定或历史根因，不自动加入sm25或重复采样。

生成后核两类结果：①改动确实暴露（实际主请求GUIDE、自动保存/显式查看/交付回执）；②整案空间/分区、门窗存在/位置/宿主/连通、窗型高度与合理用途依据，以及源/显示/装配/原图运输和离线查看器。新增能力触发不代表正确理解；严格尺寸severe和真正错拆漏门分别解释。保留全部结果，包括中断、缺评价或错楼层；不以最佳一次/旧稿修复替代冷启动成绩。

## 入口

以下prepare/preflight无模型调用：

```bash
python -m AI_agent.logs.experiments.2026-09-27_room_use_guidance_setup.run_batch prepare
python -m AI_agent.logs.experiments.2026-09-27_room_use_guidance_setup.preflight
```

下列run命令仅在用户批准具体批次后执行；拒绝覆盖已有目录，条件漂移会拒绝执行：

```bash
python -m AI_agent.logs.experiments.2026-09-27_room_use_guidance_setup.run_batch run --case sm21 --variant before
python -m AI_agent.logs.experiments.2026-09-27_room_use_guidance_setup.run_batch run --case sm21 --variant after
python -m AI_agent.logs.experiments.2026-09-27_room_use_guidance_setup.run_batch run --case sm24 --variant before
python -m AI_agent.logs.experiments.2026-09-27_room_use_guidance_setup.run_batch run --case sm24 --variant after
```

完成后执行`python -m AI_agent.logs.experiments.2026-09-27_room_use_guidance_setup.audit_run RUN_PATH`，复用固定原图/GT审计，核实际配置、生产/实验快照与提醒回执。已有评价器若因错误楼层或缺交付无法评分，原始失败保留、缺项另列，不自动重抽。浏览器入口沿用`2026-09-27_sm24_room_types_setup.browser_check`（已有Playwright临时环境），适用单/双层实际交付。各结果加入离线节点报告并补原图高度/用途语义复核，评价信息不回填生成侧。
