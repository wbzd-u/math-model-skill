#!/usr/bin/env python3
"""Validate modeling-selection intake, evidence, model specification, and solver contract."""

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
DOWNSTREAM_FILES = {
    "candidate-methods.yaml": "candidate-methods.schema.json",
    "model-decision.yaml": "model-decision.schema.json",
    "model-specification.yaml": "model-specification.schema.json",
    "validation-plan.yaml": "validation-plan.schema.json",
    "implementation-contract.yaml": "implementation-contract.schema.json",
    "modeling-selection-audit.yaml": "modeling-selection-audit.schema.json",
}
AUDIT_DIMENSIONS = {
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
}
ANALYSIS_AUDIT_DIMENSIONS = {
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
}
CRITICAL_ANALYSIS_DIMENSIONS = {
    "requirement_coverage",
    "source_traceability",
    "fact_assumption_separation",
    "scope_fidelity",
    "semantic_contract_completeness",
    "definition_impact_gating",
}
PLACEHOLDERS = {"[待填写]", "待填写", "todo", "tbd", "待定"}
FORBIDDEN_IMPLEMENTATION_KEYS = {
    "solver_code",
    "run_results",
    "numerical_results",
    "code",
    "results",
    "chosen_language",
    "programming_language",
    "implementation_language",
    "libraries",
    "dependencies",
    "run_command",
}
EXPLORATION_HARD_ERROR_MARKERS = {
    "intake-check.yaml:",
    "analysis_package.path",
    "must remain inside PROJECT_ROOT",
    "missing upstream analysis file",
    "cannot parse structured file",
    "upstream root must be an object",
    "upstream schema",
    "unsupported problem-analysis schema version",
    "does not match problem-profile.gate_status",
    "does not match problem profile",
    "does not match the recomputed upstream gate",
    "does not match the recomputed upstream scope",
    "does not match the recomputed handoff scope",
    "contains an unknown exploration scope",
    "upstream file changed after intake",
    "duplicate candidate IDs",
    "duplicate evidence IDs",
    "duplicate model component IDs",
    "duplicate notation IDs",
    "duplicate validation test IDs",
    "unknown",
    "outside the candidate scope",
    "candidate scope exceeds selected subproblems",
    "solver/run output is outside this module",
}
MODULE_ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_SCHEMA_ROOT = MODULE_ROOT.parent / "problem-analysis" / "schemas"


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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def as_dict_list(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def meaningful(value: Any) -> bool:
    if not isinstance(value, str) or len(value.strip()) < 3:
        return False
    lowered = value.strip().lower()
    return not any(marker in lowered for marker in PLACEHOLDERS)


def relax_for_exploration(
    errors: list[str], warnings: list[str]
) -> tuple[list[str], list[str], list[str]]:
    hard_errors: list[str] = []
    handoff_issues: list[str] = []
    for error in errors:
        if any(marker in error for marker in EXPLORATION_HARD_ERROR_MARKERS):
            hard_errors.append(error)
        else:
            handoff_issues.append(error)
    combined_warnings = [*warnings, *handoff_issues]
    return hard_errors, combined_warnings, handoff_issues


def find_forbidden_keys(value: Any, path: str = "$") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in FORBIDDEN_IMPLEMENTATION_KEYS:
                found.append(child_path)
            found.extend(find_forbidden_keys(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(find_forbidden_keys(child, f"{path}[{index}]"))
    return found


def duplicate_ids(items: list[dict[str, Any]], key: str = "id") -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for item in items:
        item_id = item.get(key)
        if isinstance(item_id, str) and item_id in seen:
            duplicates.add(item_id)
        elif isinstance(item_id, str):
            seen.add(item_id)
    return duplicates


def analysis_audit_ready(profile: dict[str, Any], analysis_audit: dict[str, Any]) -> bool:
    checks = as_dict_list(analysis_audit.get("checks"))
    critical_checks = {
        item.get("dimension"): item.get("status")
        for item in checks
        if item.get("dimension") in CRITICAL_ANALYSIS_DIMENSIONS
    }
    return (
        analysis_audit.get("overall_status") == profile.get("gate_status")
        and set(critical_checks) == CRITICAL_ANALYSIS_DIMENSIONS
        and all(status in {"PASS", "WARN"} for status in critical_checks.values())
    )


def derive_intake_scopes(
    profile: dict[str, Any],
    requirements: list[dict[str, Any]],
    subproblems: list[dict[str, Any]],
    ambiguities: list[dict[str, Any]],
    analysis_audit: dict[str, Any],
    selected_ids: set[str],
) -> tuple[str, list[str], list[str]]:
    """Recompute exploration and solver-handoff scopes from the handoff."""
    gate = profile.get("gate_status")
    open_ids = {
        item.get("id")
        for item in ambiguities
        if item.get("id") and item.get("status") != "resolved"
    }
    subproblem_ids = [item.get("id") for item in subproblems if item.get("id")]
    if not requirements or not subproblem_ids:
        return "BLOCKED", [], []
    unaffected = [
        item.get("id")
        for item in subproblems
        if item.get("id") and not (set(item.get("unresolved_ids", [])) & open_ids)
    ]
    audit_ready = analysis_audit_ready(profile, analysis_audit)
    handoff_allowed = unaffected if gate in {"PASS", "PASS_WITH_OPEN_ITEMS"} and audit_ready else []
    selection_status = (
        "PASS"
        if gate == "PASS"
        and audit_ready
        and not open_ids
        and selected_ids.issubset(set(handoff_allowed))
        else "EXPLORATORY"
    )
    return selection_status, subproblem_ids, handoff_allowed


def find_cycle(nodes: set[str], edges: list[dict[str, Any]]) -> bool:
    graph = {node: [] for node in nodes}
    for edge in edges:
        if edge.get("from") in graph and edge.get("to") in graph:
            graph[edge["from"]].append(edge["to"])
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        if any(visit(child) for child in graph[node]):
            return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(visit(node) for node in nodes)


def validate_json_schema(data: Any, schema_path: Path) -> list[str]:
    try:
        import jsonschema  # type: ignore
    except ImportError:
        return ["jsonschema is required for modeling-selection validation"]
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    errors: list[str] = []
    for error in sorted(validator.iter_errors(data), key=lambda item: list(item.path)):
        location = ".".join(str(part) for part in error.path) or "$"
        errors.append(f"{location}: {error.message}")
    return errors


def validate(project_root: Path, strict: bool) -> tuple[list[str], list[str], dict[str, float]]:
    module_root = Path(__file__).resolve().parents[1]
    schema_root = module_root / "schemas"
    modeling_dir = project_root / "modeling"
    errors: list[str] = []
    warnings: list[str] = []
    metrics: dict[str, float] = {}

    intake_path = modeling_dir / "intake-check.yaml"
    report_path = modeling_dir / "modeling-selection-report.md"
    if not intake_path.is_file():
        return [f"missing required file: {intake_path}"], warnings, metrics
    try:
        intake = load_structured(intake_path)
    except (OSError, ValueError) as exc:
        return [str(exc)], warnings, metrics
    errors.extend(f"intake-check.yaml: {error}" for error in validate_json_schema(intake, schema_root / "intake-check.schema.json"))
    if not isinstance(intake, dict):
        return errors + ["intake-check.yaml: root must be an object"], warnings, metrics

    analysis_rel = intake.get("analysis_package", {}).get("path", "analysis")
    if not isinstance(analysis_rel, str) or not analysis_rel:
        errors.append("intake analysis_package.path must be a non-empty relative path")
        analysis_dir = project_root / "analysis"
    else:
        analysis_dir = (project_root / analysis_rel).resolve()
        try:
            analysis_dir.relative_to(project_root)
        except ValueError:
            errors.append("intake analysis_package.path must remain inside PROJECT_ROOT")
            analysis_dir = project_root / "analysis"

    upstream: dict[str, dict[str, Any]] = {}
    for name in UPSTREAM_FILES:
        path = analysis_dir / name
        if not path.is_file():
            errors.append(f"missing upstream analysis file: {path}")
            continue
        try:
            payload = load_structured(path)
        except (OSError, ValueError) as exc:
            errors.append(str(exc))
            continue
        if not isinstance(payload, dict):
            errors.append(f"{name}: upstream root must be an object")
            continue
        schema_path = ANALYSIS_SCHEMA_ROOT / name.replace(".yaml", ".schema.json")
        for schema_error in validate_json_schema(payload, schema_path):
            errors.append(f"{name}: upstream schema: {schema_error}")
        upstream[name] = payload

    if len(upstream) < len(UPSTREAM_FILES):
        return errors, warnings, metrics
    if errors:
        return errors, warnings, metrics
    profile = upstream["problem-profile.yaml"]
    if profile.get("schema_version") != ANALYSIS_SCHEMA_VERSION:
        errors.append("upstream problem-analysis schema version must be 0.2.0")
    if intake.get("analysis_gate_status") != profile.get("gate_status"):
        errors.append("intake analysis_gate_status does not match problem-profile.gate_status")
    if intake.get("analysis_package", {}).get("project_id") != profile.get("project_id"):
        errors.append("intake analysis_package.project_id does not match problem profile")

    analysis_audit = upstream["analysis-audit.yaml"]
    if analysis_audit.get("overall_status") != profile.get("gate_status"):
        errors.append("analysis-audit overall_status must match problem-profile gate_status")
    if profile.get("gate_status") in {"PASS", "PASS_WITH_OPEN_ITEMS"}:
        upstream_audit_checks = as_dict_list(analysis_audit.get("checks"))
        upstream_audit_dimensions = {item.get("dimension") for item in upstream_audit_checks}
        if upstream_audit_dimensions != ANALYSIS_AUDIT_DIMENSIONS or len(upstream_audit_checks) != len(ANALYSIS_AUDIT_DIMENSIONS):
            warnings.append("problem-analysis audit is not a complete twelve-dimension review")
        critical_checks = {
            item.get("dimension"): item.get("status")
            for item in upstream_audit_checks
            if item.get("dimension") in CRITICAL_ANALYSIS_DIMENSIONS
        }
        if set(critical_checks) != CRITICAL_ANALYSIS_DIMENSIONS or any(
            status not in {"PASS", "WARN"} for status in critical_checks.values()
        ):
            errors.append("problem-analysis critical semantic audit checks are missing, NOT_RUN, or FAIL")
        if any(
            item.get("status") not in {"PASS", "WARN"}
            and item.get("dimension") not in CRITICAL_ANALYSIS_DIMENSIONS
            for item in upstream_audit_checks
        ):
            warnings.append("problem-analysis contains incomplete non-critical audit checks")
        if profile.get("gate_status") == "PASS" and any(item.get("status") != "PASS" for item in upstream_audit_checks):
            warnings.append("problem-analysis PASS contains WARN audit items")
        if not upstream["requirement-trace.yaml"].get("requirements") or not upstream["subproblems.yaml"].get("subproblems"):
            errors.append("passing problem-analysis handoff requires traced requirements and subproblems")

    if intake.get("analysis_package", {}).get("path") != "analysis":
        warnings.append("analysis package uses a non-default in-project path")

    selected_intake_ids = set(intake.get("selected_subproblem_ids", []))
    expected_selection_status, expected_allowed_ids, expected_handoff_ids = derive_intake_scopes(
        profile,
        as_dict_list(upstream["requirement-trace.yaml"].get("requirements")),
        as_dict_list(upstream["subproblems.yaml"].get("subproblems")),
        as_dict_list(upstream["ambiguity-register.yaml"].get("items")),
        analysis_audit,
        selected_intake_ids,
    )
    if intake.get("selection_intake_status") != expected_selection_status:
        errors.append("intake selection_intake_status does not match the recomputed upstream gate")
    if set(intake.get("allowed_subproblem_ids", [])) != set(expected_allowed_ids):
        errors.append("intake allowed_subproblem_ids does not match the recomputed upstream scope")
    if set(intake.get("handoff_allowed_subproblem_ids", [])) != set(expected_handoff_ids):
        errors.append("intake handoff_allowed_subproblem_ids does not match the recomputed handoff scope")
    if not selected_intake_ids.issubset(set(expected_allowed_ids)):
        errors.append("intake selected_subproblem_ids contains an unknown exploration scope")
    if not selected_intake_ids.issubset(set(expected_handoff_ids)):
        warnings.append("selected scope contains open items and is exploratory only")

    consumed = {item.get("path"): item.get("sha256") for item in intake.get("analysis_package", {}).get("consumed_file_hashes", [])}
    hash_ok = True
    for name in UPSTREAM_FILES:
        path = analysis_dir / name
        relative = str(path.relative_to(project_root))
        actual = sha256_file(path)
        if consumed.get(relative) != actual:
            errors.append(f"upstream file changed after intake: {relative}")
            hash_ok = False
    metrics["upstream_hash_integrity"] = 1.0 if hash_ok else 0.0

    if intake.get("selection_intake_status") == "BLOCKED":
        if any((modeling_dir / name).is_file() for name in DOWNSTREAM_FILES):
            errors.append("BLOCKED intake must not contain downstream candidate/model files")
        if not report_path.is_file():
            warnings.append(f"missing blocked intake report: {report_path}")
        elif strict and "[待填写]" in report_path.read_text(encoding="utf-8-sig"):
            warnings.append("blocked intake report contains placeholders")
        metrics.update({
            "selected_requirement_coverage": 0.0,
            "selected_difficulty_coverage": 0.0,
            "candidate_scope_coverage": 0.0,
            "model_component_coverage": 0.0,
            "validation_component_coverage": 0.0,
            "contract_scope_coverage": 0.0,
            "audit_completion": 0.0,
        })
        if strict:
            errors.append("handoff mode cannot use a BLOCKED modeling-selection intake")
        return errors, warnings, metrics

    loaded: dict[str, dict[str, Any]] = {}
    for name, schema_name in DOWNSTREAM_FILES.items():
        path = modeling_dir / name
        if not path.is_file():
            errors.append(f"missing required file: {path}")
            continue
        try:
            payload = load_structured(path)
        except (OSError, ValueError) as exc:
            errors.append(str(exc))
            continue
        for schema_error in validate_json_schema(payload, schema_root / schema_name):
            errors.append(f"{name}: {schema_error}")
        if isinstance(payload, dict):
            loaded[name] = payload
            for forbidden in find_forbidden_keys(payload):
                errors.append(f"{name}: solver/run output is outside this module at {forbidden}")
    if not report_path.is_file():
        warnings.append(f"missing modeling-selection report: {report_path}")
    elif strict and "[待填写]" in report_path.read_text(encoding="utf-8-sig"):
        warnings.append("modeling-selection-report.md still contains placeholders")
    if len(loaded) < len(DOWNSTREAM_FILES):
        return errors, warnings, metrics

    candidate_payload = loaded["candidate-methods.yaml"]
    decision_payload = loaded["model-decision.yaml"]
    specification_payload = loaded["model-specification.yaml"]
    validation_payload = loaded["validation-plan.yaml"]
    contract_payload = loaded["implementation-contract.yaml"]
    audit_payload = loaded["modeling-selection-audit.yaml"]
    draft_scope = intake.get("selected_subproblem_ids", [])
    draft_checks = as_dict_list(audit_payload.get("checks"))
    initialized_exploration = (
        candidate_payload.get("knowledge_status") == "not-searched"
        and candidate_payload.get("evidence_records") == []
        and candidate_payload.get("candidates") == []
        and candidate_payload.get("comparison_exception") is None
        and decision_payload.get("status") in {"DRAFT", "EXPLORATORY"}
        and decision_payload.get("scope_subproblem_ids") == draft_scope
        and decision_payload.get("main_candidate_ids") == []
        and decision_payload.get("baseline_candidate_ids") == []
        and decision_payload.get("alternative_candidate_ids") == []
        and decision_payload.get("comparisons") == []
        and decision_payload.get("coverage") == {
            "requirement_ids": [],
            "difficulty_refs": [],
            "subproblem_ids": draft_scope,
        }
        and specification_payload.get("status") in {"DRAFT", "EXPLORATORY"}
        and specification_payload.get("scope_subproblem_ids") == draft_scope
        and specification_payload.get("notation") == []
        and specification_payload.get("new_assumptions") == []
        and specification_payload.get("components") == []
        and specification_payload.get("model_chain") == {"nodes": [], "edges": []}
        and specification_payload.get("immutable_semantics") == []
        and validation_payload.get("status") in {"DRAFT", "EXPLORATORY"}
        and validation_payload.get("tests") == []
        and validation_payload.get("coverage") == {
            "component_ids": [],
            "difficulty_refs": [],
            "requirement_ids": [],
        }
        and contract_payload.get("status") in {"DRAFT", "EXPLORATORY"}
        and contract_payload.get("contract_id") == "contract-pending"
        and contract_payload.get("scope_subproblem_ids") == draft_scope
        and contract_payload.get("approved_component_ids") == []
        and contract_payload.get("parameters") == []
        and contract_payload.get("execution_stages") == []
        and contract_payload.get("required_outputs") == []
        and contract_payload.get("validation_test_ids") == []
        and contract_payload.get("immutable_items") == []
        and contract_payload.get("solver_discretion") == []
        and contract_payload.get("input_snapshot") == {
            "intake_sha256": "0" * 64,
            "model_spec_sha256": "0" * 64,
            "validation_plan_sha256": "0" * 64,
        }
        and audit_payload.get("overall_status") in {"DRAFT", "EXPLORATORY"}
        and {item.get("dimension") for item in draft_checks} == AUDIT_DIMENSIONS
        and len(draft_checks) == len(AUDIT_DIMENSIONS)
        and all(
            item.get("status") == "NOT_RUN"
            and item.get("evidence") == []
            and item.get("findings") == []
            and item.get("required_actions") == []
            for item in draft_checks
        )
    )
    if initialized_exploration and not strict:
        metrics.update({
            "selected_requirement_coverage": 0.0,
            "selected_difficulty_coverage": 0.0,
            "candidate_scope_coverage": 0.0,
            "model_component_coverage": 0.0,
            "validation_component_coverage": 0.0,
            "contract_scope_coverage": 0.0,
            "audit_completion": 0.0,
        })
        errors.append("modeling-selection package is initialized for exploration and is not ready for solver handoff")
        return errors, warnings, metrics

    # Schema and upstream-integrity errors are sufficient to reject the
    # package.  Stop here so malformed values cannot cause secondary crashes.
    if errors:
        return errors, warnings, metrics

    requirements = as_dict_list(upstream["requirement-trace.yaml"].get("requirements"))
    subproblems = as_dict_list(upstream["subproblems.yaml"].get("subproblems"))
    variables = as_dict_list(upstream["entity-variable-map.yaml"].get("variables"))
    datasets = as_dict_list(upstream["data-inventory.yaml"].get("datasets"))
    requirement_ids = {item.get("id") for item in requirements}
    requirement_by_id = {item.get("id"): item for item in requirements}
    subproblem_by_id = {item.get("id"): item for item in subproblems}
    subproblem_ids = set(subproblem_by_id)
    variable_ids = {item.get("id") for item in variables}
    data_ids = {item.get("id") for item in datasets}
    selected_ids = set(intake.get("selected_subproblem_ids", []))
    allowed_ids = set(intake.get("allowed_subproblem_ids", []))
    if not selected_ids <= allowed_ids or not selected_ids <= subproblem_ids:
        errors.append("selected_subproblem_ids must be a subset of allowed and existing subproblems")
    if intake.get("selection_intake_status") == "CONDITIONAL":
        for subproblem_id in selected_ids:
            unresolved = set(subproblem_by_id[subproblem_id].get("unresolved_ids", []))
            if unresolved:
                errors.append(f"conditional intake cannot select subproblem with unresolved ambiguities: {subproblem_id}")

    candidates = as_dict_list(candidate_payload.get("candidates"))
    evidence = as_dict_list(candidate_payload.get("evidence_records"))
    duplicate_candidate_ids = duplicate_ids(candidates)
    duplicate_evidence_ids = duplicate_ids(evidence)
    if duplicate_candidate_ids:
        errors.append(f"duplicate candidate IDs: {sorted(duplicate_candidate_ids)}")
    if duplicate_evidence_ids:
        errors.append(f"duplicate evidence IDs: {sorted(duplicate_evidence_ids)}")
    candidate_by_id = {item.get("id"): item for item in candidates}
    evidence_ids = {item.get("id") for item in evidence}
    for candidate in candidates:
        candidate_id = candidate.get("id")
        scope = set(candidate.get("subproblem_ids", []))
        if not scope <= selected_ids:
            errors.append(f"{candidate_id}: candidate scope exceeds selected subproblems")
        missing_requirements = set(candidate.get("requirement_ids", [])) - requirement_ids
        if missing_requirements:
            errors.append(f"{candidate_id}: unknown requirement references {sorted(missing_requirements)}")
        for requirement_id in set(candidate.get("requirement_ids", [])) & requirement_ids:
            if not (set(requirement_by_id[requirement_id].get("subproblem_ids", [])) & scope):
                errors.append(f"{candidate_id}: requirement {requirement_id} is outside the candidate scope")
        for data_id in candidate.get("data_ids", []):
            if data_id not in data_ids:
                errors.append(f"{candidate_id}: unknown data reference {data_id}")
        for evidence_id in set(candidate.get("evidence_ids", [])) - evidence_ids:
            errors.append(f"{candidate_id}: unknown evidence reference {evidence_id}")
        for stage in as_dict_list(candidate.get("chain_roles")):
            for evidence_id in set(stage.get("evidence_ids", [])) - evidence_ids:
                errors.append(f"{candidate_id}/{stage.get('id')}: unknown evidence reference {evidence_id}")
        for difficulty_ref in candidate.get("difficulty_refs", []):
            parts = difficulty_ref.split(":")
            if len(parts) != 2 or parts[0] not in subproblem_by_id or not any(driver.get("id") == parts[1] for driver in subproblem_by_id[parts[0]].get("difficulty_drivers", [])):
                errors.append(f"{candidate_id}: unknown difficulty reference {difficulty_ref}")
            elif parts[0] not in scope:
                errors.append(f"{candidate_id}: difficulty {difficulty_ref} is outside the candidate scope")

    decision = decision_payload
    main_candidate_ids = set(decision.get("main_candidate_ids", []))
    baseline_candidate_ids = set(decision.get("baseline_candidate_ids", []))
    alternative_candidate_ids = set(decision.get("alternative_candidate_ids", []))
    decision_candidate_ids = main_candidate_ids | baseline_candidate_ids | alternative_candidate_ids
    role_overlap = (
        (main_candidate_ids & baseline_candidate_ids)
        | (main_candidate_ids & alternative_candidate_ids)
        | (baseline_candidate_ids & alternative_candidate_ids)
    )
    if role_overlap:
        warnings.append(f"candidate roles overlap; confirm that the shared route has a distinct role: {sorted(role_overlap)}")
    for role_name in ("main_candidate_ids", "baseline_candidate_ids", "alternative_candidate_ids"):
        values = decision.get(role_name, [])
        if len(values) != len(set(values)):
            warnings.append(f"model-decision {role_name} contains duplicates")
    for candidate_id in decision_candidate_ids:
        if candidate_id not in candidate_by_id:
            errors.append(f"model-decision references unknown candidate {candidate_id}")
        elif candidate_by_id[candidate_id].get("status") != "selected":
            errors.append(f"model-decision candidate {candidate_id} must have status selected")
    if set(decision.get("scope_subproblem_ids", [])) != selected_ids:
        errors.append("model-decision scope must exactly match intake selected_subproblem_ids")
    if set(decision.get("coverage", {}).get("subproblem_ids", [])) != selected_ids:
        errors.append("model-decision coverage.subproblem_ids must exactly match selected scope")
    comparisons = as_dict_list(decision.get("comparisons"))
    duplicate_comparison_dimensions = duplicate_ids(comparisons, key="dimension")
    if duplicate_comparison_dimensions:
        warnings.append(f"duplicate comparison dimensions: {sorted(duplicate_comparison_dimensions)}")
    for comparison in comparisons:
        assessments = as_dict_list(comparison.get("assessments"))
        duplicate_assessment_ids = duplicate_ids(assessments, key="candidate_id")
        if duplicate_assessment_ids:
            warnings.append(f"comparison {comparison.get('dimension')} repeats candidates {sorted(duplicate_assessment_ids)}")
        assessed_ids = {assessment.get("candidate_id") for assessment in assessments}
        if decision_candidate_ids and assessed_ids != decision_candidate_ids:
            warnings.append(f"comparison {comparison.get('dimension')} does not assess every selected role candidate")
        for assessment in assessments:
            if assessment.get("candidate_id") not in candidate_by_id:
                errors.append(f"comparison references unknown candidate {assessment.get('candidate_id')}")
    coverage_requirements = set(decision.get("coverage", {}).get("requirement_ids", []))
    coverage_difficulties = set(decision.get("coverage", {}).get("difficulty_refs", []))
    if not coverage_requirements <= requirement_ids:
        errors.append("model-decision coverage contains unknown requirement IDs")

    relevant_requirements = {
        requirement.get("id")
        for requirement in requirements
        if set(requirement.get("subproblem_ids", [])) & selected_ids
    }
    main_candidate_requirements = set()
    for candidate_id in decision.get("main_candidate_ids", []):
        main_candidate_requirements.update(candidate_by_id.get(candidate_id, {}).get("requirement_ids", []))
    requirement_coverage_ok = relevant_requirements <= coverage_requirements and relevant_requirements <= main_candidate_requirements
    if not requirement_coverage_ok:
        errors.append("main candidates and model decision do not cover every selected requirement")

    main_candidate_scope = {
        subproblem_id
        for candidate_id in decision.get("main_candidate_ids", [])
        for subproblem_id in candidate_by_id.get(candidate_id, {}).get("subproblem_ids", [])
    }
    if decision.get("main_candidate_ids") and not selected_ids <= main_candidate_scope:
        errors.append("main candidate set does not cover every selected subproblem")
    baseline_candidate_scope = {
        subproblem_id
        for candidate_id in decision.get("baseline_candidate_ids", [])
        for subproblem_id in candidate_by_id.get(candidate_id, {}).get("subproblem_ids", [])
    }
    if decision.get("baseline_candidate_ids") and not selected_ids <= baseline_candidate_scope:
        warnings.append("baseline candidate set covers only part of the selected scope")

    relevant_difficulties = {
        f"{subproblem_id}:{driver.get('id')}"
        for subproblem_id in selected_ids
        for driver in subproblem_by_id[subproblem_id].get("difficulty_drivers", [])
    }
    main_candidate_difficulties = set()
    for candidate_id in decision.get("main_candidate_ids", []):
        main_candidate_difficulties.update(candidate_by_id.get(candidate_id, {}).get("difficulty_refs", []))

    spec = specification_payload
    components = as_dict_list(spec.get("components"))
    duplicate_component_ids = duplicate_ids(components)
    duplicate_notation_ids = duplicate_ids(as_dict_list(spec.get("notation")))
    if duplicate_component_ids:
        errors.append(f"duplicate model component IDs: {sorted(duplicate_component_ids)}")
    if duplicate_notation_ids:
        errors.append(f"duplicate notation IDs: {sorted(duplicate_notation_ids)}")
    component_by_id = {item.get("id"): item for item in components}
    for component in components:
        component_id = component.get("id")
        if component.get("candidate_id") not in candidate_by_id:
            errors.append(f"{component_id}: unknown candidate reference")
        expected_candidates = {
            "main": set(decision.get("main_candidate_ids", [])),
            "baseline": set(decision.get("baseline_candidate_ids", [])),
            "alternative": set(decision.get("alternative_candidate_ids", [])),
        }.get(component.get("role"))
        if expected_candidates is not None and component.get("candidate_id") not in expected_candidates:
            errors.append(f"{component_id}: component role does not match model-decision candidate role")
        if not set(component.get("subproblem_ids", [])) <= selected_ids:
            errors.append(f"{component_id}: component scope exceeds selected subproblems")
        for variable_id in set(component.get("input_variable_ids", [])) | set(component.get("output_variable_ids", [])):
            if variable_id not in variable_ids and not variable_id.startswith("dvar-"):
                errors.append(f"{component_id}: unknown variable reference {variable_id}")
        for upstream_component_id in component.get("upstream_component_ids", []):
            if upstream_component_id not in component_by_id:
                errors.append(f"{component_id}: unknown upstream component {upstream_component_id}")
    model_nodes = set(spec.get("model_chain", {}).get("nodes", []))
    if model_nodes != set(component_by_id):
        errors.append("model_chain.nodes must exactly match model component IDs")
    if find_cycle(set(component_by_id), as_dict_list(spec.get("model_chain", {}).get("edges"))):
        warnings.append("model specification chain contains a cycle; document iteration, convergence, or termination")
    for edge in as_dict_list(spec.get("model_chain", {}).get("edges")):
        if edge.get("from") not in component_by_id or edge.get("to") not in component_by_id:
            errors.append("model specification chain contains an edge with an unknown component")
    for notation in as_dict_list(spec.get("notation")):
        source_id = notation.get("source_variable_id")
        if source_id not in variable_ids and not source_id.startswith("dvar-"):
            errors.append(f"notation references unknown source variable {source_id}")

    main_components = [component for component in components if component.get("role") == "main"]
    main_component_ids = {component.get("id") for component in main_components}
    main_component_scope = {subproblem_id for component in main_components for subproblem_id in component.get("subproblem_ids", [])}
    model_component_coverage_ok = selected_ids <= main_component_scope
    if not model_component_coverage_ok:
        errors.append("model specification lacks a main component for every selected subproblem")

    validation = validation_payload
    tests = as_dict_list(validation.get("tests"))
    duplicate_test_ids = duplicate_ids(tests)
    if duplicate_test_ids:
        errors.append(f"duplicate validation test IDs: {sorted(duplicate_test_ids)}")
    test_ids = {item.get("id") for item in tests}
    for test in tests:
        missing_components = set(test.get("component_ids", [])) - set(component_by_id)
        if missing_components:
            errors.append(f"{test.get('id')}: unknown component references {sorted(missing_components)}")
        if not set(test.get("subproblem_ids", [])) <= selected_ids:
            errors.append(f"{test.get('id')}: validation scope exceeds selected subproblems")
    covered_components = {component_id for test in tests for component_id in test.get("component_ids", [])}
    validation_component_coverage_ok = main_component_ids <= covered_components and bool(main_component_ids)
    if not validation_component_coverage_ok:
        errors.append("validation plan does not cover every main model component")
    if validation.get("status") == "READY" and not {test.get("type") for test in tests} & {"constraint-check", "error", "sensitivity", "robustness", "uncertainty", "boundary", "adversarial"}:
        warnings.append("READY validation plan has no risk-oriented, error, sensitivity, or constraint test")
    validation_coverage = validation.get("coverage", {})
    if set(validation_coverage.get("component_ids", [])) != covered_components:
        warnings.append("validation coverage.component_ids differs from components referenced by tests")
    scientific_requirement_ids = {
        item.get("id")
        for item in requirements
        if item.get("id") in relevant_requirements
        and item.get("category") in {"objective", "constraint", "evaluation"}
    }
    if not scientific_requirement_ids <= set(validation_coverage.get("requirement_ids", [])):
        errors.append("validation plan does not cover every scientific objective, constraint, or evaluation requirement")
    if not relevant_difficulties <= set(validation_coverage.get("difficulty_refs", [])):
        errors.append("validation plan does not cover every selected structural difficulty")
    difficulty_coverage_ok = (
        relevant_difficulties <= coverage_difficulties
        and relevant_difficulties
        <= (main_candidate_difficulties | set(validation_coverage.get("difficulty_refs", [])))
    )
    if not difficulty_coverage_ok:
        errors.append("main candidates or validation do not cover every selected structural difficulty")

    contract = contract_payload
    contract_components = set(contract.get("approved_component_ids", []))
    if len(contract.get("approved_component_ids", [])) != len(contract_components):
        errors.append("implementation contract approved_component_ids contains duplicates")
    if not contract_components <= set(component_by_id):
        errors.append("implementation contract references unknown components")
    if set(contract.get("scope_subproblem_ids", [])) != selected_ids:
        errors.append("implementation contract scope must exactly match selected subproblems")
    contract_test_ids = set(contract.get("validation_test_ids", []))
    if len(contract.get("validation_test_ids", [])) != len(contract_test_ids):
        errors.append("implementation contract validation_test_ids contains duplicates")
    if not contract_test_ids <= test_ids:
        errors.append("implementation contract references unknown validation tests")
    main_validation_test_ids = {
        test.get("id")
        for test in tests
        if set(test.get("component_ids", [])) & main_component_ids
    }
    if contract.get("status") == "READY" and not main_validation_test_ids <= contract_test_ids:
        errors.append("READY implementation contract omits validation tests for a main model component")
    if contract.get("status") == "READY" and contract_test_ids != test_ids:
        warnings.append("READY implementation contract omits some exploratory or secondary validation tests")
    output_requirement_ids = {req_id for output in as_dict_list(contract.get("required_outputs")) for req_id in output.get("acceptance_requirement_ids", [])}
    if not output_requirement_ids <= requirement_ids:
        errors.append("implementation contract references unknown output requirements")
    if not relevant_requirements <= output_requirement_ids:
        errors.append("implementation contract outputs do not cover every selected requirement")
    output_subproblem_ids = {
        subproblem_id
        for output in as_dict_list(contract.get("required_outputs"))
        for subproblem_id in output.get("subproblem_ids", [])
    }
    if not selected_ids <= output_subproblem_ids:
        errors.append("implementation contract outputs do not cover every selected subproblem")
    execution_component_list = [
        component_id
        for stage in as_dict_list(contract.get("execution_stages"))
        for component_id in stage.get("component_ids", [])
    ]
    execution_component_ids = set(execution_component_list)
    duplicate_execution_components = {
        component_id
        for component_id in execution_component_ids
        if execution_component_list.count(component_id) > 1
    }
    if duplicate_execution_components:
        warnings.append(f"implementation contract schedules iterative components more than once: {sorted(duplicate_execution_components)}")
    if not execution_component_ids <= set(component_by_id):
        errors.append("implementation contract execution stages reference unknown components")
    if contract.get("status") == "READY" and not main_component_ids <= execution_component_ids:
        errors.append("READY implementation contract must schedule every main model component")

    route_audit = decision.get("route_audit") if isinstance(decision.get("route_audit"), dict) else {}
    route_audit_status = route_audit.get("status")
    route_audit_items = as_dict_list(route_audit.get("items"))
    if route_audit_status == "audited":
        duplicate_route_audit_ids = duplicate_ids(route_audit_items)
        if duplicate_route_audit_ids:
            errors.append(f"route audit contains duplicate item IDs: {sorted(duplicate_route_audit_ids)}")
        audited_main_ids = {item.get("main_candidate_id") for item in route_audit_items}
        if audited_main_ids != main_candidate_ids:
            errors.append("route audit must cover every selected main candidate exactly once")
        stage_by_id = {stage.get("id"): stage for stage in as_dict_list(contract.get("execution_stages"))}
        test_by_id = {test.get("id"): test for test in tests}
        feedback_triggers = set(contract.get("feedback_policy", {}).get("triggers", []))
        for item in route_audit_items:
            item_id = item.get("id", "<unnamed>")
            main_candidate_id = item.get("main_candidate_id")
            simpler_candidate_id = item.get("simpler_candidate_id")
            if main_candidate_id not in main_candidate_ids:
                errors.append(f"{item_id}: route audit references a candidate that is not a selected main route")
                continue
            if simpler_candidate_id is not None and simpler_candidate_id not in candidate_by_id:
                errors.append(f"{item_id}: route audit references an unknown simpler candidate")
            main_candidate_components = {
                component_id
                for component_id, component in component_by_id.items()
                if component.get("candidate_id") == main_candidate_id
            }
            deciding_test = test_by_id.get(item.get("deciding_test_id"))
            if deciding_test is None:
                errors.append(f"{item_id}: route audit references an unknown deciding test")
            elif not main_candidate_components & set(deciding_test.get("component_ids", [])):
                errors.append(f"{item_id}: deciding test does not exercise the audited main candidate")
            elif deciding_test.get("failure_action") not in {"revise-model", "solver-diagnostic", "return-to-analysis"}:
                errors.append(f"{item_id}: deciding test must feed failure back to modeling or diagnostics")
            execution_stage = stage_by_id.get(item.get("first_execution_stage_id"))
            if execution_stage is None:
                errors.append(f"{item_id}: route audit references an unknown first execution stage")
            elif not main_candidate_components & set(execution_stage.get("component_ids", [])):
                errors.append(f"{item_id}: first execution stage does not schedule the audited main candidate")
            if item.get("feedback_trigger") not in feedback_triggers:
                errors.append(f"{item_id}: feedback trigger is not declared by the implementation contract")
    elif route_audit_status == "not-needed":
        if route_audit_items:
            errors.append("route audit marked not-needed must not contain audit items")
    else:
        errors.append("route audit must declare whether an audit is needed")

    spec_immutable_refs = {
        item.get("source_ref")
        for item in as_dict_list(spec.get("immutable_semantics"))
    }
    contract_immutable_refs = {
        item.get("source_ref")
        for item in as_dict_list(contract.get("immutable_items"))
    }
    if not spec_immutable_refs <= contract_immutable_refs:
        errors.append("implementation contract does not preserve every model-specification immutable semantic")
    input_snapshot = contract.get("input_snapshot", {})
    if input_snapshot.get("intake_sha256") != sha256_file(intake_path):
        errors.append("implementation contract intake snapshot does not match current intake file")
    spec_path = modeling_dir / "model-specification.yaml"
    validation_path = modeling_dir / "validation-plan.yaml"
    if input_snapshot.get("model_spec_sha256") != sha256_file(spec_path):
        errors.append("implementation contract model specification snapshot does not match")
    if input_snapshot.get("validation_plan_sha256") != sha256_file(validation_path):
        errors.append("implementation contract validation snapshot does not match")
    required_component_ids = main_component_ids
    contract_scope_coverage_ok = (
        set(contract.get("scope_subproblem_ids", [])) == selected_ids
        and required_component_ids <= contract_components
        and bool(contract_components)
    )
    if not contract_scope_coverage_ok:
        errors.append("implementation contract does not cover selected scope")

    audit = audit_payload
    audit_checks = as_dict_list(audit.get("checks"))
    duplicate_audit_dimensions = duplicate_ids(audit_checks, key="dimension")
    if duplicate_audit_dimensions:
        warnings.append(f"duplicate modeling-selection audit dimensions: {sorted(duplicate_audit_dimensions)}")
    audit_dimensions = {item.get("dimension") for item in audit_checks}
    if audit_dimensions != AUDIT_DIMENSIONS:
        warnings.append(f"modeling-selection audit dimensions are incomplete: missing={sorted(AUDIT_DIMENSIONS - audit_dimensions)}, extra={sorted(audit_dimensions - AUDIT_DIMENSIONS)}")
    audit_completion = sum(1 for item in audit_checks if item.get("status") != "NOT_RUN") / len(AUDIT_DIMENSIONS) if audit_checks else 0.0
    metrics.update({
        "selected_requirement_coverage": 1.0 if requirement_coverage_ok else 0.0,
        "selected_difficulty_coverage": 1.0 if difficulty_coverage_ok else 0.0,
        "candidate_scope_coverage": 1.0 if all(set(candidate.get("subproblem_ids", [])) <= selected_ids for candidate in candidates) else 0.0,
        "model_component_coverage": 1.0 if model_component_coverage_ok else 0.0,
        "validation_component_coverage": 1.0 if validation_component_coverage_ok else 0.0,
        "contract_scope_coverage": 1.0 if contract_scope_coverage_ok else 0.0,
        "route_audit_linkage": 1.0 if route_audit_status in {"not-needed", "audited"} and not any("route audit" in error for error in errors) else 0.0,
        "audit_completion": audit_completion,
    })

    if strict:
        handoff_allowed_ids = set(intake.get("handoff_allowed_subproblem_ids", []))
        if not selected_ids or not selected_ids <= handoff_allowed_ids:
            errors.append("handoff mode requires every selected subproblem to be in handoff_allowed_subproblem_ids")
        if not report_path.is_file() or "[待填写]" in report_path.read_text(encoding="utf-8-sig"):
            warnings.append("handoff report is missing or still contains placeholders")
        if not candidates:
            errors.append("handoff mode requires at least one candidate method chain")
        if not 2 <= len(candidates) <= 4 and not meaningful(candidate_payload.get("comparison_exception")):
            warnings.append("consider documenting why the candidate set is outside the usual two-to-four range")
        if candidate_payload.get("knowledge_status") == "not-searched":
            warnings.append("knowledge sources were not searched; record none-available when no source exists")
        if decision.get("status") != "READY":
            errors.append("handoff mode requires model-decision status READY")
        if not decision.get("main_candidate_ids"):
            errors.append("handoff mode requires a main candidate")
        if not decision.get("baseline_candidate_ids") and not meaningful(decision.get("baseline_exception")):
            warnings.append("no baseline is defined; document the limitation when comparison is not useful")
        if not decision.get("alternative_candidate_ids") and not meaningful(decision.get("alternative_exception")):
            warnings.append("no fallback route is defined; document the risk when no alternative is useful")
        if len(decision_candidate_ids) > 1 and not comparisons:
            warnings.append("multiple candidates are selected without a common comparison")
        if spec.get("status") != "READY":
            errors.append("handoff mode requires model-specification status READY")
        if validation.get("status") != "READY":
            errors.append("handoff mode requires validation-plan status READY")
        if contract.get("status") != "READY":
            errors.append("handoff mode requires implementation-contract status READY")
        if not spec.get("immutable_semantics") or not contract.get("immutable_items"):
            errors.append("handoff mode requires immutable model semantics in the implementation contract")
        if not contract.get("solver_discretion"):
            errors.append("handoff mode requires an explicit solver discretion boundary")
        if audit.get("overall_status") not in {"PASS", "PASS_WITH_OPEN_ITEMS"}:
            warnings.append("modeling-selection audit is not marked PASS; rely on concrete validator findings")
        critical_modeling_dimensions = {
            "semantic_fidelity",
            "model_specification_completeness",
            "assumption_discipline",
            "validation_executability",
            "implementation_contract_consistency",
            "solver_boundary",
        }
        if any(
            item.get("dimension") in critical_modeling_dimensions and item.get("status") == "FAIL"
            for item in audit_checks
        ):
            errors.append("handoff mode cannot ignore a FAIL in a critical scientific audit dimension")
        if any(item.get("status") == "NOT_RUN" for item in audit_checks):
            warnings.append("some modeling-selection audit checks were not run")
    elif audit.get("overall_status") in {"DRAFT", "EXPLORATORY"}:
        warnings.append("modeling-selection audit remains exploratory")

    return errors, warnings, metrics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--mode", choices=["explore", "handoff"], default="explore")
    parser.add_argument("--strict", action="store_true", help="compatibility alias for --mode handoff")
    parser.add_argument("--json", action="store_true", dest="json_output")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = Path(args.project_root).expanduser().resolve()
    mode = "handoff" if args.strict else args.mode
    errors, warnings, metrics = validate(project_root, mode == "handoff")
    handoff_issues: list[str] = []
    if mode == "explore":
        errors, warnings, handoff_issues = relax_for_exploration(errors, warnings)
    status = "FAIL" if errors else "PASS"
    intake_status = None
    try:
        intake = load_structured(project_root / "modeling" / "intake-check.yaml")
        if isinstance(intake, dict):
            intake_status = intake.get("selection_intake_status")
    except (OSError, ValueError):
        pass
    if not errors and intake_status == "BLOCKED":
        status = "BLOCKED"
    elif not errors and mode == "explore":
        status = "EXPLORATORY"
    ready_for_solver = mode == "handoff" and not errors and intake_status != "BLOCKED"
    payload = {
        "status": status,
        "mode": mode,
        "ready_for_solver": ready_for_solver,
        "metrics": metrics,
        "errors": errors,
        "handoff_issues": handoff_issues,
        "warnings": warnings,
    }
    if args.json_output:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"STATUS: {status}")
        print(f"MODE: {mode}")
        print(f"READY_FOR_SOLVER: {str(ready_for_solver).lower()}")
        for name, value in metrics.items():
            print(f"METRIC: {name}={value:.3f}")
        for warning in warnings:
            print(f"WARNING: {warning}")
        for error in errors:
            print(f"ERROR: {error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
