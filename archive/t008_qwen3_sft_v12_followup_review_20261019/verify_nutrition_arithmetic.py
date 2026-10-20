"""Recompute the internal arithmetic of source 563, not nutrition advice."""
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

HERE = Path(__file__).resolve().parent
row = next(r for r in map(json.loads, (HERE / 'mixin_all.jsonl').read_text().splitlines()) if r['source_line_one_based'] == 563)
values = []
for line in row['final_answer'].splitlines():
    if not line.startswith('|'):
        continue
    fields = [x.strip() for x in line.strip('|').split('|')]
    if len(fields) == 11:
        try:
            values.append([Decimal(x) for x in fields[1:]])
        except InvalidOperation:
            pass
computed = [str(sum(row[i] for row in values)) for i in range(10)]
record = json.loads((HERE / 'nutrition_arithmetic_check.json').read_text())
assert len(values) == record['food_rows'] == 11
assert computed == record['computed_totals']
assert computed[0] == '490' and record['stated_totals'][0] == '520'
print(json.dumps({'source_line_one_based': 563, 'food_rows': 11, 'computed_totals_verified': computed}))
