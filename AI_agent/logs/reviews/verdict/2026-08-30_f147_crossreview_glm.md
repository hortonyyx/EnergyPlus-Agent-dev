# 跨家族裁决 · F-147（吸附阈值签字落地 + 新增角度门）· GLM

- **日期**：2026-08-30 · **审方**：GLM 家族 · **请求书** → [`../request/2026-08-30_f147_crossreview_glm.md`](../request/2026-08-30_f147_crossreview_glm.md)
- **送审对象** = `git diff 37607dd..cfb8ba7`（施工自述仅当索引用，全部读数均为本席独立重跑）
- **裁决**：**APPROVE-WITH-FINDINGS · 阻断 0 · 不阻断 4**

---

## 〇、环境与方法（先亮底）

- 全部实验跑在 `git archive cfb8ba7` 的 **/tmp 干净副本**（`/tmp/f147_rev`，与主树 `src/` 逐字节同——`diff` 验证过；`cfb8ba7..HEAD` 仅动 4 份 md）；基线对照树 = `git archive 37607dd`（`/tmp/f147_base`）。**未碰主树一个字节、未跑任何写 site-packages 的命令。**
- ⭐⭐⭐ **A1 的负样本不是重造的，就是我自己 08-29 造的那份原件**：`/tmp/negsample_diagonal.dxf` + `/tmp/negsample_request.json` 仍在盘上（mtime Aug 29 20:35），`source_dxf_sha256` 双哈希核对一致；三条合成线坐标实测 = 194E/194F 各 800 mm 歪 5.5 mm（**0.3939°**）、y 名义间距 120 mm；1950 = 60 mm 歪 5 mm（**4.7636°**）；1951 = 45°。
- 受影响子集（19 文件）在**主树** `-n auto` 前台跑：**448 passed / 1 xfailed / 0 failed**（187.5 s，exit 0）——与执行档自报逐位同数。

---

## 一、A1 · ⭐⭐⭐ 端到端答案：**在 1.0° 下 walls 确实 55 → 56。签字材料没有把风险说大**

四个跑（同一份负样本、同一 build_as_measured 入口、只换树/阈值）：

| 跑 | 代码树 / 阈值 | face_lines | **walls** | axis_snapped | s1_discarded |
|---|---|---|---|---|---|
| ① 对照·改前 | `37607dd`（6 mm，无角度门）| 224→**227** | 55→**56** | +194E/194F/**1950** | 1951 |
| ② **送审对象** | `cfb8ba7`（10 mm + **1.0°**）| 224→**226** | 55→**56** | +194E/194F | **1950**/1951 |
| ③ 干净基准 | `cfb8ba7`，未加线 | 224 | 55 | 13AD/13AE | [] |
| ④ 反事实 | `cfb8ba7`，**注入 0.25°** | 224 | **55** | 13AD/13AE | 194E/194F/1950/1951 |

- ②里那第 56 堵墙 = `w_x_256690_257890_316690_324690`（lo=`194F`，hi=`194E`），厚度直方图 1200 (=120 mm): **28→29**——与我 08-29 在 ②-1b-S 复核时造出的**同一堵、同一坐标**。两面各自的吸附诊断带 `minor_leg_mm=5.5, angle_deg=0.39390227821820434`。
- 跑①逐位复现我当时的读数（227/56/1950 被吸）⇒ 复现通道可信，②的 56 不是环境伪影。
- ⇒ **「引述」升级为「实测」**：用户已知情接受的代价真实存在，签字材料与代码 docstring 的表述（`tarch_normalize.py:150-166`）**不需要更正**。
- ⭐ 附带两个实测（签字材料没细说的两面）：
  - **F-147 相对改前的真实增益**：4.76° 短线（1950）在改前被吸进 face_lines，现在被角度门拦下（`refused_by=['angle_deg']`，`minor_leg_mm=5.0 ≤ 10` 毫米门放行、`angle_deg=4.7636 > 1.0` 角度门拒）——face_lines 227→226 就是它。
  - **docstring「0.25° 会拒」属实**（跑④）：194E/194F `refused_by=['angle_deg']`，walls 回到 55。可选区间 `(0.091°, 0.394°)` 的两个端点行为都与单内描述吻合。

