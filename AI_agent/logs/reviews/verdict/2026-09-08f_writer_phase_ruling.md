# 裁决 · as_drawn writer 的阶段契约（GPT 席位 B 类停报的回复）

> **停报方** = GPT 席位（`8f46650d`）　**裁决方** = orchestrator
> 席位问的是：「as_drawn writer 该用**哪一个经过重放认证的、宿主解析前的状态**核验
> original/prefix，又如何绑定 finalize 后的候选？」

## 〇 ⛔ 先认一条：任务 B 的题面是我给错的，而且是**新种类**

我引用的病因是「as_drawn finalize 产出**空** corrections」。
席位实测：**补上窗之后 finalize 产出 31 条 corrections、0 条 conflicts** ⇒ 前提已假。

⭐ **这条病因写下来时是真的，是被【我自己这一轮的改动】变假的**（补窗把空 corrections 填满）。
⇒ 与之前几次「转引别人的事实」不同族。新的自查话术：
**引用一个事实时，除了问「它当时对不对」，还要问「我这一轮的改动会不会把它变假」。**
（停下上报读数 **74/74**，仍然全是派工方的题错。）

## 一 · 裁决：契约已经写在代码里，⛔ 不需要发明

`stage_runner.py:428-433` 的注释**原文**：

> `corrections` is append-only downstream of the core: window host resolution
> **APPENDS** `window_host_resolution` rows to it but never rewrites the core's own
> entries — so **the core-replayed list must be an exact PREFIX of the candidate's**,
> not a full match. The suffix's shape (exactly one row per resolved window, all
> `window_host_resolution`) is checked below once `audit_rows` exists.

⇒ **writer 要的是【宿主解析之前】的状态**；候选 = 重放前缀 + 宿主解析后缀。

而 `chain_replay.py:299` 返回的是 `finalize_as_drawn_chain_geometry(...)` 的结果 ——
**已经跑过 `apply_window_host_resolutions`** ⇒ 重放侧也带上了那 31 条
⇒ 后缀算出 0，而 `:481` 要求它等于 `audit_rows` 的 31 ⇒ `0 != 31`。

### ⇒ 修法（唯一一条）

**`replay_as_drawn_chain` 必须返回【宿主解析之前】的几何** ——
即 Vg 段 + 31 个窗都在，但**尚未** `apply_window_host_resolutions` 的那一份。
这正是 legacy 腿的 core replay 在同一位置交出的东西。

⛔ **不许改 writer 的前缀/后缀判断** —— 那是 F-22 拦截点的一部分，
且它对两条腿是同一份契约；改它等于为新腿放宽。
⛔ **不许删审计条目、不许跳过 gate**（席位本轮也没做，做得对）。

## 二 · 62 处容器类型差异：这是**比较方式**的缺陷，⛔ 不是可容忍的噪声

席位实测：`corrections` 的 `source_ids` / `tolerance_names` 在
**候选**（已归档字节重新加载）里是 `list`，在**内存重放**里是 `tuple`，
**元素与顺序完全相同**，来源是 `window_host.py:1062` 的 `audit.model_dump()` 与候选的 JSON 往返。

⇒ **两边不同源**：一边过了 JSON 往返、一边没有。
⭐ 与本项目一贯口径一致（零阈值比较要求两边同源）：
**把比较统一到 canonical JSON 之后再比**，⛔ 不是加一个「list 与 tuple 视为相等」的容忍分支
—— 那会顺带放过真正的类型漂移。

## 三 · 验收（不变）

⭐ 判据是**读数**，⛔ 不是「不报错」：
`run_win_e2e/1_correction/attempts/001/output.json` 里 **`windows` 长度 = 31**。
全量 `0 failed`（`PYTHONPATH=... /opt/venv/bin/python -m pytest -n 6 -q`，⛔ 禁 `uv run`）。

## 四 · 任务 B 的新题面（替换我给错的那份）

⛔ 作废：「finalize 产出空 corrections」。
✅ 现状：finalize 产出 **31 条 corrections / 0 条 conflicts**（席位实测）。
⇒ `correction.audit_completeness` 现在**还红不红、红在哪**，需要**重新实测**后再定题面。
⛔ 本裁决**不预设**它还红 —— 先修完 §一/§二，再拿真跑读数说话。
