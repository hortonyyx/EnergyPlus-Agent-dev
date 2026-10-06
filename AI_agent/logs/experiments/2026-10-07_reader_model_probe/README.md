# 读图员换模型摸底（10-07，Opus）

**目的：** 分工路线第 ⑥ 步“逐角色换 4、5 档”的第一份画像：只跑读图员（sm24 一层平面＋四个立面，同时开始），不跑调度员与整案，看候选模型在读图员岗位上能否自己交付、读得准不准、花多少。用户 10-07 再批 Paratera 测试额度 50 元（“你按需取用”），本实验从中支出。

**条件：** [run_probe.py](run_probe.py)。原图与 D1b 小题相同（`2026-10-01_opus_dev_sm24/images`），目标写法规范（`F1`、`North/F1` 等），说明为简短的同一套；读图员额度用运行时默认值（平面 40 次请求、立面 16 次）；同时最多 8 个读图员。线路 Paratera，`enable_thinking=true`、温度 0.7、输出上限 16,384（与 10-05 的 27B 单模型同参数）。请求前按本次估算花费检查，达到上限（默认 8 元）就不再发新请求。参照答案只在读图员结束后用于打分（D1-A 的 sm24 参照与严格评分器），从不给读图员。从跑整案的工作树（`EnergyPlus-Agent-worktrees/runs-d1g`，主线 `fb97cd48`，Agent `t1-20261007-d1g.3`）运行，原始目录在该工作树的 `AI_agent/archive/local_backup/reader_model_probe/`。

**对照：** 同一批读图任务在 GLM 订阅 `glm-5.3-flash` 上的表现，取 [平面读图员实测](../2026-10-06_plan_reader_probe/README.md) run3 与 [10-07 分工调试](../2026-10-07_role_division_debug/README.md) 的读图员部分。

## qwen27b_r1（Qwen3.8-27B，10-07 02:06 启动）

进行中。
