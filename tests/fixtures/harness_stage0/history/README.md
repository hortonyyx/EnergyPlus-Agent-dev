# 历史事件映射

本目录的两个 JSON 由
`AI_agent/logs/experiments/2026-10-02_harness_stage0/map_history.py` 确定性生成，
输入是 `../sources/claude_run99_excerpt.json` 与 `../sources/sol_bridge_excerpt.json`。
它们是历史节选，不是新运行记录。

- `claude_run99_event_log.json` 按历史 stream 的实际行序保存独立消息。每条消息
  保留自身的完整原文与 usage；receipt 的运行累计 usage 另存为
  `run_usage_summary`，不回填到单条消息。`agent_request.json` 只是启动记录，
  所以最终适配器请求明确为 missing。CLI 的 `tool_result` 是模型可见层记录，
  raw MCP 返回明确为 missing。
- `sol_bridge_event_log.json` 保存外层 dispatch、桥接 operation、工具执行、桥接
  后的外层 return 与运行汇总缺失；模型请求边界另外明确记录最终请求和外层
  prompt 未存档。operation 保存档案中的桥接请求和返回，return 保存控制器的完成
  回执，两者不是同一个返回层。
  `inference_001` 是原返回中的真实 ID；
  `synthetic:archive:...:call-index:3` 只是档案请求/返回的映射身份，不是服务或
  MCP 提供的 operation ID。桥接返回已存档为 raw，模型是否实际读取未知，
  所以 shown result 明确为 missing。

历史没有保存的六层版本均写成 `identifier = "not_captured"`。这不是一个版本号，
也不表示各层相同，只表示本节选无法核实。远端模型别名同样标为 `unverified`。
每个事件的 `source_refs` 都指回原历史文件，带选择器和完整文件 SHA-256。
