from __future__ import annotations

import unittest

from autologging.knowledge import KnowledgeBase


class KnowledgeRulesTest(unittest.TestCase):
    def test_textbook_interpretation_constraints_are_available(self):
        knowledge = KnowledgeBase()
        constraints = knowledge.data["interpretation_constraints"]
        self.assertIn("quality_control", constraints)
        self.assertIn("lithology", constraints)
        self.assertIn("porosity", constraints)
        self.assertIn("saturation", constraints)
        self.assertIn("fluid_identification", constraints)

    def test_retrieves_saturation_dependency_rule(self):
        knowledge = KnowledgeBase()
        rules = knowledge.retrieve("interpret water saturation with porosity and Archie")
        self.assertTrue(any(rule["id"] == "porosity_before_saturation" for rule in rules))

    def test_exception_policy_has_tiered_actions(self):
        knowledge = KnowledgeBase()
        policy = knowledge.data["exception_policy"]
        self.assertIn("retry", policy["minor"]["actions"])
        self.assertIn("select_backup_model", policy["moderate"]["actions"])
        self.assertIn("request_expert_review", policy["critical"]["actions"])


if __name__ == "__main__":
    unittest.main()
