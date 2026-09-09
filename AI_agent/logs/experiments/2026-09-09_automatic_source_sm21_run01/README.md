# 原图自动生成源 BIM：sm21 run01

[原图与新观测对照](index.html) · [汇总记录](report.json) · [读图诊断](reading_diagnosis.md) · [统一灰色查看](../2026-09-09_gray_enclosure_view/index.html)。

本次完成自动读图入口的实跑，但没有得到可用的新 BIM。六张原图新启动 Haiku 读图，技术检查在 exploratory 下接受；对照原图发现内部隔墙、走廊和门洞信息失真。校正 Sonnet 首次请求 600 秒超时，旧逻辑启动第二个请求后，主助手因已知输入失真中断，未继续消耗；不能把超时或未记录用量算作零成本。

## 输入与实际执行

原图来自 `case_tests/e2e_tests/sm21_anchor/case_data` 的六张平立面。没有复制历史 reading/correction，没有 GT/开发助手几何答案作为生成输入。读图 `claude-haiku-4-5-20251001`，校正 `claude-sonnet-4-6`，均经已授权 Claude 订阅；没有 DeepSeek、付费 API 回退或 EP 求解。

新入口见代码提交 `9223785f`。`command.json` 保留原命令：自动读图成功后遇到主流程缺少 manifest-loader import；补齐后按相同 argv 恢复，见 `resume_command.json`，复用同一已接受读图且摘要不变，没有再次抽图。集成缺陷已有离线回归。

读图 44 个 CLI turn，约 340 秒；CLI 估算 $0.5196532，只是估算，不是账单。其模型与用量原记录在 `report.json` 以及 `reading_isolation.tar.gz` 的审计目录。校正实际启动两个请求，第一个超时、第二个人工中断，用量不可得，所以不报告精确总费用。`--budget-draws 1` 是阶段轮数，旧校正一轮内仍允许最多三次请求，本次未跑第三次。

配置为本目录 `llm.yaml` 与 `run/run_config.yaml`；准确 argv、耗时、退出码见两份 command 记录。重现须使用新的实验目录，先按 [运行指南](../../../workflow/run_case.md) 准备配置。不要直接重跑本目录已知失真输入来追求成功次数。

## 可用证据与限制

- `run/0_reading/attempts/001` 保留六视图汇总、原始检查、CV 侧车证据和确定性投影；有 97 pass / 24 N/A / 8 fail，后者在 exploratory 中属于非阻断 cross-check。
- [诊断](reading_diagnosis.md) 记录下排隔墙缺失、走廊错位、门缺少几何和 CV 未约束输出；尺寸链与窗框告警需要结合真实结构判断，不应把所有细尺寸警告一律提升为严重错误。
- `reading_isolation.tar.gz` 保存这次完整隔离输入、工具、输出和外部审计，临时路径消失后仍可追查。采用 observe 配置，不把它宣称为操作系统强隔离证明。
- 校正调用每次 request/timeout 等记录在 `run/1_correction`；第一次缺 import 和后续中断的 traceback 保留在 `flow_stdout.txt`、`resume_stdout.txt`，控制停止原因见 `controller_stop.json`。
- 本次 judge 关闭，没有完成自动图纸保真评价、源 BIM 或仿真。主助手查看了原始 1F 与新读图投影，未做浏览器 WebGL 验收。

## 验证与下一步

最终核心检查 74 项通过；旧隔离恢复等 3 项定向复查通过，覆盖开发中遇到的三个失败。较早组合运行 438 passed / 3 failed 是开发过程记录，不能冒称最终全量通过，也不与上述重叠检查累加。详情见 `test_summary.json` 和对应日志。

下一项以本次真实反例为依据：让标定及图像线窗证据实际支撑观测，保留有位置的门/空开口，在校正前能识别实质性分区丢失。先修根因，再用独立新 run 验证；保留当前探索产物，不能靠套 GT、放宽检查或反复重抽掩盖失败。
