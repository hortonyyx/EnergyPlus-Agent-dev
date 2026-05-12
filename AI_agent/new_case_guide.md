# 新建测试样例操作指南（2026-05-06 重写，2026-05-12 B1 对齐）

> 面向 [../test_data/SmallOffice/](../test_data/SmallOffice/) 下新增一个 SmallOffice 测试案例的标准流程。
>
> **2026-05-12 B1 对齐**：
> - 跟 [plan.md B1](plan.md) "旧 skill 能力迁移 + 关键硬约束补强" 同步：Step 4 自检 checklist 加 per-floor window chain / absolute world z / cross-floor split-pairing 三条硬约束；§八 加入 sm_18 / sm_19 真踩过的两类典型坑
>
> **2026-05-06 重写背景**（详见 [CLAUDE.md §7.13](CLAUDE.md)）：
> - 架构定位修订：本项目侧职责仅到 `IntakeOutput` Pydantic 对象；下游 9 个 subagent + simulate 由 [src/agent/graph.py](../src/agent/graph.py) 自动跑（[architecture.md](architecture.md) §1）
> - LLM 分工（[src/configs/llm.yaml](../src/configs/llm.yaml) 多 section）：**intake = Claude Opus 4.7**（手动，订阅）／**下游 9 subagent = DeepSeek V4 pro**（自动，API）
> - 流程从「整条 MCP 工具链人工驱动」变为「半人工 intake + 自动下游」
> - 实验日志归档目录从 `AI_agent/experiments/` 迁到 [../test_data/test_baseline/runs/](../test_data/test_baseline/runs/)
>
> **2026-04-29 历史背景** 仍生效：素材规范使用 schema A（`Floor plans` 数组），共享外包硬约束（每层 W × D 一致），立面图按朝向命名。

---

## 零、流水线总览

```
Step 1 准备视觉素材  →  Step 2 建案例目录  →  Step 3 写 testdata_prompt.json
   ↓ （以上同旧流程）

Step 4 半人工 intake（Claude Code 会话 + Opus）
   - 投递 INTAKE_SYSTEM_PROMPT + 图 + JSON
   - 产出：<case>/output/intake_output.json （IntakeOutput Pydantic）

Step 5 自动跑下游（DeepSeek V4 pro 驱动）
   - python scripts/run_full_pipeline.py <case> --intake-from output/intake_output.json
   - intake_node 短路 → 9 个 subagent 并行/串行 → cross_ref → validate → simulate
   - 产出：<case>/output/<case>.yaml + .idf + eplusout.*

Step 6 验证（4 层）+ Step 7 留痕到 test_baseline/runs/
```

旧 Step 4「挂 MCP 服务器 + 投递 3 份 skill 文档让 Opus 调 MCP」流程 **已弃用**——现在 MCP 工具由 [src/agent/tools/](../src/agent/tools/) 在 in-process 包装后给 9 个 subagent 直接用，无需挂 server。旧版本备份在 [backup/new_case_guide.md.bak_2026-05-06](backup/new_case_guide.md.bak_2026-05-06)。

---

## 一、Step 1 · 准备视觉素材

> **本节与旧版完全一致**——素材规范没变。

立面图**按朝向命名**，每个文件代表其所**面朝**的立面。1–4 张立面图均可，未提供的朝向按无窗处理。

| 文件名（强约定） | 必需 | 内容 |
|---|---|---|
| `{k}f_view.png`（k=1..N） | **必需** | 第 k 层平面图，含尺寸标注；外包围 `W × D` 必须每层一致 |
| `top_view.png`（旧） | back-compat | 单张共享平面图（仅当所有层内部分区相同时使用） |
| `South_view.png` | 可选 | 南立面（y=0 立面） |
| `North_view.png` | 可选 | 北立面（y=y_max 立面） |
| `East_view.png` | 可选 | 东立面（x=x_max 立面） |
| `West_view.png` | 可选 | 西立面（x=0 立面） |
| `supp_plan.png` | 可选 | 补充平面 / 剖面 / 轴测 |

### 1.1 尺寸标注规范