**复现命令**（任何席位可重放）：
```bash
git archive cfb8ba7 | tar -x -C /tmp/f147_rev && cd /tmp/f147_rev
python3 -c "
from pathlib import Path
from src.agent.judge.as_measured import build_as_measured
doc = build_as_measured(Path('/tmp/negsample_diagonal.dxf'),
                        Path('/tmp/negsample_request.json'), view_ids=['plan-F1'])
v = next(x for x in doc.views if x.view_id == 'plan-F1')
print(len(v.face_lines), len(v.walls),
      [r.id for r in v.converter_readouts.axis_snapped_lines],
      v.converter_readouts.s1_nonorthogonal_discarded_handles)"
# → 226 56 ['13AD','13AE','194E','194F'] ['1950','1951']
```
（0.25° 反事实 = 运行时包一层 `tn._tols_from` 强制 `axis_snap_max_angle_deg=0.25`，本席脚本 `/tmp/f147_rev/e_a1_inject025.py`。）

---

## 二、A2 · ①b 自供夹具量到的是真东西：**R1 的独立锁成立，不是 ⑤ 的重复**

在 /tmp 副本上做两个方向的单因子变异，各跑全文件 `tests/test_tarch_converter_p1_geometry.py`（34 条）：

| 变异 | 结果 |
|---|---|
| 毫米 10→**6**（角度 1.0 不动）| **恰好 1 红 = ①b**（`..._1b_the_signed_10mm_deviation_value_has_teeth`），33 passed |
| 角度 1.0→**5.0**（毫米 10 不动）| **恰好 1 红 = ②**（`..._2_short_slant...`），**①b 绿** |
| 恢复 cfb8ba7 原值 | 34 passed |

⇒ ①b 的夹具（2000 mm 歪 8 mm = **0.229°**）在两个毫米档下角度门都放行（0.229° ≪ 1.0°），判决只由毫米值决定；角度门怎么放宽它都不红。**它声称覆盖的那一维（毫米门 6→10 这 4 mm 窗）真的被量到了，且与角度门解耦。** 施工方自报的最薄弱处（变异矩阵 M2 行七格全绿 ⇒ 全语料 6–10 mm 带零存货 ⇒ 自加夹具供货）处置正确。

补充：6 mm 变异下跑**完整受影响子集**（19 文件）得 3 红——除 ①b 外两条均非毫米观测器：
- `test_tarch_converter_reproducibility.py::test_f_d_d_...` 在 **10 mm 干净副本上同样红**（`git show` 在无 `.git` 的 /tmp 副本 `CalledProcessError`）⇒ 环境假红，与本单无关（NF-D）；
- `test_gt_facts_staging_sm25.py::test_1_..._bit_for_bit` = 指纹链锁：改任何闭包内代码都翻 `converter_implementation_fingerprint` ⇒ 落盘件≠重建。它红证明的是「改常量必被逐位锁看见」，不是 R1 缺锁。

---

## 三、A3 · `refused_by` 三问

1. **「为空却走了拒绝分支」——结构性不存在，且三态全实测**。`tarch_normalize.py:568` `refused_by = ([] if mm_gate_ok else ["deviation_mm"]) + ([] if angle_gate_ok else ["angle_deg"])`，而 else 分支的进入条件即「至少一门 False」⇒ 至少一名。端到端三输入实测：仅毫米拒（注入 `axis_snap_max_m=0.003`，13AD 5.81 mm>3 且 0.091°<1°）⇒ `['deviation_mm']`；仅角度拒（1950）⇒ `['angle_deg']`；45°（1951）⇒ `['deviation_mm','angle_deg']`。且全 `src/` 该码**只有 `tarch_normalize.py:570` 一个产生点**（`as_measured.py:1157` 是消费者），不存在第二个不带 `refused_by` 的同名码把原因重新压回空白。
2. **吸附侧与拒绝侧同一套算法——是同一次计算**。全 `src/agent/judge/` 唯一的 `atan2` 在 `tarch_normalize.py:558`，`angle_deg` 在同一循环体里算一次、吸附分支（`:599` 的 context）与拒绝分支（`:573`）**共用同一变量**。将来不存在两处漂移的面。
3. ⭐⭐ **消费者那半句要打折扣 ⇒ NF-1（本审头号 finding，见下）**：`angle_deg` 只写进了 converter 诊断（并 verbatim 转运进 `as_measured` 的 `converter_readouts.diagnostics`，`as_measured.py:1073`）；**人签 `revisions` 时逐条过目的那个结构化清单 `axis_snapped_lines` 没有它**——`AsMeasuredAxisSnapV1`（`as_measured.py:324`）字段止于 `minor_leg_units`（`:354`），transport（`:1054`）也只取 `minor_leg_mm`。

