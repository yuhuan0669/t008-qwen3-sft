"""Regression checks for concrete final-review findings; no model calls."""
from pathlib import Path
import json
import unittest
from build_candidate import decision

D=Path(__file__).resolve().parent
P=D.parent/'stage1-cpu-v0.1.14'
parent=[json.loads(x) for x in (P/'train.jsonl').read_text().splitlines()]

class CandidatePolicy(unittest.TestCase):
    def test_adjacent_english_and_han_are_preserved(self):
        for line in [23,206,291,485,571]:
            with self.subTest(line=line):
                self.assertEqual(decision(parent[line-1]),'preserve_english_or_mixed')

    def test_general_mail_translation_does_not_get_business_system(self):
        self.assertEqual(decision(parent[1261]),'preserve_general_scope_conflict')

    def test_chinese_identity_and_business_examples_still_get_system(self):
        for line in [16,1254,1276,1280,1314]:
            with self.subTest(line=line):self.assertEqual(decision(parent[line-1]),'add_system')

    def test_config_points_to_its_own_cpu_report(self):
        cfg=json.loads((D/'training-config.json').read_text())
        self.assertEqual(cfg['cpu_validation_report'],f'stage1/variants/{D.name}/cpu-check/report.json')

if __name__=='__main__':unittest.main()
