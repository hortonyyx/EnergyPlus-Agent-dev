# 阶段 3：局部观察角色小测题库

本目录给只读的“局部观察”角色准备 **10 道题**。题目只引用仓库已有图片字节，没有新渲染、没有复制图片，也没有模型调用。10 张实际使用的图片均在 10-02 出题时逐张打开查看；路径、原字节 SHA-256、原图尺寸、可用像素框和 view／坐标来源都写在 [`manifest.json`](manifest.json)。

运行侧只读取 `manifest.json` 和其中列出的图片。参照答案、原始依据路径和人工评分细则只在 [`references.json`](references.json)，不能下发给局部观察角色。这样同一题可以交给 Qwen3.8-27B 或 Flash 对照，而不会把参照答案混进证据包。

## 题目分布

`test_group` 是本轮四组验收统计；`input_kind` 是材料格式；`information_sufficiency` 单独说明这张材料能确定多少。三者不互相替代，所以“信息不足”两题仍如实记录其输入是网格渲染，而不是把输入格式写成“推理”。

| 题组 | 题数 | 输入格式 | 信息充分程度 | 主要检查 |
|---|---:|---|---|---|
| 图纸 `drawing` | 3 | 图纸 | 局部充分 | sm24 东／西立面大窗与普通窗的两种窗顶；平面 10×20 m 总尺寸链和南门 900 mm |
| 三维网格既有渲染 `mesh_render` | 3 | 网格渲染 | 部分充分 | Voimatalo 西侧差异竖带、内院低层附属体、俯视体量关系；不把室内用途当直接观察 |
| 照片代替品 `photo_surrogate` | 2 | 照片 | 不充分 | 复用阶段 0 的贴图/扫描渲染代替品，检查是否识别破碎与拉伸并拒绝精确报楼层、窗数和进深 |
| 信息不足 `information_insufficient` | 2 | 网格渲染 | 不充分 | 邻楼遮挡下的端墙有无窗、严重缺面的附属体层数／开口数；只评诚实不确定 |

共 10 题；四组分别为 3／3／2／2。按 `input_kind` 为图纸 3、网格渲染 5、照片 2；按 `information_sufficiency` 为局部充分 3、部分充分 3、不充分 4。真实照片仍待用户选样，本目录两道照片题都显式设置 `photo_surrogate: true`。

## `manifest.json` 接口

每题包含：

- `case_id`：稳定题号；
- `test_group`、`input_kind`、`information_sufficiency`：分别用于验收分组、输入格式和信息充分程度；
- `photo_surrogate`：是否以渲染代替真实照片；
- `question`：发给局部观察角色的精炼问题，不含答案提示；
- `images[]`：`view_id`、仓库相对路径、SHA-256、原图宽高、完整可用 `available_bbox_px`、恒等的原图像素 `coordinate_relation`、视图来源和坐标来源；
- `response_contract`：沿用阶段 0 的 `localized_evidence_result_v1`。返回必须分成 `directly_seen`、`interpretations`、`uncertain`，每条直接观察给原图像素框。

像素框统一为原图坐标 `[left, top, right, bottom]`，左上原点，右／下边界不包含。当前题库发整张原图，`available_bbox_px` 因而都是 `[0, 0, width, height]`；角色自己在返回中定位局部，不把评价侧框提前泄漏给它。主线程接真实委派时可把 manifest 一题转换成正式 `EvidencePackage`，并在运行时补入该次任务的 `package_id`、`task_id`、源 BIM 版本和预算预留号。

## 评价办法

每题满分 10 分，分项覆盖实际内容、标注或解释依据、像素定位和不确定性边界。图纸三题有独立读图 JSON 与同日窗高小测作参照；Voimatalo 题引用原始渲染、米制投影记录、阶段 0 代替品说明和用户已验收版本的局部记录。参照只约束其明确覆盖的局部，既有推断 BIM 不冒充真实室内。

照片代替品与两道信息不足题设有 `honesty_only: true`：人工只检查它是否准确描述现有像素、识别破损／遮挡、并诚实保留无法确定的量。它给出某个听起来合理的楼层数或窗数，不能因 JSON 合法或碰到关键词而得正确性分。

[`evaluate.py`](evaluate.py) 做两件事：

1. `validate` 核对题数、四组覆盖、输入与充分程度分列、图片路径／哈希／尺寸／bbox、参照路径／哈希及评分总分；
2. `prepare-review` 把主线程保存的真实返回与评价侧参照拼成人工复核包，仅提示三栏和 bbox 等结构缺失，**不自动判正确性**。

真实返回可写成 `{case_id: response}`，或 `{"responses": [{"case_id": ..., "response": ...}]}`。生成的人工复核包保留空的 `criterion_scores`、`total`、`verdict` 和 `notes`，由评价者逐题填写。

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD \
  python AI_agent/logs/experiments/2026-10-02_harness_stage3/role_cases/evaluate.py validate

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD \
  python AI_agent/logs/experiments/2026-10-02_harness_stage3/role_cases/evaluate.py \
  prepare-review --responses /path/to/responses.json --out /path/to/human_review.json
```

## 来源与边界

- sm24 三题复用 `case_tests/e2e_tests/sm24_anchor/case_data/`，东、西立面窗高同时由同日 GLM 基线失败和 Paratera 局部小测验证过；角色问题没有提示“大窗可能不同”。
- Voimatalo 复用 09-10 既有纹理网格渲染和 10-01 已验收精细档的局部记录。用户验收的是该推断方案的细度与可用性，不等于真实室内参照；评分细则已把这种边界写开。
- 仓库没有获批真实照片案例。两道照片题只是阶段 0 已登记的代替品，不能据此声称真实照片能力通过。
- 像素定位参考框由本次人工查看原图后记录，用于复核是否框到同一对象，允许合理松紧，不做逐像素 IoU 自动门槛。
- 本题库没有挑选或隐藏模型结果；截至交付尚未运行任何题。主线程统一执行后，应按 `test_group`、`input_kind` 和 `information_sufficiency` 把全部对错一起报告。
