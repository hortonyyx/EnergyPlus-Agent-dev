# Sonnet5固定与立面标定叠图（09-29）

CLI按用户要求更新至2.1.284；BIM订阅入口及JSON订阅入口将Sonnet角色固定为`claude-sonnet-5`，更新后最小文本调用实际仍为5。见[实测回执](../2026-09-29_sonnet5_pinned_update/receipt.json)。恢复质量后再考虑是否换模，当前不自动采用5.5。

本包给既有`view_elevation_candidate`增加可选`horizontal_anchors`、`z_anchors`、`basis`。各轴两个原像素/世界米锚点；南北水平轴为世界x，东西为世界y，竖向为绝对z，不额外反转朝向。返回干净原图与同坐标的实际源轮廓，复用原图view_id/源投影/不可变叠图记录。只处理轴对齐图，标定和方向由调用者解释，不认证图意、不自动拟合/修源；再次查看修订稿时显式重用原基准。

31项不同的定向检查最终通过，见[验证记录](validation.json)。首次1项测试误设多边形首顶点顺序，已改为完整投影范围断言，生产代码未为此改动；其余30项复用有效结果。首次离线重放整JSON相等断言因保存稿导入的generation.provenance及其摘要变化而失败；已核除这两项外全部源字段严格相同，保留前两份查看记录，未启动模型。

开发者从原图整栋宽/总高端点作标定，独立检查实际投影：[东侧叠图](offline_replay/image_overlays/overlay_003.png)中F1:W7窗顶低11.000009像素；正确F2:W7差约0，南F1:W4差0.191像素，见[南侧叠图](offline_replay/image_overlays/overlay_004.png)。原图、旧稿与离线seed字节未被查看过程改写。开发者标定值/错误位置只留离线检查，未放进拟议工作模型输入；不是自主恢复证明。

## 已准备的一次节点回归，尚未批准或执行

- sm21六原PNG与run88/candidate_01原proposal，当前main工具；不导入旧claim、具体错误/目标数值、开发标定或GT。
- 单`claude-sonnet-5` / medium，3000秒、24候选，1主调用；CLI禁review_detail，0续跑/自动重试/局部模型/付费回退。
- 明确是保存稿复核，不是冷启动或稳定性验证；CLI/工具/任务范围均有变化，不作单变量因果归因。
- 检查实际自主标定/对应/修订行为、全部原图门窗及高度、房间/隔墙/宿主/连接保持、源重放与可查看交付。未采用叠图、未改错或旧宽容差通过都不自动算恢复。
- [冻结条件](frozen.json)绑定43实现/执行文件、CLI版本、原图/原proposal、提示和本脚本；[预检](preflight.json)通过真实MCP并在订阅进程边界截断，0 BIM模型调用。

待用户明确批准后，保存批准原话及本冻结文件摘要到approval.json，再执行`PYTHONPATH=. python AI_agent/logs/experiments/2026-09-29_calibrated_elevation_review/batch.py run`。输出为独立run89，已有目录拒绝覆盖/重试；模型真实回执异常即保存结束，不启动下一批。
