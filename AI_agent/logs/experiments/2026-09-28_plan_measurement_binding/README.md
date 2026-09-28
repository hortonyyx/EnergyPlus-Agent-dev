# 已选像素量测直接进入平面声明

本包只修复“选定量测后仍须手抄坐标”的接口缺口。真实失败轨迹已有正确墙线量测却仍使用错误墙坐标，并通过缩窗消除宿主错误；它没有证明缺少引用接口就是退步原因。对象识别、代表面选择、漏墙及窗型对应仍由工作模型解决。

## 实现及边界

复用`profile_observation_binding.py`既有候选读取/原图/轴/散列校验；增加`resolve_plan_pixels`，接入`build_plan_bim`及其局部修订路径。像素槽支持`{"profile":"profile_001","candidate":"C02","at":"peak"}`及两个候选的`midpoint`，不增加任意表达式、自动识别或吸附。标定的米值和z不解析引用，已有数字声明完全保留。

存在引用时保存`submitted_plan.json`、供旧消费者读取的数字`plan.json`、`measurement_bindings.json`及其散列；含两个端点候选和解析值的快照可追溯。错误引用保留提交稿，明确`measurement_binding`错误阶段，不产出候选。不强制每次量测或每个点都引用，不以引用存在判定图纸保真。按需`plan_partition`参考补充用法，全局任务和角色不变。

## 实际验证

- `python -m pytest -n 0 tests/test_plan_measurement_binding.py tests/test_profile_observation_binding.py tests/test_bim_agent_plan_partition.py tests/test_plan_revision.py -q`：39 passed，38.28秒，无provider调用。
- 真实MCP合成原图：两条线→取中点→墙与门→局部修订保留其他窗→两个楼层装配，源空间/门连接和保存声明均核对。
- [实际入口预检](runtime_preflight.json)：只用sm21原图准备到模型启动边界并阻断调用，40个生产文件快照包含解析器，真实MCP返回新版`plan_partition`全文及中点语法；0模型调用。脚本[runtime_preflight.py](runtime_preflight.py)复用旧批次的输入参数，不执行/覆盖旧批次，也不是新增回归批准。
- [开发辅助重放](report.json)：run83/draft_003原样先报W_S1；开发者根据原图选择x=768/779两条细墙线，把P_O12两端x绑定为中点773.5。再次编译报W_S3，W_S1冲突消失；全部窗、其余墙及声明保持，0新候选/模型调用/GT输入。原图和旧稿散列未变。完整产物在[developer_replay](developer_replay/)，脚本为[replay.py](replay.py)。
- [纠正后的数字兼容对照](numeric_compatibility.json)：run57/58/83的8份数字草稿，解析前后声明完全相同，6份编译成功、2份原有错误；成功proposal和标定元数据、错误文本均一致，历史原件散列未变。脚本为[numeric_compatibility.py](numeric_compatibility.py)。

复查纠正：首次`replay.py`的数字兼容分支把manifest的list直接传给要求tuple的`image_size`，所以[原报告](report.json)中8个`compiled=false`只到参数校验，不能作为几何兼容证据。原报告保留；仅这一字段由`numeric_compatibility.json`替代。脚本已修正tuple转换。实际Toolkit修墙链使用PIL的tuple，从开始即有效，声明相等检查也不受影响。两脚本均拒绝覆盖本次输出；复做请换新目录。

## 未证明的事

开发者选择了物理墙及候选，这不是Sonnet独立采用。W_S3、北侧漏墙/错并和窗型高度仍未修复，也没有整层BIM。09-21立面引用实测已经表明选错物理对象时，正确绑定坐标仍会得到错误结果。不能以39项接口检查或本次重放宣布质量恢复；后续行为回归须分别核正确选取、实际采用、保存结果和旧能力保持。
