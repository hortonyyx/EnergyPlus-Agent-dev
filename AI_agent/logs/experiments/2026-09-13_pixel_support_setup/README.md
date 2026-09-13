# 局部像素支持工作方式试验

本批只推进sm24还原建模。新量具把局部颜色匹配的真实坐标和断续支持画出来，让模型解释可回查；不自动识墙、不自动补线。

## 独立运行入口

- `run_probe.py`：原图东南空间局部观察，默认Haiku、150秒；可显式选Sonnet及新out。无旧BIM/GT/给定裁区或正确坐标。
- `run_recovery.py`：从run04/candidate_01恢复，五原图加完整未改写观察，Sonnet medium、300秒；可显式选观察目录及新out。生成拒绝覆盖已有run。
- `verify_probe_views.py`、`verify_measurements.py`：生成结束后核对原图/返回图、输入隔离、候选峰值支持区间，均不判断墙/门语义。
- `audit_source_changes.py`：生成结束后比较实际源对象字段；源字段不变不证明图纸保真。
- `archive_streams.py`：生成结束后无损压缩事件流，先核对往返摘要再删除原始重复流。

[Haiku观察](../2026-09-13_sm24_pixel_support_observation/README.md) · [run05无修改恢复](../2026-09-13_bim_agent_sm24_run05/README.md) · [Sonnet同题观察](../2026-09-13_sm24_pixel_support_observation_sonnet/README.md) · [run06错宿主移门](../2026-09-13_bim_agent_sm24_run06/README.md)

独立观察的prompt/system、原图与实现摘要相同，见`comparison_inputs.json`；模型/effort及模型自选量测不同，只各做一次，不视为稳定优势或端到端成功率。父恢复收到原文，未收到开发评测或人工修正数字；全部评测在独立目录，生成不可访问。

生产调用仅Claude现有订阅，Sonnet级上限。CLI估算不是订阅账单；前置观察与后续恢复为两次串行调用，时间/用量分别记账，不能当作同一父进程已包含的子任务重复或漏算。
