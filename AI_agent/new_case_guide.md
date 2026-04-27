# 新建测试样例操作指南

> 面向 [../test_data/SmallOffice/](../test_data/SmallOffice/) 目录下新增一个 SmallOffice 测试案例的标准流程。
> 当前基于 **Claude Opus 人工流水线**；未来脚本化评测参见本文第四节。
>
> **2026-04-25 更新**：流水线已拆分为两阶段。本指南面向**几何阶段**（产物：YAML + IDF + claude_ep.md + 标注图，IDF 用 OpenStudio 3D 视图验证几何）。Materials / Schedule / People / Lights / HVAC 由独立的 **MEP 阶段**处理，本指南中所有相关步骤已移除或标注为"MEP 阶段"。EnergyPlus 仿真验收（§6.2 ④⑤）属于 MEP 阶段，几何阶段不做仿真。

---

## 零、流水线总览

```
Step 1 准备素材 → Step 2 建目录 → Step 3 写 JSON →
Step 4 挂 MCP → Step 5 LLM 执行 → Step 6 验证归档 → Step 7 留痕
```

---

## 一、Step 1 · 准备视觉素材

立面图**按朝向命名**,每个文件代表其所**面朝**的立面(不是"从哪边看过去")。1–4 张立面图均可,未提供的朝向 skill 会自动按无窗处理。

| 文件名（强约定） | 必需 | 内容 | 规格建议 |
|---|---|---|---|
| `top_view.png` | **必需** | 俯视平面图，含尺寸标注（开间/进深/墙位） | ≥ 1024 px 宽；黑线墙 + 白色房间；走廊留白 |
| `South_view.png` | 可选 | 南立面图（y=0 立面） | 能看清层高、窗位、窗高 |
| `North_view.png` | 可选 | 北立面图（y=y_max 立面） | 同上 |
| `East_view.png` | 可选 | 东立面图（x=x_max 立面） | 同上 |
| `West_view.png` | 可选 | 西立面图（x=0 立面） | 同上 |
| `<supp_plan>.png` | 可选 | 补充平面图 / 剖面 / 轴测 | 复杂造型时提供 |

**朝向命名不可替换**：skill [§D5](../skills/energyplus_mcp/energyplus_mcp_prompt.md) 规定文件名即权威的 facade 对应关系,不存在 `front_view` / `side_view` 的同义词。文件缺省 = 该立面无窗 = **零个 `create_fenestration_surface` 调用**。

**关键约束**：
- 俯视图 **必须有尺寸链**（见 §1.1），否则 LLM 无法精确还原房间边界。
- 走廊画成 **宽白带**（宽度 ≥ 房间 1/3），不是细线墙 —— LLM 依靠「宽白带 vs 细黑线」区分走廊和墙（[energyplus_mcp_prompt.md](../skills/energyplus_mcp/energyplus_mcp_prompt.md) 第 3 条）。
- 楼梯 / 卫生间 / 电梯画出标准符号（楼梯：平行斜线+箭头；WC 标志；电梯框）。

### 1.1 尺寸标注规范（sm_13 起强制）

> **背景**：sm_0 ~ sm_12 全部是**无尺寸的纯几何线框**，坐标完全靠 LLM 从 `Floor area` 反推猜测（见 [smalloffice_0/claude_ep.md:14-29](../test_data/SmallOffice/smalloffice_0/claude_ep.md) 的 `0m/5m/10m/15m` 全是 Claude 自编）。这导致「房间尺寸中位误差」永远无 ground truth 可比。**sm_13 起必须带尺寸标注**，以支撑 [pivot_criteria.md §1.1](pivot_criteria.md) 的房间尺寸误差阈值可测。

**俯视图（`top_view.png`）**：
- **两级尺寸链**
  - 一级（外部）：总开间 / 总进深，画在图外侧上方 + 左侧，单根带箭头
  - 二级（外部）：分段开间 / 分段进深，画在一级之外一层，每段独立数字
