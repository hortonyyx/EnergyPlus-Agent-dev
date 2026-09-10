# 任务3独立报告：reading单/双线出口下一步方案比较

范围说明：本任务独立完成，未读取本轮其他助手的产物或结论，仅用 Read/Grep/Glob 核对原始代码与产物，未调用模型、未跑仿真、未改文件。

## 一、三个方案对照代码核实后的真实定义

用户给出的 A/B/C 是待比较的**假设方案**，不是既定标签。核实源码后，三者对应仓库里两套**并存且路由分离**的真实实现，而不是三个候选设计：

| 方案 | 用户表述 | 对照代码后的实际情形 |
|---|---|---|
| A | reading直接出单线 | 即历史 `ReadingView.strokes`（`src/agent/reading/schema.py:34-56`）：每笔画一条线，`geometry`含`p1/p2/thickness_m`，`provenance∈{seen,dimension_derived,estimated,unknown}`。07-07、08-20 S1 等"好reading"全部是这个格式，好结果**同时依赖**测量工具箱（`crop_zoom`/`wall_line_profiler`/`px_m_calibrator`）与pilot停等门，不是"模型自由画单线"就够。 |
| B | 保留双线证据，后续解释为单线 | 即 `as_drawn_plan_v2`（`src/agent/reading/as_drawn/schema.py`）：`observations.face_lines`是逐条测到的墨迹面线（一堵墙通常两条面线），`hypotheses.pairs`是"认"出的配对（谁与谁是同一堵墙）。 |
| C | 同时保存原观测与派生单线 | **代码已经这样做，不是待选项**：`ResolvedWallV1`（`src/agent/correction/wall_compiler.py:270-293`）里`source_claim_ids`/`source_refs`指回原始`face_lines`，`resolved_centerline`是派生单线，两者同存一条记录，不是B描述的"解释完就丢"。 |

**关键发现**：B和C不是两个独立可选架构，而是同一条 as-drawn 管线在"是否保留可追溯引用"上的实现细节，当前代码已经按 C 的方式实现了 wall_compiler 层。所以真正的选择不是"B还是C"，而是"A（legacy单线）还是 as-drawn（双线观测+可追溯单线派生，即B/C合一）"。

## 二、09-09失败反例不能用来裁定A/as-drawn优劣（回答"是否预设答案"的核心证据）

核实 `AI_agent/logs/experiments/2026-09-09_automatic_source_sm21_run01`：

- `run/0_reading/1f_view.json` 第11行是 `"strokes": [...]`——本次冷启动走的是**A（legacy单线）**，与 as-drawn（B/C）完全无关，`automatic_reading.py`全文档没有一处引用 `as_drawn`（已grep核实）。
- `reading_summary.md` 第93行模型自述："Without pixel-to-meter calibration via CV tools, interior wall positions are visual estimates"——即**模型自己承认没有按规矩用测量工具**，尽管 `skills/intake_pipeline/0_reading/cv_toolbox.md` 第114行明文写着"Measure before drawing... Do not write pure eyeballed coordinates"，且该skill文件确实被打包进了本次隔离环境（`isolation_archive/MANIFEST.json`第85-112行）。
- 与之对照，历史唯一在**当前代码树、全六图**上复现9/9·7/7·15/15的`run_2026-08-20_acceptance_sonnet_S1`，`run_config.yaml`第34行`review.reading: true`——**pilot停等门开着**，且有Opus做orchestrator审第一张图。09-09 run01是"显式关闭pilot"跑的（`2026-09-10_session_wrapup.md`第10行）。

**结论**：09-09失败的两个已知直接原因（工具箱未被有效使用、pilot门被关闭）都发生在A路径内部，且恰好复现了07-05控制组、08-15 A2/B1/D1等历史失败模式的共同特征——**与"该不该换成双线架构"无关**。如果其余两项任务把这次失败当作"应该转向as-drawn"的证据，属于把"这次没按历史好配方跑"误读成"这个配方本身不行"，是一种预设答案的风险；反过来如果因此断定"应该继续单线、放弃as-drawn"，同样缺乏依据，因为as-drawn根本没有被这次实跑测试过。

## 三、as-drawn（B/C）路线的真实完成度：尚未被真实模型独立验证过

核实 `AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/README.md`：

- 第557行（§七第7条，原文明说）：**"本轮perception由主控产出、且主控此前已看过gt侧结果 ⇒ 探索档，「模型能不能做到」这个问题本轮没有回答，要冷启隔离读图器才算数。"** 即 gt侧93.3%（sm25）/100%（sm24）这些分数，是开发者本人（已见过GT）替代模型完成的"认"（family_roles/pairs配对），不是模型自主判断的结果。
- 第555行：sm24 98条面线里78条被"认"为无法判断（`ambiguous`/弃权），只对20条下了判断——说明即便是人工、已见GT的情况下，配对判断的覆盖率也不高，模型自主判断的负担和出错空间可能更大。
- 09-02b（`2026-09-02b_m7_evidence_chain_run/README.md`）是correction决定环唯一一次真实模型调用，用的是**DeepSeek**（未获本次授权），且只跑了sm25 2F一张平面的厚度决策，不是完整建筑判断，也不是Claude订阅通道。

**结论**：as-drawn（B/C）在"代码测量+可追溯派生"这一半有扎实实现（`as_drawn_v2.py`确定性CV测量、`wall_compiler.py`可追溯编译、11条不读GT的判据），但"模型认（family/pairs/门窗身份）"这一半从未被自主模型在盲测条件下验证过，也从未接入`automatic_reading.py`冷启动入口。

