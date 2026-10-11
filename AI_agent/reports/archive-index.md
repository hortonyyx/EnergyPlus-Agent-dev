# 历史资料位置

## 2026-10-11：domain 清理前快照

Git 基准 `3e917b8ecb0c3c8757edf590fcf9cc41a44c9999` 保留本轮清理前的跟踪文件。另有本机独立副本 `D:/Sim-BIM-Agent/archive/architecture-cleanup-20261011-3e917b8e`，74 个管理文档及旧阶段资源、720,489 字节，全部复制后 SHA-256 相符；逐项路径/大小/哈希在该目录 `manifest.json`。此副本不是新增远端备份，跨机器可从上述 Git 提交恢复跟踪原文。

其中 `AI_agent/workflow/models.md`、`run_case.md`、`design/reading_correction.md`、`role_division.md`、`model_configuration.md` 保留完整历史方法、提示、用量和旧方案。当前同名文件只维护现行职责和操作；历史批次授权不自动生效。仍被执行的旧资源及管线入口已归入 `src/agent/legacy`，详见 [legacy 索引](../../src/agent/legacy/README.md)。

## 迁移时保全的历史资料

当前开发唯一主库为 `D:\Sim-BIM-Agent\repo`。2026-10-11 复制自桌面后，424,586 个资料文件逐项 SHA-256 核验，零差异；1155 个链接只记录、不跟随。

批量移位操作被工具自动审批拒绝（仅返回 blocked by policy）。采用保守布局：完整历史资料留在核验过的 D 副本原位，并退出当前 Git 版本、默认测试及发布包。没有重试该移位。

| 内容 | 实际位置 |
|---|---|
| 旧实验、交接、审阅 | `D:\Sim-BIM-Agent\repo\AI_agent\logs` |
| 旧开发归档 | `D:\Sim-BIM-Agent\repo\AI_agent\archive` |
| 历史案例、原输入、GT | `D:\Sim-BIM-Agent\repo\case_tests` |
| 旧快照、展示、output | `D:\Sim-BIM-Agent\repo\backup`、`showcase`、`output` |
| 迁移核验与旧树独有证据 | `D:\Sim-BIM-Agent\archive` |
| 新用户案例 / 新运行 / 缓存 | `D:\Sim-BIM-Agent\cases` / `runs` / `cache` |

历史回放须显式传 `--archive-root D:/Sim-BIM-Agent/repo --cases-root D:/Sim-BIM-Agent/repo/case_tests`。不可把整个案例根交给work model；GT仍只用于评价。

Git提交 `9f5332ae55fe0f011197cc009190bbadae7ad6b2` 保留历史跟踪文件；本机额外未跟踪证据由上述 D 实体副本和哈希清单保全。正常clone不下载当前目录树中的旧实验；完整Git历史未重写。