---

## 四、A4 · docstring 翻指纹：施工方更正**成立**（独立复核）；NF-1 排期不必为指纹让路

① 三段实测（/tmp 副本，恢复后与基线逐位同）：

| 变异 | `converter_sha256()` | 翻 |
|---|---|---|
| 基线（cfb8ba7）| `d5825959b9f09c59…71cd81bb` | — |
| 加一行 `#` 注释 | `d5825959b9f09c59…71cd81bb` | **否** |
| 模块 docstring 改一个词 | `6e1d81e2482ee9cf…5faeac6` | **是** |

`_behavioural_source_digest` 自己的 docstring 早已写明（`NOT immune to docstring/string-literal edits -- those ARE Constant nodes`）——派工单 §四② 把「注释/docstring」并列成都不翻确系**题错**，施工方更正被本席独立复现证实。

② **下游后果（排期方向，未动代码）**：`CONVERTER_CLOSURE_FILES` 13 文件清单里**没有 `gt_facts_staging.py`**（闭包 = tarch 五件 + gt_manifest/gt_schema/gt_extraction + correction 七件）。⇒ **NF-1（出口全检，落点 `gt_facts_staging.py`/新文件）落地不会翻 `converter_sha256`，gt 侧不会因此再 drift 一次**——它不必为指纹顾虑推迟，按 ②-1c 自身节奏排即可。真正要守的是一条**攒批原则**：凡会进闭包的文件（含只改 docstring 措辞，见 NF-1 下面的更正项）攒到与 ②-1c / 下次重签**同一批**动完、`gt_staging/` 重生成一次，避免「翻指纹→重生成→再翻」多轮抖动。staging 候选重生成是机械动作、代价低，多翻的真正代价是每轮让 `bit_for_bit` 类锁红一次。

---

## 五、A5 · 禁令核对（独立验）

`git diff 37607dd..cfb8ba7 --name-only` = 9 文件：① **答案根 `case_tests/test_baseline/gt/` 零改动**（diff 该路径输出为空）；② **`src/agent/judge/gt_facts_staging.py` 零改动**（不在 9 文件中）✅。另核：
- `gt_staging/` 三份候选的全键递归 diff：`as_measured.json` 3 片（1 指纹 + 2×`angle_deg`）；`as_signed.json` 6 片（指纹 + derivation 两个反向引用 + views 内同 2 片 `angle_deg`）；`revisions.json` **恰 1 片** = `as_measured_content_sha256` 反向引用，**五条 revision 的 finding/candidate_action/target 逐字未动、verdict 全 `unsigned`、`signed_by/signed_at` 全 `null`**——「重新生成 ≠ 重签」由产物直接证明。
- 顺手复核主控免检三件：几何逐字节不变（两树对照 224/55 同 + staging 全键 diff 几何 0 片）✅；`_KNOWN_SIGNED_RISK` 写法（`tests/test_tarch_converter_p1_geometry.py:744-745`）✅；monkeypatch 实调用 0 次（文件内唯一一处字样是 `:587` 的禁令注释）✅。

---

## 六、findings

### 阻断（0 条）

无。

### 不阻断（4 条）

