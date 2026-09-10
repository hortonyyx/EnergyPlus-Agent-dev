# reading / correction 架构演变与现有真实接线核查（任务2）

**方法**：全程只用 Read/Grep/Glob 读本仓库代码与原始产物，未跑模型、未跑 EP、未改文件。下文【实证】=我直接打开的代码/产物；【二手】=只见于历史总账文档；【推断】=基于实证的合理推理；【未核实】=有矛盾或找不到直接证据。不把旧 judge 分数当源 BIM 通过证明。

## 一、单线→三层→路由落地的演变时间线

| 时间 | 事件 | 依据 |
|---|---|---|
| 07-02～08-20 | "好 reading"实际产出：墙笔画全是 `kind:"line"` 单线段，基准按构件类型混合（外周墙=外皮线，内部隔墙=中线），**写在自由文本 note 里，不是结构化字段**（如 sm21/sm24 `S1.note`="outer face"/"中线"）；门洞多数只在 note 里提一句"healed door opening"，不是独立开口对象 | 【实证】`case_tests/e2e_tests/sm21_anchor/run_2026-07-07_haiku_cv_retest/0_reading/1f_view.json`、`sm24_anchor/run_2026-07-07_haiku_cv_probe/0_reading/1f_view.json`（任务1核查已交叉验证） |
| 08-23 | 用户拍板"reading/correction 两轴新分工"：认=模型、量=代码、对账=代码门；correction 三拍循环（代码列歧义→模型裁决→代码落坐标）立项，是为解决单线"reading 读得好就不需要 correction"的分工塌陷 | `AI_agent/archive/2026-09-08_pre_takeover/guides/reading_correction_split_guide.md:12-24` |
| 08-23～08-25 | as-drawn 三层产物（observations/declarations/hypotheses）定型，"哪两条线是一堵墙"的配对判断从代码按阈值改为模型选、代码对账；"reading 判像不像/correction 判对不对"的分工写死 | 同上 §一、§四 |
| 08-25 | `as_drawn_v2.py` 落地为**纯像素量具**：只测线/空档/剖面，"族角色"（谁是墙/门窗）仍靠**外部注入的 perception**，当前是配置/开发者手填，不是模型产出 | 【实证】`src/agent/reading/as_drawn/as_drawn_v2.py:37-51` |
| 08-30～09-02 | correction 证据契约（六形态→三正交契约）定稿；decision_executor（module 6，三拍环骨架）落地，**明写"model once module 7 lands"** | `decision_executor.py:1-10`【实证】 |
| 09-02 | module 7（真模型接入）真正落地：`pipeline.run_correction_evidence_chain` 可用 `_make_decision_response_provider` 接一个真实模型做"整体接受"裁决；**唯一一次真跑用了历史 DeepSeek 通道**（`run_win_e2e`） | 【实证】`case_tests/.../run_win_e2e/1_correction/_run/evidence_chain_route.json`：`llm_model_resolved:"deepseek-v4-pro"` |
| 09-07～09-08 | W-1 路由表落地：`_w1_route_correction` 按 0_reading 产物的**契约分类**（不是文件名/配置）二选一走 legacy 或 as_drawn 腿；补窗（`populate_as_drawn_windows`）、补洞（`populate_as_drawn_openings`）、`wall_gap_review.py`（走廊连续性冻结决定）陆续接入 as_drawn 腿 | 【实证】`scripts/tool_scripts/run_stage.py:417-488, 546-745` |
| 09-09 | sm25 29 空间重建**明确记为"developer_assisted"人工辅助判读**，不是模型产出 | 【实证】`AI_agent/logs/worklog/2026-09-09_m0_wall_gap_review.md` |

## 二、现有真实接线（分支/输入/输出/状态）

| 模块 | 输入 → 输出 | 状态 |
|---|---|---|
| `automatic_reading.py`+`isolation.py` | 原图 PNG → **legacy `ReadingView`**（strokes，模型自由绘制单线，可选调用像素探针工具，但产物 schema 仍是 legacy） | **live wired**（`flow --reading-model` 真实入口） |
| `_w1_route_correction` | 0_reading 产物 → 按 `classify_vector_json` 契约二选一 legacy/as_drawn | **live wired**，`run_stage.py:417` |
| legacy 腿 `_draw_correction`→`pipeline.run_correction` | 一次性大 prompt："world-frame, wall-centerline, self-consistent room cells"，模型自由产出整栋几何 JSON | **live wired**，但是"模型再次自由写整栋几何"的旧模式（`pipeline.py:421-424`），正是09-09 sm21 失败的那条线 |
| `as_drawn_v2.py`（像素量具） | 原图 → observations/declarations/hypotheses；族角色需外部 perception | **implemented，但未接自动入口**——不是 automatic_reading 的产物来源 |
| `_draw_correction_as_drawn`→`run_multifloor_correction` | as_drawn 契约产物 → 每层调 `run_correction(evidence_chain=True,...)` | **live wired** |
| `decision_executor.py`（module 6/7，三拍环） | `WallCompilationV1` open_items → 模型裁决 → 重编译 | **live wired 但默认走 DeepSeek**：`MultiFloorPlanRun.fixed_responses=None`（生产默认），`llm.yaml` 的 `correction_decision` 段默认 `deepseek-v4-pro`（`src/configs/llm.yaml:81-91`）。**这与项目"DeepSeek 需逐次许可"的规则直接相关，需要下一步确认近期 sm24/sm25 重建是否真的走了这条真模型环，还是走了下面的 replay 分支** |
| `wall_gap_review.py`（走廊连续性判定） | 冻结决定文件（`review_mode: developer_assisted/model/user`）→ 确定性拆分续接 | **manual/replay-only**：sm25 实际用的是 `developer_assisted`（开发助手看原图填），不是模型；一旦决定文件存在，走 `chain_replay.py` **纯重放**，不再调模型 |
| `chain_replay.py` | 冻结 compilation 字节 → 重建 producer，byte-compare | **replay-only**（写入前审计锁，不产生新判断） |
| `evidence_adapters.py`：`adapt_legacy_reading_view` | legacy `ReadingView` → `CorrectionEvidenceBundleArtifactV1` | **implemented + wired**（被 `run_correction_evidence_chain` 消费），**但 `run_stage.py` 从未把 legacy 契约路由到这条腿** |

