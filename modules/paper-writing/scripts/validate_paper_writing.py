#!/usr/bin/env python3
"""Validate evidence grounding and delivery readiness for paper-writing."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


MODULE_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_FILES = {
    "intake.yaml": "intake.schema.json",
    "argument-map.yaml": "argument-map.schema.json",
    "terminology-ledger.yaml": "terminology-ledger.schema.json",
    "source-map.yaml": "source-map.schema.json",
    "writing-audit.yaml": "writing-audit.schema.json",
}
AUDIT_DIMENSIONS = {
    "input_integrity", "requirement_coverage", "claim_evidence", "terminology",
    "numerical_consistency", "figures_tables", "citations", "limitations",
    "competition_format", "render_quality",
}


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


def validate_schema(data: Any, schema_path: Path) -> list[str]:
    import jsonschema  # type: ignore

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    errors = []
    for error in sorted(validator.iter_errors(data), key=lambda item: list(item.path)):
        where = ".".join(str(part) for part in error.path) or "$"
        errors.append(f"{where}: {error.message}")
    return errors


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_inside(root: Path, value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value.split("#", 1)[0])
    if not path.is_absolute():
        path = root / path
    path = path.resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"path escapes project root: {value}") from exc
    return path


def duplicates(values: list[str]) -> set[str]:
    seen: set[str] = set()
    result: set[str] = set()
    for value in values:
        if value in seen:
            result.add(value)
        seen.add(value)
    return result


def emit(json_output: bool, mode: str, status: str, ready: bool, errors: list[str], warnings: list[str], metrics: dict[str, float]) -> int:
    payload = {"status": status, "mode": mode, "ready_for_submission": ready, "errors": errors, "warnings": warnings, "metrics": metrics}
    if json_output:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"STATUS: {status}")
        print(f"MODE: {mode}")
        print(f"READY_FOR_SUBMISSION: {str(ready).lower()}")
        for key, value in metrics.items():
            print(f"{key} = {value:.3f}")
        for warning in warnings:
            print(f"WARNING: {warning}")
        for error in errors:
            print(f"ERROR: {error}")
    return 1 if errors else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--mode", choices=["draft", "final"], default="draft")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    root = args.project_root.resolve()
    paper = root / "paper"
    errors: list[str] = []
    warnings: list[str] = []
    loaded: dict[str, dict[str, Any]] = {}
    for name, schema_name in SCHEMA_FILES.items():
        path = paper / name
        if not path.is_file():
            errors.append(f"missing paper file: paper/{name}")
            continue
        try:
            data = load_structured(path)
            errors.extend(f"{name}: {item}" for item in validate_schema(data, MODULE_ROOT / "schemas" / schema_name))
            loaded[name] = data
        except (OSError, ValueError, ImportError) as exc:
            errors.append(str(exc))
    manuscript_path = paper / "manuscript.md"
    references_path = paper / "references.bib"
    if not manuscript_path.is_file():
        errors.append("missing paper/manuscript.md")
    if not references_path.is_file():
        errors.append("missing paper/references.bib")
    if len(loaded) != len(SCHEMA_FILES):
        return emit(args.json_output, args.mode, "FAIL", False, errors, warnings, {})

    intake = loaded["intake.yaml"]
    argument = loaded["argument-map.yaml"]
    ledger = loaded["terminology-ledger.yaml"]
    source_map = loaded["source-map.yaml"]
    audit = loaded["writing-audit.yaml"]
    if intake.get("mode") != args.mode or argument.get("mode") != args.mode:
        errors.append("paper package mode does not match requested mode")
    if intake.get("status") != "READY" or not intake.get("gate", {}).get("eligible"):
        errors.append("paper intake is not eligible")

    for item in intake.get("upstream_files", []):
        path_value = item.get("path")
        try:
            path = resolve_inside(root, path_value)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if path is None or not path.is_file():
            message = f"upstream file is missing: {path_value}"
            (errors if item.get("required") else warnings).append(message)
        elif item.get("sha256") != sha256_file(path):
            errors.append(f"upstream SHA-256 changed: {path_value}")

    solver_manifest_path = root / "solver" / "results-manifest.yaml"
    validation_path = root / "solver" / "validation-results.yaml"
    reproducibility_path = root / "solver" / "reproducibility.json"
    solver_manifest: dict[str, Any] = {}
    validation: dict[str, Any] = {}
    reproducibility: dict[str, Any] = {}
    for path, target, label in ((solver_manifest_path, "solver", "results manifest"), (validation_path, "validation", "validation results"), (reproducibility_path, "reproducibility", "reproducibility manifest")):
        if path.is_file():
            try:
                data = load_structured(path)
                if target == "solver": solver_manifest = data
                elif target == "validation": validation = data
                else: reproducibility = data
            except ValueError as exc:
                errors.append(str(exc))
        elif args.mode == "final":
            errors.append(f"missing solver {label}")
    if args.mode == "final":
        if solver_manifest.get("ready_for_writing") is not True:
            errors.append("final paper requires solver ready_for_writing")
        if validation.get("status") not in {"COMPLETE", "COMPLETE_WITH_LIMITATIONS"}:
            errors.append("final paper requires completed solver validation")
        if reproducibility.get("status") != "COMPLETE":
            errors.append("final paper requires complete solver reproducibility")

    sections = {item.get("id") for item in argument.get("sections", [])}
    terms = ledger.get("terms", [])
    duplicate_terms = duplicates([str(item.get("canonical")) for item in terms])
    if duplicate_terms:
        warnings.append(f"terminology ledger has duplicate canonical terms: {sorted(duplicate_terms)}")
    items = source_map.get("items", [])
    ids = [item.get("id") for item in items]
    anchors = [item.get("anchor") for item in items]
    if duplicates(ids): errors.append("source map contains duplicate claim IDs")
    if duplicates(anchors): errors.append("source map contains duplicate anchors")
    claim_ids = set(ids)
    for section in argument.get("sections", []):
        unknown = set(section.get("claim_ids", [])) - claim_ids
        if unknown:
            errors.append(f"argument section {section.get('id')} references unknown claims")
    citation_key_list = [item.get("key") for item in source_map.get("citation_records", [])]
    citation_records = {item.get("key"): item for item in source_map.get("citation_records", [])}
    if duplicates(citation_key_list):
        errors.append("source map contains duplicate citation keys")
    manuscript = manuscript_path.read_text(encoding="utf-8") if manuscript_path.is_file() else ""
    if args.mode == "final":
        for section in argument.get("sections", []):
            expected_heading = f"## {section.get('title')}"
            if expected_heading not in manuscript:
                errors.append(f"final manuscript is missing planned section heading: {section.get('title')}")
    requirement_ids = set(intake.get("requirement_ids", []))
    supported_requirements: set[str] = set()
    supported_core = 0
    for item in items:
        item_id = item.get("id")
        if item.get("section_id") is not None and item.get("section_id") not in sections:
            errors.append(f"claim {item_id} references unknown section")
        if f"<!-- claim: {item.get('anchor')} -->" not in manuscript:
            errors.append(f"manuscript is missing claim anchor {item.get('anchor')}")
        for citation_key in item.get("citation_keys", []):
            record = citation_records.get(citation_key)
            if record is None:
                errors.append(f"claim {item_id} references unknown citation key {citation_key}")
            elif args.mode == "final" and not record.get("verified"):
                errors.append(f"final claim {item_id} uses unverified citation {citation_key}")
        for ref in item.get("evidence_refs", []):
            if ref.startswith(("claim-", "val-", "out-", "exp-")):
                continue
            try:
                path = resolve_inside(root, ref)
                if path is None or not path.exists():
                    errors.append(f"claim {item_id} references missing evidence {ref}")
            except ValueError as exc:
                errors.append(str(exc))
        if item.get("importance") == "core" and item.get("support_status") in {"supported", "bounded"}:
            supported_core += 1
            supported_requirements.update(item.get("requirement_ids", []))
            if item.get("support_status") == "bounded" and not item.get("boundary"):
                errors.append(f"bounded core claim {item_id} lacks a boundary")
        if args.mode == "final" and item.get("importance") == "core":
            if item.get("support_status") not in {"supported", "bounded"}:
                errors.append(f"core claim {item_id} is not evidence-supported")
            if not item.get("evidence_refs") and not item.get("citation_keys"):
                errors.append(f"core claim {item_id} has no evidence or citation")
    if args.mode == "final" and not requirement_ids <= supported_requirements:
        errors.append(f"requirements without supported paper answers: {sorted(requirement_ids - supported_requirements)}")
    if args.mode == "final" and "[[" in manuscript:
        errors.append("final manuscript contains unresolved placeholders")
    if args.mode == "final" and not argument.get("core_argument"):
        errors.append("final argument map lacks a core argument")
    if source_map.get("citation_records") and references_path.is_file() and not references_path.read_text(encoding="utf-8").strip():
        errors.append("citation records exist but references.bib is empty")

    check_names = [item.get("dimension") for item in audit.get("checks", [])]
    if set(check_names) != AUDIT_DIMENSIONS or duplicates(check_names):
        errors.append("writing audit dimensions are incomplete or duplicated")
    if args.mode == "final":
        if any(item.get("status") == "FAIL" for item in audit.get("checks", [])):
            errors.append("writing audit has FAIL")
        if audit.get("overall_status") not in {"PASS", "PASS_WITH_WARNINGS"}:
            errors.append("writing audit is not ready for final delivery")

    feedback_path = paper / "writing-feedback.yaml"
    if feedback_path.is_file():
        try:
            feedback = load_structured(feedback_path)
            errors.extend(f"writing-feedback.yaml: {item}" for item in validate_schema(feedback, MODULE_ROOT / "schemas" / "writing-feedback.schema.json"))
            if args.mode == "final" and feedback.get("status") == "OPEN":
                errors.append("final paper has unresolved writing feedback")
        except (OSError, ValueError, ImportError) as exc:
            errors.append(str(exc))

    metrics = {
        "upstream_hash_integrity": 0.0 if any("SHA-256" in item for item in errors) else 1.0,
        "requirement_answer_coverage": len(supported_requirements & requirement_ids) / len(requirement_ids) if requirement_ids else 1.0,
        "core_claim_support": supported_core / len([item for item in items if item.get("importance") == "core"]) if items else 0.0,
        "claim_anchor_coverage": sum(f"<!-- claim: {item.get('anchor')} -->" in manuscript for item in items) / len(items) if items else 1.0,
    }
    ready = args.mode == "final" and not errors
    if errors:
        status = "FAIL"
    elif args.mode == "draft":
        status = "DRAFT_READY"
    else:
        status = "PASS"
    return emit(args.json_output, args.mode, status, ready, errors, warnings, metrics)


if __name__ == "__main__":
    raise SystemExit(main())