**NF-1 ·【⭐⭐ 签字补偿控制的「角度维」对人不可见——两份单子中间的缝】**
人签 `revisions` 时逐条过目的清单 `axis_snapped_lines`（`as_measured.py:324` `AsMeasuredAxisSnapV1`）只有 `minor_leg_units`、**没有 `angle_deg`**；角度读数只活在同文档的 `diagnostics` 里。实害形状（用本审 A1 的实测数说话）：真手抖 13AD = 58 单位（0.091°，无害）与缓斜墙 194E = 55 单位（0.39°，本审实测造出第 56 堵虚构墙）——**在清单上两个毫米数几乎一样、风险差一个量级，签字人从清单本身无法分辨**，得自己去 diagnostics 按 handle 翻或手算 atan2。而 `tarch_normalize.py:162-165` 的表述（"a human reads the itemised snap list (axis_snapped_lines) line by line … Nothing here is silent -- every admission emits tarch_wall_axis_snapped carrying both readings"）把「清单」与「两个读数」拼接在一段里，读起来像过目时能看到角度——**补偿控制被表述得比实际强**。派工单 R3 只要求「context 增加角度读数」（字面已满足），主控免检项也只核了测试写法——这条缝两份单子都没照到，正是请求书 A3.3 点名要查的。
**修法**（两选一，建议都做，随 ②-1c 同批、按 A4 攒批原则一次重生成 staging）：`AsMeasuredAxisSnapV1` 加 `angle_millideg`（或等价）字段 + `_axis_snap_records`（`as_measured.py:1040-1054`）transport 一行；同时把 `tarch_normalize.py:162-165` 那句改成如实表述（角度读数在 diagnostics、清单只带毫米）。**判不阻断的理由**：数据未丢（verbatim 在同一份文档内）、几何零影响、修复面明确且小。

**NF-2 ·【A4 排期结论】闭包外文件不翻指纹；闭包内（含 docstring）攒批**
见 §四②。NF-1 的修复若动 `as_measured.py`——查实它**不在** 13 文件闭包内（闭包只含 `tarch_normalize/tarch_converter_schema/affine_space/gt_manifest/gt_schema/gt_extraction` + correction 七件）⇒ **NF-1 补字段同样不翻 `converter_sha256`**，只会翻 staging 的 `as_measured_content_sha256`（本来就要重生成）。⇒ NF-1 与 NF-2 可安全合并成 ②-1c 的一小步，无需单独排期窗口。

**NF-3 ·【流程】施工席位在他人审阅期间动了主树（施工方自己如实上报）**
执行档 §五.3 自报：②-1b-T-R 复核在途时本单动了 `src/`，让复核席撞上一条红（哈希 `5591a8c3… ≠ 74b22e66…`，即本审 §五核过的那对 staging 反向引用）。实害为零——复核席自己发现、正确归因、改用 `git archive` 干净副本重跑（本审沿用同一纪律）。同型已是第三犯（memory：席位跑全量时连文档提交都不做）。**支持施工方建议**：派工单模板加一行「同机有席位在飞时，动 `src/` 前先与派工方对一次表」。

**NF-4 ·【环境备注】`git archive` 副本跑 `test_tarch_converter_reproducibility.py` 会假红一条**
`test_f_d_d_known_pre_fix_values_are_pinned_not_recomputed` 内嵌 `git show a40d56d:…`（`:249-252`），在无 `.git` 的 /tmp 副本必 `CalledProcessError`（本席实测：10 mm 干净副本上照红；主树同文件 448 绿含它）。非本单缺陷；记下供未来席位在 /tmp 副本跑子集时预判，别把这条读成回归。

---

## 七、范围外对账（请求书 §三）

- ②-1b-T-R 的 5 条 NF / AnswerCompiler / 出模两种形式 / edge boundary_condition / 出口全检 / correction 侧 / 重签答案 / promote_gt_v3 / F-128 / F-132 / `_snap_short_leg_to_axis` 做法——均未在本单 diff 中出现，对账一致。
- ⚠️ 缝里两份单子都没覆盖的一块 = **NF-1**（清单 schema vs 诊断 context 两个面的错位），已点名如上。除此之外本席未再发现。

---

## 八、裁决理由

本单的四个承重面全部独立复现成立：**两道门 AND 落了地且各自有独立牙**（A2 双向单因子变异）、**几何逐字节不变**（两树对照 + staging 全键 diff）、**签字风险 55→56 从引述变实测**（A1，且改前 4.76° 被吸 / 改后被拦的增益同样实测）、**指纹翻转走的是 §五 合法路径且未碰答案根**（A5）。施工方两处主动申报（①b 无锁自补、docstring 翻指纹更正派工单）都被证实为真——自报最薄弱处恰好是本审能补上的那半步（A1 端到端），这正是「谁写谁不批」要的分工。唯一实质缺口 NF-1 是表述与 schema 的半步滞后，不动物理几何，随 ②-1c 一批即可。⇒ **APPROVE-WITH-FINDINGS**。
