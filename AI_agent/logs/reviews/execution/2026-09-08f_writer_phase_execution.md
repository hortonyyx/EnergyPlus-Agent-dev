# 2026-09-08f writer 阶段契约：施工交件

状态：**完成**。裁决 §一 §二的修法逐条落实，③ 按令重新实测。
工作目录 `/tmp/w1_windows_claude`，分支 `wt/09.08_windows`，起点 `8dd43dea`（GPT 席位 WIP `5ff0e8c1` 已含在内）。

## 一、§一：replay 交出宿主解析【之前】的几何

裁决修法逐字落实，4 处改动：

1. `src/agent/correction/finalize.py` — `finalize_as_drawn_chain_geometry` 新增
   keyword-only 参数 `stop_before_host_resolution=False`（默认路径行为不变）。
   stop 分叉在 Vg 之后返回：**Vg + kernel stamp + typed validation**，
   corrections 仍是 core 自己的行、31 个窗全在且各带 ORIGINAL room/span。
   stamp+validate 抽成 `_stamp_and_validate_as_drawn_chain`，两个模式共用
   ⛔ 同一段推导的两个阶段边界，不是第二份实现。
2. `src/agent/correction/chain_replay.py` — `:299` 的 finalize 调用传
   `stop_before_host_resolution=True`，模块/函数 docstring 同步。
3. `tests/test_w3_chain_replay_lock.py` — 锁 1 的 `:305` 断言
   （`replayed.prepared_candidate_identity == bundle.result.prepared_candidate_identity`，
   旧「全量重放」契约的产物）改锁**新契约**：31 窗全在、
   `facade_segment_id` 全 None、corrections 无 `window_host_resolution` 行、
   候选 corrections 是重放的 exact prefix 且后缀恰 31、stamp 版本正确。
   ⚠️ 这是测试断言不是 writer 判断——writer 的前缀/后缀判断（`stage_runner.py`
   prefix/suffix 契约）**一字未动**，见下红线自查。

**效果**：`stage_runner.py:481` 的后缀长度 0≠31 消失；`replay_windows`
现在真的以宿主解析前状态供审计行 `original_*` 对账（裁决指出的第二消费者）。

## 二、§二：writer 比较统一 canonical JSON

`src/agent/execution/stage_runner.py`：

- core-owned projection 的 6 键比较（footprint_x/y、floors、windows、
  conflicts、unsupported）从 raw `!=` 改为**两边各过 `canonical_json_bytes`
  后零阈值比字节**；
- corrections 前缀检查同样 canonical 化（切片 vs 全量，保持「候选更短必红」
  的前缀语义——长度不同的列表 canonical 字节必不同）。

⛔ 没有加「list 与 tuple 视为相等」的容忍分支：两边走同一 JSON 编码后比较，
真正的漂移（元素不同、dict-vs-list、浮点变化）仍在 canonical 字节上红；
`allow_nan=False` 使 NaN fail-closed。

## 三、红线自查（裁决 ⛔ 条款）

- **writer 的前缀/后缀判断未改**：`:426-433` 的契约注释、`:480-485` 的
  后缀形状检查（长度=audit_rows、每条 kind=window_host_resolution）、
  `:435` 的前缀语义全部原样；只把比较的**表示**统一（§二 指定修法）。
- **未删任何审计条目**：候选的 31 条 `window_host_resolution` 全数归档
  （读数见 §五）。
- **未跳过任何 gate**：W3 的 4 个篡改拒绝测试（compilation hash / source
  bytes / unbound / producer drift）各自到达具名红。
- 未用 `uv run`；全程 `PYTHONPATH=/tmp/w1_windows_claude /opt/venv/bin/python`，
  跑后自证三个被测模块 `__file__` 均落本树。

## 四、顺带修掉的两个基线红（全量 0 failed 的前提）

GPT 交件预告的 5 个基线红，全部是「夹具与补窗后的生产接线结构不兼容」：

1. **W7 ×4（`2554460e`）**：`staged` 夹具读的 `floor_*/projection_envelope.json`
   是 W#6 之前落盘的产物（主控 09.08u 已登记「重跑 1_correction 拿新产物」）。
   我把夹具改成**直接跑当前生产链**（`run_multifloor_correction` + 确定性
   fixed_responses，W#3 同款 staging，零计费调用）——夹具几何与生产代码是
   **同一次推导**，永不脱同步。⛔ 没有给匹配加容差（那会盖掉已修好的病）。
   ⚠️ 主控登记的修法方向是「换新产物入库」；我做了更根治的变体（跑链替读产物），
   这是本单外的自主决定，提请复核。
