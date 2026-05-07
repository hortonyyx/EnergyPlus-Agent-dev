# 行动清单

> **当前状态**：A 段「代码跑通 / 架构迁移」全部闭环（[CLAUDE.md §5.3](CLAUDE.md)）。当前能力主战场切到 B 段「识图建模能力提升」。idfpy 替换主线（[idfpy_embed.md](idfpy_embed.md)）等协作者交付，搁置中。
>
> 优先级：P0（立即）/ P1（一周内）/ P2（依赖 P0/P1）。

---

## 推荐执行顺序

接下来一周：**B0 → B1 → B2 → B3 → B4**（一周内拿到第一份可量化 vision baseline，B4/B5 优化才有反馈环）。
B5 / B6 / B7 等 B1-B4 跑通且 GT 集成熟后再启。

---

## A. 代码跑通（已完成 ✅，2026-05-06）

| 项 | 描述 | 状态 |
|---|---|---|
| A1 | IntakeOutput schema 与协作者 trace 对齐 drift 检查 | ✅ 11 字段 / BuildingSchema 8 / SiteLocationSchema 5 全部一致，无 drift。详见 [CLAUDE.md §5.3.A](CLAUDE.md) |
| A2 | per-subagent LLM 配置（intake / default 两 section） | ✅ [llm.yaml](../src/configs/llm.yaml) 多 section + [llm.py:create_llm(node_name)](../src/agent/llm.py) 路由。详见 [CLAUDE.md §5.3.C](CLAUDE.md) |
| A3 | 端到端验收脚本 | ✅ [scripts/run_full_pipeline.py](../scripts/run_full_pipeline.py)（三入口：全自动 / `--intake-from` / `--intake-only`），原 A3 "preview_geometry 截止 fenestration" 设想被全图脚本替代——下游 DeepSeek 跑近免费，不必砍 |
| A4 | 文档同步（CLAUDE.md / architecture.md / new_case_guide.md） | ✅ 全部修订；[CLAUDE.md](CLAUDE.md) 410 → 175 行精简；[new_case_guide.md](new_case_guide.md) 重写为半人工 7 步流程 |

---

## B. 识图建模能力提升（视觉能力主线）

> **能力主战场是 [architecture.md §3](architecture.md) 表格里"几何依赖：强"的 5 个字段**：`building.name` / `site_location` / `zone_specs` / `surface_specs` / `fenestration_specs`。其余 6 个字段从文本可推，不是瓶颈。
>
> 主指标：[pivot_criteria.md](pivot_criteria.md) 视觉层阈值 — zone F1 ≥90% / 尺寸误差 ≤5% / 走廊 F1 ≥0.85 / 特殊 zone F1 ≥0.80。

---

### B0. [P0] 端到端首跑（验证半人工流）— ✅ 部分完成 2026-05-07

**实跑案例**：`smalloffice_16_newarch`（复制 sm_16 用于测试架构）

**已 PASS**：
- 14 节点机制全部跑通（intake 短路 → phase1 → cross_ref_foundations → construction → surface → fenestration → phase3 → cross_ref_complete → validate → simulate）
- L1 Pydantic ✅ / L2 cross_ref errors=[] ✅
- DeepSeek tool-calling 多轮 ReAct 通（`thinking={'type':'disabled'}` 修复有效）
- 总耗时 ~28 min（surface ~4min / construction ~20min 占大头）

**未通过**：L4 simulate — 卡在 `GeometrySchema.validate_geometry_closure` 几何闭合校验（12/19 zones 有 unclosed 顶点）。**这是下游 surface_agent 的 T-vertex bug**（详见 B0'），不影响架构验证

**架构改造结论**：✅ 半人工 intake + 自动下游联通无机制 bug；剩下是建模质量（Plan B 范畴）

**遗留 todo**（移到 [§8.1](CLAUDE.md)）：
- [ ] sm_17 端到端再跑一次（不同图纸验证可复用性）
- [ ] OpenStudio 验收 sm_15 / sm_16 / sm_17 / sm_16_newarch（用户填 `dimensions_check`）

---

### B0'. [P0] surface_agent T-vertex 缺失（首跑发现）

**bug**：F2 zone 划分比 F1 细 → F1 的 ceiling 被切成 N 片以匹配 F2 → 但**F1 对应的 South/North 墙没在切分处插 T-vertex** → `validate_geometry_closure` 拒收（12/19 zones）。

**实例**（sm_16_newarch F1_North_W）：
- 该 zone 顶上有 2 片 ceiling 共享点 `(3.75, 5, 3.6)` → count=2
- 但 South_Wall 顶边直接从 `(0,5,3.6)` 走到 `(5,5,3.6)`，没在 `x=3.75` 插断点 → 该点最终 count=2 < 3 → 不闭合

