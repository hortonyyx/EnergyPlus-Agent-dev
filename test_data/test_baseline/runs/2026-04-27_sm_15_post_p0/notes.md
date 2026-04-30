# 2026-04-27_sm_15_post_p0

## 本次目的

P0 三档 token 优化全部落地后（ack-only 返回 + batch 工具 + export_idf 外置），用 `smalloffice_15_post` 案例做几何阶段端到端回归，与 anchor `2026-04-26_sm15_pre_p0`（~150k token，逐次 update_surface）比较，验证 token 节省是否落进预期 70–80k 区间。

## 异常 / 失败点

- 无掉线、无重跑。
- `validate_config` 返回 96 条占位 Construction 引用错误（`Default_Ext_Wall` / `Default_Int_Wall` / `Default_Window` 全部不存在）—— 这是几何阶段已知行为，由 `Tool_scripts/export_idf.py` 的 Patch 0 在 `convert_all` 前预注入 stub Construction 解决；不视为失败。
- 标注脚本第一次 `python ... > /tmp/upd.json` 失败（Windows bash 无 /tmp），改写到 `output/_upd.json` 后通过。已落 feedback memory。
- 脚本 `baseline_record.py` 自动找 IDF 时优先匹配到旧的 `smalloffice_15/output/smalloffice_15.idf`，已手工把 `geometry.json._source_idf` 改指向 `smalloffice_15_post/output/smalloffice_15_post.idf`。两者计数恰好相同（14/84/12），未影响 counts 字段。

## 与上一 anchor 的差异观察（基于 context.txt 真实数据）

| 指标 | pre_p0 anchor | post_p0 | Δ |
|---|---|---|---|
| `/context` Total | 221.3k | **163.4k** | **-57.9k (-26%)** |
| Messages 一项 | 199.2k | 141.1k | -58.1k (-29%) |
| MCP 调用数 | ~115 | **22** | **-81%** |
| 会话数 | 2（含 1 次掉线） | **1** | -50% |
| MCP 工具总数 | 77 | 79 | +2（新增 2 个 batch） |
| Counts (z/s/f) | 14/84/12 | 14/84/12 | 一致 ✓ |

**结论**：P0 三档收益真实存在，但**幅度小于 token_optimization.md §7.7.4 当时的预测**（预测 150k → 70-80k 即 -50%；实际 221k → 163k 即 -26%）。

### 为何与 70-80k 预测偏离一倍多

token_optimization.md §1.1 当时的 sm_15 baseline "≈150k" 本身就是低估，未计入 Claude Code 的 harness 固定开销：

| harness 开销项 | 量级 | 与本项目工作的关系 |
|---|---|---|
| Deferred MCP tools（Notion / HuggingFace / GoogleDrive 等） | ~36k | **无关**，外部 connector 注册 |
| System tools + deferred | ~31k | 框架自带 |
| Autocompact buffer | ~33k | Claude Code 预留压缩区 |
| 合计 | ~100k | 任何 case 都有 |

→ 真实 token 下限其实是 `harness ~100k + 必要工作 ~70k ≈ 170k`，与 post_p0 实测 163.4k 几乎一致。说明 P0 已经把"必要工作"那一段压到接近极限了，**继续往下减必须靠减 harness**（关掉不相关的 MCP server，能省 ~20-36k）或减 messages（P1 自动 boundary 推断、压缩 skill 文档）。

> ⚠️ **2026-04-29 修订**：上文 "harness ~100k" 把 `MCP tools (deferred) 36k` + `System tools (deferred) 19k` + `Autocompact buffer 33k` 都算进了 harness，但实测 `8.9 + 11.8 + 2.4 + 0.1 + 0.6 + 141.1 ≈ 164.9k ≈ 显示的 163.4k`，说明 deferred 三项 **不计入 `Tokens used` Total**，autocompact 也不计入。**真实计入 Total 的 harness 仅 ~24k**（`System prompt + System tools + MCP tools(loaded) + Memory + Skills`）。"关掉无关 MCP server 省 20-36k" 的判断作废 —— 那部分本就没花。继续向下压 token 必须聚焦 Messages 段（141k 占 86%）。

### token 估算的失败教训

`tokens_estimate` 字段当时合计 ~75k，与真实 Messages 141.1k 差近一倍。原因：
- 估算把每次 MCP 调用当作"单次成本"独立加总，**忽略 history 累积** —— 14 次 create_zone 时第 14 次的 context 含前 13 次完整结果
- skill 文档 + 系统 prompt 在每个 turn 都被引用一次，估算只算一次
- vision 部分图像 token 估算偏低

**纪律修订**：以后 tokens.total **必须**从 `/context` 真实读，估算只能作为 by_phase / by_tool 的相对分布参考，不参与 Δ 比较。

## 下次改进候选

- **关掉不相关 MCP server**（Notion / HuggingFace / GoogleDrive）→ 预计省 ~20-36k harness token，且这是无成本的纯收益
- `baseline_record.py` 自动 IDF 匹配应优先匹配 `<case>_<tag>` 拼接路径（如 `sm_15` + `post_p0` → `smalloffice_15_post`）
- Sonnet 4.6 降级测试：在此 post_p0 anchor 上做对照跑；当前 163k Messages 对 Sonnet 仍有压力但应能跑通
- 开源模型迁移前必须做 P1 改动 3（自动 boundary 推断），否则 141k Messages 远超主流开源模型 32k 上下文窗口
- token_optimization.md §1.1 / §3 的预测表需重写（未做，待评估是否补一篇 retro 文档）
