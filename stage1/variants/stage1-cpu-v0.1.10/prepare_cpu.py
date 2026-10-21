"""Adapt the previous proven CPU checker for eight replacements, including empty-think JSON."""
from pathlib import Path
import ast
import json

D = Path(__file__).resolve().parent
ROOT = D.parents[2]
PARENT = ROOT / 'stage1/variants/stage1-cpu-v0.1.9'
OUT = D / 'cpu-check'
OUT.mkdir(exist_ok=True)
source = (PARENT / 'cpu-check/check_cpu.py').read_text()
replacements = [
    ("import json\n", "import json\nimport re\n"),
    ("PARENT = ROOT / 'stage1/variants/stage1-cpu-v0.1.8'", "PARENT = ROOT / 'stage1/variants/stage1-cpu-v0.1.9'"),
    ("PARENT / 'cpu-check/encoding-report.json'", "PARENT / 'cpu-check/report.json'"),
    ("(LOSS3 / 'identity-keys.json')", "(PARENT / 'identity-keys.json')"),
    ("assert dict(old_totals) == reference['source_supervised_tokens']", "assert dict(old_totals) == reference['source_supervised_tokens_after']"),
    ("old_totals[source] += prior", "old_totals[parent_row['dataset']] += prior"),
    ("assert dict(counts) == {'swift/Qwen3-SFT-Mixin': 1036, 'swift/self-cognition': 216,\n                        't008/project-positioning-v1': 23}",
     "assert dict(counts) == {'swift/Qwen3-SFT-Mixin': 1032, 'swift/self-cognition': 216,\n                        't008/project-positioning-v1': 23, 't008/strict-json-v1': 4}"),
    ("assert len(probes) == 5", "assert len(probes) == 8"),
    ("        assert content in text, (i, text)\n        assert text.count('<think>') == text.count('</think>') == 1",
     "        thought = re.search(r'<think>(.*?)</think>', content, re.S)\n        nonempty = bool(thought and thought[1].strip())\n        visible = content.split('</think>')[-1].strip()\n        assert visible in text, (i, text)\n        if nonempty:\n            assert content in text, (i, text)\n            assert text.count('<think>') == text.count('</think>') == 1\n        else:\n            assert '<think>' not in text and '</think>' not in text, (i, text)\n        if source == 't008/strict-json-v1':\n            json.loads(visible)\n            assert '```' not in visible"),
    ("'full_nonempty_thought_and_body_supervised': True,", "'answer_and_eos_supervised': True,\n                       'nonempty_thought_present': nonempty,\n                       'thought_supervised_if_present': True,\n                       'empty_think_masked_if_present': True,"),
    ("'five_short_thoughts_body_and_eos_supervised': True,", "'all_eight_changed_answers_and_eos_supervised': True,\n    'all_six_new_nonempty_thoughts_supervised': True,\n    'two_json_empty_thoughts_masked': True,\n    'strict_json_answer_weight': 1,"),
]
for a, b in replacements:
    assert source.count(a) == 1, a
    source = source.replace(a, b)
ast.parse(source)
(OUT / 'check_cpu.py').write_text(source)
pod = json.loads((PARENT / 'cpu-check/pod-cpu.json').read_text())
pod['metadata'].update(name='t008-v0110-cpu-20261020', labels={'t008-cpu-check': 'v0110-20261020'})
pod['spec']['containers'][0]['command'][-1] = pod['spec']['containers'][0]['command'][-1].replace('/tmp/v019-check', '/tmp/v0110-check')
(OUT / 'pod-cpu.json').write_text(json.dumps(pod, indent=2) + '\n')
print('Prepared native Swift CPU checker; GPU hidden; no model, Trainer, or optimizer.')
