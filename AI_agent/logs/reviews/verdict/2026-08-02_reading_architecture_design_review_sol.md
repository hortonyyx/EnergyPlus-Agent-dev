# reading 环节目标形态与架构细稿 · 对抗审（sol）

- **日期**：2026-08-02
- **审阅方**：sol（跨家族对抗审）
- **受审件**：`2026-08-02_reading_architecture_design_fable.md`
- **性质**：只审架构设计，不施工
- **当前状态**：审毕

## 0. 总裁决

**REWORK**

| 级别 | 数量 |
|---|---:|
| BLOCKER | 4 |
| MAJOR | 8 |
| MINOR | 1 |
| NIT | 0 |

阻塞项不是「再补几个测试名」即可闭合：P-1 的信息边界未证实，P-2 把不可追溯的历史映射写成事实；Q-E 在解除命令限制时没有给出 OS 级隔离信任根；Q-C/Q-D 只删回调参数，未关闭现存 CLI/共享文件系统实时通道。严重度逐项记账如下，N-6 的方向盲区计入 P-3，不重复计数：

- **BLOCKER ×4**：P-1、P-2、P-5、P-8。
- **MAJOR ×8**：P-3（含 N-6）、P-4、P-6、P-7、P-9、F-1、F-2、F-3。
- **MINOR ×1**：F-4。

## 1. 承重命题 P-1 … P-9

### P-1 · `reading-agent` 不需要看图

- **判定**：**不成立（BLOCKER，与 P-2 同根）**
- **依据**：受审稿自己把「逐候选 accept/reject 的语义判别」与「跨图互证」归给 VLM（受审稿 107、109 行），但四信号只能证明有处置、有自洽、有 crop 调用，不能证明 disposition 语义正确。07-07 sm21 的第一版真实出现过「19 个候选未逐条核验」与错锚；sm24 记录了「只描主要墙/窗漏描」。前序调查已明确区分：字段空、残差等可看 JSON；候选是假墙还是真墙、窗门是否漏掉，需源图/crop/overlay 或另一 VLM 视觉核验（`2026-08-02_reading_regression_controller_cv_investigation.md` §2.3–2.4）。
- **反例形状**：工具找到真墙 C7，worker 实际打开 crop 但错判为家具，在 ledger 写 `rejected`；其他尺寸链自洽、标定自洽、可疑点 crop 已覆盖。四信号全绿，但不看图的 agent 没有任何新信息可以翻转这个错判。这不是虚构能力类：07-30 把尺寸累加位/窗垛当墙、07-07 pilot 对家具/墙候选重做语义处置，都是同类历史病灶。
- **要判定最小可行边界需跑什么**：不能只跑受审稿的 C/D 两臂；应把同一份冻结首遍产物分叉为「代码直转 gate worklist」、「纯文本 Flash agent」、「只看被点名 crop 的 Flash 多模态 agent」，比较其对已知语义错判的修复能力；每种至少两抽。

### P-2 · 07-07 干预映射是有据而非倒推

- **判定**：**不成立；属倒推，必须降级为待验假设（BLOCKER）**
- **依据**：07-07 事前完整 prompt、pilot r1 原产物和逐轮 transcript 均未落盘。现存 `reading_summary.md` 是返工后的最终总结；它能证明最终 52 个候选被处置，不能证明返工前「只描主要墙」的必要且唯一原因是候选 ledger 未覆盖。`llm.yaml` 只证明有 `discipline 1 + schema 1` 两轮，不证明 discipline 轮的全部内容。「终态有完整 ledger」 + 「事后摘要说不完整」 不能推出「当时的视觉审查可被 ledger coverage 完全代替」。
- **排他原因失败**：「只描主要墙」还可由候选生成召回不足、已处置候选的 accept/reject 判错、worker 提前停止、或跨图漏用造成。受审稿自己承认候选 5 vs 真实 16 的召回天花板（183–187 行），却又在地基结论中把该映射称为「代码可判定的事实」，前后不相容。
- **探针**：查读现存 07-07 `reading_summary.md` / `llm.yaml` / attempts 目录；未找到事前件或 transcript。这个历史命题已无法被追溯性坐实；只能通过新的受控实验验证架构假设，不能把新实验回写成 07-07 的历史事实。

