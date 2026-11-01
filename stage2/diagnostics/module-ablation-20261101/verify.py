"""Local archive verification; does not call inference or restore UAT."""
from pathlib import Path
from collections import Counter,defaultdict
import json,hashlib
D=Path(__file__).resolve().parent;O=D/'results';R=D.parents[2]
def read(p):return json.loads(p.read_text())
def jl(p):return [json.loads(x) for x in p.read_text().splitlines()]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
bound=read(D/'input-binding.json')
for k,p in [('manifest_sha256',D/'inputs/manifest.json'),('protocol_sha256',D/'inputs/protocol.json'),('cases_sha256',D/'inputs/cases.json'),('script_sha256',D/'diagnose.py')]:assert sha(p)==bound[k]
for n,m in read(D/'inputs/manifest.json')['files'].items():assert sha(D/'inputs'/n)==m['sha256']
complete=read(O/'completed.json');assert complete['complete'] and complete['scores']==256 and complete['generations']==128
assert complete['adapter_memory_unchanged'] and not complete['training'] and complete['judge_calls']==0
assert sha(O/'scores.jsonl')==complete['scores_sha256'] and sha(O/'generations.jsonl')==complete['generations_sha256']
check=read(O/'ablation-check.json');assert check['zero_scaling_equals_disabled'] and check['max_logit_difference']==0
assert check['adapter_memory_sha256_before']==complete['adapter_memory_sha256']
all_modules=set(read(O/'modules-all_on.json')['active_modules'])
attn=set(read(O/'modules-attention_only.json')['active_modules']);mlp=set(read(O/'modules-mlp_only.json')['active_modules'])
assert len(all_modules)==252 and len(attn)==144 and len(mlp)==108 and not attn&mlp and attn|mlp==all_modules
assert not read(O/'modules-all_off.json')['active_modules']
scores=jl(O/'scores.jsonl');gens=jl(O/'generations.jsonl');arms=['all_on','attention_only','mlp_only','all_off']
assert Counter(x['arm'] for x in scores)==dict.fromkeys(arms,64)
assert Counter(x['arm'] for x in gens)==dict.fromkeys(arms,32)
prefixes=defaultdict(set);targets=defaultdict(set)
for r in scores:prefixes[(r['case_id'],r['system'])].add(r['prefix_sha256']);targets[(r['case_id'],r['system'],r['reference'])].add(r['target_sha256'])
assert all(len(x)==1 for x in [*prefixes.values(),*targets.values()])
for r in gens:assert r['prefix_sha256'] in prefixes[(r['case_id'],r['system'])] and r['seed'] in [42,43] and len(r['token_ids'])==r['output_tokens']<=2048
summary=read(D/'SUMMARY.json');assert summary['unreviewed_slots']==0
hold=read(R/'stage2/uat-pause-hold.json');assert hold['active'] and not hold['automatic_restore_authorized']
live=read(D/'final-runtime.json');assert live['replicas']==live['ready_replicas']==0 and live['spec_equal_except_replicas'] and live['task_pod_deleted']
save={'verified':True,'scores':256,'generations':128,'same_prompt_and_target_tokens_for_all_arms':True,'active_modules':{'all_on':252,'attention_only':144,'mlp_only':108,'all_off':0},'zero_scaling_matches_disabled_adapter':True,'adapter_memory_unchanged':True,'unique_reviewed':summary['reviewed_unique'],'unreviewed_slots':0,'uat_stays_paused':True,'training':False,'deployment':False,'judge_calls':0,'task_pod_deleted':True,'files_sha256':{str(p.relative_to(D)):sha(p) for p in [O/'completed.json',O/'verdicts.jsonl',D/'SUMMARY.json',D/'REPORT.md',D/'final-runtime.json',D/'results.tar.gz']}}
(D/'verification.json').write_text(json.dumps(save,indent=2)+'\n');print(json.dumps(save))
