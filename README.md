# sm25 F1 分工模式小测证据 — 2026-10-09

固定生产代码 `30085ccefdd50ee742ecea2fecf65941ad70f941`，runtime-v2-20261009 / domain-v56-20261009。GLM 订阅 glm-5.3-flash / medium，只运行一个平面读图员 F1 任务，共 40 次请求、40 次响应，58.08 分钟。技术流程完成并 accepted 提交；独立原图复核与质量评价失败。没有运行整案、重复抽样或使用其他 work model 线路。

## 文件与恢复

- `sm25_f1_run.max.tar.xz.part-000` 至 `part-010`：按 `archive_parts.json` 顺序连接后得到权威远端恢复包 `sm25_f1_run.max.tar.xz`，10,691,424 字节，SHA256 `f210e647cbdf576343b0a84b530908a42358ee6d8a4ea96cb8b4d85ba97dde65`。解压得到 68,608,000-byte tar，SHA256 `1b9eb1fad1485e996094c24784c34507e131eee6b895aead6ae40cd09cc3f36e`，与主树保留的原 gzip 解压结果逐字节相同；其中是完整原始运行，3,492 文件、62,281,350 字节。
- `sm25_f1_supplemental.tar.gz`：过程日志、退出码、两组 JUnit/pytest 检查记录、离线汇总及 F1 独立评价，20 文件、2,000,214 字节；归档 SHA256 `95813094188de8dd0df26f4542eb07fa231fc65f79253059b0cb163935028fdf`。
- 四份 source/copy manifest：源运行和本地副本各两轮逐文件路径、长度、SHA256 校验，结果一致；两个 archive manifest 同时记录归档成员，全部读回核验。
- `probe_execution.json`、`probe_summary.json`：最终运行状态及技术/质量结论。前者作为独立文件补入，不在 supplemental 归档中。
- `live_behavior_notes.md`：独立观察原始请求、工具参数/返回、返工和最终产物的全过程记录。
- `process_samples.jsonl`：运行中一次资源快照，不是峰值或单独 runtime 本体占用。
- `evidence_secret_scan.json`：两个归档的 3,512 个文件经过已知凭据值及高置信敏感模式检查，零发现；没有导出凭据值。
- `published_files_manifest.json`：本分支除 manifest 自身外的文件大小和 SHA256。

主树继续完整保留原 `sm25_f1_run.tar.gz`：28,382,250 字节，SHA256 `b8570922f6576cae388d5dfe72bcd9462dc784da43cc7d82faf8c21f0d204aac`。整包及 4 MiB 上传发生连接重置或 HTTP 408；改为 1 MiB gzip 分片后只上传了部分中间片，因此这些片仅保留在 Git 历史中，已从最新 tree 删除，不能用于恢复完整 gzip。最新 tree 以体积更小且 tar 内容完全相同的 XZ 分片为权威远端恢复格式。先按 `archive_parts.json` 验证各片，再按编号连接并核验 XZ 与解压 tar 的 SHA256。

两个归档的 tar 成员路径相对项目根目录。先核验哈希，再解压到独立恢复目录；原始运行位于 `AI_agent/archive/local_backup/role_runtime_repair/sm25_f1`，评价位于同级 `f1_evaluation`。此证据分支为独立 orphan 分支，不覆盖生产分支，不含环境凭据。

质量失败主要由外轮廓包入建筑外空白、约 140 m² 虚构东北室内空间、错误拆分及 10 个未匹配参照门窗支持。固定评分中 2 cm 的房间边界阈值也会把小偏差标为 severe，因此不把所有 severe 标签当作严重几何错误。详见 `probe_summary.json` 的评价边界。
