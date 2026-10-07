# D1j 执行报告

状态：A–F 完成，G 文件范围/LF/不提交已完成；临时目录清理被安全策略拒绝，已停止。基准 `f73fbbc8`，工作树 `d1j`。执行方 Astra，未派子代理（本包工作集中在共用装配链，直接开发便于核对文件边界）；work model / Paratera / DeepSeek 均 0 次调用。所有修改留在工作树，未提交。

## 范围与设计

- A：先冻结全部指定真实立面交付和旧对位结果；只在同面、同层、同类、顺序唯一的组上尝试横向比例和平移拟合。结合真实残差定容差、最少数量及比例范围；保留歧义、漏项、错宽的冲突，不修改平面位置。
- B：立面新提交只表达图上横向标定，任务目标决定朝向与坐标轴，旧格式继续可读；在本包负责的 `elevation.py` 提供归一化，不修改 D1k 的提交模块。
- C：建层时从平面房间种子与已有依据生成用途依据，传给现有几何工具；不改变房间种子格式，不要求读图员重复填写。
- D：在分工侧 `session.py` 替换调度员的 `revise_bim` 目录入口，用扁平的小修参数转换成现有修改操作；单模型工具保持原样。
- E：仅替换调度员与立面读图员指引，记录参数结构、指引和说明字符数，平面读图员段不改。
- F：离线重放全部指定交付、run7 七次小修意图、三例贯通与恢复，以及角色检查和单模型逐字节对照；显式 `-n 2`，不跑全量。
- G：文本 LF；临时证据在 `AI_agent/archive/local_backup/d1j/`；保留可复查的精简证据与脚本，交付前核文件范围，给出建议提交分组。

## 已核对的边界

已完整读取 Agent.md、产品目标、当前任务、工作方式及最新 10-07 交接，读取派工单和 A–G 验收要求。初始工作树干净。D1k 负责的 `readers.py`、`trial.py`、`submission.py`、`plan_format.py`、平面读图员指引及 Agent 登记不在本包修改范围。主树历史运行只读；正在执行的三例对照不干预。

## A：横向比例漂移

`match_elevation` 保留原直接对位；存在超出 0.35 m 的横向偏差时，才对同立面、同层、同类的完整组尝试一条比例和平移换算。源平面位置、宽度、隔墙均不调整。

- 至少 3 个、两边数量相同、顺序唯一，不从组内挑有利子集。两点总能拟合，至少三点才能有残差核对。
- 横向跨度至少 1.4 m，相邻中心间距大于两倍残差上限，避免短距离或重合中心放大噪声。
- 比例限于 0.90–1.10，平移不超过既有位置容差 0.35 m；覆盖本次实测约 2.4% 漂移，同时拒绝方向错误、大偏移和明显比例错误。
- 所有残差不超过 0.10 m（调用方若给更小位置容差，取更小值）；严格于原 0.35 m，不把放宽容差当成拟合。
- 图中标注宽度与源宽度仍须符合原 0.25 m 容差，拟合后的像素宽度也须与图中标注宽度一致。数量、宽度、残差等任一条件不满足便保留未对上项。

run7 第一份 East：三扇窗拟合比例 **0.9755801469**，平移 **−0.04676251 m**，最大残差 **0.00739976 m**。新增 `E-W2 → W-r2 → op_afc`、`E-W3 → W-r1 → op_aea`；原横向偏差分别 0.4153 / 0.5200 m，拟合后 −0.0074 / +0.0037 m，两扇的窗台/窗顶均为 1.0 / 2.8 m，与参照一致。

34 份真实交付全部重放，按各运行最终源稿核对（无成楼稿的 run4、27B 用**仅供评测**的参照 fixture，不是该次运行成功成楼）。参照不传入生产代码；逐个比对源位置/宽度、原始读图坐标最近的参照对象及高度。已有原始冲突继续保留。

| 运行 | 交付数 | 改前对上 | 改后对上 | 读图门窗数 |
|---|---:|---:|---:|---:|
| sm24 run3 | 4 | 14 | 14 | 14 |
| sm24 run4 | 3 | 6 | 6 | 9 |
| sm24 run5 | 6 | 18 | 18 | 23 |
| sm24 run6 | 4 | 9 | 9 | 14 |
| sm24 run7（包括一次 East 返工） | 5 | 16 | 18 | 18 |
| sm21 run1 | 4 | 17 | 17 | 17 |
| sm25 run1 | 4 | 34 | 34 | 34 |
| 27B 摸底 | 4 | 14 | 14 | 14 |
| 合计 | 34 | 128 | 130 | 143 |

