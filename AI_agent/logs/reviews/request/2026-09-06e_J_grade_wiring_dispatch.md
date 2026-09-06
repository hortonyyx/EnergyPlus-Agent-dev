# 派工单 · **J：判分接线 + 补立面**（闸⑤ · 第一次跑 sm25 要「跑通 ＋ 判出分」）

## 〇 状态与分工

- **施工方**：**GLM**（`scripts/glm_code.sh`，默认 `glm-5.3`）· **审**：**Claude 家族**（⛔ 不得同族自审）
- **基点**：主线 HEAD `8c66e3fd`（⭐ 必须用这个）
- **工作目录**：`/tmp/j_grade_glm`（`wt/09.06e_j_grade`）
- ⚠️ **同期有另一条线在飞**（E-a′，`gpt-6-astra`，动 `src/agent/correction/`）
  ⇒ **跑测一律 `-n 6`**，且 ⛔ **不许碰 `src/agent/correction/` 与 `src/agent/pipeline.py`**。

---

## 一 ⭐⭐⭐ 事实基线（主控 2026-09-06 只读实测，⛔ 非转引）

```sh
# ① 新的识图判分器【存在】，且已经是容差带比对（⛔ 不是逐位相等）
grep -n "POS_TOL_M\|END_TOL_M\|def grade" src/agent/judge/as_drawn/reading_grade.py
#   :47 POS_TOL_M = 0.08   :49 END_TOL_M = 0.30   :116 def grade(...)

# ② 但它在生产路径上【零调用者】
grep -rn "reading_grade" src/ scripts/ --include=*.py | grep -v /tests/
#   只有 :287 的自身版本串、render_grade.py 的两处函数名、docstring 引用
#   ⇒ 没有任何地方 import 它的 grade()

# ③ flow 现在仍然走【旧】识图判分
grep -n "reading_score" scripts/tool_scripts/run_stage.py
#   :1483  from src.agent.judge.reading_score import floor_name_for_image, score_floor

# ④ 新判分那三个文件对立面【完全没有覆盖】
grep -rci "elevation\|facade\|立面" src/agent/judge/as_drawn/*.py
#   __init__.py:0   denominator.py:0   reading_grade.py:0
```

**⇒ 缺的是「接线」和「立面」，⛔ 不是判分器本身。**（这一点很重要：别去重写 `reading_grade.py` 的打分逻辑。）

---

## 二 本单要做的三件事

### 2.1 ⭐ 接线：让 `flow` 的识图段走新判分器

- 目标态：`flow <case> <run> --judge stop --to 0_reading` 跑完，**自动产出**新格式的
  `score_vs_gt` / `grade.png` / `attempts/NNN/`，⛔ 不需要任何人手工调 API。
- 已有的画图脚本 [`render_reading_grade.py`](../../../../scripts/tool_scripts/render_reading_grade.py) **今天也零调用者** ⇒ 一并接上。
- ⛔ **不许删旧路径** —— 旧 `reading_score` 还服务历史 run。新旧并存，**由产物的契约决定走哪条**
  （⭐ 复用 `src/agent/reading/vector_contract.py` 的分类器，⛔ **不许按文件名判**，
  ⛔ **不许自己再写一个第二分类器** —— 那正是该文件头 #1 点名禁止的「第二处定义」）。

### 2.2 ⭐⭐ 补立面（J-3 的验收项）

- 目标态：**sm25 四张立面每张都判得出分**。
- ⛔⛔ **硬禁令：不许有「一张立面跨两层就整份丢」这一档**（F-89 的老形状）——
  sm25 四张立面**每张都跨 F1+F2**，那一档等于四张全丢。
  ⇒ **必须有一条锁**：喂一张跨两层的立面，**必须判出分**，⛔ 不许 filter 掉。
- ⚠️ ⛔ **不是去改旧的 `elevation_score.py` adapter** —— 那是旧格式的活。本单是**在新判分器里建立立面维度**。

### 2.3 判分口径两条（写进实现，⛔ 不写散文）

> **J-1**：判分**必须容差带比对**，⛔ 不许逐位相等。
> 理由：pipeline 出口 **10 mm** 网格、gt **1 mm** ⇒ **最大差半格 5 mm**；写成 `==` 会全红。
> ⭐ 平面侧 `reading_grade.py` 已经是容差带了（`POS_TOL_M=0.08`）—— **你新建的立面侧要同样处理**。
>
> **J-2**：两个分辨率（gt 侧 1 mm / pipeline 出口 10 mm）**各自声明 + 各自消费**，
> ⛔ **不是「要求两者相等」**。⭐ 该规则今天尚未实现 ⇒ 现在定形来得及。
> **要求**：两个分辨率各有**一个具名常量 + 一个声明点**，判分侧**读声明**，
> ⛔ 不许在判分代码里写死数字。喂一份声明了别的分辨率的产物，判分必须**跟着变**（给一条锁证明）。

---

## 三 ⭐⭐⭐ 必须先量、⛔ 不许假设的一件事

**新判分器的立面维度，答案侧supply得起吗？**

主控只量到这一步（⛔ 没有再往下核）：

