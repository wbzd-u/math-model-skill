# 题目分析模块

## 1. 模块定位

将数学建模题目、附件和竞赛要求转化为结构化的问题定义，为建模与方法选择阶段提供可靠输入。

本模块只负责理解题目和数据，不负责决定最终数学模型，也不负责编写求解代码。

## 2. 处理目标

- 识别比赛类型、题目要求和评价目标。
- 读取 PDF、Excel、CSV、图片或文本附件。
- 审计字段、单位、缺失值、异常值、数据规模和时间范围。
- 将总题目拆分为可独立验证的子问题。
- 建立子问题之间的输入、输出和依赖关系。
- 区分题目明确条件、合理假设和待验证事实。
- 形成“给定/决策→事件或状态→成功判定→评价聚合→输出”的语义契约。
- 识别有证据的动态、耦合、信息时点、聚合和定义难点。

## 3. 输入

- 题目正文和官方说明。
- 题目附件及其文件清单。
- 比赛名称、年份、题号和格式要求（如果已知）。
- 用户希望回答的范围，例如只分析某一问或分析整题。

输入附件默认只读。需要修改或转换时，先在项目目录生成副本，不修改原始文件。

## 4. 核心职责

### 4.1 竞赛和题目识别

- 判断 CUMCM、MCM/ICM 或其他竞赛模式。
- 读取对应的当届官方规则；不使用往届经验替代官方要求。
- 识别题目背景、目标、约束、评价指标和交付格式。

### 4.2 数据与附件审计

- 列出每个附件的格式、大小、字段和单位。
- 检查缺失值、重复记录、异常值、编码问题和数据泄漏风险。
- 标记无法从附件确认的字段含义和参数来源。

### 4.3 子问题拆解

- 将自然语言任务改写为输入、决策变量、目标和输出。
- 区分预测、评价、分类、优化、仿真、网络和统计任务。
- 记录子问题之间的顺序依赖、共享数据和可并行部分。

### 4.4 假设与边界整理

- 将假设标记为题目给定、数据支持、领域常识或待验证。
- 记录每个假设失效时可能影响的结论。
- 不为了套用某个模型而添加未经依据的假设。

## 5. 执行流程

1. 建立项目输入清单并锁定原始附件。
2. 读取题目正文和官方要求。
3. 按文件类型审计附件和数据。
4. 建立题目画像和术语表。
5. 拆分子问题，形成语义契约，并按题型加载结构检查卡。
6. 绘制题问级依赖关系，登记题内时间、空间、资源和全局—局部耦合。
7. 列出显式条件、竞争性解释、未知信息和待确认问题。
8. 检查输出是否足以进入建模与方法选择阶段。

只有当题目画像、数据清单和子问题定义完整时，才允许进入下一阶段。

模块使用 `manifest.yaml` 识别竞赛和输入模式，只加载匹配的 `static/fragments/`，随后按 `analysis_sequence` 依次执行七轮分析方法。初始化和校验命令：

```text
python scripts/init_problem_analysis.py --project-root <PROJECT_ROOT> --title <TITLE> --competition <TYPE> --source <PATH>
python scripts/validate_problem_analysis.py --project-root <PROJECT_ROOT> --strict
```

## 6. 输出文件

```text
analysis/problem-profile.yaml
analysis/requirement-trace.yaml
analysis/data-inventory.yaml
analysis/entity-variable-map.yaml
analysis/subproblems.yaml
analysis/data-task-matrix.yaml
analysis/dependency-graph.yaml
analysis/ambiguity-register.yaml
analysis/assumption-register.yaml
analysis/analysis-audit.yaml
analysis/problem-analysis-report.md
```

`problem-profile.yaml` 至少包含比赛信息、题目目标、评价指标、数据范围和输出要求。所有 YAML 文件保持为 JSON-compatible YAML，并按 `schemas/` 中的契约填写。

## 7. 阶段门禁

进入建模与方法选择前，必须确认：

- 所有子问题都有明确输入和预期输出。
- 每个实质子问题都有成功判定、评价聚合、验收测试及结构难点或无难点依据。
- 附件字段、单位和时间范围已经记录。
- 未知字段和数据质量风险已经标记。
- 显式条件与假设没有混写。
- 题目要求没有被模型选择提前改写。
- 未解决歧义没有改变目标、硬约束、成功判定、核心实体、聚合口径或输出接口。

## 8. 失败与回退

- 题意不清：列出具体歧义和需要用户确认的选项。
- 附件无法读取：保留错误信息，说明缺少的工具或文件。
- 字段含义不确定：标记为待确认，不擅自推断。
- 数据不足以定义子问题：回退用户补充输入，不进入模型选择。
- 定义性歧义未裁决：标记为 `BLOCKED`，不以 `PASS_WITH_OPEN_ITEMS` 放行。

## 9. 不负责的事项

- 不在本阶段选择最终模型。
- 不根据关键词直接套用历年论文方法。
- 不编写正式求解代码。
- 不提前生成论文结论。
- 不掩盖数据质量问题以推进流程。

## 10. 需要加载的 references

按任务需要加载：

- `static/core/` 中的契约、工作流和阶段门禁。
- `static/analysis-methods/` 中按顺序执行的七轮分析提示卡。
- `static/core/structural-pressure-test.md` 与按 `task_tags` 条件加载的结构检查卡。
- 与当前竞赛匹配的 `static/fragments/competition/` 片段。
- 与当前输入匹配的 `static/fragments/input-mode/` 片段。
- 后续由用户提供并登记的竞赛规则、题型说明和历年赛题结构资料。

不要一次性加载全部优秀论文和方法资料；它们属于后续的建模与方法选择阶段。

## 11. 与前后模块的交接协议

本模块向 `modeling-selection` 提供：

- `problem-profile.yaml`
- `requirement-trace.yaml`
- `data-inventory.yaml`
- `entity-variable-map.yaml`
- `subproblems.yaml`
- `data-task-matrix.yaml`
- `dependency-graph.yaml`
- `ambiguity-register.yaml`
- `assumption-register.yaml`
- `analysis-audit.yaml`
- `problem-analysis-report.md`

如果后续发现题目理解、字段含义或数据范围错误，必须返回本模块修正，不在下游静默覆盖。
