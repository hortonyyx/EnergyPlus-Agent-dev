# 2026-09-05 · 席位名册探针（GPT-6 Astra / GLM-5.3-flash）

> **性质 = 主控自己量的一手读数**（⛔ 非转引）。用户当日令：「核一下 GPT 那边是否可以调用，
> 可以的话加到模型家族作为最高档；glm-5.3-flash 也加进来，暂定和 deepseek flash 一档，且具有识图能力。」
> 结论已写入 [`../../../guides/codex_execution_protocol.md` §1](../../../guides/codex_execution_protocol.md)。

## 一、GPT-6 Astra

### 1. 模型 id = `gpt-6-astra`（官方文档，非猜）
`https://developers.openai.com/codex/models` → 308 → `https://learn.chatgpt.com/docs/models`：
`gpt-6-astra` / `gpt-5.6-{sol,terra,luna}` / `gpt-5.3-codex-spark`(Pro only)。

### 2. ⛔⛔ 第一次探针【不可判读】—— 两种原因压成同一句话
CLI **0.144.1**（2026-07-10 装）下：
```
$ echo "Reply with exactly: OK" | codex exec -m gpt-6 --sandbox read-only --skip-git-repo-check
ERROR: 400 "The 'gpt-6' model is not supported when using Codex with a ChatGPT account."
```
**同一句话也出现在**：`gpt-6-codex` · `gpt-6-sol` · **`zzz-not-a-model`（我编的、必然不存在）** · `gpt-5.5-pro`（真实存在但本套餐无权）。
⇒ **这条报错分不清「id 不存在」「套餐无权」「CLI 太旧」三种原因** ——
若当时就据此回报「GPT-6 调不了」，会是一条**由代理量得出的错结论**。
对照组 `gpt-5.6-terra` 同命令返回 `OK` ⇒ 通道本身是通的。

### 3. ⭐ 真正可判读的那次：用**正确 id** 探，报错立刻换了一句
```
$ echo "Reply with exactly: OK" | codex exec -m gpt-6-astra ...      # CLI 0.144.1
ERROR: 400 "The 'gpt-6-astra' model requires a newer version of Codex.
            Please upgrade to the latest app or CLI and try again."
```
**报错文案本身就是判别签名**：版本门 ≠ 套餐门 ⇒ **本账号有权，只是 CLI 太旧**。

### 4. 升级后实测通过
```
$ npm install -g @openai/codex@0.153.4     # 原 0.144.1 → npm latest 0.153.4
$ codex --version                          # codex-cli 0.153.4
$ echo "Reply with exactly: OK" | codex exec -m gpt-6-astra --sandbox danger-full-access --skip-git-repo-check
model: gpt-6-astra / reasoning effort: xhigh / codex → OK      (tokens used 7,877)
```
**回归验证（升级没打坏既有通道）**：
- `codex exec -m gpt-5.6-sol` → `OK`（tokens 3,201）
- `bash scripts/seat_gpt.sh <dir> <prompt> <log> gpt-6-astra` → 席位起来、**真跑了 shell**
  （`/bin/bash -lc 'echo SEAT_OK'` succeeded）→ 末行 `SEAT_OK` ⇒ 启动器四个参数与
  `--sandbox danger-full-access --skip-git-repo-check` + stdin 喂 prompt 的契约在 0.153.4 下不变。

**账号事实**：`~/.codex/auth.json` → `auth_mode=chatgpt`，plan_type=**plus**。

## 二、GLM-5.3-flash

### 1. 文本通道（`$GLM_BASE_URL/chat/completions`）
| id | 结果 |
|---|---|
| `glm-5.3-flash` | ✅ 200，正常出 token（**thinking 强制常开**，`reasoning_tokens` 照计——与 glm-5.3 同）|
| `glm-5.3` | ✅ 200 |
| `glm-5v-turbo` | ⛔ **`{"error":{"code":"1311","message":"当前订阅套餐暂未开放GLM-5V-Turbo权限"}}`** |

### 2. ⭐⭐⭐ 识图实测（anthropic 端点 `/v1/messages`，base64 image block —— 与席位真实通道同形）
自造矩形图，**答案不可猜**：每张同时问【矩形数量】+【指定序位的颜色】两个量，**两个都对**才算「看见了」
（只问数量会被瞎猜命中 —— 这正是探针要两个量的原因）。两种图形几何各跑若干次：

| 试次 | 图（真值） | `glm-5.3-flash` | `glm-5.3` |
|---|---|---|---|
| 1 | A：7 矩形 / 第 5 红 | ✅ 7 / red | ⛔ 自称**看不见**（"I cannot actually see the image"）|
| 2 | B：4 矩形 / 第 2 绿 | ✅ 4 / green | ⛔ 自称**看不见**（`max_tokens` 900 下完整答完）|
| 3 | A'：7 矩形 / 第 5 红 | ✅ 7 / red | ✗ 7 / **orange** |
| 4 | B'：4 矩形 / 第 2 绿 | ✅ 4 / green | ✗ **3** / **yellow** |
| 5 | A' 复测 ×3 | ✅ 7 / red | ✗ **6** / pink · ✗ 7 / **blue** |
| 6 | B' 复测 ×3 | ✅ 4 / green | ✅ 4 / green · ✗ **6** / green |

**逐位计数**：`glm-5.3-flash` **6/6 两个量全对**；`glm-5.3` **6 次里只 1 次全对**，另有 **2 次自称看不见**、
3 次数量或颜色答错。

⇒ **三条一手结论**：
1. **`glm-5.3-flash` 有真识图能力**（两种几何、两个量、6 次全对）。
2. ⛔⛔ **`glm-5.3`（旗舰）不可作识图用，且失败形态是【静默的】** —— 接口**收下** image block、
   **返回 200**、照常出一段像模像样的推理，只是有时说「我看不见」、有时**直接答错**（6 矩形 / 黄色 / 蓝色）。
   **它不报错** ⇒ 不专门量就会以为它看过图了。
   ⚠️ **⛔ 别把这条写成「它是瞎的」** —— 它 6 次里对过 1 次、且数量常对颜色错，
   实测支持的说法只有「**不稳定且静默出错，不能承重**」。
   （同族教训：[[instrument-blind-to-the-asked-quantity]] / [[absence-conflates-causes-in-observables]]）
3. **原册子里 GLM 侧唯一的视觉候选 `glm-5v-turbo` 今天已被套餐挡死（1311）**
   ⇒ **GLM 家族今天唯一能承重看图的就是 `glm-5.3-flash`**。

## 三、复现脚本
`vision_probe.py`（同目录）= 造两张探针图 + 打两个端点。⛔ 凭据从 `.env` 读，脚本里没有明文。
