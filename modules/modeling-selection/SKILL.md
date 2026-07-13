---
name: modeling-selection
description: 承接 problem-analysis v0.2 结构化交接包，完成探索式候选方法生成、历史案例与方法证据检索、适用性比较、数学模型规格、诊断性验证和 solver 实施契约。用于 CUMCM、MCM、ICM 及一般建模项目的方法选择与模型设计；默认允许在开放项下进行分支建模，正式求解前再执行科学 handoff 校验，不编写求解代码或伪造数值结果。
---

# 方法选择与模型设计路由器

## 根目录

- `MODULE_ROOT`：本文件所在目录，只读。
- `PROJECT_ROOT`：用户赛题或项目目录。
- 上游 `PROJECT_ROOT/analysis/` 只读；本模块只写 `PROJECT_ROOT/modeling/`。

## 路由协议

### 1. 加载规则

读取 [manifest.yaml](manifest.yaml)，再读取 `always_load` 中的核心契约、工作流、准入门禁和质量门禁。

### 2. 执行上游准入

先运行：

```text
python scripts/init_modeling_selection.py --project-root <PROJECT_ROOT> [--subproblem sp-01 ...]
```

初始化器读取并哈希上游十个结构化文件。只要存在可定位的要求和子问题，即使上游为 `DRAFT` 或 `BLOCKED`，也生成完整 `EXPLORATORY` 骨架，允许比较不同解释、提出暂定假设和设计诊断性试算。只有连最小问题定义都不存在时才停止。

若 `modeling/` 已有本模块产物，初始化器会拒绝混合新旧文件。只有在确认要用当前上游重新建立整个建模包时才添加 `--force`；该选项会覆盖本模块产物，并在阻断状态下清除旧的下游候选与契约文件。

### 3. 渐进加载

先读取 `intake-check.yaml`，再根据上游比赛类型加载一个竞赛片段。按选定子问题的 `task_tags`、`difficulty_drivers` 和数据状态检索 [references/index.yaml](references/index.yaml)；只加载命中的少量案例卡、方法卡和验证卡。

索引为空或没有命中时，明确记录 `knowledge_status: none-available`。可以依据上游结构生成候选能力链，但不得声称检索到历史案例或理论证据。

### 4. 依次执行六轮

按 `manifest.yaml.selection_sequence` 顺序执行：

1. 准入与范围确认：复核 `intake-check.yaml`，写报告范围摘要。
2. 结构化证据检索：填写 `candidate-methods.yaml.evidence_records` 与 `knowledge_status`。
3. 候选方法链生成：填写 `candidate-methods.yaml.candidates`。
4. 比较与选型决策：完成 `model-decision.yaml`。
5. 数学模型规格化：完成 `model-specification.yaml`。
6. 诊断与 solver 契约：依次完成 `validation-plan.yaml`、`implementation-contract.yaml`、`modeling-selection-audit.yaml` 和报告。

执行每轮前读取对应方法文件和目标文件的 JSON Schema。每轮只写入其负责的结构化产物。先定义候选链需要完成的能力角色，再按需引用具体方法卡；不得由题型关键词直接跳到算法名称。

候选比较先排除明确回答错误问题或无法产生必交输出的路线，再比较其结构、数据、假设、解释性、风险和实现成本。候选数量、基线和备选由问题需要决定，不为满足格式凑模型。`model-specification.yaml` 与 `validation-plan.yaml` 最终写定后，重新计算它们及 `intake-check.yaml` 的 SHA-256，写入实施契约快照。

### 5. 科学底线

- 将 `analysis/` 视为只读事实契约，不静默修改题意、变量角色、成功判定或评价口径。
- 新增建模假设必须记录依据、影响和验证方式，不能回写成题面事实。
- 可以选择建模方法和定义数学结构，但不选择编程语言、库、数据结构或未批准的数值实现细节。
- 探索状态下允许竞争性解释和暂定假设，但必须标明分支、适用范围、证伪方式和升级为正式方案所需的证据。
- 不编写代码、不运行实验、不生成数值结果、不撰写论文。

### 6. 两种校验模式

日常迭代默认运行：

```text
python scripts/validate_modeling_selection.py --project-root <PROJECT_ROOT> --mode explore
```

`explore` 只阻止无法解析、路径越界、引用不存在、ID 冲突、上游哈希失效或越过 solver 边界等结构性错误；候选不足、验证未完成和缺少基线等作为警告继续推进。

准备正式求解时运行：

```text
python scripts/validate_modeling_selection.py --project-root <PROJECT_ROOT> --mode handoff
```

`handoff` 只额外要求：选定范围已允许交接、主方案覆盖题目要求、数学规格为 `READY`、主要模型和科学主张可验证、不可修改语义进入实施契约、solver 自主边界明确。`--strict` 保留为 `--mode handoff` 的兼容别名。

handoff 通过后，solver 读取 `modeling/implementation-contract.yaml` 及其引用文件。solver 可先执行低成本诊断性试算；若结果否定结构假说、出现不可实现、约束冲突或数据不足，必须携带证据回到本模块修订。

## 固定交付物

只要存在最小问题定义，就生成：

```text
modeling/intake-check.yaml
modeling/candidate-methods.yaml
modeling/model-decision.yaml
modeling/model-specification.yaml
modeling/validation-plan.yaml
modeling/implementation-contract.yaml
modeling/modeling-selection-audit.yaml
modeling/modeling-selection-report.md
```

只有缺少可定位要求或子问题、无法形成任何探索闭环时，才只生成 `intake-check.yaml` 与阻断报告。