- **字体 & 线型**：
  - 数字用**黑色等宽字体**（Consolas / 等线），字号占图面高度 1.5%~2.5%
  - 引出线用 0.5 pt 细黑线，**不与墙线重合颜色**
  - 尺寸线与墙体保持 ≥ 字号 × 2 的留白，避免 OCR 粘连
- **单位**：
  - 全图**只用一种单位**（`mm` 推荐，与下游 `*_mm` 字段对齐）
  - 数字裸写数值（如 `3600`），单位只在图例角落注明一次
- **坐标原点**：左下角 = (0, 0)，x 向右、y 向上（CCW），与 `zonetool_prompt.md` 约定一致。

**立面图（`{South|North|East|West}_view.png`，各文件独立）**：
- 文件名即朝向,见 [skill §D5](../skills/energyplus_mcp/energyplus_mcp_prompt.md)。缺省的文件 = 该立面无窗。
- 层高尺寸链画在**左侧**外部，逐层标注 `floor_height_mm`,各立面的左链必须一致。
- 右侧标 per-floor 三段子链(top_gap | window_height | sill_height),符合 skill §D4。
- 底部标窗水平位置链:南/北立面求和 = 俯视图总开间 W,东/西立面求和 = 俯视图总进深 D。
- 窗台高 `window_sill_mm` 与窗顶高 `window_head_mm` 用细引线标注。
- 室外地坪标高（Z=0）明确标出。

**禁忌**（会让 PaddleOCR 误读）：
- ❌ 尺寸数字压在墙线上
- ❌ 多单位混用（`3600mm` 和 `3.6m` 并存）
- ❌ 分数 / 带小数点不足 2 位（`3.6` vs `3.60` 不一致）
- ❌ 红色 / 蓝色标注（走廊白带区分依赖单色通道）

### 1.2 `testdata_prompt.json` 字段约定（sm_13 版本）

现阶段仅关心 IDF 建模正确性(含开窗),**暂不写 Ground Truth 字段**。评测方案搭好后再单独拆一个 `gt.json` 持有 GT(见 [plan.md P0](plan.md)),不与 prompt.json 混在一起。

当前保留的字段如下:

| 字段 | 说明 |
|---|---|
| `TestName` | 与目录名严格一致（如 `SmallOffice_13`） |
| `Building location` | 气象数据文件名映射（目前仅有 Shenzhen.epw） |
| `Floor area` | 总建筑面积字符串（如 `"192m²"`,可空） |
| `Building type` | 建筑类型（`Office` 等） |
| `Top view path of the building` | **必填**,俯视图相对路径 |
| `South view path of the building` | 可空。空字符串 → 南立面无窗 |
| `North view path of the building` | 可空。空字符串 → 北立面无窗 |
| `East view path of the building` | 可空。空字符串 → 东立面无窗 |
| `West view path of the building` | 可空。空字符串 → 西立面无窗 |
| `Path of the supplementary plan example drawing for the building` | 可空 |
| `Number of thermal zones per floor of the building` | 每层 zone 数（串) |
| `Number of total thermal zones in the building` | 总 zone 数（串) |
| `Number of floors` | 层数（串) |

模板参见项目根目录的 [../testdata_prompt.json](../testdata_prompt.json),新建案例时复制到对应目录并按图纸改写。

---

## 二、Step 2 · 建案例目录

在 [../test_data/SmallOffice/](../test_data/SmallOffice/) 下**编号递增**建目录（当前末位 `smalloffice_12`，新案例用 `smalloffice_13`）：

```bash
mkdir -p test_data/SmallOffice/smalloffice_13/output
cp /path/to/top_view.png    test_data/SmallOffice/smalloffice_13/top_view.png

# 以下立面图按实际有窗情况挑选拷贝,未提供 = 无窗
cp /path/to/South_view.png  test_data/SmallOffice/smalloffice_13/South_view.png
# cp /path/to/North_view.png  test_data/SmallOffice/smalloffice_13/North_view.png
# cp /path/to/East_view.png   test_data/SmallOffice/smalloffice_13/East_view.png
# cp /path/to/West_view.png   test_data/SmallOffice/smalloffice_13/West_view.png
```

---

## 三、Step 3 · 写 `testdata_prompt.json`（Format A 入口）

