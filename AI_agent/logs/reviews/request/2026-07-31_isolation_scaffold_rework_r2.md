# 返工单 r2 · 硬隔离脚手架批（sol 对抗审 REWORK）

> 主控 Opus 5 · 2026-07-31
> 依据 = [sol 裁决书](../verdict/2026-07-31_isolation_scaffold_sol.md)（REWORK · 4 MAJOR / 3 MINOR）
> 主控独立复核：**MAJOR-1 / MAJOR-2 活体复现，MAJOR-4 读码确认，四条全部成立、无一驳回。**

---

## 0. 先说清楚责任

**MAJOR-2 的根因是主控的返工单 r1 写得不全**，不是施工方擅自缩范围。
r1 只裁了「content 角色整个免扫」，**没有裁「path 角色必须无条件检查」**，
于是实现保留了 `_looks_like_path()` 作为所有非 content 字符串的前置门 ——
无斜杠、无已知后缀的**裸路径**（如 `case_tests`）就整个漏出去了。

**这是今天第三次同一形状**（U-13 的成因分类 / r1 的 path 角色 / 本条），
与 2026-07-28 的 MAJOR-1 同族：**主控把边界写窄或写不全，就会被精确地实现得同样窄。**
本单因此把规则写成**对参数角色的全函数**，不留缺省分支。

MAJOR-1 / MAJOR-3 / MAJOR-4 属施工方与主控共同未预见（主控六条探针也没覆盖到 helper 副作用），
按常规返工处理。

---

## 1. 必修项

### R2-1 · MAJOR-2 · 词法检查改为「按参数角色的全函数」（主控独立复现）

**实况**：

```
                    file_path=case_tests      file_path=case_tests/x
f98d248（改造前）    DENY                      DENY
HEAD  （改造后）    ⛔ALLOW                    DENY
```

施工方的夹具用的是带斜杠的 `case_tests/x` ⇒ 测试照绿 = **夹具形状造成的假锁**。
同一缺口还令 bare、无后缀的越界 symlink（`file_path="escape"`）放行，
而 `"./escape"` 因以 `.` 开头才被拦 —— 安全性质依赖字符串长相，不成立。

**死骨架（三分支全函数，禁留「其余按形状猜」的缺省）**：

对**非 Bash** 工具，遍历 tool_input 的每个叶子字符串，按其所在的 **key 名**三选一：

| 角色 | key（显式枚举） | 处置 |
|---|---|---|
| **content 角色** | `content` / `old_string` / `new_string` / `new_source` | **一个字符都不扫**（r1 已对，保持） |
| **path 角色** | `file_path` / `notebook_path` / `path` / 以及 Read/Glob/Grep 的路径参数 | **无条件**做 `_lexical_check` + `_path_arg`，**不许**先过 `_looks_like_path` |
| **其余一切 key（含未知 key）** | — | **按 path 角色处理**（无条件检查）= fail-closed |

**「其余一律按 path 处理」是硬要求**，不是可选项：这样未来新增任何参数都默认落进安全侧，
要豁免必须显式加进 content 角色表 —— 也就是今天这个洞不会以第四种形状复发。
`_looks_like_path()` 保留给 `_validate_request_file` 用，**不再作为 path-role 的前置门**。

**必须新增的锁**：
1. bare `file_path="case_tests"` ⇒ **DENY**（与 `case_tests/x` 并列参数化，防夹具形状假锁）。
2. bare、无后缀的越界 symlink（`file_path="escape"`，`escape -> /etc/passwd`）⇒ **DENY**。
3. 未知 key 携带越界路径 ⇒ **DENY**（钉住 fail-closed 缺省）。
4. r1 的 prose ALLOW 锁全部保留仍绿。

### R2-2 · MAJOR-1 · 白名单 helper 的写副作用必须同样受约束（主控独立复现）

**实况**（主控在生产 `build_isolation_workspace` 产出的干净 staging 上复现）：
request 里写 `{"tool":"crop_zoom","args":{"out_dir":"tools",...}}`，
`guard rc=0` 放行、helper `rc=0` 执行，**真在 `tools/**` 下落了三个文件**。

⇒ 「子代理只能写 `out/**` + `requests/**`」这条声称**不成立**；
写保护只管住了 Write/Edit 的直接目标，管不到**唯一被允许执行的 helper 的副作用**。

**死骨架**：
1. `_validate_request_file` 必须**按 request 参数角色**判定：凡是会被 helper 当作**输出落点**的参数
   （至少 `out_dir`，请把 cv_toolbox 里所有写文件的 tool 逐个核一遍、列全），
   必须解析到**可写根**（`out/**`；`requests/**` 仅供请求文件本身），
   **仅「在 staging 内」不够**。
