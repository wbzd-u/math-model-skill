# Competition Writing and Delivery Adapters

This protocol absorbs XiaoMa's official-template-first DOCX route, ZSL's competition distinctions and outstanding-paper reading value, and UnknownJack's sectioned-delivery concept. LaTeX is the preferred formal source for formula-heavy, reproducible competition papers. These adapters cannot override the evidence chain or upstream facts.

## Format selection

1. Read current official rules and the user-provided template first.
2. When an official DOCX template is mandatory, use it as the format source and run rendering/validation through `DOCX工具` or `docx`.
3. Otherwise, use LaTeX as the formal source: maintain `paper/manuscript.tex`, `paper/references.bib`, the real figure files, and an actual `latex-compile` log. Keep Markdown as an evidence-auditable companion.
4. Use Typst only when the user requests it or the project already has a usable template; preserve sectional sources and an actual compile log. Do not assume a usable Typst asset exists.

Templates control layout, not scientific content. Current rules always override old templates and examples.

## Learn from competition samples

- identify the argument function of the summary, restatement, model, validation, results, limitations, and recommendations;
- use official CUMCM/MCM/ICM rules to choose language, summary, and section emphasis;
- identify likely reader challenges, then return to the current project to fill the evidence gap.

Do not reproduce sample titles, wording, section sentences, figures, data, parameters, conclusions, reference combinations, or detailed layout. Page limits, attachment requirements, and format rules must come from the current official files, never fixed skill content.

## Pre-delivery record

Record alongside `writing-audit.yaml`: template origin, version or hash, rendering command, layout/compile issues, and their resolution. Passing layout checks does not imply that the evidence chain passes; both are required.
