# HANDOFF：Opus 5.5 独立质量调查 → Astra

- 执行：Opus 5.5（claude-opus-5-5，max），2026-09-28 10:25–11:00 UTC；分支 dev/opus-quality-20260928，基准 ceb8b1df。
- 用量与改动：0 次模型/代理/API/DeepSeek 调用；0 处生产、全局文档或历史实验改动；未读凭据或全局设置；未 push/merge。
- 工作树处理：本工作树交付时为空检出（只有稀疏规则），我执行了 `git read-tree -mu HEAD`，并把本目录加入稀疏规则。两者都只影响本工作树。
- 报告：[REPORT.md](REPORT.md)。初判：[initial_findings.md](initial_findings.md)，在读 Astra 记录之前单独提交于 9b859b37。

## 独立确认

1. run57/58/81 的请求文件字节相同（sha256 44ee38d1…），CLI、模型、36 个工具名、图像和参考文本都一致。完整旧树复跑在请求端的控制可信。
2. run72 是 mm/m 单位错误；run81 拓扑正确、墙位只差几厘米；relation 检查只按调用方给的预期自证。以上三点与 Astra 一致。
3. 对象级错误都在该层首份声明中进入，后续候选没有改正（逐候选复评）。
4. sm24 的开口位置从 21/21 降到 17/21、15/21，这组数字属实；但失配只是 7–25 cm 的端点误差，宿主和连接全对。

## 独立反驳/更正

1. **run83“x≈718 的无关线”不成立。** 原图北侧两房之间唯一贯通的竖线在 x=1114/1125（`check_north_divider_run83_2f.md`），原图 x≈718 处没有竖线。模型用的裁切原点是 400、比例 1，裁切内 718 正对应原图 1118。所以是**看对了对象，却混用了裁切坐标，并用“无灰填/无墙厚支撑”判据否掉了它**；尺寸链中 1889/1891 的分点也被误读。修复应针对坐标系和判据，不是“找错了线”。
2. **“sm21 全部 severe”不等于全部退步。** 严格 GT 的 2 cm 容差把参照面选择（墙面还是中线；原图两条尺寸链分别对应两者）判成 severe；sm24/sm25 的好结果在这把尺子下也是 severe。对象级错误实际是 4/12（72、75、83、82）。

## 新增观察（相关性，未证因果）

- 六次好结果都没读 reconstruction/plan_assembly 参考。首建中位 167 s，首建前像素工具 0 次，隔墙按尺寸链或画线中线定位。
- sm21 run69 以后 12 次冷启动中，11 次读了该参考（run80 没读），首建中位 677 s，首建前像素工具中位 14 次，9/12 次按像素或墙面实测定位。字节相同请求的旧树 run81 也属后一类。
- 该参考要求“测双线两侧墙面、用像素剖面、两峰不一定是墙、家具也有边”。
- 反例：run80 没读也切换了；run58 用了 8 次像素工具仍然精确；sm24 run61/62 直接读图仍有尺寸误差。

## 关键未知

- 行为切换的原因：参考文本、服务端漂移或抽样方差，目前无法区分。
- 切换是否跨案例：09-27 07:24 之后没有任何有效的 sm24/sm25 冷启动。
- 新代码是否提高对象级错误率：旧树只有 1 个样本，判定不了。
- 用户级 CLI 配置（未记录、未读）。
- run57 的 src 是否与 468d83f7 逐字节一致。

## 建议的能力包与最小对照（详见 REPORT §6）

1. **P0 评价分层（离线）**：对象拓扑、宿主和连接作为主指标；边界偏差作为连续值，墙厚量级内记为尺寸级；窗高分族。可直接复用 `reevaluate_partitions.py` 的思路。
2. **P1 确定性提示（生产改动，由 Astra 决定）**：
   - (a) 单位合理性拦截：锚点米值 >1000 或外廓 >1 km 时报错。
   - (b) 建层后自动报告“空间内部贯通线”。原型离线结果：命中 75/83/74 的全部漏墙和错位墙；71/71 对人为合并被报出；误报为 sm21 每栋 2 处 L 形桌边，sm24/sm25 为 0。模型是否采纳，需整案验证。
3. **P2 行为 A/B（需用户批准）**：当前树 sm21 两臂各 2 次，一臂保持 reconstruction 现状，另一臂不要求读、且去掉“测双面/像素剖面”段；A 臂再加 1 次 sm24 冷启动。预测与反驳条件见 REPORT。
4. **路线建议**：继续在当前树推进，不整体回旧基线逐包加回（旧树已复现行为切换）。切换到“旧基线逐包”的条件见 REPORT §6。

## 文件与验证

| 文件 | 内容 | 重放 |
|---|---|---|
| survey_runs.py → runs_survey.json/.md | run53–83 请求、回执、动作与评价汇总 | `python3 survey_runs.py` |
| reevaluate_partitions.py → partition_tolerance_reevaluation.json | 未改评价函数的多容差复评（sm21 全部候选） | `PYTHONPATH=<tree> /opt/venv/bin/python3 reevaluate_partitions.py` |
| reevaluate_sm24_sm25.py → sm24_sm25_evaluation.json | sm24/sm25 同法复评，含原图分区与开口位置/宿主计数 | `PYTHONPATH=<tree> /opt/venv/bin/python3 reevaluate_sm24_sm25.py` |
| behavior_profile.py → behavior_table.json、first_declaration_basis.json | 参考读取、首建时刻、像素用量、首份声明依据 | `python3 behavior_profile.py`（需先有上面三个输出） |
| public_actions.py | 公开动作抽取，跳过 thinking | `python3 public_actions.py <run_dir>` |
| check_north_divider.py → check_north_divider_run83_2f.md | run83 二层北侧隔墙像素核查 | `/opt/venv/bin/python3 check_north_divider.py <2f_view.png>` |
| interior_stroke_audit.py / interior_stroke_mutation.py → *.json | P1(b) 原型、真实失败命中与变异灵敏度 | `/opt/venv/bin/python3 interior_stroke_audit.py run57 …` |

- 原文件保持：`git status` 只显示本目录新增文件；`src/`、历史 run 都无 diff。
- 关键输入哈希：
  - 请求 44ee38d1…（57/58/81）
  - run83 流 0e1bd62c…、run75 流 e49599a8…、run81 流 1c85f706…
  - 1f_view ac620916…、2f_view d7cd58d3…（与各 run 的 inputs.json 一致）
  - source_partition.py 09dfebcf…、partition_evidence.py b7f582c8…
- 没有运行 pytest：本次未改生产代码。

## 运行状态

无后台任务；无运行中的模型调用；本目录已按两次提交交回（初判 9b859b37，终稿见随后的提交）。未 push/merge。项目文档与 main 合并由 Astra 负责。