## 四、比较表

| 维度 | A（legacy单线） | as-drawn（B/C合一） |
|---|---|---|
| 墙基准/厚度 | S1好结果里墙用测量中线、窗用名义链位置，两套基准混用未被扫描器发现（`reading_fixtures.json`第101行`known_defects_note` R-2） | 面线各自独立测量，中线由代码从两面派生，基准更自洽，但仅在人工替代perception下验证 |
| 门洞/连通 | 07-07等好reading靠模型直接画门；09-09失败样本证明"门被压平进墙"是A路径真实风险 | 门窗身份判定"没有外置"（README第550行原话），当前六桶里没有逐洞口身份桶，仍是已知缺口 |
| 观察/推断分开 | Stroke.provenance区分seen/estimated，但provenance不能当路线判据（good_reading文档§4.3第204行已证伪） | observations/hypotheses物理分层，结构性更强 |
| 模型判断负担 | 每笔画一次性下决定，负担集中在画的那一刻 | 拆成"认族/配对/命名洞口"多步判断，单步负担轻但步骤多，sm24实测判不出的比例高（78/98） |
| 可复用模块 | `automatic_reading.py`+`ReadingView`已端到端接通冷启动 | `as_drawn_v2.py`测量、`wall_compiler.py`编译、`decision_executor.py`决定环已各自实现，但彼此之间、以及与冷启动入口之间**未接通** |
| 实现代价 | 低：已有入口，缺的是"按历史配方跑"（工具箱纪律+pilot门) | 高：需新增"perception模型化"、门窗身份外置、接入`automatic_reading.py`，且需要真实模型（非DeepSeek）验证 |
| 质量/时间成本 | 历史好结果单图约$7-8、全案受5小时会话窗口限制需分段跑（good_reading文档第174行） | 无真实模型run的成本数据，只有确定性CV测量的耗时（未记录） |

## 五、不依赖新实验即可得出的结论

1. 09-09失败不能作为否定A或肯定as-drawn的证据——失败发生在缺失历史成功配方（工具箱纪律+pilot门）的A路径内，两个已知缺陷与线表示法无关。
2. as-drawn的B/C不是两个独立方案，当前`wall_compiler.py`已按C（观测+可追溯单线并存）实现，用户框架里的B应理解为C的一个更弱子集，不必单列比较。
3. as-drawn路线"模型能不能做双线到单线的认"这个核心问题至今没有被真实模型回答过（README第557行原话），这条结论**不需要新实验**，因为过往实验本身已明确写出了这个局限。
4. 单线路线的历史成功强依赖测量工具箱与pilot门，不是"模型直接画单线"本身。

## 六、不能得出的结论（需要新实验才能回答）

1. as-drawn双线观测在真实模型（非人工替代perception）盲测下，是否真能比A更好地保住门洞/分区——无证据支持或反对。
2. as-drawn的模型判断步骤增多，是否会带来更高的总成本/更多轮次失败——无成本数据。
3. A路径若严格恢复工具箱纪律+pilot门，在当前代码树、当前门窗更复杂的sm21/sm25全案上是否还能复现9/9这类结果——08-20 S1只做了reading单阶段验收臂，未接correction/建模全链路。

## 七、"必须全用某种表示"的主张：证据不足，是取舍不是定论

无论是"必须用legacy单线"还是"必须用as-drawn双线"，仓库里都找不到支持"唯一正确表示"的证据。两条线各自的已知短板（A的门/分区易失真，as-drawn的perception未经模型验证）说明这是**按具体图纸类型/复杂度做的工程取舍**，不是可以论证到"非此不可"的问题。

## 八、推荐的有界下一项与验收标准

**推荐**：不切换架构，先在A路径上做一次**受控复现实验**，检验"09-09失败是否确由缺工具箱纪律+缺pilot门解释"，而不是急于改造as-drawn。

- 输入：sm21六张原图（与run01相同案例），显式恢复：①per-run directive重申"measure before draw"（与08-20 S1同源指令）②开启pilot停等门（先出1F、人工/orchestrator审过再放量）。
- 执行方式必须标注三选一：历史replay（复用旧reading）、人工辅助（开发者补齐perception或决定）、新冷启动（模型独立完成，无GT可见）——本次应做**新冷启动**，且需在报告中显式声明。
- 验收（可判定成功/失败）：内部隔墙0自由端、门有ID+端点+宽度（不被压平进墙）、`dimension_chain_closure`至少plan视图通过、CV工具调用次数与好reading历史量级（个位数到几十次，非0-1次）相当。任一项不达标即判失败，不靠放宽检查掩盖。
- 若该受控复现仍失败，才有理由认为问题不止是纪律缺失，需要认真评估as-drawn是否值得接入`automatic_reading.py`；若成功，as-drawn的优先级应让位于先把A路径在sm24/sm25更复杂案例上跑通。

## 九、未核实事项

- as-drawn的`decision_executor`是否曾在Claude订阅通道（而非DeepSeek）上跑过任何真实决策——未在本次范围内找到证据，需要向另两项任务或后续实验确认。
- F-88（门垛几何判定缺陷是否污染已签字gt.json的厚度证据）README自称"未查"，本任务未展开核实。
- 08-20 S1之后是否有correction/建模阶段的全链路验收——本任务只核实了reading单阶段的run_config.yaml，未继续追踪该run后续是否有1_correction产物。