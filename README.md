# sm25 F1 分工模式小测证据 — 2026-10-09

固定生产代码 `30085ccefdd50ee742ecea2fecf65941ad70f941`，runtime-v2-20261009 / domain-v56-20261009。GLM 订阅 glm-5.3-flash / medium，只运行一个平面读图员 F1 任务，共 40 次请求、40 次响应，58.08 分钟。技术流程完成并 accepted 提交；独立原图复核与质量评价失败。没有运行整案、重复抽样或使用其他 work model 线路。

## 文件与恢复

- `sm25_f1_run.tar.gz.part001` 至 `part007`：按 `archive_parts.json` 顺序连接后得到 `sm25_f1_run.tar.gz`，完整原始运行，3,492 文件、62,281,350 字节；归档 SHA256 `b8570922f6576cae388d5dfe72bcd9462dc784da43cc7d82faf8c21f0d204aac`。
- `sm25_f1_supplemental.tar.gz`：过程日志、退出码、两组 JUnit/pytest 检查记录、离线汇总及 F1 独立评价，20 文件、2,000,214 字节；归档 SHA256 `95813094188de8dd0df26f4542eb07fa231fc65f79253059b0cb163935028fdf`。
- 四份 source/copy manifest：源运行和本地副本各两轮逐文件路径、长度、SHA256 校验，结果一致；两个 archive manifest 同时记录归档成员，全部读回核验。
- `probe_execution.json`、`probe_summary.json`：最终运行状态及技术/质量结论。前者作为独立文件补入，不在 supplemental 归档中。
- `live_behavior_notes.md`：独立观察原始请求、工具参数/返回、返工和最终产物的全过程记录。
- `process_samples.jsonl`：运行中一次资源快照，不是峰值或单独 runtime 本体占用。
- `evidence_secret_scan.json`：两个归档的 3,512 个文件经过已知凭据值及高置信敏感模式检查，零发现；没有导出凭据值。
- `published_files_manifest.json`：本分支除 manifest 自身外的文件大小和 SHA256。

原归档整包上传遇到连接重置与 HTTP 408，故本分支使用 4 MiB 分片逐批提交；原归档哈希保持不变。先按 `archive_parts.json` 验证各片，再按编号连接并核验完整归档 SHA256。

两个 tar.gz 的成员路径相对项目根目录。先核验哈希，再解压到独立恢复目录；原始运行位于 `AI_agent/archive/local_backup/role_runtime_repair/sm25_f1`，评价位于同级 `f1_evaluation`。此证据分支为独立 orphan 分支，不覆盖生产分支，不含环境凭据。

质量失败主要由外轮廓包入建筑外空白、约 140 m² 虚构东北室内空间、错误拆分及 10 个未匹配参照门窗支持。固定评分中 2 cm 的房间边界阈值也会把小偏差标为 severe，因此不把所有 severe 标签当作严重几何错误。详见 `probe_summary.json` 的评价边界。