130 个对上的对象均通过逐项参照核对；新增 2 个正确，新增错配 0。另按原始记录中的 **41 个历史 candidate 对位上下文**复验，135 → 137，新增仍为同两扇，没有新增错配。重复交付/上下文的计数不代表不同物理门窗数量。

证据：[逐个核对表](pair_table.md)、[完整对位数据](matching.json)。表中的 run6 最终稿 9 个与 D1i 一步稿 8 个是不同 candidate，不混用；本包没有修复既有读图漏项。

run7 不提供 East 返工交付，仅用第一份读图调用一次 `assemble_from_readers`：内部一次建平面、一次写用途依据、**一次高度事务写齐 14 个**；实际覆盖报告 14/14，第二次相同调用不新增候选。未改覆盖检查或 `height_evidence.py`，也未把拟合后的坐标伪装成新的观测。

## B：立面参数

本包在 `elevation.py` 提供立面工具包装器；不修改 D1k 的 `readers.py` 或 `submission.py`。新目录不含 orientation、view_direction、world_axis 或有方向的世界端点。朝向由 task.target 绑定，外部观看方向和轴由代码推出；内部仍保存可校验的旧标准格式。

新 `x_calibration` 为两处像素 `pixel_start/pixel_end`、从**图中建筑左边缘**量起的 `distance_start_m/distance_end_m`，以及整立面的 `facade_length_m`。局部尺寸链必须保留距图左边缘的偏移，不能把局部长度当总长；North/West 由代码用总长减去距离，South/East 正向换算。多给一个总长，是为了消除 run6 North 局部链的起点换算负担；不是让模型重新判断世界坐标升降。

三份首交的像素点和局部距离保持不变，仅按新字段表达并补入图纸已有的总尺寸：run5 East、run6 West/North 均首次验证通过。North 的 0.54/5.34 m 自动换成 9.46/4.66 m。34 份旧格式产物仍按原含义可读，不静默改写已存读图。证据：[方向重放](directions.json)。

## C：用途依据

一步装配完成后，将种子用途通过现有 `set_space_role` 写入源模型，附来源图、任务、种子 ID、原读图依据与假设，保留已有用途依据和后续人工修订。当前种子格式没有可验证的“原文用途标签”标记，因此保守记为 **inferred**，不把家具解读提升为观测事实；不改种子格式、不要求读图员重填。

| 运行 | 原用途依据齐全空间 | 修改后 |
|---|---:|---:|
| sm24 run7 | 0/8 | 8/8 |
| sm21 run1 | 0/14 | 14/14 |
| sm25 run1 | 0/29 | 29/29 |

三例房间用途、门窗平面位置和宿主均保留。sm21 原始立面楼层标高不一致，本次使用该次调度员已记录的 level_overrides，不把冲突默认值强行成楼；sm25 仍返回两项旧高度超宿主冲突。覆盖分别为 14/14、15/17、32/34，后两例缺口没有隐藏。[三例装配与空间依据](assemblies.json)。

## D：小修入口

调度员目录用 `edit_bim(candidate, edits)` 取代 `revise_bim`，每项 action+reason；height 用 id/sill_m/head_m/image/bbox，use 用 id/role/image（默认 inferred），position 用 id/along_start_m/along_end_m/image，note 用 text。角色别名由既有目录归一化。高度通过既有原子依据事务，其余通过既有局部修改；说明追加保存，不删除旧未决项。高度与其他修改分开成批。

run7 七次意图分别在各自原候选的独立副本上重新表达：2 次各写两扇窗高度、4 次各补 8 个用途、1 次追加说明，**7/7 首次成功**，重复调用不新增写入，非目标内容保留。这里验证的是新工具能够直接表达原意，未声称自动修复旧错误 JSON，也没有新 work model 行为验证。原参数、新参数、保存结果见 [七次重放](edits.json)。

## E：替换指引与说明

字符统计以 Unicode 字符计；参数结构采用 `json.dumps(..., ensure_ascii=False)` 默认分隔符，与派工单约 2317 字符口径一致，另保留紧凑 JSON 数值。

| 项目 | 改前 | 改后 |
|---|---:|---:|
| 立面提交参数结构 | 2317 | 2193 |
| 参数结构（紧凑 JSON） | 2107 | 1997 |
| 调度员指引 | 1930 | 1874 |
| 立面读图员指引 | 5770 | 5672 |
| 平面读图员指引 | 9084 | 9084，逐字相同 |
| 立面提交工具说明 | 278 | 287 |
| 一步装配工具说明 | 520 | 444 |
| 局部修改工具说明（revise_bim → edit_bim） | 346 | 466 |