### P-3 · gate① 四信号足够，且盲区已声明

- **判定**：**不成立（MAJOR）**
- **依据**：四条都是自洽/过程信号，不是视觉真值信号。仓库现有回归明文固化了 `test_self_consistent_wrong_dimension_passes_linter`：所有尺寸都错但 `3+3+3+6=15` 仍闭合，确定性门 PASS（`tests/test_checks_reading_correction.py:636-644`；实现 docstring 也在 `reading.py:693-699` 明说此盲区）。标定 RMSE 同样只检查 worker 自选锚点之间是否相容；锚点选错但一致时会绿。candidate ledger 全覆盖不检查 disposition 真假；crop 日志不检查看过后是否理解正确。反向立面在四条下也全部对镜像不变，而细稿未声明这个盲区。
- **未声明的常见盲区**：①候选被全部处置但分类全错；②自洽错 OCR/错尺寸链；③左右反向；④工具侧车被 worker 改写。细稿只充分声明了「候选召回不足」与「未来本地执行环境日志可用性」，不足以满足 P-3。
- **探针**：现有回归夹具已是反例；无需先施工新门才能判定。新门的真实分辨力仍需在 R2 用历史好/坏产物重放，但该实验只能估计灵敏度，不能消灭上述不可识别类。

### P-4 · `access_log.jsonl` 可交叉验证且不可刷

- **判定**：**不成立（MAJOR）**
- **可刷路径**：对 gate 点名的每个 bbox 批量运行 `crop_zoom`，不读 crop 图或不做任何语义判断，再在 ledger 中给每条写一个 `rejected` 理由。受审稿的检查只求 bbox 重叠，不能观测「真核验」这个认知事实。即使再要求一次 `Read(crop.png)`，也只是多一个可批量空跑的计数器。
- **日志实体与细稿不符**：细稿 230–232 行称它是「命令原文日志」并可取 `crop_zoom bbox`；现实 `guard.py:828-843` 对 **allow** 记录只落 `input_hash + normalized_paths + tool + decision/reason`，只在 **deny** 时落 `tool_input_excerpt`。08-02 真实日志中批量 crop 的 allow 行只显示图、out 目录与 request JSON 路径，不包 bbox；无法按细稿所述直接交叉。
- **「伪造不了」也不能继承到 Q-E**：新 CV Lab 允许同 UID 任意 Python，而细稿没有设计由沙箱外进程持有的 append-only 审计通道。因此 Python 可直接改写/截断 staging 内 `access_log.jsonl`；hook 不会看见该 Python 进程内部的 `open()`。
- **探针**：逐行解析 `run_2026-08-02_sonnet_full_unsup/.../access_log.jsonl`，198 条记录即呈现上述 schema；实现可在 `guard.py:828-843` 直接复核。要改判本命题，至少需要：沙箱外审计器、签名/序号链、不可由 worker 写的日志，以及证明「检查了内容」而非「调过命令」的独立产物契约；仅计次不可用。

### P-5 · 新隔离边界不会开漏题通道