**修复方向**（任选其一）：
- A. **改 surface_agent prompt**：硬约束 "当顶 ceiling / 楼板被切成 N 片时，对应 zone 的 4 面墙必须在切分位置插 T-vertex"
- B. **后处理**：[src/converters/surface_converter.py](../src/converters/surface_converter.py) `validate()` 之前自动找未对齐顶点并插入；最稳但复杂
- C. **放宽 validator**：`validate_geometry_closure` 改为只检查首尾闭合 + 邻接 surface 配对，不强制 ≥3 共享。需评估对 EnergyPlus 实际影响

**工作量**：A=~1 天 / B=~3-5 天 / C=~半天但风险大

**验收**：
- sm_16_newarch 重跑 → simulate 通 → IDF 落盘 → `eplusout.end` "EnergyPlus Completed Successfully"
- L4 PASS

**依赖**：B0 闭环（已具备）

---

### B0'''. [P1] 半人工流 token 收集协议升级

**背景**：[test_baseline/README.md §4.1 / §4.3](../test_data/test_baseline/README.md) 强制 `/context` 作为 `tokens.total` 唯一权威源；这是为旧 `yaml_to_idf_v1`（Opus 单会话全流程）设计的，**半人工流下 token 不再单一来源**：
- Opus 端在用户的 Step 4 临时会话 `/context`
- 下游 9 subagent 走 DeepSeek API，token 不在任何 `/context` 里
- 助手协调会话（本仓库会话）的 token 与任务无关，不应计入

临时方案已写进 [README.md §4.5](../test_data/test_baseline/README.md)（2026-05-07 起新增），但是 stop-gap，需要正式升级。

**任务**：
- [ ] 在 [scripts/run_full_pipeline.py](../scripts/run_full_pipeline.py) 加 LangSmith / DeepSeek API usage 收集 hook，落到 `<case>/output/downstream_token.json`
- [ ] 在 [test_baseline/README.md](../test_data/test_baseline/README.md) §4.3 拆出 `4.3a yaml_to_idf_v1` / `4.3b halfmanual_v1` 两套触发执行清单
- [ ] `tokens.json` schema 加 `intake_total` / `downstream_total` / `total` 三字段（`total = intake_total + downstream_total`，缺一为 null）
- [ ] 已存的半人工 anchor（2026-05-07_sm_16_newarch_v4pro_no_sim_v1）回填 downstream_total（如能从 DeepSeek 账单查到）

**工作量**：~半天（hook 代码 + README 拆分 + 一份 anchor 回填）

**验收**：下次跑半人工 case 时 `tokens.json` 自动填齐；`/context` 不再是阻塞条件

**依赖**：B0' 修完后、B1 GT 集前（B1 跑 4 case baseline 时直接走升级版 token 协议）

---

### B0''. [P1] sm_17 端到端首跑

**任务**：
- 用户在新 Claude Code 会话按 [new_case_guide.md §四](new_case_guide.md) 跑 Step 4 → 产 `smalloffice_17/output/intake_output.json`
- 助手按 [§5.0](new_case_guide.md) 触发协议跑下游
- 触发 `记录这次跑 sm_17 e2e_v1` 落 baseline

**验收**：与原 B0 一致；关注 sm_17 是否暴露**新**类型 bug（vs B0' 那个 T-vertex）

**依赖**：B0' 修完（否则同样 simulate 失败）

---

### B1. [P0] 建 GT 数据集（M1 milestone）

**任务**：
- 在每个 case 目录下加 `gt.json`（不另起 `AI_agent/datasets/`，与素材就近）
- 起步集：sm_13 / sm_14 / sm_15 / sm_16（已有人工 baseline 的 4 个），后续扩到 ≥10 case
- 字段（最小集）：

  ```json
  {
    "zones": ["GF_Lobby", "GF_Atrium", "..."],
    "num_floors": 5,
    "zones_per_floor": {"GF": 6, "F2": 12, "...": "..."},
    "footprint_W_m": 40.0,
    "footprint_D_m": 30.0,
    "facade_wwr": {"South": 0.40, "North": 0.25, "East": 0.40, "West": 0.25},
    "special_zones": {
      "atrium": ["GF_Atrium", "F2_Atrium"],
      "core":   ["GF_Core"],
      "server": ["F2_East_Server"]
    }
  }
  ```

- 标注源：手动从 testdata_prompt.json + 已存 baseline + OpenStudio 截图反推

**工作量**：~2 天（4 case × 0.5 天）

**验收**：
- `test_data/SmallOffice/smalloffice_{13,14,15,16}/gt.json` 都存在且字段齐
- 与 [test_baseline/](../test_data/test_baseline/) 现有数据交叉对验

