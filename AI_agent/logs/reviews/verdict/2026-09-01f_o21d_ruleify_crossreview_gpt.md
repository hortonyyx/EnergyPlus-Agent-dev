# ②-1d exclusion 锁「规则化」跨家族复核裁决（GPT）

## 1. 裁决

**A 层停下上报；未进入复核。阻断 1 / 不阻断 0。**

阻断 1：开工前 site-packages 哨兵不符合本单及用户指令写死的环境前提。期望值为
`58f547fa9433af6eca0e8f362652b78916b13a21fbeab4ef06f1e07e46744e43`，实测为
`e7171c929a4f12339023618e6d34aa4726c60508ebba4a85e2dcd47162790619`。
按“看着不对就停下上报”及开工自检纪律，本席没有运行 pytest、没有做变异、没有改动独立 worktree。

## 2. 攻击面 1

**未执行。** 不是把“无读数”冒充完成，而是开工前哨兵已经失败，必须先停报；在环境前提修复并重新派工前，不能合法取得“25 腔底料喂进 11 条锁”的 pytest 读数。

## 3. 攻击面 2 / 3 / 4

均未执行，原因同上。未产生可供裁决的测试读数。

## 4. 三格读数表

| 格 | 状态 | 读数 |
|---|---|---|
| ① `5ac0885^` 旧锁 | 未执行 | 开工前哨兵失败 |
| ② `5ac0885` 新锁 | 未执行 | 开工前哨兵失败 |
| ③ 同形输入 / 25 腔底料 | 未执行 | 开工前哨兵失败 |

## 5. 复现命令与原始输出

```text
$ cd /tmp/o21d_review_gpt
$ git log --oneline -1
8028bab 09.01w_TwoCrossreviewAsks_TheDeletedFiftyLinesHeldTheOppositeSemantics

$ git status --porcelain

$ python -c "import src.agent.judge.answer_compiler as m; print(m.__file__)"
/tmp/o21d_review_gpt/src/agent/judge/answer_compiler.py

$ sha256sum /opt/venv/lib/python3.12/site-packages/_editable_impl_energyplus_agent.pth
e7171c929a4f12339023618e6d34aa4726c60508ebba4a85e2dcd47162790619  /opt/venv/lib/python3.12/site-packages/_editable_impl_energyplus_agent.pth
```

开工前哨兵读数：`e7171c929a4f12339023618e6d34aa4726c60508ebba4a85e2dcd47162790619`（失败）。

交件前原始输出：

```text
$ sha256sum /opt/venv/lib/python3.12/site-packages/_editable_impl_energyplus_agent.pth
e7171c929a4f12339023618e6d34aa4726c60508ebba4a85e2dcd47162790619  /opt/venv/lib/python3.12/site-packages/_editable_impl_energyplus_agent.pth

$ git status --porcelain
```

交件前哨兵读数仍为 `e7171c929a4f12339023618e6d34aa4726c60508ebba4a85e2dcd47162790619`（失败）；独立 worktree 状态为空。

## 6. 本单写错之处

1. 本单环境读数及并发条款声称哨兵应为 `58f5...4e43`，但本席按写死路径开工实测为 `e717...0619`；环境前提与现场不一致。
2. 用户要求“内容按复核单 §六的七项”，但复核单 §六实际仅列出 6 项。这是条数错误；本裁决没有虚构不存在的第七项。

## 7. 执行范围声明

本席在独立 worktree 中只做了开工自检和只读复核单；未运行测试、未变异文件、未执行任何 `pip install` 或 site-packages 写操作。唯一写入为用户明确允许的本裁决文件。