新增局部修改说明明确四种参数和依据，长度增加；未把所有变化描述成压缩。旧方向表和调度员旧收尾写法已替换，兼容旧产物的标准格式示例仍保留在共享校验路径。[详细统计](metrics.json)。

## F：检查结果与边界

**209 个角色检查的最新结果全部通过**。完整角色范围首轮 207 通过、2 失败（429.16 秒）；两项均为同一条旧立面单位文本断言的参数化实例，按派工要求删除，未修改底层坐标模块。最终限定复验 27/27 通过（33.16 秒），覆盖这两项、新增 D1j 行为、指引及单模型逐字节对照。其余成功结果复用，没有再跑全套角色范围或仓库全量。

完整角色范围包含 sm21/sm24/sm25 离线贯通、读图/装配/高度写入中断恢复、旧交付与防重复写入、单模型首请求/工具/指引逐字节对照。已知忙机偶发的 `test_resume_reader_after_trial_checkpoint_does_not_repeat_trial` 本轮通过，未作例外重跑。新增检查还验证了小修已持久化后返回中断时重取回执、未知写入结果不重做、无效批次不部分写入、需要复核时阻止新的修改。

开发首轮局部检查发现旧字段文本断言、装配测试替身缺少内部 revise 支持、正式版本指纹与工作副本不一致；均已处理。后续局部检查里的返回 envelope 文本键序断言改为结构化内容对照，保存效果不变。生产代码没有为了让检查通过而关闭版本核验或图纸覆盖检查。

常规检查均先执行 `. .\scripts\activate_windows.ps1`，确认 `src.agent.__file__` 指向本树，显式 `-n 2`；临时目录在 `AI_agent/archive/local_backup/d1j/`。主命令：

```powershell
$env:BIM_AGENT_REGISTRY_PATH = (Resolve-Path 'AI_agent/archive/local_backup/d1j/local_agent_versions.json').Path
$roleTests = @(rg --files tests -g 'test_role*.py')
python -m pytest -n 2 @roleTests --basetemp AI_agent/archive/local_backup/d1j/pytest --junitxml AI_agent/archive/local_backup/d1j/roles.xml -q
python -m pytest -n 2 tests/test_role_c4.py tests/test_role_d1j.py tests/test_role_guidance.py tests/test_role_single_parity.py --basetemp AI_agent/archive/local_backup/d1j/pytest_final --junitxml AI_agent/archive/local_backup/d1j/final.xml -q
```

正式 Agent 版本登记留给 D1k/Opus 合并后办理。本树使用既有 `BIM_AGENT_REGISTRY_PATH` 扩展点，在临时副本登记当前 84 个文件，最初从真实本地工具目录探测四种目录指纹；最终刷新仅涉及分工文件，复用未变化的共用目录指纹。严格文件核验和单模型真实目录对照都通过，正式 `agent_versions.json` 未修改。[逐项检查结果、最终源码哈希与几何回读](verification.json)。

复现入口为 [replay.py](replay.py)，可选 matching / directions / assemblies / edits / metrics；无需模型、网络或新付费额度。三例真实读图回放使用冻结交付，不是新冷启动整案。没有真实模型复测，离线通过不代表真实画图质量、收尾耗时或 token 已改善；本包只给可直接复核的接口和保存结果证据。

## G：交付与提交分组

`git diff --check` 通过，新增/修改文本为 LF。改动限定为四个负责的生产文件、对应角色检查与本实验目录；未改 `height_writes.py` / `height_evidence.py`、D1k 的文件或平面指引、单模型/共享几何/运行底座、正式版本登记。主树运行只读，三例并行对照未干预。无 Git 写入、无提交或推送。

建议 Opus 合并时分为两组（本树不执行）：

1. `feat(roles): normalize facade readings and simplify assembly corrections`：`elevation.py`、`assembly.py`、`session.py`、`guidance.py` 的本包段，以及 `test_role_d1j.py`、D1h/C4/guide 对应检查。实现与检查一起提交。
2. `docs(roles): record D1j offline replay evidence`：本实验目录新增的报告、复现脚本、逐个核对表、JSON 证据与检查摘要；原 brief 不变。

清理前只读盘点：自建临时目录约 **480.85 MiB**、14,869 个文件、100 个 pytest 链接。已确认删除目标的绝对路径限定在本工作树；拟在检查链接目标后用 PowerShell `Remove-Item -LiteralPath ... -Recurse` 删除。该命令被自动审批/安全策略直接拒绝，原因为 **`blocked by policy`**，未执行，也未改用其他方式绕过。临时目录保留在 `AI_agent/archive/local_backup/d1j/`，不入 Git；可交接证据已独立保存在本实验目录。
