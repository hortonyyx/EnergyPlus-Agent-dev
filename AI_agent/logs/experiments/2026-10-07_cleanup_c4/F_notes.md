# C4 F：字符串化结构参数宽容解析

## 接口

新增 `src/agent/runtime_roles/parameters.py`：

```python
normalize_stringified_parameters(arguments, schema) -> dict
```

它只在工具 `inputSchema` 明确声明 `object`、`array` 或 `boolean` 的节点上，把能解析成对应类型的 JSON 字符串解码一次，再递归处理该结构中明确声明的子字段。同一路径即使同时出现在根 schema 与 union 分支，也按“字段路径＋原字符串”复用一次解析结果；不会借分支重入逐层解开双重编码。真实字符串（包括 `*_json`）、数字、null 与未声明字段不猜测；无效 JSON 或解码后类型不符保持原值，交原有校验拒绝。

`oneOf`／`anyOf` 先用类型、已出现的 `const`／`enum` 判别分支，能用 `required` 区分时再收窄；仍有多个可能分支时，只保留各分支产生的相同变换，避免把不同 operation 变体的字段拼在一起。已覆盖 `match_id` 的 string／array 兼容，以及按 `op` 区分的平面返工操作。

## 接入

`ReaderTools.call_tool` 在单图权限检查、试建结构检查和原工具调用之前，从它实际公布的 `_catalog[name]["inputSchema"]` 取 schema 并调用 helper。运行循环的 `_execute_pending` 直接把模型参数交给 `tools.call_tool`，MCP 客户端只检查最外层是字典，没有更早的 schema 拒绝，因此该边界能够接到真实调用。调度员 `RoleSession` 的接入由主助手负责，避免本任务修改 `session.py`。

## 检查覆盖与局限

新增四项行为检查：递归解码同时保留字符串和数字；union／operation 分支不串值；根属性与 union 分支重叠时同一节点只解析一次且双重编码保持原样；通过真实 `ReaderTools.call_tool` 与实际 catalog schema 把 `"false"` 变为布尔后再调用冻结工具。按派工要求本任务未运行 pytest；已不经 pytest 直接执行这四项，全部通过，仍等待主助手统一登记并低并发执行正式检查。

本 helper 不替代 JSON Schema 校验，不解析 `$ref`，也不推断没有明确 `type` 的开放 schema。`allOf` 支持逐项应用；无法判清的 `oneOf`／`anyOf` 只应用各分支一致的变化，宁可让原校验拒绝，也不跨分支改数据。
