# sm24 五图＋声明质量实验：正常结束，还原失败

**不采用，保留sm24/run12与sm21/run22。** Sonnet medium在1800秒上限内用937.07秒正常结束，保存并选定 **7空间/42源边界/9窗/8门/8连接**。源几何自洽通过，但独立分区为severe；原图也支持真实漏墙、错误拆并和走廊截断，不是仅尺寸微差。

[可查看候选与事后结论](index.html) · [实际源文件](candidate_01/source_model.json) · [独立评价](evaluation/index.html) · [原图复核](post_run_review.md)。候选仅保留为失败证据，不替代当前采用模型。

## 输入与运行范围

五张原始PNG、完整原始建筑声明JSON；无seed、旧观察、正确源房间数/坐标或GT。原声明`thermal_zones:8`确实提供，保留后端含义。开发侧选定质量实验及可选像素墙网能力，生成中没有追加具体错处提示或手填几何。

运行使用Claude现有订阅、Sonnet medium，实际`claude-sonnet-5`。一次主调用，没有局部Haiku读图委派；CLI自身记录的少量Haiku辅助用量不计为产品读图分工。CLI估算 **$2.513121**，不是订阅账单；输出65650 token、缓存创建163543、缓存读取1820160等完整原始统计保留在[回执](agent_receipt.json)。没有DeepSeek、付费API回退或EP调用。

实现以功能提交`89d1fd2c`冻结。运行过程中[所有冻结源码相同](frozen_code_verification.json)，实际快照保存在`implementation/`。运行结束后`07723b1c`收窄内部编译故障捕获；不把本实验改称在后补修复上重跑。

## 实际过程与失败

模型实际取得声明和五图，成功38次原图查看（39次尝试）、1次编号区域总览、1次参数参考。首次建模在首个工具后885.67秒；只有1份像素墙网，首编译成功。随后取得源平面/原图回叠、显式再看源平面、取开口清单并`finish_bim`，**没有修订，没有提交开口观察marks**。[完整时序](execution_summary.json)。

当前候选省略东北内部隔墙、截断走廊并省略南端折角，模型把这些解释成可简化/可合并内容；开口也有丢失、合并或错误归属。模型自述叠图匹配不采作保真结论。具体图证、开口清单与允许的尺寸容差由[事后复核](post_run_review.md)说明。独立窗比较器当前不支持此v3参照，9/11只作数量诊断，不称位置匹配成绩。

本次没有触发编译失败，所以**新失败草图只在本轮离线重放/MCP测试中验证，未证明生成模型实际利用它纠错**；成功源图确实返回。不同于旧run17，本次包含五图、更长预算及新反馈，不能作单变量归因。937秒正常结束仍失败，只说明这一次组织未达标，不证明有限模型智力在其他有效方法下无法达到目标。

## 核验与复现

- [原JSON与实际输入运输](declaration_execution_audit.json)、[原图与源图运输](execution_verification.json)通过。
- [原始墙网/宿主计算重放](compilation_verification.json)、[独立源重导出](source_replay.json)通过。
- [离线Chromium查看与旋转](browser_check/summary.json)通过，无外部请求或页面错误。
- [原始流归档](stream_archive.json)无损gzip，原始/解压SHA一致。保存候选及原始流未被事后评价改写。

复现入口：[run_quality.py](../2026-09-14_quality_feedback_setup/run_quality.py)。必须使用新目录；自动评价、运输审核、源重导出与查看沿用该setup及既有脚本。普通环境没有playwright，本次复用已有`/tmp/ep-bim-browser-qa/bin/python`，设置`PLAYWRIGHT_BROWSERS_PATH=/tmp/ep-bim-browser-qa/browsers`完成查看，没有安装/更新项目依赖。

下一项应围绕原图中物理隔墙及其两侧空间的完整对应、开口与宿主的独立性形成可核查观察，再验证是否引发正确修订。当前不据失败继续盲目加长整案或放宽几何检查；稳定性需后续重复及换例支持。
