# sm24 开发方法迁移：首轮未通过

[图形对照](index.html) · [失败候选旋转查看](candidate_01/viewer.html) · [逐项质量/改删记录](quality_audit.json) · [此前开发示范](../2026-09-16_sm24_developer_reconstruction/index.html)

本轮给Sonnet原五图、原建筑声明与新通用操作参考，没有旧BIM、开发坐标、正确房间/开口数量或GT。代码基点`ffad2b65`；实际主模型`claude-sonnet-5`、medium effort，1800秒上限内963.36秒正常结束。CLI估算$2.6217162，非订阅账单。没有局部Haiku委派；回执含CLI自身Haiku辅助用量，不能写成分工读图。完整输入、请求、工具轨迹和回执均保留。

## 实际发生了什么

模型读取`reconstruction`和`plan_partition`参考，11次原图查看覆盖五图，9次像素剖面量测。提交五份墙网草稿：

1. 端点未接齐，东南门洞处拆成两段而非带洞的完整墙，编译拒绝。
2. 接齐部分端点，但删除东南两段墙及该门；走廊和东南用途种子落同一空间，仍拒绝。
3. 合并用途种子，东外门错位且跨隔墙，宿主检查拒绝。
4. 将该门像素跨度从358–416裁成371–415，随后东长窗又因跨隔墙拒绝。
5. 将长窗像素跨度从472–646裁成472–585，成功导出**7空间/44边界/11窗/9门/9连接**。模型再看一次实际北立面及平面回叠，选择交付，没有修订源。

首份build后没有新的原图查看或像素量测，也没有开口回查。最后备注明确承认删除东南墙门、东侧尺寸未和平面核对、裁开口迁就宿主、部分窗高仅套用北立面。完整改删与动作计数见`quality_audit.json`；它们表明方法参考已送达，但关键返工方法没有执行，不能将其等同开发示范的完整方法复现。

## 独立结果

源几何自洽不等于还原成功。独立评价只在`summary.json`生成后执行，未回流生成：

- 原点统一后仍**severe**：东南房间与走廊错并，原图有的折角墙和门丢失。北横墙约7cm位置差另列，不与错并混为一类。
- 外开口虽然仍为11窗/3外门，东侧两扇短窗与一处外门却错位；沿墙重叠逐项配对仅11对，另3处参照原位缺失/源错处新增。11对也不代表正确：东长窗中心差约1.63m、宽少约1.69m，西侧四短窗顶高约0.60m。
- 三外门采用0–2.4m；相对图示/参照底顶低约0.20m。原图未明确地坪完成面，不据此推断台阶；内部门没有逐门GT，高度假设单列。
- 旧工作模型采用基点sm24/run12、sm21/run22与已核开发示范均不替换；这次失败不证明Sonnet能力上限或新方法可稳定迁移。

模型最终用北边y=0、南边y=-20，参照以南边y=0。`evaluation/`保留未经变换的原始结果；`frame_aligned_partition.json`和`opening_comparison.json`另保留显式[0,20,0]平移后的评价。位移由最终两轴声明和原图20000mm总长决定，不依据GT拟合墙位；无旋转/缩放、源候选字节不改。

## 验证

26项相关离线工具/编译检查通过（36.38秒）；新参考实际经stdio逐字送达。五原图和声明散列一致，proposal到源/显示字节精确重放；17张有保存对应物的工具返回图逐像素一致。普通原图裁看未逐张重绘核验，实际文件输入范围和散列已核。离线浏览器打开、旋转、源散列与交付页通过，无脚本错误/外部请求。详见`verification.json`及`browser_verification.json`。普通验证、GT、浏览器都不冒充用户验收。

源模型、草稿及其错误是生成期原始产物。后续新增的开口失败局部图反馈不在本次生成代码中；只在独立离线重放验证，不能反写成本次模型使用过或已改善。

## 复现命令

运行命令、模型/工具参数可从`agent_request.json`、`inputs.json`、`tools.jsonl`查回；新的模型实验必须另建目录。

```bash
python AI_agent/logs/experiments/2026-09-20_sm24_method_transfer_run01/verify_run.py \
  --original-dir case_tests/e2e_tests/sm24_anchor/case_data --gt \
  --translation-m 0 20 0 \
  --translation-basis '原图南北20000mm；最终声明北边0、南边-20；仅统一到南边0的坐标原点'
PLAYWRIGHT_BROWSERS_PATH=/tmp/ep-bim-browser-qa/browsers \
  /tmp/ep-bim-browser-qa/bin/python \
  AI_agent/logs/experiments/2026-09-20_sm24_method_transfer_run01/verify_browser.py
```

`align_evaluation.py`要求`--translation-m`和`--basis`，已有报告拒绝覆盖；复核须`--out`指定新文件。`verify_run.py`/浏览器脚本允许重算其独立核验报告，不能用于生成中。没有DeepSeek、付费API、EP或外部judge调用。
