# Math Modeling Skill

面向 CUMCM、MCM/ICM 及一般数学建模项目的 Codex skill。它将题目解读、模型设计、数值实验和论文写作拆为可追溯的四个阶段：先固定题意与数据事实，再进行探索式建模，之后执行真实实验，最后仅使用有证据支撑的内容写作。

本项目追求的不是固定算法清单或自动堆叠方法，而是让每个模型选择、实验结果、图表和论文结论都能回答三个问题：它解决了什么问题、依据是什么、在什么条件下会失效。

## 目录

- [适用范围](#适用范围)
- [核心原则](#核心原则)
- [四阶段流程](#四阶段流程)
- [安装](#安装)
- [快速开始](#快速开始)
- [阶段与交接](#阶段与交接)
- [图表、后端与论文交付](#图表后端与论文交付)
- [目录结构](#目录结构)
- [校验与测试](#校验与测试)
- [外部参考与边界](#外部参考与边界)
- [模块文档](#模块文档)

## 适用范围

适用于以下任务：

- 解读数学建模赛题、附件、数据表、图片或官方规则；
- 设计可解释、可验证、可实现的模型与方法链；
- 编写并运行 Python、MATLAB、R 或其他适合环境中的数值实验；
- 生成结果表、证据图、敏感性/鲁棒性分析与复现清单；
- 撰写 CUMCM、MCM/ICM 或一般建模项目的竞赛论文；
- 对多条候选建模路线进行科学比较，识别复杂模型是否值得采用。

它不替代当届官方规则、领域专家判断或真实数据核验。官方题面、附件、模板和提交要求始终高于本 skill 的默认做法。

## 核心原则

1. **事实先于方法**：题面、数据字段、单位、约束、评价口径和必交输出不能被下游静默改写。
2. **探索允许不确定性**：上游有开放项时，可提出分支模型和诊断性试算；正式求解前必须通过 handoff 校验。
3. **复杂度必须有收益**：复杂主路线只有在解决简单路线缺失的能力、且可由本题验证时才值得采用。
4. **真实运行才产生结果**：未运行的代码、外部论文数值或主观猜测都不是本题数值结论。
5. **图表是视觉证据**：图必须支持判断、诊断、比较或决策，不按固定数量生成。
6. **论文由证据向外写作**：主张、数字、图表和引用必须回链到模型定义、真实输出或已核验来源。
7. **复用但不抄袭**：成熟库、公开方法和论文公式可合理参考；代码许可、版本、用途、偏离和验证必须记录。

## 四阶段流程

```text
题目、规则与附件
        |
        v
problem-analysis
        |  problem-profile + subproblems + data audit
        v
modeling-selection
        |  model specification + validation plan + implementation contract
        v
numerical-solving
        |  results + figures + validation + reproducibility
        v
paper-writing
        |  manuscript + source map + formatted submission
        v
最终论文
```

发现问题时按来源回退，而不是在下游文字中掩盖：

```text
题意、字段、单位、数据定义问题  -> problem-analysis
目标、约束、假设、模型关系问题  -> modeling-selection
实现、依赖、数值稳定性、实验问题 -> numerical-solving
论证、证据映射、术语、格式问题   -> paper-writing
```

每个模块只写入自己的项目目录。`analysis/`、`modeling/`、`solver/` 的上游产物在下游均视为只读证据。

## 安装

在 PowerShell 中将仓库克隆到 Codex skills 目录：

```powershell
git clone https://github.com/wbzd-u/math-model-skill.git "$env:USERPROFILE\.codex\skills\my-math-modeling"
```

重新打开或刷新 Codex 后，可通过总入口 `my-math-modeling` 启动完整流程，也可按任务使用单独模块。项目中的脚本使用 Python；运行校验和测试时需要可用的 `jsonschema`，YAML 输入还需要 `PyYAML`。DOCX、PDF、表格和 LaTeX 交付按实际任务调用已安装的相应工具 skill。

## 快速开始

先建立一个独立的项目目录，并将题面、规则和附件放入其中。不要在 skill 安装目录中存放某次赛题的原始数据或运行结果。

```text
my-project/
  sources/
    problem.pdf
    attachment.xlsx
```

从仓库根目录依次执行：

```powershell
# 1. 题目分析
python modules/problem-analysis/scripts/init_problem_analysis.py --project-root <PROJECT_ROOT>
python modules/problem-analysis/scripts/validate_problem_analysis.py --project-root <PROJECT_ROOT>

# 2. 方法选择与模型设计：探索后再正式交接
python modules/modeling-selection/scripts/init_modeling_selection.py --project-root <PROJECT_ROOT>
python modules/modeling-selection/scripts/validate_modeling_selection.py --project-root <PROJECT_ROOT> --mode explore
python modules/modeling-selection/scripts/validate_modeling_selection.py --project-root <PROJECT_ROOT> --mode handoff

# 3. 数值求解：先 probe，再在 READY 契约下 solve
python modules/numerical-solving/scripts/init_numerical_solving.py --project-root <PROJECT_ROOT> --mode probe
python modules/numerical-solving/scripts/validate_numerical_solving.py --project-root <PROJECT_ROOT> --mode probe
python modules/numerical-solving/scripts/init_numerical_solving.py --project-root <PROJECT_ROOT> --mode solve
python modules/numerical-solving/scripts/validate_numerical_solving.py --project-root <PROJECT_ROOT> --mode solve

# 4. 论文写作：先 draft，再 final
python modules/paper-writing/scripts/init_paper_writing.py --project-root <PROJECT_ROOT> --mode draft
python modules/paper-writing/scripts/validate_paper_writing.py --project-root <PROJECT_ROOT> --mode draft
python modules/paper-writing/scripts/init_paper_writing.py --project-root <PROJECT_ROOT> --mode final
python modules/paper-writing/scripts/validate_paper_writing.py --project-root <PROJECT_ROOT> --mode final
```

初始化器只创建结构化骨架，不会替代分析、建模、实验或写作。已存在同阶段目录时，初始化器会拒绝混入新旧产物；只有确认重建时才使用相应的 `--force`。

## 阶段与交接

| 模块 | 目标 | 主要产物 | 关键门禁 |
| --- | --- | --- | --- |
| `problem-analysis` | 从题面和附件提取可追溯问题定义 | `analysis/problem-profile.yaml`、`subproblems.yaml`、`data-inventory.yaml`、歧义与假设登记 | 题意、数据、实体、变量、依赖关系和结构难点必须可定位；不选最终算法 |
| `modeling-selection` | 生成候选路线、比较适用性、写出数学规格与验证契约 | `modeling/model-decision.yaml`、`model-specification.yaml`、`validation-plan.yaml`、`implementation-contract.yaml` | `explore` 允许开放项；`handoff` 要求主路线、可执行验证与 solver 边界清晰 |
| `numerical-solving` | 忠实实现契约、执行诊断/正式运行、产出复现包 | `solver/run-plan.yaml`、`results-manifest.yaml`、`validation-results.yaml`、图表、日志、`reproducibility.json` | `probe` 永不进入论文；`solve` 只接受 READY 契约，且须真实运行与验证 |
| `paper-writing` | 将模型与真实结果组织为可追溯论文 | `paper/argument-map.yaml`、`source-map.yaml`、`manuscript.md`、`manuscript.tex`、`manuscript.pdf` | `final` 要求 `ready_for_writing: true`、核心主张有证据、引用可核验、无未解决反馈 |

### 题目分析

题目分析负责识别比赛类型、题目要求、评价目标、数据规模、字段质量、子问题和依赖关系，并区分：

- 题面显式事实；
- 仍需确认的歧义；
- 为建模提出、且必须验证的假设；
- 可能改变方法选择的隐藏结构或难点。

它不选择最终模型，不编写求解代码，也不撰写论文。

### 方法选择与路线审计

方法选择先定义能力链，再选择方法族。候选路线应说明输入、输出、数据需求、假设、验证方式、实现成本、解释性、风险和拒绝条件。

`model-decision.yaml` 内置轻量路线审计：

- `route_audit.status: not-needed`：透明路线没有实质复杂升级，或额外比较不能改变科学决策；写明理由即可。
- `route_audit.status: audited`：复杂主路线必须绑定已有的 `val-*` 决胜测试、`run-*` 首次执行阶段与实施契约中的反馈触发器。

审计的目的不是强制多个模型，而是形成可执行闭环：

```text
简单路线缺少的能力
  -> 主路线新增的能力
  -> 决胜验证
  -> 失败/翻转条件
  -> solver 反馈
```

### 数值求解与复现

solver 负责实现，不拥有修改题意、目标、硬约束、变量含义、核心假设或评价口径的权限。它必须记录：

- 输入、参数、配置、源码状态和环境；
- 实际执行命令、随机种子、开始/结束时间、日志和退出状态；
- 中间量、收敛/残差/约束信息、成功与失败实验；
- 验证测试、结果文件 SHA-256、限制和回退反馈；
- 第三方库、论文方法或开源实现的来源、版本、许可证与验证方式。

模型不可实现、关键假设被否定、约束冲突或数据不足时，solver 生成 `solver/modeling-feedback.yaml`，并带运行证据返回上游，而不是私自替换模型。

### 论文写作

论文模块先建立一句核心论证、术语台账、章节职责和主张-证据映射，再写正文。每个核心主张必须指向：

- 真实 solver 结果或验证；
- 已写入的模型定义；
- 或经核验的原始文献、规则或数据来源。

论文模块不能创造实验结果、引用、图表或创新性结论。缺少结果、图表、验证、复现或证据时，必须回退对应上游模块。

## 图表、后端与论文交付

### 图表设计

图表在 `numerical-solving` 阶段按需设计。作图前，Agent 需为每幅候选图明确：

- 要支持或否定的结论；
- 要帮助读者作出的比较、诊断或决策；
- 对应的真实 `exp-*` 输出、字段或中间量；
- x/y/系列/区间/约束标记的含义；
- 可能误导结论的尺度、缺失、抽样误差或不可比性；
- 图文件、验证或论文主张之间的追溯关系。

规则根据问题类型建议图形，而不固定图数：预测任务优先比较观测、预测、误差和区间；优化任务优先展示同约束方案比较、Pareto、瓶颈或余量；敏感性分析优先展示参数响应或决策翻转边界；评价任务优先展示排名稳定性和指标贡献。流程图、收敛图、雷达图、饼图和三维图只有在确实比替代图形更能回答判断时才使用。

### Python、MATLAB 与 R

`solver/run-plan.yaml` 必须声明：

```yaml
plotting_backend:
  language: python | matlab | r | not-needed
  rationale: 选择理由
  data_handoff_path: 跨语言数据交接路径或 null
```

选择顺序如下：

1. 用户、官方模板或已有项目代码明确指定语言时遵守指定；
2. 已有稳定求解代码时，默认使用同一语言作图；
3. Python 适合通用数据处理、优化/仿真输出和高度定制布局；
4. MATLAB 适合既有 MATLAB 求解、控制、信号和矩阵计算工作流；
5. R 适合统计推断、回归诊断、分布/分组比较和既有 R 工作流；
6. 跨语言必须有明确能力收益，并通过 CSV/TSV 等可追溯数据交接；最终绘图、预览、导出和视觉 QA 使用同一后端。

颜色语义应在项目内一致：基线使用中性/低饱和色，主方案使用稳定主色，风险或违约使用强调色；不能只用红绿区分类别。定量图优先导出 SVG/PDF，必要时同时生成至少 300 DPI PNG，并在最终插入尺寸下检查文字、标签、图例、比例和可读性。

### LaTeX 与其他格式

除非当届官方规则或用户提供的模板明确要求 DOCX，正式论文默认走：

```text
paper/manuscript.tex -> paper/manuscript.pdf
```

Markdown 稿 `paper/manuscript.md` 保留为可审计内容稿；`references.bib`、图表、公式、引用和编译日志必须可追溯。使用 LaTeX 时通过 `latex-compile` 编译实际主文件，并检查 PDF 的公式、表格、图表、浮动体、页码、文字溢出和空白页。官方 DOCX 模板是格式例外，优先于默认 LaTeX 路线。

## 目录结构

```text
my-math-modeling/
  SKILL.md                       # 总入口
  modules/
    problem-analysis/
      SKILL.md  manifest.yaml  schemas/  scripts/  static/
    modeling-selection/
      SKILL.md  manifest.yaml  schemas/  scripts/  static/  references/
    numerical-solving/
      SKILL.md  manifest.yaml  schemas/  scripts/  static/  references/
    paper-writing/
      SKILL.md  manifest.yaml  schemas/  scripts/  static/  references/
  references/
    external-skill-adapters.md
```

典型项目工作区：

```text
my-project/
  sources/                       # 用户提供的题面、附件、规则；保持只读
  analysis/                      # problem-analysis 产物
  modeling/                      # modeling-selection 产物
  solver/                        # 代码、配置、实验、结果、图表、日志
  paper/                         # 论文、引用、格式化交付物
```

`static/` 存放按工作流加载的提示与规则；`schemas/` 定义机器可校验的数据边界；`scripts/` 负责初始化和校验；`references/` 存放按需阅读的来源说明和扩展规则。

## 校验与测试

每个模块有初始化器、JSON Schema 和校验器。校验器关注结构安全、上游快照、语义边界、真实运行证据、来源与许可证、复现信息和最终主张证据，而不会因为缺少固定数量的模型、图表、基线或引用而机械失败。

从仓库根目录运行模块回归测试：

```powershell
python -m unittest discover -s modules/problem-analysis/tests
python -m unittest discover -s modules/modeling-selection/tests
python -m unittest discover -s modules/numerical-solving/tests
python -m unittest discover -s modules/paper-writing/tests
```

修改 schema、初始化器或校验器后，应同时增加能证明预期行为和失败边界的测试。不要只修改文档来掩盖未被验证的实现变化。

## 外部参考与边界

本 skill 选择性吸收以下经验：

- XiaoMa：官方模板优先、DOCX 校验、可视化导出和角色交接；
- ZSL：赛制差异、优秀论文的结构观察与方法参考；
- LocalWorkflow：模型、求解和写作的职责分离；
- route-selection：复杂路线的反驳、工程可行性与回退思路；
- Nature 系列：证据先于文字、术语统一、主张强度、图表契约和视觉 QA。

这些来源只用于提取可迁移的流程原则。不得复制优秀论文正文、图表、表格、代码、参数或结论；不得将历史赛题或获奖论文的数值直接视为当前题证据；复制、改编或打包外部资产前必须核对其 LICENSE、NOTICE、署名义务和比赛规则。详细边界见 [外部 skill 适配说明](references/external-skill-adapters.md)。

本仓库目前未声明单独的开源许可证。在许可证明确前，请勿假定可以再发布、再许可或复制仓库内容。

## 模块文档

- [题目分析](modules/problem-analysis/README.md)
- [方法选择与建模](modules/modeling-selection/README.md)
- [数值求解](modules/numerical-solving/README.md)
- [论文写作](modules/paper-writing/README.md)

## 贡献

提交改动时应保持四个原则：

1. 新规则必须有明确任务价值和来源边界；
2. 新字段必须有下游消费者或校验价值；
3. 不新增固定模型数、图数、页数或引用数，除非官方规则明确要求；
4. 修改后运行受影响模块测试，修改跨模块契约时运行全部测试。
