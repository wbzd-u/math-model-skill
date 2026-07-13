from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_ROOT = Path(__file__).resolve().parents[1]
INIT = MODULE_ROOT / "scripts" / "init_problem_analysis.py"
VALIDATE = MODULE_ROOT / "scripts" / "validate_problem_analysis.py"
SCHEMA_VERSION = "0.2.0"
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


class ProblemAnalysisScriptsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.project = Path(self.tempdir.name)
        result = subprocess.run(
            [
                sys.executable,
                str(INIT),
                "--project-root",
                str(self.project),
                "--title",
                "Example Problem",
                "--competition",
                "generic",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def run_validator(self, strict: bool = False) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(VALIDATE), "--project-root", str(self.project)]
        if strict:
            command.append("--strict")
        return subprocess.run(command, capture_output=True, text=True)

    def load(self, name: str) -> dict:
        return json.loads((self.project / "analysis" / name).read_text(encoding="utf-8"))

    def save(self, name: str, payload: dict) -> None:
        (self.project / "analysis" / name).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def base_contract() -> dict:
        return {
            "exogenous_or_given_variable_ids": [],
            "controllable_variable_ids": [],
            "outcome_variable_ids": ["var-001"],
            "state_or_event_relation": "题面给定信息被整理为评价对象的当前状态。",
            "information_timing": "只使用题面在评价时点前给定的信息。",
            "success_predicate": "输出可追溯且回应题目要求的评价结论。",
            "evaluation_aggregation": "单一评价对象，不进行跨对象聚合。",
            "feasibility_summary": "没有额外资源决策，输出不得超出题面范围。",
            "boundary_or_termination": "在题面规定的评价范围结束时停止。",
            "couplings": [],
            "acceptance_tests": [
                {
                    "criterion": "评价结论可追溯且完整回应问题一。",
                    "source_requirement_ids": ["req-001"],
                }
            ],
        }

    @staticmethod
    def structural_driver() -> dict:
        return {
            "id": "diff-01",
            "type": "coupling",
            "statement": "评价结果依赖于题面给定状态与输出口径的一致性。",
            "evidence_refs": ["src-001:p1"],
            "why_it_changes_problem": "口径不一致会改变评价结果的解释。",
            "affected_dimensions": ["evaluation", "output"],
            "affected_variable_ids": ["var-001"],
            "affected_subproblem_ids": ["sp-01"],
            "omission_consequence": "结果可能回应了不同的问题。",
            "status": "risk",
        }

    def make_strictly_valid(self) -> None:
        profile = self.load("problem-profile.yaml")
        profile["objectives"] = ["对给定对象给出可追溯评价"]
        profile["deliverables"] = ["问题一评价结论"]
        profile["task_tags"] = ["evaluation"]
        profile["gate_status"] = "PASS"
        self.save("problem-profile.yaml", profile)

        self.save(
            "requirement-trace.yaml",
            {
                "schema_version": SCHEMA_VERSION,
                "requirements": [
                    {
                        "id": "req-001",
                        "statement": "对问题一给出可追溯评价结论",
                        "category": "objective",
                        "source_ref": "src-001:p1",
                        "subproblem_ids": ["sp-01"],
                        "status": "mapped",
                    }
                ],
            },
        )
        self.save(
            "entity-variable-map.yaml",
            {
                "schema_version": SCHEMA_VERSION,
                "entities": [
                    {
                        "id": "ent-001",
                        "name": "研究对象",
                        "type": "system",
                        "source_refs": ["src-001:p1"],
                        "relationships": [],
                    }
                ],
                "variables": [
                    {
                        "id": "var-001",
                        "name": "评价结果",
                        "symbol": None,
                        "role": "outcome",
                        "entity_ids": ["ent-001"],
                        "data_ids": [],
                        "unit": None,
                        "domain": None,
                        "temporal_granularity": None,
                        "spatial_granularity": None,
                        "source_ref": "src-001:p1",
                        "status": "confirmed",
                    }
                ],
            },
        )
        self.save(
            "subproblems.yaml",
            {
                "schema_version": SCHEMA_VERSION,
                "subproblems": [
                    {
                        "id": "sp-01",
                        "statement": "基于题面给定信息评价问题一并给出结论",
                        "source_requirement_ids": ["req-001"],
                        "inputs": ["题面给定的评价对象与条件"],
                        "required_outputs": ["可追溯的评价结论"],
                        "objectives": ["完整回应问题一的评价要求"],
                        "constraints": ["不得引入题面外的评价口径"],
                        "evaluation_criteria": ["结论与题面要求和证据一致"],
                        "task_tags": ["evaluation"],
                        "semantic_contract": self.base_contract(),
                        "difficulty_assessment": {
                            "status": "none-evidenced",
                            "rationale": "该最小测试题没有共享资源、动态事件或定义分叉。",
                        },
                        "difficulty_drivers": [],
                        "upstream_ids": [],
                        "unresolved_ids": [],
                    }
                ],
            },
        )
        self.save(
            "data-task-matrix.yaml",
            {
                "schema_version": SCHEMA_VERSION,
                "mappings": [
                    {
                        "subproblem_id": "sp-01",
                        "needs": [
                            {
                                "item": "无需外部数据",
                                "status": "not-applicable",
                                "data_ids": [],
                                "field_refs": [],
                                "gap": None,
                                "impact": None,
                            }
                        ],
                    }
                ],
            },
        )
        self.save(
            "dependency-graph.yaml",
            {"schema_version": SCHEMA_VERSION, "nodes": ["sp-01"], "edges": []},
        )
        self.save(
            "analysis-audit.yaml",
            {
                "schema_version": SCHEMA_VERSION,
                "checks": [
                    {
                        "dimension": dimension,
                        "status": "PASS",
                        "evidence": ["validated fixture"],
                        "findings": [],
                        "required_actions": [],
                    }
                    for dimension in AUDIT_DIMENSIONS
                ],
                "overall_status": "PASS",
            },
        )
        (self.project / "analysis" / "problem-analysis-report.md").write_text(
            "# 题目分析报告\n\n## 阶段门禁\n\nPASS\n",
            encoding="utf-8",
        )

    def set_structural_tags(self, tags: list[str], driver: dict | None = None) -> None:
        profile = self.load("problem-profile.yaml")
        profile["task_tags"] = tags
        self.save("problem-profile.yaml", profile)
        subproblems = self.load("subproblems.yaml")
        subproblem = subproblems["subproblems"][0]
        subproblem["task_tags"] = tags
        if driver:
            subproblem["difficulty_assessment"] = {"status": "identified", "rationale": "存在结构性风险。"}
            subproblem["difficulty_drivers"] = [driver]
        self.save("subproblems.yaml", subproblems)

    def add_definition_ambiguity(self, status: str = "blocking", resolution_evidence: str | None = None) -> None:
        ambiguities = self.load("ambiguity-register.yaml")
        ambiguities["items"] = [
            {
                "id": "amb-001",
                "statement": "成功判定存在两种合理解释。",
                "source_ref": "src-001:p1",
                "impact": "会改变问题一的评价结果。",
                "definition_impact": True,
                "affected_subproblem_ids": ["sp-01"],
                "alternatives": [
                    {"interpretation": "按口径 A 判定成功。", "impact_on": ["evaluation"]},
                    {"interpretation": "按口径 B 判定成功。", "impact_on": ["objective", "evaluation"]},
                ],
                "resolution_evidence": resolution_evidence,
                "disposition": "verify_rules",
                "status": status,
            }
        ]
        self.save("ambiguity-register.yaml", ambiguities)
        subproblems = self.load("subproblems.yaml")
        subproblems["subproblems"][0]["unresolved_ids"] = [] if status == "resolved" else ["amb-001"]
        self.save("subproblems.yaml", subproblems)

    def test_initialized_package_passes_non_strict_validation(self) -> None:
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("STATUS: PASS", result.stdout)
        self.assertIn("DRAFT", result.stdout)

    def test_initialized_package_fails_strict_validation(self) -> None:
        result = self.run_validator(strict=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("gate_status", result.stdout)

    def test_completed_package_passes_strict_validation(self) -> None:
        self.make_strictly_valid()
        result = self.run_validator(strict=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_unknown_cross_reference_fails(self) -> None:
        self.make_strictly_valid()
        requirements = self.load("requirement-trace.yaml")
        requirements["requirements"][0]["subproblem_ids"] = ["sp-99"]
        self.save("requirement-trace.yaml", requirements)
        result = self.run_validator(strict=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown subproblem references", result.stdout)

    def test_method_selection_leakage_fails(self) -> None:
        self.make_strictly_valid()
        profile = self.load("problem-profile.yaml")
        profile["selected_model"] = "forbidden-example"
        self.save("problem-profile.yaml", profile)
        result = self.run_validator(strict=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("method-selection key is forbidden", result.stdout)

    def test_incomplete_requirement_mapping_fails_coverage(self) -> None:
        self.make_strictly_valid()
        requirements = self.load("requirement-trace.yaml")
        requirements["requirements"][0]["subproblem_ids"] = []
        self.save("requirement-trace.yaml", requirements)
        result = self.run_validator(strict=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requirement_mapping_coverage", result.stdout)

    def test_optimization_without_controllable_variable_fails(self) -> None:
        self.make_strictly_valid()
        self.set_structural_tags(["optimization"], self.structural_driver())
        result = self.run_validator(strict=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("optimization", result.stdout)
        self.assertIn("controllable variable", result.stdout)

    def test_controllable_variable_must_have_controllable_role(self) -> None:
        self.make_strictly_valid()
        self.set_structural_tags(["optimization"], self.structural_driver())
        subproblems = self.load("subproblems.yaml")
        subproblems["subproblems"][0]["semantic_contract"]["controllable_variable_ids"] = ["var-001"]
        self.save("subproblems.yaml", subproblems)
        result = self.run_validator(strict=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("is not a controllable variable", result.stdout)

    def test_structural_task_requires_evidence_backed_difficulty(self) -> None:
        self.make_strictly_valid()
        self.set_structural_tags(["simulation"])
        result = self.run_validator(strict=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("structural task requires one to three", result.stdout)

    def test_definition_impact_requires_blocked_gate(self) -> None:
        self.make_strictly_valid()
        self.add_definition_ambiguity()
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("require problem-profile.gate_status BLOCKED", result.stdout)

    def test_blocked_package_is_valid_but_not_strictly_handoff_ready(self) -> None:
        self.make_strictly_valid()
        self.add_definition_ambiguity()
        profile = self.load("problem-profile.yaml")
        profile["gate_status"] = "BLOCKED"
        self.save("problem-profile.yaml", profile)
        audit = self.load("analysis-audit.yaml")
        audit["overall_status"] = "BLOCKED"
        self.save("analysis-audit.yaml", audit)
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("STATUS: BLOCKED", result.stdout)
        strict_result = self.run_validator(strict=True)
        self.assertNotEqual(strict_result.returncode, 0)
        self.assertIn("strict mode requires gate_status", strict_result.stdout)

    def test_resolved_definition_ambiguity_requires_resolution_evidence(self) -> None:
        self.make_strictly_valid()
        self.add_definition_ambiguity(status="resolved")
        result = self.run_validator(strict=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("resolution_evidence", result.stdout)

    def test_subproblem_tag_must_be_declared_by_profile(self) -> None:
        self.make_strictly_valid()
        subproblems = self.load("subproblems.yaml")
        subproblems["subproblems"][0]["task_tags"] = ["prediction"]
        self.save("subproblems.yaml", subproblems)
        result = self.run_validator(strict=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("task tags must be declared", result.stdout)


if __name__ == "__main__":
    unittest.main()
