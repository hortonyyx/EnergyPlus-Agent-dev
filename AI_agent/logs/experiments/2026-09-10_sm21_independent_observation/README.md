# sm21：先看原图、不看旧候选的局部观察

本轮只推进还原建模。开发助手选择“南立面下层开口”作为有界问题，用现有只读MCP工具让Haiku独立观察，再把**未改写的回答**交给Sonnet恢复已有BIM。该方法在本实验中由开发助手安排，不是总Agent已能自主选择这套分工，也不构成整案冷启动。

## 第一步实际结果

[观察原文](observe01/observation.json) · [输入快照](observe01/inputs.json) · [请求](observe01/observer_request.json) · [回执](observe01/observer_receipt.json) · [独立事后核对](observe01/assessment.json)

Haiku在166.68秒内正常完成；实际模型 `claude-haiku-4-5-20251001`，一次Claude订阅调用，CLI估算 $0.1499565，非账单。执行22次图像查看、3次像素投影、1次像素坐标换算、1次尺寸链累计。累计工具得到15米，期望总长单位正确、闭合差为0。

它正确区分下层一门三窗，并将小横开口判断为高窗台、不落地的窗。这比旧候选自查继续坚持“两门”的结果更有用，但不能只因身份数对就宣布读图可靠：

- 包围框大多直接复用了裁切区域，并非开口轮廓；最右框没有包住实际最右窗。
- 小窗估成约2400×1100毫米，图上明确是1200×600毫米；门宽估成约2000毫米，也明显过大。
- 大窗高度和开口对应段亦有误。正确计算没有自动变成正确的对象量测。

这些事后核对仅由开发助手看原图作出，没有作为修正答案传入下一步。下一步仍须检验主模型能否采用正确身份线索、拒绝错误量测。

## 输入隔离与范围

观察目录只含一张原字节南立面，清单没有seed、房间、旧开口列表、平面、GT或历史观察。观察进程的工具仅有输入查看、图像/局部裁切和像素/尺寸计算；没有shell、仓库读写、候选检查/构建、独立评价或嵌套模型工具。9项实际核验通过，包括原图/实施哈希、所有工具调用只读且只看指定图、没有seed或候选产物。

该限制来自现有 `run_bim_agent.py --readonly` 与独立run目录；不依赖一句“请忽略旧答案”。这也不保证模型观察正确。开发助手选择已知问题所在的局部属于明确的辅助条件，不能算无干预发现问题或未知样本泛化。

第二步记录见 [sm21 run10](../2026-09-10_bim_agent_sm21_run10/README.md)。Sonnet仍可看六张原图与run08的保存方案，观察作为不确定假设原样传入scope；不传本页事后评价，不供给GT或开发正确坐标。

## 复现

使用新输出目录，脚本不会覆盖已有run。先观察，确认请求实际完成，再选择是否恢复；观察失败不会自动重试或换模型。

```bash
python AI_agent/logs/experiments/2026-09-10_sm21_independent_observation/run_probe.py observe \
  --images AI_agent/logs/experiments/2026-09-10_bim_agent_sm21_run08/images \
  --out AI_agent/logs/experiments/2026-09-10_sm21_independent_observation/observe_replay --timeout 180

python AI_agent/logs/experiments/2026-09-10_sm21_independent_observation/run_probe.py recover \
  --images AI_agent/logs/experiments/2026-09-10_bim_agent_sm21_run08/images \
  --observation AI_agent/logs/experiments/2026-09-10_sm21_independent_observation/observe_replay \
  --seed AI_agent/logs/experiments/2026-09-10_bim_agent_sm21_run08/candidate_01 \
  --out /tmp/sm21-local-recovery --timeout 420
```

观察与恢复用量分别保留，总耗时/费用在本轮工作记录汇总。没有改生产运行器或源几何内核，没有DeepSeek、付费API或EP调用，没有推进部分推理建模。
