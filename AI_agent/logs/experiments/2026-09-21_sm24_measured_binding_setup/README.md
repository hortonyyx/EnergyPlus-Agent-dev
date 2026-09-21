# 量测候选直接进入开口声明

上一轮run07已收到正确扫描候选，却提交了重新估读的错误区间。本批保留同一局部任务、两原图、Sonnet medium和1200秒预算，新增候选引用方法，检验量测能否被正确采用。此前方向比较v2边界修正也首次随本批进入工作模型，因此不宣称严格单因素消融。

`run_observation.py`复制原平面/East图到独立run，只加入原有通用问题及“已量测坐标用候选引用”的程序性要求。不给旧候选、旧模型、旧答案、正确开口数量/坐标/方向或GT。工作模型自己选裁图、颜色、阈值、候选和分组；数字槽仍支持明确的视觉估计，不能因此把未引用值计为已绑定量测。

```bash
python AI_agent/logs/experiments/2026-09-21_sm24_measured_binding_setup/run_observation.py --out AI_agent/logs/experiments/2026-09-21_sm24_measured_binding_run08 --timeout 1200
```

run目录拒绝覆盖；已有结果优先检查，不重复调用模型。现有Claude订阅、只读MCP、无API回退/DeepSeek，不做源BIM生成。主模型与CLI辅助模型的用量按回执分别记录。局部题目由开发选择，不计整楼自主任务组织。

`verify_observation.py --run RUN`在模型完成后核输入/实现、原图返回逐像素重放、每次扫描的候选和数值重放、比较请求/绑定/存盘/返回一致。量测记录保留原字节散列，候选重放除变化的剩余时间外需一致。比较仍只提供数值证据，不自动接受方向或改变BIM。

开发先做了[真实旧扫描的引用重放](../2026-09-21_sm24_measured_binding_replay/README.md)，它使用开发选定候选，仅作确定性接口验证，不进入run08工作模型。

本批已完成：run08在421.26秒实际引用17个量测值，标定及三处水平对应改善，但墙窗/门高仍错。随后按最大残差自动选择范围，Haiku/run09在360.17秒复查后仍错误，未回灌或改BIM。两run机制/图像/离线页面均通过，语义均未通过。见[完整节点交接](../../worklog/2026-09-21_reconstruction_measured_binding.md)。

```bash
python AI_agent/logs/experiments/2026-09-21_sm24_measured_binding_setup/review_largest_residual.py --parent AI_agent/logs/experiments/2026-09-21_sm24_measured_binding_run08 --out AI_agent/logs/experiments/2026-09-21_sm24_residual_review_run09 --timeout 600
```

上条命令只说明实际运行方式，已有目录拒绝覆盖，不再调用。review输入含未验证旧声明，不是原图冷启动；用`verify_observation.py --run RUN --review-only`核机制，独立原图语义结论另存。下一项优先复用[完整同色连通范围](component_method_note.md)，并保留旧工具独立输入pilot，按产物选择路线。