模板(基于根目录 [../testdata_prompt.json](../testdata_prompt.json),**不要改 key**):

```json
{
    "TestName": "SmallOffice_13",
    "Building location": "Shenzhen",
    "Floor area": "192m²",
    "Building type": "Office",
    "Top view path of the building": "test_data/SmallOffice/smalloffice_13/top_view.png",
    "South view path of the building": "test_data/SmallOffice/smalloffice_13/South_view.png",
    "North view path of the building": "",
    "East view path of the building": "",
    "West view path of the building": "",
    "Path of the supplementary plan example drawing for the building": "",
    "Number of thermal zones per floor of the building": "5",
    "Number of total thermal zones in the building": "10",
    "Number of floors": "2"
}
```

**字段说明**：
- `TestName` → 必须与目录名严格一致（现有 sm_0 / sm_5 的 TestName 都错写成 `"SmallOffice_0"`，**不要沿袭**，新案例务必正确填 `SmallOffice_13`）。
- `Building location` → 当前仅有 [../data/weather/Shenzhen.epw](../data/weather/Shenzhen.epw)，**首选深圳**；其他城市需自备 EPW 放到 [../data/weather/](../data/weather/)。
- `Floor area` → 可空字符串，LLM 会从俯视图尺寸链自算。
- 图像路径 → 相对项目根的 `test_data/...` 路径(历史版本的 `test/test_data/...` 前缀是 bug,**不要沿袭**)。4 条立面路径空串 = 该朝向无窗。
- 末 3 个整数字段（`Number of thermal zones per floor / total / Number of floors`）→ 这是 **Ground Truth**，评测脚本要拿它比对 LLM 产出，**务必数准**。

---

## 四、Step 4 · 挂载 MCP 服务器

项目 MCP 工具**不是内建的**，必须先启 MCP 服务。二选一：

```bash
# 方式 A：stdio（配合 Claude Desktop / Claude Code 直接挂）
uv run main.py mcp-server

# 方式 B：HTTP（给其他 MCP 客户端用）
uv run main.py mcp-server --transport http --host 127.0.0.1 --port 8000
```

**Claude Desktop** 配置参考（[../README.md](../README.md)）：

```json
{
  "mcpServers": {
    "EnergyPlus-Agent": {
      "command": "uv",
      "args": ["--directory",
               "c:/Users/Horton/Desktop/科研2/EnergyPlus-Agent-dev",
               "run", "main.py", "mcp-server"]
    }
  }
}
```

> server key 用 `EnergyPlus-Agent`(与仓库根 [../.mcp.json](../.mcp.json) 保持一致),这样 Claude 端看到的工具名前缀就是 `mcp__EnergyPlus-Agent__*`,与 skill 文档里 `mcp__EnergyPlus-Agent__create_zone` 一类引用对齐。如果 key 换成别的(如 `energyplus-agent`),工具前缀会跟着变,skill 里的示例就对不上。

**Claude Code** 用户：仓库根已提供 [../.mcp.json](../.mcp.json)（2026-04-21 补建，此前 sm_13 首轮因无此文件退化到手写 `build_yaml.py`，见 [sm_13 run_log §4](../test_data/SmallOffice/smalloffice_13/output/run_log.md)）。只要在仓库根启动 Claude Code，会话一开始就会提示挂载该 server；接受后工具列表出现 `mcp__EnergyPlus-Agent__create_zone / create_surface / create_fenestration_surface / export_yaml / validate_config / ...`。若会话已开未挂，可用 `/mcp` 重挂，或退出后在仓库根重进。

---

## 五、Step 5 · 触发 LLM 执行

打开 Claude（模型 = **Opus**），投递 3 份 skill 文档 + 案例路径：

````text
请按以下 skill 文档完成 EnergyPlus 几何阶段 IDF 构建：

@skills/energyplus_mcp/energyplus_mcp_prompt.md
@skills/energyplus_mcp/zonetool_prompt.md
@skills/energyplus_mcp/export_idf.md

测试案例目录：
test_data/SmallOffice/smalloffice_13/

