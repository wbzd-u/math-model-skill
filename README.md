# Math Modeling Skill

面向 CUMCM、MCM/ICM 及一般数学建模项目的四阶段 Codex skill。它把题目解读、模型设计、数值实验和论文写作拆开交接：先保留题意与数据事实，再允许探索式建模，最后只用真实运行结果完成论文。

## 流程

```text
题目与附件
  -> problem-analysis
  -> modeling-selection
  -> numerical-solving
  -> paper-writing
```

| 阶段 | 解决的问题 | 关键产物 |
| --- | --- | --- |
| `problem-analysis` | 题目究竟要求什么，数据是否可用，真正难点和歧义在哪里 | `analysis/problem-profile.yaml`、`subproblems.yaml`、`data-inventory.yaml` |
| `modeling-selection` | 哪些方法与模型链合理，为什么选择，如何验证 | `modeling/model-specification.yaml`、`validation-plan.yaml`、`implementation-contract.yaml` |
| `numerical-solving` | 如何忠实实现、诊断、求解和复现模型 | `solver/results-manifest.yaml`、图表、日志、复现清单 |
| `paper-writing` | 如何把可追溯的模型与结果写成竞赛论文 | `paper/manuscript.md`、`manuscript.tex`、`manuscript.pdf`、证据映射 |

每一阶段只写入自己的目录，不能静默修改上游题意、模型语义或数值结果。发现问题时将带证据退回来源阶段。

## 使用方式

将本目录放入 Codex skills 目录后，使用总入口 `my-math-modeling` 启动完整流程，或按任务调用单独模块：

```text
problem-analysis
modeling-selection
numerical-solving
paper-writing
```

每个模块有独立的 `SKILL.md`、初始化脚本、JSON Schema、校验脚本和测试。项目工作目录的典型结构为：

```text
project/
  sources/
  analysis/
  modeling/
  solver/
  paper/
```

先把题面和附件放入项目目录。初始化和校验命令由相应模块的 `SKILL.md` 给出；不要手工伪造下游交接文件。

## 设计原则

- 题目、附件与官方规则优先于经验模板和知识库。
- 方法库、历史赛题和优秀论文是可选参考，不是推理的替代品。
- 允许探索，但正式求解必须有清晰的模型规格、验证计划和实施契约。
- 优先复用语义匹配且许可明确的成熟库或公开方法；记录来源、版本、许可和验证。
- 论文结论必须回链到真实结果、模型定义或已核验文献；不生成无证据结论。

## 论文交付

除非当届官方规则或用户提供的模板明确要求 DOCX，正式稿默认采用 LaTeX：

```text
paper/manuscript.tex -> paper/manuscript.pdf
```

`paper/manuscript.md` 保留为可审计内容稿，`references.bib`、图表、公式、引用和 PDF 编译日志应可追溯。官方 DOCX 模板是格式例外，仍优先于默认 LaTeX 路线。

## 外部参考与许可

本 skill 吸收 XiaoMa 的官方模板与 DOCX 校验思路、ZSL 的赛制与案例阅读思路、LocalWorkflow 的角色交接思路，以及 Nature 系列的证据与术语纪律。详细边界见 [外部 skill 适配说明](references/external-skill-adapters.md)。

不得复制优秀论文的正文、图表、表格、代码、参数或结论。复制、改编或打包任何外部资产前，必须核对其许可证、署名义务和比赛规则。

## 模块文档

- [题目分析](modules/problem-analysis/README.md)
- [方法选择与建模](modules/modeling-selection/README.md)
- [数值求解](modules/numerical-solving/README.md)
- [论文写作](modules/paper-writing/README.md)
