# Opus 5.5 本轮开发任务：Voimatalo 残缺外部补全

你与 Astra 同为最高档开发负责人；用户刚确认额度恢复，要求两边各推进一程后由 Astra 统一收工。两个家族不绑定路线。你的当前 cwd 是独立工作树，分支 dev/opus-voimatalo-20260926，基准 8be2f049。Astra 同时做还原多层/立面。

## 范围与授权
先读取 AI_agent/Agent.md、project/goal.md、workflow/development.md、workflow/models.md、最新 09-25 交接；最新用户恢复额度授权覆盖上轮额度中断状态。可以按需派内置子代理。使用现有 Claude 订阅，不调用付费 API、DeepSeek，不读/输出凭据或 .env，不下载新素材，不调用其他工作模型做迁移。用户尚未验收候选；本轮仍是开发模型完善待验收方案。
只允许新增/修改 AI_agent/logs/experiments/2026-09-26_voimatalo_opus_completion/ 下的代码、方案、观察、验证、结果和任务交接；不得改旧结果/原始输入、公共src/scripts、全局项目文档。需要公共能力修改，提供具体最小补丁或说明给 Astra。用现有 /opt/venv/bin/python，PYTHONPATH当前树，禁止 uv sync/uv run/依赖安装。先确认 src.agent.geometry.source_bim.__file__ 属于本树。可 git add/commit 自己目录，不合并/推送主线。稀疏工作树具备 src/scripts/tests/AI_agent 和原 Voimatalo 单体目录；如缺只读依赖，可在本树用 git sparse-checkout add 加载必要路径，不修改父主树。

## 技术起点
- 09-25 新候选：AI_agent/logs/experiments/2026-09-25_voimatalo_opus_development/candidate_01/；80空间/300窗/88门，源sha256=56b6a912c292fa2458cd127e8b4e51591d0b2f12f7e0619c630960fb04aacedc。该目录 README、HANDOFF、review/coordinator_disposition.md、PUBLIC_INTERFACE_NOTES.md、装配/量测/打包/验证脚本可复用。
- 原始带贴图单体 case_tests/textured_mass/single_buildings/voimatalo/input.glb，建筑声明在09-15开发目录。
- 原交接明确仍有：内院被裁突出体未补、部分院面窗/短翼东侧扫描缺口/退台端部未知。

## 目标和判断
本轮集中完成一个实质外部缺失补全节点，优先核原扫描的内院突出体及关联围护、楼层/核心连接；如原证据不足以唯一还原，提出并实际生成与现有输入相容的明确推断方案，记录观测/假设及不确定范围。重要缺失不能只标unknown结束，也不能一律当透空/无窗墙。必要的内部局部调整可做，但保留09-25已成的交通/服务分隔、可靠窗几何和连续核心。避免为数量增加而虚构房间。不是全楼重做，不做EP/材料。

## 完成依据
1. 查看原贴图/网格，用现有量测/投影工具保存选定缺失部位的实际证据；保留原输入，不用GT。
2. 在新目录实际装配新候选，保存可重放声明/脚本/source/proposal/display/viewer；至少针对新部位制作原扫描/09-25/新方案的可查看对照。关键推断白话解释，用户可评审。
3. 确定性验证：源重放、无无意空间重叠/假楼板、开口宿主、保留旧可靠窗与门（若改须逐项理由）、新部位与全楼真实门/敞开接触连通、浏览器离线显示/可旋转与链接完整。不要把技术检查当用户验收。用已存在相关检查，不重复全套。
4. 在有限开发轮内取得完整可 review 的局部成果。约45分钟内保存关键候选并进入收尾，整次最大60分钟；无需凑时间或为小修再起子审阅。最多一项独立子审阅按需。
5. 写 HANDOFF.md 列实际修改、前后差异、基准/成果提交、验证、真实子代理、遗留、活动进程。明确仍待用户验收，不迁移工作模型。给 Astra 简洁最终交接，不写全局文档。
