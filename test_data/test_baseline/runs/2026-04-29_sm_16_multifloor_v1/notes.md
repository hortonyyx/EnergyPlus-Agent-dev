# 2026-04-29_sm_16_multifloor_v1

## 本次目的

首次跑多层（3 层、每层独立平面图）案例 `smalloffice_16`，验证 skill `2026-04-29_energyplus_mcp_pre_multifloor` 中新增的 `Floor plans` 数组输入 + 共享外包 §D3.1 不变量 + 每层独立 `xs_f / ys_f` 等多层规则在端到端流程下能否一次跑通；同时观察规模翻倍（19 zones / 114 surfaces / 16 windows，对照 sm_15 post_p0 的 14/84/12）后 token 总量的变化。

## 异常 / 失败点

- 无掉线、无重跑（session_count = 1）。
- `validate_config` 返回 130 条占位 Construction 引用错误 — 几何阶段已知行为，由 `Tool_scripts/export_idf.py` 的 Patch 0 在 `convert_all` 前预注入 stub Construction 解决，不视为失败。
- 标注脚本第一次用整图最暗像素 bbox 检测到的范围把 dimension chain 的箭头尖端也包了进去，导致标签偏外；改成"按行/列暗像素密度阈值"挑出建筑主轮廓后通过。已落到 `output/annotate.py`。
- baseline_record.py 自动 IDF 匹配这次直接命中 `smalloffice_16/output/smalloffice_16.idf`，无需手工纠正（与 sm_15 post_p0 那次需要改 `_source_idf` 形成对照）。

## 与上一 anchor 的差异观察（基于 context.txt 真实数据）

Anchor: `2026-04-27_sm_15_post_p0`（sm_15 post_p0，14/84/12，total 163.4k）

| 指标 | sm_15 post_p0 | sm_16 multifloor_v1 | Δ |
|---|---|---|---|
| `/context` Total | 163.4k | **164.3k** | +0.9k (+0.5%) |
| Messages | 141.1k | 140.2k | -0.9k (-0.6%) |
| Harness overhead（计入 Total 的部分） | ~24k | ~24k | ≈0 |
| Deferred MCP tools 行 | 36k（单独列出，**不计入 Total**） | 已并入动态 schema，无该行 | -（口径变化） |
| MCP 调用数 | 22 | **28** | +6 (+27%) |
| 其中 create_zone 次数 | 14 | 19 | +5（多 5 个 zone） |
| 会话数 | 1 | 1 | 0 |
| MCP 工具总数 | 79 | 79 | 0 |
| Counts (z/s/f) | 14 / 84 / 12 | **19 / 114 / 16** | +5 / +30 / +4 |
| 输入图像数 | 5（单层 + 4 facade） | 7（3 层 + 4 facade） | +2 |

**核心结论**：规模显著上升（zone +36%、surface +36%、windows +33%、输入图像 +40%），但**总 token 几乎持平**（+0.5%）。

### 为什么规模翻倍而 token 没翻倍

1. **Batch 工具吃掉了规模增长** — 114 surface 与 16 windows 仍各只有 **1 次** MCP 调用；增量只来自 `create_zone` 多 5 次（×~1k token = ~5k）和多读 2 张图（vision 估 ~10k）。
2. **Harness 23k 才是真实固定底座**（修正先前 100k 的口径错误） — `system_prompt 9.1k + system_tools 11.8k + mcp_tools 2.5k + memory 0.2k + skills 0.6k ≈ 24k` 是真正计入 `Tokens used` 的固定头开销；`autocompact_buffer 33k` 是预留区不计入 Total，`Free space 802.6k` 同理。这部分不会跟着 zone 数线性增长。
3. **vision token 占比反而下降** — sm_16 7 张图但每张内容相对简单（3 层平面 + 立面均为单色 CAD），与 sm_15 单张更密集的平面相比单图成本相当。

### 与 token_optimization.md §1.1 早期预测的对照

§1.1 早期推断 batch 化是 P0 中**单点 ROI 最高**的一档。本次 19 zone × 6 surface = 114 surface 一次 batch 全填，正是 batch 价值最直观的展示。如果回到 pre_p0 的 14 次 update_surface 循环模式，仅 `update_surface` 单条这一项就会再增 ~30k token（按 sm_15 pre vs post 的差额线性推算）。可视为 batch 化在更大规模上**仍然成立**的二次验证。

## 下次改进候选

- 以本 run 为 anchor 起一个 **multi-floor capability bucket**（与 sm_15 系列单层并列），后续 sm_17 / sm_18 在此基础上做 setback、L 形、楼梯井等扩展时直接对照本 anchor。
- skill `2026-04-29_energyplus_mcp_pre_multifloor` 第一版即跑通，可考虑把 §D3.1 共享外包不变量与 §M1 多层 `xs_f` 推导的措辞固化到下个稳定快照。
- vision 阶段 7 张图占的 ~30k 估算偏粗；如要进一步压榨可考虑把 South/North 立面合并成单图（sm_16 这种对称底层重复内容多）—— 但这是案例输入侧的改造，不是 skill 改造。
- `baseline_record.py` 在 sm_16 上自动匹配成功，sm_15 post_p0 时的 `<case>_<tag>` 拼接路径搜索仍可补充，避免下次又踩 `smalloffice_15` vs `smalloffice_15_post` 命名歧义。
- ~~关闭无关 MCP server 省 ~20-36k~~ **作废**：核对两次 `context.txt` 后发现 sm_15 anchor 那 36k `MCP tools (deferred)` 行是单独列出但**不计入 `Tokens used` Total** 的，关与不关对真实预算几乎无影响。Claude Code 现已改为动态 schema 搜索（deferred 行连显示都省了），原假设的"无成本纯收益"基本前提不成立——以后 token 优化路线应聚焦在 Messages 上（占 14% × 1M = 140k 是真正的大头，且会随 case 规模和重复 history 增长），不再追这条 harness 路线。
