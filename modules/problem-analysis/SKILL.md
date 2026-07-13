---
name: problem-analysis
description: 将数学建模赛题、官方规则和 PDF、表格、图片或文本附件转化为可追溯的结构化问题定义。用于 CUMCM、MCM、ICM 及一般建模项目的题目解读、附件与数据审计、要求追踪、子问题拆解、依赖分析、歧义登记和建模前交接；不负责选择最终模型、编写求解代码或撰写论文。
---

# 题目分析路由器

## 根目录

- `MODULE_ROOT`：本文件所在目录，只读。
- `PROJECT_ROOT`：用户题目所在目录，所有产物写入 `PROJECT_ROOT/analysis/`。
- 输入题目、附件和官方规则只读；转换副本写入项目目录。

## 路由协议

每次调用都按以下顺序执行。

### 1. 加载 manifest 和核心规则

读取 [manifest.yaml](manifest.yaml)，再读取 `always_load` 中列出的全部文件。核心契约、工作流和阶段门禁必须同时生效。

### 2. 识别路由轴

根据用户输入和本地文件识别：

- `competition`：`cumcm`、`mcm-icm` 或 `generic`。
- `input_mode`：`text-only`、`documents`、`tabular` 或 `mixed`。

优先采用用户明确提供的比赛信息；无法确认时使用 `generic`，并在歧义登记中记录。混合附件使用 `mixed`，不要为每种格式同时加载所有片段。

### 3. 加载匹配片段

对每个路由轴只读取其匹配文件。不要加载其他竞赛或输入模式片段。完成第三轮并形成初步 `task_tags` 后，按 `manifest.yaml.references.on_demand` 只加载匹配的结构检查卡；`mixed` 不能单独触发全部卡片。当前参考资料库为空时，继续完成基于题目、附件和官方规则的分析，不编造外部依据。

### 4. 初始化交付文件

如 `analysis/` 尚未初始化，运行：

```text
python scripts/init_problem_analysis.py --project-root <PROJECT_ROOT> --title <TITLE> --competition <TYPE> --source <PATH> [...]
```

脚本只创建缺失文件，除非显式使用 `--force`。输出为 JSON-compatible YAML，可由 YAML 或 JSON 工具读取。

### 5. 依次执行七轮分析

按 `manifest.yaml.analysis_sequence` 的顺序，每次只加载并执行一个分析方法文件：

1. 字面证据提取。
2. 实体与变量分析。
3. 要求与子问题拆解。
4. 数据与任务对齐。
5. 子问题依赖分析。
6. 歧义与假设分层。
7. 对抗性完整性审查。

每轮完成后先写入对应结构化产物，再进入下一轮。不要一次性凭总体印象填写所有文件。记录可检查的证据和判断，不输出或要求隐藏的内部思维过程。

第三轮后，先为每个子问题写入初步 `task_tags` 与 `semantic_contract`，再加载匹配的结构检查卡并补全耦合、成功判定、验收测试和最多三项结构难点。

保留来源锚点。题面判断应指向文件、页码、段落、表名、工作表或单元格范围；不能追溯时标记来源不足。

### 6. 阻止方法选择泄漏

允许使用 `prediction`、`optimization`、`evaluation` 等任务结构标签，但不要推荐或比较具体算法。不得出现 `selected_model`、`selected_method`、`algorithm_choice` 或 `solver` 等下游决策字段。

题目明确指定的方法可以作为原题要求记录，但不得在本阶段评价或扩展它。

### 7. 校验并交付

运行：

```text
python scripts/validate_problem_analysis.py --project-root <PROJECT_ROOT> --strict
```

校验失败时修正当前阶段产物；如果失败源于题意、附件或规则缺失，保留具体歧义并停止在门禁处。不要为了通过校验猜测缺失信息。

## 固定交付物

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

## 边界

- 不选择最终模型或算法。
- 不编写正式求解代码。
- 不生成论文结论。
- 不把历史论文结论当作当前题目事实。
- 不因缺少参考资料而跳过题面与附件分析。
- 不把结构难点直接转换为模型、算法或求解器建议。
