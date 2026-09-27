# 房间功能类型表

09-27 用户要求优先复用 EnergyPlus 生态既有类型表，工作模型从表中选，BIM HTML 按类型固定配色。

EnergyPlus `Space.Space Type` **没有预定义枚举**，默认空值归 General；[官方 I/O Reference](https://bigladdersoftware.com/epx/docs/25-2/input-output-reference/group-thermal-zone-description-geometry.html#field-space-type)明确允许任意字符串。这里采用 OpenStudio(R) 标准库的一级空间功能表，完整保留 **61 个上游类别**，另有项目的 `unknown`（不属于上游）。不把它称为 EnergyPlus 内置表。

上游固定到提交 `83b1e64c6f130f02b48c8b3ad4eeb3eb4da41663`：[原始表](https://github.com/NatLabRockies/openstudio-standards/blob/83b1e64c6f130f02b48c8b3ad4eeb3eb4da41663/lib/openstudio-standards/space_type/data/level_1_space_types.json)。上游 JSON 和许可证一起保存在 `src/agent/data/openstudio/`；唯一运行时表为 [room_types.json](../../src/agent/data/room_types.json)，其中同时保存原名、上游 ID/注释、中文显示名、命名 token、固定颜色及已知旧别名。中文、颜色和别名是项目定义，不冒称上游规范。新版本需显式更新，运行不联网拉表。

生成规则：

- `get_bim_reference('room_types')` 返回该表；生成指引要求选表，导出校验拒绝表外功能。已知 `meeting`、`wc`、`stair` 等旧写法映射到标准项；原始 proposal 保留，源 BIM 写标准代码。
- 缺少功能、证据不足或确实没有匹配类别时选 `unknown`，原图文字和推断写 `source_refs` / `assumptions`；禁止 `office_inferred` 等自行扩词。不另造 mixed 类，不因混合用途把实际开敞房间拆开。
- 源 BIM 记录表版本、SHA256 与来源；HTML 内嵌同表，色块和图例从这张表读取。未知灰色；无角色数据的历史纯几何查看保留原白色行为。
- 本表只用于功能分类、命名和显示，不自动套用负荷、时刻表、材料或 HVAC；原始上游文件中的参数引用仅用于溯源，未导入任何物性。
- 注意上游限定：`multifamily` 指多户住宅**公共区域**，不是住户套内；`living quarters` 示例为消防站集体起居，`sleeping quarters` 为宿舍寝区。部分上游行带 `to be revised`，原注释保留。

09-27 实跑后补充：仅列出功能表并不能保证工作模型会实际使用；sm24/run59仍全部unknown，未读表或逐房记录功能判断。新指引要求物理空间完成后回查功能，家具可支持明确标注的推断，证据不足仍保留unknown。功能推断不授权拆分实际开敞空间。

已有候选可通过 `revise_bim` 的 `set_space_role` 局部修改功能。输入为 `space_id`、表内 `role`、`basis`（observed/inferred/unknown）、`source_refs`、`assumptions` 和 `reason`。unknown与unknown依据成对，推断须写明假设；操作只替换当前功能与 `role_evidence`，原几何、房间ID、门窗和连接保持。旧功能依据留在修订记录，几何来源／假设不被功能说明覆盖。直接源导出也校验已提供的 `role_evidence` 与功能相符。历史或初次草稿可没有该可选记录，不能据此补造证据。

源房间现在同时保留草稿已有的 `source_refs` / `assumptions`，追加内部追溯指针，不再只留下correction路径。房间功能依据单独保存，不能传播为每面墙的图证。HTML点房间显示功能判定、依据及假设，并合并展示房间／围护已有说明；固定色表不变。这是文字依据的可查看增量，不是此前待讨论的全构件置信度视图。重导出旧稿会增加元数据并改变源hash，原归档不改写。

| 标准代码（role） | 中文显示 | 固定颜色 | 上游 ID |
|---|---|---|---|
| `atrium` | 中庭 | `#afbddf` | 1 |
| `attic` | 阁楼 | `#cbdfaf` | 2 |
| `audience seating` | 观众席 | `#dfafd9` | 3 |
| `banking` | 银行营业区 | `#afdfd7` | 4 |
| `classroom/lecture/training` | 教室／讲堂／培训 | `#dfc9af` | 5 |
| `computer room` | 计算机房 | `#bbafdf` | 6 |
| `conference/meeting/multipurpose` | 会议／多功能 | `#d7ecd2` | 7 |
| `confinement cells` | 拘留室 | `#dfafbf` | 8 |
| `copy/print` | 复印／打印 | `#afcddf` | 9 |
| `corridor` | 走廊 | `#fdf0c8` | 10 |
| `courtroom` | 法庭 | `#d5afdf` | 11 |
| `datacenter/high ite` | 高设备负载数据中心 | `#afdfc7` | 12 |
| `datacenter/low ite` | 低设备负载数据中心 | `#dfb9af` | 13 |
| `dining` | 用餐区 | `#afb3df` | 14 |
| `dressing room` | 化妆／换装室 | `#c1dfaf` | 15 |
| `electrical/mechanical` | 电气／机械设备 | `#cfe0db` | 16 |
| `emergency room` | 急诊室 | `#afdddf` | 17 |
| `emergency vehicle garage` | 应急车辆车库 | `#dfd3af` | 18 |
| `exam/treatment` | 检查／治疗 | `#c5afdf` | 19 |
| `exercise area` | 健身区 | `#afdfb7` | 20 |
| `exhibit` | 展览区 | `#dfafb5` | 21 |
| `guest room` | 客房 | `#afc3df` | 22 |
| `imaging` | 医学影像 | `#d1dfaf` | 23 |
| `interior parking` | 室内停车 | `#dfafdf` | 24 |
| `judges chambers` | 法官办公室 | `#afdfd1` | 25 |
| `food preparation` | 食品制备 | `#fde0e0` | 26 |
| `laboratory` | 实验室 | `#b5afdf` | 27 |
| `laundry/washing` | 洗衣 | `#b7dfaf` | 28 |
| `library` | 图书馆 | `#dfafc5` | 29 |
| `living quarters` | 集体起居区 | `#afd3df` | 30 |
| `loading dock` | 装卸区 | `#dfddaf` | 31 |
| `lobby` | 门厅 | `#f6d6c2` | 32 |
| `locker room` | 更衣室 | `#afdfc1` | 33 |
| `lounge/breakroom` | 休息室／茶歇 | `#dfb3af` | 34 |
| `manufacturing` | 生产制造 | `#afb9df` | 35 |
| `medical supply` | 医疗物资 | `#c7dfaf` | 36 |
| `multifamily` | 多户住宅公共区 | `#dfafd5` | 37 |
| `nursery` | 育婴室 | `#afdfdb` | 38 |
| `nurses station` | 护士站 | `#dfcdaf` | 39 |
| `office` | 办公 | `#cfe3f2` | 40 |
| `office/enclosed` | 独立办公室 | `#b9d4eb` | 41 |
| `operating room` | 手术室 | `#dfafbb` | 42 |
| `patient room` | 病房 | `#afc9df` | 43 |
| `pharmacy` | 药房 | `#d7dfaf` | 44 |
| `physical therapy` | 物理治疗 | `#d9afdf` | 45 |
| `playing area` | 运动场地 | `#afdfcb` | 46 |
| `plenum` | 吊顶／架空夹层 | `#dfbdaf` | 47 |
| `post office` | 邮局 | `#afafdf` | 48 |
| `recovery` | 康复区 | `#bddfaf` | 49 |
| `recreation/common living` | 休闲／公共起居 | `#dfafcb` | 50 |
| `restroom` | 卫生间 | `#e6d5f0` | 51 |
| `retail` | 零售 | `#f0e4b0` | 52 |
| `shaft` | 竖井 | `#d0d0d0` | 53 |
| `sleeping quarters` | 集体寝室 | `#afdfbb` | 54 |
| `sports arena` | 体育场馆 | `#dfafb1` | 55 |
| `stairwell` | 楼梯间 | `#dcdcdc` | 56 |
| `storage` | 储藏 | `#e6e3d2` | 57 |
| `transportation` | 交通客运 | `#dfafdb` | 58 |
| `vehicular maintenance` | 车辆维修 | `#afdfd5` | 59 |
| `workshop` | 车间 | `#dfc7af` | 60 |
| `worship` | 宗教礼拜 | `#b8afdf` | 61 |
| `unknown` | 未知／待判定 | `#c9ced4` | 项目占位 |