- **判定**：**不成立（BLOCKER）**
- **新开的本地漏题路径**：现行守卫把 `python -c`、其他脚本和复合 shell 硬拒（`guard.py:_check_bash`）。Q-E 要删掉这个限制，却仍只描述 hook 级「路径前缀判定」，没有 mount namespace/chroot/container bind-mount/seccomp 等让禁区在 OS 层不可达的机制。于是 `python -c` 内部的 `open('/workspaces/.../case_tests/test_baseline/gt/...')`、`Path.rglob()`、`/proc/self/root/...` 不再经过 PreToolUse 路径解析，可直接读 GT/历史 run。对字符串做静态解析也无法挡住运行时拼路径。这是「新边界可达、旧边界不可达」的直接差分。
- **外传路径**：现行 `clean_spawn_env()` 保留 `ANTHROPIC_API_KEY`（`isolation.py:444-448`）。Q-E 又提议「仅放行模型 API 端点」，但没有把模型 broker 与 worker 运行的任意 Python 分成不同网络身份/凭据边界。任意脚本可用同一放行端点当出站通道；域名白名单不等于「禁数据外传」。
- **伪造审计路径**：同一任意 Python 还可直接改 staging 内 sidecar、output、request 与 `access_log.jsonl`；Q-E 宣称保留 access log 即可审计，但信任根与被测进程同 UID/同可写文件系统，不成立。
- **要判定需跑什么**：先出一份可执行的威胁模型与 OS 隔离方案，再在真实运行身份中跑红队矩阵：绝对路径、运行时拼路径、symlink/hardlink、`/proc`、子进程、环境变量/凭据、模型端点外传、日志截断/伪造、超时后孙进程残留。所有失败应在 OS/broker 层被拒，不能依赖命令文本命中。

### P-6 · Q-F 晋升门能挡住同 case GT 调参伪泛化

- **判定**：**不成立（MAJOR）**
- **可穿透序列**：候选版本 A 做一次 GT 人工核对并失败；开发者据该失败改成 B；把 B 标成「新的一次晋升尝试」，再次提交 `iteration_count: 1`；依次 B→C→D。受审稿 775–778 行明确允许「下次提交视为新尝试」，验收锁只拒绝**单条记录**的 `iteration_count > 1`（820–822 行）。所以每次记录都合法，整条 lineage 却正是在同一 case GT 上迭代；换 attempt ID 不能洗掉信息污染。
- **代理门也挡不住**：holdout 只用 gate①/自洽性，受审稿 829–838 行自己承认「系统性偏但自洽」可以通过。当前候选池又只有公开且反复使用的 sm20/sm21/sm24，不能长期保持未参与开发。数值字面量扫描只能抓最笨的硬编码，参数化、归一化或分支编码均可绕过。
- **探针**：按本稿字段构造 A/B/C 三条晋升记录，每条都是新 attempt、`iteration_count: 1` 且引用同一 GT case；本稿列出的四把锁没有一把能据跨 attempt lineage 拒绝它。这是规格级反例，不必先写晋升 CLI 才能成立。
- **必须改成的边界**：晋升服务维护不可变的候选工具 lineage（源码/参数/依赖哈希）；某 case 的 GT 一旦向该 lineage 泄露，无论版本号或 attempt 是否变化，该 case 永久从该 lineage 的晋升证据中烧毁。失败只返回不含定位细节的结果；再提交须换从未暴露的新盲测 case，最终 Core 验收由开发者看不到 GT 的独立 evaluator 执行。若项目目前没有足够的新 case，就应明说 Core 晋升被资源阻塞，不能用 `iteration_count: 1` 伪装不可迭代。

### P-7 · Q-G 实验能分离因果且成本合理