**依赖**：无

---

### B2. [P0] IntakeOutput diff 评测脚本（M2 milestone）

**任务**：
- 新建 `AI_agent/eval/intake_diff.py`：
  - 输入：candidate IntakeOutput JSON 路径 + gt.json 路径
  - 解析 candidate 的自然语言 specs（regex / 二次 LLM 抽结构）
  - 输出指标：

    | 指标 | 计算 |
    |---|---|
    | `zone_f1` | candidate zone 名集合与 GT 的 F1 |
    | `num_floors_match` | 整数对错（0/1）|
    | `zones_per_floor_mae` | 每层 zone 数绝对误差均值 |
    | `footprint_W_err_m` / `footprint_D_err_m` | 外包尺寸绝对误差 |
    | `wwr_mae_pct` | 各立面 WWR 绝对误差均值（百分点）|
    | `special_zone_f1` | atrium / core / server 等特殊 zone 检测 F1 |

  - 输出 CSV 到 `test_data/test_baseline/runs/<date>_<model>_<case>/eval.csv`
- README 到 `AI_agent/eval/README.md`

**工作量**：~1 天

**验收**：
- `python -m AI_agent.eval.intake_diff --candidate <path> --gt <path>` 跑出指标
- 用 sm_17 e2e_v1 baseline 的 `intake_output.json` + sm_15 GT（手工迁移）跑通

**依赖**：B1 数据就位

---

### B3. [P0] Opus baseline 重建（M3 milestone）

**任务**：
- **半人工流**：用户在 Claude Code 会话里按 [new_case_guide.md §四](new_case_guide.md) 跑全部 GT case 一次（4 个 case × ~10 分钟人工 = ~半天）
  - 每 case 产出 `intake_output.json`
- 助手跑 B2 `intake_diff` 对每 case 产 metrics CSV
- 汇总到 `test_data/test_baseline/runs/<date>_opus_baseline/summary.csv`

**工作量**：~半天（用户人工 + 助手脚本）

**验收**：
- summary.csv 给出 zone_f1 / 尺寸误差 / WWR 误差等所有指标的均值
- 与 [pivot_criteria.md §4.4](pivot_criteria.md) 阈值对齐 → 看现状离阈值多远

**依赖**：B0 + B1 + B2 + 用户重复 Step 4 四次

> 注：原 plan.md "Anthropic API 直跑 4 case" 方案因用户无 API key 已废；改为半人工。

---

### B4. [P1] CoT prompt 优化

**背景**：视觉非首要瓶颈但确实是 zone 几何错的直接原因，分步 CoT 收益明确。**2026-05-06 DeepSeek smoke test 还暴露了一个新约束**：禁用 `Floor_N_*` / `for N in ...` 模板写法（已临时打补丁在 [new_case_guide.md §4.2](new_case_guide.md) Step 4 prompt 里）。

