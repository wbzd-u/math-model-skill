#!/usr/bin/env python3
"""Initialize a numerical-solving package from a modeling implementation contract."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "0.1.0"
MODULE_ROOT = Path(__file__).resolve().parents[1]
MODELING_ROOT = MODULE_ROOT.parent / "modeling-selection"
PROBLEM_ROOT = MODULE_ROOT.parent / "problem-analysis"
MODELING_FILES = [
    "intake-check.yaml",
    "model-specification.yaml",
    "validation-plan.yaml",
    "implementation-contract.yaml",
]
ANALYSIS_FILES = [
    "data-inventory.yaml",
    "entity-variable-map.yaml",
    "data-task-matrix.yaml",
]
AUDIT_DIMENSIONS = [
    "mode_fidelity",
    "upstream_integrity",
    "input_binding",
    "semantic_fidelity",
    "reuse_provenance",
    "license_and_attribution",
    "implementation_checks",
    "experiment_traceability",
    "validation_completion",
    "result_evidence",
    "reproducibility",
    "failure_disclosure",
]
FIXED_FILES = [
    "intake.yaml",
    "run-plan.yaml",
    "implementation-provenance.yaml",
    "experiment-registry.yaml",
    "validation-results.yaml",
    "results-manifest.yaml",
    "reproducibility.json",
    "solver-audit.yaml",
    "solver-report.md",
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
            raise ValueError(f"cannot parse structured file {path}: {exc}") from exc


def validate_json_schema(data: Any, schema_path: Path) -> list[str]:
    try:
        import jsonschema  # type: ignore
    except ImportError as exc:
        raise ValueError("jsonschema is required for numerical-solving initialization") from exc
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
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


def relative_to_project(path: Path, project_root: Path) -> str:
    resolved = path.resolve()
    root = project_root.resolve()
    try:
        return resolved.relative_to(root).as_posix()
    except ValueError as exc:
        raise ValueError(f"path escapes project root: {path}") from exc


def resolve_project_path(project_root: Path, value: str) -> Path:
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = project_root / candidate
    relative_to_project(candidate, project_root)
    return candidate.resolve()


def solver_output_path(destination: str) -> str:
    normalized = destination.replace("\\", "/").lstrip("/")
    if not normalized or normalized == ".":
        raise ValueError("empty required output destination")
    candidate = Path(normalized)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"unsafe required output destination: {destination}")
    if normalized.startswith("solver/"):
        return normalized
    return f"solver/{normalized}"


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def reset_solver_dir(solver_dir: Path, project_root: Path) -> None:
    resolved = solver_dir.resolve()
    root = project_root.resolve()
    if resolved.parent != root or resolved.name != "solver":
        raise ValueError(f"refusing to reset unsafe solver path: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)


def package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def upstream_handoff_ok(project_root: Path) -> tuple[bool, str]:
    validator = MODELING_ROOT / "scripts" / "validate_modeling_selection.py"
    if not validator.exists():
        return False, "modeling-selection handoff validator is unavailable"
    result = subprocess.run(
        [sys.executable, str(validator), "--project-root", str(project_root), "--mode", "handoff"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return True, "modeling-selection handoff passed"
    detail = (result.stdout or result.stderr).strip().splitlines()
    tail = detail[-1] if detail else "unknown handoff validation failure"
    return False, f"modeling-selection handoff failed: {tail}"


def build_bindings(
    project_root: Path,
    contract: dict[str, Any],
    model_spec: dict[str, Any],
    data_inventory: dict[str, Any],
    entity_map: dict[str, Any],
    data_matrix: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    stages = contract.get("execution_stages", [])
    variables = {item.get("id"): item for item in entity_map.get("variables", []) if item.get("id")}
    notation = {item.get("id"): item for item in model_spec.get("notation", []) if item.get("id")}
    generated_ids = {
        ref
        for component in model_spec.get("components", [])
        for ref in component.get("output_variable_ids", [])
    }
    parameters = {item.get("id"): item for item in contract.get("parameters", []) if item.get("id")}
    stage_by_ref: dict[str, set[str]] = {}
    for stage in stages:
        stage_id = stage.get("id")
        for ref in stage.get("input_refs", []):
            stage_by_ref.setdefault(ref, set()).add(stage_id)
            variable = variables.get(ref, {})
            for data_id in variable.get("data_ids", []):
                stage_by_ref.setdefault(data_id, set()).add(stage_id)

    data_bindings: list[dict[str, Any]] = []
    path_errors: list[str] = []
    data_status: dict[str, str] = {}
    data_items = {item.get("id"): item for item in data_inventory.get("datasets", []) if item.get("id")}
    for data_id, item in data_items.items():
        raw_path = item.get("path", "")
        observed_hash: str | None = None
        issues = list(item.get("issues", []))
        try:
            resolved = resolve_project_path(project_root, raw_path)
            status = "available" if resolved.is_file() else "missing"
            if resolved.is_file():
                observed_hash = sha256_file(resolved)
        except ValueError as exc:
            status = "unresolved"
            path_errors.append(str(exc))
            issues.append(str(exc))
        required_by = sorted(stage_by_ref.get(data_id, set()))
        if not required_by and status == "available":
            status = "not-required"
        data_status[data_id] = status
        data_bindings.append(
            {
                "data_id": data_id,
                "path": raw_path,
                "format": item.get("format", "unknown"),
                "observed_sha256": observed_hash,
                "required_by_stage_ids": required_by,
                "status": status,
                "issues": issues,
            }
        )

    field_refs_by_data: dict[str, set[str]] = {}
    selected = set(contract.get("scope_subproblem_ids", []))
    for mapping in data_matrix.get("mappings", []):
        if mapping.get("subproblem_id") not in selected:
            continue
        for need in mapping.get("needs", []):
            for data_id in need.get("data_ids", []):
                field_refs_by_data.setdefault(data_id, set()).update(need.get("field_refs", []))

    variable_bindings: list[dict[str, Any]] = []
    all_variable_ids = set(variables) | set(notation)
    for variable_id in sorted(all_variable_ids):
        source = variables.get(variable_id, {})
        data_ids = list(source.get("data_ids", []))
        field_refs = sorted({ref for data_id in data_ids for ref in field_refs_by_data.get(data_id, set())})
        role = source.get("role")
        if variable_id in generated_ids or variable_id.startswith("dvar-"):
            kind = "generated"
            status = "generated"
        elif data_ids:
            kind = "field" if field_refs else "given"
            statuses = {data_status.get(data_id, "unresolved") for data_id in data_ids}
            status = "resolved" if statuses <= {"available", "not-required"} else "unresolved"
        elif role == "controllable":
            kind, status = "decision", "resolved"
        elif role == "state":
            kind, status = "state", "partial"
        elif role in {"outcome", "unknown"}:
            kind, status = "generated", "generated"
        elif role in {"given", "index"}:
            kind, status = "given", "partial"
        else:
            kind, status = "unresolved", "unresolved"
        source_refs = [source.get("source_ref")] if source.get("source_ref") else []
        variable_bindings.append(
            {
                "variable_id": variable_id,
                "kind": kind,
                "data_ids": data_ids,
                "field_refs": field_refs,
                "expected_unit": source.get("unit", notation.get(variable_id, {}).get("unit")),
                "source_refs": source_refs,
                "status": status,
            }
        )

    parameter_bindings: list[dict[str, Any]] = []
    for parameter_id, item in sorted(parameters.items()):
        source = str(item.get("source", ""))
        policy = item.get("value_policy")
        lowered = f"{source} {policy}".lower()
        if item.get("calibration_allowed"):
            kind = "calibrated"
        elif "data" in lowered or "数据" in lowered:
            kind = "data-derived"
        elif "scenario" in lowered or "情景" in lowered:
            kind = "scenario"
        elif "solver" in lowered or "求解" in lowered:
            kind = "solver-choice"
        else:
            kind = "fixed"
        parameter_bindings.append(
            {
                "parameter_id": parameter_id,
                "kind": kind,
                "value_or_config_ref": policy,
                "source_refs": [source] if source else [],
                "calibration_allowed": bool(item.get("calibration_allowed")),
                "status": "partial" if source and policy not in {None, ""} else "unresolved",
            }
        )

    variable_status = {item["variable_id"]: item["status"] for item in variable_bindings}
    parameter_status = {item["parameter_id"]: item["status"] for item in parameter_bindings}
    unresolved_items: list[dict[str, Any]] = []
    stage_bindings: list[dict[str, Any]] = []
    for stage in stages:
        stage_id = stage.get("id")
        unresolved_refs: list[str] = []
        partial = False
        for ref in stage.get("input_refs", []):
            if ref in data_status:
                status = data_status[ref]
                if status in {"missing", "unresolved"}:
                    unresolved_refs.append(ref)
            elif ref in variable_status:
                status = variable_status[ref]
                if status == "unresolved":
                    unresolved_refs.append(ref)
                elif status == "partial":
                    partial = True
            elif ref in parameter_status:
                status = parameter_status[ref]
                if status == "unresolved":
                    unresolved_refs.append(ref)
                else:
                    partial = True
            elif ref in generated_ids:
                continue
            else:
                unresolved_refs.append(ref)
        if unresolved_refs:
            stage_status = "unresolved"
            unresolved_items.append(
                {
                    "id": f"binding-{stage_id}",
                    "kind": "input",
                    "statement": f"stage {stage_id} has unresolved input refs: {', '.join(sorted(set(unresolved_refs)))}",
                    "affected_stage_ids": [stage_id],
                    "source_refs": sorted(set(unresolved_refs)),
                    "severity": "blocking",
                }
            )
        elif partial:
            stage_status = "partial"
        else:
            stage_status = "resolved"
        stage_bindings.append(
            {
                "stage_id": stage_id,
                "input_refs": list(stage.get("input_refs", [])),
                "output_refs": list(stage.get("output_refs", [])),
                "status": stage_status,
            }
        )
    return data_bindings, variable_bindings, parameter_bindings, stage_bindings, unresolved_items, path_errors


def report_template(mode: str, status: str, reasons: list[str]) -> str:
    reason_lines = "\n".join(f"- {reason}" for reason in reasons) if reasons else "- 当前没有准入阻断。"
    return f"""# 数值求解报告