```sh
python3 -c "import json;d=json.load(open('case_tests/test_baseline/gt/sm25-L_anchor/gt.json'));print(list(d.keys()))"
#   [... 'floors'(2), 'openings'(34), ...]   ⇒ 洞口 34 条在一个平铺列表里
ls case_tests/test_baseline/gt/sm25-L_anchor/review/
#   opening_elevation_audit.json  ← 另有一份立面审计件
```

⇒ **本单第一步：量清楚「新判分器判一张立面，需要答案侧给什么；今天的 gt 给不给得出」。**

- ⛔ **不许假设它够用，也不许假设它不够。** 量。
- 交出**逐项对照**：立面判分需要的每一样 × 今天 gt 里有没有 × 在哪个字段。
- ⭐ **如果答案侧确实缺** ⇒ **A 层停报**。⛔ **别在判分单里改 gt**（gt 铁律 §1.5#4：
  动答案根等于全部历史成绩作废；且 sm25 gt 整份重签是排在这批改造之后、要用户签字的另一件事）。

---

## 四 硬约束

- ⛔ **不碰**：`src/agent/correction/**` · `src/agent/pipeline.py` · ⭐ **`src/agent/reading/vector_contract.py`**
  （这三处 **E-a′ 正在改，会撞车**）—— §2.1 要你**复用**那个分类器，是 ⭐ **只读复用**：
  ⛔ 不许改它、⛔ 不许在它里面加新契约。若你发现非改不可 ⇒ **A 层停报**（两单同时改一个文件必撞）。·
  `case_tests/test_baseline/gt/**`（答案根）· `src/agent/judge/as_measured.py`（A-11 刚落）。
- ⛔ **判分器绝不 import gt 以外的答案通道**；`gt.py:load_gt` 是**唯一可读 gt 的入口**（不变量 §1.5#4）。
- ⭐ **判据不许从结果反着写** —— ⛔ 不许把「本轮实测出来的那几个数」写成通过标志。
  自查话术：**「这条判据什么情况下会不通过？」** 答不上来就是写错了。
- ⭐ **绿锚必须锚在本单自己负责的那一段上**，⛔ 不许锚在「整份全绿」上（那会让本单的锁成为别人家缺陷的人质）。
- ⛔ 新加的锁**不许只有负向断言**（只会恒绿/恒红、结构上不可观测）。
  每条锁都要**当场证明它能变红**，且**变异方向要对**（粗化无牙 / 细化恒等都不算）。

---

## 五 跑测与纪律

```sh
cd /tmp/j_grade_glm && \
python -c "import src.agent.judge.as_drawn.reading_grade as g; print(g.__file__)" && \
python -m pytest -q -n 6 -p no:cacheprovider
```

- ⭐⭐⭐ `m.__file__` **必须落在 `/tmp/j_grade_glm` 里**（承重不变量，⛔ 不是 `.pth` 哈希）。
- ⛔ **一律 `-n 6`**（同机另有一路在飞）。**判跑完看汇总行**，⛔ 不看退出码文件、⛔ 不用 `nohup`。
- **基线 `3907`**；逐位闭合**你自己数**，差一条都要说明差在哪。
- ⛔ `pip install -e .` 或任何写 `site-packages` 的命令。
- ⛔ `git add -A`；逐路径 add，commit 前看 **`git diff --cached --numstat`**（⛔ `git show` 不接 `--cached`）。
- ⚠️ `.gitignore:258` 有 `*.txt`，新增 txt 证据必须 `git add -f`。
- ⭐⭐⭐ **必须分段提交**（每完成一个能独立成立的小步就 commit）——
  GLM 席位 09-02 撞 5 小时上限时留下过 **1035 行**未提交半成品，而日志只字不提。

---

## 六 交件

`AI_agent/logs/reviews/execution/2026-09-06e_J_grade_wiring_execution.md`，必须含：

- **§三 那次测量的逐项对照表**（立面判分要什么 × gt 有没有 × 在哪个字段）
- **接线点清单**：`flow` 的识图段现在怎么选判分器、分类器复用在哪一行
- **跨两层立面必须判出分**那条锁在哪一行 + 当场证明能变红
- **J-2 两个分辨率各自的具名常量与声明点**，以及「换一个声明分辨率判分跟着变」的实测
- **完整全量汇总行 + 逐位闭合**（自己数）
- **最薄弱一处**（⛔ 不许写「无」）

⛔ 不许留占位符。

---

## 七 ⭐ 停下上报（分层）

- **A 层（停）**：① **§三 量下来答案侧撑不起立面判分** ② 本单承重前提是错的
  ③ 要动 §四 禁令（尤其是要改 gt） ④ 会改到已落库产物的哈希或已签字基线。
- **B 层（记一条继续）**：行号 / 措辞 / 外围数值不一致。

> 本项目至今 **70/70** 次「停下上报」全部是**派工方的题出错** ⇒ 该停就停，⛔ 不要自行绕路。

---

## 八 ⛔ 本单**不做**（登记，另开单）

- **J-5 语义升格为正式答案字段并计分**（配对 / 门窗身份 / 墨族角色 / 「我认不出来」这个声明本身）
  —— 需要先冻结字段与语义，是设计活，⛔ 不塞进本单。
- **F-98 判分对浮点末位敏感** —— 观察项。
