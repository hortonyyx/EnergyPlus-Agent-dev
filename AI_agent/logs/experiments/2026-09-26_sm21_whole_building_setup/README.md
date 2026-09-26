# sm21 六原图整栋回归

沿用 sm24/run55–56 的逐字相同任务范围，仅替换为 sm21 六张原 PNG（两平面、四立面）。工作模型通过现有 Claude 订阅使用 Sonnet/medium，单主调用，无开发或产品子代理；不输入旧 BIM、旧标定、建筑说明 JSON、GT、局部低档答案或开发核验参照。原图到声明、确定性分区编译、逐层装配、高度观察及候选交付由工作模型组织；开发不在运行中介入。

生产基准 `b5dbf156`，33 项实现 hash 留在 run/inputs.json。相比 sm24/run55–56，只有 `bim_agent_guidance.py`、`bim_claims.py` 两项生产 hash 变化，对应上一程的严格对象类型错误提示；不把跨案例表现变化当作该提示的因果验证。

`audit_original.py --reference-only` 在生成期间、查看候选前保存独立原图参照：首层复用已有原图观察，二层由开发查看原图和原像素扫描补齐全部门窗。该文件与 GT 都不进入生成。两层按实际楼层高度顺序对应，空间内部点和门窗端点分别核位置、宿主和门连接；完整房形另看未改容差的 GT 分区诊断。

## 复现命令

在仓库根执行，生成不可覆盖既有 run；要重做须另建独立 run 并保持旧证据。事后核验须保留 manifest 所列生产实现。

```bash
python -m AI_agent.logs.experiments.2026-09-26_sm21_whole_building_setup.run_cold
python -m AI_agent.logs.experiments.2026-09-26_sm21_whole_building_setup.audit_run
python -m AI_agent.logs.experiments.2026-09-26_sm21_whole_building_setup.audit_original
python -m AI_agent.logs.experiments.2026-09-26_sm21_whole_building_setup.audit_transport
PLAYWRIGHT_BROWSERS_PATH=/tmp/ep-bim-browser-qa/browsers /tmp/ep-bim-browser-qa/bin/python AI_agent/logs/experiments/2026-09-26_sm25_height_review_setup/browser_check.py AI_agent/logs/experiments/2026-09-26_sm21_whole_building_claude_run57
```

图像运输与真实最终工具回执单独检查；离线浏览器只验源 hash、两层选择、旋转与页面错误，不等于图纸保真或用户验收。内门高度允许明确假设，但门的存在、位置和连接不能因此免验。

## 实跑结果

[run57 交付页](../2026-09-26_sm21_whole_building_claude_run57/delivery.html)，最终 `candidate_04`：两层14空间、15窗、14门/14连接。六原图无旧答案，377.66秒正常完成；实际 `claude-sonnet-5`/medium，1主调用、无子模型/回退，CLI估算 $1.232221（非订阅账单、不含开发用量）。

- 原图两层29门窗位置/宿主全部对应，14门连接对应，无未配对项；完整两走廊、首层六侧房及二层六侧房保留。参照的端点6cm、内墙线7cm/外墙代表面16cm容差沿用原首层观察，未为本次结果放宽。
- 既有严格2cm GT分区 `minor`，14/14空间对应，无拓扑发现；最大边界差0.002841m，最小IoU0.9982415。是与既有规整参照的残差，不代表原图达毫米测量精度。F1底0m/高3m，F2底3m/高3.6m与参照一致。
- sm21是旧版GT；新增仅评测侧的旧格式外开口参数诊断，保持GT/生产代码和judge配置不变。17外开口位置/宽/高全部容差内，最大高度端点差约2.48cm。旧版没有开口宿主字段，宿主由独立原图另核，不冒充typed v3宿主评分；既有窗评价也为15/15 complete（within_tol是另一互斥档，不把其0误读成失败）。
- 10条当前图像高度claim实际应用于17外开口。candidate_03→04只调整外开口Z和依据/修订记录；楼层、空间、边界、连接记录及全部开口XY/类型/宿主严格保持，12内门高度仍为各层上2.1m假设。高度小数来自像素换算，不是精度声明。
- 模型抽查6对当前空间关系，均一致；6张原图直接查看。未调用专门源立面渲染、完整墙路径支持或逐开口全面回查，不将事后开发评价冒充模型全范围自检。
- 无旧的“高度待立面检查”备注；逐层装配产生的重复假设/未决文本仍保留，模型明确承认未执行replace_note。本轮没有再调模型只为去重，也没有人工改写生成结果。
- 原图/33生产hash、逐层装配和最终源/显示精确重放通过；18张实际回执图片可解码，finish实际9020字符直接JSON、无脱离工具的大文件提示。零实际工具错误，但不同案例不足以证明类型提示修复的因果收益。
- 离线浏览器源hash、两层选择的不同画面、旋转、交付说明和无页面/外网错误通过。生成原流已验证无损gzip归档。无用户验收或EP验证。

审计脚本开发时遇到两项可恢复问题：原图诊断与GT评价首次共用新建目录，改为evaluation/gt隔离；继承脚本只接受typed v3，随后补旧格式参数诊断。都发生在模型退出后，未增加模型调用或修改生产结果。旧格式诊断另以真实产物内存副本做高度+0.5m和移除一个外开口的负向控制，均检出；不改原GT/原候选。

追加核验：

```bash
python -m AI_agent.logs.experiments.2026-09-26_sm21_whole_building_setup.verify_evidence
```

本程没有生产代码变更，不重复上一程24项claim测试或全量pytest。下一项冻结同范围做sm21独立重复，确认三例范围与未核内容后，再按实际缺口试功能角色选模/并发。
