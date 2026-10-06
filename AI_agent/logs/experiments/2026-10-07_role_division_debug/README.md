# 分工整案调试（10-07，Opus）

**目的：** 接 [10-06 sm24 分工整案调试](../2026-10-06_role_division_sm24_debug/README.md)。先复跑 sm24（run4）验证 D1g（坐标方向固定、建层前定标高、写高度一次成稿、对位编号唯一、并发 8）；再做两层楼的 sm25、sm21。这是开发调试，不是报批的三例对照；对照仍需用户批准。

**条件：** 配置 [role_division_debug.json](role_division_debug.json)，由 10-06 调试配置复制，只改批次名、输出路径、版本说明，并把同时读图员上限写成 8（用户 10-06 定的新默认）。三个角色都用 GLM 订阅智谱 Anthropic 兼容线路 `glm-5.3-flash`，medium，输出上限 32000；保护线 3 小时、400 次请求、800 次工具调用、3000 万 token，不以时限考核。输入只有原图。Paratera 0，DeepSeek 0。用 `Start-Process` 脱离会话启动，启动脚本与日志在 `AI_agent/archive/local_backup/role_debug/`。

## sm24 run4（Agent `t1-20261006-d1g.1`，10-07 00:44 启动）

- 0.8 分钟：调度员第一次派工把目标写成 `plan/F1`、`elevation/North`，整批被拒（要求 `F1`、`North`）；改写后五个读图任务同时开始。已列入 D1h 的 E 项（目标写法宽容）。
