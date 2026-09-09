# EP 分叉的最小物性输入契约

本文说明共同源 BIM 到 EnergyPlus 分叉之间，几何团队与物性协作者目前需要交换的最小内容。范围只覆盖当前一房一热区、外窗、显式关闭门和理想负荷系统，不把后续物性治理或通用 HVAC 设计提前塞进本轮。

## 权威对象与绑定方向

源 BIM 是空间、物理边界和开口的唯一几何权威。物性输入引用源对象 ID，但不提供坐标、不新建或拆并空间，也不改变源开口状态。

| 对象 | 权威内容 | 物性侧最小输入 | EP 后端职责 |
|---|---|---|---|
| 源空间 | `spaces[].id`、形状、楼层、高度、用途 | 每个源空间 ID 对应一个唯一 EP 热区名 | 一房一热区，派生 Zone 和完整表面切片，并保存源空间到热区映射 |
| 源边界 | `boundaries[].id`、所属空间、两侧关系、完整面 | 当前不要求逐边界配置 | 根据表面类型选择固定构造名；每个派生面必须回指唯一源边界，并核对完整覆盖和配对关系 |
| 外窗 | `openings[].id`、宿主边界和顶点 | 当前不要求逐窗配置 | 保留源顶点，派生 EP 窗并记录源开口 ID；使用 `Default_Window` |
| 门 | `openings[].id`、两侧宿主、几何、源 `connectivity` | 仅在明确按关闭门模拟时，按源开口 ID 给关闭策略和门构造 | 在两侧墙上生成互相配对的 Door 子面，记录一对多派生映射，不回写源状态 |
| 空通道 | `kind=open` 且按源契约必为 `connectivity=open` | 本轮没有可接受的“关闭”配置 | 明确阻断；不得改造成门或实体墙 |

这一区分很关键：边界相邻表示两个空间共享物理隔断，开口连接表示隔断上存在门洞或空通道。热区名和物性不能反过来改变这两种源关系。

## 当前已实现的输入面

截至 `818df391` 的基线，`src/agent/execution/ep_branch.py` 已接收以下三项输入：

1. `source_bim_v2` 源文件。摘要、单位、Z 轴、几何验证、未建项和不支持项均需通过；后端运行前后核对源文件字节不变。
2. 无几何的 `physics.idf`。它可包含版本、运行控制、地点、作息、材料、构造、人员、灯光、电器负荷、恒温器、每区理想负荷系统和有限输出对象；不得包含 Zone、BuildingSurface、FenestrationSurface 或其他未列入白名单的对象。
3. `zone_bindings.json`。当前格式是一个无包裹的 JSON 对象，键集合必须与全部源空间 ID 精确相等，值是非空、大小写不重复且不含 IDF 分隔字符的 EP 热区名。

基线已经做到：源空间/边界/外窗 ID 追溯、一房一热区、派生表面覆盖核对、相邻表面配对核对、源北向覆盖模板北向、未知北向采用模板值并写入假设、Relative 坐标和全零热区变换、最低源楼层接地、每个热区恰有一个理想负荷系统、所有负荷对象只能引用绑定后的热区，以及所需构造存在。

基线尚未做到：门或空通道的 EP 表达、逐源边界或逐窗构造覆盖、非正交空间、热区合并、一般 HVAC、物性 JSON 到 IDF 的通用生成，以及完整的作息和对象引用预检。作息名、恒温器引用等错误目前可能要到 EnergyPlus 实跑才暴露。本轮已在该基线上接入第四项 `opening_policy.json` 和关闭门适配器；空通道仍明确阻断。

构造名仍是后端固定词汇，不是逐对象绑定：

```text
Default_Ext_Wall
Default_Int_Wall
Default_GroundWall
Default_GroundFloor
Default_ExtFloor
Default_Roof
Cons_InterFloor
Default_Window
```

模板只需覆盖实际派生几何用到的名称；若希望同一模板跨多层和悬挑案例复用，则应提供完整词汇。门构造名不固定，由每个门的策略显式给出，但必须在模板中唯一存在、属于普通不透明 `Construction`，不能复用玻璃窗构造。

## 本轮已实现的最小门接口

本轮已在 CLI 增加独立 `--opening-policy` JSON，并接通关闭门的派生、IDF 写入和审计。最小文件按源开口 ID 直接映射，不加入空间名、边界 ID 或坐标：

```json
{
  "corridor_north_mouth": {
    "state": "closed",
    "construction": "Diagnostic_Door",
    "reason": "为本次传热验证明确假设该未知状态双扇门全年关闭"
  }
}
```

最小判定规则如下：

- 不存在全局“所有门默认关闭”。每个被接纳的门都必须按源开口 ID 明确配置。
- 源 `connectivity=closed` 可按关闭门导出；源 `connectivity=unknown` 只有在策略为 `closed` 且 `reason` 非空时才可导出。该理由进入运行证据，源 BIM 仍保持 `unknown`。
- 源 `connectivity=open` 或 `kind=open` 继续阻断，即使策略文件声称 `closed` 也不能覆盖源事实。空通道不能用门构造填上。
- 策略中的 ID 必须存在且属于门；缺项、额外 ID、空构造名、模板中缺少对应构造都失败。
- 内部门在两个宿主墙面各派生一片或多片 Door（跨后端切配墙面时拆片），两侧逐片设置互相配对的外边界对象；全部派生片使用同一构造并共同回指一个源开口 ID。源边界仍是完整物理墙，门作为子面表达，不应从源边界关系中删除门洞面积。

