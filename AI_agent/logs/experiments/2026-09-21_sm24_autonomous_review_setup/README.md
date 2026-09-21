# sm24 少指示自主复核/恢复实验

本批为用户09-21“继续推吧”后的首个增量。生产代码不变，均使用Claude现有订阅Sonnet、medium、1800秒上限；两个独立run不共享新观察/输出，无GT或开发指示错处进入运行。

| 运行 | 输入 | 检验内容 |
|---|---|---|
| `2026-09-21_sm24_autonomous_review_run05` | 原五图、原声明、09-20/run04/candidate_02的proposal | 已修候选是否保留，能否自主选择其余问题并核实依据 |
| `2026-09-21_sm24_autonomous_recovery_run06` | 同一原五图/原声明、09-20/run01/draft_003未验证墙网 | 已知失败起点能否在无具体错处提示时自行定位与修复 |

两份scope仅因输入为candidate/draft而措辞不同，均为整楼原图复核、证据驱动修订、区分本轮核验/继承说法/未核范围。run06选用上一会话run02的同一恢复起点；新通用目标与旧限定目标有差异，不将两次结果当严格因果消融。run05与run06的起点也不同，不能直接以用时或最终质量判断哪种表示更好。

这两次都是恢复实验，不算独立原图冷启动或稳定性通过。run05即使保留正确候选也不能独自证明能发现严重错误，因此另设run06。生成后才做源/显示重放、修订链和新旧对象比较、真实工具/图像运输、原图视觉及独立GT评价。各run原始产物保留，不覆盖旧实验，不按GT回写生成几何。

入口为本目录`launch.py`与`launch_failed_plan.py`，均拒绝覆盖已存在的run。准确命令、scope和代码提交记于各自launch JSON；22份生产实现散列由实验入口保存到run的inputs.json。本目录外层日志仅保存调度输出，模型原始输入、工具轨迹及结果在各run内。

两run已完成及核验：run05[结果](../2026-09-21_sm24_autonomous_review_run05/README.md)360.92秒保留seed，无几何改善；run06[结果](../2026-09-21_sm24_autonomous_recovery_run06/README.md)1096.95秒仍错并，并误改门/拆窗，不采用。两份源/显示/图像/离线查看通过，不等于自主保真通过。另完成[双方向开发探针](../2026-09-21_sm24_facade_direction_probe/index.html)，不注入本批模型。全部调用已结束，本轮无DeepSeek、付费API、EP或部分推理。

## 本批核验入口

生成结束后用`audit_review.py --run <新run>`检查实际工具、候选链和对象变化；`verify_completed_run.py --run <新run> --original-dir case_tests/e2e_tests/sm24_anchor/case_data`复用已有源/显示/图像验证并分别校验seed导入、未验证plan恢复、新候选生成来源和实现散列。输出拒绝覆盖；无需重复全量pytest。这些是实验审计脚本，不是新生产验收门槛。

浏览器复用已存在的环境和旧检查：`PLAYWRIGHT_BROWSERS_PATH=/tmp/ep-bim-browser-qa/browsers /tmp/ep-bim-browser-qa/bin/python AI_agent/logs/experiments/2026-09-21_sm24_autonomous_review_setup/verify_browser.py --run <新run>`。若此临时环境在其他机器不存在，需使用具备Playwright/Chromium的现有环境；不把默认Python无浏览器包误报为候选损坏。
