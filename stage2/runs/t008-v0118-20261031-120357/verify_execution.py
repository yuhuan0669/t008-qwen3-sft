"""Validate finished experiment bytes, requests, schema and restoration; no generation."""
from pathlib import Path
from collections import Counter
import hashlib,json,math,subprocess
D=Path(__file__).resolve().parent;R=D.parents[2];P=D.parent/'t008-v0117-20261031-100924';E=D/'evaluation';V=R/'stage1/variants/stage1-cpu-v0.1.17'
def read(p):return json.loads(p.read_text())
def jl(p):return [json.loads(s) for s in p.read_text().splitlines()]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def key(r):return tuple(r[k] for k in ['group','model','case_id','repeat'])
def main():
    frozen=read(V/'FILES.sha256.json')
    for n,i in frozen.items():assert sha(V/n)==i['sha256'],n
    full=read(D/'outputs/full/run_manifest.json');smoke=read(D/'outputs/smoke/run_manifest.json')
    assert full['training_verified'] and full['training_exit_code']==0 and (full['global_step'],full['epoch'],full['rows'])==(85,1.0,1357)
    assert smoke['global_step']==3 and smoke['training_exit_code']==0
    assert full['command']==read(D/'expected-full-command.json')
    prior=read(P/'outputs/full/run_manifest.json')['command']
    diff=[(a,b) for a,b in zip(prior,full['command']) if a!=b]
    assert len(prior)==len(full['command']) and diff==[('1e-4','5e-5')]
    assert full['data_sha256']==sha(V/'train.jsonl')
    assert full['adapter_package_sha256']==full['clearml_model_readback_sha256']==sha(R/'stage2/local-models/model-v0.1.18/adapter.zip')
    assert full['upload_status']=='VERIFIED'
    scalars=read(D/'outputs/full/training-scalars.json')['scalars'];old=read(P/'outputs/full/training-scalars.json')['scalars']
    lr={x['step']:x['value'] for x in scalars if x['tag']=='train/learning_rate'}
    oldlr={x['step']:x['value'] for x in old if x['tag']=='train/learning_rate'}
    assert lr.keys()==oldlr.keys() and max(lr.values())<=5.000001e-5
    assert all(math.isclose(v,oldlr[k]*.5,rel_tol=1e-6,abs_tol=1e-10) for k,v in lr.items())
    assert all(math.isfinite(x['value']) for x in scalars if 'loss' in x['tag'] or 'grad_norm' in x['tag'])
    cfg=read(E/'evaluation-config.json');oldcfg=read(P/'evaluation/evaluation-config.json')
    for field in read(E/'reuse-summary.json')['unchanged_eval_fields']:assert cfg[field]==oldcfg[field],field
    assert sha(E/'cases.json')==cfg['cases_sha256'] and sha(E/'system.txt')==cfg['system_sha256']
    assert sha(E/'thinking-prefill.jinja')==cfg['chat_template']['sha256']
    assert sha(P/'evaluation/combined.jsonl')==read(E/'reuse-summary.json')['sha256']
    rows=jl(E/'results.jsonl');combined=jl(E/'combined.jsonl');slots=read(E/'missing-slots.json')
    assert len(rows)==556 and set(map(key,rows))==set(map(key,slots))
    assert len(combined)==2780 and len(set(map(key,combined)))==2780
    assert read(E/'complete.json')['results_sha256']==sha(E/'results.jsonl')
    cases={c['id']:c for c in read(E/'cases.json')['items']};groups={g['name']:g for g in cfg['groups']}
    schema_items=[];aliases=read(E/'runtime-binding.json')['aliases']
    for r in rows:
        g=groups[r['group']];c=cases[r['case_id']]
        expect=dict(cfg['request_modes'][g['mode']]);expect.update(model=aliases[r['model']],messages=([{'role':'system','content':(E/'system.txt').read_text()}] if g['system'] else [])+c['messages'])
        if c.get('json_schema'):
            expect['response_format']={'type':'json_schema','json_schema':{'name':'t008_structured_answer','schema':c['json_schema'],'strict':True}}
            schema_items.append({'key':key(r),'answer':r['response']['choices'][0]['message']['content'],'schema':c['json_schema']})
        assert r['request']==expect and r['http_status']==200 and r['input_ids_verified']
        assert r['response']['model']==expect['model']
        raw=E/r['raw_path'];assert read(raw/'request.json')==r['request'] and read(raw/'response.raw.json')==r['response']
        assert key(read(raw/'meta.json'))==key(r)
    assert len(schema_items)==14 and read(E/'server-input-verification.json')=={'matched':196,'all_equal':True}
    script="import json,sys,importlib.metadata as md;from jsonschema import validate\nx=json.load(sys.stdin);errors=[]\nfor r in x:\n try:validate(json.loads(r['answer']),r['schema'])\n except Exception as e:errors.append({'key':r['key'],'error':str(e)})\nprint(json.dumps({'total':len(x),'errors':errors,'jsonschema_version':md.version('jsonschema')}))"
    k=['kubectl','--context','lmas00-direct','--request-timeout=30s','-n','swift','exec','-i',D.name+'-prep','--','python3','-c',script]
    p=subprocess.run(k,input=json.dumps(schema_items),text=True,capture_output=True,check=True);schema= json.loads(p.stdout)
    (E/'json-schema-check.json').write_text(json.dumps(schema,indent=2)+'\n')
    state=read(D/'window-state.json');pub=read(D/'public-restoration-verification.json')
    assert state['restored'] and not state['paused'] and read(D/'vllm-before.json')['spec']==read(D/'uat-restored.json')['spec']
    assert pub['deployment_spec_equal'] and pub['ready']==pub['available']==1 and len(pub['public_health'])==2 and all(x['status']==200 for x in pub['public_health'])
    for name,h in read(D/'execution-code-binding.json')['sha256'].items():assert sha(D/name)==h,name
    report={'status':'PASS','data_files_unchanged':len(frozen),'data_version':'stage1-cpu-v0.1.17','data_rows':1357,
        'full_steps':85,'epoch':1,'only_training_command_change':diff,'logged_learning_rate_half_at_all_logged_steps':True,
        'learning_rate_logged_steps':len(lr),'local_and_clearml_package_verified':True,'new_responses':556,'reused_responses':2224,
        'rendered_prompts_verified':196,'raw_request_response_pairs_verified':556,'schema_check':schema,
        'restoration':pub,'technical_retries':read(E/'complete.json')['technical_retries'],
        'limits':'Integrity verification; semantic findings separately. Old generation times/batches differ; no paired request seed.'}
    (D/'execution-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
