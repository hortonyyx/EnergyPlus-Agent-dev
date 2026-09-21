# 下一次 07-07 sm21 Haiku 历史 pilot：可执行短方案

本方案只准备历史路线的下一次有界测试，不替代当前主线，也不在本次启动 worktree、模型或网络调用。目标是检验 **723b0f9 的旧规则与 CV 工具，在答案隔离后，当前 Haiku 是否能完成一张 1F 原图的可审 reading**。是否先跑这一独立臂，仍由主助手结合当前 run08 结果决定。本轮只做 pilot；未通过就停，不进入 2F、四立面、correction 或 BIM。下面的隔离与检查是本次实验控制，不预设为产品固定流程。

## 先处理一个新发现：旧 worked example 与 sm21 墙网相同

`1595981`（07-02 Sonnet 运行树）和 `723b0f9`（07-07 Haiku 运行树）的旧 kickoff 都要求先读：

`case_tests/e2e_tests/smalloffice_20/0_reading/1f_view.json`

该文件不是中性格式例。它的 10 条墙与两份历史成功 sm21 1F 输出的墙线集合完全相同：15×8 外框、两道 y=3/5 的贯通墙、四段 x=5/10 的上下内墙。具体原件为 `1595981:skills/intake_pipeline/0_reading/session_kickoff.md:13-15,61` 和 `1595981:case_tests/e2e_tests/smalloffice_20/0_reading/1f_view.json:12-43`；该示例到 `723b0f9` 字节未变，SHA-256 为 `d3424c42...`。逐项比较结果：

- 示例：10 墙、0 窗、16 条粗尺寸；
- 07-02 sm21 1F：10 墙、7 窗、32 条详细尺寸；
- 07-07 sm21 1F：10 墙、7 窗、32 条详细尺寸；
- 三份的 10 条墙按端点方向归一后完全相同；示例没有七扇窗，尺寸条目也不等同于成功输出的详细链。

因此旧 100 分结果仍是当时 scorer 下的有效成绩，窗和详细尺寸仍有独立量测链；但“墙网完全由原图独立发现”不能再作为已证事实。不能据此断言模型照抄，也不能否定其真实 CV 动作。09-16 跑的是 sm24，该示例并不是 sm24 答案，不能用这项发现解释 09-16 成败。

**下一次 pilot 不向 reader 暴露该示例。** 这是相对历史条件的明确变化，换来可解释的独立性。若以后要原样复现历史数值，可另设“含同墙网示例的历史辅助臂”，结果必须标为 assisted，不能与本次独立 pilot 混算。

旧 `guide.md` 里也有 `(0,0)→(15,0)`、`(5,0)→(10,0)` 和 15000/5/10 等格式片段（`723b0f9:skills/intake_pipeline/0_reading/guide.md:126-146,180-245`）。这些常见单线段/数值不足以给出目标完整布局，不能仅因数字相同就判为答案泄露，也不应为追求“零相同数字”而改写整套旧规则。下一 pilot 保留 guide 原字节，将这些片段列为残余上下文；强隔离对象是能给出完整、有识别性 sm21 墙网组合的 worked example、GT 和旧 run。

## 1. 冻结源树，但不给 reader 整棵树的可见权

执行时建立完整 detached worktree，固定到：

`723b0f98ed37285b66cb3d1d30caa8e42eb01a74`

完整树只作为字节来源和控制侧校验对象，不能直接作为 reader 的可浏览 cwd。它含有明显答案源：

- `case_tests/test_baseline/gt/sm21_anchor/`：GT JSON、DXF、GT render 和六张 overlay；
- `case_tests/e2e_tests/sm21_anchor/`：除 `case_data` 外约 508 个历史文件，含多份旧 reading、judge packet、score、correction 和 BIM；723 树已经含 07-02 满分输出及 07-05 失败输出；
- 上述 `smalloffice_20` worked example：直接给出 sm21 1F 同墙网；
- `AI_agent/`、测试、评分脚本和其他 case：含历史成绩、方法取证、fixture 或 GT 路径；
- `.git`：即使工作目录隐藏答案，reader 仍可用 `git show` 读取对象；当前 main、其他 worktree、home 也可能旁路访问答案。

reader 只能看到从完整 worktree 原路径只读映射出的以下内容：

1. `skills/intake_pipeline/0_reading/` 的旧规则全文；
2. `src/agent/reading/` 与 `scripts/tool_scripts/cv_probe.py`；
3. `case_tests/e2e_tests/sm21_anchor/case_data/` 的六张原图和原 `testdata_prompt.json`；
4. 一个新的空白可写 `0_reading/` 和 `requests/`；
5. Python 运行依赖。

旧 kickoff 保持原字节，但 prompt 明说 worked-example 路径因与目标墙网重合而故意不可用，格式以 guide 和旧 schema 为准。原声明中的每层 `thermal_zones: 7` 属于正式输入，继续提供并在报告中列为先验辅助；不把它扩写成目标墙窗数量。

隔离必须在操作系统文件可见性层生效，Claude settings 的 `Read deny` 不够，因为 Bash/Python 可绕过。优先用临时容器或已验证的 mount namespace 建只读可见视图；若本机 namespace 不能用，则退回“从完整 worktree 按 allowlist 生成的逐字节投影视图”，并明确记录它不是完整树运行。启动模型前必须保存负向自检：reader 同权限下用 Read 和 Bash/Python 均打不开 GT、任一 sm21 旧 run、worked example、`.git`、当前 main、其他 worktree和 home；同时旧 CV CLI 对一份复制到 scratch 的输入能正常 `--help`/导入。任一答案路径可读就停止，不靠 prompt 承诺继续。

