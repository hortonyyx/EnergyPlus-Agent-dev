# 读图器写出的**未声明产物**（orchestrator 于合并前移出，⛔ 未删除）

`_validated_1f_view.json` 由读图器自行创建（它在回执里称「kept in sync」），
**不在 view manifest 声明的产物集合里** ⇒ `merge_isolated_output` 按规矩拒绝合并：

```
ValueError: merge refused: unexpected per-image view files not declared in the
view manifest: ['_validated_1f_view']
```

**门的行为是正确的**（清单外产物 = identity error，任何 run_profile 下都 BLOCK）。
orchestrator 的处置 = **移出 staging 的 `out/` 并原样归档到此处**，⛔ 不删除、⛔ 不改内容，
然后重新合并。移出的是**副本**，不是交付件；交付件 `1f_view.json` 未被触碰。

⚠️ 登记一条观察：读图器会自发产出「自校验副本」这类清单外文件。
本次由门拦住；若哪天该门放松，这类副本可能被误当交付件消费。
