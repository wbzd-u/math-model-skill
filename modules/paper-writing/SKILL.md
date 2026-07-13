---
name: paper-writing
description: 承接 problem-analysis、modeling-selection 与 numerical-solving 的结构化产物，生成可追溯的数学建模竞赛论文论证图、Markdown 稿件、引用清单和指定格式交付物。用于 CUMCM、MCM、ICM 及一般建模项目的摘要、模型、结果、讨论与完整论文写作；支持 draft 证据骨架和 final 正式交付，遵循官方模板优先、证据先于文字、术语一致和真实结果回链，不创造结果或引用。
---

# 数学建模论文写作路由器

## 根目录

- `MODULE_ROOT`：本文件所在目录，只读。
- `PROJECT_ROOT`：用户赛题或项目目录。
- 将 `analysis/`、`modeling/`、`solver/` 视为只读证据；本模块只写 `paper/`。
- 官方模板、官方规则和用户指定格式优先于本模块的默认章节结构。

## 初始化

选择模式后运行：

```text
python scripts/init_paper_writing.py --project-root <PROJECT_ROOT> --mode draft|final
```

- `draft`：整理证据、术语、论证链和章节骨架。允许存在证据缺口，但每个缺口必须显式标记，不能写成结论。
- `final`：要求 `solver/results-manifest.yaml` 的 `ready_for_writing: true`，验证、复现和核心结果均可追溯。只有此模式可形成可提交稿件。

初始化器生成 `paper/intake.yaml`、`argument-map.yaml`、`terminology-ledger.yaml`、`source-map.yaml`、稿件骨架和审计清单。已有 `paper/` 时拒绝混入新旧证据；只有确认重建时使用 `--force`。

## 五轮写作

按 `manifest.yaml.writing_sequence` 依次执行：

1. **证据准入**：核对题目要求、模型规格、实际结果、验证、图表、文献和格式规则。
2. **论证与术语**：写出一句核心论证，锁定模型、变量、指标、单位和缩写的标准称呼。
3. **章节与证据映射**：每段只承担一个任务；每个核心主张绑定到结果、验证、模型定义或核验文献。
4. **起草与引用**：从证据向外写作，按比赛类型安排摘要、模型、结果和评价；引用原始且可核验的来源。
5. **一致性与交付**：检查数字、公式、图表、章节引用、术语、限制、模板和渲染效果，生成格式化交付物。

## 从 Nature 系列流程吸收的原则

- 先写“问题、回答、方法、证据、边界”一句话论证，再写正文。
- 每段有单一任务：背景、问题、方法、结果、比较、解释或限制。
- 术语、符号、单位和缩写使用同一台账，不为文采强行换名。
- 主张强度与证据相配；不能以“证明”“显著优于”等词替代未完成验证。
- 文献必须支持实际陈述。论文标题相关、搜索摘要或二手转述不构成引用证据。

不要继承 Nature/CNS 的期刊范围、版式或夸张新颖性表述。数学建模竞赛以题目回答完整、逻辑清楚、模型可复现和官方格式合规为首要目标。

## 竞赛适配

根据 `analysis/problem-profile.yaml` 和官方规则选择 `cumcm`、`mcm-icm` 或 `generic` 片段。

- CUMCM：中文表达、摘要/关键词、问题重述、假设、符号、模型、求解、结果、评价；当届官方页数和模板优先。
- MCM/ICM：英文 Summary、问题解释、模型与验证、结果、局限和建议；不要把 CUMCM 固定章节直接套入。
- ICM：当题目涉及政策、社会、环境或伦理维度时，将其写入证据支持的讨论，而不是空泛展望。

## 引用、模板与渲染

- 使用方法、数据、理论或他人成果时记录原始来源、稳定标识、核验状态和正文位置。
- 用户明确要求 Nature/CNS 风格引用时，调用 `nature-citation`；一般建模论文不限制期刊家族，可使用已安装的通用文献检索工具。
- DOCX 交付时按 `docx` 或 `DOCX工具` skill 的渲染校验规则执行；LaTeX 交付时使用 `latex-compile`；无指定格式时维护 Markdown 主稿。
- 图表只使用 `solver/results-manifest.yaml` 和真实输出中可追溯的文件。不要为装饰添加无结果支撑的图。

## 回退边界

必须回退而非自行修补的情况：

- 题意、术语、字段或符号错误：`problem-analysis`。
- 目标、约束、假设、模型关系或方法解释错误：`modeling-selection`。
- 缺少结果、图表、验证、复现信息，或数值与代码不一致：`numerical-solving`。

不修改上游代码、数据、模型或结果来让稿件“更顺”。所有回退写入 `paper/writing-feedback.yaml`。

## 校验与交付

```text
python scripts/validate_paper_writing.py --project-root <PROJECT_ROOT> --mode draft|final
```

`draft` 允许未完成项并报告 `DRAFT_READY`。`final` 要求所有核心要求和主张有支撑、终稿无占位、来源可核验、审计无失败，并给出 `ready_for_submission: true`。

固定产物：

```text
paper/intake.yaml
paper/argument-map.yaml
paper/terminology-ledger.yaml
paper/source-map.yaml
paper/manuscript.md
paper/references.bib
paper/writing-audit.yaml
paper/paper-report.md
paper/writing-feedback.yaml       # 仅需回退时生成
paper/manuscript.docx|tex|pdf     # 仅按目标格式生成
```