## 2. 复用 09-16 runner 的部分

现有 `2026-09-16_reading_method_reproduction/reproduce.py` 可复用这些机制，后续另建实验入口，不原地改旧实验：

- 固定请求 `claude-haiku-4-5-20251001`，禁 provider/model fallback；
- 首轮记录 session ID，返工使用 `--resume` 保持同一会话；
- 每轮保存准确 prompt、stream events、stderr、receipt、实际模型、CLI 版本、耗时和用量；
- 每轮结束完整快照 `0_reading/`、`requests/`，并记录文件散列；
- 超时后终止整进程组，禁止后台残留；
- 单独审计图像返回是否与本地文件像素相同、工具调用和错误，不用模型自述代替。

不能原样复用的部分：`prepare()` 当前只挑 20 份文件且固定 sm24；settings 允许宽泛 Bash，只有提示级隔离；worked example 被复制进输入；cwd/路径、manifest 和 prompt 都固定到 sm24。这些必须换成 sm21、上述答案隔离视图和新的输入清单。

仍无法恢复的历史条件要在运行前写进 provenance：07-07 完整原 prompt、Fable 5 原反馈全文、旧 Agent-tool 宿主、当时服务端权重/采样、视觉内部预处理及会话额度状态；本次为独立性而排除了同墙网 worked example。若当前只能走 Claude CLI，这次应称“723 工具与工序的当前宿主独立性复现”，不能称逐环境原样重放。

## 3. 首个 1F pilot 的派工要求

prompt 不写正确坐标、墙窗数量、历史分数或历史候选数。只要求 reader：

1. 只处理 `case_data/1f_view.png`，保持原图像素帧；裁图必须保留逆变换，所有引用像素回到原图坐标；
2. 从实际尺寸线的 tick/extension 选锚，保存标定输入、残差和被淘汰的失败标定；跨轴明显冲突时先回看锚，不靠平均掩盖；
3. 对墙、窗、门符号、家具、尺寸线等候选看局部原图后分类，保留 accepted/rejected/uncertain 及理由；投影峰不能直接延长成整栋墙；
4. 转录自己在原图中实际看见的尺寸链，未标注对象可用标定后的像素量测，但需标 `pixel-measured`、留空 `dimension_refs` 并引用 sidecar；
5. 仅在可见门符号属于该墙时治愈门洞，保留真实开放段和不确定项；
6. 写历史 schema 的 `0_reading/1f_view.json`，并停止等待外部复核，不开始其他五图。

必须交付的自产物是：`1f_view.json`、原图框架下的 render/overlay、标定 sidecar、墙/窗候选 sidecar、用于关键端点与歧义分类的 crop、候选处置台账，以及一份 pilot self-check，逐项列出未看清和未检查的范围。**不设调用次数、crop 数、候选数、墙数、窗数或尺寸数下限。** 动作多不等于正确；要求的是每条输出主张能回到原图证据，且没有把整类对象静默省略。

## 4. 主控检查与同会话返工

主控在 pilot 阶段不打开 GT、旧 sm21 reading、score 或 worked example；只看原 1F 图、声明、reader 自产物和旧 schema。由于开发主控已经知道部分历史答案，放行依据必须按运行前冻结的检查表逐条写证据，反馈中禁止给目标坐标、正确墙窗数、历史值或“应当长成什么格局”。

检查顺序：

1. **坐标运输**：每个 crop 的逆变换可重算，所有锚和像素支持位于原图范围；
2. **标定真实性**：锚落在同一条真实尺寸链的 tick/extension，不是文字、墙端或全图色块范围；多锚残差与原 overlay 一致；
3. **几何支持**：逐条输出墙/窗在原图上有连续范围和端点支持，整长笔画没有由单个投影峰臆造；
4. **候选取舍**：已生成的物质候选都有 accepted/rejected/uncertain 处置，理由能由 crop/overlay检查；同时回看原图中容易混淆的墙端、门弧、家具和窗带，避免通过少生成候选规避台账；
5. **信息完整性**：可见尺寸链和对象类别没有被整类漏掉；`uncertain/uncaptured` 写的是具体区域或对象，不用笼统声明代替阅读；
6. **schema 与诚实来源**：loader 可载入、字段合法，量测与标注来源没有混写；旧 gate 结果只作为格式/局部关系信号；
7. **原图回看**：将 reader render 叠回原图，检查多墙、漏墙、错治愈和窗/家具混淆。此检查不比较 GT，也不以元素数量接近历史为理由。

首轮不合格时只发一次同会话内容返工，指出 reader 自己证据中的具体矛盾、遗漏类别或未检查区域，不给修正答案；保留首轮快照。返工后再次按同表检查。仍不合格就停止该 pilot，记录失败位置，不靠重复抽样或继续增加动作凑通过。纯 schema 机械错误可以同会话单独修，但不得借机给几何答案。

## 5. 冻结后再评分，评分不回灌

source-only 主控通过或两轮用尽后，先冻结候选 hash，再由 reader 不可见的控制侧运行 723 loader/gate及旧 `score_reading_vs_gt`。GT 分数只作事后评价，不进入 pilot 反馈，也不允许据分数继续改同一候选。报告分开写：

- 输入先验与 worked-example 排除；
- 当前宿主、实际模型、会话和全部工具动作；
- source-only pilot verdict；
- 冻结后的旧 reading 分数；
- 与历史环境仍不可恢复的差异。

只有1F原图检查通过，才根据结果安排同一会话的2F和四立面；用户对继续工作的授权已经有效，无需因此另问许可。本方案暂不安排批量调用，也不涉及当前run08、生产工具、DeepSeek、correction或源BIM。
