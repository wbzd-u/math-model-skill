from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_ROOT = Path(__file__).resolve().parents[1]
INIT = MODULE_ROOT / "scripts" / "init_numerical_solving.py"
VALIDATE = MODULE_ROOT / "scripts" / "validate_numerical_solving.py"
MODELING_TEST_PATH = MODULE_ROOT.parent / "modeling-selection" / "tests" / "test_modeling_selection.py"


def load_modeling_fixture_module():
    spec = importlib.util.spec_from_file_location("modeling_selection_fixture", MODELING_TEST_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load modeling-selection test fixture")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MODELING_FIXTURE = load_modeling_fixture_module()


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


class NumericalSolvingScriptsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.project = self.root / "project"
        fixture = MODELING_FIXTURE.ModelingSelectionScriptsTest(methodName="runTest")
        fixture.project = self.project
        fixture.root = self.root
        fixture.write_analysis(self.project, gate_status="PASS")
        result = fixture.run_initializer(self.project)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        fixture.complete_package(self.project)
        source = self.project / "sources" / "input.csv"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("x\n0.25\n0.75\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    @staticmethod
    def load(project: Path, directory: str, name: str) -> dict:
        return json.loads((project / directory / name).read_text(encoding="utf-8"))

    @staticmethod
    def save(project: Path, directory: str, name: str, payload: dict) -> None:
        write_json(project / directory / name, payload)

    @staticmethod
    def run_initializer(project: Path, mode: str, *extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(INIT), "--project-root", str(project), "--mode", mode, *extra],
            capture_output=True,
            text=True,
        )

    @staticmethod
    def run_validator(project: Path, mode: str, json_output: bool = False) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(VALIDATE), "--project-root", str(project), "--mode", mode]
        if json_output:
            command.append("--json")
        return subprocess.run(command, capture_output=True, text=True)

    def make_contract_exploratory(self) -> None:
        contract = self.load(self.project, "modeling", "implementation-contract.yaml")
        contract["status"] = "EXPLORATORY"
        self.save(self.project, "modeling", "implementation-contract.yaml", contract)

    def initialize_solve(self) -> None:
        result = self.run_initializer(self.project, "solve")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def complete_solver(self) -> None:
        solver = self.project / "solver"
        source = solver / "src" / "solve.py"
        source.write_text("print('completed')\n", encoding="utf-8")
        result_file = solver / "results" / "score.csv"
        result_file.write_text("score\n0.25\n0.75\n", encoding="utf-8")
        log_file = solver / "logs" / "exp-001.log"
        log_file.write_text("status=optimal\nconstraints=passed\n", encoding="utf-8")

        plan = self.load(self.project, "solver", "run-plan.yaml")
        plan.update({"status": "READY", "language": "Python"})
        stage = plan["stages"][0]
        stage["input_bindings"] = [
            {
                "contract_ref": "var-001",
                "binding_kind": "field",
                "binding_ref": "sources/input.csv#x",
                "source_ref": "analysis/entity-variable-map.yaml#var-001",
                "unit_policy": "dimensionless; no conversion",
                "status": "resolved",
            }
        ]
        stage["output_bindings"] = [
            {"contract_ref": "dvar-001", "path": "solver/results/score.csv", "format": "text/csv"}
        ]
        stage["source_files"] = ["solver/src/solve.py"]
        stage["commands"] = ["python solver/src/solve.py"]
        stage["invariant_checks"] = [
            {
                "statement": "Preserve the req-001 score meaning.",
                "method": "Check representative values and bounds.",
                "status": "PASSED",
                "evidence_ref": "solver/logs/exp-001.log",
            }
        ]
        stage["validation_test_ids"] = ["val-001", "val-002"]
        stage["provenance_record_ids"] = []
        stage["status"] = "COMPLETE"
        self.save(self.project, "solver", "run-plan.yaml", plan)

        provenance = self.load(self.project, "solver", "implementation-provenance.yaml")
        provenance["status"] = "READY"
        provenance["custom_components"] = [
            {
                "component_ids": ["cmp-001", "cmp-002"],
                "reason": "The contract mapping is trivial project-specific glue around bounds checks.",
                "alternatives_considered": ["Python standard arithmetic"],
                "rejection_reasons": ["No external numerical kernel is needed."],
                "correctness_checks": ["Hand-computed interior and boundary examples."],
            }
        ]
        self.save(self.project, "solver", "implementation-provenance.yaml", provenance)

        input_file = self.project / "sources" / "input.csv"
        experiment = {
            "schema_version": "0.1.0",
            "mode": "solve",
            "run_id": "solve-001",
            "experiments": [
                {
                    "id": "exp-001",
                    "kind": "main",
                    "stage_ids": ["run-01"],
                    "status": "SUCCEEDED",
                    "command": "python solver/src/solve.py",
                    "working_directory": ".",
                    "input_artifacts": [{"path": "sources/input.csv", "sha256": sha256_file(input_file)}],
                    "config_paths": [],
                    "seed": None,
                    "started_at": "2026-07-13T10:00:00+08:00",
                    "finished_at": "2026-07-13T10:00:01+08:00",
                    "exit_code": 0,
                    "output_artifacts": [{"path": "solver/results/score.csv", "sha256": sha256_file(result_file), "kind": "result-table"}],
                    "log_path": "solver/logs/exp-001.log",
                    "metrics": [{"name": "bound violations", "value": 0, "unit": "count"}],
                    "invariant_results": [{"statement": "Preserve the req-001 score meaning.", "status": "PASSED", "evidence_ref": "solver/logs/exp-001.log"}],
                    "failure": None,
                }
            ],
        }
        self.save(self.project, "solver", "experiment-registry.yaml", experiment)

        validation = self.load(self.project, "solver", "validation-results.yaml")
        validation["status"] = "COMPLETE"
        for item in validation["results"]:
            item.update(
                {
                    "status": "PASSED",
                    "procedure_executed": "Executed representative values and boundary checks.",
                    "metric_values": [{"metric": "violation count", "value": 0, "unit": "count"}],
                    "criteria_evaluation": "The declared criterion passed.",
                    "evidence_refs": ["exp-001", "solver/logs/exp-001.log"],
                    "limitation": None,
                }
            )
        self.save(self.project, "solver", "validation-results.yaml", validation)

        manifest = self.load(self.project, "solver", "results-manifest.yaml")
        manifest.update({"status": "COMPLETE", "ready_for_writing": True})
        manifest["contract_outputs"] = [
            {
                "output_id": "out-001",
                "status": "PRODUCED",
                "path": "solver/results/score.csv",
                "sha256": sha256_file(result_file),
                "experiment_ids": ["exp-001"],
                "acceptance_evidence_refs": ["val-001", "val-002"],
                "description": "Traceable score table.",
                "limitations": [],
            }
        ]
        manifest["claims"] = [
            {
                "id": "claim-001",
                "statement": "The computed scores satisfy the declared bounds on the supplied inputs.",
                "subproblem_ids": ["sp-01"],
                "evidence_refs": ["exp-001", "val-002"],
                "scope": "Only the supplied fixture inputs.",
                "limitations": [],
            }
        ]
        self.save(self.project, "solver", "results-manifest.yaml", manifest)

        reproducibility = self.load(self.project, "solver", "reproducibility.json")
        reproducibility.update(
            {
                "status": "COMPLETE",
                "input_files": [{"path": "sources/input.csv", "sha256": sha256_file(input_file)}],
                "source_files": [{"path": "solver/src/solve.py", "sha256": sha256_file(source)}],
                "commands": [
                    {
                        "id": "cmd-001",
                        "command": "python solver/src/solve.py",
                        "working_directory": ".",
                        "experiment_ids": ["exp-001"],
                    }
                ],
                "verified_command_ids": ["cmd-001"],
            }
        )
        self.save(self.project, "solver", "reproducibility.json", reproducibility)

        audit = self.load(self.project, "solver", "solver-audit.yaml")
        for item in audit["checks"]:
            item.update({"status": "PASS", "evidence": ["solver package"], "findings": [], "required_actions": []})
        audit["overall_status"] = "PASS"
        self.save(self.project, "solver", "solver-audit.yaml", audit)

    def test_probe_accepts_exploratory_contract(self) -> None:
        self.make_contract_exploratory()
        result = self.run_initializer(self.project, "probe")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        intake = self.load(self.project, "solver", "intake.yaml")
        self.assertEqual(intake["mode"], "probe")
        self.assertEqual(intake["contract_status"], "EXPLORATORY")

    def test_solve_rejects_exploratory_contract(self) -> None:
        self.make_contract_exploratory()
        result = self.run_initializer(self.project, "solve")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("solve requires READY", result.stdout)

    def test_solve_accepts_ready_handoff(self) -> None:
        self.initialize_solve()
        intake = self.load(self.project, "solver", "intake.yaml")
        self.assertEqual(intake["status"], "READY")
        self.assertFalse(self.load(self.project, "solver", "results-manifest.yaml")["ready_for_writing"])

    def test_contract_snapshot_mismatch_blocks_initialization(self) -> None:
        contract = self.load(self.project, "modeling", "implementation-contract.yaml")
        contract["input_snapshot"]["model_spec_sha256"] = "0" * 64
        self.save(self.project, "modeling", "implementation-contract.yaml", contract)
        result = self.run_initializer(self.project, "probe")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("snapshot mismatch", result.stdout)

    def test_existing_solver_requires_force(self) -> None:
        self.initialize_solve()
        result = self.run_initializer(self.project, "solve")
        self.assertEqual(result.returncode, 2)
        result = self.run_initializer(self.project, "solve", "--force")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_probe_skeleton_is_exploratory_not_failure(self) -> None:
        self.make_contract_exploratory()
        self.assertEqual(self.run_initializer(self.project, "probe").returncode, 0)
        result = self.run_validator(self.project, "probe", json_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "EXPLORATORY")
        self.assertFalse(payload["ready_for_writing"])

    def test_probe_allows_documented_generated_diagnostic_inputs(self) -> None:
        self.make_contract_exploratory()
        self.assertEqual(self.run_initializer(self.project, "probe").returncode, 0)
        config = self.project / "solver" / "configs" / "boundaries.json"
        config.write_text("{\"values\": [-1, 0, 1, 2]}\n", encoding="utf-8")
        plan = self.load(self.project, "solver", "run-plan.yaml")
        plan["stages"][0]["input_bindings"].append(
            {
                "contract_ref": "var-001:diagnostic-boundaries",
                "binding_kind": "generated",
                "binding_ref": "solver/configs/boundaries.json",
                "source_ref": "modeling/validation-plan.yaml#val-002",
                "unit_policy": "dimensionless boundary cases",
                "status": "resolved",
            }
        )
        plan["simplifications"] = [
            {
                "id": "simp-001",
                "description": "Use a finite diagnostic boundary set.",
                "affected_stage_ids": ["run-01"],
                "justification": "The probe checks boundary behavior before formal solving.",
                "unsupported_claims": ["The diagnostic set is not the final problem result."],
            }
        ]
        self.save(self.project, "solver", "run-plan.yaml", plan)
        result = self.run_validator(self.project, "probe")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("documented diagnostic input", result.stdout)

    def test_solve_skeleton_is_not_ready(self) -> None:
        self.initialize_solve()
        result = self.run_validator(self.project, "solve")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not ready_for_writing", result.stdout)

    def test_completed_solve_passes(self) -> None:
        self.initialize_solve()
        self.complete_solver()
        result = self.run_validator(self.project, "solve", json_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "PASS")
        self.assertTrue(payload["ready_for_writing"])

    def test_evidence_refs_may_include_file_and_stable_id_anchor(self) -> None:
        self.initialize_solve()
        self.complete_solver()
        manifest = self.load(self.project, "solver", "results-manifest.yaml")
        manifest["claims"][0]["evidence_refs"] = [
            "solver/experiment-registry.yaml#exp-001",
            "solver/validation-results.yaml#val-002",
        ]
        self.save(self.project, "solver", "results-manifest.yaml", manifest)
        result = self.run_validator(self.project, "solve")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_probe_can_never_be_ready_for_writing(self) -> None:
        self.make_contract_exploratory()
        self.assertEqual(self.run_initializer(self.project, "probe").returncode, 0)
        manifest = self.load(self.project, "solver", "results-manifest.yaml")
        manifest["ready_for_writing"] = True
        self.save(self.project, "solver", "results-manifest.yaml", manifest)
        result = self.run_validator(self.project, "probe")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("probe can never", result.stdout)

    def test_upstream_change_after_initialization_fails(self) -> None:
        self.initialize_solve()
        model_spec = self.load(self.project, "modeling", "model-specification.yaml")
        model_spec["components"][0]["purpose"] = "Changed after solver intake."
        self.save(self.project, "modeling", "model-specification.yaml", model_spec)
        result = self.run_validator(self.project, "solve")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("upstream SHA-256 changed", result.stdout)

    def test_path_escape_fails(self) -> None:
        self.make_contract_exploratory()
        self.assertEqual(self.run_initializer(self.project, "probe").returncode, 0)
        plan = self.load(self.project, "solver", "run-plan.yaml")
        plan["environment_files"] = ["../outside.txt"]
        self.save(self.project, "solver", "run-plan.yaml", plan)
        result = self.run_validator(self.project, "probe")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("escapes project root", result.stdout)

    def test_unsafe_contract_output_blocks_probe_initialization(self) -> None:
        self.make_contract_exploratory()
        contract = self.load(self.project, "modeling", "implementation-contract.yaml")
        contract["required_outputs"][0]["destination"] = "../outside.csv"
        self.save(self.project, "modeling", "implementation-contract.yaml", contract)
        result = self.run_initializer(self.project, "probe")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unsafe required output destination", result.stdout)

    def test_unlicensed_adapted_code_fails_even_in_probe(self) -> None:
        self.make_contract_exploratory()
        self.assertEqual(self.run_initializer(self.project, "probe").returncode, 0)
        provenance = self.load(self.project, "solver", "implementation-provenance.yaml")
        provenance["sources"] = [
            {
                "id": "ext-001",
                "kind": "source-code",
                "title": "Public repository without a license",
                "canonical_url": "https://example.invalid/repo",
                "official_docs_url": None,
                "version_or_identifier": "commit-1",
                "repository_commit": "commit-1",
                "accessed_at": "2026-07-13",
                "verification_status": "verified-primary",
                "license": {"spdx_id": None, "status": "unknown", "evidence_ref": None, "compatibility": "unassessed", "obligations": []},
                "decision": "selected",
            }
        ]
        provenance["reuse_records"] = [
            {
                "id": "reuse-001",
                "component_ids": ["cmp-002"],
                "execution_stage_ids": ["run-01"],
                "source_ids": ["ext-001"],
                "reuse_kind": "adapted-code",
                "upstream_locators": ["src/model.py"],
                "local_paths": ["solver/src/model.py"],
                "purpose": "Implement the main component.",
                "modifications": ["Renamed variables."],
                "semantic_deviations": [],
                "attribution_required": True,
                "attribution_locations": [],
                "obligations_satisfied": False,
                "validation_test_ids": ["val-002"],
            }
        ]
        self.save(self.project, "solver", "implementation-provenance.yaml", provenance)
        result = self.run_validator(self.project, "probe")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("verified compatible license", result.stdout)

    def test_licensed_library_api_can_replace_custom_implementation(self) -> None:
        self.initialize_solve()
        self.complete_solver()
        provenance = self.load(self.project, "solver", "implementation-provenance.yaml")
        provenance["custom_components"] = []
        provenance["sources"] = [
            {
                "id": "ext-001",
                "kind": "library",
                "title": "Example numerical library",
                "canonical_url": "https://example.invalid/library",
                "official_docs_url": "https://example.invalid/library/docs",
                "version_or_identifier": "1.0.0",
                "repository_commit": None,
                "accessed_at": "2026-07-13",
                "verification_status": "verified-primary",
                "license": {"spdx_id": "BSD-3-Clause", "status": "verified", "evidence_ref": "https://example.invalid/library/license", "compatibility": "compatible", "obligations": []},
                "decision": "selected",
            }
        ]
        provenance["reuse_records"] = [
            {
                "id": "reuse-001",
                "component_ids": ["cmp-001", "cmp-002"],
                "execution_stage_ids": ["run-01"],
                "source_ids": ["ext-001"],
                "reuse_kind": "package-api",
                "upstream_locators": ["public API"],
                "local_paths": ["solver/src/solve.py"],
                "purpose": "Use a maintained public API for numeric clipping.",
                "modifications": [],
                "semantic_deviations": [],
                "attribution_required": False,
                "attribution_locations": ["solver/solver-report.md"],
                "obligations_satisfied": True,
                "validation_test_ids": ["val-001", "val-002"],
            }
        ]
        self.save(self.project, "solver", "implementation-provenance.yaml", provenance)
        plan = self.load(self.project, "solver", "run-plan.yaml")
        plan["stages"][0]["provenance_record_ids"] = ["reuse-001"]
        self.save(self.project, "solver", "run-plan.yaml", plan)
        result = self.run_validator(self.project, "solve")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_paper_implementation_requires_paper_source(self) -> None:
        self.initialize_solve()
        self.complete_solver()
        provenance = self.load(self.project, "solver", "implementation-provenance.yaml")
        provenance["custom_components"] = []
        provenance["sources"] = [
            {
                "id": "ext-001",
                "kind": "official-document",
                "title": "Not a paper",
                "canonical_url": "https://example.invalid/docs",
                "official_docs_url": "https://example.invalid/docs",
                "version_or_identifier": "2026",
                "repository_commit": None,
                "accessed_at": "2026-07-13",
                "verification_status": "verified-primary",
                "license": {"spdx_id": None, "status": "not-applicable", "evidence_ref": None, "compatibility": "not-applicable", "obligations": []},
                "decision": "selected",
            }
        ]
        provenance["reuse_records"] = [
            {
                "id": "reuse-001",
                "component_ids": ["cmp-001", "cmp-002"],
                "execution_stage_ids": ["run-01"],
                "source_ids": ["ext-001"],
                "reuse_kind": "independent-paper-implementation",
                "upstream_locators": ["Algorithm 1"],
                "local_paths": ["solver/src/solve.py"],
                "purpose": "Implement an alleged paper method.",
                "modifications": [],
                "semantic_deviations": [],
                "attribution_required": True,
                "attribution_locations": ["solver/solver-report.md"],
                "obligations_satisfied": True,
                "validation_test_ids": ["val-002"],
            }
        ]
        self.save(self.project, "solver", "implementation-provenance.yaml", provenance)
        result = self.run_validator(self.project, "solve")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("has no paper source", result.stdout)

    def test_unapproved_semantic_deviation_fails_solve(self) -> None:
        self.initialize_solve()
        self.complete_solver()
        plan = self.load(self.project, "solver", "run-plan.yaml")
        plan["semantic_deviations"] = [
            {
                "id": "dev-001",
                "contract_ref": "modeling/implementation-contract.yaml#immutable_items[0]",
                "description": "Replace the bounded score with an unbounded score.",
                "impact": "Changes the evaluation meaning.",
                "status": "feedback-required",
                "approval_ref": None,
            }
        ]
        self.save(self.project, "solver", "run-plan.yaml", plan)
        result = self.run_validator(self.project, "solve")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unresolved semantic deviation", result.stdout)

    def test_missing_required_output_fails_solve(self) -> None:
        self.initialize_solve()
        self.complete_solver()
        (self.project / "solver" / "results" / "score.csv").unlink()
        result = self.run_validator(self.project, "solve")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("file is missing", result.stdout)

    def test_raw_input_change_after_intake_fails_even_if_run_uses_new_hash(self) -> None:
        self.initialize_solve()
        self.complete_solver()
        input_file = self.project / "sources" / "input.csv"
        input_file.write_text("x\n0.99\n", encoding="utf-8")
        current_hash = sha256_file(input_file)
        registry = self.load(self.project, "solver", "experiment-registry.yaml")
        registry["experiments"][0]["input_artifacts"][0]["sha256"] = current_hash
        self.save(self.project, "solver", "experiment-registry.yaml", registry)
        reproducibility = self.load(self.project, "solver", "reproducibility.json")
        reproducibility["input_files"][0]["sha256"] = current_hash
        self.save(self.project, "solver", "reproducibility.json", reproducibility)
        result = self.run_validator(self.project, "solve")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("intake raw data", result.stdout)

    def test_manifest_output_must_be_an_experiment_artifact(self) -> None:
        self.initialize_solve()
        self.complete_solver()
        registry = self.load(self.project, "solver", "experiment-registry.yaml")
        registry["experiments"][0]["output_artifacts"] = []
        self.save(self.project, "solver", "experiment-registry.yaml", registry)
        result = self.run_validator(self.project, "solve")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("absent from its source experiment artifacts", result.stdout)

    def test_audit_not_ready_prevents_paper_handoff(self) -> None:
        self.initialize_solve()
        self.complete_solver()
        audit = self.load(self.project, "solver", "solver-audit.yaml")
        audit["overall_status"] = "NOT_READY"
        self.save(self.project, "solver", "solver-audit.yaml", audit)
        result = self.run_validator(self.project, "solve")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("audit is not ready", result.stdout)

    def test_failed_experiment_must_be_disclosed_in_solve(self) -> None:
        self.initialize_solve()
        self.complete_solver()
        registry = self.load(self.project, "solver", "experiment-registry.yaml")
        registry["experiments"].append(
            {
                "id": "exp-002",
                "kind": "validation",
                "stage_ids": ["run-01"],
                "status": "FAILED",
                "command": "python solver/src/solve.py --bad-config",
                "working_directory": ".",
                "input_artifacts": [],
                "config_paths": [],
                "seed": None,
                "started_at": "2026-07-13T10:00:02+08:00",
                "finished_at": "2026-07-13T10:00:03+08:00",
                "exit_code": 1,
                "output_artifacts": [],
                "log_path": "solver/logs/exp-001.log",
                "metrics": [],
                "invariant_results": [],
                "failure": {"category": "implementation_bug", "message": "bad config", "trace_ref": "solver/logs/exp-001.log", "next_action": "fix config"},
            }
        )
        self.save(self.project, "solver", "experiment-registry.yaml", registry)
        result = self.run_validator(self.project, "solve")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not disclosed", result.stdout)

    def test_probe_model_rejection_with_feedback_is_valid_completion(self) -> None:
        self.make_contract_exploratory()
        self.assertEqual(self.run_initializer(self.project, "probe").returncode, 0)
        registry = self.load(self.project, "solver", "experiment-registry.yaml")
        registry["experiments"] = [
            {
                "id": "exp-001",
                "kind": "probe",
                "stage_ids": ["run-01"],
                "status": "FAILED",
                "command": "python solver/src/probe.py",
                "working_directory": ".",
                "input_artifacts": [],
                "config_paths": [],
                "seed": None,
                "started_at": "2026-07-13T10:00:00+08:00",
                "finished_at": "2026-07-13T10:00:01+08:00",
                "exit_code": 2,
                "output_artifacts": [],
                "log_path": None,
                "metrics": [],
                "invariant_results": [],
                "failure": {"category": "contract_model_issue", "message": "constraints conflict", "trace_ref": None, "next_action": "return to modeling-selection"},
            }
        ]
        self.save(self.project, "solver", "experiment-registry.yaml", registry)
        validation = self.load(self.project, "solver", "validation-results.yaml")
        validation["status"] = "FEEDBACK_REQUIRED"
        validation["results"][0].update({"status": "FAILED", "failure_action": "revise-model", "evidence_refs": ["exp-001"]})
        self.save(self.project, "solver", "validation-results.yaml", validation)
        feedback = {
            "schema_version": "0.1.0",
            "feedback_id": "feedback-001",
            "status": "OPEN",
            "run_id": "probe-001",
            "trigger": "contract_conflict",
            "return_to": "modeling-selection",
            "affected_refs": ["run-01", "cmp-001"],
            "diagnosis": "The diagnostic run found mutually conflicting constraints.",
            "evidence_refs": ["exp-001"],
            "reproduction_commands": ["python solver/src/probe.py"],
            "semantic_change_required": True,
            "proposed_action": "Review the constraint set before formal solving.",
        }
        self.save(self.project, "solver", "modeling-feedback.yaml", feedback)
        manifest = self.load(self.project, "solver", "results-manifest.yaml")
        manifest.update(
            {
                "status": "NEEDS_REVISION",
                "ready_for_writing": False,
                "disclosed_failed_experiment_ids": ["exp-001"],
                "feedback_ref": "solver/modeling-feedback.yaml",
            }
        )
        self.save(self.project, "solver", "results-manifest.yaml", manifest)
        result = self.run_validator(self.project, "probe", json_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "PROBE_COMPLETE")

    def test_all_schemas_are_valid_draft_2020_12(self) -> None:
        import jsonschema

        for path in (MODULE_ROOT / "schemas").glob("*.json"):
            jsonschema.Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))


    def test_external_adapter_register_is_available(self) -> None:
        manifest = (MODULE_ROOT / "manifest.yaml").read_text(encoding="utf-8")
        self.assertIn("../../references/external-skill-adapters.md", manifest)
        self.assertIn("references/figure-design-sources.md", manifest)
        self.assertIn("static/execution-methods/figure-design.md", manifest)
        self.assertTrue((MODULE_ROOT.parents[1] / "references" / "external-skill-adapters.md").is_file())
        self.assertTrue((MODULE_ROOT / "references" / "figure-design-sources.md").is_file())
        self.assertTrue((MODULE_ROOT / "static" / "execution-methods" / "figure-design.md").is_file())


if __name__ == "__main__":
    unittest.main()
