---
name: numerical-solving
description: 承接 modeling-selection 的结构化实施契约，完成数学建模代码实现、诊断试算、正式数值求解、实验验证、结果图表与可复现交付。用于 CUMCM、MCM、ICM 及一般建模项目的 Python、MATLAB、R 或其他适合环境中的求解执行；支持 probe 探索诊断和 solve 正式求解，优先复用语义匹配且许可明确的成熟库或公开方法，不静默改变模型，也不撰写论文。
---

# 数值求解与实验执行路由器

## 根目录

- `MODULE_ROOT`：本文件所在目录，只读。
- `PROJECT_ROOT`：用户赛题或项目目录。
- 将 `PROJECT_ROOT/analysis/` 与 `PROJECT_ROOT/modeling/` 视为只读输入；只写 `PROJECT_ROOT/solver/`，除非上游契约明确指定其他项目内输出路径。
- 原始数据保持只读；清洗数据、缓存和中间结果写入 `solver/`。

## 加载与初始化

1. 读取 [manifest.yaml](manifest.yaml) 和其中 `always_load` 的核心规则。
2. 根据用户目的选择模式：结构诊断、可行性试算或建模反馈使用 `probe`；正式结果使用 `solve`。目的不明确时默认 `probe`。
3. 运行：

```text
python scripts/init_numerical_solving.py --project-root <PROJECT_ROOT> --mode probe|solve
```

初始化器校验上游 Schema 和契约快照，再从 `analysis/data-inventory.yaml`、`entity-variable-map.yaml`、`data-task-matrix.yaml` 与建模契约生成 `solver/intake.yaml`。该文件是派生运行时视图，不是新的题意事实来源。

`probe` 接受 `EXPLORATORY` 或 `READY` 契约。`solve` 只接受 `READY` 契约；哈希失效、输入绑定无法解析或上游 handoff 不成立时停止正式求解。

若 `solver/` 已存在，初始化器拒绝混合新旧运行。只有确认要按当前契约重建整个 solver 包时才使用 `--force`。

## 执行五轮

按 `manifest.yaml.execution_sequence` 依次执行，每轮先读取对应方法文件和目标 Schema：

1. **准入与绑定**：复核模式、范围、数据、变量、参数、阶段和输出绑定；不唯一的绑定保持 `unresolved`。
2. **复用与计划**：为每个非平凡组件判断成熟库、官方实现、论文方法或自研路线，完成 `run-plan.yaml` 与 `implementation-provenance.yaml`。
3. **实现与局部校验**：忠实翻译模型，先完成最小可运行链，使用小例、性质测试、边界样例或已知解检查实现。
4. **运行与诊断**：执行真实命令，保留种子、配置、日志、失败运行、中间数据、约束与终止信息。
5. **验证与交付**：执行契约指定的 `val-*` 和必要的基础健全性检查，生成结果清单、复现清单、报告或建模反馈。

不要按关键词加载算法百科。仅当当前模型族需要时，查询 [references/index.yaml](references/index.yaml) 并加载少量实现卡或诊断卡。索引为空时可以使用官方文档、可靠开源库和原始论文，但必须记录来源。

## 双模式

### `probe`

- 允许缩小规模、降低精度、使用合成边界样例、放松非核心数值设置或替换为廉价代理以回答明确的诊断问题。
- 在 `run-plan.yaml` 记录每项简化、适用范围和不能支持的结论。
- 模型假说被否定是有效结果；保留证据并生成 `modeling-feedback.yaml`。
- 不要求完成全部正式输出，也不强制运行未被诊断问题需要的基线、备选或验证。
- `ready_for_writing` 永远为 `false`，不得把 probe 数值写成题目最终结论。

### `solve`

- 只执行 `READY` 契约批准的组件、阶段、必需输出和验证测试。
- 基线、备选、敏感性、鲁棒性和图表只在契约或科学判断确有需要时执行，不为格式凑数量。
- 验证失败时保留全部运行证据，状态设为 `NEEDS_REVISION`；不得筛掉不利结果。
- 只有必需输出、关键不变量、验证记录、来源台账与复现信息完整时，才能设置 `ready_for_writing: true`。

## 复用优先但不降低验证

优先顺序通常为：成熟库公开 API、许可明确的官方/作者实现、依据原始论文独立实现、自研。库若不能忠实表达目标、约束、变量域、评价口径或精度要求，不得为了复用而改变模型。

- 使用公开 API 不属于抄袭，但要记录包名、版本、官方来源、许可证和用途。
- 公开仓库不等于允许复制。复制、修改或 vendoring 代码前必须核对代码自己的许可证、竞赛规则和署名义务。
- 依据论文实现时，定位原始公式、章节或算法，独立组织代码并记录偏离；不得复制论文文字、图表、结果或把论文参数当作本题事实。
- 自研不等于方法创新。没有匹配实现、许可证冲突、环境不可用或本题组合逻辑特殊时可以自研，但记录原因和正确性验证。
- 对复用和自研代码执行同等的约束、边界、数值与基准检查。

涉及第三方代码、论文实现或许可证判断时读取 [references/reuse-and-provenance.md](references/reuse-and-provenance.md)。

## 执行边界

在上游授权范围内，可选择语言、维护良好的库、等价数值算法、数据结构、并行策略、缓存、随机种子、容差和日志方式。

以下变化必须生成反馈并返回上游：

- 改变目标、硬约束、变量含义或变量域、单位、核心假设、评价口径或必交输出；
- 更改不允许校准的参数或参数来源政策；
- 用启发式近似替代要求精确性的模型，却仍声称原结论；
- 删除约束、样本或失败运行来获得更好结果；
- 字段语义、单位或题意事实不清，需要重新解释题目。

实现错误、依赖安装、内存管理、数值稳定性和等价求解器切换由本模块处理。模型或契约错误返回 `modeling-selection`；数据语义或题意错误返回 `problem-analysis`。

## 校验

迭代时运行：

```text
python scripts/validate_numerical_solving.py --project-root <PROJECT_ROOT> --mode probe
```

正式交付前运行：

```text
python scripts/validate_numerical_solving.py --project-root <PROJECT_ROOT> --mode solve
```

校验器只把结构损坏、路径越界、上游哈希失效、语义越权、无许可源码复用、伪造运行证据和正式必需输出缺失视为硬错误。候选库数量、图表数量、语言选择、是否存在基线或备选不构成硬门槛。

## 固定交付物

```text
solver/intake.yaml
solver/run-plan.yaml
solver/implementation-provenance.yaml
solver/experiment-registry.yaml
solver/validation-results.yaml
solver/results-manifest.yaml
solver/reproducibility.json
solver/solver-audit.yaml
solver/solver-report.md
solver/modeling-feedback.yaml        # 仅需回退时生成
solver/src/ solver/configs/ solver/results/ solver/figures/ solver/logs/
```

报告当前模式、执行状态、真实运行、失败实验、限制、反馈去向和 `ready_for_writing`。不撰写论文，不从未运行的代码推断数值结果。
