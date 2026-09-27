# sm24：功能选表、证据保留与自主复核

[对照查看入口](index.html) · [完整数据](comparison.json) · [独立语义核查](semantic_review.md) · [实现与测试](implementation.json)

本轮Astra独立开发，4次Claude既有订阅Sonnet调用；全部正常结束，无开发／产品子代理、DeepSeek、付费API或仿真。GT、原图手工参照、[生成前功能观察](semantic_reference.md)均留在评测侧；没有中途干预或提供用途答案。

| 运行 | 性质与结果 | 局限 |
|---|---|---|
| [run59](../2026-09-27_sm24_room_types_claude_run59/delivery.html) | 五原图冷启动，8空间／11窗／10门；位置21/21，宿主21/21、连接10/10；14外开口参数及高度claim关联 | 未读功能表，全unknown；原图分区minor、严格GT分区severe |
| [run60](../2026-09-27_sm24_room_types_recovery_claude_run60/delivery.html) | 仅功能恢复，实际读表并用局部操作写8项推断；原run59物理几何及关系全部保持；5种颜色及依据可点看 | 北侧两家具解释存争议；不是自主整案，前次高度claims未随proposal导入 |
| [run61](../2026-09-27_sm24_room_types_cold_claude_run61/delivery.html) | 无旧稿，测试新指引／局部工具；8空间／21宿主／10连接，14外开口参数及图像关联 | 仍未读表，全unknown；位置17/21，原图和严格GT分区severe |
| [run62](../2026-09-27_sm24_room_types_feedback_claude_run62/delivery.html) | 无旧稿，增加实际候选缺项反馈；8空间／21宿主／10连接，14外开口参数对应 | 反馈已送达仍未处理；位置15/21，最大端点差约24.76cm；21高度均无本次claim关联，原图和严格GT分区severe |

三次冷启动使用完全相同的五PNG与任务正文，但实现逐步变化，不是冻结重复。工作模型实际均claude-sonnet-5/medium，时限冷启动3000秒、限定恢复1800秒，未以短限时抢交付。实际145.17／44.05／153.30／121.13秒，共463.65秒；CLI估算合计$1.9594994为订阅回执估算，非账单，不含开发用量。

## 实现与验证

`4de15e27`：草稿房间source_refs／assumptions贯通源空间；新set_space_role只改功能与role_evidence，区分observed/inferred/unknown，保留原几何、来源、关系及旧修订记录。HTML显示功能依据／假设，名字与颜色由固定目录生成。房间用途证据不扩散为墙面实测依据。

`26254bde`：构建／检查／交付返回当前room_use_review，区分已说明未知与未记录依据，按源hash绑定，返回上限20个ID及分页提示；不供用途答案、不认证语义、不阻止有用的部分交付。`9886f062`补大回执保留检查。136项不同离线测试通过，详细组别见implementation.json。

四次源／显示重放、原图／GT诊断及浏览器已完成；运行流无损gzip归档。run59源重放在7dcb1d0b生产实现下完成；run60/61在4de15e27下完成；run62在26254bde下完成。后两次工具改动后不要拿当前hash去伪装旧实现重放。run59额外记录原manifest漏列的source_model.py/schema.py摘要；新入口已将二者纳入manifest。

## 复现入口

生成脚本依次为run_cold.py、run_recovery.py、run_new_cold.py、run_feedback_cold.py。使用`/opt/venv/bin/python -m AI_agent.logs.experiments.2026-09-27_sm24_room_types_setup.<模块名>`，重新实验必须改为新输出目录，不覆盖本轮。对应frozen_method文件保存实际输入／任务和人为参与范围。

生成后冷启动沿用09-26_sm24_whole_building_setup.audit_run，传本轮run与对应frozen文件；恢复用audit_recovery.py。浏览器：

```bash
PLAYWRIGHT_BROWSERS_PATH=/tmp/ep-bim-browser-qa/browsers /tmp/ep-bim-browser-qa/bin/python -m AI_agent.logs.experiments.2026-09-27_sm24_room_types_setup.browser_check RUN
```

全部评价完成后summarize.py汇总四次真实回执和产物。不改变生成结果、原图参照或容差。本节点下一项是让总Agent根据当前缺项选择并执行有界续查动作，功能／高度都作为检验对象；不再用同型原图重抽或加严unknown门槛代替自主任务推进。