## 1. 准入与模式

- 模式：`{mode}`
- 状态：`{status}`

### 当前事项

{reason_lines}

## 2. 输入与运行时绑定

[待填写]

## 3. 实现与外部来源

[待填写]

## 4. 实验与失败记录

[待填写]

## 5. 验证与结果

[待填写]

## 6. 限制、反馈与下一阶段

[待填写；probe 必须说明结果不能进入论文，solve 必须报告 ready_for_writing]
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--mode", choices=["probe", "solve"], default="probe")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    modeling_dir = project_root / "modeling"
    analysis_dir = project_root / "analysis"
    solver_dir = project_root / "solver"

    if solver_dir.exists() and any(solver_dir.iterdir()):
        if not args.force:
            print("ERROR: solver package already exists; use --force only to rebuild it from the current contract")
            return 2
        try:
            reset_solver_dir(solver_dir, project_root)
        except ValueError as exc:
            print(f"ERROR: {exc}")
            return 2

    reasons: list[str] = []
    hard_failures: list[str] = []
    loaded: dict[str, dict[str, Any]] = {}
    upstream_files: list[dict[str, Any]] = []

    modeling_schema_map = {
        "intake-check.yaml": "intake-check.schema.json",
        "model-specification.yaml": "model-specification.schema.json",
        "validation-plan.yaml": "validation-plan.schema.json",
        "implementation-contract.yaml": "implementation-contract.schema.json",
    }
    for name in MODELING_FILES:
        path = modeling_dir / name
        if not path.is_file():
            hard_failures.append(f"missing required upstream file: modeling/{name}")
            upstream_files.append({"path": f"modeling/{name}", "sha256": None, "required": True})
            continue
        try:
            payload = load_structured(path)
            errors = validate_json_schema(payload, MODELING_ROOT / "schemas" / modeling_schema_map[name])
            if errors:
                hard_failures.extend(f"{name}: {error}" for error in errors)
            loaded[name] = payload
        except (OSError, ValueError) as exc:
            hard_failures.append(str(exc))
        upstream_files.append({"path": f"modeling/{name}", "sha256": sha256_file(path), "required": True})

    analysis_schema_map = {
        "data-inventory.yaml": "data-inventory.schema.json",
        "entity-variable-map.yaml": "entity-variable-map.schema.json",
        "data-task-matrix.yaml": "data-task-matrix.schema.json",
    }
    analysis_loaded: dict[str, dict[str, Any]] = {}
    for name in ANALYSIS_FILES:
        path = analysis_dir / name
        if not path.is_file():
            reasons.append(f"analysis/{name} is unavailable; runtime bindings require manual resolution")
            upstream_files.append({"path": f"analysis/{name}", "sha256": None, "required": args.mode == "solve"})
            if args.mode == "solve":
                hard_failures.append(f"missing analysis binding source: analysis/{name}")
            continue
        try:
            payload = load_structured(path)
            errors = validate_json_schema(payload, PROBLEM_ROOT / "schemas" / analysis_schema_map[name])
            if errors:
                message = [f"{name}: {error}" for error in errors]
                reasons.extend(message)
                if args.mode == "solve":
                    hard_failures.extend(message)
            analysis_loaded[name] = payload
        except (OSError, ValueError) as exc:
            reasons.append(str(exc))
            if args.mode == "solve":
                hard_failures.append(str(exc))
        upstream_files.append({"path": f"analysis/{name}", "sha256": sha256_file(path), "required": args.mode == "solve"})

    contract = loaded.get("implementation-contract.yaml", {})
    intake = loaded.get("intake-check.yaml", {})
    model_spec = loaded.get("model-specification.yaml", {})
    validation_plan = loaded.get("validation-plan.yaml", {})
    contract_status = contract.get("status", "BLOCKED")

    if args.mode == "probe" and contract_status not in {"EXPLORATORY", "READY"}:
        hard_failures.append(f"probe requires EXPLORATORY or READY contract, got {contract_status}")
    if args.mode == "solve" and contract_status != "READY":
        hard_failures.append(f"solve requires READY contract, got {contract_status}")

    if contract:
        snapshots = contract.get("input_snapshot", {})
        expected = {
            "intake_sha256": modeling_dir / "intake-check.yaml",
            "model_spec_sha256": modeling_dir / "model-specification.yaml",
            "validation_plan_sha256": modeling_dir / "validation-plan.yaml",
        }
        for key, path in expected.items():
            if path.is_file() and snapshots.get(key) != sha256_file(path):
                hard_failures.append(f"implementation contract snapshot mismatch: {key}")

    components = list(contract.get("approved_component_ids", []))
    stage_ids = [item.get("id") for item in contract.get("execution_stages", []) if item.get("id")]
    validation_ids = list(contract.get("validation_test_ids", []))
    output_ids = [item.get("id") for item in contract.get("required_outputs", []) if item.get("id")]
    for output in contract.get("required_outputs", []):
        try:
            solver_output_path(output.get("destination", ""))
        except ValueError as exc:
            hard_failures.append(str(exc))
    feedback_path = contract.get("feedback_policy", {}).get("path")
    if feedback_path:
        try:
            resolve_project_path(project_root, feedback_path)
        except ValueError as exc:
            hard_failures.append(str(exc))
    if not (components or stage_ids or validation_ids):
        hard_failures.append("no approved component, execution stage, or validation test is available for execution")

    if args.mode == "solve" and not hard_failures:
        ok, detail = upstream_handoff_ok(project_root)
        if not ok:
            hard_failures.append(detail)
        else:
            reasons.append(detail)

    try:
        bindings = build_bindings(
            project_root,
            contract,
            model_spec,
            analysis_loaded.get("data-inventory.yaml", {"datasets": []}),
            analysis_loaded.get("entity-variable-map.yaml", {"variables": []}),
            analysis_loaded.get("data-task-matrix.yaml", {"mappings": []}),
        )
        data_bindings, variable_bindings, parameter_bindings, stage_bindings, unresolved_items, path_errors = bindings
        hard_failures.extend(path_errors)
    except (OSError, ValueError) as exc:
        hard_failures.append(str(exc))
        data_bindings, variable_bindings, parameter_bindings, stage_bindings, unresolved_items = [], [], [], [], []

    if args.mode == "solve" and unresolved_items:
        hard_failures.extend(item["statement"] for item in unresolved_items)
    elif unresolved_items:
        reasons.extend(item["statement"] for item in unresolved_items)

    eligible = not hard_failures
    all_reasons = list(dict.fromkeys(hard_failures + reasons))
    status = "READY" if eligible else "BLOCKED"
    run_id = f"{args.mode}-001"
    project_id = intake.get("analysis_package", {}).get("project_id", project_root.name)

    intake_payload = {
        "schema_version": SCHEMA_VERSION,
        "mode": args.mode,
        "status": status,
        "run_id": run_id,
        "project_id": project_id,
        "contract_id": contract.get("contract_id", "contract-unavailable"),
        "contract_status": contract_status if contract_status in {"DRAFT", "EXPLORATORY", "READY", "BLOCKED"} else "BLOCKED",
        "upstream_files": upstream_files,
        "scope_subproblem_ids": list(contract.get("scope_subproblem_ids", [])),
        "component_ids": components,
        "stage_ids": stage_ids,
        "validation_test_ids": validation_ids,
        "required_output_ids": output_ids,
        "data_bindings": data_bindings,
        "variable_bindings": variable_bindings,
        "parameter_bindings": parameter_bindings,
        "stage_bindings": stage_bindings,
        "immutable_items": list(contract.get("immutable_items", [])),
        "solver_discretion": list(contract.get("solver_discretion", [])),
        "unresolved_items": unresolved_items,
        "gate": {"eligible": eligible, "reasons": all_reasons},
    }
    solver_dir.mkdir(parents=True, exist_ok=True)
    write_json(solver_dir / "intake.yaml", intake_payload)
    write_text(solver_dir / "solver-report.md", report_template(args.mode, status, all_reasons))

    if not eligible:
        print(f"STATUS: BLOCKED\nMODE: {args.mode}\nOUTPUT: {solver_dir / 'intake.yaml'}")
        for reason in all_reasons:
            print(f"ERROR: {reason}")
        return 1

    validation_by_id = {item.get("id"): item for item in validation_plan.get("tests", []) if item.get("id")}
    run_plan_stages = []
    for stage in contract.get("execution_stages", []):
        stage_id = stage.get("id")
        candidate_binding = next((item for item in stage_bindings if item["stage_id"] == stage_id), None)
        input_status = candidate_binding.get("status") if candidate_binding else "unresolved"
        run_plan_stages.append(
            {
                "contract_stage_id": stage_id,
                "component_ids": list(stage.get("component_ids", [])),
                "input_bindings": [
                    {
                        "contract_ref": ref,
                        "binding_kind": "unresolved",
                        "binding_ref": None,
                        "source_ref": None,
                        "unit_policy": None,
                        "status": "unresolved" if input_status != "resolved" else "partial",
                    }
                    for ref in stage.get("input_refs", [])
                ],
                "output_bindings": [],
                "source_files": [],
                "commands": [],
                "invariant_checks": [
                    {"statement": statement, "method": "待根据实现填写", "status": "PLANNED", "evidence_ref": None}
                    for statement in stage.get("required_invariants", [])
                ],
                "validation_test_ids": [
                    test_id
                    for test_id in validation_ids
                    if set(validation_by_id.get(test_id, {}).get("component_ids", [])) & set(stage.get("component_ids", []))
                ],
                "provenance_record_ids": [],
                "status": "PLANNED",
            }
        )

    payloads: dict[str, object] = {
        "run-plan.yaml": {
            "schema_version": SCHEMA_VERSION,
            "mode": args.mode,
            "run_id": run_id,
            "status": "DRAFT",
            "diagnostic_question": None,
            "language": None,
            "plotting_backend": {"language": "not-needed", "rationale": "尚未决定是否需要图表。", "data_handoff_path": None},
            "environment_files": [],
            "stages": run_plan_stages,
            "simplifications": [],
            "numerical_controls": {"seeds": [], "tolerances": [], "stopping_criteria": []},
            "semantic_deviations": [],
        },
        "implementation-provenance.yaml": {
            "schema_version": SCHEMA_VERSION,
            "contract_id": contract.get("contract_id"),
            "mode": args.mode,
            "status": "DRAFT",
            "distribution_context": "competition-or-project-delivery",
            "sources": [],
            "reuse_records": [],
            "custom_components": [],
        },
        "experiment-registry.yaml": {"schema_version": SCHEMA_VERSION, "mode": args.mode, "run_id": run_id, "experiments": []},
        "validation-results.yaml": {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "status": "DRAFT",
            "results": [
                {
                    "test_id": test_id,
                    "status": "NOT_RUN",
                    "procedure_executed": None,
                    "metric_values": [],
                    "criteria_evaluation": None,
                    "evidence_refs": [],
                    "failure_action": validation_by_id.get(test_id, {}).get("failure_action", "none"),
                    "limitation": None,
                }
                for test_id in validation_ids
            ],
            "additional_checks": [],
        },
        "results-manifest.yaml": {
            "schema_version": SCHEMA_VERSION,
            "mode": args.mode,
            "run_id": run_id,
            "status": "DRAFT",
            "ready_for_writing": False,
            "contract_outputs": [
                {
                    "output_id": item.get("id"),
                    "status": "NOT_PRODUCED",
                    "path": solver_output_path(item.get("destination", "")),
                    "sha256": None,
                    "experiment_ids": [],
                    "acceptance_evidence_refs": [],
                    "description": item.get("type"),
                    "limitations": [],
                }
                for item in contract.get("required_outputs", [])
            ],
            "claims": [],
            "disclosed_failed_experiment_ids": [],
            "limitations": [],
            "feedback_ref": None,
        },
        "reproducibility.json": {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "status": "DRAFT",
            "platform": {
                "os": platform.system() or None,
                "os_version": platform.version() or None,
                "architecture": platform.machine() or None,
                "hardware": platform.processor() or None,
                "timezone": datetime.now().astimezone().tzname(),
            },
            "runtimes": [{"name": "Python", "version": platform.python_version()}],
            "dependencies": [
                {"name": name, "version": version, "source_id": None}
                for name in ("jsonschema", "PyYAML")
                if (version := package_version(name)) is not None
            ],
            "environment_files": [],
            "input_files": [
                {"path": item["path"], "sha256": item["observed_sha256"]}
                for item in data_bindings
                if item["observed_sha256"]
            ],
            "source_files": [],
            "config_files": [],
            "seeds": [],
            "commands": [],
            "verified_command_ids": [],
            "notes": [],
        },
        "solver-audit.yaml": {
            "schema_version": SCHEMA_VERSION,
            "checks": [
                {
                    "dimension": dimension,
                    "status": "WARN" if dimension in {"mode_fidelity", "upstream_integrity"} else "NA",
                    "evidence": ["solver/intake.yaml"] if dimension in {"mode_fidelity", "upstream_integrity"} else [],
                    "findings": ["Execution package initialized; review not complete."],
                    "required_actions": ["Complete execution and validation evidence."],
                }
                for dimension in AUDIT_DIMENSIONS
            ],
            "overall_status": "NOT_READY",
        },
    }
    for name, payload in payloads.items():
        write_json(solver_dir / name, payload)

    for directory in ("src", "configs", "results", "figures", "logs", "runs"):
        (solver_dir / directory).mkdir(parents=True, exist_ok=True)

    print(f"STATUS: READY\nMODE: {args.mode}\nOUTPUT: {solver_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
