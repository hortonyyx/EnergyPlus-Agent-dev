# CV 工具箱 C0+C1（`e3ec9ae`）事后代码审 — verdict + 同轮修复

- **日期**: 2026-07-06（排队单 ①，Fable5 定序）
- **流程**: Claude 编排 → Codex 对抗式事后审（danger-full-access,自跑 pytest 496 绿确认基线）→ Claude 逐条独立核验（5/5 属实）→ Codex 同线程落修 → Claude 独立复跑全量 pytest。
- **结论**: FINDINGS 3 MAJOR + 2 MINOR,全部当轮修复;496→**500 绿 + 9 xfail**(+4 回归测试),零契约/schema 改动。

## Findings 与修复

| # | 级别 | 位置 | 缺陷 | 修复 |
|---|---|---|---|---|
| F1 | MAJOR | `sidecar.py` | `--sidecar-name` 未净化:`../../../x` 穿越、绝对路径逃逸 `cv_evidence`;`exists()`→`write_text()` TOCTOU 可覆盖 | 显式名强制 `^\d{3}_[A-Za-z0-9_-]+(\.json)?$`;`write_sidecar` 改 `open("x")` 独占创建 |
| F2 | MAJOR | `test_gt_discipline.py` | 扫描 token 抓不到直读 `gt.json`(只认 import 形 token)→ 纪律测试是纸面守卫 | `_FORBIDDEN` 补 `"gt.json"`、`"/gt/"`(预查扫描树零误伤) |
| F3 | MAJOR | `tools.py:_prepare_image` | float bbox 记账用浮点、实际裁剪 `int()` 截断 → crop_chain 逆变换差最多 1px,破可逆契约 | bbox 一次性归一 floor/ceil 整数,裁剪/记账/offset 用同一组整数 |
| F4 | MINOR | `tools.py:overlay_logger` | geometry 派生失败静默记 null、无画痕(违「接受/拒绝都留痕」) | `_candidate_geometry` 返 None 即 raise(Claude 裁定:不硬性要求字面 `geometry` 键,`anchor_px` 派生合法) |
| F5 | MINOR | `tools.py:_load_rgb` | RGBA/LA/P-transparency 的 alpha 被 `convert("RGB")` 丢弃 → 全透明灰像素当有效 clean-vector 掩膜 | 有 alpha 先白底 `alpha_composite` 再转 RGB;`_mask_clean_vector` 改走 `_load_rgb` |

## 方案审 4 findings 落地复核（Codex 逐条 file:line 确认）

1. API 收紧 = 基本在位(crop 校验/line profiler 核/calibrator LS/CC 8-连通),缺口即 F4,本轮补齐。
2. Phase B 预留槽 = 在位(`_base_result` + sidecar provenance)。
3. attempts/report 收编=注释标记未来集成 = 在位。
4. 无 OCR/弱 VLM 过度承诺 = 在位(skill 文档)。
