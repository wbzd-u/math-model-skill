#!/usr/bin/env python3
"""Initialize a modeling-selection package from a problem-analysis handoff."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "0.1.0"
ANALYSIS_SCHEMA_VERSION = "0.2.0"
UPSTREAM_FILES = [
    "problem-profile.yaml",
    "requirement-trace.yaml",
    "data-inventory.yaml",
    "entity-variable-map.yaml",
    "subproblems.yaml",
    "data-task-matrix.yaml",
    "dependency-graph.yaml",
    "ambiguity-register.yaml",
    "assumption-register.yaml",
    "analysis-audit.yaml",
]
AUDIT_DIMENSIONS = [
    "intake_gate",
    "upstream_traceability",
    "evidence_quality",
    "candidate_coverage",
    "comparison_fairness",
    "semantic_fidelity",
    "model_specification_completeness",
    "assumption_discipline",
    "validation_executability",
    "implementation_contract_consistency",
    "solver_boundary",
    "method_bloat",
]
CRITICAL_ANALYSIS_DIMENSIONS = {
    "requirement_coverage",
    "source_traceability",
    "fact_assumption_separation",
    "scope_fidelity",
    "semantic_contract_completeness",
    "definition_impact_gating",
}
MODULE_ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_SCHEMA_ROOT = MODULE_ROOT.parent / "problem-analysis" / "schemas"
DOWNSTREAM_FILES = [
    "candidate-methods.yaml",
    "model-decision.yaml",
    "model-specification.yaml",
    "validation-plan.yaml",
    "implementation-contract.yaml",
    "modeling-selection-audit.yaml",
]


def load_structured(path: Path) -> Any:
    text = path.read_text(encoding="utf-8-sig")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        try:
            import yaml  # type: ignore
            return yaml.safe_load(text)
        except Exception as exc:  # YAML parser exceptions vary by implementation.
            raise ValueError(f"cannot parse structured file {path}: {exc}") from exc


def validate_json_schema(data: Any, schema_path: Path) -> list[str]:
    try:
        import jsonschema  # type: ignore
    except ImportError as exc:
        raise ValueError("jsonschema is required for modeling-selection initialization") from exc
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"missing problem-analysis schema: {schema_path}") from exc
    validator = jsonschema.Draft202012Validator(schema)
    errors: list[str] = []
    for error in sorted(validator.iter_errors(data), key=lambda item: list(item.path)):
        location = ".".join(str(part) for part in error.path) or "$"
        errors.append(f"{location}: {error.message}")
    return errors


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: object, force: bool) -> str:
    if path.exists() and not force:
        return "skipped"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return "written"


def write_text(path: Path, content: str, force: bool) -> str:
    if path.exists() and not force:
        return "skipped"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return "written"


def report_template(status: str, blocked_items: list[dict[str, Any]]) -> str:
    if status == "BLOCKED":
        lines = [
            "# 方法选择与模型设计准入报告",
            "",
            "## 结论",
            "",
            "`BLOCKED`：当前材料尚未形成可探索的要求与子问题定义。",
            "",
            "## 必须补充或裁决",
            "",
        ]
        for item in blocked_items:
            lines.append(f"- `{item['id']}`（{item['kind']}）：{item['statement']}；来源：{item['source_ref']}")
        lines.extend([
            "",
            "先补齐最基本的问题定义，再重新运行 `init_modeling_selection.py`。",
            "",
        ])
        return "\n".join(lines)
    if status == "EXPLORATORY":
        lines = [
            "# 方法选择与模型设计报告",
            "",
            "## 1. 准入与范围",
            "",
            "`EXPLORATORY`：允许提出分支解释、候选路线和诊断性验证，但当前不能正式交给 solver。",
            "",
            "### 当前开放项",
            "",
        ]
        if blocked_items:
            for item in blocked_items:
                lines.append(f"- `{item['id']}`（{item['kind']}）：{item['statement']}；来源：{item['source_ref']}")
        else:
            lines.append("- 当前没有硬阻断项，但交接条件尚未全部满足。")
        lines.extend([
            "",
            "探索时必须把不同解释、暂定假设和适用范围分别记录，不得把它们写成题面事实。",
            "",
            "## 2. 结构化证据与知识缺口",
            "",
            "[待填写]",
            "",
            "## 3. 候选方法链与比较",
            "",
            "[待填写]",
            "",
            "## 4. 模型规格与假设",
            "",
            "[待填写]",
            "",
            "## 5. 诊断性验证与实施契约",
            "",
            "[待填写]",
            "",
            "## 6. 当前结论与升级条件",
            "",
            "[待填写]",
            "",
        ])
        return "\n".join(lines)
    return """# 方法选择与模型设计报告

