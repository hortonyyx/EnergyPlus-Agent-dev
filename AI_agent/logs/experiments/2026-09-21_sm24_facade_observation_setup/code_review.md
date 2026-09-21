# 立面区间对照接入只读审查

审查范围为 `src/agent/geometry/facade_span_comparison.py`、
`scripts/tool_scripts/run_bim_agent.py` 中的新工具接线、操作参考及两份相关测试。
未修改生产文件，未读取 GT，未调用模型/API。

## 发现

### 1. 中：数量不等时 `unpaired_*` 会把错误的对象标成未配对

`compare_direction` 先取两份中心排序列表的相同长度前缀逐项配对，再把较长列表的尾部写成
`unpaired_*`（算法第 79–97 行）。如果额外开口在开头或中间，真正额外项会被错误配入，最后一个正常项反而被标成未配对。

例如平面为 `p1=[2,3]、p2=[7,8]m`，立面为
`extra-left=[0.1,0.5]、e1=[2,3]、e2=[7,8]m`，当前输出配成
`p1↔extra-left、p2↔e1`，并把 `e2` 列为 `unpaired_elevation`。
工具已拒绝在数量不等时给方向，参考也说部分配对不能识别漏项，因此不会直接选错方向；但逐对残差和
`unpaired_*` 的对象级标签仍可能误导后续核图去查错位置。

最小处理可在数量不等时不给对象级 `unpaired` 归因：保留两份完整排序列表及数量差，明确所有配对均为
`rank_pairing_only`；或者将字段改名为 `unpaired_rank_tail`。现有测试只覆盖额外项恰在尾部，没有覆盖开头/中间额外项。

### 2. 中：`direction_distinguishable=true` 只表示相对误差有差距，也会对两个都很差的方向成立

第 117–138 行仅用两个方向的**平均绝对残差之差**是否大于 0.05m 设置
`direction_distinguishable`。控制例中正向平均残差 4m、反向 5m，仍返回
`lower_residual_direction=forward`、`direction_distinguishable=true`。操作参考文字已要求同时检查绝对残差，
但机器字段名称容易被总 Agent 当作方向已可靠区分。

建议保持两方向数值不变，把该布尔量改成更准确的 `relative_error_separated`，或另加明确的
`absolute_fit_not_evaluated`，避免把“相对更小”表达成“可定向”。不宜在没有产品容差依据时硬加绝对通过阈值。
现有测试只检查零误差真反向和对称情况，没有锁住“两边都很差”的语义。

### 3. 低：未校验要原样保存的扩展证据是否为有限、标准 JSON

算法只验证 anchors 和 pixels。工具把原始 `observations` 连同 `kind/evidence` 等扩展字段原样写入报告，
且 `json.loads/json.dump` 使用 Python 默认的 `NaN/Infinity` 宽松行为（工具第 696、718–723 行）。因此
`{"confidence": NaN}` 会被接受并持久化为含裸 `NaN` 的文件，严格 JSON 读取器会拒绝，破坏后续证据交换。

最小处理是在解析后递归拒绝所有非有限浮点，或保存时使用 `allow_nan=False` 并将错误返回调用者。
当前测试只覆盖 `pixels` 中的 NaN，没有覆盖保留证据字段中的 NaN。

## 未发现的问题与限制

- 工具绑定了输入清单中的精确原图名、散列、尺寸和轴，散列变化会拒绝；成功记录使用独占文件名，不覆盖旧证据。
- 算法不改候选或源 BIM，正反方向、绝对残差、数量差和对称歧义均保留；输入像素区间与 anchors 的有限性、范围、零长度和重复 ID 已检查。
- 本次是静态审查和三个最小控制输入复现，没有评价 run07 的原图观察是否完整或正确，也没有复跑主助手已通过的 32 项检查。

## 建议修订范围（run07 结束后应用）

已准备 `/tmp/facade_hardening.patch`，范围仅为上述三点及其定向测试：

1. 数量不等时两方向均不生成中心序号配对和残差；把两份完整列表全部保留为尚未对应，避免错误指认漏项。
2. schema 升为 `facade_span_direction_probe_v2`，将容易过度解读的
   `direction_distinguishable` 改为 `relative_error_separated`，并固定返回
   `absolute_fit_status: not_evaluated`；不引入未经产品确认的绝对误差阈值。
3. 递归拒绝 observations 中任意层级的非有限数；解析时拒绝裸
   `NaN/Infinity/-Infinity`，保存时使用严格 JSON。测试同时覆盖 `1e999` 溢出为无穷的情况。
4. 更新通用参考，明确数量不等不配对、相对区分不等于绝对吻合；测试覆盖开头/中间额外项、两方向都存在米级大残差和扩展证据中的非有限数。

补丁未应用到生产树。`git apply --check /tmp/facade_hardening.patch`通过；补丁后的临时副本均可编译，三类算法控制输入通过。未在临时副本上运行项目 pytest，应用后应运行补丁包含的两份定向测试。
# 主助手集成结果

run07已正常结束，v1输入/实现/图像/比较精确核验通过后才应用本报告建议的补丁。最终两份定向测试39项通过（31.09秒）；真实5对4观察用v2离线重放，全部原观察保留、两方向均零配对/无配对残差。v2未另做模型实测，未改写run07旧结果。本轮另发现已返回的正确像素候选未被模型采用，后续量测记录绑定单独设计，不混入本修订。
