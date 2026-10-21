"""Mechanical comparisons, separate from semantic development review."""
from pathlib import Path
from collections import Counter, defaultdict
import json, hashlib
R=Path(__file__).resolve().parent;D=R/'development';ROOT=R.parents[2]
def lines(path):return [json.loads(x) for x in path.read_text().splitlines()]
def save(name,obj):(D/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def text(row):return row['response']['choices'][0]['message'].get('content') or ''
def thought(row):
 m=row['response']['choices'][0]['message'];return m.get('reasoning') or m.get('reasoning_content') or ''
def digest(s):return hashlib.sha256(s.encode()).hexdigest()
spec=json.loads((D/'spec.json').read_text());raw=lines(D/'additional-results.jsonl');assert len(raw)==240
sessions={};normalized=[];pairs={};groups=defaultdict(list)
for r in raw:
 c=r['case'];b=r['request'];q=r['response']['choices'][0];body=text(r);reason=thought(r)
 assert 'error' not in r and r['input_ids_verified']
 assert len(r['server_render']['token_ids'])==r['response']['usage']['prompt_tokens']
 assert b['seed']==c['seed'] and b['model'] in ['t008-old','t008-new']
 for k,v in spec['modes'][c['mode']].items():
  assert (b['chat_template_kwargs']['enable_thinking'] if k=='enable_thinking' else b[k])==v
 if c['system_variant']=='current':assert digest(b['messages'][0]['content'])==spec['additional']['system_sha256']
 else:assert b['messages'][0]['role']=='user'
 if c['turn']==1:sessions[c['session_id']]=[dict(x) for x in b['messages']]+[{'role':'assistant','content':body}]
 else:
  assert b['messages'][:-1]==sessions[c['session_id']]
  sessions[c['session_id']]=b['messages']+[{'role':'assistant','content':body}]
 x=dict(c,model=b['model'],question=b['messages'][-1]['content'],body=body,reasoning=reason,
        finish_reason=q['finish_reason'],completion_tokens=r['response']['usage']['completion_tokens'],
        body_sha256=digest(body),reasoning_sha256=digest(reason),empty_body=not body.strip(),
        exact_product_name_present='能碳章鱼垂直大模型' in body,
        exact_company_name_present='能碳章鱼（湖北）人工智能科技有限公司' in body,
        correct_date_present='2026年7月8日' in body,correct_location_present='武汉市武昌区' in body)
 normalized.append(x);groups[(b['model'],c['system_variant'],c['mode'])].append(x)
 key=(c['case_id'],c['system_variant'],c['mode'],c['seed'],c['turn']);pairs.setdefault(key,{})[b['model']]=r
for key,p in pairs.items():
 a,b=p['t008-old'],p['t008-new']
 assert {k:v for k,v in a['request'].items() if k not in ['model','messages']}=={k:v for k,v in b['request'].items() if k not in ['model','messages']}
 if key[-1]==1:assert a['request']['messages']==b['request']['messages'] and a['server_render']['token_ids']==b['server_render']['token_ids']
 else:assert a['request']['messages'][-1]==b['request']['messages'][-1]
summary={}
for key,items in groups.items():
 identity=[x for x in items if x['case_id']=='CN11-01'];facts=[x for x in items if x['case_id']=='CN11-02' and x['turn']==2]
 summary['/'.join(key)]={'requests':len(items),'empty_body':sum(x['empty_body'] for x in items),'length_finish':sum(x['finish_reason']=='length' for x in items),'short_identity_name_present':sum(x['exact_product_name_present'] for x in identity),'short_identity_count':len(identity),'company_date_and_location_present':sum(x['correct_date_present'] and x['correct_location_present'] for x in facts),'company_fact_count':len(facts)}
save('additional-summary.json',{'groups':summary,'all_initial_prompt_ids_identical':True,'real_generated_multiturn_history_verified':True,'requests':240,'sessions':len(sessions),'formal_acceptance':False,'counts_are_literal_presence_not_semantic_pass':True})
(D/'additional-normalized.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in normalized))
md=['# 新增中文场景逐题正文','', '旧模型v0.1.10、新模型v0.1.12；current为同一版含公司事实的System。多轮使用各模型真实上一轮正文。自动计数不代表语义通过。','']
for x in normalized:md += ['## '+x['id'],'',x['question'],'',x['body'] or '（空正文）','',f"结束：{x['finish_reason']}；token：{x['completion_tokens']}。",'']
(D/'ADDITIONAL_ANSWERS.md').write_text('\n'.join(md))
# Schema comparison uses the frozen v0.1.10 proposed System; never pool with SFT gains.
state=json.loads((D/'schema-state.json').read_text())
if state['status']=='COMPLETE':
 old=lines(ROOT/'stage2/runs/t008-v0110-20261020-224753/development/results.jsonl');old={r['case']['id']:r for r in old}
 constrained=lines(D/'schema-results.jsonl');fixtures={r['case_id']:r for r in lines(R/'inputs/evaluation/json-schema-cases.jsonl')}
 def parse(s):
  def pairs(v):
   d={}
   for k,x in v:
    if k in d:raise ValueError('duplicate key')
    d[k]=x
   return d
  return json.loads(s,object_pairs_hook=pairs,parse_constant=lambda v:(_ for _ in ()).throw(ValueError(v)))
 def structure(obj,schema):
  typ=schema['type'];types=typ if isinstance(typ,list) else [typ]
  hit=any({'object':type(obj)is dict,'array':type(obj)is list,'string':type(obj)is str,'integer':type(obj)is int,'number':type(obj)in [int,float],'boolean':type(obj)is bool,'null':obj is None}.get(t,False) for t in types)
  if not hit:return False
  if type(obj)is dict:
   return set(schema.get('required',[]))<=set(obj) and (schema.get('additionalProperties',True) or set(obj)<=set(schema['properties'])) and all(structure(x,schema['properties'][k]) for k,x in obj.items() if k in schema['properties'])
  if type(obj)is list:return all(structure(x,schema['items']) for x in obj)
  return True
 def equal(a,b):
  if type(a)is not type(b):return False
  if isinstance(a,dict):return a.keys()==b.keys() and all(equal(a[k],b[k]) for k in a)
  if isinstance(a,list):return len(a)==len(b) and all(equal(x,y) for x,y in zip(a,b))
  return a==b
 scores=[]
 for after in constrained:
  c=after['case'];before=old[c['id']];fixture=fixtures[c['case_id']]
  assert before['server_render']['token_ids']==after['server_render']['token_ids']
  assert {k:v for k,v in before['request'].items() if k!='model'}=={k:v for k,v in after['request'].items() if k not in ['model','response_format']}
  for kind,row in [('unconstrained',before),('schema',after)]:
   valid=True;shape=False;values=False
   try:
    obj=parse(text(row));shape=structure(obj,fixture['response_format']['json_schema']['schema']);values=equal(obj,fixture['expected_for_scoring_only'])
   except (ValueError,TypeError):valid=False
   scores.append({'kind':kind,'id':c['id'],'mode':c['mode'],'parse_valid':valid,'schema_valid':shape,'values_correct':values,'finish_reason':row['response']['choices'][0]['finish_reason'],'body':text(row)})
 group={}
 for kind in ['unconstrained','schema']:
  for mode in ['nonthinking','thinking']:
   items=[x for x in scores if x['kind']==kind and x['mode']==mode]
   group[kind+'/'+mode]={'count':len(items),**{key:sum(x[key] for x in items) for key in ['parse_valid','schema_valid','values_correct']}}
 save('schema-summary.json',{'groups':group,'matching_prompt_tokens_and_generation_config':True,'frozen_baseline_reused':True,'model':'v0.1.10','system':'frozen v0.1.10 proposed','not_sft_improvement':True})
 (D/'schema-scored.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in scores))
print(json.dumps({'additional':summary,'schema':state},ensure_ascii=False))
