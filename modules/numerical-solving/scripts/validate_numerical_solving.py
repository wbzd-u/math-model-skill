#!/usr/bin/env python3
"""Validate numerical-solving provenance, experiments, results, and reproducibility."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


MODULE_ROOT = Path(__file__).resolve().parents[1]
MODELING_ROOT = MODULE_ROOT.parent / "modeling-selection"
SCHEMA_FILES = {
    "intake.yaml": "intake.schema.json",
    "run-plan.yaml": "run-plan.schema.json",
    "implementation-provenance.yaml": "implementation-provenance.schema.json",
    "experiment-registry.yaml": "experiment-registry.schema.json",
    "validation-results.yaml": "validation-results.schema.json",
    "results-manifest.yaml": "results-manifest.schema.json",
    "reproducibility.json": "reproducibility.schema.json",
    "solver-audit.yaml": "solver-audit.schema.json",
}
AUDIT_DIMENSIONS = {
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
}
CODE_REUSE_KINDS = {"adapted-code", "copied-code", "vendored-code"}
CRITICAL_FAILURE_ACTIONS = {"revise-model", "return-to-analysis", "solver-diagnostic"}


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
        raise ValueError("jsonschema is required for numerical-solving validation") from exc
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


def resolve_inside(project_root: Path, value: str | None) -> Path | None:
    if value in {None, ""}:
        return None
    candidate = Path(str(value))
    if not candidate.is_absolute():
        candidate = project_root / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(project_root.resolve())
    except ValueError as exc:
        raise ValueError(f"path escapes project root: {value}") from exc
    return resolved


def duplicates(values: list[Any]) -> set[Any]:
    seen: set[Any] = set()
    repeated: set[Any] = set()
    for value in values:
        if value in seen:
            repeated.add(value)
        seen.add(value)
    return repeated


def expected_solver_output_path(destination: str) -> str:
    normalized = destination.replace("\\", "/").lstrip("/")
    candidate = Path(normalized)
    if not normalized or candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"unsafe required output destination: {destination}")
    return normalized if normalized.startswith("solver/") else f"solver/{normalized}"


def as_dict_list(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def check_hashed_path(
    project_root: Path,
    path_value: str | None,
    expected_hash: str | None,
    label: str,
    errors: list[str],
) -> Path | None:
    try:
        path = resolve_inside(project_root, path_value)
    except ValueError as exc:
        errors.append(str(exc))
        return None
    if path is None or not path.is_file():
        errors.append(f"{label} file is missing: {path_value}")
        return path
    if expected_hash is None:
        errors.append(f"{label} has no SHA-256: {path_value}")
    elif sha256_file(path) != expected_hash:
        errors.append(f"{label} SHA-256 mismatch: {path_value}")
    return path


def evidence_ref_error(project_root: Path, value: str, known_ids: set[str]) -> str | None:
    if value in known_ids:
        return None
    path_value, separator, fragment = value.partition("#")
    try:
        path = resolve_inside(project_root, path_value)
    except ValueError as exc:
        return str(exc)
    if path is None or not path.exists():
        return f"missing evidence file: {path_value}"
    if separator and fragment and fragment.startswith(("exp-", "val-", "out-", "claim-", "check-")) and fragment not in known_ids:
        return f"unknown evidence anchor: {fragment}"
    return None


def validate_paths(project_root: Path, payloads: dict[str, dict[str, Any]], errors: list[str]) -> None:
    plan = payloads["run-plan.yaml"]
    provenance = payloads["implementation-provenance.yaml"]
    registry = payloads["experiment-registry.yaml"]
    manifest = payloads["results-manifest.yaml"]
    reproducibility = payloads["reproducibility.json"]
    intake = payloads["intake.yaml"]

    path_values: list[tuple[str, str | None]] = []
    path_values.extend(("intake data", item.get("path")) for item in as_dict_list(intake.get("data_bindings")))
    path_values.extend(("environment file", path) for path in plan.get("environment_files", []))
    path_values.append(("plotting data handoff", plan.get("plotting_backend", {}).get("data_handoff_path")))
    for stage in as_dict_list(plan.get("stages")):
        path_values.extend(("stage source", path) for path in stage.get("source_files", []))
        path_values.extend(("stage output", item.get("path")) for item in as_dict_list(stage.get("output_bindings")))
    for record in as_dict_list(provenance.get("reuse_records")):
        path_values.extend(("reused local path", path) for path in record.get("local_paths", []))
        path_values.extend(("attribution path", path) for path in record.get("attribution_locations", []))
    for experiment in as_dict_list(registry.get("experiments")):
        path_values.append(("experiment working directory", experiment.get("working_directory")))
        path_values.append(("experiment log", experiment.get("log_path")))
        path_values.extend(("experiment input", item.get("path")) for item in as_dict_list(experiment.get("input_artifacts")))
        path_values.extend(("experiment config", path) for path in experiment.get("config_paths", []))
        path_values.extend(("experiment output", item.get("path")) for item in as_dict_list(experiment.get("output_artifacts")))
    path_values.extend(("contract output", item.get("path")) for item in as_dict_list(manifest.get("contract_outputs")))
    path_values.append(("feedback", manifest.get("feedback_ref")))
    for group in ("environment_files", "input_files", "source_files", "config_files"):
        path_values.extend((f"reproducibility {group}", item.get("path")) for item in as_dict_list(reproducibility.get(group)))
    for command in as_dict_list(reproducibility.get("commands")):
        path_values.append(("reproducibility working directory", command.get("working_directory")))

    for label, value in path_values:
        if value in {None, ""}:
            continue
        try:
            resolve_inside(project_root, value)
        except ValueError as exc:
            errors.append(f"{label}: {exc}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--mode", choices=["probe", "solve"], default="probe")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    solver_dir = project_root / "solver"
    modeling_dir = project_root / "modeling"
    errors: list[str] = []
    warnings: list[str] = []
    loaded: dict[str, dict[str, Any]] = {}

    for name, schema_name in SCHEMA_FILES.items():
        path = solver_dir / name
        if not path.is_file():
            errors.append(f"missing solver file: solver/{name}")
            continue
        try:
            payload = load_structured(path)
            schema_errors = validate_json_schema(payload, MODULE_ROOT / "schemas" / schema_name)
            errors.extend(f"{name}: {error}" for error in schema_errors)
            loaded[name] = payload
        except (OSError, ValueError) as exc:
            errors.append(str(exc))

    feedback_path = solver_dir / "modeling-feedback.yaml"
    feedback: dict[str, Any] | None = None
    if feedback_path.is_file():
        try:
            feedback = load_structured(feedback_path)
            schema_errors = validate_json_schema(feedback, MODULE_ROOT / "schemas" / "modeling-feedback.schema.json")
            errors.extend(f"modeling-feedback.yaml: {error}" for error in schema_errors)
        except (OSError, ValueError) as exc:
            errors.append(str(exc))

    if len(loaded) != len(SCHEMA_FILES):
        return emit(args.json_output, args.mode, "FAIL", False, errors, warnings, {})

    intake = loaded["intake.yaml"]
    plan = loaded["run-plan.yaml"]
    provenance = loaded["implementation-provenance.yaml"]
    registry = loaded["experiment-registry.yaml"]
    validation = loaded["validation-results.yaml"]
    manifest = loaded["results-manifest.yaml"]
    reproducibility = loaded["reproducibility.json"]
    audit = loaded["solver-audit.yaml"]

    run_id = intake.get("run_id")
    for name, payload in loaded.items():
        if "mode" in payload and payload.get("mode") != args.mode:
            errors.append(f"{name} mode {payload.get('mode')} does not match requested mode {args.mode}")
        if "run_id" in payload and payload.get("run_id") != run_id:
            errors.append(f"{name} run_id does not match intake")
    if intake.get("mode") != args.mode:
        errors.append("intake mode does not match requested mode")
    if intake.get("status") != "READY" or not intake.get("gate", {}).get("eligible"):
        errors.append("solver intake is not eligible")

    for item in as_dict_list(intake.get("upstream_files")):
        path_value = item.get("path")
        try:
            path = resolve_inside(project_root, path_value)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if path is None or not path.is_file():
            message = f"upstream file is missing: {path_value}"
            (errors if item.get("required") else warnings).append(message)
            continue
        if item.get("sha256") != sha256_file(path):
            errors.append(f"upstream SHA-256 changed: {path_value}")

    for item in as_dict_list(intake.get("data_bindings")):
        observed_hash = item.get("observed_sha256")
        if observed_hash:
            check_hashed_path(project_root, item.get("path"), observed_hash, f"intake raw data {item.get('data_id')}", errors)
        elif args.mode == "solve" and item.get("required_by_stage_ids"):
            errors.append(f"required raw data lacks an observed SHA-256: {item.get('data_id')}")

    contract_path = modeling_dir / "implementation-contract.yaml"
    model_spec_path = modeling_dir / "model-specification.yaml"
    validation_plan_path = modeling_dir / "validation-plan.yaml"
    if not contract_path.is_file() or not model_spec_path.is_file() or not validation_plan_path.is_file():
        errors.append("current modeling contract package is incomplete")
        contract: dict[str, Any] = {}
        model_spec: dict[str, Any] = {}
        validation_plan: dict[str, Any] = {}
    else:
        try:
            contract = load_structured(contract_path)
            model_spec = load_structured(model_spec_path)
            validation_plan = load_structured(validation_plan_path)
            for payload, schema_name, label in (
                (contract, "implementation-contract.schema.json", "implementation contract"),
                (model_spec, "model-specification.schema.json", "model specification"),
                (validation_plan, "validation-plan.schema.json", "validation plan"),
            ):
                schema_errors = validate_json_schema(payload, MODELING_ROOT / "schemas" / schema_name)
                errors.extend(f"{label}: {error}" for error in schema_errors)
        except (OSError, ValueError) as exc:
            errors.append(str(exc))
            contract, model_spec, validation_plan = {}, {}, {}

    if args.mode == "probe" and contract.get("status") not in {"EXPLORATORY", "READY"}:
        errors.append("probe requires EXPLORATORY or READY implementation contract")
    if args.mode == "solve" and contract.get("status") != "READY":
        errors.append("solve requires READY implementation contract")
    if intake.get("contract_id") != contract.get("contract_id"):
        errors.append("intake contract_id does not match current implementation contract")

    contract_components = set(contract.get("approved_component_ids", []))
    contract_stages = {item.get("id"): item for item in as_dict_list(contract.get("execution_stages")) if item.get("id")}
    contract_tests = set(contract.get("validation_test_ids", []))
    contract_outputs = {item.get("id"): item for item in as_dict_list(contract.get("required_outputs")) if item.get("id")}
    if set(intake.get("component_ids", [])) != contract_components:
        errors.append("intake component_ids do not match contract")
    if set(intake.get("stage_ids", [])) != set(contract_stages):
        errors.append("intake stage_ids do not match contract")
    if set(intake.get("validation_test_ids", [])) != contract_tests:
        errors.append("intake validation_test_ids do not match contract")
    if set(intake.get("required_output_ids", [])) != set(contract_outputs):
        errors.append("intake required_output_ids do not match contract")

    unresolved = as_dict_list(intake.get("unresolved_items"))
    if args.mode == "solve" and unresolved:
        errors.append("solve has unresolved runtime bindings")
    elif unresolved:
        warnings.append(f"probe retains {len(unresolved)} unresolved runtime binding item(s)")

    validate_paths(project_root, loaded, errors)

    plan_stages = as_dict_list(plan.get("stages"))
    plan_stage_ids = [item.get("contract_stage_id") for item in plan_stages]
    repeated = duplicates(plan_stage_ids)
    if repeated:
        errors.append(f"run plan contains duplicate stage IDs: {sorted(repeated)}")
    unknown_stages = set(plan_stage_ids) - set(contract_stages)
    if unknown_stages:
        errors.append(f"run plan references unknown stages: {sorted(unknown_stages)}")
    if args.mode == "solve" and set(plan_stage_ids) != set(contract_stages):
        errors.append("solve run plan must cover every contract stage")
    if args.mode == "probe" and not plan_stages:
        errors.append("probe run plan has no diagnostic stage")

    for stage in plan_stages:
        stage_id = stage.get("contract_stage_id")
        contract_stage = contract_stages.get(stage_id, {})
        component_ids = set(stage.get("component_ids", []))
        allowed_components = set(contract_stage.get("component_ids", []))
        if not component_ids <= allowed_components:
            errors.append(f"stage {stage_id} includes components not approved for that stage")
        if args.mode == "solve" and component_ids != allowed_components:
            errors.append(f"solve stage {stage_id} does not implement every contracted component")
        input_bindings = as_dict_list(stage.get("input_bindings"))
        input_refs = [item.get("contract_ref") for item in input_bindings]
        if duplicates(input_refs):
            errors.append(f"stage {stage_id} contains duplicate input bindings")
        contracted_inputs = set(contract_stage.get("input_refs", []))
        extra_inputs = set(input_refs) - contracted_inputs
        if extra_inputs and args.mode == "solve":
            errors.append(f"stage {stage_id} binds inputs outside the contract")
        elif extra_inputs:
            binding_by_ref = {item.get("contract_ref"): item for item in input_bindings}
            for ref in sorted(extra_inputs):
                binding = binding_by_ref.get(ref, {})
                base_ref = ref.split(":", 1)[0] if isinstance(ref, str) else None
                valid_diagnostic = (
                    base_ref in contracted_inputs
                    and binding.get("binding_kind") in {"generated", "literal"}
                    and bool(binding.get("source_ref"))
                    and bool(plan.get("simplifications"))
                )
                if valid_diagnostic:
                    warnings.append(f"probe stage {stage_id} adds documented diagnostic input {ref}")
                else:
                    errors.append(f"probe stage {stage_id} has an ungrounded extra input binding: {ref}")
        if args.mode == "solve":
            if set(input_refs) != contracted_inputs:
                errors.append(f"solve stage {stage_id} does not bind every contract input")
            if any(item.get("status") != "resolved" or item.get("binding_kind") == "unresolved" for item in input_bindings):
                errors.append(f"solve stage {stage_id} has unresolved input bindings")
            for binding in input_bindings:
                if binding.get("status") != "resolved":
                    continue
                if binding.get("binding_ref") in {None, ""}:
                    errors.append(f"solve stage {stage_id} has a resolved binding without a binding_ref")
                if binding.get("binding_kind") not in {"prior-stage", "generated"} and not binding.get("source_ref"):
                    errors.append(f"solve stage {stage_id} has a resolved binding without source provenance")
                if binding.get("binding_kind") in {"data", "field"} and isinstance(binding.get("binding_ref"), str):
                    file_part = binding["binding_ref"].split("#", 1)[0]
                    try:
                        bound_path = resolve_inside(project_root, file_part)
                        if bound_path is None or not bound_path.exists():
                            errors.append(f"solve stage {stage_id} binding path is missing: {file_part}")
                    except ValueError as exc:
                        errors.append(str(exc))
            if not stage.get("commands") or not stage.get("source_files"):
                errors.append(f"solve stage {stage_id} lacks source files or commands")
            if stage.get("status") != "COMPLETE":
                errors.append(f"solve stage {stage_id} is not COMPLETE")
        elif any(item.get("status") == "unresolved" for item in input_bindings):
            warnings.append(f"probe stage {stage_id} has unresolved inputs")
        plan_tests = set(stage.get("validation_test_ids", []))
        if not plan_tests <= contract_tests:
            errors.append(f"stage {stage_id} references unknown validation tests")

    simplifications = as_dict_list(plan.get("simplifications"))
    if args.mode == "solve" and simplifications:
        errors.append("formal solve cannot retain diagnostic simplifications")
    if args.mode == "probe" and simplifications:
        warnings.append(f"probe records {len(simplifications)} diagnostic simplification(s)")
    for deviation in as_dict_list(plan.get("semantic_deviations")):
        status = deviation.get("status")
        if status in {"proposed", "feedback-required"}:
            message = f"unresolved semantic deviation: {deviation.get('id')}"
            (errors if args.mode == "solve" else warnings).append(message)
        if status == "approved" and not deviation.get("approval_ref"):
            errors.append(f"approved semantic deviation lacks approval_ref: {deviation.get('id')}")

    source_list = as_dict_list(provenance.get("sources"))
    source_ids = [item.get("id") for item in source_list]
    if duplicates(source_ids):
        errors.append("implementation provenance contains duplicate source IDs")
    source_by_id = {item.get("id"): item for item in source_list if item.get("id")}
    reuse_records = as_dict_list(provenance.get("reuse_records"))
    reuse_ids = [item.get("id") for item in reuse_records]
    if duplicates(reuse_ids):
        errors.append("implementation provenance contains duplicate reuse IDs")
    reuse_by_id = {item.get("id"): item for item in reuse_records if item.get("id")}
    used_source_ids: set[str] = set()
    covered_components: set[str] = set()
    for record in reuse_records:
        record_id = record.get("id")
        record_sources = set(record.get("source_ids", []))
        used_source_ids |= record_sources
        covered_components |= set(record.get("component_ids", []))
        if not record_sources <= set(source_by_id):
            errors.append(f"reuse record {record_id} references unknown sources")
        if not set(record.get("component_ids", [])) <= contract_components:
            errors.append(f"reuse record {record_id} references unknown components")
        if not set(record.get("execution_stage_ids", [])) <= set(contract_stages):
            errors.append(f"reuse record {record_id} references unknown stages")
        if not set(record.get("validation_test_ids", [])) <= contract_tests:
            errors.append(f"reuse record {record_id} references unknown validation tests")
        for source_id in record_sources:
            source = source_by_id.get(source_id, {})
            license_info = source.get("license", {})
            if record.get("reuse_kind") in CODE_REUSE_KINDS:
                if license_info.get("status") != "verified" or license_info.get("compatibility") != "compatible" or not license_info.get("spdx_id"):
                    errors.append(f"code reuse {record_id} lacks a verified compatible license")
                if not record.get("local_paths"):
                    errors.append(f"code reuse {record_id} has no local path mapping")
                if not record.get("obligations_satisfied"):
                    errors.append(f"code reuse {record_id} has unsatisfied license obligations")
                if record.get("attribution_required") and not record.get("attribution_locations"):
                    errors.append(f"code reuse {record_id} lacks required attribution locations")
            elif args.mode == "solve" and source.get("decision") == "selected":
                if not source.get("version_or_identifier"):
                    errors.append(f"selected source {source_id} lacks version or stable identifier")
                if source.get("kind") in {"library", "source-code", "commercial-software"} and license_info.get("status") != "verified":
                    errors.append(f"selected software source {source_id} has unverified license")
            elif source.get("verification_status") in {"provisional", "unverified"}:
                warnings.append(f"source {source_id} is not yet verified from a primary source")
        if record.get("reuse_kind") == "independent-paper-implementation":
            paper_sources = [source_by_id.get(item, {}) for item in record_sources]
            if not any(item.get("kind") == "paper" for item in paper_sources):
                errors.append(f"paper implementation {record_id} has no paper source")
            if not record.get("local_paths"):
                errors.append(f"paper implementation {record_id} has no local implementation path")
            if not record.get("validation_test_ids"):
                warnings.append(f"paper implementation {record_id} has no mapped contract validation test")

    selected_sources = {item.get("id") for item in source_list if item.get("decision") == "selected"}
    unbound_selected = selected_sources - used_source_ids
    if unbound_selected:
        message = f"selected external sources lack reuse records: {sorted(unbound_selected)}"
        (errors if args.mode == "solve" else warnings).append(message)

    custom_components = as_dict_list(provenance.get("custom_components"))
    custom_covered: set[str] = set()
    for item in custom_components:
        item_components = set(item.get("component_ids", []))
        custom_covered |= item_components
        if not item_components <= contract_components:
            errors.append("custom implementation references unknown components")
        if not item.get("alternatives_considered"):
            warnings.append(f"custom implementation {sorted(item_components)} records no existing alternative")
    uncovered = contract_components - covered_components - custom_covered
    if uncovered:
        warnings.append(f"contract components lack reuse/custom provenance classification: {sorted(uncovered)}")
    if args.mode == "solve" and provenance.get("status") != "READY":
        errors.append("solve implementation provenance is not READY")
    if args.mode == "solve" and plan.get("status") != "READY":
        errors.append("solve run plan is not READY")

    for stage in plan_stages:
        unknown_reuse = set(stage.get("provenance_record_ids", [])) - set(reuse_by_id)
        if unknown_reuse:
            errors.append(f"stage {stage.get('contract_stage_id')} references unknown reuse records")

    experiments = as_dict_list(registry.get("experiments"))
    experiment_ids = [item.get("id") for item in experiments]
    if duplicates(experiment_ids):
        errors.append("experiment registry contains duplicate IDs")
    experiment_by_id = {item.get("id"): item for item in experiments if item.get("id")}
    succeeded_ids: set[str] = set()
    failed_ids: set[str] = set()
    succeeded_stage_ids: set[str] = set()
    for experiment in experiments:
        experiment_id = experiment.get("id")
        stage_refs = set(experiment.get("stage_ids", []))
        if not stage_refs <= set(contract_stages):
            errors.append(f"experiment {experiment_id} references unknown stages")
        status = experiment.get("status")
        for item in as_dict_list(experiment.get("input_artifacts")):
            if item.get("sha256"):
                check_hashed_path(project_root, item.get("path"), item.get("sha256"), f"experiment {experiment_id} input", errors)
        if status == "SUCCEEDED":
            succeeded_ids.add(experiment_id)
            succeeded_stage_ids |= stage_refs
            if not experiment.get("command") or experiment.get("exit_code") != 0:
                errors.append(f"succeeded experiment {experiment_id} lacks a successful command record")
            if not experiment.get("started_at") or not experiment.get("finished_at"):
                errors.append(f"succeeded experiment {experiment_id} lacks timestamps")
            if not experiment.get("output_artifacts"):
                errors.append(f"succeeded experiment {experiment_id} has no output artifacts")
            if not experiment.get("log_path"):
                errors.append(f"succeeded experiment {experiment_id} has no log")
            else:
                try:
                    log_path = resolve_inside(project_root, experiment.get("log_path"))
                    if log_path is None or not log_path.is_file():
                        errors.append(f"succeeded experiment {experiment_id} log is missing")
                except ValueError as exc:
                    errors.append(str(exc))
            for item in as_dict_list(experiment.get("output_artifacts")):
                check_hashed_path(project_root, item.get("path"), item.get("sha256"), f"experiment {experiment_id} output", errors)
        elif status == "FAILED":
            failed_ids.add(experiment_id)
            if experiment.get("failure") is None:
                errors.append(f"failed experiment {experiment_id} lacks failure evidence")
            if not experiment.get("command") or experiment.get("exit_code") is None:
                errors.append(f"failed experiment {experiment_id} lacks command or exit-code evidence")
            if not experiment.get("started_at") or not experiment.get("finished_at"):
                errors.append(f"failed experiment {experiment_id} lacks timestamps")
        elif args.mode == "solve" and status in {"PLANNED", "RUNNING"}:
            warnings.append(f"solve experiment {experiment_id} is not terminal")

    if args.mode == "solve" and set(contract_stages) - succeeded_stage_ids:
        errors.append(f"contract stages lack successful experiments: {sorted(set(contract_stages) - succeeded_stage_ids)}")
    if args.mode == "probe" and manifest.get("status") in {"COMPLETE", "COMPLETE_WITH_LIMITATIONS", "NEEDS_REVISION"} and not experiments and feedback is None:
        errors.append("completed probe has neither a real experiment nor structured blocking feedback")

    validation_by_id = {item.get("id"): item for item in as_dict_list(validation_plan.get("tests")) if item.get("id")}
    result_items = as_dict_list(validation.get("results"))
    result_test_ids = [item.get("test_id") for item in result_items]
    if duplicates(result_test_ids):
        errors.append("validation results contain duplicate test IDs")
    if set(result_test_ids) != contract_tests:
        errors.append("validation results must contain exactly the contract validation test IDs")
    critical_validation_failure = False
    limitation_validation_failure = False
    for item in result_items:
        test_id = item.get("test_id")
        planned_action = validation_by_id.get(test_id, {}).get("failure_action")
        if planned_action and item.get("failure_action") not in {planned_action, "none"}:
            errors.append(f"validation result {test_id} changes the planned failure action")
        status = item.get("status")
        if status == "FAILED":
            action = item.get("failure_action")
            if action in CRITICAL_FAILURE_ACTIONS:
                critical_validation_failure = True
            elif action == "report-limitation":
                limitation_validation_failure = True
                if not item.get("limitation"):
                    errors.append(f"failed validation {test_id} marked as limitation without limitation text")
        if args.mode == "solve" and status == "NOT_RUN":
            errors.append(f"solve validation {test_id} was not run")
        if args.mode == "solve" and status in {"PASSED", "FAILED", "INCONCLUSIVE"} and not item.get("evidence_refs"):
            errors.append(f"validation {test_id} has no evidence refs")
    if critical_validation_failure and manifest.get("status") != "NEEDS_REVISION":
        errors.append("critical validation failure must set results status NEEDS_REVISION")
    if validation.get("status") == "FEEDBACK_REQUIRED" and feedback is None:
        errors.append("validation requires feedback but modeling-feedback.yaml is missing")

    manifest_outputs = as_dict_list(manifest.get("contract_outputs"))
    manifest_output_ids = [item.get("output_id") for item in manifest_outputs]
    if duplicates(manifest_output_ids):
        errors.append("results manifest contains duplicate output IDs")
    if set(manifest_output_ids) != set(contract_outputs):
        errors.append("results manifest must contain exactly the contract output IDs")
    for item in manifest_outputs:
        output_id = item.get("output_id")
        contract_output = contract_outputs.get(output_id, {})
        try:
            expected_path = expected_solver_output_path(contract_output.get("destination", ""))
            if item.get("path") != expected_path:
                errors.append(f"contract output {output_id} path does not match the contracted destination")
        except ValueError as exc:
            errors.append(str(exc))
        if item.get("status") == "PRODUCED":
            check_hashed_path(project_root, item.get("path"), item.get("sha256"), f"contract output {output_id}", errors)
            source_experiments = set(item.get("experiment_ids", []))
            if not source_experiments or not source_experiments <= succeeded_ids:
                errors.append(f"produced output {output_id} is not linked only to successful experiments")
            matching_artifact = any(
                artifact.get("path") == item.get("path") and artifact.get("sha256") == item.get("sha256")
                for experiment_id in source_experiments
                for artifact in as_dict_list(experiment_by_id.get(experiment_id, {}).get("output_artifacts"))
            )
            if not matching_artifact:
                errors.append(f"produced output {output_id} is absent from its source experiment artifacts")
            if not item.get("acceptance_evidence_refs"):
                errors.append(f"produced output {output_id} has no acceptance evidence")
        elif args.mode == "solve":
            errors.append(f"solve required output {output_id} was not produced")

    result_status_by_id = {item.get("test_id"): item.get("status") for item in result_items}
    known_evidence_ids = set(experiment_by_id) | set(result_test_ids)
    for claim in as_dict_list(manifest.get("claims")):
        for evidence_ref in claim.get("evidence_refs", []):
            evidence_id = evidence_ref.partition("#")[2] or evidence_ref
            problem = evidence_ref_error(project_root, evidence_ref, known_evidence_ids)
            if problem:
                errors.append(f"claim {claim.get('id')} has invalid evidence {evidence_ref}: {problem}")
                continue
            if manifest.get("ready_for_writing") and evidence_id in experiment_by_id and evidence_id not in succeeded_ids:
                errors.append(f"claim {claim.get('id')} relies on a non-successful experiment: {evidence_id}")
            if manifest.get("ready_for_writing") and evidence_id in result_status_by_id and result_status_by_id[evidence_id] != "PASSED":
                errors.append(f"claim {claim.get('id')} relies on a validation result that did not pass: {evidence_id}")

    disclosed_failed = set(manifest.get("disclosed_failed_experiment_ids", []))
    if not disclosed_failed <= failed_ids:
        errors.append("results manifest discloses unknown or non-failed experiments")
    undisclosed_failed = failed_ids - disclosed_failed
    if undisclosed_failed:
        message = f"failed experiments are not disclosed: {sorted(undisclosed_failed)}"
        (errors if args.mode == "solve" else warnings).append(message)

    if args.mode == "probe" and manifest.get("ready_for_writing"):
        errors.append("probe can never be ready_for_writing")
    if args.mode == "solve" and manifest.get("ready_for_writing"):
        if validation.get("status") not in {"COMPLETE", "COMPLETE_WITH_LIMITATIONS"}:
            errors.append("paper handoff requires completed validation results")
        if manifest.get("status") not in {"COMPLETE", "COMPLETE_WITH_LIMITATIONS"}:
            errors.append("ready_for_writing requires COMPLETE or COMPLETE_WITH_LIMITATIONS")
        if critical_validation_failure:
            errors.append("critical validation failure prevents paper handoff")
        if limitation_validation_failure and manifest.get("status") != "COMPLETE_WITH_LIMITATIONS":
            errors.append("limitation validation failure requires COMPLETE_WITH_LIMITATIONS")
    if manifest.get("status") == "NEEDS_REVISION" and feedback is None:
        errors.append("NEEDS_REVISION requires modeling-feedback.yaml")
    if manifest.get("feedback_ref"):
        try:
            referenced_feedback = resolve_inside(project_root, manifest.get("feedback_ref"))
            if referenced_feedback is None or not referenced_feedback.is_file():
                errors.append("results manifest feedback_ref is missing")
        except ValueError as exc:
            errors.append(str(exc))

    for group in ("environment_files", "input_files", "source_files", "config_files"):
        for item in as_dict_list(reproducibility.get(group)):
            check_hashed_path(project_root, item.get("path"), item.get("sha256"), f"reproducibility {group}", errors)
    repro_commands = as_dict_list(reproducibility.get("commands"))
    command_ids = [item.get("id") for item in repro_commands]
    if duplicates(command_ids):
        errors.append("reproducibility manifest contains duplicate command IDs")
    verified_commands = set(reproducibility.get("verified_command_ids", []))
    if not verified_commands <= set(command_ids):
        errors.append("verified reproducibility command IDs are unknown")
    recorded_command_text = {item.get("command") for item in repro_commands}
    for experiment_id in succeeded_ids:
        command = experiment_by_id[experiment_id].get("command")
        if command not in recorded_command_text:
            errors.append(f"successful experiment {experiment_id} command is absent from reproducibility manifest")
    experiment_seeds = {item.get("seed") for item in experiments if item.get("seed") is not None}
    if not experiment_seeds <= set(reproducibility.get("seeds", [])):
        errors.append("reproducibility manifest omits experiment seeds")
    if args.mode == "solve" and manifest.get("ready_for_writing"):
        if reproducibility.get("status") != "COMPLETE":
            errors.append("paper handoff requires COMPLETE reproducibility manifest")
        if not verified_commands:
            errors.append("paper handoff requires at least one verified reproduction command")
        recorded_sources = {item.get("path") for item in as_dict_list(reproducibility.get("source_files"))}
        planned_sources = {path for stage in plan_stages for path in stage.get("source_files", [])}
        if not planned_sources <= recorded_sources:
            errors.append("reproducibility manifest omits planned source files")
        recorded_inputs = {item.get("path") for item in as_dict_list(reproducibility.get("input_files"))}
        required_inputs = {
            item.get("path")
            for item in as_dict_list(intake.get("data_bindings"))
            if item.get("required_by_stage_ids") and item.get("observed_sha256")
        }
        if not required_inputs <= recorded_inputs:
            errors.append("reproducibility manifest omits required raw inputs")

    audit_checks = as_dict_list(audit.get("checks"))
    audit_names = [item.get("dimension") for item in audit_checks]
    if set(audit_names) != AUDIT_DIMENSIONS or duplicates(audit_names):
        errors.append("solver audit dimensions are incomplete or duplicated")
    if any(item.get("status") == "FAIL" for item in audit_checks) and manifest.get("ready_for_writing"):
        errors.append("solver audit FAIL prevents paper handoff")
    if manifest.get("ready_for_writing") and audit.get("overall_status") not in {"PASS", "PASS_WITH_WARNINGS"}:
        errors.append("solver audit is not ready for paper handoff")

    if feedback is not None:
        if feedback.get("run_id") != run_id:
            errors.append("modeling feedback run_id does not match intake")
        for evidence_ref in feedback.get("evidence_refs", []):
            problem = evidence_ref_error(project_root, evidence_ref, known_evidence_ids)
            if problem:
                errors.append(f"modeling feedback has invalid evidence {evidence_ref}: {problem}")

    ready_for_writing = bool(manifest.get("ready_for_writing")) and args.mode == "solve"
    if args.mode == "solve" and not ready_for_writing:
        errors.append("solve package is not ready_for_writing")

    metrics = {
        "upstream_hash_integrity": 0.0 if any("upstream SHA-256" in item or "snapshot" in item for item in errors) else 1.0,
        "contract_stage_coverage": (len(succeeded_stage_ids & set(contract_stages)) / len(contract_stages)) if contract_stages else 0.0,
        "validation_completion": (sum(item.get("status") != "NOT_RUN" for item in result_items) / len(contract_tests)) if contract_tests else 1.0,
        "required_output_completion": (sum(item.get("status") == "PRODUCED" for item in manifest_outputs) / len(contract_outputs)) if contract_outputs else 1.0,
        "failed_run_disclosure": 1.0 if not failed_ids else len(disclosed_failed & failed_ids) / len(failed_ids),
    }
    if errors:
        status = "FAIL"
    elif args.mode == "probe":
        terminal_probe = manifest.get("status") in {"COMPLETE", "COMPLETE_WITH_LIMITATIONS", "NEEDS_REVISION", "BLOCKED"}
        status = "PROBE_COMPLETE" if terminal_probe else "EXPLORATORY"
    else:
        status = "PASS"
    return emit(args.json_output, args.mode, status, ready_for_writing and not errors, errors, warnings, metrics)


def emit(json_output: bool, mode: str, status: str, ready_for_writing: bool, errors: list[str], warnings: list[str], metrics: dict[str, float]) -> int:
    payload = {
        "status": status,
        "mode": mode,
        "ready_for_writing": ready_for_writing,
        "errors": errors,
        "warnings": warnings,
        "metrics": metrics,
    }
    if json_output:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"STATUS: {status}")
        print(f"MODE: {mode}")
        print(f"READY_FOR_WRITING: {str(ready_for_writing).lower()}")
        for key, value in metrics.items():
            print(f"{key} = {value:.3f}")
        for warning in warnings:
            print(f"WARNING: {warning}")
        for error in errors:
            print(f"ERROR: {error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