## 1. 准入与范围

[待填写]

## 2. 结构化证据与知识缺口

[待填写]

## 3. 候选方法链与比较

[待填写]

## 4. 模型规格与假设

[待填写]

## 5. 验证计划与实施契约

[待填写]

## 6. 审计与阶段门禁

[待填写]
"""


def build_payloads(
    project_root: Path,
    analysis_dir: Path,
    profile: dict[str, Any],
    subproblems: list[dict[str, Any]],
    ambiguities: list[dict[str, Any]],
    gate_status: str,
    selected_ids: list[str],
    definition_available: bool,
    audit_ready: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    relative_hashes = []
    for name in UPSTREAM_FILES:
        path = analysis_dir / name
        relative_path = str(path.relative_to(project_root))
        relative_hashes.append({"path": relative_path, "sha256": sha256_file(path)})

    blocking_items = []
    conditional_items = []
    for ambiguity in ambiguities:
        status = ambiguity.get("status")
        affected = ambiguity.get("affected_subproblem_ids", [])
        item = {
            "id": ambiguity.get("id"),
            "kind": "ambiguity",
            "statement": ambiguity.get("statement", ""),
            "source_ref": ambiguity.get("source_ref", ""),
        }
        # A resolved definition issue remains useful provenance, but it must not
        # block a new selection intake.  The upstream analysis gate is the
        # authoritative status; this check only mirrors unresolved items.
        if status == "blocking" or (ambiguity.get("definition_impact") is True and status != "resolved"):
            blocking_items.append(item)
        elif status not in {"resolved"}:
            conditional_items.append({"id": ambiguity.get("id"), "statement": ambiguity.get("statement", ""), "affected_subproblem_ids": affected})

    all_ids = [item.get("id") for item in subproblems if item.get("id")]
    open_ids = {item.get("id") for item in ambiguities if item.get("status") != "resolved"}
    unaffected_ids = [
        item.get("id")
        for item in subproblems
        if item.get("id") and not (set(item.get("unresolved_ids", [])) & open_ids)
    ]

    allowed_ids = all_ids if definition_available else []
    if gate_status == "PASS" and audit_ready:
        handoff_allowed_ids = unaffected_ids
    elif gate_status == "PASS_WITH_OPEN_ITEMS" and audit_ready:
        handoff_allowed_ids = unaffected_ids
    else:
        handoff_allowed_ids = []

    if not definition_available or not all_ids:
        selection_status = "BLOCKED"
        selected_ids = []
        blocking_items.append({
            "id": "problem-definition-missing",
            "kind": "scope",
            "statement": "当前缺少可定位的题目要求或子问题，无法形成最小探索闭环。",
            "source_ref": "analysis/requirement-trace.yaml;analysis/subproblems.yaml",
        })
    else:
        selected_ids = selected_ids or allowed_ids
        selection_status = (
            "PASS"
            if gate_status == "PASS"
            and audit_ready
            and set(selected_ids).issubset(set(handoff_allowed_ids))
            and not blocking_items
            and not conditional_items
            else "EXPLORATORY"
        )

    if gate_status in {"DRAFT", "BLOCKED"}:
        blocking_items.append({
            "id": "analysis-gate",
            "kind": "audit",
            "statement": f"上游题目分析状态为 {gate_status}；可以探索，但不能正式交接。",
            "source_ref": "analysis/problem-profile.yaml",
        })
    if not audit_ready:
        blocking_items.append({
            "id": "analysis-audit-open",
            "kind": "audit",
            "statement": "上游审计尚未达到正式交接条件；探索结论必须保留条件和风险。",
            "source_ref": "analysis/analysis-audit.yaml",
        })

    intake = {
        "schema_version": SCHEMA_VERSION,
        "analysis_package": {
            "path": str(analysis_dir.relative_to(project_root)),
            "project_id": profile.get("project_id", ""),
            "schema_version": profile.get("schema_version"),
            "consumed_file_hashes": relative_hashes,
        },
        "analysis_gate_status": gate_status,
        "selection_intake_status": selection_status,
        "selected_subproblem_ids": selected_ids,
        "allowed_subproblem_ids": allowed_ids,
        "handoff_allowed_subproblem_ids": handoff_allowed_ids,
        "blocked_items": blocking_items,
        "conditional_items": conditional_items,
    }
    audit = {
        "schema_version": SCHEMA_VERSION,
        "checks": [
            {"dimension": dimension, "status": "NOT_RUN", "evidence": [], "findings": [], "required_actions": []}
            for dimension in AUDIT_DIMENSIONS
        ],
        "overall_status": "EXPLORATORY",
    }
    return intake, audit


def empty_payloads(intake: dict[str, Any], audit: dict[str, Any]) -> dict[str, Any]:
    scope = intake["selected_subproblem_ids"]
    return {
        "candidate-methods.yaml": {"schema_version": SCHEMA_VERSION, "knowledge_status": "not-searched", "evidence_records": [], "candidates": [], "comparison_exception": None},
        "model-decision.yaml": {"schema_version": SCHEMA_VERSION, "status": "EXPLORATORY", "scope_subproblem_ids": scope, "main_candidate_ids": [], "baseline_candidate_ids": [], "alternative_candidate_ids": [], "baseline_exception": None, "alternative_exception": None, "comparisons": [], "coverage": {"requirement_ids": [], "difficulty_refs": [], "subproblem_ids": scope}, "decision_rationale": "当前处于探索阶段，尚未确定正式模型。", "residual_risks": [], "route_audit": {"status": "not-needed", "rationale": "尚未选定主路线；完成候选比较后判断是否需要审计复杂升级、验证与回退。", "items": []}},
        "model-specification.yaml": {"schema_version": SCHEMA_VERSION, "status": "EXPLORATORY", "scope_subproblem_ids": scope, "notation": [], "new_assumptions": [], "components": [], "model_chain": {"nodes": [], "edges": []}, "immutable_semantics": []},
        "validation-plan.yaml": {"schema_version": SCHEMA_VERSION, "status": "EXPLORATORY", "tests": [], "coverage": {"component_ids": [], "difficulty_refs": [], "requirement_ids": []}},
        "implementation-contract.yaml": {"schema_version": SCHEMA_VERSION, "status": "EXPLORATORY", "contract_id": "contract-pending", "input_snapshot": {"intake_sha256": "0" * 64, "model_spec_sha256": "0" * 64, "validation_plan_sha256": "0" * 64}, "scope_subproblem_ids": scope, "approved_component_ids": [], "parameters": [], "execution_stages": [], "required_outputs": [], "validation_test_ids": [], "immutable_items": [], "solver_discretion": [], "feedback_policy": {"path": "solver/modeling-feedback.yaml", "triggers": ["不可实现", "约束冲突", "数据不足", "诊断结果否定当前结构假说"], "required_evidence": ["错误信息或诊断结果", "输入和参数", "复现命令"]}},
        "modeling-selection-audit.yaml": audit,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--subproblem", action="append", default=[])
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = Path(args.project_root).expanduser().resolve()
    analysis_dir = project_root / "analysis"
    modeling_dir = project_root / "modeling"
    existing_outputs = [
        modeling_dir / name
        for name in ["intake-check.yaml", "modeling-selection-report.md", *DOWNSTREAM_FILES]
        if (modeling_dir / name).exists()
    ]
    if existing_outputs and not args.force:
        print(
            "ERROR: modeling output already exists; use --force to reinitialize: "
            + ", ".join(path.name for path in existing_outputs)
        )
        return 1
    missing = [name for name in UPSTREAM_FILES if not (analysis_dir / name).is_file()]
    if missing:
        print("ERROR: missing upstream analysis files: " + ", ".join(missing))
        return 1

    loaded: dict[str, Any] = {}
    for name in UPSTREAM_FILES:
        try:
            payload = load_structured(analysis_dir / name)
        except (OSError, ValueError) as exc:
            print(f"ERROR: {exc}")
            return 1
        if not isinstance(payload, dict):
            print(f"ERROR: {name} root must be an object")
            return 1
        schema_path = ANALYSIS_SCHEMA_ROOT / name.replace(".yaml", ".schema.json")
        try:
            schema_errors = validate_json_schema(payload, schema_path)
        except ValueError as exc:
            print(f"ERROR: {exc}")
            return 1
        if schema_errors:
            print(f"ERROR: invalid upstream {name}: " + " | ".join(schema_errors[:8]))
            return 1
        loaded[name] = payload
    profile = loaded["problem-profile.yaml"]
    if profile.get("schema_version") != ANALYSIS_SCHEMA_VERSION:
        print(f"ERROR: unsupported problem-analysis schema version: {profile.get('schema_version')}")
        return 1
    subproblems = loaded["subproblems.yaml"].get("subproblems", [])
    requirements = loaded["requirement-trace.yaml"].get("requirements", [])
    ambiguities = loaded["ambiguity-register.yaml"].get("items", [])
    requested = list(dict.fromkeys(args.subproblem))
    known_ids = {item.get("id") for item in subproblems}
    unknown_requested = set(requested) - known_ids
    if unknown_requested:
        print("ERROR: unknown requested subproblems: " + ", ".join(sorted(unknown_requested)))
        return 1

    gate_status = profile.get("gate_status", "DRAFT")
    if gate_status not in {"DRAFT", "PASS", "PASS_WITH_OPEN_ITEMS", "BLOCKED"}:
        print(f"ERROR: unsupported problem-analysis gate status: {gate_status}")
        return 1
    analysis_audit = loaded["analysis-audit.yaml"]
    audit_checks = analysis_audit.get("checks", [])
    critical_audit_checks = {
        item.get("dimension"): item.get("status")
        for item in audit_checks
        if isinstance(item, dict) and item.get("dimension") in CRITICAL_ANALYSIS_DIMENSIONS
    }
    audit_ready = (
        analysis_audit.get("overall_status") == gate_status
        and set(critical_audit_checks) == CRITICAL_ANALYSIS_DIMENSIONS
        and all(status in {"PASS", "WARN"} for status in critical_audit_checks.values())
    )

    intake, audit = build_payloads(
        project_root,
        analysis_dir,
        profile,
        subproblems,
        ambiguities,
        gate_status,
        requested,
        definition_available=bool(requirements and subproblems),
        audit_ready=audit_ready,
    )
    modeling_dir.mkdir(parents=True, exist_ok=True)
    if args.force and intake["selection_intake_status"] == "BLOCKED":
        for name in DOWNSTREAM_FILES:
            stale = modeling_dir / name
            if stale.exists():
                stale.unlink()
    print(write_json(modeling_dir / "intake-check.yaml", intake, args.force).upper(), modeling_dir / "intake-check.yaml")
    report = report_template(intake["selection_intake_status"], intake["blocked_items"])
    print(write_text(modeling_dir / "modeling-selection-report.md", report, args.force).upper(), modeling_dir / "modeling-selection-report.md")

    if intake["selection_intake_status"] == "BLOCKED":
        print("INFO: minimum problem definition is unavailable; downstream files were not initialized")
        return 0

    if intake["selection_intake_status"] == "EXPLORATORY":
        print("INFO: exploratory modeling is allowed; handoff issues remain open")

    payloads = empty_payloads(intake, audit)
    for name, payload in payloads.items():
        print(write_json(modeling_dir / name, payload, args.force).upper(), modeling_dir / name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