- **判定**：**不成立（MAJOR）**
- **臂定义没有分离变量**：B 有 gate 升级却没有任何消费者或返工，故在 exploratory 执行中原则上不能改善 reading 产物；B≈A 是设计内的必然，不是「确定性审计贡献接近零」的证据。C−A 同时加入新 gate、worklist、第二次 worker 调用、额外 token/时长和所谓 reading-agent，不能把差值归因给 agent。D 与 C 按 Q-D 都只复制 gate 已有 ID/check_id，输入和职责相同；模型更强不是有效处理变量，若 D 能凭能力添加新判断，反而违反 Q-D 规格。
- **成本账不闭合**：Q-D 的行为验收要求 sm21、sm24 **各两抽**，仅 C 验收就需四场；Q-G 却把 C「两抽都达标」写成整批验收，并把阶段一 A+C 计为四场，没有说明两抽如何覆盖两个 case。`plan.md` 的 R6 仍只写 sm24。于是 8/12 场的总账与本稿自己承诺的验收样本不相容。
- **隔离混杂不能靠标签消掉**：本稿允许 Q-E 前先跑 R6，只标 `isolation-confounded`，之后还只建议重跑最弱一臂；这种数据不能支持 Q-D 的因果声称。R7 又只用 Sonnet；Sonnet 无差异最多说明 Sonnet 不敏感，不能推出旧隔离对目标低档 Haiku 无害。
- **探针**：按 Q-D 规格把相同 gate evidence 分别喂给 C/D 的结构化 copier，它们的合法输出集合完全相同；再展开本稿场次表，C 在两个 case 各两抽已经是四场，和「C 两抽验收」及 8/12 总账无法同时满足。两者都是设计文本内即可复算的反例。
- **建议实验形状**：冻结同一份首遍产物后做配对分叉：A=不返工；B=确定性 gate 直接生成 worklist 并触发一次 scoped rework（无 LLM copier）；C=只对点名 crop 做语义复核的 Flash 多模态 reviewer；D 只在 C 失败时换同职责强模型。清单外字节锁定，计入完整成本，并在 Q-E 的最终边界中对 sm21、sm24 各两抽。这样 B−A 才是确定性闭环贡献，C−B 才近似视觉语义贡献。

### P-8 · 验收脱离 dev 角色是结构性保证

- **判定**：**不成立（BLOCKER）**
- **反例 1：现存正式入口仍可改变提示**。`spawn_isolated_reader.py` 公开 `feedback` 子命令与 `spawn --directive`；`spawn_command()` 会在启动 prompt 追加 directive，并在 `feedback.md` 存在时通知 worker 先读。`tests/test_isolation.py:298-319` 还把这两条通道固化为期望行为。它们本身主要是启动/续跑时通道，但足以证明正式验收需要一份明确的 channel inventory 与禁用策略；受审稿只锁 `ReadingService.run` 的 signature 无 iterator/callback，没有要求在 formal run 中删除、撤权或物理隔断这些入口。
- **反例 2：共享身份/共享 staging 绕过接口**。orchestrator/dev 与 worker 若仍是同 OS 用户，可在 worker 运行期间直接写 `feedback.md`、request/output/sidecar，发 signal，或操作其子进程；无需经过 `ReadingService` 的 Python 参数。因此「函数没有 callback」不是实时无干预的结构证明。
- **冻结哈希也不够**：若冻结件仍是可写路径，worker 或 dev 可在校验后读取前替换内容，形成 TOCTOU；内容有 hash 不等于运行期间只能读该 hash 对应的只读快照。
- **探针**：只读展开当前 CLI、`spawn_command()` 与相应回归，确认 directive/feedback 确实可达；再检查受审稿的五把 Q-D 锁，只有 payload/schema/budget/signature 断言，没有「正式运行身份无法写 staging、无法 signal、入口撤权」的验收。要改判仍需对最终执行原型做同身份文件写入、IPC、signal、调试/attach 的负测试。
- **必须具备的结构**：验收执行服务使用独立身份/namespace，只挂载 content-addressed 只读输入快照与私有输出卷；调用者只拿 opaque job handle、状态与一次性结果，不拿宿主 staging 路径；formal run 禁用 directive/feedback，禁止共享可写 FS、IPC、process signal 与调试入口；所有入站消息由沙箱外审计器记录。dev 修改 skill/tool 只能形成新 bundle hash 和新 run，不能影响正在跑的 run。验收要包含对现存 CLI/文件/信号通道已禁用的负测试，而不是只做 `inspect.signature`。

### P-9 · 三处问题书修正正确