逐层平面图每张要画完整尺寸链；走廊画成宽白带（≥ 房间 1/3 宽）；楼梯/WC/电梯画标准符号。两级尺寸链：
- 一级（外部）：总开间 / 总进深
- 二级（外部）：分段开间 / 分段进深
- 单位统一 `mm`；坐标原点 = 左下角 (0, 0)，x 向右、y 向上

立面图：左侧标层高链（各立面一致）；右侧标 `top_gap | window_height | sill_height`；底部标窗水平位置链；标 Z=0 室外地坪。

详细规范（字体 / 引线 / 禁忌）见旧 [backup/new_case_guide.md.bak_2026-05-06](backup/new_case_guide.md.bak_2026-05-06) §1.1，本次未变更。

### 1.2 `testdata_prompt.json` 字段约定（schema A）

| 字段 | 说明 |
|---|---|
| `TestName` | 与目录名严格一致（`smalloffice_17` 全小写下划线） |
| `Building location` | 气象数据文件名映射；当前仅有 [../data/weather/Shenzhen.epw](../data/weather/Shenzhen.epw) |
| `Floor area` | 总建筑面积字符串（可空） |
| `Building type` | `Office` 等 |
| `Number of floors` | 整数；与 `Floor plans` 长度一致 |
| `Floor plans` | **必填**，数组：`[{"floor": k, "path": "{k}f_view.png", "thermal_zones": int}, ...]` |
| `Top view path of the building` | back-compat；新案例留空 |
| `{South,North,East,West} view path of the building` | 可空。空串 = 该朝向无窗 |
| `Path of the supplementary plan example drawing for the building` | 可空 |

---

## 二、Step 2 · 建案例目录

```powershell
$case = "smalloffice_17"
mkdir -p "test_data/SmallOffice/$case/output"

# 逐层平面图
cp /path/to/1f_view.png  "test_data/SmallOffice/$case/1f_view.png"
cp /path/to/2f_view.png  "test_data/SmallOffice/$case/2f_view.png"

# 立面图按实际有窗情况挑选
cp /path/to/South_view.png "test_data/SmallOffice/$case/South_view.png"
# ...
```

---

## 三、Step 3 · 写 `testdata_prompt.json`

模板（以 sm_17 为例，按图纸改写；参考 [smalloffice_16/testdata_prompt.json](../test_data/SmallOffice/smalloffice_16/testdata_prompt.json)）：

```json
{
    "TestName": "smalloffice_17",
    "Building location": "Shenzhen",
    "Floor area": "240m²",
    "Building type": "Office",
    "Number of floors": 2,
    "Floor plans": [
        {"floor": 1, "path": "test_data/SmallOffice/smalloffice_17/1f_view.png", "thermal_zones": 7},
        {"floor": 2, "path": "test_data/SmallOffice/smalloffice_17/2f_view.png", "thermal_zones": 7}
    ],
    "South view path of the building": "test_data/SmallOffice/smalloffice_17/South_view.png",
    "North view path of the building": "test_data/SmallOffice/smalloffice_17/North_view.png",
    "East view path of the building":  "test_data/SmallOffice/smalloffice_17/East_view.png",
    "West view path of the building":  "test_data/SmallOffice/smalloffice_17/West_view.png",
    "Path of the supplementary plan example drawing for the building": ""
}
```

---

## 四、Step 4 · 半人工 intake（Claude Code 会话）

> **目标**：在一个独立的 Claude Code 会话里用 Opus 看图 + 设计意图 → 产出 `IntakeOutput` Pydantic JSON。**不调用任何 MCP 工具**，最终把 JSON 存到 `<case>/output/intake_output.json`。

### 4.1 启动 Claude Code

在仓库根 `c:/Users/Horton/Desktop/科研2/EnergyPlus-Agent-dev/` 启动**新的** Claude Code 会话（不是当前正在干活的那个）。模型选 **Claude Opus 4.7**。

### 4.2 投递 prompt

把下面整段（`---` 之间的部分）作为**第一条消息**贴给会话。

