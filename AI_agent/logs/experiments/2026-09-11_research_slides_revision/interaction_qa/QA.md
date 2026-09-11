# 整页交互 QA

- 入口：`showcase/2026-09-11-research-report/index.html`（`file://`）
- 浏览器：Chromium + SwiftShader，`--no-sandbox --use-gl=angle --use-angle=swiftshader --enable-unsafe-swiftshader`
- 网络：HTTP/HTTPS 全部拦截；所有轮次的实际外网请求均为 0
- 最终结果：通过

## 完整交互轮次

| 画幅 | 完整功能检查 | 外网请求 | page error | console error | 所处版本 |
| --- | ---: | ---: | ---: | ---: | --- |
| 1440 × 900 | 76 项通过 | 0 | 0 | 58 | `Scene.add` 空过滤修复前 |
| 1920 × 1080 | 76 项通过 | 0 | 0 | 0 | 修复后最终 embed |

两种分辨率均完整覆盖：

- 七页的上一页/下一页、目录、数字键、Home/End 导航；
- 页面滚轮不引起意外翻页；模型 canvas 内滚轮和普通按键不引起翻页；
- 第 1/3/5 页各一个 iframe、第 6 页两个 iframe，第 2/4/7 页无 iframe；
- 每个活跃 iframe 的真实 Three.js canvas 完成加载，拖动前后 canvas 像素摘要发生变化；
- 点击 iframe canvas 后，`ArrowRight` 经 `postMessage` 翻到下一页；小写 `f`、`o` 也能转发到父页；
- 离开页面后隐藏 iframe 的 `src` 与加载标志移除，返回后重新出现真实 canvas；
- 第 5 页两张平面和四张立面均使用实际原图，六图同时有自然尺寸和可见尺寸；
- 第 5、6 页输出侧均标为“轻量 BIM / Lightweight BIM”；
- 不存在 `.demo-button` 或 `<dialog>` 元素；模型源页面的旧 `aside` 面板均不可见。

1440 × 900 完整轮次末尾捕获的 58 条同类 console error 为：

```text
THREE.Object3D.add: object not an instance of THREE.Object3D. undefined
```

这是 embed 的场景装饰过滤器在过滤出空数组后仍调用 `Scene.add` 导致的错误。该轮只作为修复前完整功能证据，不能作为最终控制台通过证据，也没有对错误做豁免。逐项原始记录保存在 `results.json`。

## 修复后最终回归

空 `Scene.add` 调用修正后，在最终文件上补跑 1440 × 900 最短回归；与修复后 1920 × 1080 完整轮次共同覆盖最终构建：

| 最终 embed | 实际位置 | canvas | 加载 | 拖动像素变化 | 旧 raw 面板 |
| --- | --- | ---: | --- | --- | --- |
| sm25 轻量 BIM | 第 5 页 | 787 × 426 | 通过 | 通过 | 不可见 |
| Voimatalo 原始贴图 | 第 6 页左侧 | 547 × 426 | 通过 | 通过 | 不可见 |
| Voimatalo 轻量 BIM | 第 6 页右侧 | 671 × 426 | 通过 | 通过 | 不可见 |

最终短回归结果：外网请求 0、page error 0、console error 0。机器可读证据保存在 `final_console_recheck.json`。

## 执行命令

完整双分辨率轮次：

```bash
PLAYWRIGHT_BROWSERS_PATH=/tmp/ep-bim-browser-qa/browsers \
  /tmp/ep-bim-browser-qa/bin/python \
  AI_agent/logs/experiments/2026-09-11_research_slides_revision/interaction_qa.py
```

embed 修复后的最短控制台回归：

```bash
PLAYWRIGHT_BROWSERS_PATH=/tmp/ep-bim-browser-qa/browsers \
  /tmp/ep-bim-browser-qa/bin/python \
  AI_agent/logs/experiments/2026-09-11_research_slides_revision/interaction_qa.py --console-recheck
```