- **判定**：**整体不成立（MAJOR；Q-B 的拆分成立，其余两处不足）**
- **Q-B**：把 `READING_COMPLETENESS` 拆为可观测复合门与 blindspot 文档是正确修正；但这不救 P-3，因为盲区清单并不完整。
- **Q-F**：「去掉能力档维度」只做了命名层修正。本稿随即又规定低档模型可默认自动触发 Recipe、高档仅可选（755–757 行），能力档仍改变正式调用策略与有效工具链。更根本地，原铁律禁止为当前 Haiku/当前样本写特供；它不等价于禁止研究一种可泛化、可审计、由图纸特征触发的弱模型辅助界面。降档目标本来就可能通过代码/工具补偿模型能力。正确边界应是工具实现和检测触发只依赖输入特征，模型档不能偷偷选不同工具；若要研究调用策略，单列为实验变量和 provenance，不能口头声称已经消除。
- **§2.3 隔离归属**：不能只藏在 Q-D。P-8 的 CLI/文件/进程通道与 P-5 的 OS、网络、凭据、日志信任根都是跨 Q-C/Q-D/Q-E/Q-F 的系统属性。应增设独立问题「formal run 的输入冻结、角色/凭据隔离、所有入站通道与 GT 污染生命周期如何结构性封闭」，并以威胁模型和红队矩阵验收；否则每个局部 API 都可自称无回调，合起来仍然可干预。
- **探针**：逐条对照细稿 Q-B/Q-F/§2.3：Q-B 有明确 composite + blindspot 输出形态；Q-F 在同一方案内先称去能力档、后又按能力档改变自动触发；§2.3 的验收只检查接口回调，未枚举 P-8 已存在的外部通道。故结论不是三处全错，而是 1 处成立、2 处未完成。

## 2. 清单外自主发现

### F-1 · `candidate_ledger` 的分母不是受信任客观集合（MAJOR）

受审稿 217–225 行称 `cv_evidence` 候选「被测者改不了」。实际上工具侧车落在 staging `out/**`，而现行权限明确允许 worker `Write/Edit(out/**)`；merge 只对 output/守卫/日志摘要建指纹，`_archive_isolation_artifacts()` 不归档 `cv_evidence` 整树。Q-E 放开任意 Python 后更可绕过 hook 直改。因此分母可被删候选、改 ID、改 bbox，而现有指纹不会为此变红。

另外，设计键只有 `{source_tool, candidate_id}`，没有侧车内容哈希/调用 ID/工具参数/工具版本。同一图重复跑同一工具时，候选 ID 是按当次结果序号和坐标现算（`tools.py:245-265`），不是跨参数/跨版本稳定主键。细稿已自报「未逐行核对」，却同时建议该 schema 可立即开工，顺序倒置。必须先定义由沙箱外生成并密封的 `candidate_set_manifest`（候选 canonical fingerprint + sidecar hash + tool/version/params + source-image hash），然后 ledger 只引用该密封集合。

### F-2 · 「更少 blocker = 更优产物」不成立（MAJOR）

Q-D 要在首遍/返工版中按 blocking 集合选「更优」。但 P-3 已证明 gate 有语义、召回、自洽错、方向盲区；返工版可清掉一个自洽 blocker，同时改坏清单内几何或引入盲区错误。细稿把「清单外 stroke 逐字节不变」只放在风险段的「建议补锁」，未放入主方案/必选验收。正确形态应是对密封首遍产物做 worklist-scoped patch，清单外字节不变是必要门；即便如此，「触发检查清零」也只能证明返工完成，不能声称整体质量更优。

### F-3 · reading-agent 按当前规格是 LLM 形状的确定性 copier（MAJOR）

Q-D 明说清单内容 100% 来自 gate evidence，agent 不添加任何新判断，职责只是原样摘出 ID/check_id。这个函数可被几行确定性代码完整实现，且比 Flash LLM 更快、可复算、不会越界。受审稿既要求「能代码化的就代码化」，又为纯拷贝任务引入 agent，架构不自洽。二选一必须说清：若不看图，把它收缩为代码 router；若坚持它是 reading-agent，就必须规格化一个代码不能完成的有界语义职责，并重做 P-1/P-7。