```text
请按 EnergyPlus-Agent 项目的 INTAKE 流程，从给定的建筑设计意图（文本 + 平面图 + 立面图）产出一个严格符合 IntakeOutput Pydantic schema 的 JSON。

在开始产出前，你必须先读取以下规则来源，并把它们视为一个整体的 intake 规则库：
- src/agent/nodes/intake.py
- skills/energyplus_mcp/ 目录下全部 `.md` 文件

其中：
- `src/agent/nodes/intake.py` 负责定义 intake 的最小 system prompt 与规则库装配方式
- `skills/energyplus_mcp/*.md` 是被 intake 引用的规则文档库，需整体遵守，不要只读其中一份

Step 1：读取案例文件
- 读 test_data/SmallOffice/smalloffice_17/testdata_prompt.json
- 读 Floor plans 数组里的每一张 {k}f_view.png（多模态）
- 读 JSON 中非空的 {South|North|East|West}_view.png（空串路径或文件不存在 = 该朝向无窗，不要伪造）
- 若 Floor plans 缺失但 Top view path of the building 非空，按 back-compat 视为各层共享平面

Step 2：先执行共享外包与立面有效性检查
- 每张层平面独立读出 W_f, D_f，验证全部相等（容差 ≤0.01 m）
- 若任意楼层外包不一致，视为退台 / 多外包案例（当前不支持）→ 直接停下并告诉用户
- 对每个立面，文件名朝向就是权威朝向；空串路径 / 缺文件 / 无蓝色窗矩形 = blank facade，不要伪造窗

Step 3：按规则库完成 intake
- 使用单一世界坐标系：原点 = 共享外包西南内角，x 向右，y 向上，楼层 z 由立面层高链累加
- 相信尺寸链数字，不要从像素反推长度
- corridor / stair / WC / lift / lobby / service room 需要显式识别，不能被吞成普通 office
- 所有 zone 必须逐个枚举，严禁 `Floor_N_*`、`for N in 2..5`、`typical floor` 一类模板压缩写法
- `zone_specs` / `surface_specs` / `fenestration_specs` 必须足够具体，使下游可机械恢复几何与拓扑关系
- `schedule_specs` 必须一次性写全，覆盖 thermostat / ideal_loads / people / lights 将引用的所有 schedule
- 所有跨字段引用名必须逐字一致；所有名字只能用 `[A-Za-z0-9_]`
- 不允许 TBD / 空串 / see above / etc. / 省略号等占位

Step 4：输出
返回**仅一个 JSON 对象**，符合 IntakeOutput schema：
- 11 个 top-level 字段：building, site_location, zone_specs, material_specs, schedule_specs, construction_specs, surface_specs, fenestration_specs, hvac_specs, people_specs, lights_specs
- building 用 BuildingSchema 嵌套（字段名 Title Case 带空格："Name", "North Axis", ...）
- site_location 用 SiteLocationSchema 嵌套（"Name", "Latitude", "Longitude", "Time Zone", "Elevation"）
- 9 个 *_specs 是自然语言段（snake_case lowercase 的 top-level key）

不要 markdown 代码块包裹，不要解释性 prose。

完成后先自检（B1 强化必查项）：
- 所有尺寸链是否闭合
- 所有楼层是否共享同一 W × D
- 所有 zone / schedule / construction 引用是否都有定义且逐字一致
- 所有窗是否只落在真实非空立面、真实 exterior wall 上
- **每个 facade 是否逐层独立读了 window chain**（不同楼层可以有不同窗数 / 不同分布 / 局部 blank）
- **每个窗是否写出了 absolute world z_min / z_max**（含 z_floor offset，不只是相对的 sill / head）
- **每个上下层 partition 错位处的 InterZone ceiling / floor 是否逐 piece 写出了 paired zone**（禁止 "split where needed" 这种软话）
- 所有 fenestration 名是否在 fenestration_specs 单独成行 + 列出 facade 平面 + 父墙 (Wall_1..Wall_4) + absolute z 范围

完成后用 Write 工具把这个 JSON 写到：
test_data/SmallOffice/smalloffice_17/output/intake_output.json
```

> **替换提示**：把每处 `smalloffice_17` 换成你的 case 名字。

### 4.3 Claude 会做的事

- `Read` testdata_prompt.json
- `Read` 多张图片（多模态）
- 内部完成几何理解 + spec 撰写
- `Write` 写入 `output/intake_output.json`

### 4.4 完工检查（在原会话或独立 Bash 跑）

```powershell
# Pydantic 验证 + 字段检查
python -c "
import sys, json
sys.path.insert(0, '.')
from src.agent._share import ensure_schema_initialized
ensure_schema_initialized()
from src.agent.state import IntakeOutput
data = json.loads(open('test_data/SmallOffice/smalloffice_17/output/intake_output.json', encoding='utf-8').read())
io = IntakeOutput.model_validate(data)
print('OK 11 fields')
print(' building.name =', io.building.name)
print(' site            =', io.site_location.name, '(', io.site_location.latitude, ',', io.site_location.longitude, ')')
print(' zone_specs len  =', len(io.zone_specs))
print(' schedule_specs len =', len(io.schedule_specs))
"
```

通过 = JSON 结构正确，可进 Step 5。Pydantic 报错 = 让 Claude 改 JSON 重存。

---

## 五、Step 5 · 自动跑下游（DeepSeek 驱动）

### 5.0 触发约定（2026-05-07 新增）

> Step 4 跑完 → 用户**不必手敲命令**。切回长期工作的 Claude Code 会话（不是 Step 4 临时会话），用自然语言触发即可。

**用户口令**（任一）：
- `跑下游 <case>`
- `Step 5 <case>`
- `跑 sm_17 下游` 之类

**助手收到口令必须依次**：

1. **先校验入参**：
   - `test_data/SmallOffice/<case>/output/intake_output.json` 存在
   - 跑 `python -c "..."` Pydantic L1 校验（[§4.4](#四4-完工检查在原会话或独立-bash-跑) 那段）
   - 不通过 = 报错，让用户回 Step 4
2. **echo 当前模型配置**（读 [src/configs/llm.yaml](../src/configs/llm.yaml) `default` section）：

   ```text
   下游模型配置（src/configs/llm.yaml default）：
     provider     = openai (DeepSeek 兼容)
     model_name   = deepseek-v4-pro
     base_url     = https://api.deepseek.com
     temperature  = 0.7
     max_tokens   = 64000
     thinking     = disabled  ← 见 §5.0.1
   ```

3. **询问 y/n** 确认：`以上配置开跑？(y/n)`
4. **y** → 后台启动 `python scripts/run_full_pipeline.py <case> --intake-from output/intake_output.json`，stdout tee 到 `<case>/output/pipeline_run.log`。完成后报告每节点耗时 + 产物 + L1/L2/L4 状态
5. **n** → 等用户改 [llm.yaml](../src/configs/llm.yaml) 后再触发

#### 5.0.1 为什么 thinking 默认关闭（2026-05-07 sm_16_newarch 首跑发现）

- DeepSeek v4-pro thinking 模式要求 multi-turn 时把上一轮 `reasoning_content` 回传 API；`langchain_openai` 标准 `ChatOpenAI` 不知道这个 DeepSeek 私有字段，第二轮 ReAct tool result 回灌时丢字段 → API 400：`The reasoning_content in the thinking mode must be passed back to the API.`
- 单 turn 文本（intake capability test 2026-05-06）不暴露此 bug；多轮 tool-calling（9 个 subagent ReAct）必踩
- 临时方案：[llm.yaml](../src/configs/llm.yaml) `default.extra_body.thinking.type=disabled`，关掉 thinking
- **能力影响**：v4-pro 关 thinking ≈ v4-flash 非 thinking；CRUD 类 subagent（zone/material/schedule/lights/people/hvac/construction/fenestration）能力够用（首跑 8 个全过），瓶颈在 surface 几何
- 何时升级：等 surface T-vertex bug（[plan.md B0'](plan.md)）修了仍翻车 → 上方案 A 自定义 `ChatOpenAI` 子类回传 `reasoning_content`

### 5.1 配置 API key（首次）

仓库根新建 `.env`：

```
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

参考 [.env.example](../.env.example)。Anthropic 字段留空（intake 已人工跑完不需要）。

### 5.2 跑全链路

> 推荐路径：用 [§5.0](#50-触发约定2026-05-07-新增) 对话触发，由助手代跑。下面命令是**助手内部执行**的等价形式 / 用户绕过助手手敲时的备份。

```powershell
python scripts/run_full_pipeline.py smalloffice_17 `
    --intake-from output/intake_output.json
```

脚本动作：
1. 读 testdata_prompt.json → user_input + image_paths
2. 读 `output/intake_output.json` → 装入 `AgentState.intake_output`
3. `build_graph()` 编译 14 节点全图
4. `intake_node` 检测到 `state.intake_output is not None` → **短路**（不调 Anthropic API），只 seed `config_state.building` / `config_state.site_location`
5. `phase 1` 并行：zone / material / schedule（DeepSeek 各跑 ReAct）
6. `cross_ref_foundations`（自动检 zone × material × schedule 命名一致性）
7. `construction → surface → fenestration` 串行
8. `phase 3` 并行：hvac / people / lights
9. `cross_ref_complete → validate`（auto_approval）
10. `simulate`：export YAML → 转 IDF → 跑 EnergyPlus

### 5.3 中途异常

| 现象 | 处理 |
|---|---|
| `RuntimeError: ... no api_key` | 检查 `.env` 的 `DEEPSEEK_API_KEY` 拼写 |
| `cross_ref_foundations` 报命名 drift | 回 Step 4，让 Opus 把 `intake_output.json` 的命名修齐重存 |
| 某 subagent 卡 ReAct 死循环 | DeepSeek 偶发；终止后从 checkpoint 恢复（thread_id = case 名）或加 `--no-resume` 重跑 |
| `validate` interrupt 被 `auto_approval` 拒（cross-ref 错误未清空） | 同样回 Step 4 修 IntakeOutput |
| `simulate` Fatal | 跳到 Step 6 看 `eplusout.err`，多半是 IDF 几何 bug，回 Step 4 修 surface_specs |

---

## 六、Step 6 · 验证（4 层）

### L1 — IntakeOutput schema

Step 4.4 的 Pydantic 校验。这一关在 Step 5 启动时已经强制（脚本 `_load_intake_from()` 内部调 `model_validate`），不通过根本进不来 Step 5。

### L2 — cross_ref 自动一致性

`cross_ref_foundations` + `cross_ref_complete` 两个节点会输出 `validation_errors`。`validate` 节点根据 errors 决定是否 interrupt；`auto_approval` 在 errors 非空时拒批，把 feedback 回喂 intake（在我们的半人工流里相当于停下来报错）。

执行后看终端 `[node=cross_ref_*]` 行；errors=[] = 通过。

### L3 — OpenStudio 三维视察（人工）

```powershell
# IDF 路径
$idf = "test_data/SmallOffice/smalloffice_17/output/smalloffice_17.idf"
# 用 OpenStudio / SketchUp 打开 $idf
```

人工核对：
- 每层 zone 轮廓与对应 `{k}f_view.png` 一致
- 各层外包围 `W × D` 完全相同（共享外包硬约束）
- 内墙两侧匹配，无悬空 surface
- 窗户贴在正确朝向的父墙上，sill / head Z 正确（`z_f = Σ_{k<f} h_k`）
- 楼板叠放正确（F2 不直接落地；中间层楼板/天花对应 Adiabatic）

### L4 — EnergyPlus 仿真完成

```powershell
$out = "test_data/SmallOffice/smalloffice_17/output"
Get-Content "$out/eplusout.end"           # 看 "EnergyPlus Completed Successfully" / "Fatal"
(Select-String 'Severe' "$out/eplusout.err").Count
```

---

## 七、Step 7 · 留痕到 `test_baseline/runs/`

> **2026-05-06 起** 实验日志归到 [../test_data/test_baseline/runs/](../test_data/test_baseline/runs/)（不再用 `AI_agent/experiments/`）。建模 baseline 的 5 字段格式见 [test_baseline/README.md §3](../test_data/test_baseline/README.md)。

跑完一轮想存档时：

```text
对（任一）Claude Code 会话说：记录这次跑 sm_17 e2e_v1
```

会按 [test_baseline/README.md §4.3](../test_data/test_baseline/README.md) 流程：
1. `Tool_scripts/baseline_record.py sm_17 e2e_v1` 建目录 + 解析 IDF counts
2. 用户粘 `/context` 输出到 `context.txt`（Token Total 唯一权威来源）
3. Claude 填 `meta.json` / `tokens.json` / `geometry.json` 的非用户字段
4. 用户 OpenStudio 验完填 `dimensions_check`

非 baseline 的 capability 类实验（如 "测试 DeepSeek 不同 reasoning_effort 档输出对比"）也放 runs/，但 dirname 用 `<YYYY-MM-DD>_capability_<topic>/` 区分（参考 [test_baseline/runs/2026-05-06_capability_deepseek_v4pro_intake/](../test_data/test_baseline/runs/2026-05-06_capability_deepseek_v4pro_intake/)）。

---

## 八、常见坑位清单

| 坑 | 表现 | 处理 |
|---|---|---|
| Step 4 Claude 输出带 markdown ```json 代码块 | Pydantic 报 JSON 解析错 | 重投 prompt 时强调"begin with `{` end with `}`，no fences" |
| Step 4 Claude 用了 `Floor_N_*` 模板 | cross_ref_foundations 检不出但 surface 节点会卡 | 重投 prompt 强调"all zone names must be enumerated"（已写在 Step 4.2） |
| Step 5 报 `'ModelPrivateAttr' object has no attribute 'Building'` | `IntakeOutput.model_validate()` 没先调 `ensure_schema_initialized()` | 脚本 `_load_intake_from()` 已内置调用；如果你写自己的脚本，别忘了 |
| `.env` 的 `DEEPSEEK_API_KEY` 没被 load_dotenv() 读到 | `create_llm()` 报 missing api_key | 确认 `.env` 在仓库根、不是子目录；启动 shell 后没改环境变量 |
| 共享外包不一致 | Step 4 Claude 在 §D3.1 不变量检查处停 | 返工对账各层尺寸链 |
| `TestName` 写错（沿袭 sm_0/5 的 bug） | 评测脚本按目录名对不上 | 命名与目录严格一致 |
| LLM 在几何阶段创建 schedule/lights/HVAC | 不再适用——新流程下 Step 5 自动跑 MEP 阶段，不存在"只几何不 MEP"的人工切分 | — |
| 内墙跨区构造不对称 | OpenStudio 显示悬空 surface / EP Severe: InterZone not matched | 现在由 `cross_ref_complete` + `simulate` 检；看 `eplusout.err` 报错后回 Step 4 改 surface_specs |
| Cross-floor split-pairing 写软（sm_18 真踩，2026-05-12） | `eplusout.err`: `RoofCeiling:Detailed="<F1_NW_CEILING_E>" references an outside boundary surface that cannot be found:<F2_N1_FLOOR_E>` → EP fatal | surface_specs 必须**逐 piece** 写出 paired zone（"Zone_F1_NW ceiling x 0.00 to 3.75 pairs with Zone_F2_N1 floor"），禁止 "split at combined breaks where needed" 这种软话。详见 [skills/energyplus_mcp/intake_output_contract.md "Cross-floor split-pairing"](../skills/energyplus_mcp/intake_output_contract.md) |
| Upper-floor window 没加 z_floor offset（sm_19 真踩，2026-05-12） | EP 跑通但 `eplusout.err` 多个 `Base surface does not surround subsurface (CHKSBS), Overlap Status=Partial-Overlap`；OpenStudio 看上层窗位置错（落到地面或墙体外） | fenestration_specs 必须写**absolute world z_min / z_max**（含 z_floor offset），sill/head 仅为辅助 scratch。`z_min = z_floor + sill_height`、`z_max = z_floor + sill_height + window_height`。详见 [skills/energyplus_mcp/intake_output_contract.md `fenestration_specs`](../skills/energyplus_mcp/intake_output_contract.md) + [zonetool_prompt.md "Window Vertex Synthesis Templates"](../skills/energyplus_mcp/zonetool_prompt.md) |
| 非深圳位置缺 EPW | `simulate` 节点报找不到 weather | 准备 `data/weather/<City>.epw`；脚本默认 `--epw data/weather/Shenzhen.epw` 可改 |
| `uv.lock` 解析报错 `duplicate key "xxhash"` | `uv run` 启动失败 | `Remove-Item uv.lock` 让 uv 重建（约 45s） |
| Step 5 中途崩溃想续跑 | LangGraph 用 `InMemorySaver`，进程退出即丢 checkpoint | 重新跑 Step 5 即可（intake 已落盘，不会重复扣 Opus 配额） |

---

## 九、与 Pivot 路线图的关系

新流程下，**Step 4 仍是 Opus 主战场**——多模态识图准确率优化都集中在这里。Step 5 是机械跑 DeepSeek，主要看下游 subagent 的 prompt + tool-calling 稳定性，不是识图能力。

后续目标（[plan.md B](plan.md)，2026-05-12 三阶段路线）：

- **阶段 1 — B1 旧 skill 能力迁移**（识图建模硬约束补强）：本节直接受益项。Step 4 的 prompt 模板 + intake 规则文档库（[skills/energyplus_mcp/*.md](../skills/energyplus_mcp/)）一起承载迁移成果
- **阶段 2 — B2 GT 数据集 / B3 IntakeOutput diff 评测脚本 / B4 Opus baseline + 校对方案 + token 协议**：直接对 Step 4 输出的 `intake_output.json` 做字段级 diff；用半人工流跑 4 个有 GT 的 case 给指标均值
- **阶段 3 — B5 非方形 / B6 全局坐标退台挑空 / B7 规范化绘图**：Step 4 的能力扩展，超出当前矩形 + 共享外包假设
- **远期 — B8 开源模型评测 / B9 LoRA SFT**：Step 4 换成 Qwen2.5-VL 等本地模型 → 对比 Opus baseline

Step 5 的下游链路一旦在 sm_16_newarch 跑通即视为稳定，不再频繁迭代——后续工作的反馈环都在 Step 4。下游 subagent prompt 的演进归协作者侧（[CLAUDE.md §2.2](CLAUDE.md)）。

---

## 十、与旧流程的对照

| 关注点 | 旧流程（2026-04-29）| 新流程（2026-05-06） |
|---|---|---|
| Opus 输入 | 图 + 设计意图 + 3 份 skill 文档 | 图 + 设计意图 + INTAKE_SYSTEM_PROMPT 摘要 |
| Opus 调 MCP 工具 | 是（create_zone × N、update_surface × N、…） | **否**（不调任何 MCP；只输出 JSON） |
| MCP server 启动 | 必需（`uv run main.py mcp-server`）| 不必（subagent 在 in-process 直接调 tool 函数） |
| Opus 输出物 | claude_ep.md + YAML + IDF + 标注图 | **`intake_output.json`** 一个 JSON 文件 |
| 下游 LLM | 没有"下游"概念（Opus 一手包） | **DeepSeek V4 pro × 9 个 subagent**（自动） |
| EP 仿真 | MEP 阶段独立做（拆分会话） | 同会话自动跑（`simulate` 节点） |
| 实验日志 | `AI_agent/experiments/<date>_<model>/` | `test_data/test_baseline/runs/<date>_<case>_<tag>/` |

---

_2026-05-12 — 对齐 plan.md B1 强化：§四.4.2 Step 4 prompt 自检 checklist 加 3 条新硬约束（per-floor window chain / absolute world z / cross-floor split-pairing）；§八常见坑加 sm_18 / sm_19 两类真踩 bug + 对应 skill 文档定位；§九 Pivot 路线图重写以匹配 plan.md 现行 B1-B9 编号（B1=旧 skill 迁移已完成，B2-B4=评测基线，B5-B7=能力升级，B8-B9=Pivot）。_

_2026-05-06 重写：固化半人工工作流（Claude Code intake + DeepSeek 下游）；删旧 §四挂 MCP 章节、改 §五成 run_full_pipeline.py 自动调用；§六验收改为 L1-L4 四层；§七留痕路径迁到 test_baseline/runs/；§八常见坑按新流程改写；§九/§十新增（Pivot 关系 + 新旧对照）。旧版备份在 [backup/new_case_guide.md.bak_2026-05-06](backup/new_case_guide.md.bak_2026-05-06)。_
