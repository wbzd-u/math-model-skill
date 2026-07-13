from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_ROOT = Path(__file__).resolve().parents[1]
INIT = MODULE_ROOT / "scripts" / "init_modeling_selection.py"
VALIDATE = MODULE_ROOT / "scripts" / "validate_modeling_selection.py"
SCHEMA_VERSION = "0.1.0"
ANALYSIS_SCHEMA_VERSION = "0.2.0"
ANALYSIS_AUDIT_DIMENSIONS = [
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


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


class ModelingSelectionScriptsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.project = self.root / "pass-project"
        self.write_analysis(self.project, gate_status="PASS")
        result = self.run_initializer(self.project)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    @staticmethod
    def run_initializer(project: Path, *extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(INIT), "--project-root", str(project), *extra],
            capture_output=True,
            text=True,
        )

    @staticmethod
    def run_validator(
        project: Path,
        strict: bool = False,
        mode: str | None = None,
        json_output: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(VALIDATE), "--project-root", str(project)]
        if mode:
            command.extend(["--mode", mode])
        if strict:
            command.append("--strict")
        if json_output:
            command.append("--json")
        return subprocess.run(command, capture_output=True, text=True)

    @staticmethod
    def load(project: Path, directory: str, name: str) -> dict:
        return json.loads((project / directory / name).read_text(encoding="utf-8"))

    @staticmethod
    def save(project: Path, directory: str, name: str, payload: dict) -> None:
        write_json(project / directory / name, payload)

    def write_analysis(self, project: Path, gate_status: str) -> None:
        blocked = gate_status == "BLOCKED"
        analysis = project / "analysis"
        write_json(
            analysis / "problem-profile.yaml",
            {
                "schema_version": ANALYSIS_SCHEMA_VERSION,
                "project_id": project.name,
                "title": "Minimal evaluation problem",
                "competition": {
                    "type": "generic",
                    "year": None,
                    "problem_id": None,
                    "rules_sources": [],
                },
                "scope": "one subproblem",
                "source_files": [],
                "objectives": ["Evaluate a supplied decision"],
                "deliverables": ["A traceable score"],
                "task_tags": ["evaluation"],
                "gate_status": gate_status,
            },
        )
        write_json(
            analysis / "requirement-trace.yaml",
            {
                "schema_version": ANALYSIS_SCHEMA_VERSION,
                "requirements": [
                    {
                        "id": "req-001",
                        "statement": "Return a traceable evaluation score",
                        "category": "objective",
                        "source_ref": "src-001:p1",
                        "subproblem_ids": ["sp-01"],
                        "status": "mapped",
                    }
                ],
            },
        )
        write_json(
            analysis / "data-inventory.yaml",
            {
                "schema_version": ANALYSIS_SCHEMA_VERSION,
                "datasets": [
                    {
                        "id": "data-01",
                        "path": "sources/input.csv",
                        "format": "text/csv",
                        "role": "input",
                        "read_only": True,
                        "fields": [],
                        "issues": [],
                    }
                ],
            },
        )
        write_json(
            analysis / "entity-variable-map.yaml",
            {
                "schema_version": ANALYSIS_SCHEMA_VERSION,
                "entities": [],
                "variables": [
                    {
                        "id": "var-001",
                        "name": "observed state",
                        "symbol": "x",
                        "role": "given",
                        "entity_ids": [],
                        "data_ids": ["data-01"],
                        "unit": "dimensionless",
                        "domain": "real",
                        "temporal_granularity": "static",
                        "spatial_granularity": None,
                        "source_ref": "src-001:p1",
                        "status": "confirmed",
                    }
                ],
            },
        )
        unresolved_ids = ["amb-001"] if blocked else []
        write_json(
            analysis / "subproblems.yaml",
            {
                "schema_version": ANALYSIS_SCHEMA_VERSION,
                "subproblems": [
                    {
                        "id": "sp-01",
                        "statement": "Evaluate the supplied state",
                        "source_requirement_ids": ["req-001"],
                        "inputs": ["var-001"],
                        "required_outputs": ["traceable score"],
                        "objectives": ["produce a score"],
                        "constraints": ["preserve the stated evaluation meaning"],
                        "evaluation_criteria": ["traceability"],
                        "task_tags": ["evaluation"],
                        "semantic_contract": {
                            "exogenous_or_given_variable_ids": ["var-001"],
                            "controllable_variable_ids": [],
                            "outcome_variable_ids": [],
                            "state_or_event_relation": "The supplied state is evaluated.",
                            "information_timing": "All inputs are known before evaluation.",
                            "success_predicate": "A traceable score is returned.",
                            "evaluation_aggregation": "One score is reported.",
                            "feasibility_summary": "No decision is optimized.",
                            "boundary_or_termination": "Stop after one evaluation.",
                            "couplings": [],
                            "acceptance_tests": [
                                {
                                    "criterion": "The score is traceable.",
                                    "source_requirement_ids": ["req-001"],
                                }
                            ],
                        },
                        "difficulty_assessment": {
                            "status": "identified",
                            "rationale": "The evaluation meaning must be preserved.",
                        },
                        "difficulty_drivers": [
                            {
                                "id": "diff-01",
                                "type": "definition",
                                "statement": "The score must preserve the stated meaning.",
                                "evidence_refs": ["src-001:p1"],
                                "why_it_changes_problem": "A different score answers a different question.",
                                "affected_dimensions": ["evaluation"],
                                "affected_variable_ids": ["var-001"],
                                "affected_subproblem_ids": ["sp-01"],
                                "omission_consequence": "The result would not answer the prompt.",
                                "status": "confirmed",
                            }
                        ],
                        "upstream_ids": [],
                        "unresolved_ids": unresolved_ids,
                    }
                ],
            },
        )
        write_json(
            analysis / "data-task-matrix.yaml",
            {
                "schema_version": ANALYSIS_SCHEMA_VERSION,
                "mappings": [
                    {
                        "subproblem_id": "sp-01",
                        "needs": [
                            {
                                "item": "observed state",
                                "status": "available",
                                "data_ids": ["data-01"],
                                "field_refs": [],
                                "gap": None,
                                "impact": None,
                            }
                        ],
                    }
                ],
            },
        )
        write_json(
            analysis / "dependency-graph.yaml",
            {"schema_version": ANALYSIS_SCHEMA_VERSION, "nodes": ["sp-01"], "edges": []},
        )
        ambiguities = []
        if blocked:
            ambiguities = [
                {
                    "id": "amb-001",
                    "statement": "The success definition is unresolved.",
                    "source_ref": "src-001:p1",
                    "impact": "It changes the score.",
                    "definition_impact": True,
                    "affected_subproblem_ids": ["sp-01"],
                    "alternatives": [
                        {"interpretation": "Use definition A.", "impact_on": ["evaluation"]},
                        {"interpretation": "Use definition B.", "impact_on": ["evaluation"]},
                    ],
                    "resolution_evidence": None,
                    "disposition": "verify_rules",
                    "status": "blocking",
                }
            ]
        write_json(
            analysis / "ambiguity-register.yaml",
            {"schema_version": ANALYSIS_SCHEMA_VERSION, "items": ambiguities},
        )
        write_json(
            analysis / "assumption-register.yaml",
            {"schema_version": ANALYSIS_SCHEMA_VERSION, "items": []},
        )
        write_json(
            analysis / "analysis-audit.yaml",
            {
                "schema_version": ANALYSIS_SCHEMA_VERSION,
                "checks": [
                    {
                        "dimension": dimension,
                        "status": (
                            "WARN"
                            if gate_status in {"PASS_WITH_OPEN_ITEMS", "BLOCKED"}
                            and dimension == "definition_impact_gating"
                            else "PASS"
                        ),
                        "evidence": ["minimal upstream fixture"],
                        "findings": [],
                        "required_actions": [],
                    }
                    for dimension in ANALYSIS_AUDIT_DIMENSIONS
                ],
                "overall_status": gate_status,
            },
        )

    @staticmethod
    def candidate(candidate_id: str, name: str, method_family: str) -> dict:
        return {
            "id": candidate_id,
            "name": name,
            "subproblem_ids": ["sp-01"],
            "chain_roles": [
                {
                    "id": "stage-01",
                    "role": "evaluation",
                    "method_family": method_family,
                    "purpose": "Convert the observed state into the required score.",
                    "input_refs": ["var-001"],
                    "output_refs": ["dvar-001"],
                    "evidence_ids": ["ev-001"],
                }
            ],
            "requirement_ids": ["req-001"],
            "difficulty_refs": ["sp-01:diff-01"],
            "data_ids": ["data-01"],
            "evidence_ids": ["ev-001"],
            "assumptions": ["The observed state is measured on the declared scale."],
            "output_type": "traceable evaluation score",
            "validation_plan": ["Compare meanings and check declared bounds."],
            "risks": ["The evaluation scale may be misspecified."],
            "rejection_conditions": ["The method changes the success definition."],
            "transfer_limits": ["Only applies to the declared one-state evaluation."],
            "implementation_cost": "low",
            "interpretability": "strong",
            "validation_strength": "strong",
            "contest_fit": "strong",
            "status": "selected",
        }

    @staticmethod
    def component(component_id: str, candidate_id: str, role: str, definition: str) -> dict:
        return {
            "id": component_id,
            "candidate_id": candidate_id,
            "role": role,
            "subproblem_ids": ["sp-01"],
            "type": "evaluation mapping",
            "purpose": "Produce the requested evaluation score.",
            "formal_definition": definition,
            "input_variable_ids": ["var-001"],
            "output_variable_ids": ["dvar-001"],
            "objective_statements": ["Preserve the requested evaluation meaning."],
            "constraint_statements": ["The output remains on the declared scale."],
            "state_or_event_relations": ["The output is a deterministic function of var-001."],
            "parameter_sources": ["No fitted parameter is required."],
            "upstream_component_ids": [],
        }

    def complete_package(self, project: Path | None = None) -> None:
        project = project or self.project
        modeling = project / "modeling"
        write_json(
            modeling / "candidate-methods.yaml",
            {
                "schema_version": SCHEMA_VERSION,
                "knowledge_status": "partial",
                "evidence_records": [
                    {
                        "id": "ev-001",
                        "type": "structural",
                        "title": "Evaluation structure extracted from the handoff",
                        "source_ref": "analysis/subproblems.yaml#sp-01",
                        "relevance": "It fixes the score meaning and required output.",
                        "transfer_limits": ["It is evidence about structure, not numerical performance."],
                        "verified": True,
                    }
                ],
                "candidates": [
                    self.candidate("cand-001", "Identity baseline", "direct baseline"),
                    self.candidate("cand-002", "Constraint-aware score", "constrained evaluation"),
                ],
                "comparison_exception": None,
            },
        )
        write_json(
            modeling / "model-decision.yaml",
            {
                "schema_version": SCHEMA_VERSION,
                "status": "READY",
                "scope_subproblem_ids": ["sp-01"],
                "main_candidate_ids": ["cand-002"],
                "baseline_candidate_ids": ["cand-001"],
                "alternative_candidate_ids": [],
                "baseline_exception": None,
                "alternative_exception": "No third route adds a materially different capability for this minimal fixture.",
                "comparisons": [
                    {
                        "dimension": "structural-fit",
                        "assessments": [
                            {
                                "candidate_id": "cand-001",
                                "rating": "moderate",
                                "evidence_refs": ["ev-001"],
                                "comment": "It provides a transparent baseline.",
                            },
                            {
                                "candidate_id": "cand-002",
                                "rating": "strong",
                                "evidence_refs": ["ev-001"],
                                "comment": "It explicitly preserves the declared constraint.",
                            },
                        ],
                    }
                ],
                "coverage": {
                    "requirement_ids": ["req-001"],
                    "difficulty_refs": ["sp-01:diff-01"],
                    "subproblem_ids": ["sp-01"],
                },
                "decision_rationale": "Use a direct baseline and a constraint-aware main score.",
                "residual_risks": ["The declared scale still needs a boundary check."],
            },
        )
        write_json(
            modeling / "model-specification.yaml",
            {
                "schema_version": SCHEMA_VERSION,
                "status": "READY",
                "scope_subproblem_ids": ["sp-01"],
                "notation": [
                    {
                        "id": "var-001",
                        "source_variable_id": "var-001",
                        "symbol": "x",
                        "definition": "Observed state",
                        "unit": "dimensionless",
                    },
                    {
                        "id": "dvar-001",
                        "source_variable_id": "dvar-001",
                        "symbol": "s",
                        "definition": "Evaluation score",
                        "unit": "dimensionless",
                    },
                ],
                "new_assumptions": [],
                "components": [
                    self.component("cmp-001", "cand-001", "baseline", "s_0 = x"),
                    self.component("cmp-002", "cand-002", "main", "s = min(1, max(0, x))"),
                ],
                "model_chain": {
                    "nodes": ["cmp-001", "cmp-002"],
                    "edges": [],
                },
                "immutable_semantics": [
                    {
                        "source_ref": "analysis/subproblems.yaml#sp-01",
                        "statement": "The score must answer req-001 without changing its meaning.",
                    }
                ],
            },
        )
        write_json(
            modeling / "validation-plan.yaml",
            {
                "schema_version": SCHEMA_VERSION,
                "status": "READY",
                "tests": [
                    {
                        "id": "val-001",
                        "type": "baseline-comparison",
                        "subproblem_ids": ["sp-01"],
                        "component_ids": ["cmp-001"],
                        "target_claim": "The baseline preserves the raw observed scale.",
                        "procedure": "Evaluate representative in-range inputs.",
                        "metrics": ["absolute deviation"],
                        "pass_criteria": "The baseline equals the supplied input.",
                        "failure_action": "revise-model",
                    },
                    {
                        "id": "val-002",
                        "type": "constraint-check",
                        "subproblem_ids": ["sp-01"],
                        "component_ids": ["cmp-002"],
                        "target_claim": "The main score remains inside the declared bounds.",
                        "procedure": "Evaluate lower, interior, and upper boundary cases.",
                        "metrics": ["bound violation count"],
                        "pass_criteria": "No evaluated score lies outside [0, 1].",
                        "failure_action": "revise-model",
                    },
                ],
                "coverage": {
                    "component_ids": ["cmp-001", "cmp-002"],
                    "difficulty_refs": ["sp-01:diff-01"],
                    "requirement_ids": ["req-001"],
                },
            },
        )
        write_json(
            modeling / "modeling-selection-audit.yaml",
            {
                "schema_version": SCHEMA_VERSION,
                "checks": [
                    {
                        "dimension": dimension,
                        "status": "PASS",
                        "evidence": ["minimal completed fixture"],
                        "findings": [],
                        "required_actions": [],
                    }
                    for dimension in AUDIT_DIMENSIONS
                ],
                "overall_status": "PASS",
            },
        )
        write_json(
            modeling / "implementation-contract.yaml",
            {
                "schema_version": SCHEMA_VERSION,
                "status": "READY",
                "contract_id": "contract-001",
                "input_snapshot": {
                    "intake_sha256": sha256_file(modeling / "intake-check.yaml"),
                    "model_spec_sha256": sha256_file(modeling / "model-specification.yaml"),
                    "validation_plan_sha256": sha256_file(modeling / "validation-plan.yaml"),
                },
                "scope_subproblem_ids": ["sp-01"],
                "approved_component_ids": ["cmp-001", "cmp-002"],
                "parameters": [],
                "execution_stages": [
                    {
                        "id": "run-01",
                        "component_ids": ["cmp-001", "cmp-002"],
                        "input_refs": ["var-001"],
                        "output_refs": ["dvar-001"],
                        "required_invariants": ["Preserve the req-001 score meaning."],
                        "solver_freedom": ["Choose a programming language and numeric type."],
                    }
                ],
                "required_outputs": [
                    {
                        "id": "out-001",
                        "subproblem_ids": ["sp-01"],
                        "type": "result table",
                        "destination": "results/score.csv",
                        "acceptance_requirement_ids": ["req-001"],
                    }
                ],
                "validation_test_ids": ["val-001", "val-002"],
                "immutable_items": [
                    {
                        "type": "evaluation",
                        "source_ref": "analysis/subproblems.yaml#sp-01",
                        "statement": "Do not change the score meaning.",
                    }
                ],
                "solver_discretion": ["Language, libraries, and data structures."],
                "feedback_policy": {
                    "path": "solver/modeling-feedback.yaml",
                    "triggers": ["infeasible contract", "missing data", "conflicting constraints"],
                    "required_evidence": ["error output", "inputs", "reproduction command"],
                },
            },
        )
        (modeling / "modeling-selection-report.md").write_text(
            "# Modeling selection report\n\n"
            "The intake passed. A baseline and a constraint-aware main route were selected.\n\n"
            "Validation and the solver contract are ready.\n",
            encoding="utf-8",
        )

    def refresh_contract_snapshots(self, project: Path | None = None) -> None:
        project = project or self.project
        modeling = project / "modeling"
        contract = self.load(project, "modeling", "implementation-contract.yaml")
        contract["input_snapshot"] = {
            "intake_sha256": sha256_file(modeling / "intake-check.yaml"),
            "model_spec_sha256": sha256_file(modeling / "model-specification.yaml"),
            "validation_plan_sha256": sha256_file(modeling / "validation-plan.yaml"),
        }
        self.save(project, "modeling", "implementation-contract.yaml", contract)

    def make_single_candidate_ready(self, project: Path | None = None) -> None:
        project = project or self.project
        candidate_payload = self.load(project, "modeling", "candidate-methods.yaml")
        candidate_payload["candidates"] = [
            item for item in candidate_payload["candidates"] if item["id"] == "cand-002"
        ]
        candidate_payload["comparison_exception"] = "One scientifically sufficient route remains after feasibility screening."
        self.save(project, "modeling", "candidate-methods.yaml", candidate_payload)

        decision = self.load(project, "modeling", "model-decision.yaml")
        decision["baseline_candidate_ids"] = []
        decision["alternative_candidate_ids"] = []
        decision["baseline_exception"] = None
        decision["alternative_exception"] = None
        decision["comparisons"] = []
        self.save(project, "modeling", "model-decision.yaml", decision)

        specification = self.load(project, "modeling", "model-specification.yaml")
        specification["components"] = [
            item for item in specification["components"] if item["id"] == "cmp-002"
        ]
        specification["model_chain"] = {"nodes": ["cmp-002"], "edges": []}
        self.save(project, "modeling", "model-specification.yaml", specification)

        validation = self.load(project, "modeling", "validation-plan.yaml")
        validation["tests"] = [item for item in validation["tests"] if item["id"] == "val-002"]
        validation["coverage"]["component_ids"] = ["cmp-002"]
        self.save(project, "modeling", "validation-plan.yaml", validation)

        contract = self.load(project, "modeling", "implementation-contract.yaml")
        contract["approved_component_ids"] = ["cmp-002"]
        contract["execution_stages"][0]["component_ids"] = ["cmp-002"]
        contract["validation_test_ids"] = ["val-002"]
        self.save(project, "modeling", "implementation-contract.yaml", contract)
        self.refresh_contract_snapshots(project)

    def test_initialized_package_passes_non_strict_validation(self) -> None:
        result = self.run_validator(self.project)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("STATUS: EXPLORATORY", result.stdout)
        self.assertIn("READY_FOR_SOLVER: false", result.stdout)
        self.assertIn("initialized for exploration", result.stdout)
        json_result = self.run_validator(self.project, json_output=True)
        payload = json.loads(json_result.stdout)
        self.assertTrue(payload["handoff_issues"])

    def test_tampered_draft_does_not_use_initialized_fast_path(self) -> None:
        contract = self.load(self.project, "modeling", "implementation-contract.yaml")
        contract["approved_component_ids"] = ["cmp-999"]
        self.save(self.project, "modeling", "implementation-contract.yaml", contract)
        result = self.run_validator(self.project)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("references unknown components", result.stdout)

    def test_initialized_draft_fails_strict_validation(self) -> None:
        result = self.run_validator(self.project, strict=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires model-decision status READY", result.stdout)

    def test_blocked_upstream_still_creates_exploratory_modeling_package(self) -> None:
        project = self.root / "blocked-project"
        self.write_analysis(project, gate_status="BLOCKED")
        init_result = self.run_initializer(project)
        self.assertEqual(init_result.returncode, 0, init_result.stdout + init_result.stderr)
        produced = {path.name for path in (project / "modeling").iterdir()}
        self.assertEqual(
            produced,
            {
                "intake-check.yaml",
                "candidate-methods.yaml",
                "model-decision.yaml",
                "model-specification.yaml",
                "validation-plan.yaml",
                "implementation-contract.yaml",
                "modeling-selection-audit.yaml",
                "modeling-selection-report.md",
            },
        )
        intake = self.load(project, "modeling", "intake-check.yaml")
        self.assertEqual(intake["selection_intake_status"], "EXPLORATORY")
        self.assertEqual(intake["handoff_allowed_subproblem_ids"], [])
        result = self.run_validator(project)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("STATUS: EXPLORATORY", result.stdout)

    def test_missing_minimum_problem_definition_is_truly_blocked(self) -> None:
        project = self.root / "undefined-project"
        self.write_analysis(project, gate_status="PASS")
        requirements = self.load(project, "analysis", "requirement-trace.yaml")
        requirements["requirements"] = []
        self.save(project, "analysis", "requirement-trace.yaml", requirements)
        subproblems = self.load(project, "analysis", "subproblems.yaml")
        subproblems["subproblems"] = []
        self.save(project, "analysis", "subproblems.yaml", subproblems)
        init_result = self.run_initializer(project)
        self.assertEqual(init_result.returncode, 0, init_result.stdout + init_result.stderr)
        produced = {path.name for path in (project / "modeling").iterdir()}
        self.assertEqual(produced, {"intake-check.yaml", "modeling-selection-report.md"})
        result = self.run_validator(project)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("STATUS: BLOCKED", result.stdout)

    def test_open_item_allows_exploration_but_blocks_handoff(self) -> None:
        project = self.root / "conditional-project"
        self.write_analysis(project, gate_status="PASS_WITH_OPEN_ITEMS")
        ambiguities = self.load(project, "analysis", "ambiguity-register.yaml")
        ambiguities["items"] = [
            {
                "id": "amb-001",
                "statement": "A non-definitional data label remains unresolved.",
                "source_ref": "src-001:p1",
                "impact": "It blocks this subproblem until the field is identified.",
                "definition_impact": False,
                "affected_subproblem_ids": ["sp-01"],
                "alternatives": [],
                "resolution_evidence": None,
                "disposition": "verify_data",
                "status": "open",
            }
        ]
        self.save(project, "analysis", "ambiguity-register.yaml", ambiguities)
        subproblems = self.load(project, "analysis", "subproblems.yaml")
        subproblems["subproblems"][0]["unresolved_ids"] = ["amb-001"]
        self.save(project, "analysis", "subproblems.yaml", subproblems)
        init_result = self.run_initializer(project)
        self.assertEqual(init_result.returncode, 0, init_result.stdout + init_result.stderr)
        intake = self.load(project, "modeling", "intake-check.yaml")
        self.assertEqual(intake["selection_intake_status"], "EXPLORATORY")
        self.assertEqual(intake["allowed_subproblem_ids"], ["sp-01"])
        self.assertEqual(intake["handoff_allowed_subproblem_ids"], [])
        explore_result = self.run_validator(project)
        self.assertEqual(explore_result.returncode, 0, explore_result.stdout + explore_result.stderr)
        handoff_result = self.run_validator(project, mode="handoff")
        self.assertNotEqual(handoff_result.returncode, 0)
        self.assertIn("handoff_allowed_subproblem_ids", handoff_result.stdout)

    def test_reinitialize_requires_force_and_deduplicates_scope(self) -> None:
        rerun = self.run_initializer(self.project, "--subproblem", "sp-01")
        self.assertNotEqual(rerun.returncode, 0)
        self.assertIn("use --force", rerun.stdout)
        forced = self.run_initializer(
            self.project,
            "--subproblem",
            "sp-01",
            "--subproblem",
            "sp-01",
            "--force",
        )
        self.assertEqual(forced.returncode, 0, forced.stdout + forced.stderr)
        intake = self.load(self.project, "modeling", "intake-check.yaml")
        self.assertEqual(intake["selected_subproblem_ids"], ["sp-01"])

    def test_force_blocked_reinitialize_replaces_downstream_with_exploratory_templates(self) -> None:
        self.complete_package()
        self.write_analysis(self.project, gate_status="BLOCKED")
        result = self.run_initializer(self.project, "--force")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        produced = {path.name for path in (self.project / "modeling").iterdir()}
        self.assertIn("candidate-methods.yaml", produced)
        decision = self.load(self.project, "modeling", "model-decision.yaml")
        self.assertEqual(decision["status"], "EXPLORATORY")

    def test_completed_pass_package_passes_strict_validation(self) -> None:
        self.complete_package()
        result = self.run_validator(self.project, strict=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("STATUS: PASS", result.stdout)
        self.assertIn("audit_completion=1.000", result.stdout)

    def test_upstream_hash_change_fails(self) -> None:
        self.complete_package()
        requirements = self.load(self.project, "analysis", "requirement-trace.yaml")
        requirements["requirements"][0]["statement"] += " (changed after intake)"
        self.save(self.project, "analysis", "requirement-trace.yaml", requirements)
        result = self.run_validator(self.project)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("upstream file changed after intake", result.stdout)

    def test_unknown_candidate_reference_fails(self) -> None:
        self.complete_package()
        decision = self.load(self.project, "modeling", "model-decision.yaml")
        decision["main_candidate_ids"] = ["cand-999"]
        self.save(self.project, "modeling", "model-decision.yaml", decision)
        result = self.run_validator(self.project)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("references unknown candidate cand-999", result.stdout)

    def test_overlapping_candidate_roles_warn_but_do_not_block_handoff(self) -> None:
        self.complete_package()
        decision = self.load(self.project, "modeling", "model-decision.yaml")
        decision["alternative_candidate_ids"] = ["cand-002"]
        decision["alternative_exception"] = None
        self.save(self.project, "modeling", "model-decision.yaml", decision)
        result = self.run_validator(self.project, strict=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("candidate roles overlap", result.stdout)

    def test_missing_main_candidate_fails(self) -> None:
        self.complete_package()
        decision = self.load(self.project, "modeling", "model-decision.yaml")
        decision["main_candidate_ids"] = []
        self.save(self.project, "modeling", "model-decision.yaml", decision)
        explore_result = self.run_validator(self.project)
        self.assertEqual(explore_result.returncode, 0, explore_result.stdout + explore_result.stderr)
        self.assertIn("handoff_issues", self.run_validator(self.project, json_output=True).stdout)
        result = self.run_validator(self.project, strict=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires a main candidate", result.stdout)

    def test_alternative_cannot_supply_missing_main_requirement_coverage(self) -> None:
        project = self.root / "main-coverage-project"
        self.write_analysis(project, gate_status="PASS")
        requirements = self.load(project, "analysis", "requirement-trace.yaml")
        requirements["requirements"].append(
            {
                "id": "req-002",
                "statement": "Report a bounded score",
                "category": "output",
                "source_ref": "src-001:p1",
                "subproblem_ids": ["sp-01"],
                "status": "mapped",
            }
        )
        self.save(project, "analysis", "requirement-trace.yaml", requirements)
        init_result = self.run_initializer(project)
        self.assertEqual(init_result.returncode, 0, init_result.stdout + init_result.stderr)
        self.complete_package(project)

        candidate_payload = self.load(project, "modeling", "candidate-methods.yaml")
        alternative = self.candidate("cand-003", "Bounded fallback", "bounded fallback")
        alternative["requirement_ids"] = ["req-002"]
        candidate_payload["candidates"].append(alternative)
        self.save(project, "modeling", "candidate-methods.yaml", candidate_payload)

        decision = self.load(project, "modeling", "model-decision.yaml")
        decision["alternative_candidate_ids"] = ["cand-003"]
        decision["alternative_exception"] = None
        decision["coverage"]["requirement_ids"] = ["req-001", "req-002"]
        decision["comparisons"][0]["assessments"].append(
            {
                "candidate_id": "cand-003",
                "rating": "moderate",
                "evidence_refs": ["ev-001"],
                "comment": "It covers req-002 only as a fallback.",
            }
        )
        self.save(project, "modeling", "model-decision.yaml", decision)

        validation = self.load(project, "modeling", "validation-plan.yaml")
        validation["coverage"]["requirement_ids"] = ["req-001", "req-002"]
        self.save(project, "modeling", "validation-plan.yaml", validation)
        contract = self.load(project, "modeling", "implementation-contract.yaml")
        contract["required_outputs"][0]["acceptance_requirement_ids"] = ["req-001", "req-002"]
        self.save(project, "modeling", "implementation-contract.yaml", contract)
        self.refresh_contract_snapshots(project)

        explore_result = self.run_validator(project)
        self.assertEqual(explore_result.returncode, 0, explore_result.stdout + explore_result.stderr)
        result = self.run_validator(project, strict=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("main candidates and model decision do not cover every selected requirement", result.stdout)

    def test_single_scientifically_complete_candidate_can_handoff(self) -> None:
        self.complete_package()
        self.make_single_candidate_ready()
        result = self.run_validator(self.project, mode="handoff")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("no baseline is defined", result.stdout)
        self.assertIn("READY_FOR_SOLVER: true", result.stdout)
        strict_alias = self.run_validator(self.project, strict=True)
        self.assertEqual(strict_alias.returncode, 0, strict_alias.stdout + strict_alias.stderr)

    def test_missing_validation_component_coverage_fails(self) -> None:
        self.complete_package()
        validation = self.load(self.project, "modeling", "validation-plan.yaml")
        validation["tests"][1]["component_ids"] = ["cmp-001"]
        validation["coverage"]["component_ids"] = ["cmp-001"]
        self.save(self.project, "modeling", "validation-plan.yaml", validation)
        self.refresh_contract_snapshots()
        explore_result = self.run_validator(self.project)
        self.assertEqual(explore_result.returncode, 0, explore_result.stdout + explore_result.stderr)
        result = self.run_validator(self.project, strict=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not cover every main model component", result.stdout)

    def test_contract_snapshot_mismatch_fails(self) -> None:
        self.complete_package()
        contract = self.load(self.project, "modeling", "implementation-contract.yaml")
        contract["input_snapshot"]["model_spec_sha256"] = "0" * 64
        self.save(self.project, "modeling", "implementation-contract.yaml", contract)
        explore_result = self.run_validator(self.project)
        self.assertEqual(explore_result.returncode, 0, explore_result.stdout + explore_result.stderr)
        self.assertIn("snapshot does not match", explore_result.stdout)
        result = self.run_validator(self.project, strict=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("model specification snapshot does not match", result.stdout)

    def test_contract_must_preserve_immutable_semantics(self) -> None:
        self.complete_package()
        contract = self.load(self.project, "modeling", "implementation-contract.yaml")
        contract["immutable_items"] = []
        self.save(self.project, "modeling", "implementation-contract.yaml", contract)
        explore_result = self.run_validator(self.project)
        self.assertEqual(explore_result.returncode, 0, explore_result.stdout + explore_result.stderr)
        self.assertIn("does not preserve", explore_result.stdout)
        result = self.run_validator(self.project, strict=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not preserve every model-specification immutable semantic", result.stdout)

    def test_malformed_upstream_is_reported_without_traceback(self) -> None:
        profile = self.load(self.project, "analysis", "problem-profile.yaml")
        profile["competition"] = "generic"
        self.save(self.project, "analysis", "problem-profile.yaml", profile)
        result = self.run_initializer(self.project, "--force")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid upstream problem-profile.yaml", result.stdout)
        self.assertNotIn("Traceback", result.stderr)


    def test_external_adapter_protocols_are_registered(self) -> None:
        manifest = (MODULE_ROOT / "manifest.yaml").read_text(encoding="utf-8")
        self.assertIn("references/external-case-evidence-protocol.md", manifest)
        self.assertTrue((MODULE_ROOT / "references" / "external-case-evidence-protocol.md").is_file())
        self.assertTrue((MODULE_ROOT.parents[1] / "references" / "external-skill-adapters.md").is_file())


if __name__ == "__main__":
    unittest.main()
