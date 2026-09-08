---
name: headless-seat-silence-is-not-death
description: 判席位死活只能按 /proc/<pid>/environ 或可执行名——日志空白≠死，pgrep -f 命令串会匹配到自己；席位撞额度会留下污染主线的孤儿半成品
metadata:
  node_type: memory
  type: feedback
  originSessionId: 09798ed8-e8c7-49aa-acbb-c22338642851
  modified: 2026-08-30T08:10:00.000Z
---

2026-08-28 实犯，一次踩三个坑：

1. **`bash scripts/glm_code.sh -p ...` 跑满 10 分钟、日志只有一行启动 warning** ——
   我按 timeout 砍了它。**其实它在正常工作**：headless `-p` 模式**只在整轮结束时输出**，
   中途日志必然是空的。⇒ **日志空白不是进度信号，什么都不是。**
2. **改用 `nohup ... &` 塞进工具调用** —— 工具返回后我 `pgrep` 没找到、`ps` 也没有近期进程，
   判定"没起来"又重启一次。**实际它活着**（进程名是 `claude`，不是 `glm_code.sh`，
   而我 grep 的是脚本名）⇒ 造出**两个 GLM 会话跑同一份题**：
   踩 §5#7.5「同家族⛔ 不许并行两个」，烧双份额度，**且两边会抢写同一个输出文件**。
3. 正解 = **工具自带的 `run_in_background`**（跨轮次常驻、结束有通知），
   ⛔ 不要自己 `nohup &`。

**判席位死活的唯一可靠方法**（⛔ 不看日志、⛔ 不 grep 脚本名）：
```
for p in $(ps -eo pid,comm | awk '$2=="claude"{print $1}'); do
  tr '\0' '\n' < /proc/$p/environ | grep -q "bigmodel.cn" && echo "GLM 存活: $p"
done
```
按 **`/proc/<pid>/environ` 里的 `ANTHROPIC_BASE_URL`** 认家族 —— 进程名全都叫 `claude`，分不出来。
重启任何席位**之前**先跑这一段；**重启之后**再跑一次确认"恰好一个"。

---

## ⭐⭐ 2026-08-30 补两条（同一天各犯一次）

### A · `pgrep -f "<命令串>"` **会匹配到发出这条命令的我自己**

我用 `pgrep -cf 'codex exec'` 确认 GPT 席位是否存活，得到 `1` ⇒ 判"活着"。
**实际那 `1` 是我自己那条含 `codex exec` 字样的 bash 命令行**，真正的席位**已经死了**。
⇒ ⛔ **认进程一律不用命令行字符串**。可靠写法二选一：
```
ps -eo pid,comm,args | awk '$2=="codex" && $0 ~ /exec/ {print $1}'   # 按【可执行名】+ 参数
tr '\0' '\n' < /proc/<pid>/environ | grep ANTHROPIC_BASE_URL          # 按【环境变量】认家族
```
⭐ 与本条正文同根：**载体选错**——我以为在量"进程"，实际量的是"包含某字符串的命令行"
（同族 [[gate-measures-right-but-carrier-gets-swapped]]）。

### B · 席位撞额度上限 ⇒ 留下**污染主线的孤儿半成品**

GLM 席位施工到一半撞 **5 小时使用上限**（`429 · [1308]`，限额约 3 小时后重置）。
它**不是没起来，是干到一半被拦断**：树上留下 **未提交、未跑测、未过审** 的
新文件 707 行 + 改动 156 行 + 5 个探针。

⇒ **主控在收到席位失败通知后，第一件事永远是 `git status --porcelain`**，⛔ 不是只读日志。
理由：孤儿半成品**会污染任何后续跑测**（包括权威全量），而它在日志里一个字都不会提。

**处置（三步，做完主线才算干净）**：
1. 半成品**移出 `src/`**，存进 `logs/experiments/<日期>_<单号>_probe/`；改动文件 `git checkout --` 还原。
2. 写 README **写死定位**：**「本目录一切是线索，不是证据」**——没交件 / 没自评 / 没跑测 / 没过审，
   ⛔ 接手方不得直接采信或复制（同族 [[rework-review-needs-the-same-shape-input]]）。
3. ⭐ **主控扫一眼，把自己看到的可疑处点名写进 README**，交给接手方**自己判**、⛔ 不代判。
   本次点名两处：① 它把 jamb-cap 推导换成从 `wall_bands` 取——而 `wall_bands` 正是
   「33 条虚构墙」的病根载体，**这里用它也许恰恰是对的，但需要论证，⛔ 不能因为"看起来合理"就放行**；
   ② 删掉了一段有出处的记账注释而变量保留，**分不清是重构完成还是改到一半断的**。

⭐ **派工给接手方时必须显式写**：「从派工单**重新实现**，那个目录只当『有人先趟过一遍』的参考；
若复用任何一段，**必须自己重新论证 + 自己补锁**，⛔ 不许写『沿用上一席位的实现』。」

同族：[[exit-code-file-must-not-be-reused-across-runs]]（判跑完看汇总行不看退出码）·
[[wrapup-commit-sweeps-other-seats-wip]]（有席位在飞就禁 `git add -A`）·
[[codex-execution-protocol]]（并发治理：跨家族可并行、同家族不许）。

**⭐⭐ 2026-09-02 再补两条（都是【死席位】而不是沉默席位）**：
1. **root 下 CLI 拒绝 `--dangerously-skip-permissions`**（原文：`cannot be used with root/sudo privileges`）
   ⇒ 席位**启动即死**，日志只有那一行。**⛔ 关键点：死席位与活席位都留下近乎空的日志** ——
   所以「日志空 ≠ 死了」这条**反过来也成立**：**日志空 ≠ 活着**。
   ⇒ **发射后必须显式 `kill -0` 查存活**（已写进 `scripts/seat_{claude,glm,gpt}.sh` 的三秒检查）。
   合法出口 = **显式工具白名单**（`--permission-mode acceptEdits --allowedTools Bash Edit Write Read Grep Glob`），
   ⛔ 不是 `IS_SANDBOX=1` 那种绕过安全检查的写法。
2. **codex 席位在本 dev container 里 `--sandbox workspace-write` 全程不可用** ——
   `bwrap: No permissions to create a new namespace`（容器不允许非特权 user namespace）
   ⇒ 它的**每一条 shell 命令都失败**，整轮零交付。
   ⭐ 但该席位**拒绝拿施工方自述代替实测、也没有据此擅下裁决** —— 这是正确行为，⛔ 别记成它失职。
   修法 = `--sandbox danger-full-access`（容器本身即沙箱），⚠️ 但该命令会被权限分类器拦，需要用户放行。

**⭐⭐ 2026-09-03 再补一条（差点让一个家族白白空转 8 小时）**：
**席位报的「限额将在 X 重置」用的是 provider 的【本地时区】，⛔ 不是 UTC。**
实例：GLM 报「您的限额将在 2026-09-03 **15:13:43** 重置」，我按 UTC 算出「还差 472 分钟」并据此
准备让它闲置；对账才发现错误 trace id 里的 `20260903120306` = **北京 12:03**（= UTC 04:03），
5 小时窗口 ⇒ 北京 15:13 重置 = **UTC 07:13**，而当时已是 **07:21** ⇒ **早就恢复了**。
⇒ **判断家族可用性时，⛔ 不许拿那个时间戳直接和 UTC 比**；最省事的做法是
**直接试发一次**（失败成本 ≈ 0，而误判成本是整条线停摆数小时）。

