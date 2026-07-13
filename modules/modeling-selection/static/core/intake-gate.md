# 上游准入门禁

- `PASS`：可以探索，并可在 handoff 条件满足后正式交接。
- `PASS_WITH_OPEN_ITEMS`：所有已定义子问题都可探索；只有未受开放项影响的范围可以 handoff。
- `DRAFT` 或 `BLOCKED`：只要要求与子问题可定位，仍生成 `EXPLORATORY` 建模骨架，用分支解释、暂定假设和诊断性验证推进；handoff 范围为空。
- 只有要求或子问题本身缺失，无法形成“输入/假设 → 关系 → 判定 → 输出”的最小闭环时，才停止生成下游骨架。

`allowed_subproblem_ids` 表示可探索范围，`handoff_allowed_subproblem_ids` 表示可正式求解范围。准入时记录上游十个结构化文件的 SHA-256；任何文件改变后必须重新准入。

`problem-analysis-report.md` 只用于阅读，不作为结构化事实来源。