**任务**：
- 改 [intake.py INTAKE_SYSTEM_PROMPT](../src/agent/nodes/intake.py#L34) 为分步：
  1. 先识别外墙边界（输出闭合多边形）
  2. 再读尺寸链数字（自检 `sum(segments) + 2 × wall ≟ total_width`）
  3. 再识别走廊（宽白连通区）
  4. 再识别楼梯 / WC / 电梯符号
  5. 综合为 zone 列表 + x/y 范围
  6. 再生成 surface 邻接矩阵（可机械推导）
- 每个子步骤用 Pydantic 中间结构约束（避免开源模型自由发挥）
- 把 [new_case_guide.md §4.2](new_case_guide.md) 的 Floor_N_* 模板禁用规则正式合并进 INTAKE_SYSTEM_PROMPT
- A/B 比对 B3 baseline

**工作量**：~1 周

**验收**：
- 跑 B3 同一 4 case，zone_f1 / 尺寸误差对 baseline 提升
- 提升幅度落到 `test_data/test_baseline/runs/<date>_capability_cot_v1/notes.md`

**依赖**：B3 baseline 落档

---

### B5. [P2] PaddleOCR + cv2 预处理 hook

**背景**：尺寸链 OCR 用 PaddleOCR、走廊用 cv2 形态学，是方案 2 最低 ROI 的子模块，但收益直接（解决"尺寸 OCR 错"+"走廊漏识别"两个具体问题）。

**任务**（半人工流下做法变了）：
- 新建 `Tool_scripts/preprocess_floor_plan.py` —— **不再插到 graph.py 里**（半人工流 intake 在 Claude Code 会话外）
  - 输入：image_paths
  - 用 PaddleOCR 提平面图所有数字 + 坐标 → JSON
  - 用 cv2 形态学找宽白连通区 → 走廊候选 bbox 列表
  - 输出 `<case>/output/preprocess.json`
- 在 [new_case_guide.md §四](new_case_guide.md) Step 4 prompt 模板里加一段「预处理结果（可信度高）」，让用户先跑预处理脚本，把结果贴给 Opus 当 hint

**工作量**：~3-5 天

**验收**：
- B3 同一 4 case，footprint_W/D_err / wwr_mae 对 B4 进一步下降
- 落 `test_baseline/runs/<date>_capability_preprocess_v1/notes.md`

**依赖**：B4 完成（避免变量耦合）

---

### B6. [P2] 开源模型评测（M4 milestone）

**任务**：
- 部署 vLLM + Qwen2.5-VL（先 7B，再 32B / 72B）/ DeepSeek-VL
- 把 [llm.yaml](../src/configs/llm.yaml) `intake` section 切到 vLLM endpoint（A2 已就绪）
- 半人工流改全自动：把 Step 4 从 Claude Code 会话改成 `python scripts/run_full_pipeline.py <case>` 直接走 vLLM
- 跑 B2 同一套评测
- 横向对比 Opus baseline + CoT + 预处理 + 开源模型四档

**工作量**：~1 周（含部署 + 调参）

**验收**：
- 候选模型至少一档达 Opus 80%+（[pivot_criteria.md §4.4](pivot_criteria.md) 阈值）
- 落对比表到 [open_model_guide.md](open_model_guide.md)

**依赖**：B4 + B5 完成

---

### B7. [P3] LoRA SFT + Pivot 切换（M5/M6）

**任务**：
- 见 [pivot_criteria.md §4.1](pivot_criteria.md)：用 Opus baseline 的 IntakeOutput JSON 集合作 SFT 数据种子（≥500 对，需扩 GT 集到 ≥10 case）
- LoRA 微调候选开源模型
- holdout 集评测达 Opus 80% 后切 [llm.yaml](../src/configs/llm.yaml) `intake` 默认 provider
- 全量回归

**工作量**：~2-3 周

**验收**：[pivot_criteria.md](pivot_criteria.md) 全部阈值达标

**依赖**：B6 完成 + Pivot 阈值达标判定

---

## C. 暂搁置（依赖外部进展，不安排时间）

- **idfpy 替换主线**（[idfpy_embed.md](idfpy_embed.md)）：等协作者完成 [§3.1 MCP 全线重写](idfpy_embed.md)；本项目侧 §3.2 等他们交付后再启
- **token_optimization §4.1-4.5**（[token_optimization.md](token_optimization.md)）：等 idfpy 切换完成后大量 CRUD 工具消失，重新评估
- **OpenStudio 几何验收 sm_15/16/17**（[CLAUDE.md §8.1](CLAUDE.md)）：用户人工跑，不卡代码

---

## D. 与 Milestone（[CLAUDE.md §4.3](CLAUDE.md) — 注：§4.3 在精简版中已删除，原映射如下）

| Milestone | 对应本文 TODO |
|---|---|
| M1（多模态 golden 数据集 v0.1）| B1 |
| M2（自动评测脚本）| B2 |
| M3（Opus baseline 重建）| B3 |
| M4（vLLM + 开源模型评测）| B6 |
| M5（gap 修补：prompt / few-shot / 微调）| B4 + B5 + B7 |
| M6（切默认 provider，全量回归）| B7 |

---

## 关联文档

- [architecture.md](architecture.md) — 当前架构事实参考
- [CLAUDE.md](CLAUDE.md) — 项目管理总览（精简版）
- [new_case_guide.md](new_case_guide.md) — 新建测试样例 7 步流程（半人工版）
- [pivot_criteria.md](pivot_criteria.md) — Pivot 双阈值
- [open_model_guide.md](open_model_guide.md) — 开源模型操作手册
- [idfpy_embed.md](idfpy_embed.md) — idfpy 替换主线（搁置中）

---

_2026-05-07 — A 段四项全闭环（A1 schema drift PASS / A2 多 section LLM / A3 run_full_pipeline 三入口 / A4 文档全修订），从主体下沉到表格；新增 B0 sm_17 端到端首跑作为半人工流验证；B3 改半人工版（用户无 Anthropic API）；B4 加入 Floor_N_* 模板禁用补丁；B5 改 Tool_scripts 预处理脚本（半人工流 intake 在会话外）；B6 footnote 去掉 A2 依赖（已就绪）；C 段加 sm_17。_

_2026-05-05 全文重写。删旧版 CoT vs 前置小模型探讨；按 architecture.md 新架构理解重组为「代码跑通 + 识图能力」两线 TODO。_
