#!/usr/bin/env python3
"""Validate completeness, structural depth, and handoff safety of problem-analysis artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "0.2.0"
STRUCTURED_FILES = {
    "problem-profile.yaml": "problem-profile.schema.json",
    "requirement-trace.yaml": "requirement-trace.schema.json",
    "data-inventory.yaml": "data-inventory.schema.json",
    "entity-variable-map.yaml": "entity-variable-map.schema.json",
    "subproblems.yaml": "subproblems.schema.json",
    "data-task-matrix.yaml": "data-task-matrix.schema.json",
    "dependency-graph.yaml": "dependency-graph.schema.json",
    "ambiguity-register.yaml": "ambiguity-register.schema.json",
    "assumption-register.yaml": "assumption-register.schema.json",
    "analysis-audit.yaml": "analysis-audit.schema.json",
}
FORBIDDEN_KEYS = {"selected_model", "selected_method", "algorithm_choice", "solver"}
AUDIT_DIMENSIONS = {
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
TASK_TAGS = {
    "prediction",
    "evaluation",
    "optimization",
    "classification",
    "simulation",
    "network",
    "mechanism",
    "policy-analysis",
    "uncertainty-analysis",
}
STRUCTURAL_TASK_TAGS = {
    "mechanism",
    "simulation",
    "optimization",
    "network",
    "policy-analysis",
    "uncertainty-analysis",
}
TEXT_CONTRACT_FIELDS = {
    "state_or_event_relation",
    "information_timing",
    "success_predicate",
    "evaluation_aggregation",
    "feasibility_summary",
    "boundary_or_termination",
}
PLACEHOLDER_MARKERS = {"[待填写]", "待填写", "todo", "tbd", "待定", "migration_required"}


def load_structured(path: Path) -> Any:
    text = path.read_text(encoding="utf-8-sig")
    try:
        return json.loads(text)
    except json.JSONDecodeError as json_error:
        try:
            import yaml  # type: ignore
        except ImportError as exc:
            raise ValueError(
                f"{path.name} is not JSON-compatible YAML and PyYAML is unavailable: {json_error}"
            ) from exc
        return yaml.safe_load(text)


def find_forbidden_keys(value: Any, path: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in FORBIDDEN_KEYS:
                findings.append(child_path)
            findings.extend(find_forbidden_keys(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(find_forbidden_keys(child, f"{path}[{index}]"))
    return findings


def as_dict_list(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


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


def coverage(items: list[dict[str, Any]], predicate: Any) -> float:
    if not items:
        return 0.0
    return sum(1 for item in items if predicate(item)) / len(items)


def meaningful_text(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    text = value.strip()
    if len(text) < 3:
        return False
    lowered = text.lower()
    return not any(marker in lowered for marker in PLACEHOLDER_MARKERS)


def find_cycle(nodes: set[str], edges: list[dict[str, Any]]) -> bool:
    graph = {node: [] for node in nodes}
    for edge in edges:
        source, target = edge.get("from"), edge.get("to")
        if source in graph and target in nodes:
            graph[source].append(target)

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
        return [
            "jsonschema is required for v0.2.0 validation; install it rather than using a partial fallback"
        ]

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    errors = []
    for error in sorted(validator.iter_errors(data), key=lambda item: list(item.path)):
        location = ".".join(str(part) for part in error.path) or "$"
        errors.append(f"{location}: {error.message}")
    return errors


def semantic_contract_complete(subproblem: dict[str, Any]) -> bool:
    contract = subproblem.get("semantic_contract")
    if not isinstance(contract, dict):
        return False
    if not all(meaningful_text(contract.get(field)) for field in TEXT_CONTRACT_FIELDS):
        return False
    return bool(as_dict_list(contract.get("acceptance_tests")))


def structural_driver_complete(subproblem: dict[str, Any]) -> bool:
    drivers = as_dict_list(subproblem.get("difficulty_drivers"))
    if not 1 <= len(drivers) <= 3:
        return False
    return all(
        meaningful_text(driver.get("statement"))
        and meaningful_text(driver.get("why_it_changes_problem"))
        and meaningful_text(driver.get("omission_consequence"))
        and bool(driver.get("evidence_refs"))
        and bool(driver.get("affected_dimensions"))
        for driver in drivers
    )


def task_gate_errors(subproblem: dict[str, Any], variable_by_id: dict[str, dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    subproblem_id = subproblem.get("id", "<unknown>")
    tags = set(subproblem.get("task_tags", []))
    contract = subproblem.get("semantic_contract")
    if not isinstance(contract, dict):
        return [f"{subproblem_id}: missing semantic_contract"]

    controllable = contract.get("controllable_variable_ids", [])
    outcomes = contract.get("outcome_variable_ids", [])
    couplings = as_dict_list(contract.get("couplings"))
    drivers = as_dict_list(subproblem.get("difficulty_drivers"))

    if tags & {"optimization", "policy-analysis"}:
        if not controllable:
            errors.append(f"{subproblem_id}: {sorted(tags & {'optimization', 'policy-analysis'})} requires a controllable variable")
        if not meaningful_text(contract.get("feasibility_summary")):
            errors.append(f"{subproblem_id}: optimization or policy task requires a feasibility summary")
    if "prediction" in tags or "classification" in tags:
        if not outcomes:
            errors.append(f"{subproblem_id}: prediction or classification task requires an outcome variable")
        if not meaningful_text(contract.get("information_timing")):
            errors.append(f"{subproblem_id}: prediction or classification task requires information timing")
    if tags & {"mechanism", "simulation"}:
        if not meaningful_text(contract.get("state_or_event_relation")):
            errors.append(f"{subproblem_id}: mechanism or simulation task requires state/event semantics")
        if not meaningful_text(contract.get("boundary_or_termination")):
            errors.append(f"{subproblem_id}: mechanism or simulation task requires a boundary or termination condition")
    if "evaluation" in tags:
        if not meaningful_text(contract.get("success_predicate")):
            errors.append(f"{subproblem_id}: evaluation task requires a success predicate")
        if not meaningful_text(contract.get("evaluation_aggregation")):
            errors.append(f"{subproblem_id}: evaluation task requires an aggregation rule")
    if "uncertainty-analysis" in tags and not any(
        driver.get("type") in {"uncertainty", "identifiability"} for driver in drivers
    ):
        errors.append(f"{subproblem_id}: uncertainty-analysis requires an uncertainty or identifiability driver")
    if "network" in tags and not any(
        coupling.get("type") in {"network", "resource", "information"} for coupling in couplings
    ):
        errors.append(f"{subproblem_id}: network task requires a network, resource, or information coupling")
    if tags & STRUCTURAL_TASK_TAGS and not structural_driver_complete(subproblem):
        errors.append(f"{subproblem_id}: structural task requires one to three evidence-backed difficulty drivers")

    for variable_id in controllable:
        variable = variable_by_id.get(variable_id)
        if variable and variable.get("role") != "controllable":
            errors.append(f"{subproblem_id}: {variable_id} is not a controllable variable")
    for variable_id in outcomes:
        variable = variable_by_id.get(variable_id)
        if variable and variable.get("role") != "outcome":
            errors.append(f"{subproblem_id}: {variable_id} is not an outcome variable")
    return errors


def validate(
    project_root: Path, strict: bool
) -> tuple[list[str], list[str], dict[str, float]]:
    module_root = Path(__file__).resolve().parents[1]
    schema_root = module_root / "schemas"
    analysis_dir = project_root / "analysis"
    errors: list[str] = []
    warnings: list[str] = []
    metrics: dict[str, float] = {}
    loaded: dict[str, dict[str, Any]] = {}

    for name, schema_name in STRUCTURED_FILES.items():
        path = analysis_dir / name
        if not path.is_file():
            errors.append(f"missing required file: {path}")
            continue
        try:
            data = load_structured(path)
        except (OSError, ValueError) as exc:
            errors.append(str(exc))
            continue
        for schema_error in validate_json_schema(data, schema_root / schema_name):
            errors.append(f"{name}: {schema_error}")
        if not isinstance(data, dict):
            errors.append(f"{name}: root value must be an object")
            continue
        loaded[name] = data
        for forbidden in find_forbidden_keys(data):
            errors.append(f"{name}: downstream method-selection key is forbidden at {forbidden}")

    report_path = analysis_dir / "problem-analysis-report.md"
    if not report_path.is_file():
        errors.append(f"missing required file: {report_path}")
    elif strict and "[待填写]" in report_path.read_text(encoding="utf-8-sig"):
        errors.append("problem-analysis-report.md still contains [待填写] placeholders")

    if len(loaded) < len(STRUCTURED_FILES):
        return errors, warnings, metrics

    profile = loaded["problem-profile.yaml"]
    requirements = as_dict_list(loaded["requirement-trace.yaml"].get("requirements"))
    datasets = as_dict_list(loaded["data-inventory.yaml"].get("datasets"))
    entity_map = loaded["entity-variable-map.yaml"]
    entities = as_dict_list(entity_map.get("entities"))
    variables = as_dict_list(entity_map.get("variables"))
    subproblems = as_dict_list(loaded["subproblems.yaml"].get("subproblems"))
    mappings = as_dict_list(loaded["data-task-matrix.yaml"].get("mappings"))
    graph = loaded["dependency-graph.yaml"]
    ambiguities = as_dict_list(loaded["ambiguity-register.yaml"].get("items"))
    assumptions = as_dict_list(loaded["assumption-register.yaml"].get("items"))
    audit = loaded["analysis-audit.yaml"]
    audit_checks = as_dict_list(audit.get("checks"))

    collections = {
        "requirements": requirements,
        "datasets": datasets,
        "entities": entities,
        "variables": variables,
        "subproblems": subproblems,
        "ambiguities": ambiguities,
        "assumptions": assumptions,
    }
    for label, items in collections.items():
        duplicates = duplicate_ids(items)
        if duplicates:
            errors.append(f"duplicate {label} IDs: {', '.join(sorted(duplicates))}")
    duplicate_mappings = duplicate_ids(mappings, "subproblem_id")
    if duplicate_mappings:
        errors.append(f"duplicate data-task mappings: {', '.join(sorted(duplicate_mappings))}")
    duplicate_audits = duplicate_ids(audit_checks, "dimension")
    if duplicate_audits:
        errors.append(f"duplicate audit dimensions: {', '.join(sorted(duplicate_audits))}")

    requirement_ids = {item.get("id") for item in requirements}
    dataset_ids = {item.get("id") for item in datasets}
    entity_ids = {item.get("id") for item in entities}
    variable_by_id = {item.get("id"): item for item in variables if isinstance(item.get("id"), str)}
    subproblem_ids = {item.get("id") for item in subproblems}
    ambiguity_by_id = {item.get("id"): item for item in ambiguities if isinstance(item.get("id"), str)}
    mapping_ids = {item.get("subproblem_id") for item in mappings}
    graph_nodes = set(graph.get("nodes", [])) if isinstance(graph.get("nodes"), list) else set()

    for item in requirements:
        missing = set(item.get("subproblem_ids", [])) - subproblem_ids
        if missing:
            errors.append(f"{item.get('id')}: unknown subproblem references {sorted(missing)}")

    for variable in variables:
        missing_entities = set(variable.get("entity_ids", [])) - entity_ids
        missing_data = set(variable.get("data_ids", [])) - dataset_ids
        if missing_entities:
            errors.append(f"{variable.get('id')}: unknown entity references {sorted(missing_entities)}")
        if missing_data:
            errors.append(f"{variable.get('id')}: unknown data references {sorted(missing_data)}")

    incoming: dict[str, set[str]] = {item_id: set() for item_id in subproblem_ids}
    for edge in as_dict_list(graph.get("edges")):
        source, target = edge.get("from"), edge.get("to")
        if source not in subproblem_ids or target not in subproblem_ids:
            errors.append(f"dependency edge has unknown endpoint: {edge}")
        elif target in incoming:
            incoming[target].add(source)

    profile_tags = set(profile.get("task_tags", []))
    profile_specific_tags = profile_tags - {"mixed"}
    if strict and "mixed" in profile_tags and not profile_specific_tags:
        errors.append("strict mode requires mixed to be accompanied by at least one concrete task tag")
    if strict and subproblems and not profile_specific_tags:
        errors.append("strict mode requires problem-profile.task_tags to include concrete task tags")

    task_tag_gate_results: list[bool] = []
    semantic_results: list[bool] = []
    structural_results: list[bool] = []
    unresolved_by_subproblem: dict[str, set[str]] = {}
    for item in subproblems:
        subproblem_id = item.get("id")
        missing_requirements = set(item.get("source_requirement_ids", [])) - requirement_ids
        missing_upstream = set(item.get("upstream_ids", [])) - subproblem_ids
        missing_ambiguities = set(item.get("unresolved_ids", [])) - set(ambiguity_by_id)
        if missing_requirements:
            errors.append(f"{subproblem_id}: unknown requirement references {sorted(missing_requirements)}")
        if missing_upstream:
            errors.append(f"{subproblem_id}: unknown upstream references {sorted(missing_upstream)}")
        if missing_ambiguities:
            errors.append(f"{subproblem_id}: unknown ambiguity references {sorted(missing_ambiguities)}")
        if set(item.get("upstream_ids", [])) != incoming.get(subproblem_id, set()):
            errors.append(f"{subproblem_id}: upstream_ids must exactly match dependency-graph incoming edges")
        unresolved_by_subproblem[str(subproblem_id)] = set(item.get("unresolved_ids", []))

        subproblem_tags = set(item.get("task_tags", []))
        if not subproblem_tags <= TASK_TAGS:
            errors.append(f"{subproblem_id}: contains unknown task tags {sorted(subproblem_tags - TASK_TAGS)}")
        if not subproblem_tags <= profile_specific_tags:
            errors.append(f"{subproblem_id}: task tags must be declared by problem-profile.task_tags")

        contract = item.get("semantic_contract")
        contract_errors: list[str] = []
        if not isinstance(contract, dict):
            contract_errors.append(f"{subproblem_id}: semantic_contract must be an object")
        else:
            for field in TEXT_CONTRACT_FIELDS:
                if not meaningful_text(contract.get(field)):
                    contract_errors.append(f"{subproblem_id}: semantic_contract.{field} must be meaningful")
            for field in ("exogenous_or_given_variable_ids", "controllable_variable_ids", "outcome_variable_ids"):
                for variable_id in contract.get(field, []):
                    if variable_id not in variable_by_id:
                        contract_errors.append(f"{subproblem_id}: {field} references unknown variable {variable_id}")
            for coupling in as_dict_list(contract.get("couplings")):
                for variable_id in coupling.get("affected_variable_ids", []):
                    if variable_id not in variable_by_id:
                        contract_errors.append(f"{subproblem_id}: coupling references unknown variable {variable_id}")
                for affected_subproblem_id in coupling.get("affected_subproblem_ids", []):
                    if affected_subproblem_id not in subproblem_ids:
                        contract_errors.append(f"{subproblem_id}: coupling references unknown subproblem {affected_subproblem_id}")
            for acceptance_test in as_dict_list(contract.get("acceptance_tests")):
                missing_requirements = set(acceptance_test.get("source_requirement_ids", [])) - requirement_ids
                if missing_requirements:
                    contract_errors.append(f"{subproblem_id}: acceptance test references unknown requirements {sorted(missing_requirements)}")

        drivers = as_dict_list(item.get("difficulty_drivers"))
        duplicate_driver_ids = duplicate_ids(drivers)
        if duplicate_driver_ids:
            contract_errors.append(f"{subproblem_id}: duplicate difficulty IDs {sorted(duplicate_driver_ids)}")
        for driver in drivers:
            for variable_id in driver.get("affected_variable_ids", []):
                if variable_id not in variable_by_id:
                    contract_errors.append(f"{subproblem_id}: difficulty driver references unknown variable {variable_id}")
            for affected_subproblem_id in driver.get("affected_subproblem_ids", []):
                if affected_subproblem_id not in subproblem_ids:
                    contract_errors.append(f"{subproblem_id}: difficulty driver references unknown subproblem {affected_subproblem_id}")

        semantic_results.append(not contract_errors and semantic_contract_complete(item))
        errors.extend(contract_errors)
        task_errors = task_gate_errors(item, variable_by_id)
        task_tag_gate_results.append(not task_errors and subproblem_tags <= profile_specific_tags)
        if strict:
            errors.extend(task_errors)
            for field in ("inputs", "objectives", "constraints", "evaluation_criteria"):
                if not all(meaningful_text(value) for value in item.get(field, [])):
                    errors.append(f"{subproblem_id}: strict mode requires meaningful {field}")

        if subproblem_tags & STRUCTURAL_TASK_TAGS:
            structural_results.append(structural_driver_complete(item))

    for mapping in mappings:
        subproblem_id = mapping.get("subproblem_id")
        if subproblem_id not in subproblem_ids:
            errors.append(f"data-task matrix references unknown subproblem {subproblem_id}")
        for need in as_dict_list(mapping.get("needs")):
            missing_data = set(need.get("data_ids", [])) - dataset_ids
            if missing_data:
                errors.append(f"{subproblem_id}: unknown data references {sorted(missing_data)}")

    for item in assumptions:
        missing = set(item.get("affected_subproblems", [])) - subproblem_ids
        if missing:
            errors.append(f"{item.get('id')}: unknown affected subproblems {sorted(missing)}")

    if graph_nodes != subproblem_ids:
        errors.append(
            "dependency-graph nodes must exactly match subproblem IDs: "
            f"nodes={sorted(graph_nodes)}, subproblems={sorted(subproblem_ids)}"
        )
    if find_cycle(subproblem_ids, as_dict_list(graph.get("edges"))):
        errors.append("dependency graph contains a cycle")

    definition_checks: list[bool] = []
    has_blocking_ambiguity = False
    for ambiguity_id, item in ambiguity_by_id.items():
        affected = set(item.get("affected_subproblem_ids", []))
        missing_affected = affected - subproblem_ids
        if missing_affected:
            errors.append(f"{ambiguity_id}: unknown affected subproblems {sorted(missing_affected)}")
        status = item.get("status")
        definition_impact = item.get("definition_impact") is True
        if status == "blocking":
            has_blocking_ambiguity = True
        if definition_impact:
            conforms = True
            if status != "resolved":
                if status != "blocking":
                    errors.append(f"{ambiguity_id}: unresolved definition-impact ambiguity must be blocking")
                    conforms = False
                for subproblem_id in affected:
                    if ambiguity_id not in unresolved_by_subproblem.get(str(subproblem_id), set()):
                        errors.append(f"{ambiguity_id}: affected {subproblem_id} must reference it in unresolved_ids")
                        conforms = False
            else:
                if not meaningful_text(item.get("resolution_evidence")):
                    errors.append(f"{ambiguity_id}: resolved definition-impact ambiguity requires resolution evidence")
                    conforms = False
                for subproblem_id, unresolved in unresolved_by_subproblem.items():
                    if ambiguity_id in unresolved:
                        errors.append(f"{ambiguity_id}: resolved ambiguity must not remain in {subproblem_id}.unresolved_ids")
                        conforms = False
            definition_checks.append(conforms)

    if has_blocking_ambiguity and profile.get("gate_status") != "BLOCKED":
        errors.append("blocking ambiguities require problem-profile.gate_status BLOCKED")
    if profile.get("gate_status") == "BLOCKED" and audit.get("overall_status") != "BLOCKED":
        errors.append("BLOCKED problem-profile status requires BLOCKED analysis-audit overall_status")

    audit_dimensions = {item.get("dimension") for item in audit_checks}
    if audit_dimensions != AUDIT_DIMENSIONS:
        errors.append(
            "analysis-audit dimensions must exactly match the required set: "
            f"missing={sorted(AUDIT_DIMENSIONS - audit_dimensions)}, "
            f"extra={sorted(audit_dimensions - AUDIT_DIMENSIONS)}"
        )

    metrics = {
        "requirement_mapping_coverage": coverage(requirements, lambda item: bool(item.get("subproblem_ids"))),
        "requirement_source_coverage": coverage(requirements, lambda item: bool(item.get("source_ref"))),
        "subproblem_data_coverage": len(subproblem_ids & mapping_ids) / len(subproblem_ids) if subproblem_ids else 0.0,
        "audit_completion": coverage(audit_checks, lambda item: item.get("status") != "NOT_RUN"),
        "semantic_contract_coverage": coverage(subproblems, semantic_contract_complete),
        "structural_difficulty_coverage": (
            sum(1 for passed in structural_results if passed) / len(structural_results)
            if structural_results
            else 1.0
        ),
        "task_tag_gate_coverage": (
            sum(1 for passed in task_tag_gate_results if passed) / len(task_tag_gate_results)
            if task_tag_gate_results
            else 1.0
        ),
        "definition_impact_gating": (
            sum(1 for passed in definition_checks if passed) / len(definition_checks)
            if definition_checks
            else 1.0
        ),
    }

    if strict:
        gate_status = profile.get("gate_status")
        if gate_status not in {"PASS", "PASS_WITH_OPEN_ITEMS"}:
            errors.append("strict mode requires gate_status PASS or PASS_WITH_OPEN_ITEMS")
        if audit.get("overall_status") != gate_status:
            errors.append("analysis-audit overall_status must match problem-profile gate_status")
        if not requirements:
            errors.append("strict mode requires at least one traced requirement")
        if not entities:
            errors.append("strict mode requires at least one identified entity")
        if not variables:
            errors.append("strict mode requires at least one identified variable")
        if not subproblems:
            errors.append("strict mode requires at least one subproblem")
        if any(item.get("status") == "blocked" for item in requirements):
            errors.append("strict mode does not allow blocked requirements")
        if any(item.get("status") == "blocking" for item in ambiguities):
            errors.append("strict mode does not allow blocking ambiguities")
        if any(item.get("status") in {"NOT_RUN", "FAIL"} for item in audit_checks):
            errors.append("strict mode requires every audit dimension to run without FAIL")
        if any(item.get("status") == "WARN" for item in audit_checks) and gate_status == "PASS":
            errors.append("audit WARN requires gate_status PASS_WITH_OPEN_ITEMS")
        for name, value in metrics.items():
            if value < 1.0:
                errors.append(f"strict mode requires {name}=1.0, got {value:.3f}")
        for source in profile.get("source_files", []):
            if source.get("role") != "user-note" and not source.get("sha256"):
                errors.append(f"{source.get('id')}: strict mode requires a readable hashed source file")
        for item in subproblems:
            if not item.get("required_outputs"):
                errors.append(f"{item.get('id')}: strict mode requires at least one output")
            if not item.get("source_requirement_ids"):
                errors.append(f"{item.get('id')}: strict mode requires source requirement links")
    elif profile.get("gate_status") == "DRAFT":
        warnings.append("analysis package is still DRAFT; run strict validation before handoff")

    return errors, warnings, metrics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--json", action="store_true", dest="json_output")
    return parser.parse_args()


def current_gate_status(project_root: Path) -> str | None:
    path = project_root / "analysis" / "problem-profile.yaml"
    if not path.is_file():
        return None
    try:
        payload = load_structured(path)
    except (OSError, ValueError):
        return None
    return payload.get("gate_status") if isinstance(payload, dict) else None


def main() -> int:
    args = parse_args()
    project_root = Path(args.project_root).expanduser().resolve()
    errors, warnings, metrics = validate(project_root, args.strict)
    status = "FAIL" if errors else "PASS"
    if not errors and current_gate_status(project_root) == "BLOCKED":
        status = "BLOCKED"

    if args.json_output:
        print(json.dumps({"status": status, "metrics": metrics, "errors": errors, "warnings": warnings}, ensure_ascii=False, indent=2))
    else:
        print(f"STATUS: {status}")
        for name, value in metrics.items():
            print(f"METRIC: {name}={value:.3f}")
        for warning in warnings:
            print(f"WARNING: {warning}")
        for error in errors:
            print(f"ERROR: {error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
