---
name: sm21-dualmodel-round-2026-06-21
description: sm21 双模型识图轮(2026-06-21) GPT-5.4 干净/Sonnet 0/2 + 主问题根因 + 下轮 backlog
metadata: 
  node_type: memory
  type: project
  originSessionId: 2ee0e63e-a274-4690-a06a-829360d44eb7
---

2026-06-21 sm21_anchor 双模型识图轮（judge-in-the-loop 真跑）。三个 run 落在 `case_tests/e2e_tests/sm21_anchor/`：

- **run_2026-06-20_gpt54_reading**（GPT-5.4 识图）= ✅ clean，14区/112面/15窗，EP 0 severe/6 warn。
- **run_2026-06-20_sonnet_reading**（Sonnet#1）= ❌ J1 severe 阻塞：校正 16 区（南排各多切1，把外墙门窗尺寸刻度当内墙）。
- **run_2026-06-21_sonnet_reading_retry**（Sonnet#2 盲重试）= ❌ J0 severe 阻塞：门当窗(South8/West2) + 平面过切更乱。**Sonnet 0/2，系统性弱点=分不清内隔墙 vs 房内尺寸刻度/门**。

**judge-in-the-loop 验证成功**：双向都灵、每个阻塞都能定位根因+归对阶段（root=0_reading manual→human_redraw，没误伤 DeepSeek 校正）。

**主问题根因（用户点的，已坐实+2026-06-21 修正）= GPT 这版 112面 vs 06-16 Opus 100面**：GPT-5.4 把两层走廊读得不一样宽（F1 y[3.12,4.88] / F2 y[3.2,4.8]，差~10cm）→ 碎面。**注：原记「各层独立 snap」有误**——轴线图本就全楼共享，真因=同层/跨层共用 `axis_jitter_tol=0.05`、跨层差恰 0.10 卡容差缝（不聚类 + sliver `<0.10` 严格不并）→ 两轴幸存。**已修（`6.21_CrossFloorWallAlign`）**：`_reconcile_cross_floor` provenance-aware 跨层对齐，sm21 112→100、走廊对齐 y[3.15,4.85]。详 [[sm21-dualmodel-backlog]] [[codex-execution-protocol]]。

**接入打通**：GPT-5.4/codex 看图只能走 **CLI `codex exec -i <图> --sandbox read-only`**（MCP 路 view_image 走 bwrap、本机内核禁 userns、救不了）；坑=后台进程 stdin 不 EOF 致 codex 死等干耗(额度不掉)，**`echo "" | codex …` 喂 EOF 修复**。立面 rect 我 prompt 给错字段(p1/p2)、需 x_range_m/y_range_m。

**本轮已改代码（待 commit）**：run_stage S5 装配缺 IDD 初始化 → 加 `ensure_schema_initialized()`（备份 backup/scripts_history/2026-06-21_run_stage_idd_init/）。

下轮 backlog 见 [[sm21-dualmodel-backlog]]。关联 [[sm21-review-backlog]] [[cad-to-gt-direction]] [[per-stage-validation-judge-architecture]]。
