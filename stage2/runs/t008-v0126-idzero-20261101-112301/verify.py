"""Verify the saved ablation, original requests and review; no runtime mutation."""
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,math,tarfile,zipfile
D=Path(__file__).resolve().parent;R=D.parents[2];V=R/'stage1/variants/stage1-cpu-v0.1.22'
def read(p):return json.loads(p.read_text())
def jl(p):return [json.loads(s) for s in p.read_text().splitlines()]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for n,h in read(V/'FILES.sha256.json')['files'].items():assert sha(V/n)==h,n
binding=read(D/'execution-code-binding.json')
for n,h in binding['files_sha256'].items():assert sha(D/n)==h,n
cpu=read(D/'ablation-cpu-report.json');assert cpu['verified']
assert cpu['nonidentity_native_loss_gradient_rng_bitwise_equal'] and cpu['all_native_denominators_preserved']
assert cpu['plugin_sha256']==sha(D/'ablation/identity_zero.py')
members=read(D/'ablation/membership.json')['members'];audits={}
for stage,steps in [('smoke',3),('full',66)]:
    m=read(D/'outputs'/stage/'run_manifest.json');a=jl(D/'outputs'/stage/'identity-zero-audit.jsonl')
    assert m['training_verified'] and m['identity_zero_audit_verified'] and m['global_step']==steps
    assert m['source_commit']==binding['prepared_commit'] and m['data_sha256']==sha(V/'train.jsonl')
    assert m['adapter_scope']['parameter_count']==21823488 and m['adapter_scope']['tensor_count']==504
    assert m['identity_zero']['plugin_sha256']==sha(D/'ablation/identity_zero.py')
    assert m['identity_zero_audit']['sha256']==sha(D/'outputs'/stage/'identity-zero-audit.jsonl')
    assert all(x['weighted_after']==(0 if x['identity'] else x['weighted_before']) for x in a)
    for start in range(0,len(a),16):
        g=a[start:start+16];assert all(x['num_items_in_batch']==sum(y['valid_tokens'] for y in g) for x in g)
    assert all(math.isfinite(x['value']) for x in read(D/'outputs'/stage/'training-scalars.json')['scalars'])
    audits[stage]=a
full=read(D/'outputs/full/run_manifest.json');a=audits['full']
assert full['epoch']==1 and full['command']==read(D/'expected-full-command.json')
assert len(a)==1047 and sum(x['identity'] for x in a)==234
assert Counter(x['key'] for x in a)==Counter({k:v['multiplicity'] for k,v in members.items()})
assert sum(x['valid_tokens'] for x in a)==928890 and sum(x['weighted_after'] for x in a)==920027
local=read(D/'model-local-copy.json');assert local['verified']
assert sha(R/local['path'])==full['adapter_package_sha256']==full['clearml_model_readback_sha256']
with zipfile.ZipFile(R/local['path']) as z:
    for n,h in full['adapter_files'].items():assert hashlib.sha256(z.read(n)).hexdigest()==h['sha256']
results=jl(D/'evaluation/results.jsonl');done=read(D/'evaluation/complete.json')
assert len(results)==done['count']==208 and sha(D/'evaluation/results.jsonl')==done['results_sha256']
assert done['attempts']==208+done['technical_retries']
assert read(D/'evaluation/server-input-verification.json')=={'matched':80,'all_equal':True}
raw=read(D/'raw-evidence-readback.json');assert raw['verified'] and sha(D/raw['local_path'])==raw['sha256']
with tarfile.open(D/raw['local_path'],'r:gz') as t:
    allnames=t.getnames();assert sum(n.endswith('response.raw.json') for n in allnames)==208
    for r in results:
        name=r['raw_path'].removeprefix('/runwork/evaluation/')
        parsed=json.loads(t.extractfile(name+'/response.raw.json').read())
        assert parsed==r['response']
        req=json.loads(t.extractfile(name+'/request.json').read())
        assert req==r['request']
        assert 'seed' not in req and req['n']==1
combined=jl(D/'evaluation/combined.jsonl')
assert len(combined)==832 and Counter(x['model'] for x in combined)==dict.fromkeys(['original_base','v0.1.14','candidate_v0.1.22','candidate_v0.1.26'],208)
assert len({(x['model'],x['group'],x['case_id'],x['repeat']) for x in combined})==832
reuse=read(D/'evaluation/reuse-summary.json')
assert sha(R/reuse['source'])==reuse['source_sha256']
assert sha(D/'evaluation/reused-responses.jsonl')==reuse['selected_sha256']
semantic=read(D/'evaluation/semantic-summary.json');queue=read(D/'evaluation/review-queue.json')
assert semantic['slots']==832 and semantic['unreviewed_slots']==0
for n,h in semantic['input_binding']['files_sha256'].items():assert sha(D/'evaluation'/n)==h,n
review=read(D/'evaluation/review-evidence.json')
assert review['slots']==832 and review['unique_reviewed']==semantic['unique_reviewed']
assert review['new_unique_root_read']==queue['new_unique_review_required']
assert sha(D/'evaluation'/review['archive'])==review['archive_sha256']
for n,h in review['files_sha256'].items():assert sha(D/'evaluation'/n)==h,n
state=read(D/'window-state.json');final=read(D/'final-runtime-readback.json')
assert state['paused'] and not state['restored'] and state['task_gpu_cleaned']
assert final['replicas']==final['ready_replicas']==0 and not final['remaining_task_workloads']
assert final['spec_equal_except_replicas'] and not final['automatic_restore_authorized']
out={'verified':True,'utc':datetime.now(timezone.utc).isoformat(),'data_rows':1047,'data_changed':False,
 'identity_rows_zeroed':234,'remaining_supervised_rows':813,'denominator_tokens':928890,'weighted_after':920027,
 'native_batch_denominators_preserved':True,'full_steps':66,'full_runs':1,'smoke_steps':3,
 'trainable_parameters':21823488,'new_generations':208,'reused_responses':624,
 'reviewed_unique':semantic['unique_reviewed'],'unreviewed_slots':0,'raw_request_response_pairs_verified':208,
 'server_input_matches':80,'technical_retries':done['technical_retries'],'uat_paused':True,'uat_restored':False,
 'automatic_restore_authorized':False,'model_deployed':False,'external_judge_called':False,'quality_accepted':False,
 'files_sha256':{str(p.relative_to(D)):sha(p) for p in [D/'outputs/full/run_manifest.json',D/'evaluation/semantic-summary.json',D/'evaluation/review-evidence.json',D/'RESULT.md',D/'raw-evidence-readback.json',D/'final-runtime-readback.json']}}
(D/'execution-verification.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
