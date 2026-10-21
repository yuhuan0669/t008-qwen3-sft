"""Verify the complete frozen matrix and freshly restored UAT; read-only cluster calls."""
from pathlib import Path
from collections import Counter
import datetime
import hashlib
import json
import subprocess

O=Path(__file__).resolve().parent
R=O.parents[2]
K=['kubectl','--context','lmas00-direct','--request-timeout=30s']


def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(*args):return subprocess.check_output(K+list(args),text=True,timeout=90)
def save(name,x):(O/name).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')


def main():
    spec=load(O/'spec.json'); cases=[json.loads(x) for x in (O/'scenarios.jsonl').read_text().splitlines()]
    rows=[json.loads(x) for x in (O/'results/results.jsonl').read_text().splitlines()]
    assert len(rows)==468
    expected={f"{c['id']}__{mode}__{seed}__{model}__{t}" for c in cases for mode in spec['modes']
              for seed in spec['seeds'] for model in spec['models'] for t in range(1,len(c['user_turns'])+1)}
    assert len(expected)==468 and {r['id'] for r in rows}==expected
    assert len({r['id'] for r in rows})==468
    assert all('error' not in r and r['input_ids_verified'] is True for r in rows)
    assert all(r['response']['model']==r['model'] for r in rows)
    assert load(O/'results/complete.json')['results_sha256']==sha(O/'results/results.jsonl')
    assert load(O/'results/preflight.json')['status']=='PASS'
    assert load(O/'results/preflight.json')['versions']==spec['versions']
    for name in ['run.py','spec.json','scenarios.jsonl','thinking-prefill.jinja','custom-system.txt','authorization.json','base-files.json']:
        assert sha(O/name)==sha(O/'results'/name),name
    for filename,key in [('scenarios.jsonl','scenarios_sha256'),('custom-system.txt','system_sha256'),('thinking-prefill.jinja','template_sha256')]:
        assert sha(O/filename)==spec[key]
    prior={}
    for r in rows:
        cfg=dict(spec['modes'][r['mode']]); thinking=cfg.pop('enable_thinking')
        request=r['request']
        assert all(request[k]==v for k,v in cfg.items())
        assert request['seed']==r['seed'] and request['stream'] is False and request['repetition_penalty']==1.0
        assert request['chat_template_kwargs']=={'enable_thinking':thinking}
        case=next(x for x in cases if x['id']==r['case_id'])
        assert request['messages'][0]=={'role':'system','content':(O/'custom-system.txt').read_text()}
        assert request['messages'][-1]=={'role':'user','content':case['user_turns'][r['turn']-1]}
        assert request.get('response_format')==case.get('response_format')
        key=(r['case_id'],r['mode'],r['seed'],r['model'])
        if r['turn']==1:assert len(request['messages'])==2
        else:
            prev=prior[key]
            expected_messages=prev['request']['messages']+[{'role':'assistant','content':prev['response']['choices'][0]['message'].get('content') or ''},request['messages'][-1]]
            assert request['messages']==expected_messages
        prior[key]=r
    log=(O/'results/vllm-server.log').read_text()
    chat_successes=log.count('POST /v1/chat/completions HTTP/1.1" 200 OK')
    assert chat_successes==468,chat_successes
    source_hashes={
        'stage1/variants/stage1-cpu-v0.1.10/train.jsonl':'5b455659b0e3fea30efd5822be1a7fee0e57d2788bc0dcbf79ec755cd5f22788',
        'stage1/variants/stage1-cpu-v0.1.12/train.jsonl':'89da792c5b91a4b5cecda1a90322edc03fdc1f43e6bd0a52082c35e49e81ec8f'}
    for path,expected_sha in source_hashes.items():assert sha(R/path)==expected_sha
    state=load(O/'window-state.json');assert state['restored'] and not state['paused']
    before=load(O/'uat-before.json')
    after=json.loads(read('-n','vllm','get','deployment','vllm','-o','json'))
    assert before['spec']==after['spec']
    assert after['status']['readyReplicas']==after['status']['availableReplicas']==1
    health=json.loads(read('-n','vllm','exec','deployment/vllm','--','python3','-c',
        "import json,urllib.request; print(json.dumps({'health':urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=8).status,'models':json.load(urllib.request.urlopen('http://127.0.0.1:8000/v1/models',timeout=8))}))"))
    assert health['health']==200
    assert [x['id'] for x in health['models']['data']]==[x['id'] for x in load(O/'uat-health-before.json')['models']['data']]
    ingress=subprocess.check_output(['curl','--noproxy','*','--max-time','10','-sS','-o','/dev/null','-w','%{http_code}',
        'https://vllm.10.140.17.125.nip.io/health'],text=True,timeout=20)
    assert ingress=='200'
    pod_name=(O/'pod-name.txt').read_text().strip()
    assert read('-n','swift','get','pod',pod_name,'--ignore-not-found','-o','name').strip()==''
    save('uat-restored.json',after);save('uat-health-after.json',health)
    counts=Counter((x['model'],x['mode']) for x in rows)
    result=dict(status='PASS',verified_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        requests=468,expected_matrix_exact=True,requests_per_model_mode={k[0]+'__'+k[1]:v for k,v in counts.items()},
        chat_successes=chat_successes,retries=0,all_server_prompt_ids_verified=True,
        first_turn_paired_input_groups=load(O/'mechanical-summary.json')['first_turn_groups_verified'],
        runtime_inputs_match_frozen=True,source_datasets_unchanged=True,source_dataset_sha256=source_hashes,
        original_uat_spec_equal=True,uat_ready_replicas=1,health_status=200,ingress_health_status=200,
        uat_model_ids=[x['id'] for x in health['models']['data']],temporary_gpu_pod_removed=True,
        training=False,english=False,subagent=False,new_model_deployed=False,formal_holdout=False)
    save('verification.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
