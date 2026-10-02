# 行为记录：offline_run

来源格式 `event_envelope_jsonl`；型号 `scripted-model`；4 次工具调用（报错 1）；首稿 1.555 秒。

## 调用 1（events.jsonl）

| # | 时间 s | 工具 | 参数 | 返回 |
|---:|---:|---|---|---|
| 1 | 0.129 | view_image | {"name": "plan.png", "coordinate_grid": false} | {"conversion": "MCP image blocks moved to a user message after all tool-call replies; bytes unchanged", "image_blocks": [{"text": "Tool image: tool_call_id=offline-1; sha256=641189 …(+2623) |
| 2 | 0.302 | view_image | {"name": "missing.png"} | {"conversion": "MCP image blocks moved to a user message after all tool-call replies; bytes unchanged", "image_blocks": [], "tool_message": {"content": "{\"images\":[],\"isError\": …(+176) |
| 3 | 1.555 | build_bim | {"proposal_json": "{\"geometry\": {\"schema_version\": \"2\", \"footprint_x\": [0, 6], \"footprint_y\": [0, 4], \"floors\": [{\"name\": \"F1\", \"z_floor\": 0, \"ceiling_height\":  …(+495) | {"conversion": "MCP image blocks moved to a user message after all tool-call replies; bytes unchanged", "image_blocks": [{"text": "Tool image: tool_call_id=offline-3; sha256=452abc …(+24646) |
| 4 | 2.017 | finish_bim | {"candidate": "candidate_01"} | {"conversion": "MCP image blocks moved to a user message after all tool-call replies; bytes unchanged", "image_blocks": [], "tool_message": {"content": "{\"images\":[],\"isError\": …(+18465) |
