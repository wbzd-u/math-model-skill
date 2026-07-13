# 数值求解工作流

## 状态流

```text
modeling contract
  -> intake and bindings
  -> reuse decision and run plan
  -> minimal implementation checks
  -> real experiments
  -> validation and result manifest
  -> COMPLETE | COMPLETE_WITH_LIMITATIONS | NEEDS_REVISION | BLOCKED
```

`probe` 和 `solve` 使用相同的追溯结构，但完成含义不同：probe 验证一个明确假说；solve 完成契约范围。

## 每轮要求

1. 准入：验证上游文件、快照、范围和模式，列出未解析绑定。
2. 计划：先写输入/输出绑定、运行命令、数值控制和验证映射，再实现。
3. 复用：对非平凡数值内核记录复用或自研决策，不机械凑候选。
4. 实现：先打通一个最小垂直链，用性质或已知小例排除翻译错误。
5. 运行：一个配置对应一个 `exp-*`，记录命令、输入哈希、seed、退出状态、日志和输出。
6. 验证：执行契约测试与模型族必要诊断，把失败动作映射到修复、限制或上游反馈。
7. 交付：结果、图表和主张都必须回链到运行或验证证据。

## 失败分类

- `implementation_bug`：本模块修复并重跑。
- `environment_dependency`：调整环境、替代等价实现或记录阻断。
- `numerical_issue`：诊断尺度、容差、条件数、收敛或求解器状态；不得先改模型语义。
- `data_issue`：字段、单位、缺失或数据质量影响语义时返回题目分析。
- `contract_model_issue`：不可行、冲突、不可识别或诊断否定模型时返回方法选择与建模。

失败实验不删除。新运行使用新 `exp-*`，保留前一次失败证据。
