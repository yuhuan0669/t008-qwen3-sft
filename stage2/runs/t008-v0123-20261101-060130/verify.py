"""Verify completed evidence; no training, generation or serving mutations."""
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,math,tarfile
D=Path(__file__).resolve().parent;R=D.parents[2];V=R/'stage1/variants/stage1-cpu-v0.1.23'
def read(p):return json.loads(p.read_text())
def jl(p):return [json.loads(s) for s in p.read_text().splitlines()]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
frozen=read(V/'FILES.sha256.json')['files']
for n,h in frozen.items():assert sha(V/n)==h,n
for n,h in read(D/'execution-code-binding.json')['sha256'].items():assert sha(D/n)==h,n
full=read(D/'outputs/full/run_manifest.json');smoke=read(D/'outputs/smoke/run_manifest.json');cpu=read(D/'cpu-report.json')
assert full['training_verified'] and full['global_step']==66 and full['epoch']==1.0
assert smoke['training_verified'] and smoke['global_step']==3
assert full['command']==read(D/'expected-full-command.json')
assert full['data_sha256']==cpu['dataset_sha256']==sha(V/'train.jsonl')
assert full['rows']==cpu['rows']==cpu['actual_loader_rows']==cpu['actual_pipeline_rows']==1047
assert cpu['changed_rows']==64 and cpu['identity_exposures']==234 and cpu['identity_repaired_exposures']==0
assert cpu['unchanged_full_encoding_rows']==983 and cpu['prompt_and_empty_think_masked'] and cpu['all_identity_answer_weights_verified3']
assert all(cpu[k]==0 for k in ['truncated_rows','silent_dropped_rows','overlength_rows','empty_supervision_rows'])
assert all(math.isfinite(x['value']) for x in read(D/'outputs/full/training-scalars.json')['scalars'])
model=read(D/'model-local-copy.json');assert model['verified'] and model['adapter_files_verified']
assert sha(R/model['path'])==full['adapter_package_sha256']==full['clearml_model_readback_sha256']
complete=read(D/'evaluation/complete.json');results=jl(D/'evaluation/results.jsonl')
assert complete['count']==len(results)==208 and sha(D/'evaluation/results.jsonl')==complete['results_sha256']
assert complete['attempts']==208+complete['technical_retries']
inp=read(D/'evaluation/server-input-verification.json');assert inp=={'matched':80,'all_equal':True}
raw=read(D/'raw-evidence-readback.json');archive=D/raw['local_path'];assert raw['verified'] and sha(archive)==raw['sha256']
with tarfile.open(archive) as t:
    for r in results:
        p=r['raw_path'];assert json.load(t.extractfile(p+'/request.json'))==r['request']
        assert json.load(t.extractfile(p+'/response.raw.json'))==r['response']
rows=jl(D/'evaluation/combined.jsonl');assert len(rows)==832
assert Counter(r['model'] for r in rows)==dict.fromkeys(['original_base','v0.1.14','candidate_v0.1.22','candidate_v0.1.23'],208)
assert len({(r['model'],r['group'],r['case_id'],r['repeat']) for r in rows})==832
reuse=read(D/'evaluation/reuse-summary.json')
assert sha(R/reuse['source'])==reuse['source_sha256'] and sha(D/'evaluation/reused-responses.jsonl')==reuse['selected_sha256']
s=read(D/'evaluation/semantic-summary.json')
assert s['slots']==832 and s['unreviewed_slots']==s['unreviewed_unique']==0
for n,h in s['input_binding']['files_sha256'].items():assert sha(D/'evaluation'/n)==h,n
review=read(D/'evaluation/review-evidence.json')
assert review['slots']==832 and review['unique_reviewed']==699 and review['new_unique_root_read']==148
assert sha(D/'evaluation'/review['archive'])==review['archive_sha256']
for n,h in review['files_sha256'].items():assert sha(D/'evaluation'/n)==h,n
trace=read(D/'evaluation/thinking-empty-trace.json')
empty=next(r for r in results if r['case_id']==trace['case_id'] and r['group']==trace['group'])
msg=empty['response']['choices'][0]['message']
assert msg['content'] is None and empty['response']['choices'][0]['finish_reason']=='length'
assert hashlib.sha256(msg['reasoning'].encode()).hexdigest()==trace['reasoning_sha256']
assert msg['reasoning'].count(trace['repeated_segment'])==trace['exact_segment_count']==131
state=read(D/'window-state.json');h=read(D/'uat-health-verification.json')
assert state['restored'] and not state['paused'] and state['service_spec_equal']
assert read(D/'vllm-before.json')['spec']==read(D/'uat-restored.json')['spec']
assert h['verified'] and h['ready_replicas']==1 and h['internal_health']==200
assert len(h['public_health_samples'])>=2 and all(x['status']=='200' for x in h['public_health_samples'][-2:])
final=read(D/'final-runtime-readback.json');assert final['spec_equal'] and final['ready_replicas']==1 and not final['remaining_task_workloads']
out={'verified':True,'utc':datetime.now(timezone.utc).isoformat(),'data_rows':1047,'converted_exposures':64,
     'identity_exposures':234,'full_steps':66,'full_runs':1,'smoke_steps':3,
     'new_generations':208,'reused_responses':624,'reviewed_unique':s['unique_reviewed'],'unreviewed_slots':0,
     'raw_request_response_pairs_verified':208,'server_input_matches':80,'technical_retries':complete['technical_retries'],
     'uat_restored':True,'deployment_spec_equal':True,'health_verified':True,
     'model_deployed':False,'external_judge_called':False,'quality_accepted':False,
     'files_sha256':{str(p.relative_to(D)):sha(p) for p in [D/'outputs/full/run_manifest.json',D/'evaluation/semantic-summary.json',D/'evaluation/review-evidence.json',D/'evaluation/thinking-empty-trace.json',D/'RESULT.md',D/'uat-health-verification.json',D/'raw-evidence-readback.json',D/'final-runtime-readback.json']}}
(D/'execution-verification.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
