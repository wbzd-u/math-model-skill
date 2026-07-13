#!/usr/bin/env python3
"""Initialize an evidence-grounded paper-writing package."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "0.1.0"
MODULE_ROOT = Path(__file__).resolve().parents[1]
AUDIT_DIMENSIONS = [
    "input_integrity", "requirement_coverage", "claim_evidence", "terminology",
    "numerical_consistency", "figures_tables", "citations", "limitations",
    "competition_format", "render_quality",
]
UPSTREAM = [
    ("analysis/problem-profile.yaml", True),
    ("analysis/requirement-trace.yaml", True),
    ("analysis/entity-variable-map.yaml", False),
    ("modeling/model-specification.yaml", False),
    ("modeling/validation-plan.yaml", False),
    ("solver/results-manifest.yaml", False),
    ("solver/validation-results.yaml", False),
    ("solver/reproducibility.json", False),
]


def load_structured(path: Path) -> Any:
    text = path.read_text(encoding="utf-8-sig")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        try:
            import yaml  # type: ignore
            return yaml.safe_load(text)
        except Exception as exc:
            raise ValueError(f"cannot parse {path}: {exc}") from exc


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def reset_paper_dir(paper_dir: Path, project_root: Path) -> None:
    resolved = paper_dir.resolve()
    if resolved.parent != project_root.resolve() or resolved.name != "paper":
        raise ValueError(f"refusing to reset unsafe paper path: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)


def competition_profile(profile: dict[str, Any]) -> tuple[str, str, str | None, list[str]]:
    competition = profile.get("competition", {}) if isinstance(profile.get("competition"), dict) else {}
    raw_type = str(competition.get("type") or "unknown").lower()
    if raw_type in {"cumcm", "mcm", "icm"}:
        kind = raw_type
    else:
        kind = "generic" if raw_type not in {"", "unknown"} else "unknown"
    language = "zh" if kind == "cumcm" else "en" if kind in {"mcm", "icm"} else "unknown"
    source_files = profile.get("source_files", [])
    return kind, language, None, [str(item) for item in source_files if item]


def section_template(kind: str) -> list[tuple[str, str, str]]:
    if kind == "cumcm":
        titles = [
            ("摘要", "概述问题、模型、真实关键结果和限制"),
            ("问题重述与分析", "明确题目要求和结构"),
            ("假设与符号说明", "限定模型边界并统一符号"),
            ("模型建立与求解", "说明模型组件、算法和实现"),
            ("结果、检验与评价", "回答要求并报告验证和局限"),
            ("参考文献", "列出已核验来源"),
        ]
    elif kind in {"mcm", "icm"}:
        titles = [
            ("Summary", "State the problem, answer, method, evidence, and boundary"),
            ("Problem restatement and assumptions", "Define the task and assumptions"),
            ("Model and solution", "Specify and solve the model"),
            ("Results and validation", "Answer the task with evidence"),
            ("Limitations and recommendations", "State boundaries and applicable recommendations"),
            ("References", "List verified sources"),
        ]
    else:
        titles = [
            ("Problem and scope", "Define the required answer"),
            ("Model and solution", "Explain the model and implementation"),
            ("Results and validation", "Present traceable results and checks"),
            ("Limitations", "State the model boundary"),
            ("References", "List verified sources"),
        ]
    return [(f"sec-{index:02d}", title, purpose) for index, (title, purpose) in enumerate(titles, start=1)]


def report(mode: str, status: str, reasons: list[str]) -> str:
    lines = "\n".join(f"- {item}" for item in reasons) if reasons else "- 当前没有准入阻断。"
    return f"""# 论文写作报告

## 准入

- 模式：`{mode}`
- 状态：`{status}`

### 事项

{lines}

## 论证与证据

[待填写]

## 稿件与格式

[待填写]

## 审计与回退

