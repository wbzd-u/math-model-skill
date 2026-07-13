# 方法选择与模型设计模块

## 1. 模块定位

承接 `PROJECT_ROOT/analysis/` 的结构化题目分析包，把“已定义的问题”转化为有证据、可比较、可证伪、可实现的建模路线、数学规格、验证计划和 solver 实施契约。

本模块包含两个连续阶段：

- **方法选择**回答“哪些路线适合本题，当前证据支持到什么程度，为什么选择这一方案”。
- **模型设计**回答“选定路线如何具体数学化，并怎样交给 solver 执行”。

两者放在同一模块内，防止候选方法与最终目标、约束和变量定义失去一致性。

## 2. 处理目标

- 从题目分析中的要求、语义契约、数据状态和结构难点生成候选方法链。
- 检索并核验结构相似的历史案例、方法卡、验证卡和文献证据。
- 先执行硬条件淘汰，再统一比较可行候选。
- 确定主方案；只在有实际比较价值时增加基线或备选。
- 将选定路线写成变量、关系、目标、约束、参数来源和组件依赖。
- 在运行实验前定义验证、敏感性、鲁棒性和失败回退条件。
- 生成 solver 可以执行但不能静默改写的实施契约。

## 3. 输入

只读读取 `PROJECT_ROOT/analysis/` 的十个结构化文件：

```text
problem-profile.yaml
requirement-trace.yaml
data-inventory.yaml
entity-variable-map.yaml
subproblems.yaml
data-task-matrix.yaml
dependency-graph.yaml
ambiguity-register.yaml
assumption-register.yaml
analysis-audit.yaml
```

`problem-analysis-report.md` 仅用于人工阅读，不作为机器事实来源。模块初始化时校验上游 Schema，并记录十个文件的 SHA-256。

## 4. 核心职责

### 方法选择

- 将每个子问题压缩为“能力角色 + 结构 + 数据 + 输出 + 验证”的选择范围。
- 使用结构标签而非题目背景词检索知识库。
- 生成少量真正不同的候选能力链，不用算法名称代替输入到输出的逻辑。
- 比较要求覆盖、结构匹配、数据与可识别性、假设负担、解释性、验证强度、实现成本、竞赛适配和失败风险。
- 选择最小充分的主方案；基线和备选是有用的比较工具，不是必填数量指标。

### 模型设计

- 统一数学符号，区分上游变量和本阶段派生量。
- 登记新假设的依据、影响、验证方法和状态。
- 定义模型组件、目标、硬约束、状态/事件关系、参数来源和组件输入输出。
- 建立输入输出相容的模型链；迭代或反馈环必须说明收敛、终止或失败条件。
- 设计验证计划并形成 solver 实施契约。

## 5. 执行流程

1. 运行初始化器，校验上游并生成准入记录。
2. 确认选定子问题、必交输出、成功判定、数据状态和结构难点。
3. 检索历史案例、方法卡、验证卡和文献；空知识库明确记为 `none-available`。
4. 从一个最小可行候选开始；只有存在实质不同的结构、假设或风险处理时才增加候选。
5. 先按硬条件淘汰不可行路线，再按统一软维度比较。
6. 确定当前主方案、必要的比较路线和残余风险。
7. 写出数学模型规格和模型链。
8. 为要求、组件、主要结论和结构难点设计可执行验证。
9. 生成实施契约并写入最终输入快照哈希。
10. 日常用 `explore` 校验继续迭代；准备交给 solver 时使用 `handoff` 校验。

六轮的具体提示问题、输出和失败信号位于 `static/selection-methods/`，运行入口以 `SKILL.md` 和 `manifest.yaml` 为准。

## 6. 输出文件

存在最小问题定义时，无论当前是正式还是探索状态，所有输出写入 `PROJECT_ROOT/modeling/`：

```text
intake-check.yaml
candidate-methods.yaml
model-decision.yaml
model-specification.yaml
validation-plan.yaml
implementation-contract.yaml
modeling-selection-audit.yaml
modeling-selection-report.md
```

只有完全缺少可定位要求或子问题时才只生成：

```text
intake-check.yaml
modeling-selection-report.md
```

历史案例、方法比较和符号说明分别进入候选证据、决策、模型规格和最终报告，不另建重复文件。

## 7. 探索与交接

- `EXPLORATORY`：允许提出竞争性解释、暂定假设、单一候选和诊断性验证；结论必须保留条件，不能声称 solver 已就绪。
- `explore` 校验：引用、ID、路径、Schema 基础结构和上游哈希必须可靠；覆盖不足、缺少比较路线、审计未完成等只产生警告。
- `handoff` 校验：选定子问题必须属于 `handoff_allowed_subproblem_ids`，主方案、规格、关键验证和实施契约必须形成科学闭环。
- 上游 `DRAFT` 或 `BLOCKED` 不禁止思考；它们禁止把探索方案升级为正式交接，直到问题定义和证据足够稳定。
- 候选数量、基线、备选、完整比较矩阵和审计满分都不是 handoff 的必要条件。
- 上游文件哈希变化后必须重新初始化，防止继续解决已经改变的问题。

## 8. 失败与回退

- 题意、变量角色、成功判定、硬约束或数据含义错误：返回 `problem-analysis`。
- 候选前提不成立或被其他候选支配：留在本模块替换、降级或淘汰，并记录证据。
- 模型组件不可实现、参数不可识别、约束冲突或诊断结果否定结构假说：solver 生成 `solver/modeling-feedback.yaml`，携带错误、输入、参数和复现信息返回本模块。
- 验证失败：按 `failure_action` 返回模型设计、题目分析或 solver 诊断，不静默修改模型。
- 重复初始化必须显式使用 `--force`，防止新旧交接文件混合。

## 9. 不负责的事项

- 不修改 `analysis/` 中的题目事实、变量角色或门禁结论。
- 不通过临时假设绕过定义性歧义或缺失关键数据。
- 不选择编程语言、库、数据结构或具体数值实现细节。
- 不编写求解代码，不运行数值实验，不生成结果表或图。
- 不把历史论文的结论、参数或性能直接复制为本题结论。
- 不撰写论文，不声称尚未运行的模型已经有效或更优。

## 10. 需要加载的 references

知识索引位于 `references/index.yaml`，后续可登记：

- `case_cards`：历年赛题和优秀论文的结构化案例卡。
- `method_cards`：方法的适用条件、输入输出、假设、复杂度、风险和验证方式。
- `validation_cards`：误差、约束、敏感性、鲁棒性、边界和对抗性验证卡。

当前索引允许为空。没有真实命中时记录 `knowledge_status: none-available`，继续基于题目结构生成候选，但不得伪造证据。竞赛差异按需加载 `static/fragments/competition/` 中的一个片段。

## 11. 与前后模块的交接协议

```text
analysis/problem-profile.yaml + subproblems.yaml + 其余结构化分析文件
                              ↓
                    modeling-selection
                              ↓
modeling/model-decision.yaml + model-specification.yaml
+ validation-plan.yaml + implementation-contract.yaml
                              ↓
                    numerical-solving（尚未开放）
```

本模块不复制上游文件。solver 以 `implementation-contract.yaml` 为执行入口，同时读取契约引用的模型规格和验证计划；任何目标、硬约束、核心假设、评价口径或输出要求的改变都必须退回本模块审批。
