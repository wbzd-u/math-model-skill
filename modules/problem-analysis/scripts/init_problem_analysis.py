#!/usr/bin/env python3
"""Initialize a deterministic problem-analysis handoff package."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


SCHEMA_VERSION = "0.2.0"
ROLES = {"problem", "data", "rules", "supplement", "user-note"}
AUDIT_DIMENSIONS = [
    "requirement_coverage",
    "source_traceability",
    "entity_consistency",
    "subproblem_completeness",
    "data_alignment",
    "dependency_consistency",
    "fact_assumption_separation",
    "scope_fidelity",
    "method_leakage",
    "semantic_contract_completeness",
    "structural_difficulty",
    "definition_impact_gating",
]


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "math-modeling-project"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_source(raw: str, index: int) -> dict[str, object]:
    role = "problem" if index == 1 else "supplement"
    path_text = raw
    if "=" in raw:
        candidate, remainder = raw.split("=", 1)
        if candidate in ROLES:
            role = candidate
            path_text = remainder

    path = Path(path_text).expanduser().resolve()
    return {
        "id": f"src-{index:03d}",
        "path": str(path),
        "sha256": sha256_file(path) if path.is_file() else None,
        "role": role,
    }


def write_json_yaml(path: Path, payload: object, force: bool) -> str:
    existed = path.exists()
    if existed and not force:
        return "skipped"
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return "written" if existed else "created"


def write_text(path: Path, content: str, force: bool) -> str:
    existed = path.exists()
    if existed and not force:
        return "skipped"
    path.write_text(content, encoding="utf-8")
    return "written" if existed else "created"


def build_payloads(args: argparse.Namespace, sources: list[dict[str, object]]) -> dict[str, object]:
    project_id = args.project_id or slugify(Path(args.project_root).name or args.title)
    return {
        "problem-profile.yaml": {
            "schema_version": SCHEMA_VERSION,
            "project_id": project_id,
            "title": args.title,
            "competition": {
                "type": args.competition,
                "year": args.year,
                "problem_id": args.problem_id,
                "rules_sources": [],
            },
            "scope": args.scope,
            "source_files": sources,
            "objectives": [],
            "deliverables": [],
            "task_tags": [],
            "gate_status": "DRAFT",
        },
        "requirement-trace.yaml": {
            "schema_version": SCHEMA_VERSION,
            "requirements": [],
        },
        "data-inventory.yaml": {
            "schema_version": SCHEMA_VERSION,
            "datasets": [],
        },
        "entity-variable-map.yaml": {
            "schema_version": SCHEMA_VERSION,
            "entities": [],
            "variables": [],
        },
        "subproblems.yaml": {
            "schema_version": SCHEMA_VERSION,
            "subproblems": [],
        },
        "data-task-matrix.yaml": {
            "schema_version": SCHEMA_VERSION,
            "mappings": [],
        },
        "dependency-graph.yaml": {
            "schema_version": SCHEMA_VERSION,
            "nodes": [],
            "edges": [],
        },
        "ambiguity-register.yaml": {
            "schema_version": SCHEMA_VERSION,
            "items": [],
        },
        "assumption-register.yaml": {
            "schema_version": SCHEMA_VERSION,
            "items": [],
        },
        "analysis-audit.yaml": {
            "schema_version": SCHEMA_VERSION,
            "checks": [
                {
                    "dimension": dimension,
                    "status": "NOT_RUN",
                    "evidence": [],
                    "findings": [],
                    "required_actions": [],
                }
                for dimension in AUDIT_DIMENSIONS
            ],
            "overall_status": "DRAFT",
        },
    }


REPORT_TEMPLATE = """# 题目分析报告

## 1. 范围与竞赛信息

[待填写]

## 2. 输入与数据概览

[待填写]

## 3. 题目要求追踪

[待填写]

## 4. 实体、变量与量纲

[待填写]

## 5. 子问题拆解、语义契约与依赖

[待填写]

## 6. 结构压力测试与核心难点

[待填写]

## 7. 数据与子问题对齐

[待填写]

## 8. 目标、约束、评价标准与交付物

[待填写]

## 9. 歧义、竞争性解释、数据风险与待验证假设

[待填写]

## 10. 对抗性审查与阶段门禁

- 结论：DRAFT
- 阻塞项：[待填写]
- 可交接风险：[待填写]
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--project-id")
    parser.add_argument(
        "--competition",
        choices=["cumcm", "mcm", "icm", "generic", "unknown"],
        default="unknown",
    )
    parser.add_argument("--year", type=int)
    parser.add_argument("--problem-id")
    parser.add_argument("--scope", default="full-problem")
    parser.add_argument(
        "--source",
        action="append",
        default=[],
        help="Source path, optionally prefixed with role= (for example problem=task.pdf)",
    )
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = Path(args.project_root).expanduser().resolve()
    analysis_dir = project_root / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)

    sources = [parse_source(raw, index) for index, raw in enumerate(args.source, 1)]
    payloads = build_payloads(args, sources)

    for name, payload in payloads.items():
        status = write_json_yaml(analysis_dir / name, payload, args.force)
        print(f"{status.upper():7} {analysis_dir / name}")

    report_path = analysis_dir / "problem-analysis-report.md"
    status = write_text(report_path, REPORT_TEMPLATE, args.force)
    print(f"{status.upper():7} {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