2. **wrapper 侧（`run_cv_probe.py`）做同一约束**，不要只在 guard 做 ——
   两处策略必须一致，避免 guard/wrapper 策略差。
3. 输入类参数（如 `image`）维持现状（staging 内即可）。

**必须新增的锁**：**真 E2E**——hook 放行后**实际执行 helper**，
比较执行前后整棵 staging 树，断言 `out/**` / `requests/**` 之外**零新增、零改写**
（`__pycache__` 与 `access_log.jsonl` 可显式豁免，但必须写进断言的豁免名单里、不许默默忽略）。
这条锁是本项必须交付的核心，光改判定不加锁不算完成。

### R2-3 · MAJOR-3 · 可写根自身是 symlink 时反向授权

`_check_write_target` 把 `(root/name).resolve(strict=False)` 当作允许根。
若 `out` 本身是指向 `tools` 的 symlink，则允许根解析成 `tools`，**写 `tools/**` 反而被放行**。

**死骨架**：guard 启动时（或每次判定时）校验每个可写根：
`(root/name)` 必须是**真实目录**且 `resolve()` 后**仍等于自身字面路径**、且在 staging 内；
任一不满足 ⇒ **fail-closed 拒绝该次调用**（不是跳过该根）。

**必须新增的锁**：预置 `out -> tools` 后，写 `out/x` ⇒ **DENY**。

### R2-4 · MAJOR-4 · S1 一致性锁是假锁（主控读码确认）

`test_build_kickoff_points_at_staged_worked_example_path` 的两条断言用的都是**常量**
`WORKED_EXAMPLE_STAGED`，不是从 kickoff 文本里**解析出来**的路径：

```python
assert str(WORKED_EXAMPLE_STAGED) in kickoff        # 常量是 ".missing" 变体的子串 ⇒ 仍真
assert (staging / WORKED_EXAMPLE_STAGED).exists()   # stat 的是常量路径 ⇒ 仍真
```

⇒ kickoff 改指 `...json.missing` 时该锁**不红**（sol 实跑 `3 passed`）。
docstring 却写着 *"a real stat, not a hardcoded string compare"* —— **声称大于实况**
（同族于 2026-07-26 的 Y-06）。而这正是派工单 §3-S1 点名要求的那把锁。

**死骨架**：从 kickoff 文本里**正则解析出它实际命名的那个路径字符串**，
然后 stat **解析出来的那个**；断言它存在。
**必须新增的锁**：把 kickoff 指针改成 `<staged>.missing` ⇒ 该测试**必须红**。

### R2-5 · MINOR-1 · `_write_target` 取首个命中 key，可被遮蔽

多个目标 key 同时出现时（如 `file_path` + `notebook_path`），只取第一个 ⇒ 真实落点可被遮蔽。
**改**：present 的目标 key **全部**校验；任一不合规即 DENY；出现 ≥2 个不同目标 key ⇒ 直接 DENY（歧义）。

### R2-6 · MINOR-2 / MINOR-3

- MINOR-2：S4 把**存在但损坏**的 `output.json` 当成「不存在」处理，超出授权的放松 ⇒ 改为损坏即响亮报错。
- MINOR-3：S4 glob neuter 的自查表漏报了一条同时变红的测试（`test_merge_per_image_extra_is_rejected`）⇒ 更正执行日志。

---

## 2. 纪律

1. **不许改测试迁就实现**；现有断言不得削弱。
2. 只碰 `src/agent/execution/isolation.py`、`isolation_templates/**`、`scripts/tool_scripts/cv_probe.py`
   及其测试。**不碰** `src/agent/judge/**`（另一批）、`case_tests/test_baseline/gt/**`（受保护）、`AI_agent/CLAUDE.md`。
3. 每项修完给 **neuter 自查表**：定点破坏 → 真跑 → 报实际变红的测试名。
   **本轮已有两把假锁（R2-1 夹具形状、R2-4 常量比对）被抓，请对自己的新锁用同样的怀疑。**
4. 跑测：中间轮用 `scripts/tool_scripts/affected_tests.py` 算子集，交付前跑一次全仓。
   **当前基线 = 1881 passed / 10 xfailed / 0 failed**（主控已独立复核，含另一批的 +95）。
5. 执行日志追加「返工 r2」节到 `AI_agent/logs/reviews/execution/2026-07-31_isolation_scaffold_glm.md`。
6. 骨架有错 ⇒ **停下上报**，不要自己改了再交。

## 3. 验收

sol 复审（r2），重点复验它本轮提出的四条出口是否真闭，并再找一轮新形状。
主控轻门：独立全量 + 亲核 diff + 抽查 neuter + **亲自复跑 R2-1/R2-2 的活体探针**。