### F-4 · `ReadingProfile` 的模式不变量没有形成类型约束（MINOR）

细稿一面写 `rework_budget`「当前唯一合法值 = 1」，一面又给 `Literal[0, 1]`；同时只用文字规定 autonomous 的 agent 必须为 `None`、controlled 必填，却没有给出 profile 组合的拒绝规则。应把合法组合写成 tagged union 或 model-level validator，并明确 autonomous/controlled 各自允许的 budget、agent 与 isolation mode。否则单字段类型都合法、自相矛盾的组合仍可进入 provenance，报告末端再拒绝已经太晚。

## 3. 追加命题 N-6 · 立面读图方向的校验归属

### N-6-a · 复合 gate① 信号能否顺带抓反向

- **回答**：**不能**。四个信号对水平镜像基本不变：候选仍可 100% 处置；标定 RMSE/比例尺只约束尺度与残差，不编码「正方向来自图像左缘」；尺寸链和式镜像前后相同；逐候选 crop 覆盖只证明 bbox 被调用。一个把所有 x 写成 `W-x` 的产物可以四项全绿。现有 `reading.facade_fields` 又只查字段存在，不补这个信息缺口。

### N-6-b · 是否需要独立答案

- **回答**：**需要，而且应以结构性预防为主、独立诊断为辅**。最终分数低不是 gate① 的答案：低分不能区分方向反、局部量错、漏窗或匹配误差，也无法给 controlled lane 生成有界返工原因。更重要的是，系统性反向未必只表现为低分——若图面近似对称，它可能分数尚可甚至完全不可由 GT 几何区分。契约文字和一个判卷不读取的废弃字段都不约束实际生成行为。

### N-6-c · 可靠判据形态

- **回答**：采用「**甲为主，乙只作密封的 dev 诊断**」，但甲不能停在改字段名。

  1. **结构上消灭自由选择朝向**：canonical 字段只允许 `x_from_image_left_m`（或等义强类型），并把 generic `local_x` 从新产物 schema 移除。更可靠的做法是 worker **不直接写公制 x**：它引用密封源图上的 pixel anchor/interval 与 calibration transform；确定性代码以源图左边界 `px=0`、像素 x 向右为正，唯一地换算 `x_from_image_left_m`。产物同时锁 source-image hash、原始 pixel anchors 与 transform hash；gate① 逐项重算公制 x、查范围及从左到右单调性。这样反向公制数不是一个可被模型自由填写的等价表示。只有字段改名，模型仍可把「距右缘」的数写进 `from_left` 字段，不能算可靠预防。
  2. **不采用已被证伪的端点命中判据**：不得再比较「窗区间是否更整齐地命中产品自己转录的尺寸链端点」。该量错宽度时会偏爱镜像，North 真实反例已足以否决它；上述结构门依赖的是密封源图像素坐标到 canonical 坐标的单值变换，不依赖考生侧链端点。
  3. **乙的区分有条件地站得住**：canonical scorer 始终只算固定 aligned 方向；判卷后由独立 dev/evaluator 用同一 GT matcher 另算 mirrored counterfactual，只输出 `suspected_reversed_local_x`，不改分数、分母、匹配结果或 verdict，也不返回本次 worker/reading-agent。flag 的触发应预注册为「多个独立 opening/component 一致改善且跨过固定 margin」，阈值不能在当前 case 上边看边定；具体 margin 目前**无法从现有材料判定**。
  4. **必须锁非干预性**：诊断开/关时 canonical score、denominator、verdict 与对被测环节可见的 evidence hash 逐字节相同；诊断进独立权限日志。凡开发者看过该 flag/差分细节的 case，立即从该版本 lineage 的验收/晋升证据中烧毁，后续只能在新盲例验证。若 flag 用来替当前产物选 aligned/flipped、触发当前 run 返工、改变分数，或在同一 case 调整后又称其为验证，它就与被否决的 GT best-of 实质相同，换名字也不成立。
  5. **验证集**：先造左右不对称的 aligned/mirrored 成对夹具，再对历史立面离线重放，必须包含审阅单给出的 07-27 North 反例、真实正确方向但局部量错的样本、近似对称/不可判样本。验证目标是误报/漏报与 abstain 行为，不是提高 canonical 分数。

