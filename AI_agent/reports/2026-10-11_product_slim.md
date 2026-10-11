# 2026-10-11 项目精简与独立发布

状态：程序与测试精简已完成，审阅发现已修复。新版产品隔离验收和独立审阅均通过。原C目录删除被工具自动审批拒绝，仍保留，并已写退役转向D的说明。以下只记录已取得证据，不把历史整案质量算作通过。

## 当前入口

- 开发主库：`D:\Sim-BIM-Agent\repo`；桌面产品：`C:\Users\Horton\Desktop\Sim BIM Agent`。
- 产品提交 `8d336e2156389eabcda76b7cb2297c09ec4c3104`，runtime-v7-20261011 / domain-v64-20261011。496个payload文件18,076,192 bytes；环境独立重建，不含Git/历史案例/凭据。
- 产品的 `Start.cmd doctor`、`demo`、`check/run`、`auth` 为用户入口。真实账号未登录，真实模型调用0。
- 当前测试400模块：54 fast、195 targeted、13 node、138 historical。最新默认收集636项；node含fast共67模块。并非历史全集通过。

## 已验证

| 范围 | 结果 | 耗时 / 证据 |
|---|---|---|
| 路径与发布契约 | 新增20+兼容7通过 | 实施代理离线报告 |
| 产品入口 / 示例配置 / 发布选择 | 3通过 | 7.78s |
| 默认检查收集 | 54模块636项，仅fast（未重复执行） | 8.32s，D cache default-collection-20261011-preflight-final |
| 当前节点原批 | 745通过、2跳过、1失败 | 1100.41s，cache/pytest/test-slim/f2ee3f0d3d70/results.xml |
| 节点失败单项复验 | 1通过，恢复版本保护不变 | 140.61s，cache/pytest/test-slim/75dc028965b6/results.xml |
| 输入预检定向 | 36通过 | 3.47s，cache/pytest/release-preflight-001/results.xml |
| 桌面独立产品最终版 | 通过 | 26.907s，D cache/product-smoke-003/report.json |
| 资料11根保全 | 424586文件SHA一致，0错误；1155链接仅记元数据 | archive/migration-verify-summary.json |
| 其余源文件保全 | 1034文件；863与D副本一致，171差异另存并回读；0错误 | archive/source-before-slim/_audit/summary.json |
| Git引用保全 | 57分支、117标签的126目标对象及剥离对象可在D解析 | source-before-slim/_audit/git-summary.json |
| 审阅发现的测试修正 | 21项通过 | 64.24s，cache/pytest/test-slim/f6397aedccb7/results.xml |
| 旧D树保全 | 138266文件；833差异/独有另存回读，0错误 | archive/old-worktree-evidence |

原节点唯一失败由测试进行期间工具选择器脚本更新触发正确的跨版本恢复拒绝；稳定后仅复跑该项，通过。原批次的失败不追改。两跳过分别为真实模型opt-in与历史1269事件回放；后者已移到显式historical，最终默认集合不再包含它。

独立产品验收使用产品自身Python、-I、空PYTHONPATH、外部cwd；443模块解析路径与149实际加载模块都在产品内。合成示例产出2空间、1门、1窗，内嵌查看器资源和来源声明正确。ScriptedAdapter两次离线响应、一次真实MCP工具执行，中断后恢复及完成重开不重复执行。网络guard下外部模型/付费API/登录调用均0。查看器尚无浏览器视觉验收；本例不评真实建筑识读质量。

## 资料与清理

实际布局见 [归档索引](archive-index.md)。六目录批量移位被自动审批拒绝，仅返回 blocked by policy，未给具体原因；没有执行该移位或换途径重试。历史数据保留在已核验Drepo原位，从当前Git索引和默认测试退出。原Git历史不重写。

原C删除在保全/边界核对后再次被自动审批拒绝（同样只返回 blocked by policy），操作未执行，未换工具重试；约16.9GiB尚未释放。仅将已另存原件的旧C README.md、AI_agent/Agent.md改为退役转向D说明，防止后续误开旧主库。4个旧C闲置MCP服务/子进程已停，D/桌面产品不依赖它们。回执 `archive/old-c-removal-blocked.json`。

5个旧D开发树已删除：evidence、role-kernel、g1、lite-sm25、v53。q1/q2/v1的56个旧测试目录Access denied，未接管ACL；不可读内容未验证，目录保留。可读独有证据全保全。

## 独立审阅

全新审阅者未发现P1，产品独立性可接受。发现并修复：5项当前runtime纯合成性质误归历史；节点fallback错误自称全仓。代码静态复核与21项定向复验通过。另发现公开check对错误图片文件仍ready的旧预检弱点，已补PNG目录/有效PNG/精确文件名白名单及GLB文件边界，36项通过并经独立复核；不涉及真实模型。

桌面安装含独立依赖环境共478,414,051 bytes（约456.3MiB），其中payload约17.24MiB。开发/source历史不会进入新发布包。

独立审阅最终无未解决P1/P2，产品与测试范围通过。审阅者还实际检查了桌面合法外部配置ready、错误图片输入退出1，以及1,034个补保全目标全部SHA再核验。详见 [独立审阅记录](2026-10-11_independent_review.md)。

本轮正常保留Git历史，没有强推/历史重写。当前版本1093个已跟踪文件约29.6MiB（最后交接补充前），冻结历史退出32832个跟踪路径；本地D物理保全副本仍在，不能把Git退出说成磁盘已释放。C剩余35.92GiB，D剩余168.63GiB（2026-10-11收尾读数）。

## 产品边界与下一步

sm25最新规整整案仍为四立面完成、两平面失败，无整楼候选；未重新跑真实模型。OCR整图自动确定步长、domain减负设计及完整交互编辑仍待下一轮讨论。此次重点是交付隔离、目录精简、测试必要性和开发成本，不能当作建模质量修复。
