# Voimatalo 第二版：先推理缺面构成，再补几何

用户要求补全两端缺图处和正面凸出的竖向交通盒，并统一为 sm25 的 HTML 形式；随后强调“也不一定是封闭墙面”，需要先判断缺失面是什么，再补全。本次继续由主助手直接判读、确定性代码建模，展示包装委派 Terra。没有生产模型、DeepSeek 或 EP 调用。

## 判断依据与实际修改

第一版单体 GLB 按较粗公开轮廓裁剪，两个端面和内院窄条存在大面积缺失。本次除了重新检查原单体完整贴图，还查看了已有**去标签父瓦片**的有限上下文；这是本轮新增辅助信息，不能混成相同输入下的自动生成成绩。环境只作证据，没有进入目标 BIM。

1. **两端分别推理**：[`context/courtyard.png`](context/courtyard.png)、[`context/top.png`](context/top.png) 显示两端紧邻其他建筑；残存露出部分与山墙相符。本案据此推断为贴邻/露出山墙，不沿这些界面复制办公窗排。隐藏部位的实际开口仍未核实，判断不是由“缺图”单独推出。
2. **正面凸出体量**：[`missing_measurements/core_front.png`](missing_measurements/core_front.png) 和 [`core_side.png`](missing_measurements/core_side.png) 显示原裁剪漏掉的凸出主面及旁边退入的窄窗列。量测主面集中在局部 u=2.25–2.50 m，原主楼立面约 u=0.7 m。新增阶梯形交通盒，外伸约 1.7 m，窄窗带面约 u=1.15 m；竖向交通用途仍是结合用户建议与建筑常识的推断。
3. **带窗与不透光部分区别处理**：凸出的白色主面以不透光墙表示，旁边窄窗带补六组错层窗口；没有把整个缺口统一封成空白墙。窗的精细边界、高程及交通设备未核实，保存规整依据。
4. **空间与连接**：新交通盒为 0–27.6 m 连续空间，没有中间封堵楼板；每个主楼层有一处推断连接门。细分版在原走廊上增加一条局部支路，通过调整临近两个假设办公室接到新交通盒；原 316 个窗组及其顶点全部保留。

## 当前交付

[标准查看器主入口](../../../../showcase/2026-09-11-research-report/demos/textured-mass/index.html) · [外壳版](../../../../showcase/2026-09-11-research-report/demos/textured-mass/envelope.html)

| 版本 | 空间体 | 窗组 | 门 |
|---|---:|---:|---:|
| 外壳与楼层 | 13 | 322 | 10 |
| 空间推理方案 | 165 | 322 | 173 |

新源数据保存在展示目录 `revision_02/{exterior,inferred}/`，第一版 `exterior/`、`inferred/` 保留。主页面改用与 sm25 相同的原生左右面板、控制及颜色规则；模型说明和推断记录保存在源 JSON 与 README。没有修改 sm25 或共享查看器实现。

## 代码与核验

- `inspect_missing_context.py` 从去标签父瓦片裁出有限观察范围，保留上下文截图；`measure_missing.py` 保存交通盒的局部纹理与主面量测直方图。脚本只读原资产，未读取标签或内部 GT。
- `build_revision.py` 基于第一版建模代码生成新候选，复用原 316 个窗组观察和共用源内核。新输出目录必须不存在；一次空 enclosure 声明失败保留为 `failed_empty_declaration/`，之后按实际交通盒的 enclosed 空间声明使用接口，没有修改内核绕过检查。
- 两版源几何、接触和开口宿主检查 pass；七个标高下，主楼加交通盒的覆盖差为零，没有实质面积重叠。原 316 窗组逐 ID/顶点核对一致；交通盒仅底/顶两个水平面，八处连接门已建。
- `build_standard_viewers.py` 只包装展示层。连续空间在单层过滤中按高程裁显，已有该层楼板保留；单层隐藏顶面，并将显示裁面向楼板下方偏置 2 mm，消除共面浮点斑点，源几何不变。HUD 区分八个主楼层与十个标高层级，避免把屋顶标高算成主楼层数。
- [`geometry_and_preservation.json`](geometry_and_preservation.json) 独立核对保存的源哈希、旧窗顶点、交通盒无中间水平面和每版十个门窗宿主的实际扣洞面积；原 GLB、sm25 HTML、第一版源 JSON、去标签父瓦片哈希与已有基线一致，产品代码与输入未改。
- [`browser_qa_final/report.json`](browser_qa_final/report.json) 与截图保存整体、旋转、按层/按空间展开和恢复查看；无错误或网络请求，仅有浏览器截图时的 GPU 性能 warning。主助手查看 F3 截图发现共面斑点后修正本地裁显，旧图保留；最新强制离线检查在 [`browser_qa_offline/report.json`](browser_qa_offline/report.json)，绑定最终 HTML 哈希，两版 F3 可看、无页面异常、失败或外部请求。最终平面图为 [`browser_qa_offline/index_f3.png`](browser_qa_offline/index_f3.png)，源数据不因显示修正改变。

检查仅证明本次补全方案可用、自洽及可查看。贴邻界面、交通用途和内部布局仍含推断，不等于真实建筑保真验收或仿真验收。第一版源状态为 unknown 的含义和灰色显示均保留在原实验；当前按照新增证据作了明确推断，不能把推断转为实测事实。