严格按 skill 文档执行：
1. 识别 Format A → 读 testdata_prompt.json
2. 读 top_view.png 与 JSON 中非空的 {South|North|East|West}_view.png
   (空串路径或文件不存在的立面 = 该朝向所有楼层无窗,直接跳过,不得伪造)
3. **不裁剪原图**(要保留外围尺寸链便于人工校验),至多 2× NEAREST 放大,
   画标注后保存到 output/top_view_annotated.png
4. 写 output/claude_ep.md(Dimension Extraction 四个立面 sub-heading 都要出现;
   邻接矩阵 + 坐标表 + ASCII 平面图 + Fenestration Table)
5. 按 list_locations / list_buildings → create_location / create_building 顺序
   建场地与建筑;然后逐 zone 调 create_zone(参数见 zonetool_prompt.md)。
6. **执行 skill §IDF Tool Usage Workflow 第 3 步 Surface boundary-condition
   touch-up**:对每个 zone 自动生成的 6 个 surface,按表格设置 boundary
   condition 与占位 construction 名(外墙 Outdoors+Default_Ext_Wall;
   内墙/楼板/F1 顶 Adiabatic+Default_Int_Wall;F1 地面 Ground;顶层屋面
   Outdoors+Default_Ext_Wall)。**内墙两侧必须对称用 Default_Int_Wall**,
   否则 InterZone Fatal。
7. **执行 skill §IDF Tool Usage Workflow 第 4 步独立的 Fenestration 子步**,
   每行 Fenestration Table 对应一次 `create_fenestration_surface` 调用,
   construction_name = "Default_Window"(占位),父墙按 zonetool_prompt.md
   §M7 Wall-index 映射(Wall_1=南/Wall_2=东/Wall_3=北/Wall_4=西)。
8. validate_config + export_yaml(output/smalloffice_13.yaml)
9. 单行 Bash 跑外部脚本转 IDF：`python Tool_scripts/export_idf.py test_data/SmallOffice/smalloffice_13`
   → output/smalloffice_13.idf。脚本内置 5 条幂等补丁(占位 Construction 预注入 +
   原 4 条);**不要 inline 复制脚本内容**。

**几何阶段到此结束**。MEP 阶段(Materials / Schedule / People / Lights /
HVAC)与 EnergyPlus 仿真在独立会话进行,不在本轮验收范围。
````

**LLM 过程中会**：
- `Read` PNG（多模态）
- `Bash` 执行 PIL 标注脚本
- `Write` 生成 `claude_ep.md`
- 调 `mcp__EnergyPlus-Agent__create_zone / update_surface / create_fenestration_surface / …` 累积 `ConfigState`
- 调 `mcp__EnergyPlus-Agent__export_yaml` 导出 YAML
- `Bash` 单行调 [../Tool_scripts/export_idf.py](../Tool_scripts/export_idf.py) → IDF（几何阶段不跑 EP）

**人工兜底**（仅几何阶段相关）：
- 「请核对内墙构造是否两侧对称（都用 `Default_Int_Wall` + `Adiabatic`），避免后续 MEP 阶段或 OpenStudio 报 InterZone 不匹配」
- 「请确认 Fenestration Table 的所有行都已转化为 `create_fenestration_surface` 调用，window 数量与表格行数一致」
- 「请确认 F1 地板是 `Ground`、F2 地板/F1 天花是 `Adiabatic`、屋顶是 `Outdoors`」

> Schedule / Lights / HVAC 在几何阶段**不应出现**。若 LLM 主动调用了相关 `create_*` 工具，应阻止并指出这是 MEP 阶段任务。

---

## 六、Step 6 · 验证与归档

### 6.1 目录最终形态