本轮实验使用 `Diagnostic_Door`：单层无质量材料，热阻 `0.25 m2·K/W`。这是为了跑通闭门传热路径的明确诊断假设，并非可信门体或协作者交付物性。更合理的门层组应由物性协作者提供。无论材料层怎样选，“closed”只表示存在关闭门扇并计算其传热；它不自动代表气密，也不模拟门缝渗透、开门时段或跨区空气交换。当前白名单也没有相应气流网络对象。

## 最小物性模板约束

本轮 sm24 验证建议从已保存的 sm21 无几何模板取材料、作息和单个对象样板，然后针对 sm24 的八个源空间重新克隆对象。不能复制 sm21 的 14 区对象集合，也不能从旧 sm24 IDF 剥离得不彻底。

建议的实验假设是：

- 八个空间各一个 People，采用 `People/Area = 0.1 person/m2`，不要沿用 sm21 按旧房间面积写死的人员数。
- 八个空间各一个 Lights，采用 `Watts/Area = 10 W/m2`。
- ElectricEquipment 可省略；若加入，也需明确密度和作息，不能从旧区名暗带数值。
- 八个空间各一个恒温器和一个 `HVACTemplate:Zone:IdealLoadsAirSystem`。当前装配器硬性要求每个绑定热区恰有一个理想负荷系统。
- 材料、墙/楼板/屋面/窗构造和作息可沿用 sm21 实验模板，但要注明它们是复用假设，尚非协作者已交付或校准的 sm24 物性。
- 模板 Building 的北向只在源北向未知时作为后端假设。sm24 当前 `north_axis=null`，因此运行报告必须留下实际采用值和来源，不能把模板的 `0` 当作图纸已知朝向。

sm24 的八空间绑定可采用下列最小文件；名称只是 EP 标识，不承载新的空间划分：

```json
{
  "cell_conference_left_bottom": "Z01_Conference_Left_Bottom",
  "cell_corridor": "Z02_Corridor",
  "cell_north_reception": "Z03_North_Reception",
  "cell_office_left_middle": "Z04_Office_Left_Middle",
  "cell_office_left_upper": "Z05_Office_Left_Upper",
  "cell_office_right_bottom": "Z06_Office_Right_Bottom",
  "cell_office_right_middle": "Z07_Office_Right_Middle",
  "cell_office_right_small": "Z08_Office_Right_Small"
}
```

## sm24 真实含门验证

当前 assisted 源文件是 `AI_agent/logs/experiments/2026-09-09_source_bim_run04/sm24_assisted/source_model.json`：8 空间、52 个完整边界、11 窗和 1 门，无未建开口。门 `corridor_north_mouth` 连接 `cell_corridor` 与 `cell_north_reception`，宽 1.8 m、高 2.1 m；高度和关闭状态均非实测，源状态为 `unknown`。`opening_hosts` 已给出两侧源边界 ID，后端应据此核对实际派生宿主。

这份源文件的局部几何/关系验证是 `pass`，但独立分区评价仍是 `severe`，报告也明确只有这一处门、其他已在历史 reading 中提到的门仍未建。它可用于验证含门适配器不会改写空间和源状态，不能作为 sm24 源模型整体正确或开口完整的验收件。

旧的 `2026-06-24` sm24 成功 IDF 含 11 个 Zone、76 个 BuildingSurface、11 个 People 和 11 个 Lights，其负荷与 HVAC 均引用旧 11 区名。直接把它当物性输入会把错误分区偷偷带回后端。真实验证应只用上述 8 项绑定、独立无几何模板和单门策略，检查：

1. 输出恰有 8 个 Zone，所有 People、Lights、恒温器和理想负荷系统只引用这 8 个名字；模型中不存在旧 `Z09` 至 `Z11` 等历史区对象。
2. 52 个源边界都至少由一个派生面覆盖且无重叠遗漏；11 个源窗完整映射；一个源门得到两片互配 Door，映射仍只指向 `corridor_north_mouth`。
3. 输出 IDF 的两片门使用策略指定的 `Diagnostic_Door`，模板确实定义该不透明构造；门宿主分别属于走廊与北侧接待空间，外边界对象互指。
4. `source_model.json` 输入副本与原文件哈希一致，原文件字节不变；运行证据同时保存 `zone_bindings.json`、`opening_policy.json`、`physics.idf` 及三者哈希。
5. 先通过导出、内表面配对和源映射检查，再用真实 EPW 运行 EnergyPlus；以完成、0 severe 和完整警告为后端贯通依据。能耗数值不作校准结论，EP 成功也不降低 sm24 的源分区 severe 状态。

本轮实际 run02 已得到 8 热区、58 个基础表面、11 窗、1 个源门和 2 个互配门面，全年 EnergyPlus 完成且 0 severe、5 warnings；115 项相关测试通过。四条警告沿用 sm21 模板已知项，另一条是未使用构造。完整命令、产物、警告和验证范围见后续工作记录 [含门 EP 分叉](../logs/worklog/2026-09-09_ep_doors.md)。

## 当前风险

- 物性模板仍是 IDF 文本，能通过白名单但包含不合理数值或错误作息；本轮只能靠明确实验假设、对象引用检查和真实 EP 运行降低风险。
- 构造按表面类型统一选择，协作者目前不能按源边界或源窗 ID 给差异化构造。需要这种能力时应另增显式覆盖表，不能把差异藏在热区名里。
- 最低楼层一律接地是后端派生假设。架空层、地下室或局部悬挑会需要源侧场地接触证据或单独边界策略；当前 sm24 单层实验会把全部底板视为接地。
- 未知朝向采用模板北向只适合贯通，不适合朝向敏感结果解释。
- 关闭门模型不包含渗透和跨区空气流动。已知开启门和空通道尚无物理等价的本轮实现，保持阻断比静默封墙更可信。
