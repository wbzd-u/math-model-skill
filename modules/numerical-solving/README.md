# 数值求解与实验执行模块

## 1. 模块定位

承接 `PROJECT_ROOT/modeling/implementation-contract.yaml`，把已定义的模型转化为真实运行、可验证、可复现的代码和结果。

本模块回答“怎样忠实、可靠地算出来”。它可以选择合适的语言、维护良好的库和等价数值实现，但不静默修改模型，也不撰写论文。

## 2. 处理目标

- 将上游数据、变量、参数、阶段和输出稳定 ID 绑定到实际运行对象。
- 通过 `probe` 低成本检验可行性、可识别性、数值稳定性或结构假说。
- 通过 `solve` 执行正式契约，生成真实结果和验证证据。
- 优先复用语义匹配、维护可靠且许可明确的库或公开方法。
- 记录外部来源、版本、许可证、改动、命令、种子、哈希和失败运行。
- 发现数据或模型问题时生成可复现的上游反馈。

## 3. 输入

权威输入包括：

- `modeling/implementation-contract.yaml`
- `modeling/model-specification.yaml`
- `modeling/validation-plan.yaml`
- `modeling/intake-check.yaml`
- `analysis/data-inventory.yaml`
- `analysis/entity-variable-map.yaml`
- `analysis/data-task-matrix.yaml`
- 原始题目数据和附件

初始化后生成的 `solver/intake.yaml` 是运行时绑定视图，不是新的题意或数据事实来源。原始数据始终只读。

## 4. 核心职责

### 4.1 输入契约与绑定

- 验证上游快照和 handoff 状态。
- 将 `data-*`、`var-*`、`param-*`、`run-*`、`cmp-*`、`val-*` 和 `out-*` 映射到文件、字段、参数、代码和实验。
- 无法唯一解析的字段、单位或参数保持未解析；正式求解不能猜值。

### 4.2 双模式执行

- `probe`：接受 `EXPLORATORY` 或 `READY` 契约，用缩小规模、合成样例或低成本试算回答明确诊断问题。结果不能进入论文。
- `solve`：只接受 `READY` 契约，执行契约规定的组件、阶段、输出和验证。只有完整可信时才允许 `ready_for_writing: true`。

### 4.3 复用与自研决策

- 通常优先成熟库 API、许可明确的官方/作者实现、原始论文方法的独立实现，最后才是自研。
- 使用库不等于抄袭，但必须记录版本、来源、许可证和用途。
- 公开仓库不等于允许复制；论文引用不等于取得附带代码许可证。
- 根据论文实现时独立组织代码，记录公式或算法定位和偏离，不复制文字、图表、结果或参数结论。
- 没有合适实现时允许自研，说明原因并提供正确性验证；不把自研自动描述为创新。

### 4.4 实现、实验与验证

- 先完成最小可运行链和小例/性质/边界检查，再进行大规模实验。
- 每次真实运行记录命令、输入、配置、seed、日志、退出状态、中间量和输出哈希。
- 执行契约指定验证，并按模型族加载必要诊断，不机械套用全部检查。
- 保留失败和不利结果，区分实现、环境、数值、数据与模型契约问题。

## 5. 执行流程

1. 运行初始化器并选择 `probe` 或 `solve`。
2. 完成输入、变量、参数、阶段和输出绑定。
3. 判断外部实现是否语义匹配、许可允许且可复现。
4. 写运行计划并实现最小可运行链。
5. 运行局部检查和真实实验。
6. 执行契约验证及必要的模型族诊断。
7. 生成结果、来源和复现清单。
8. 校验阶段状态；必要时生成上游反馈。

## 6. 输出文件

```text
solver/
├── intake.yaml
├── run-plan.yaml
├── implementation-provenance.yaml
├── experiment-registry.yaml
├── validation-results.yaml
├── results-manifest.yaml
├── reproducibility.json
├── solver-audit.yaml
├── solver-report.md
├── modeling-feedback.yaml       # 仅需回退时生成
├── src/
├── configs/
├── results/
├── figures/
└── logs/
```

## 7. 阶段门禁

`probe` 完成只要求有明确诊断目标，以及真实运行或可复现阻断证据；模型被否定仍是有效诊断，但 `ready_for_writing` 必须为 `false`。

`solve` 进入论文阶段前要求：上游快照有效；必需阶段和输出来自真实运行；关键不变量及验证有证据；第三方来源与许可证可追溯；命令、环境、输入、源码、配置、seed、日志和输出可复现。

没有基线、备选、敏感性分析、固定数量图表或特定语言本身不构成失败，除非契约明确要求。

## 8. 失败与回退

- 实现错误、依赖、性能和数值稳定性：本模块修复或更换语义等价实现。
- 字段、单位、题意或数据定义问题：生成 `solver/modeling-feedback.yaml`，返回 `problem-analysis`。
- 不可行、约束冲突、参数不可识别或结构假说被否定：携带运行证据返回 `modeling-selection`。
- 验证失败：按上游 `failure_action` 处理，不把需要修订的问题降格为文字限制。

## 9. 不负责的事项

- 不擅自改变目标、硬约束、变量含义、核心假设、参数政策或评价口径。
- 不复制许可证未知的代码，不通过改名或逐行重写掩盖来源。
- 不伪造运行、选择性删除失败结果或把论文结果当作本题结果。
- 不将 probe 结果包装为正式结论。
- 不撰写论文或声称未经证据支持的方法创新。

## 10. 需要加载的 references

- 第三方代码、论文实现或许可证判断：`references/reuse-and-provenance.md`。
- 当前模型族的库适配卡、正确性检查卡和数值诊断卡：按 `references/index.yaml` 命中加载。
- 知识库为空时可查询官方文档、可靠仓库和原始论文，但必须在来源台账中记录。

不保存大段手写 GA、PSO 等算法模板；优先积累成熟库适配方法、论文来源定位和诊断知识。

## 11. 与前后模块的交接协议

本模块只读 `analysis/` 与 `modeling/`，向后续论文写作提供：

- `solver/results-manifest.yaml`
- `solver/validation-results.yaml`
- `solver/implementation-provenance.yaml`
- `solver/reproducibility.json`
- `solver/results/`、`solver/figures/` 和 `solver/solver-report.md`

只有 `solve` 校验通过且 `ready_for_writing: true` 时，论文模块才能把数值结果作为正式证据。
