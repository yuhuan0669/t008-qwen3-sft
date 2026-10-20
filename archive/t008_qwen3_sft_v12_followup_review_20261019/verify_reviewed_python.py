"""Bounded functional checks for source 991 after primary review of its code."""
import ast
import hashlib
import json
import random
import re
import string
from pathlib import Path

HERE = Path(__file__).resolve().parent
rows = [json.loads(s) for s in (HERE / 'mixin_all.jsonl').read_text().splitlines()]
row = next(r for r in rows if r['source_line_one_based'] == 991)
code = re.search(r'```python\n([\s\S]*?)```', row['final_answer'])[1]
tree = ast.parse(code)
# This exact small program was read in full before execution. No arbitrary corpus
# scripts are executed by this verifier. Only random/string imports are allowed.
assert all(isinstance(n, (ast.Import, ast.FunctionDef, ast.If)) for n in tree.body)
assert sorted(a.name for n in tree.body if isinstance(n, ast.Import) for a in n.names) == ['random', 'string']
namespace = {'__name__': 'reviewed_sample'}
exec(compile(tree, '<reviewed-source-991>', 'exec'), namespace)
checks = 0
for seed in range(100):
    random.seed(seed)
    for _ in range(10):
        value = namespace['generate_random_string']()
        assert len(value) == 15
        assert all(c in string.ascii_letters + string.digits + string.punctuation for c in value)
        assert any(c in string.ascii_lowercase for c in value)
        assert any(c in string.ascii_uppercase for c in value)
        assert any(c in string.digits for c in value)
        assert any(c in string.punctuation for c in value)
        checks += 1
report = {'source_line_one_based': 991, 'generated_strings_checked': checks,
          'seed_count': 100, 'all_functional_constraints_passed': True,
          'code_sha256': hashlib.sha256(code.encode()).hexdigest(),
          'limits': ['Does not prove cryptographic security or uniform distribution over all valid strings.',
                     'Reasoning text contains an inaccurate illustrative listing of string.punctuation; code uses the actual standard-library constant.',
                     'Only this already-reviewed small program was executed on CPU; no model or GPU used.']}
(HERE / 'reviewed_python_checks.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
