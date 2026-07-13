# 路线审计：只在复杂度需要被证明时执行

路线审计不是新阶段，也不要求每个问题拥有基线、备选或回退。它只要求对正式主路线作一个判断：与更简单、透明的可行路线相比，这个升级是否引入了需要通过本题实验验证的能力或工程风险？

在 `model-decision.yaml.route_audit` 中选择一种状态：

- `not-needed`：写明理由。适用于没有实质性复杂升级、没有合理简单对照，或额外路线不会改变科学决策的情况；`items` 必须为空。
- `audited`：为每条需要审计的主候选写一项。不要填写泛泛的“更准确”“更创新”。

每个审计项构成一个可执行闭环：

```text
capability_gap -> added_capability -> deciding_test_id
    -> first_execution_stage_id -> flip_condition -> feedback_trigger
```

字段全部引用已有交接物：

- `main_candidate_id` 是已选主候选；`simpler_candidate_id` 可为空，不能为了填写而制造基线。
- `deciding_test_id` 引用 `validation-plan.yaml` 中真正检验升级价值的 `val-*`，而不是装饰性测试。
- `first_execution_stage_id` 引用 `implementation-contract.yaml` 的 `run-*`，让 solver 在最早可行阶段获得诊断证据。
- `feedback_trigger` 必须是实施契约既有的反馈触发器。满足 `flip_condition` 时，solver 通过这一触发器写入 `solver/modeling-feedback.yaml`，不能自行换模型。

仅当主路线在数据、计算、识别、假设或解释上比透明路线增加了实质负担，或其成败会影响方法选择时使用 `audited`。不使用加权总分、固定分差或强制候选数量。