### N-6-d · 排期

- **回答**：插入 **R1.5：R1 之后、R3 gate schema 与 R4 ReadingService 接口冻结之前**。

  - 先钉 canonical `x_from_image_left`、pixel-evidence/transform manifest 与反向字段迁移规则；它们会改变 ReadingView、gate evidence、candidate/worklist 和服务结果，晚于 R3/R4 会造成二次返工。
  - R1.5 的结构门完成后，R2 可并行加入历史离线重放与 synthetic pair，估计乙的阈值和 abstain 区域；dev 诊断不应阻塞第一版结构门，但在宣布 reading 方向问题已解决前必须过反例集。
  - 顺序应为 **R1 → R1.5 方向契约/证据切片 → R3/R4 → R5 → R6/R7**。不得先跑正式新基线/R6 再补方向证据，否则实验把「方向错」与其他质量差混成一个低分，且已经冻结的产物无法补出可信 pixel provenance。

## 4. 无法判定事项与所需实验

以下事项现有产物不足，本审不以推测补洞：

1. **P-1 的最小视觉面到底多大**：无法判定 Flash 需要整图、点名 crop，还是完全不需图。需从同一密封首遍产物做「代码 worklist / 纯文本 Flash / crop-visible Flash」配对分叉，并在 sm21、sm24 各至少两抽比较语义 disposition 修复和清单外不变性。
2. **07-07 的原始干预内容**：事前完整 prompt、pilot r1、transcript 若没有外部备份，就无法再判定；新实验只能验证新假设，不能恢复历史因果。若有备份，需按时间戳/哈希恢复整轮材料再编码每条反馈的视觉信息需求。
3. **gate① 阈值的分辨力与误报率**：需 R2 锁定的历史好/坏产物盲重放，并显式纳入「自洽但全错、候选全处置但分类错、方向反、sidecar 被改」负例；不能只报触发数。
4. **Q-E 是否真能阻断漏题与日志伪造**：纸面路径白名单无法判定。需先实现最小 OS/broker 原型，再按 P-5 红队矩阵从真实 worker 身份执行；保存沙箱外网络/文件/审计证据。
5. **N-6 诊断 margin 与近对称图的 abstain 线**：现有一个 North 反例足以否决旧判据，不足以定新阈值。需预注册 synthetic pair + 历史盲集，报告混淆矩阵；阈值确定所用 case 随即烧毁，不得用于正式验收。
6. **Core 工具的泛化**：三个已知 anchor 不足以建立长期 blind holdout。要判定晋升门，需要新增从未对开发者披露的 case、独立 evaluator 与 lineage 级污染账本；资源不到位时结论应是「不可晋升」。

## 5. 复审前必须回来的最小设计包

1. 把 P-1/P-2 从事实前提改为待验假设，并采用能分离「确定性闭环」和「视觉语义复核」的配对实验。
2. 给 Q-E 一份 OS/网络/凭据/审计信任根明确的威胁模型与红队验收，不再用 hook 字符串解析承诺任意 Python 安全。
3. 将 formal run 非干预提升为独立架构问题，关闭现存 directive/feedback/共享 staging/进程通道。
4. 先密封 candidate denominator 与 pixel-direction provenance，再冻结 gate/ReadingService schema。
5. 改成 lineage 级 GT 污染与 case-burning 晋升门；修正 R6 样本数、处理变量和成本账。

上述 BLOCKER 闭合、MAJOR 有明确设计修改后可复审；本轮不建议按现稿进入 R3–R8 施工。
