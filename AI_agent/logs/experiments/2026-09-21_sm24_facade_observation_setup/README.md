# 原图局部开口观察方法迁移

用户澄清历史复现和开发示范迁移两条路线按测试综合取舍，当前不切换主线。历史审计独立并行，见[报告](../2026-09-21_reading_reproduction_audit/historical_success.md)。本批验证前一程方向探针的工作模型可执行性。

## 输入与调用

`run_observation.py` 新建独立 run，复制 sm24 的原平面与 East PNG，只加入局部观察目标、通用工具和参考。不给历史reading、旧BIM、开发探针坐标、正确数量/方向/类型/高度或GT，不读建筑声明；选择东侧题目本身是开发限定范围。

Sonnet、medium、1200秒、现有Claude订阅、readonly MCP；不调用Haiku读图子任务、DeepSeek或付费API，没有回退。CLI自身辅助模型用量以回执为准。模型自己选裁图、量测参数、轴端点及开口列表，再调用双方向计算；最终回答独立核验。结果只计局部原图观察，不是整楼冷启动或源修订成绩。

```bash
python AI_agent/logs/experiments/2026-09-21_sm24_facade_observation_setup/run_observation.py --out AI_agent/logs/experiments/2026-09-21_sm24_facade_observation_run07 --timeout 1200
```

该命令已执行，既有目录拒绝覆盖；不要为检查产物重复模型调用。首轮实测生产实现为 `d34ec189`，inputs.json 另存六份相关实现的字节散列。后续审查修订若发生在本轮之后，不补记为模型已使用。

## 验证

生成结束后 `verify_observation.py --run RUN` 检查输入来源、实现散列、每个普通原图查看的逐像素重放、已保存量测图的实际返回、比较请求/存盘/返回/重算一致、实际模型回执和无BIM写入。核验脚本不加载GT；不得把机制通过当语义正确。

`write_report.py --run RUN` 生成可查看的原图及观察列表页。核验/网页输出拒绝覆盖；精确重算需要使用 inputs.json 对应实现版本，不能让后续新版schema静默替代旧记录。

独立代码复核见[code_review.md](code_review.md)；本批运行期间保持实现不变。运行结束并完成旧版精确核验后，生产schema升至v2，收紧数量不等/绝对误差未知/非有限数边界。最终39项离线检查通过，见[测试记录](offline_checks.json)；本次5对4输入的[新版离线重放](hardened_replay.json)保留全部未对应项，不再输出误导性排序配对。v2没有另跑模型；完整结果见[run07 README](../2026-09-21_sm24_facade_observation_run07/README.md)。
