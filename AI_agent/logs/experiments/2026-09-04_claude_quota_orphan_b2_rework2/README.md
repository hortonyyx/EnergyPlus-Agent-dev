# 孤儿件 · B2 返工 2（Claude 施工席撞**月度**额度上限）

- **日期**：2026-09-04 · **席位**：Claude 家族施工席 · **工作树**：`/tmp/b2_rework2_claude`（分支 `wt/09.04g_b2_rework2`，基点 `a45f778c`）
- **任务书**：[`2026-09-04g_B2_rework2`](../../reviews/request/2026-09-04g_B2_rework2.md)
- **死法**：席位日志**全文只有一行** —— `You've hit your monthly spend limit`。
  ⚠️ 是**月度**上限，不是 5 小时窗口 ⇒ **Claude 家族施工席在额度恢复前发不出去**。
- **留下的东西**：`src/agent/correction/multifloor.py` **未提交** 315+/139-（`git diff --numstat` 原文）。
  ⛔ 一笔提交都没有（任务书写了「必须分段提交」，它没走到第一笔）。

## ⛔⛔ 这份东西是【线索】，不是【证据】

- **未提交 · 未跑测 · 未过审**，且**自相矛盾**：模块 docstring 里写「`run_correction` 已不再收裸 z」，
  而 `git status` 显示**只有 `multifloor.py` 一个文件被改过**，`src/agent/pipeline.py` **一行没动**
  ⇒ 它描述的形态**有一半没实现**（本项目已知病族：[[design-doc-described-what-code-never-implemented]]）。
- ⇒ **重派时一律要求「重新实现」**；复用这里的任何一段，**必须自己重新论证 + 自己补锁**。

## 主控点名的可疑处（⛔ 不代判，交给下一个施工方自己核）

1. **方向看起来是对的**：它走的是任务书 §〇③ 的出路 (a) —— 引入 `_ValidatedFloorLadder`
   作为装配边界的唯一入参，唯一铸造者是先跑冻结字节门的 `derive_floor_ladder`，
   并用一个从不导出的模块私有 `_LADDER_SEAL` 挡住公开 API 铸造。
2. **⚠️ 没实现的那一半**：`pipeline.py` 零改动 ⇒ 复核方点名的旧生产面
   （`run_correction` 的 `evidence_chain_z_floor_m` / `evidence_chain_ceiling_height_m`，`pipeline.py:1366-1367`）
   **原样还在**。docstring 却已经写成「已经没有了」。
3. **⚠️ `_LADDER_SEAL` 这类「私有哨兵」本身要被质疑一次**：它是不是又一个「表面」？
   —— 私有名在 Python 里不是访问控制，若某个公开函数会把 seal 传出去/返回带 seal 的对象，
   这条路就又回来了。**下一个施工方必须自己重造复核方那条公开 API 路径**，⛔ 不许照抄这里的论证。
4. **B-3（footprint 错判）在这份 WIP 里没看到动过** —— 任务书两条阻断它只碰了一条。

## 文件

- `multifloor_wip.diff` —— `git diff` 原文（549 行）
- `multifloor_wip.py` —— 死时的文件全文（528 行）

⭐ 工作树已 `git checkout --` 复原到 `a45f778c`，⛔ 未把这份 WIP 提交进任何分支。