[待填写]
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--mode", choices=["draft", "final"], default="draft")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    root = args.project_root.resolve()
    paper_dir = root / "paper"
    if paper_dir.exists() and any(paper_dir.iterdir()):
        if not args.force:
            print("ERROR: paper package already exists; use --force only to rebuild from current evidence")
            return 2
        try:
            reset_paper_dir(paper_dir, root)
        except ValueError as exc:
            print(f"ERROR: {exc}")
            return 2

    payloads: dict[str, dict[str, Any]] = {}
    upstream_files: list[dict[str, Any]] = []
    reasons: list[str] = []
    hard: list[str] = []
    for relative, required in UPSTREAM:
        path = root / relative
        if not path.is_file():
            upstream_files.append({"path": relative, "sha256": None, "required": required or args.mode == "final"})
            message = f"missing upstream file: {relative}"
            if required or args.mode == "final":
                hard.append(message)
            else:
                reasons.append(message)
            continue
        try:
            payloads[relative] = load_structured(path)
        except (OSError, ValueError) as exc:
            hard.append(str(exc))
        upstream_files.append({"path": relative, "sha256": sha256_file(path), "required": required or args.mode == "final"})

    profile = payloads.get("analysis/problem-profile.yaml", {})
    requirements = payloads.get("analysis/requirement-trace.yaml", {}).get("requirements", [])
    requirements = [item for item in requirements if isinstance(item, dict) and item.get("id")]
    requirement_ids = [item["id"] for item in requirements]
    if not requirement_ids:
        hard.append("no traceable requirement is available for the paper")
    solver_manifest = payloads.get("solver/results-manifest.yaml", {})
    validation = payloads.get("solver/validation-results.yaml", {})
    reproducibility = payloads.get("solver/reproducibility.json", {})
    if args.mode == "final":
        if solver_manifest.get("ready_for_writing") is not True:
            hard.append("final paper requires solver ready_for_writing: true")
        if validation.get("status") not in {"COMPLETE", "COMPLETE_WITH_LIMITATIONS"}:
            hard.append("final paper requires completed validation results")
        if reproducibility.get("status") != "COMPLETE":
            hard.append("final paper requires complete reproducibility evidence")
    elif not solver_manifest:
        reasons.append("no solver result package is available; only an evidence-gap outline can be drafted")

    kind, language, template_path, rule_sources = competition_profile(profile)
    status = "READY" if not hard else "BLOCKED"
    intake = {
        "schema_version": SCHEMA_VERSION,
        "mode": args.mode,
        "status": status,
        "project_id": profile.get("project_id", root.name),
        "competition": {"type": kind, "language": language, "template_path": template_path, "rule_sources": rule_sources},
        "upstream_files": upstream_files,
        "requirement_ids": requirement_ids,
        "solver_status": {
            "results_status": solver_manifest.get("status"),
            "ready_for_writing": bool(solver_manifest.get("ready_for_writing")),
            "validation_status": validation.get("status"),
            "reproducibility_status": reproducibility.get("status"),
        },
        "gate": {"eligible": not hard, "reasons": list(dict.fromkeys(hard + reasons))},
    }
    paper_dir.mkdir(parents=True, exist_ok=True)
    write_json(paper_dir / "intake.yaml", intake)
    write_text(paper_dir / "paper-report.md", report(args.mode, status, intake["gate"]["reasons"]))
    if hard:
        print(f"STATUS: BLOCKED\nMODE: {args.mode}")
        for item in hard:
            print(f"ERROR: {item}")
        return 1

    sections = section_template(kind)
    result_claims = [item for item in solver_manifest.get("claims", []) if isinstance(item, dict) and item.get("id")]
    source_items: list[dict[str, Any]] = []
    index = 1
    for requirement in requirements:
        claim_id = f"claim-{index:03d}"
        source_items.append({
            "id": claim_id, "anchor": claim_id, "type": "requirement-answer", "importance": "core",
            "statement": f"回答 {requirement['id']}：{requirement.get('statement', '')}",
            "requirement_ids": [requirement["id"]], "section_id": None,
            "evidence_refs": [], "support_status": "needs-evidence", "boundary": None, "citation_keys": [],
        })
        index += 1
    for claim in result_claims:
        claim_id = f"claim-{index:03d}"
        source_items.append({
            "id": claim_id, "anchor": claim_id, "type": "result", "importance": "core",
            "statement": str(claim.get("statement", "")), "requirement_ids": [], "section_id": None,
            "evidence_refs": list(claim.get("evidence_refs", [])),
            "support_status": "bounded" if claim.get("limitations") else "supported",
            "boundary": "; ".join(str(item) for item in claim.get("limitations", [])) or None,
            "citation_keys": [],
        })
        index += 1
    terms: list[dict[str, Any]] = []
    spec = payloads.get("modeling/model-specification.yaml", {})
    for index, item in enumerate(spec.get("notation", []), start=1):
        if not isinstance(item, dict):
            continue
        terms.append({
            "id": f"term-{index:03d}", "canonical": item.get("definition") or item.get("symbol") or f"term-{index}",
            "kind": "variable", "symbol": item.get("symbol"), "unit": item.get("unit"),
            "definition": item.get("definition") or "[待补充定义]", "variants": [], "first_use": None, "status": "locked",
        })
    argument = {
        "schema_version": SCHEMA_VERSION, "mode": args.mode, "status": "DRAFT", "core_argument": None,
        "reader_focus": "竞赛评委需要快速确认题目回答、模型可信度、结果证据和适用边界。",
        "sections": [{"id": sid, "title": title, "purpose": purpose, "paragraph_jobs": [], "claim_ids": []} for sid, title, purpose in sections],
    }
    source_map = {"schema_version": SCHEMA_VERSION, "items": source_items, "citation_records": []}
    audit = {
        "schema_version": SCHEMA_VERSION,
        "checks": [{"dimension": dim, "status": "WARN" if dim in {"input_integrity", "claim_evidence"} else "NA", "evidence": ["paper/intake.yaml"], "findings": ["Writing package initialized; audit pending."], "required_actions": ["Complete manuscript evidence mapping and format review."]} for dim in AUDIT_DIMENSIONS],
        "overall_status": "NOT_READY",
    }
    write_json(paper_dir / "argument-map.yaml", argument)
    write_json(paper_dir / "terminology-ledger.yaml", {"schema_version": SCHEMA_VERSION, "terms": terms})
    write_json(paper_dir / "source-map.yaml", source_map)
    write_json(paper_dir / "writing-audit.yaml", audit)
    headings = "\n\n".join(f"## {title}\n\n[[Evidence-grounded content required]]" for _, title, _ in sections)
    anchors = "\n".join(f"<!-- claim: {item['anchor']} -->" for item in source_items)
    title = "[Paper title required]" if language != "zh" else "[论文标题待定]"
    write_text(paper_dir / "manuscript.md", f"# {title}\n\n{anchors}\n\n{headings}\n")
    write_text(paper_dir / "references.bib", "")
    print(f"STATUS: READY\nMODE: {args.mode}\nOUTPUT: {paper_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
