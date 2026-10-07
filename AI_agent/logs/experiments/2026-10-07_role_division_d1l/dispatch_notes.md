# D1l E/F 派读图接口离线记录

范围：domain 的 roles/tools 交界，只改分工模式。检查来源为主树只读历史运行
`archive/local_backup/merged/sm25_role_n1`；本轮模型请求 0，未操作 `runs-q`，未运行 pytest。

## 首次自动补齐

- `inputs.json` 已明确把 `1f_view.png`、`2f_view.png` 列入 `floor_plan_images`，因此只按该清单认平面图。
- 同一输入清单中的 `North_view.png`、`South_view.png`、`East_view.png`、`West_view.png` 符合项目已有的四向立面命名约定，四个方向均覆盖。
- 首次有效派读图时，按角色加图名和规范化目标去重；已有明确 North 目标时不再补 North。显式任务的 `instructions`、`origin` 和其他字段保留。
- 默认平面目标从 `1f/2f` 文件名得到 `F1/F2`；自动任务继承首批显式任务的共同原点，只有显式任务没有给出可用原点时才回退到西南外角，东、北、上分别为正方向。立面目标随后带上本批全部平面楼层。
- 未列入 `floor_plan_images`、又不符合四向立面命名的图片不猜类型，也不自动派出；需在输入准备阶段补充明确语义，或由调度员显式派读图任务。
- 自动补齐清单随 `delegate_readers` 的精简返回保留。已有任一读图记录后，后续派读图不再自动补齐。

## 历史参数重放

1. 事件 35 的 `plan_f1` 说明为 425 字符，超出 25；新错误直接指出任务、超出字符数，并说明该字段可省且只写图纸事实或具体返工问题。同批 `plan_f2` 为 392 字符，本身未超限。
2. 事件 1284 使用 `rework_targets=["plan.openings"]`，旧实现启动子任务后才失败；新实现把它规范为开口集合范围。`openings` 等价，`openings:W1` 规范为 `plan.openings:W1`。
3. 事件 1309 的具体对象写法正确，但说明为 403 字符，超出 3；新错误同样给出具体超量。

开口集合范围只在试建审计时展开为修改前后实际出现的开口 ID，因此允许补一扇尚不存在的窗，同时仍拒绝隔墙、房间种子、标高等未指向对象的变化。未知写法返回三个例子：`plan.openings`、`openings`、`openings:W1`。

## 检查建议

已做 AST 语法检查、LF 检查和不发模型请求的函数级探针。按派工要求没有运行 pytest；集成时建议运行 `test_role_c4.py`、`test_role_session.py`、`test_role_rework_handoff.py`，再跑项目经理安排的角色检查与三例离线贯通。
