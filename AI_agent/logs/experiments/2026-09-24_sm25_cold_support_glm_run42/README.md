# sm25 首层原图冷启动 run42：未通过

[GLM最终候选](candidate_03/viewer.html) · [原图独立回叠](evaluation/independent_original_overlay.png) · [独立审计](postrun_audit.json) · [实际返工轨迹](evaluation/observation_and_edit_trace.json)

GLM订阅 `glm-5.3-flash` / medium，1893.10秒，CLI估算$3.5017328（非订阅账单），无局部子模型、其他模型或API回退。只给sm25首层原PNG，通用scope沿用run39/40，预算2400秒；启动前补齐凹形轮廓/凹入窗确定性编译。无旧稿、标定、数量、建筑声明、GT或中途开发内容指导，详见[设置](../2026-09-24_sm25_cold_support_setup/README.md)。

最终candidate_03为15空间/15窗/15门/15连接，几何自洽，但原始及声明坐标诊断均severe。30个已建门窗位置均在本轮容差内，26/31宿主、12/16门连接匹配，漏西侧下部外门。连续走廊在下侧转折处被一条假墙分成两个互不连通的空间；西侧上部办公室还误纳入一条约13cm宽、5m长墙带，不能把所有边界差异都解释为纯数值噪声。其他墙中线/外皮差异仍保留，不做厘米精修。

## 实际反馈与返工

共8份像素声明：首稿缺一条来源说明，第二稿混用墙面/代表线导致悬线，第三稿产生斜接线，第四稿成功围合但含假墙。draft_005/006/008虽断开了假墙，却同时删掉全部三条会议室隔墙，因空间种子冲突被拒绝；draft_007尝试以开口替代，仍丢会议室墙。不是编译器不能表达真实走廊。

模型后来调用完整路径支持工具，明确识别假墙中部为空白；另从candidate_01用米制开口续修产生candidate_02，开口未建。最终从candidate_01仅改假设/未决文字得到candidate_03，几何完全保持，并明确记录连通缺陷；没有完成开口清单回查。其“忠实修复被builder拒绝”的归因只属模型自述，已由下述控制实验纠正。

## 开发独立诊断（不回注模型、不改写成绩）

生成结束后，仅把draft_004的一条假墙替换为左右两条实际办公室底边，完整保留其余16条隔墙，立即生成14空间。原30门窗顶点、类别和13个非走廊房间完全不变，30/30宿主、15/15已建门连接恢复。再按原图补一扇西侧下部外门，得到14空间/15窗/16门，31/31位置与宿主、16/16门连接；无拆并/多房/漏房信号。该诊断仍有墙带及参考面偏差、严格分区severe，高度均是假设。

[辅助诊断模型](../2026-09-24_sm25_cold_support_setup/developer_repair_diagnostic/restore_missing_exterior_door/viewer.html) · [诊断回叠](../2026-09-24_sm25_cold_support_setup/developer_repair_diagnostic/restore_missing_exterior_door/independent_overlay.png) · [受控改动证据](../2026-09-24_sm25_cold_support_setup/developer_repair_diagnostic/summary.json)。这是开发选择改动的恢复，不是新GLM结果或完整采用基点。

源/显示精确重放、冻结代码/原图/scope与原图参照先于首稿均核验通过；23张实际返回图可解码，10张构建/路径反馈分别按原尺寸或实际缩略尺寸匹配保存RGB。旧共用运输审计只索引1600px缩略图，因此大尺寸失败草图的对应由[补充像素核验](evaluation/actual_feedback_images.json)证明。原始流无损gzip保留，viewer无远程脚本，未另做浏览器WebGL交互验收。无高度资料的内门不阻塞；单层结果不评价整栋、重复稳定性或EP。

下一项：让模型对已保存墙网做局部增删改并自动保留其余内容，避免为改一处走廊反复重写整表、误删会议室墙；随后从本失败声明做有界恢复并回查全部开口，再恢复单层冷启动验证。多层/立面后续再推进。