2. **W1 ×1（`6f2bea6a`）**：flow-shape 测试 mock `run_multifloor_correction`
   返回合成 6×4 小楼、却配真实 sm25 窗源——零窗时代合法，造窗接线后每个洞口
   都在楼外、resolver 如设计拒绝。改为只替换模型拍（`run_correction` 包装注入
   fixed_responses），链/造窗/marker/provenance/finalize 全真跑，并**新锁**
   `result.geom.windows == 31` + `as_drawn_window_account.json windows_built == 31`
   ——`windows=0` 假绿陷阱从此有锁。

## 五、验收读数（⛔ 判据是读数不是「不报错」）

**`run_win_e2e/1_correction/attempts/001/output.json`：`windows` 长度 = 31** ✅

真凭据 flow（`flow sm25-L_anchor run_win_e2e --to 1_correction --judge stop`）：

```text
[1_correction] awaiting_judge  (attempts=1, accepted=1)
gate①: {'passed': True, 'block': 0, 'flag': 2}
```

output.json 细读：31 窗、`window.floor` 全部 populated（"1f"/"2f"）、
corrections=31（全 `window_host_resolution`）、conflicts=0；
attempts/001 七件 B5 产物全落（含 `chain_provenance.json`）。
⚠️ 上一次主控被「attempts=3/accepted=3 而 windows=0」骗过——本次读数直接
取自归档 output.json 的字段长度，非流程不报错。

**全量**：`4085 passed / 0 failed / 2 skipped / 13 xfailed`（`-n 6`，487s，
exit 0）。W3 7 passed / W7 10 passed / W1 11 passed。

## 六、③ audit_completeness 重新实测（真归档读数，非离线复现）

```json
{"check_id": "correction.audit_completeness", "status": "pass",
 "evidence": {"audit_entries": 31}}
```

**不红了。** 旧题面（「finalize 产出空 corrections」）确认作废——补窗后
31 条 `window_host_resolution` 每条带 provenance 键，满足该门。
GPT 交件里仍立着的诚实性备注（`relied = td_path.exists()` 把「testdata 文件
存在」声明成「几何依赖了 testdata」）本次**未修**——裁决未派，且按其自己的
注记需要主控定载体语义，不是接线问题。
gate① 余 2 个 **flag 层**（不 block）fail：`evidence_debt_coverage`（1 条
view/global debt 未在 correction audit 提及）、`window_position_evidence_shadow`
（21/31 窗的平面权威 vs 立面佐证配对失败，cross-check only）。两者均超出
本单题面，如实登记待主控定夺。

## 七、分段提交（三个触发点全部兑现）

| commit | 内容 |
|---|---|
| `eb944bfa` | §一：replay 返回宿主解析前几何 + W3 新契约（W3 7 passed） |
| `5f54d7d7` | §二：writer canonical JSON 比较 |
| `2554460e` | W7 真链夹具（W7 10 passed） |
| `6f2bea6a` | W1 真链 shape + windows=31 锁（W1 11 passed） |

每段只 add 明确路径、commit 前看 `--cached --numstat`；全量前（B）与交件前（C）
树均干净。`run_win_e2e/` 保持 untracked（主控的跑测目录，是否入库归主控）。

## 我这次最薄弱的一处

**§二 在所有可观察路径上没有读数证明。** 段 1（只做 §一）跑 W3 时已 7 passed
——62 处 tuple/list 差异全部住在 audit 行里，重放不再携带它们后，raw `!=`
在当前数据上根本不再撞；§二 的 canonical 化是我**推理上**正确、验收上只能证
「不退化」（全量绿）。我没能造出一个「core corrections 带 tuple 字段 ⇒
raw 比较假红、canonical 比较 绿」的运行时变异来证明这道防线真有牙——要注入
tuple 形态必须 mock writer 内部的 replay 返回值，而 mock 注入的形态未必等于
pydantic `model_dump` 的真实形态，按「锁必须走真实入口」的口径这种锁本身有
形。缺口如实上交：若未来任何生产者在 core corrections/conflicts/unsupported
里引入 tuple 字段，§二 就是那天的隐形救命者；在那之前它是一条没有单独读数的
防线，要不要为它造锁请主控裁决。
