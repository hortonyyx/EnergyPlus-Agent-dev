# 建筑声明接入与还原试验编排

本程实现显式`--building-input`。5.6 Sol/high负责输入helper、CLI与三个定向测试，主助手负责接口复核、观察试验、真实运输/整案、后验检查与文档集成。Claude产品调用经已有订阅，未使用DeepSeek、付费API回退或EP；部分推理本轮未施工。

## 已有验证

- `tests/test_bim_agent_inputs.py`与`tests/test_bim_agent_tools.py`共24 passed。子代理误沿用了项目默认`-n auto --dist load`，记录实际命令`pytest -q tests/test_bim_agent_inputs.py tests/test_bim_agent_tools.py -q`，不冒充显式少worker；结果有效，不为修正命令记录再跑相同范围。后续测试按约定用`python -m pytest -n 2`。
- [真实声明运输](input_transport/verification.json)：通过真实只读stdio取得sm24原始JSON/五张PNG清单，原始字节、散列、原样字段与五图关联均一致。没有模型调用/候选生成，不计入产品成功次数。
- [原平面轮廓观察](../2026-09-14_sm24_partition_contours_probe/README.md)：Haiku在135秒查看13个实际区域轮廓后仍严重错读，不采用，不返回run16。详细边界和docstring并发变化保留在该运行记录。
- [run16](../2026-09-14_bim_agent_sm24_run16/README.md)到时保存失败候选。结束后修复显式door错放windows却被静默生成为窗的问题；新校验原案重放见[type_conflict_replay](type_conflict_replay/verification.json)。`python -m pytest -n 2 tests/test_source_proposal.py tests/test_bim_agent_tools.py tests/test_bim_agent_inputs.py -q`为30 passed，21.52秒，与先前24项重叠、不加总。

## 本程脚本

- `observe_partitions.py --out 新目录`：只给原平面，开发指定轮廓与完整分隔观察法，Haiku/240秒上限。可选Sonnet仅供明确的新实验，不自动重试或升级。
- `verify_observation.py 运行目录`：复用已有图像运输核验，检查真实原图/区域图和只读输入隔离，不判空间语义。
- `verify_building_input.py`：对实际sm24声明运行离线stdio检查，输出目录须不存在。
- `run_declared.py`：sm24/run16，原五图＋原始`testdata_prompt.json`、Sonnet medium/600秒。保持run15相同的通用目标，不携带前述Haiku观察、seed、旧生成物、正确坐标或GT；声明原本包含`thermal_zones:8`并保留其后端含义，不能称完全无数量先验。
- `verify_declared_run.py 运行目录`：在完成后检查真实模型收到的声明/图片清单与源候选的输入出处。

run16的结果和质量判断在其独立README及本程工作记录维护，不以离线接口通过代替整案保真。各实验的原流保留；源码快照供后验复现，不供运行模型读取。