```
test_data/SmallOffice/smalloffice_13/
├── testdata_prompt.json          ← 手写(输入)
├── top_view.png                  ← 必需(输入)
├── South_view.png                ← 按朝向选配,不存在即无窗(输入)
├── North_view.png                ← (输入,可缺)
├── East_view.png                 ← (输入,可缺)
├── West_view.png                 ← (输入,可缺)
└── output/                       ← 所有 LLM / 工具产出都写进这里,不再散落到案例根
    ├── top_view_annotated.png    ← LLM 生成(§三 Step 3;整图 ≤2× 放大,保留外围尺寸链)
    ├── claude_ep.md              ← LLM 生成(Dimension Extraction / 邻接 / 坐标 / Fenestration)
    ├── smalloffice_13.yaml       ← MCP export_yaml 产物
    ├── smalloffice_13.idf        ← ConverterManager 产物
    ├── run_log.md                ← 本轮执行记录(偏离说明、验证清单、仿真日志索引)
    ├── *.py                      ← 偏离 MCP 时的临时脚本(annotate / build_yaml / export_idf)
    └── eplusout.*                ← EP 仿真产物(.end / .err / .eso …; 当前阶段可缺)
```

> **2026-04-21 变更**:将 `top_view_annotated.png` / `claude_ep.md` / YAML 从案例根迁到 `output/`,配合 sm_13 run_log 结论——这些都属于"每轮可被覆盖的衍生品",与输入素材(PNG/JSON)要分层管理。历史案例(sm_0..sm_12)可暂不迁移,但新案例强制执行。

> **当前阶段关注点**:IDF 中几何 + 开窗是否正确。Schedule / Lights / HVAC 由 MEP 阶段处理,几何阶段产物里这些字段必为空(占位符 construction 名)。

### 6.2 验证清单（几何阶段）

```bash
# ① claude_ep.md 存在且非空
test -s test_data/SmallOffice/smalloffice_13/output/claude_ep.md && echo "[1] OK"

# ② YAML zones 数量 vs testdata_prompt.json 的声明
python -c "
import yaml, json
p='test_data/SmallOffice/smalloffice_13/'
with open(p+'output/smalloffice_13.yaml') as f: d=yaml.safe_load(f)
with open(p+'testdata_prompt.json') as f: j=json.load(f)
actual=len(d.get('Zone',[]))
expected=int(j['Number of total thermal zones in the building'])
print(f'[2] zones actual={actual} expected={expected} match={actual==expected}')
"

# ③ IDF 存在
test -f test_data/SmallOffice/smalloffice_13/output/smalloffice_13.idf && echo "[3] OK"

# ④ OpenStudio 几何视觉验证(人工)
#    打开 IDF → SketchUp/OpenStudio 3D 视图 → 检查:
#    - Zone 轮廓与俯视图一致
#    - 内墙两侧匹配,无悬空 surface
#    - 窗户贴在正确朝向的父墙上,sill/head Z 正确
#    - F1/F2 楼板叠放正确(F2 不直接落地)

# ⑤ (MEP 阶段才做) EP 仿真状态 + Severe 数 — 几何阶段跳过
#    cat test_data/SmallOffice/smalloffice_13/output/eplusout.end
#    grep -c "Severe" test_data/SmallOffice/smalloffice_13/output/eplusout.err
```

### 6.3 子系统覆盖度自检（几何阶段：仅核对几何对象数）

```bash
python -c "
import yaml
p='test_data/SmallOffice/smalloffice_13/output/smalloffice_13.yaml'
with open(p) as f: d=yaml.safe_load(f)
def n(k): return len(d.get(k,[])) if isinstance(d.get(k),list) else (1 if d.get(k) else 0)
print(f'zones={n(\"Zone\")}                                  ← 须 > 0,与 JSON 声明一致')
print(f'surfaces={n(\"BuildingSurface:Detailed\")}            ← 须 = zones × 6')
print(f'fenestration={n(\"FenestrationSurface:Detailed\")}    ← 须 = Fenestration Table 行数')
print(f'-- 以下字段几何阶段必为 0(MEP 阶段填充) --')
print(f'materials={n(\"Material\")} (期望 0)')
print(f'constructions={n(\"Construction\")} (期望 0)')
print(f'schedules={n(\"Schedule:Compact\")} (期望 0)')
print(f'people={n(\"People\")} (期望 0)')
print(f'lights={n(\"Lights\")} (期望 0)')
print(f'hvac_ideal={n(\"HVACTemplate:Zone:IdealLoadsAirSystem\")} (期望 0)')
"
```