## 三、逐问回答

**1) 谁判断基准/门洞/墙拓扑/跨图**
- **基准**：legacy 单线的外皮/中线选择完全由模型在自由文本 note 里声明，**没有结构化字段**，correction 提示词还额外要求"wall CENTERLINE"（`pipeline.py:421-424`），即遇到外皮线基准的历史产物，模型还要在 correction 里再做一次基准换算，全程无代码校验。as_drawn 腿则约定"中线只允许 correction 内部代码派生，不回写"。
- **门洞**：reading 层（无论 legacy 还是 as_drawn）都只给证据，不给最终判定；as_drawn 腿的最终门洞由确定性代码 `populate_as_drawn_openings` +（如有歧义）`wall_gap_review.py` 冻结决定生成，**近期实例是人工/开发助手判读**，不是模型。
- **墙拓扑（哪两条线是一堵墙）**：唯一有模型真正做过这个判断的证据是 `run_win_e2e` 一次 DeepSeek 调用；`decision_executor` 本身有完整代码但生产默认仍要经过 `correction_decision` 模型段。
- **跨图（楼层/立面）**：`_w1_cross_check_elevation_ladders`+`derive_floor_ladder` 是纯确定性代码，零容差 tuple 比较，**无模型介入**（`run_stage.py:491-543`）。

**2) 今天 `flow --reading-model` 实际走哪条**
自动读图入口（`automatic_reading.py`）**只产出 legacy ReadingView**，因此 `_w1_route_correction` 永远判定"legacy"，进入一次性大 prompt 的 `run_correction`——这正是 09-09 sm21 失败的那条线（Sonnet 校正首请求 600 秒超时）。as_drawn 腿目前**结构上不可达**于这个自动入口，只能从人工/半人工准备好的 as_drawn 契约产物进入。

**3) legacy 单线复用决定执行器的边界**
代码层面已经打通：`adapt_legacy_reading_view` 存在且被 `run_correction_evidence_chain` 承认（`evidence_adapters.py:842`）。但实测探针显示（本轮 `legacy_adapter_probe.json`）：三份历史"好"legacy 产物喂进去后，**wall_claims 全部 `source_basis=unknown`，`resolved_centerlines=0`，open_item 全是笼统的 `legacy_basis_unknown`，没有真正的候选配对项**，且窗/门笔画因是文字提及不是独立对象而被记为 `missing_channel`。也就是说：legacy 单线已经把"两条面线该不该配成一堵墙"这个决定在 reading 阶段做掉了（模型直接给一条线代表一堵墙），decision_executor 在这种输入上**没有真歧义可裁决**，能复用的价值主要是下游确定性装配、开窗/开洞填充和重放审计契约，**不是**它原本设计要解决的"墙面配对歧义"。真正要接，还需先改 `_w1_route_correction` 让 legacy 契约也走 evidence chain 腿，且要接受下游净空/宿主解析会因 `basis=unknown` 而更弱。

**4) as-drawn 现有模块的不完整之处**
- "认"（族角色/wall_pairs）仍是外部注入，非模型产出，08-25 架构文档写的盲区原样未解决（未验证是否有后续变化）。
- decision_executor 真模型环仅一次真跑（DeepSeek，`run_win_e2e`），近期 sm24/sm25 的"好"结果多为 `developer_assisted` 人工判读或纯重放，**没有反复证明模型能独立做这一步**。
- `wall_gap_review.py` 只覆盖"同墙缺口是否连续空间"一种歧义，wall_compiler 的候选配对歧义仍要靠 decision_executor。
- 立面侧回叠检查、尺寸链逐条钉墙覆盖率等 08-25 架构文档记的历史盲区，本轮未重新测量，状态未核实。

## 四、未核实事项与下一步
- 近期 sm24/sm25 的 `_draw_correction_as_drawn` 真实运行是否触发了 `correction_decision`（默认 DeepSeek）的真实调用，还是全部落在 `wall_gap_review` 冻结重放分支——本轮未找到这些具体 run 的 `evidence_chain_route.json`，需要下一步逐个核对，这直接关系到 DeepSeek 许可合规。
- as_drawn 立面回叠检查、尺寸链覆盖率现状未重新测量。
- 是否有办法让 automatic_reading 的隔离读图器直接产出 as_drawn 契约（而非 legacy），未验证，是让"自动入口"接上 as_drawn 腿的前提之一。