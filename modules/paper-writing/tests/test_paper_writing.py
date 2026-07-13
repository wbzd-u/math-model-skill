from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_ROOT = Path(__file__).resolve().parents[1]
INIT = MODULE_ROOT / "scripts" / "init_paper_writing.py"
VALIDATE = MODULE_ROOT / "scripts" / "validate_paper_writing.py"


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class PaperWritingScriptsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.project = Path(self.tempdir.name) / "project"
        self.write_project(with_solver=True)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    @staticmethod
    def load(project: Path, directory: str, name: str) -> dict:
        return json.loads((project / directory / name).read_text(encoding="utf-8"))

    @staticmethod
    def save(project: Path, directory: str, name: str, payload: dict) -> None:
        write_json(project / directory / name, payload)

    @staticmethod
    def run_init(project: Path, mode: str, *extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(INIT), "--project-root", str(project), "--mode", mode, *extra], capture_output=True, text=True)

    @staticmethod
    def run_validate(project: Path, mode: str, json_output: bool = False) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(VALIDATE), "--project-root", str(project), "--mode", mode]
        if json_output:
            command.append("--json")
        return subprocess.run(command, capture_output=True, text=True)

    def write_project(self, with_solver: bool) -> None:
        analysis = self.project / "analysis"
        write_json(analysis / "problem-profile.yaml", {"project_id": self.project.name, "competition": {"type": "generic"}, "source_files": []})
        write_json(analysis / "requirement-trace.yaml", {"requirements": [{"id": "req-001", "statement": "Return a bounded score", "status": "mapped"}]})
        write_json(analysis / "entity-variable-map.yaml", {"variables": []})
        write_json(self.project / "modeling" / "model-specification.yaml", {"notation": [{"id": "var-001", "symbol": "x", "definition": "Input score", "unit": "dimensionless"}]})
        write_json(self.project / "modeling" / "validation-plan.yaml", {"tests": []})
        if not with_solver:
            return
        answer = self.project / "solver" / "results" / "answer.csv"
        answer.parent.mkdir(parents=True, exist_ok=True)
        answer.write_text("score\n1.0\n", encoding="utf-8")
        write_json(self.project / "solver" / "results-manifest.yaml", {"status": "COMPLETE", "ready_for_writing": True, "claims": [{"id": "claim-001", "statement": "The score is bounded on the supplied input.", "evidence_refs": ["solver/results/answer.csv"], "limitations": []}]})
        write_json(self.project / "solver" / "validation-results.yaml", {"status": "COMPLETE"})
        write_json(self.project / "solver" / "reproducibility.json", {"status": "COMPLETE"})

    def init_final(self) -> None:
        result = self.run_init(self.project, "final")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def complete_final(self) -> None:
        paper = self.project / "paper"
        source_map = self.load(self.project, "paper", "source-map.yaml")
        for item in source_map["items"]:
            item["section_id"] = "sec-03"
            item["support_status"] = "supported"
            item["evidence_refs"] = ["solver/results/answer.csv"]
        self.save(self.project, "paper", "source-map.yaml", source_map)
        argument = self.load(self.project, "paper", "argument-map.yaml")
        argument["status"] = "READY"
        argument["core_argument"] = "For the stated scoring problem, the model returns a bounded score supported by a verified result file."
        argument["sections"][2]["claim_ids"] = [item["id"] for item in source_map["items"]]
        self.save(self.project, "paper", "argument-map.yaml", argument)
        anchors = "\n".join(f"<!-- claim: {item['anchor']} -->" for item in source_map["items"])
        (paper / "manuscript.md").write_text(
            "# Bounded scoring model\n\n" + anchors + "\n\n## Problem and scope\n\nThe requested score is reported.\n\n## Model and solution\n\nThe model evaluates the supplied value.\n\n## Results and validation\n\nThe result file reports the bounded score.\n\n## Limitations\n\nThe conclusion is limited to the supplied input.\n\n## References\n",
            encoding="utf-8",
        )
        audit = self.load(self.project, "paper", "writing-audit.yaml")
        for check in audit["checks"]:
            check.update({"status": "PASS", "evidence": ["paper/source-map.yaml"], "findings": [], "required_actions": []})
        audit["overall_status"] = "PASS"
        self.save(self.project, "paper", "writing-audit.yaml", audit)

    def test_draft_allows_missing_solver_package(self) -> None:
        project = Path(self.tempdir.name) / "draft-only"
        self.project = project
        self.write_project(with_solver=False)
        result = self.run_init(project, "draft")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        result = self.run_validate(project, "draft", json_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "DRAFT_READY")

    def test_final_requires_solver_ready(self) -> None:
        manifest = self.load(self.project, "solver", "results-manifest.yaml")
        manifest["ready_for_writing"] = False
        self.save(self.project, "solver", "results-manifest.yaml", manifest)
        result = self.run_init(self.project, "final")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ready_for_writing", result.stdout)

    def test_final_skeleton_is_not_submission_ready(self) -> None:
        self.init_final()
        result = self.run_validate(self.project, "final")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unresolved placeholders", result.stdout)

    def test_completed_final_passes(self) -> None:
        self.init_final()
        self.complete_final()
        result = self.run_validate(self.project, "final", json_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "PASS")
        self.assertTrue(payload["ready_for_submission"])

    def test_upstream_change_after_init_fails(self) -> None:
        self.init_final()
        profile = self.load(self.project, "analysis", "problem-profile.yaml")
        profile["project_id"] = "changed"
        self.save(self.project, "analysis", "problem-profile.yaml", profile)
        result = self.run_validate(self.project, "final")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SHA-256 changed", result.stdout)

    def test_missing_claim_anchor_fails(self) -> None:
        self.init_final()
        self.complete_final()
        manuscript = self.project / "paper" / "manuscript.md"
        manuscript.write_text(manuscript.read_text(encoding="utf-8").replace("<!-- claim: claim-001 -->\n", ""), encoding="utf-8")
        result = self.run_validate(self.project, "final")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing claim anchor", result.stdout)

    def test_missing_planned_section_fails_final(self) -> None:
        self.init_final()
        self.complete_final()
        manuscript = self.project / "paper" / "manuscript.md"
        manuscript.write_text(manuscript.read_text(encoding="utf-8").replace("## Limitations\n\nThe conclusion is limited to the supplied input.\n\n", ""), encoding="utf-8")
        result = self.run_validate(self.project, "final")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing planned section heading", result.stdout)

    def test_unsupported_requirement_answer_fails_final(self) -> None:
        self.init_final()
        self.complete_final()
        source_map = self.load(self.project, "paper", "source-map.yaml")
        source_map["items"][0]["support_status"] = "needs-evidence"
        self.save(self.project, "paper", "source-map.yaml", source_map)
        result = self.run_validate(self.project, "final")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not evidence-supported", result.stdout)

    def test_unverified_citation_fails_final(self) -> None:
        self.init_final()
        self.complete_final()
        source_map = self.load(self.project, "paper", "source-map.yaml")
        source_map["citation_records"] = [{"key": "method2026", "title": "Method paper", "stable_id": "doi:1", "source_type": "paper", "verified": False, "used_for_claim_ids": [source_map["items"][0]["id"]]}]
        source_map["items"][0]["citation_keys"] = ["method2026"]
        self.save(self.project, "paper", "source-map.yaml", source_map)
        (self.project / "paper" / "references.bib").write_text("@article{method2026,title={Method paper}}\n", encoding="utf-8")
        result = self.run_validate(self.project, "final")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unverified citation", result.stdout)

    def test_path_escape_in_evidence_fails(self) -> None:
        self.init_final()
        self.complete_final()
        source_map = self.load(self.project, "paper", "source-map.yaml")
        source_map["items"][0]["evidence_refs"] = ["../outside.csv"]
        self.save(self.project, "paper", "source-map.yaml", source_map)
        result = self.run_validate(self.project, "final")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("escapes project root", result.stdout)

    def test_open_writing_feedback_blocks_final(self) -> None:
        self.init_final()
        self.complete_final()
        feedback = {"schema_version": "0.1.0", "feedback_id": "write-feedback-001", "status": "OPEN", "return_to": "numerical-solving", "affected_claim_ids": ["claim-001"], "diagnosis": "Result requires rerun.", "evidence_refs": ["solver/results/answer.csv"], "required_action": "Regenerate the result."}
        self.save(self.project, "paper", "writing-feedback.yaml", feedback)
        result = self.run_validate(self.project, "final")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unresolved writing feedback", result.stdout)

    def test_existing_package_requires_force(self) -> None:
        self.init_final()
        result = self.run_init(self.project, "final")
        self.assertEqual(result.returncode, 2)
        result = self.run_init(self.project, "final", "--force")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_schemas_are_valid(self) -> None:
        import jsonschema
        for path in (MODULE_ROOT / "schemas").glob("*.json"):
            jsonschema.Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))


    def test_competition_delivery_adapter_is_registered(self) -> None:
        manifest = (MODULE_ROOT / "manifest.yaml").read_text(encoding="utf-8")
        self.assertIn("references/competition-delivery-adapters.md", manifest)
        self.assertIn("static/writing-methods/latex-delivery.md", manifest)
        self.assertTrue((MODULE_ROOT / "references" / "competition-delivery-adapters.md").is_file())
        self.assertTrue((MODULE_ROOT / "static" / "writing-methods" / "latex-delivery.md").is_file())
        self.assertTrue((MODULE_ROOT.parents[1] / "references" / "external-skill-adapters.md").is_file())


if __name__ == "__main__":
    unittest.main()
