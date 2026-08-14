# run_2026-08-13_accept_A_aborted_envflake — ⛔ 作废（环境层失败，非管线缺陷）

**这不是一次有效的验收跑。** 保留仅为留证。

- 真实退出码 **1**（非以往的 30），栈见 [flow_aborted.log](flow_aborted.log)：
  `stage_runner.py:600 os.replace(adir, final_attempt_dir)` →
  `PermissionError: [Errno 13] ... attempts/.001.xauh2idc -> attempts/001`
- **失败时的文件系统实况（orchestrator 实测）**：`attempts/001` **并不存在**、
  `attempts/` 与各级父目录 `drwxr-xr-x root root` 可写、进程为 root、盘余量 900G
  ⇒ 常规 Linux 语义下不该 EACCES ⇒ 判为**环境层目录改名失败**（本机 overlay/WSL2）。
- **⛔ orchestrator 的操作错（本次真因的可疑来源）**：把**验收跑**与**全仓 pytest**
  **同时**放在同一棵工作树上跑，而全仓里有会**遍历整个 `case_tests` 树做元数据指纹**的守卫
  （F-23 那族），恰在 flow 改名 attempt 目录时扫过。
  ⇒ **纪律：真链路验收跑必须独占工作树，⛔ 不许与全量测试并行。**
  （与既有纪律「最多两个施工席位同时在同一棵工作树上」同族。）
- ⇒ 有效的验收跑另起（`run_2026-08-13_accept_A2` 起），在全量结束之后**单独**跑。
