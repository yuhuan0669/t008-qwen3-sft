"""Verify archived evidence without starting jobs, inference or service changes."""
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,math,struct,tarfile,zipfile
D=Path(__file__).resolve().parent;R=D.parents[2];V=R/'stage1/variants/stage1-cpu-v0.1.22'
def read(p):return json.loads(p.read_text())
def jl(p):return [json.loads(s) for s in p.read_text().splitlines()]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for n,h in read(V/'FILES.sha256.json')['files'].items():assert sha(V/n)==h,n
for n,h in read(D/'execution-code-binding.json')['sha256'].items():assert sha(D/n)==h,n
full=read(D/'outputs/full/run_manifest.json');smoke=read(D/'outputs/smoke/run_manifest.json')
cpu=read(D/'cpu-module-check.json')
assert full['training_verified'] and full['global_step']==66 and full['epoch']==1.0
assert smoke['training_verified'] and smoke['global_step']==3
assert full['command']==read(D/'expected-full-command.json')
assert full['source_commit']==read(D/'execution-code-binding.json')['source_git_commit']
assert full['data_sha256']==cpu['dataset_sha256']==sha(V/'train.jsonl')
assert full['rows']==cpu['rows']==cpu['native_encoding_equal_rows']==1047
assert cpu['identity_exposures']==234 and cpu['system_rows']==0
assert cpu['max_tokens']==2041 and cpu['overlength_rows']==cpu['silent_dropped_rows']==0
assert all(math.isfinite(x['value']) for x in read(D/'outputs/full/training-scalars.json')['scalars'])
for m in [smoke,full]:
    assert m['adapter_scope']['verified'] and m['adapter_scope']['parameter_count']==7667712
    assert set(m['adapter_scope']['target_modules'])=={'q_proj','k_proj','v_proj','o_proj'}
model=read(D/'model-local-copy.json');assert model['verified'] and model['adapter_files_verified']
assert sha(R/model['path'])==full['adapter_package_sha256']==full['clearml_model_readback_sha256']
with zipfile.ZipFile(R/model['path']) as z:
    cfg=json.loads(z.read('adapter_config.json'));assert set(cfg['target_modules'])=={'q_proj','k_proj','v_proj','o_proj'}
    data=z.read('adapter_model.safetensors');n=struct.unpack('<Q',data[:8])[0];header=json.loads(data[8:8+n])
    tensors={k:v for k,v in header.items() if k!='__metadata__'}
    assert sum(math.prod(t['shape']) for t in tensors.values())==7667712
    assert len(tensors)==288 and all('.lora_' in k and any('.'+m+'.' in k for m in cfg['target_modules']) for k in tensors)
complete=read(D/'evaluation/complete.json');results=jl(D/'evaluation/results.jsonl')
assert complete['count']==len(results)==208 and sha(D/'evaluation/results.jsonl')==complete['results_sha256']
assert complete['attempts']==208+complete['technical_retries']
assert read(D/'evaluation/server-input-verification.json')=={'matched':80,'all_equal':True}
raw=read(D/'raw-evidence-readback.json');archive=D/raw['local_path'];assert raw['verified'] and sha(archive)==raw['sha256']
with tarfile.open(archive) as t:
    for r in results:
        p=r['raw_path'];assert json.load(t.extractfile(p+'/request.json'))==r['request']
        assert json.load(t.extractfile(p+'/response.raw.json'))==r['response']
rows=jl(D/'evaluation/combined.jsonl');assert len(rows)==832
assert Counter(r['model'] for r in rows)==dict.fromkeys(['original_base','v0.1.14','candidate_v0.1.22','candidate_v0.1.24'],208)
assert len({(r['model'],r['group'],r['case_id'],r['repeat']) for r in rows})==832
reuse=read(D/'evaluation/reuse-summary.json')
assert sha(R/reuse['source'])==reuse['source_sha256'] and sha(D/'evaluation/reused-responses.jsonl')==reuse['selected_sha256']
s=read(D/'evaluation/semantic-summary.json');q=read(D/'evaluation/review-queue.json')
assert s['slots']==832 and s['unreviewed_slots']==s['unreviewed_unique']==0
for n,h in s['input_binding']['files_sha256'].items():assert sha(D/'evaluation'/n)==h,n
review=read(D/'evaluation/review-evidence.json')
assert review['slots']==832 and review['unique_reviewed']==s['unique_reviewed']
assert review['new_unique_root_read']==q['new_unique_review_required']
assert sha(D/'evaluation'/review['archive'])==review['archive_sha256']
for n,h in review['files_sha256'].items():assert sha(D/'evaluation'/n)==h,n
state=read(D/'window-state.json');final=read(D/'final-runtime-readback.json')
assert state['paused'] and not state['restored'] and not state['automatic_restore']
assert state['task_gpu_cleaned'] and state['uat_spec_equal_except_replicas']
before=read(D/'vllm-before.json');paused=read(D/'uat-paused-final.json');expected=dict(before['spec']);expected['replicas']=0
assert expected==paused['spec'] and before['metadata']['uid']==paused['metadata']['uid']
assert final['spec_equal_except_replicas'] and final['replicas']==0 and final['ready_replicas']==0 and not final['remaining_task_workloads']
hold=read(R/'stage2/uat-pause-hold.json');assert hold['active'] and hold['run_id']==D.name and not hold['automatic_restore_authorized']
out={'verified':True,'utc':datetime.now(timezone.utc).isoformat(),'data_rows':1047,'data_changed':False,
     'identity_exposures':234,'identity_loss_multiplier':3,'full_steps':66,'full_runs':1,'smoke_steps':3,
     'trainable_parameters':7667712,'target_modules':sorted(cfg['target_modules']),
     'new_generations':208,'reused_responses':624,'reviewed_unique':s['unique_reviewed'],'unreviewed_slots':0,
     'raw_request_response_pairs_verified':208,'server_input_matches':80,'technical_retries':complete['technical_retries'],
     'uat_paused':True,'uat_restored':False,'deployment_spec_equal_except_replicas':True,'automatic_restore_authorized':False,
     'model_deployed':False,'external_judge_called':False,'quality_accepted':False,
     'files_sha256':{str(p.relative_to(D)):sha(p) for p in [D/'outputs/full/run_manifest.json',D/'evaluation/semantic-summary.json',D/'evaluation/review-evidence.json',D/'RESULT.md',D/'raw-evidence-readback.json',D/'final-runtime-readback.json']}}
(D/'execution-verification.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
