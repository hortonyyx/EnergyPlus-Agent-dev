# 阶段 0 历史来源映射

`extract_sources.py` 是离线提取器。它只读历史 `AI_agent/logs/`，只写
`tests/fixtures/harness_stage0/sources/`。每个摘录保留历史对象 ID，不给证据、
视图、声明另编 fixture ID；每个来源项都有仓库相对路径、完整文件 SHA-256 和
JSON Pointer 或 Markdown/CSV 行号。

| 阶段 0 用途 | 摘录 | 历史来源与选择器 | 已知缺口 |
| --- | --- | --- | --- |
| 还原：双层尺寸、像素视图与规整 | `sm25_cross_floor_excerpt.json` | `2026-10-02_reconstruction_discussion.md:24`；`2026-10-01_opus_dev_sm25/dev_inputs/plan_f1.json#/partitions[id=P_off16]`、`plan_f2.json#/partitions[id=P_top]`，以及 `candidate_04/source_model.json` 的 `F1:O2/F1:O3/F2:O1`；`image_views/view_0001.json`、`view_0002.json` | 4.00/3.94 是工作记录中已核实的图纸结论，旧记录没有对应 `record_claim`；图纸本身是光栅图片，尺寸字没有 JSON 子选择器。 |
| 部分推理：已验收精细档、重复门对和例外 | `partial_inference_excerpt.json` | `2026-10-01_voimatalo_door_revision/acceptance.json`、`door_layout.json#/paired_groups[id=PAIR_027],/changed_doors[id=D_F2_W_01_CORE_S]`、`candidate_02/source_model.json#/spaces[id=CORE_E]` | 已验收 BIM 没有工作模型回执；`door_layout.json` 不定义通用模板 ID。 |
| 两次 Sol 的细粒度反例 | 同上 | `2026-10-01_partial_inference_developer_tests/comparison.json#/models/0,/models/1`；`review_61sol.md:27-34`；`review_6sol.md:45-49` | 这些是单次开发模型试验的离线评价，不等于工作模型基线。 |
| 真实 Claude CLI 生命周期 | `claude_run99_excerpt.json` | `2026-09-30_sm21_instruction_fix_run99/agent_request.json`、`agent_receipt.json`、`agent_stream.jsonl.gz` 的解压 JSONL UUID/行号 | 有签名但公开思考文字为空；没有独立的最终 wire request 存档。stream 的 `tool_result` 是 CLI 可见的转换后返回，不能冒充网络层或原始 MCP 返回。 |
| 6.1 Sol 桥接记录 | `sol_bridge_excerpt.json` | `2026-10-01_partial_inference_developer_tests/run_61sol/controller_{request,receipt}.json`；`bridge/ed694e699b86430e83618f26ce1d79ee/{requests,replies}.json` | 协作接口没有 provider 实际模型、token 或账单回执，三个字段历史值均为 `null`；没有模型消息/思考记录。 |
| 完全推理少图输入替代品 | `photo_surrogate_excerpt.json` | `2026-10-01_partial_inference_developer_tests/run_61sol/images/parent_detail_front.png`（473,339 bytes） | 这是历史贴图/扫描渲染，不是真实照片；可见的深色带受裁切和破碎网格影响，不能当作建筑开口或可靠楼层证据；仓库未找到可授权的真实照片案例。 |

历史大文件仍留在原实验目录。fixture 仅保存小段原始字段或精确截断的返回文字；截断处以 `…[truncated in fixture]` 标明，并由完整源文件 SHA-256 复核。
