# 派工：Q1 补丁包 Q1b（编译前先把小偏差接好：近端点、压外轮廓的隔墙、坐标精度）

派工人：Opus 5.5（项目经理）。工作树 `D:\EnergyPlus-Agent-worktrees\q1b`，分支 `dev/astra-q1b-20261008`，基于当前主线（已含 V1、Q1、Q2、D1l）。**迭代范围：domain · BIM rules 与 kernel（两种模式共用的编译前修整），以及平面读图员试建返回的报错；runtime 不改。**

**为什么做（10-08 凌晨实测，[记录](../2026-10-08_quality_sm25/README.md)）：** sm25 分工质量实测（Q1、Q2 合入后、D1l 之前）两个平面读图员各试建 13–14 次**全部失败**，额度耗光仍交不出，调度员第 62 分钟重派。失败原因是读图员自己的平面编译不过：悬线（例如一端写 657.686、另一条线在 657.6856，只差 0.0004 像素）、隔墙压在外轮廓上、两个房间种子落在同一空间、门窗找不到宿主墙。Q1 的规整要求平面先通过严格编译才动手，所以这些近在咫尺的偏差从来没被修过；而 Q1 与 D1l 都告诉读图员“位置给大致值即可，代码会对准”，于是读图员写的大致坐标接不上，又改不对（报错给的是对齐后的小数，它照抄四舍五入的值）。10-07 夜合入效果测试（Q1 之前）同样的读图员 5–7 次试建就能提交。

**证据（只读，需要时拷到本工作树 `AI_agent/archive/local_backup/q1b/`）：** 运行目录 `D:\EnergyPlus-Agent-worktrees\runs-q\AI_agent\archive\local_backup\quality\sm25_role_q`（运行结束后会拷到主树 `AI_agent\archive\local_backup\quality\sm25_role_q`），两层平面读图员的全部试建稿在 `tasks/<任务>/bim/trial_workspace/plan_drafts/draft_*/`（`plan.json` 是读图员原样输入，`result.json` 是报错）；Q1 之前能通过的对照在主树 `AI_agent\archive\local_backup\merged\sm25_role_n1`。

**要交付的行为：**
1. **编译前修整（两种模式）：** 严格编译之前，在接头容差内（不超过 30 cm、至少几个像素，由你按比例尺定并写明）自动把隔墙端点接到最近的垂直墙线或外轮廓边上（延伸或回缩）；把沿外轮廓、距离在容差内的隔墙段并入外轮廓（删掉重复的隔墙段）；合并共线重叠的隔墙段、删去零长度或退化段；把门窗端点落到最近的宿主墙线上；全部坐标统一到一个精度，使每个接头精确相等。每一处修整记入规整清单。之后再走严格编译与 Q1 的规整、硬约束。**不改实质**：不凭空加墙删房；修整后房间、门窗数量与读图员意图一致，做不到就不修、照常报错。
2. **墨线对齐不制造新错：** 移动一条线时，落在这条线上的所有端点同一步一起移动并精确相等；对齐后的平面若编译不过而原平面能过，就用原平面并在返回里说明。
3. **报错用读图员看得懂、能照抄的形式：** 剩下的错误按读图员原来的编号与坐标报，并给出具体改法（例如悬线给出应接到的那条线和精确坐标；两个种子落在同一空间时，指出它们之间缺的那道墙大致在哪）。
4. **离线回放：** 这次运行两层全部 27 份失败试建稿，逐份给出修整后能否编译、修了什么、仍失败的原因；10-07 夜合入效果测试（`merged/sm25_role_n1`）读图员的试建稿与交付稿、三例对照的交付稿，修整前后编译结果与几何不变（或只有记录在案的修整）；Q1 的历史回放组照旧通过。
5. **指引：** 平面读图员与单模型指引里关于接头的写法按新行为替换（“端点在容差内会被接上；仍报错时按报错给的坐标改”），不追加，给出字数前后对照。

**要点：**
- 开工先在本目录写报告初稿 `README.md`，随进度更新。0 次模型请求；Paratera 0，DeepSeek 0。
- 环境：工作树根目录 `uv sync --frozen --offline --python 3.12`，再 `. .\scripts\activate_windows.ps1`，确认 `src.agent.__file__` 指向本工作树。pytest 显式 `-n 2 -p no:cacheprovider`，`--basetemp` 放 `AI_agent/archive/local_backup/q1b/pytest`，交付前用 Python 的 `shutil.rmtree` 删掉（项目经理账户删不掉沙箱建的目录）。不跑全量；改到共用编译路径，跑 `test_bim_*`、`test_plan_*`、`test_role_*` 与三例离线贯通。
- 文件归属：本包独占 `src/agent/geometry/plan_regularization.py`、`plan_ink_alignment.py`、`plan_dimension_alignment.py`、`plan_partition.py`（只在严格编译前加修整入口，不放松严格编译本身）、`plan_input.py`、`scripts/tool_scripts/bim_agent_regularization.py`、`run_bim_agent.py` 里建层与修改平面稿的入口、`src/agent/runtime_roles/trial.py`、`plan_format.py`、`guidance.py` 的平面读图员段、`bim_agent_guidance.py` 的单模型平面段，以及对应检查。不改 `src/agent_runtime/` 与登记表（合并后 Opus 统一登记）。
- 新检查要克制，只验行为；被替换设计的旧检查直接改写。写文本一律 LF；**沙箱下 `.git` 只读，不提交**，报告给出提交分组。
- 内部分工与子代理由你定（子代理优先 5.6 系列，报告写明型号与原因）。

最终回复按 1–5 逐条给结果，附 27 份失败稿的修整结果表、指引字数前后对照、检查结果与建议的提交分组。