### 6.4 窗户专项自检(sm_13 起必做)

历史 7 个到 IDF 的案例有 5 个 0 窗。sm_13 起 skill 已把 Fenestration 拆成 IDF Workflow 独立第 5 步,验证时必须跑下面的比对:

```bash
python -c "
import yaml, json, re
p='test_data/SmallOffice/smalloffice_13/'
with open(p+'testdata_prompt.json') as f: j=json.load(f)

# 1. 期望窗数:从 JSON 中四个 facade 路径 + claude_ep.md 的 Fenestration Table 推算
provided = [k for k in ('South','North','East','West')
            if j.get(f'{k} view path of the building','').strip()]
print(f'[win] provided facades = {provided}')
md = open(p+'output/claude_ep.md',encoding='utf-8').read()
expected_win = len(re.findall(r'^\| W_F\d+', md, re.M))
print(f'[win] expected windows (Fenestration Table rows) = {expected_win}')

# 2. 实际窗数:YAML
with open(p+'output/smalloffice_13.yaml') as f: d=yaml.safe_load(f)
actual_win = len(d.get('FenestrationSurface:Detailed',[]))
print(f'[win] actual windows in YAML = {actual_win}')
print(f'[win] match = {expected_win == actual_win}')

# 3. 父墙映射检查:每个窗的 building_surface_name 应该匹配 _Wall_1..4
# 且 Wall_1=南/_Wall_2=东/_Wall_3=北/_Wall_4=西
"
```

若 `actual_win < expected_win` → LLM 跳过了 Fenestration Step,需要复投 prompt 并明确"所有 Fenestration Table 行必须调用 `create_fenestration_surface`"。

---

## 七、Step 7 · 留痕（用于开源模型迁移对照）

- 用 Claude Opus 跑完的**对话记录**存成：
  ```
  AI_agent/experiments/<YYYY-MM-DD>_opus_sm13/transcript.md
  ```
- 走 LangGraph Agent 路径时用 [../scripts/export_trace.py](../scripts/export_trace.py) 导出 tool-call trace 作为微调数据。
- 把 §6 产出的 5 档指标 + 子系统覆盖度写进 `AI_agent/experiments/<date>_<model>/result.json`，供后续跨模型比对。

---

## 八、常见坑位清单

| 坑 | 表现 | 处理 |
|---|---|---|
| `TestName` 写错（沿袭 sm_0/5 的 bug） | 评测脚本按目录名对不上 | 命名与目录严格一致 |
| 俯视图缺尺寸链 | LLM 瞎猜房间宽度 → zone 数量错 | 返工加标注；或 JSON 里补 `Floor area` 兜底 |
| 走廊画成细线 | LLM 把走廊识别为墙 → 少一个 zone | 画成宽白带（≥ 房间 1/3 宽） |
| 挂 MCP 失败 / 工具不可见 | 会话里没有 `mcp__EnergyPlus-Agent__*` | 确认**仓库根**有 [../.mcp.json](../.mcp.json)(2026-04-21 已补建);Claude Code 启动时必须在仓库根目录进入;会话内用 `/mcp` 复查状态 |
| LLM 在几何阶段创建 schedule/lights/HVAC | YAML 含本应为空的字段 | 阻止并指出这是 MEP 阶段任务；如已发生，删除对应对象后重新 export_yaml |
| 内墙跨区构造不对称 | OpenStudio 显示悬空 surface / EP Severe: InterZone not matched | 几何阶段 skill §IDF Workflow 第 3 步表格强制内墙两侧用 `Adiabatic + Default_Int_Wall`；export_idf.md 第 3 条补丁仍保留作为兜底 |
| 非深圳位置缺 EPW (仅 MEP 阶段) | `energyplus` 启动即报找不到 weather | MEP 阶段需要；几何阶段不跑仿真。先放好 [../data/weather/](../data/weather/)`<City>.epw` |
| `uv.lock` 解析报错 `duplicate key "xxhash"` | `uv run` 无法启动环境 | `Remove-Item uv.lock` 让 uv 重建(约 45s,176 包) |
| typer/click 签名冲突(0.24 + 8.3) | `uv run main.py mcp-server` 报 `AttributeError: 'list' object has no attribute 'isidentifier'`,所有子命令注册都挂 | [../main.py](../main.py) `run_agent` 里 `Annotated[X, Option(default, ...)]` 这种把默认值塞进 `Option()` 的写法在新版已非法,默认值必须放函数签名等号右侧。2026-04-21 已修 |
| 标注图裁剪丢尺寸链 | `top_view_annotated.png` 只显示建筑主体,外围 `3.00 \| 2.00 \| 3.00` 类尺寸链被 crop 掉 | **不裁剪**,整图至多 2× NEAREST 放大(skill §2b 2026-04-21 已改)。若 LLM 仍沿袭 6× crop 旧模板需当面纠偏 |
| 过程产物散落案例根 | `claude_ep.md / yaml / annotated.png / 脚本` 与输入 PNG 混在一起 | 强制全部写 `<case_dir>/output/`(skill §Step 3 + guide §6.1 2026-04-21 已改)。输入 PNG / JSON 保留在案例根 |

