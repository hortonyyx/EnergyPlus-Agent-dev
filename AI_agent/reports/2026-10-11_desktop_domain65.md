# 2026-10-11：桌面 domain v65 发布与验证

用户指出桌面尚未更新。本轮将已完成的 [domain 整理](2026-10-11_domain_cleanup.md) 交付到桌面独立安装，没有追加真实模型测试或改变建模方法。

## 当前入口

- 新版：`C:/Users/Horton/Desktop/Sim BIM Agent v65/Start.cmd`，同目录 README 提供 domain 导航。
- 版本：runtime-v7-20261011 / domain-v65-20261011；发布提交 `671c815de5d05477f8a85207b671bb08128edbae`。
- 固定发布包：`D:/Sim-BIM-Agent/releases/671c815d-runtime7-domain65`；500 个 payload 文件、18,157,891 bytes。
- 旧版：`C:/Users/Horton/Desktop/Sim BIM Agent` 仍为 v64，496 个 payload 文件最终回读与原 manifest 全部一致。它不是当前 v65 入口。

新版无顶层 `skills`，旧流程及参考资源在 `src/agent/legacy`，当前入口在 `src/agent/README.md`。补充产品说明，并将导航中指向仅开发库存在的架构/继承/归档/运行说明改为仓库链接；三个 README 的 27 个链接已按发布布局核对。README 不在 runtime/domain 登记范围内，版本不因此递增。

## 验证

| 范围 | 版本 | 结果 | 耗时 | 真实模型/付费 API 请求 |
|---|---|---|---|---|
| D 盘发布包自身环境的完整隔离验收 | runtime v7 / domain v65 | 通过 | 33.578 s | 0 / 0 |
| 桌面新版自身环境的完整隔离验收 | 同上 | 通过 | 31.391 s | 0 / 0 |
| 实际桌面 Start.cmd doctor + auth status | 同上 | ready；原账号本地 signed_in=true | 3.620 s | 0 / 0 |
| 新旧两安装 payload SHA-256 回读 | v65 / v64 | 500 / 496 文件全部一致；新版无顶层 skills | 未单计 | 0 / 0 |

两次隔离验收均使用各自安装目录原地创建的 Python 3.12 环境、`-I -B`、外部 cwd 和空 PYTHONPATH；445 个模块解析及 149 个实际加载模块均来自对应安装。合成示例生成 2 空间、1 门、1 窗及内嵌资源查看器；两次脚本响应、一次实际本地 MCP 工具执行，中断后恢复和完成重开均不重复执行工具。未发生被网络 guard 拦截的外联尝试。

证据：

- `D:/Sim-BIM-Agent/cache/product-smoke-domain65-release-20261011/report.json`
- `D:/Sim-BIM-Agent/cache/product-smoke-domain65-desktop-20261011/report.json`
- `D:/Sim-BIM-Agent/cache/product-smoke-domain65-desktop-20261011/launcher-and-auth.json`
- `D:/Sim-BIM-Agent/cache/desktop-domain65-deployment.json`

首次临时发布环境尝试离线安装时缓存不完整，随后按现有 uv.lock 下载缺少依赖；最终发布环境和桌面新版均按锁文件独立建立，未复制虚拟环境。桌面安装使用补全后的缓存离线完成。授权检查只读取本地安全元数据，没有刷新令牌、获取模型目录或重新登录。外部授权存储沿用既有位置。

## 原位更新未执行

原计划先备份再更新原桌面目录。旧版 496 个文件已经复制到 `D:/Sim-BIM-Agent/archive/desktop-before-domain65-20261011` 并逐项 SHA-256 核对，旧 manifest 和 backup-receipt 一并保存；没有复制环境或凭据。

随后“更新旧版文件并移除已迁移目录”的 PowerShell 操作被自动审批拒绝，仅返回 `blocked by policy`，没有具体原因；该操作没有执行。未使用其他工具重试同一替换或删除，而是新增独立的 v65 安装。旧目录及其环境完整保留，用户当前应打开带 v65 后缀的目录。旧目录合并/移除仍未完成，不能声称桌面只剩一个安装。

中间候选 `D:/Sim-BIM-Agent/releases/runtime7-domain65` 基于 `6c53f5c0`，没有作为桌面入口；最终入口和正式验收均为 `671c815d`。没有创建新工作树。

本轮验收证明发布独立性、资源加载、工具与恢复能力；未运行真实图纸整案、照片/mesh 推断或 EnergyPlus 仿真，未做查看器浏览器视觉验收。GPT-6 Sol 标杆与照片/细度方案仍待讨论。收尾磁盘时点读数：C 51.68 GiB、D 170.00 GiB。
