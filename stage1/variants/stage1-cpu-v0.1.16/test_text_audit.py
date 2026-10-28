import unittest
from audit_text import shared_fragments

class TextAudit(unittest.TestCase):
    def test_detects_shared_span_inside_different_questions(self):
        self.assertEqual(shared_fragments(["前缀甲乙丙丁戊己庚辛壬癸子丑后缀"], ["另一题甲乙丙丁戊己庚辛壬癸子丑结尾"]), {"甲乙丙丁戊己庚辛壬癸子丑"})
    def test_does_not_join_unrelated_turns(self):
        self.assertEqual(shared_fragments(["甲乙丙丁戊己", "庚辛壬癸子丑"], ["甲乙丙丁戊己庚辛壬癸子丑"]), set())
    def test_whitespace_normalization_and_short_inputs(self):
        self.assertEqual(shared_fragments(["甲乙丙丁 戊己庚辛 壬癸子丑"], ["甲乙丙丁戊己庚辛壬癸子丑"]), {"甲乙丙丁戊己庚辛壬癸子丑"})
        self.assertEqual(shared_fragments(["只核对已有资料"], ["只核对已有资料"]), set())

if __name__ == '__main__': unittest.main()
