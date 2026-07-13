# 论文写作模块

## 1. 模块定位

将题目分析、模型设计和真实求解结果组织为符合竞赛或项目要求的论文。它负责论证、表达、引用和格式，不负责制造结果、修改模型或补写不存在的结论。

## 2. 处理目标

- 建立题目要求、模型、结果、验证、图表、文献和正文之间的证据映射。
- 先写核心论证和章节任务，再撰写摘要、模型、结果、评价和结论。
- 锁定术语、变量、单位、指标、公式和图表编号。
- 按 CUMCM、MCM/ICM 或用户规则选择结构与语言，并以当届官方模板为准。
- 检查论文中的数字、图表、公式和引用是否与真实上游证据一致。

## 3. 输入

- `analysis/problem-profile.yaml`、`analysis/requirement-trace.yaml`
- `modeling/model-specification.yaml`、`modeling/validation-plan.yaml`
- `solver/results-manifest.yaml`、`solver/validation-results.yaml`、`solver/reproducibility.json`
- 经核验的文献、官方规则和官方模板

上游文件只读。论文产物全部写入 `paper/`。

## 4. 核心职责

### 4.1 证据与论证

每个核心结论在 `source-map.yaml` 中记录题目要求、证据、支持状态、边界、正文锚点和引用。每段只承担一个任务，例如问题、方法、结果、验证或限制。

### 4.2 草稿与终稿

- `draft`：允许生成带缺口标记的章节计划、术语表和稿件骨架；不能把它当作最终论文。
- `final`：要求 solver 的 `ready_for_writing: true`、验证和复现完成，且每项核心主张和题目要求均有支撑。

### 4.3 参考原则

吸收 Nature 写作 skill 的证据优先、术语台账、段落任务和有边界主张；吸收数模论文手的官方模板优先、真实图表、渲染检查和赛种差异。不会套用 Nature/CNS 的期刊限制，也不会把竞赛论文写成期刊新闻稿。

### 4.4 引用与格式

- 引用实际使用的理论、数据、方法和解释来源，优先原始且可核验的资料。
- 用户要求 Nature/CNS 引用时调用 `nature-citation`；一般建模论文不限制期刊家族。
- DOCX、LaTeX 或 PDF 输出按用户指定模板和相应工具 skill 渲染校验。

## 5. 执行流程

1. 运行初始化器，选择 `draft` 或 `final`。
2. 核对题目要求、模型、结果、验证、复现和官方模板。
3. 建立一句核心论证、术语台账、段落任务图和主张证据映射。
4. 起草正文，并在每项核心主张处保留来源锚点。
5. 管理引用、图表、公式和格式化交付物。
6. 运行一致性审计；缺证据时回退上游。

## 6. 输出文件

```text
paper/
├── intake.yaml
├── argument-map.yaml
├── terminology-ledger.yaml
├── source-map.yaml
├── manuscript.md
├── references.bib
├── writing-audit.yaml
├── paper-report.md
├── writing-feedback.yaml       # 仅需回退时生成
└── manuscript.docx|tex|pdf     # 按指定格式生成
```

## 7. 阶段门禁

终稿要求：每个题目要求都有支持的回答；核心主张有真实结果、模型定义或核验文献；数字和图表可追溯；限制不被隐藏；引用可核验；审计无失败；官方模板和渲染已检查。

没有固定图表、引用、篇幅或“创新点”数量要求，除非官方规则明确规定。

## 8. 失败与回退

- 题意、字段、符号或要求错误：返回 `problem-analysis`。
- 模型、假设、目标或约束解释错误：返回 `modeling-selection`。
- 结果、图表、验证或复现缺失：返回 `numerical-solving`。
- 文献不能核验：保留缺口，不加入终稿。

## 9. 不负责的事项

- 不编造实验结果、参数、图表、参考文献或创新性。
- 不为篇幅或叙事便利改变模型和代码。
- 不把未完成的 draft 或 probe 结果包装为终稿结论。
- 不用流畅文风掩盖证据不足。

## 10. 需要加载的 references

- Nature 可迁移写作原则：`references/nature-informed-principles.md`。
- 比赛模板、优秀论文结构、格式要求和核验过的引用卡：按 `references/index.yaml` 选择性加载。
- 具体 DOCX、LaTeX、PDF 输出按相应格式工具 skill 执行。

## 11. 与前后模块的交接协议

本模块只读前三阶段产物。论文交付后的 `paper/source-map.yaml`、`paper/writing-audit.yaml`、`paper/manuscript.md` 和格式化文件是最终证据包。

若发现上游问题，在 `paper/writing-feedback.yaml` 中记录受影响主张、证据和所需动作，然后退回对应模块。
