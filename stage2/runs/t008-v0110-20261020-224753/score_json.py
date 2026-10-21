"""Score entire visible answers as JSON; fenced payload scores are diagnostic only."""
from collections import Counter
from pathlib import Path
import hashlib
import json
import re

RUN = Path(__file__).resolve().parent
D = RUN / 'development'
REPO = RUN.parents[2]
def same_types_and_values(a, b):
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(same_types_and_values(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(same_types_and_values(x, y) for x, y in zip(a, b))
    return a == b

def no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key: ' + key)
        result[key] = value
    return result

def parse(text):
    def reject_constant(x):
        raise ValueError('Nonstandard JSON constant ' + x)
    return json.loads(text, object_pairs_hook=no_duplicate_keys, parse_constant=reject_constant)


raw = [json.loads(x) for x in (D/'results.jsonl').read_text().splitlines()]
new = {r['case']['id']:r for r in raw}
baseline = [json.loads(x) for x in (REPO/'stage2/diagnostics/json-format-check-20261020/results/results.jsonl').read_text().splitlines()]
old = {r['case']['id']:r for r in baseline if r['model_key']=='v019'}
fixtures=json.loads((RUN/'inputs/evaluation/json-subset.json').read_text())
assert len(fixtures)==len(old)==24
results=[]; pairs=[]
for case in fixtures:
 a,b=old[case['id']],new[case['id']]
 assert a['server_render']['token_ids']==b['server_render']['token_ids']
 assert {k:v for k,v in a['request'].items() if k!='model'}=={k:v for k,v in b['request'].items() if k!='model'}
 for label,row in [('v019',a),('v0110',b)]:
  choice=row['response']['choices'][0];body=choice['message'].get('content') or ''
  try:valid=True;passed=same_types_and_values(parse(body),case['expected'])
  except (ValueError,TypeError):valid=False;passed=False
  fence=re.fullmatch(r'\s*```(?:json)?\s*\n(.*?)\n```\s*',body,re.S|re.I)
  try:content=same_types_and_values(parse(body if fence is None else fence[1]),case['expected'])
  except (ValueError,TypeError):content=False
  results.append(dict(model=label,id=case['id'],case_id=case['case_id'],mode=case['mode'],seed=case['seed'],strict_pass=passed,whole_content_valid_json=valid,content_correct_ignoring_outer_fence=content,outer_code_fence=bool(fence),finish_reason=choice['finish_reason'],body=body))
 aa,bb=results[-2:];pairs.append({'id':case['id'],'before':aa['strict_pass'],'after':bb['strict_pass']})
groups={}
for label in ['v019','v0110']:
 for mode in ['nonthinking','thinking']:
  group=[r for r in results if r['model']==label and r['mode']==mode]
  groups[label+'/'+mode]={'count':len(group),'strict_pass':sum(r['strict_pass'] for r in group),'fences':sum(r['outer_code_fence'] for r in group),'content_correct_ignoring_outer_fence':sum(r['content_correct_ignoring_outer_fence'] for r in group)}
summary={'cases_per_model':24,'identical_protocol_and_prompt_tokens':True,'groups':groups,'paired_outcomes':dict(Counter('both_pass' if p['before'] and p['after'] else 'new_only_pass' if p['after'] else 'old_only_pass' if p['before'] else 'both_fail' for p in pairs)),'formal_acceptance':False,'baseline_reused':True,'two_overlapping_conditions_reused_from_regression':True}
(D/'json-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
(D/'json-scored.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in results))
lines=['# JSON逐题配对（整段正文严格解析）','', '| 题目 / 模式 | v0.1.9 | v0.1.10 |','| --- | ---: | ---: |']
for case_id in ['DEV-07','JSON-NEW-01','JSON-NEW-02','JSON-NEW-03']:
 for mode in ['nonthinking','thinking']:
  counts=[sum(r['strict_pass'] for r in results if r['model']==label and r['mode']==mode and r['case_id']==case_id) for label in ['v019','v0110']]
  lines.append(f'| {case_id} / {mode} | {counts[0]}/3 | {counts[1]}/3 |')
lines+=['','基线复用上一轮JSON诊断的v0.1.9输出；两次重合请求复用本轮40次回归中的结果。未剥离围栏后判通过；围栏内内容只作诊断。','']
for r in results:
 lines += [f"## {r['model']} / {r['id']}",'',f"严格通过：{r['strict_pass']}；忽略围栏的字段内容正确：{r['content_correct_ignoring_outer_fence']}。",'','````text',r['body'],'````','']
(D/'JSON_COMPARISON.md').write_text('\n'.join(lines))
print(json.dumps(summary,ensure_ascii=False))