---

## 九、自动化脚本蓝图（未来工作）

当前 Step 5 仍是**人工对话驱动**。目标是把整条流水线脚本化，复用 [../src/agent/](../src/agent/) 的 LangGraph：

```python
# AI_agent/eval/run_case.py （草图）
def run_case(case_dir: Path, llm_config: LLMConfig) -> CaseResult:
    prompt_json = case_dir / "testdata_prompt.json"
    images = [case_dir / n for n in ("top_view.png",
                                     "South_view.png",
                                     "North_view.png",
                                     "East_view.png",
                                     "West_view.png")]

    graph = build_graph()
    initial = AgentState(
        user_input = prompt_json.read_text(encoding="utf-8"),
        image_paths = [str(p) for p in images if p.exists()],
    )
    context = SimContext(
        epw_path  = Path("data/weather/Shenzhen.epw"),
        output_dir = case_dir / "output",
    )
    state = run_session(graph, initial, context,
                        {"configurable": {"thread_id": case_dir.name}},
                        on_interrupt=auto_approval)

    return CaseResult(
        # 几何阶段指标
        has_claude_ep   = (case_dir/"output"/"claude_ep.md").exists(),
        has_yaml        = bool(list((case_dir/"output").glob("*.yaml"))),
        has_idf         = (case_dir/"output"/f"{case_dir.name}.idf").exists(),
        zone_match      = count_zones() == expected_total_zones(),
        window_match    = count_windows() == expected_window_rows(),
        # MEP 阶段指标(几何阶段不跑 EP,这两项留给 MEP 阶段评测)
        # ep_started    = (case_dir/"output"/"eplusout.end").exists(),
        # ep_completed  = "Successfully" in (case_dir/"output"/"eplusout.end").read_text(),
    )
```

脚本到位后，新建案例只做 Step 1–3，然后：

```bash
python AI_agent/eval/run_case.py test_data/SmallOffice/smalloffice_13
```

即可自动跑完 Step 4–6 并产出指标。这是 [claude.md §4.3](claude.md) 的 **M2 里程碑**。

---

_最后更新：2026-04-25（流水线拆分为几何阶段 + MEP 阶段；本指南面向几何阶段；移除 schedule_compact_guide.md 引用；Step 5 投递 prompt 重写：增 Surface boundary touch-up 第 6 步、Fenestration 改为 IDF Workflow 第 4 步、删除仿真步骤；§6.2 ④⑤ 仿真验证标注为 MEP 阶段；§6.3 子系统期望值翻转为"几何阶段必为 0"；§8 常见坑更新；§9 蓝图删除 ep_started/ep_completed 指标）_

_2026-04-21（立面图改按朝向命名 `{South|North|East|West}_view.png`；GT 字段暂从 JSON 移除；补 §6.4 窗户专项自检;skill 内 IDF Workflow 拆出独立 Fenestration 步 + §M7 Wall-index 映射;sm_13 首轮后:所有 LLM 产物迁入 `output/`、标注图不再裁剪、仓库根补 `.mcp.json`）_
