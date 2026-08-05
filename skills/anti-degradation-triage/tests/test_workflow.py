import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_PATH = ROOT / "SKILL.md"
CASES_PATH = Path(__file__).with_name("cases.json")

PRINCIPLES = [
    "Reproduce Before Repairing",
    "Establish Capability and Ownership",
    "Classify the Defect Mechanism",
    "Fix the Narrowest Root Cause",
    "Prefer Deletion and Consolidation",
    "Verify Behavior and Surrounding Contracts",
]

ISSUE_TYPES = {"Capability", "Scope", "Knowledge", "Judgment", "Regression"}
REPAIR_MODES = {"none", "route-away", "instance", "class-level"}
EXPECTED_FIELDS = {
    "classification",
    "repair_mode",
    "actions",
    "forbidden",
    "completion_evidence",
}
CHECKPOINT_FIELDS = [
    "Issue type",
    "Boundary result",
    "Root-cause choice",
    "Blast radius",
    "Preserved invariants",
    "Bloat result",
    "Behavioral validation",
    "Package validation",
]


def load_cases():
    with CASES_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)["cases"]


class SkillStructureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = SKILL_PATH.read_text(encoding="utf-8")

    def test_six_principles_exist_once_and_in_order(self):
        positions = []
        for principle in PRINCIPLES:
            heading = f"### {principle}"
            self.assertEqual(self.skill.count(heading), 1, heading)
            positions.append(self.skill.index(heading))
        self.assertEqual(positions, sorted(positions))

    def test_boundary_checks_precede_content_classification(self):
        boundary = self.skill.index("### Establish Capability and Ownership")
        content = self.skill.index("### Classify the Defect Mechanism")
        self.assertLess(boundary, content)

    def test_all_issue_types_are_defined(self):
        for issue_type in ISSUE_TYPES:
            self.assertRegex(self.skill, rf"\b{re.escape(issue_type)}(?: Gap| Regression|\b)")

    def test_checkpoint_is_complete(self):
        for field in CHECKPOINT_FIELDS:
            self.assertIn(f"- {field}:", self.skill)

    def test_unavailable_change_control_has_explicit_fallback(self):
        verification = self.skill.split(
            "### Verify Behavior and Surrounding Contracts", 1
        )[1]
        self.assertIn("skill-change-control", verification)
        self.assertIn("create-skill", verification)
        self.assertIn("explicitly requested", verification)

    def test_each_principle_has_a_completion_criterion(self):
        sections = re.split(r"^### ", self.skill, flags=re.MULTILINE)[1:]
        principle_sections = {
            section.splitlines()[0]: section for section in sections
        }
        for principle in PRINCIPLES:
            self.assertIn("**Completion criterion:**", principle_sections[principle])


class BehavioralFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = load_cases()

    def test_case_ids_are_unique(self):
        ids = [case["id"] for case in self.cases]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_principle_has_behavioral_coverage(self):
        covered = {case["principle"] for case in self.cases}
        self.assertEqual(set(PRINCIPLES), covered)

    def test_every_issue_type_has_behavioral_coverage(self):
        covered = {
            case["expected"]["classification"]
            for case in self.cases
            if case["expected"]["classification"] is not None
        }
        self.assertEqual(ISSUE_TYPES, covered)

    def test_expected_results_are_complete(self):
        for case in self.cases:
            with self.subTest(case=case["id"]):
                self.assertEqual(EXPECTED_FIELDS, set(case["expected"]))
                classification = case["expected"]["classification"]
                self.assertTrue(
                    classification is None or classification in ISSUE_TYPES
                )
                self.assertIn(case["expected"]["repair_mode"], REPAIR_MODES)
                self.assertTrue(case["expected"]["actions"])
                self.assertTrue(case["expected"]["forbidden"])
                self.assertTrue(case["expected"]["completion_evidence"])

    def test_boundary_precedence_is_covered(self):
        precedence_cases = [
            case for case in self.cases if "precedence" in case["tags"]
        ]
        self.assertTrue(precedence_cases)
        self.assertTrue(
            all(
                case["expected"]["classification"] in {"Capability", "Scope"}
                for case in precedence_cases
            )
        )

    def test_instance_and_class_level_repairs_are_covered(self):
        modes = {case["expected"]["repair_mode"] for case in self.cases}
        self.assertIn("instance", modes)
        self.assertIn("class-level", modes)

    def test_anti_bloat_and_verification_cases_exist(self):
        all_tags = {tag for case in self.cases for tag in case["tags"]}
        self.assertIn("consolidation", all_tags)
        self.assertIn("single-source-of-truth", all_tags)
        self.assertIn("blast-radius", all_tags)
        self.assertIn("save-gate", all_tags)


if __name__ == "__main__":
    unittest.main()
