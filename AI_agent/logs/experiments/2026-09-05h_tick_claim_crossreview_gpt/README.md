# 刻度认领返工 2 · GPT 独立复核证据

被审对象固定为 `75f7732a`，工作树 `/tmp/tickrw2_review_gpt`。只在本目录和本轮裁决书写文件；不修改上一轮材料、被审稿、源码或测试。

复现命令：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 AI_agent/logs/experiments/2026-09-05h_tick_claim_crossreview_gpt/capture.py
```

- `evidence.md`：E01–E16，原命令、未经编辑的 stdout/stderr、退出码。E02 独立复读上一轮五阻断与四不阻断；E03–E12 是本席重新检索的文件行号；E13 为本轮新输入；E14–E16 复跑旧探针。
- `numbers.md`：对 **802 行本稿** 扫描，168 个数字 token、1058 次出现；`legacy_numbers.md` 为旧稿探针的 170/948，不能混作本稿自查。
- `legacy_capture.md`：完整复跑上一轮 `capture_evidence.py` 的 14 组命令。只把输出目的地改到本目录，上一轮文件原样保留。
- `probe.py`：独立新输入。`ACTUAL` 执行本树现有代码；`SPEC` 是稿中公式、分支顺序或字段形状的明确直译，不是拟议生产类型的测试。前缀和直译采用 `range(1, len(cum))`，短数组反例只证明未定义边界条件会留下这种实现选择。

D6 探针先执行稿中工厂原文，记录实际 API 参数个数错误；随后仅加参数桥接，仍执行原文载体，使用两个 **现有校验器均接受、源字节完全相同** 的不同 manifest bundle。未实现稿中未定义的 `_derive_tick_claims_from_frozen_bytes`：用诊断函数回报它收到了哪个 bundle。证明范围是“消费前没有绑定本次 bundle”，不声称生产 tick 坐标已经被改。

F1 的 tuple 缺项例及 F4 的 operand 字段例仅证明展示的字段不蕴含所宣称的关系；稿中承诺的构造守卫还没有实现。本席另以缺失的来源绑定、消费入口及相互冲突的签名说明设计不足，不以没有生产实现本身判阻断。

无 pytest、模型调用、依赖安装、B2/T4-a 重审或全量测试。B2 已过审合并与主线 3850 passed 的事实直接采用任务书；本树的旧快照不推翻当前主线状态。没有进入主工作树写文件。
