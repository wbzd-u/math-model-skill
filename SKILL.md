---
name: my-math-modeling
description: 面向 CUMCM、MCM、ICM 及一般数学建模任务的四阶段工作流。完成题目分析、探索优先的模型设计、契约驱动的代码求解和证据落地的论文写作，可生成附件审计、候选模型、实施契约、诊断试算、正式结果、复现清单、论证图和竞赛论文。当用户要求赛题解读、建模方案、代码求解、数值实验、结果验证、数学建模论文或启动完整数学建模流程时使用。
---

# 我的数学建模

## 当前能力

当前开放四个连续阶段：

1. 题目分析：读取 [modules/problem-analysis/SKILL.md](modules/problem-analysis/SKILL.md) 并完整执行其路由协议。
2. 方法选择与模型设计：题目分析形成最小问题定义后即可进入探索；读取 [modules/modeling-selection/SKILL.md](modules/modeling-selection/SKILL.md) 并完整执行其路由协议。开放项阻止正式 handoff，但不阻止分支建模。
3. 数值求解与实验执行：读取 [modules/numerical-solving/SKILL.md](modules/numerical-solving/SKILL.md)。诊断性试算使用 `probe`；正式结果使用 `solve`，并要求上游 handoff 通过。
4. 论文写作：读取 [modules/paper-writing/SKILL.md](modules/paper-writing/SKILL.md)。`draft` 形成论证与证据骨架；`final` 只在 solver 允许写作后形成可提交稿。

不要使用占位 README 代替正式规则，也不要把 probe 结果直接用于论文。

## 目录契约

- `SKILL_ROOT`：本文件所在目录，只读。
- `PROJECT_ROOT`：用户赛题或项目所在目录；题目分析写入 `analysis/`，方法选择与模型设计写入 `modeling/`，数值求解写入 `solver/`，论文写作写入 `paper/`。
- 原始题目、附件和官方规则保持只读；需要转换时在 `PROJECT_ROOT` 中创建副本。

## 人机协作与决策台账

LLM 负责提出可验证的选项与推荐，Skill 负责证据、边界、交接和回退；人只负责高影响取舍。仅当当前任务确有高影响决定时，从 [assets/human-decision-ledger.template.yaml](assets/human-decision-ledger.template.yaml) 在 `PROJECT_ROOT/decisions/human-decision-ledger.yaml` 创建或更新台账，并遵守 [references/human-decision-ledger.md](references/human-decision-ledger.md)。

- **自动执行**：文件审计、字段检查、模板映射、代码实现细节、日志、复现、视觉 QA 和低风险诊断。
- **提出选项，可人工选择**：候选路线、数据清洗细节、求解器、图表和验证配置。
- **必须等人工确认**：问题范围、核心假设、目标/风险取舍、外部数据政策、主路线承诺，以及最终主张的适用范围或创新性表述。

`awaiting-human` 的条目阻断其依赖的 `READY` handoff、正式 `solve` 或 `final`，但不阻断不依赖该决定的附件审计、候选探索和诊断准备。不得把 Agent 推荐、沉默或默认值记作人工选择。

判断提示从其他 Skill 独立适配时，读取 [references/judgment-prompt-adapters.md](references/judgment-prompt-adapters.md) 了解可迁移的提问结构与明确排除的固定套路。

## 路由

| 用户意图 | 执行 |
|---|---|
| 题目分析、读题、附件审计、子问题拆解 | 执行题目分析模块 |
| 方法选择、建模方案、模型设计 | 若缺少最小题目分析包，先执行题目分析；否则默认以 `explore` 模式执行方法选择与模型设计 |
| 诊断试算、检查模型能否实现 | 上游至少有 `EXPLORATORY` 契约后，以 `probe` 执行 numerical-solving |
| 正式代码求解、实验、结果验证 | 上游 handoff 通过后，以 `solve` 执行 numerical-solving |
| 论文提纲、论证图、证据映射 | 执行 paper-writing 的 `draft` 模式，显式保留证据缺口 |
| 数学建模论文、摘要、模型章节、最终稿 | solver 已就绪时执行 paper-writing 的 `final` 模式 |
| 启动完整数学建模流程 | 依次执行题目分析、探索式模型设计、handoff、正式求解、论文写作 |

## 完成判定

每个阶段都要报告当前状态，而不是用一个严格门禁掩盖有效进展：

- 题目分析：比赛、范围、输入、子问题、依赖、歧义、数据风险和门禁状态。
- 方法选择与模型设计：探索范围、可 handoff 范围、知识状态、候选路线、当前主方案、模型组件、验证计划、实施契约和 `ready_for_solver`。
- 数值求解：模式、输入绑定、复用/自研决策、真实实验、验证状态、必需输出、失败记录、复现信息、反馈和 `ready_for_writing`。
- 论文写作：论证主线、术语台账、主张证据、要求覆盖、格式状态、回退清单和 `ready_for_submission`。
- 每个阶段均报告校验结果、未解决项和交付文件位置。
