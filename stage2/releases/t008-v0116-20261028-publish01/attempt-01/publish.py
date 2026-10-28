"""Authorized LoRA-only release, bounded probes, rollback on release failure."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import subprocess
import time

D=Path(__file__).resolve().parent
ROOT=D.parents[2]
K=['kubectl','--context','lmas00-direct','--request-timeout=30s']
API='https://vllm.10.140.17.125.nip.io'


def now(): return datetime.now(timezone.utc).isoformat()
def save(name,obj): (D/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def call(*args): return subprocess.check_output(K+list(args),text=True,timeout=90)
def get(*args): return json.loads(call(*args,'-o','json'))
def curl(route,body=None):
    argv=['curl','--noproxy','*','--max-time','180','--fail-with-body','-sS',API+route]
    if body is not None: argv+=['-H','Content-Type: application/json','--data-binary','@'+str(body)]
    return subprocess.check_output(argv,text=True,timeout=190)


def ready():
    argv=[x if x!='--request-timeout=30s' else '--request-timeout=0' for x in K]
    with (D/'rollout.log').open('a') as f:
        subprocess.run(argv+['-n','vllm','rollout','status','deployment/vllm','--timeout=600s'],stdout=f,stderr=subprocess.STDOUT,check=True,timeout=630)
    after=get('-n','vllm','get','deployment','vllm')
    assert after['status'].get('readyReplicas')==after['spec']['replicas']==1
    assert after['status']['observedGeneration']==after['metadata']['generation']
    return after


def snapshot_others():
    return [{'namespace':x['metadata']['namespace'],'name':x['metadata']['name'],
             'spec_sha256':hashlib.sha256(json.dumps(x['spec'],sort_keys=True,separators=(',',':')).encode()).hexdigest(),
             'replicas':x['spec'].get('replicas'),'ready':x.get('status',{}).get('readyReplicas',0)}
            for x in get('get','deployments','-A')['items'] if (x['metadata']['namespace'],x['metadata']['name'])!=('vllm','vllm')]


def probes(release):
    source=ROOT/'stage2/runs/t008-v0116-20261028-130519/evaluation'
    spec=json.loads((source/'spec.json').read_text())
    conditions=[json.loads(x) for x in (source/'conditions.jsonl').read_text().splitlines()]
    system=(D/'system.txt').read_text()
    items=[('base-nonthinking','octa-carbon-v1','nonthinking',None),
           ('v0114-nonthinking','octa-carbon-sft-v0114','nonthinking',None),
           ('v0116-nonthinking',release['model_alias'],'nonthinking',None),
           ('v0116-thinking',release['model_alias'],'thinking',None),
           ('v0116-json',release['model_alias'],'nonthinking',next(x for x in conditions if x['case_id']=='D16-12'))]
    result=[]
    for name,model,mode,condition in items:
        question='请用一句话说明你的模型名称。' if mode=='nonthinking' else '一台功率为2千瓦的设备连续运行3小时，用电量是多少？简短回答。'
        messages=condition['messages'] if condition else [{'role':'user','content':question}]
        body={**spec['modes'][mode],**spec['common'],'model':model,'messages':[{'role':'system','content':system}]+messages,'stream':False}
        if condition:body['response_format']=condition['response_format']
        assert 'seed' not in body
        request=D/'probes'/f'{name}-request.json';request.write_text(json.dumps(body,ensure_ascii=False,indent=2)+'\n')
        start=time.monotonic();raw=curl('/v1/chat/completions',request)
        (D/'probes'/f'{name}-response.json').write_text(raw)
        response=json.loads(raw);choice=response['choices'][0];message=choice['message']
        record={'name':name,'model':model,'mode':mode,'seconds':time.monotonic()-start,
                'response_id':response['id'],'model_matches':response['model']==model,
                'finish_reason':choice['finish_reason'],'nonempty':bool((message.get('content') or '').strip()),
                'reasoning_present':bool(message.get('reasoning') or message.get('reasoning_content')),
                'seed_sent':False,'system_sha256':sha(D/'system.txt')}
        assert record['model_matches'] and record['nonempty'] and record['finish_reason']=='stop',record
        if mode=='thinking':assert record['reasoning_present'],record
        if condition:
            value=json.loads(message['content'])
            record['json_values_correct']=isinstance(value,dict) and set(value)=={'items','status'} and sorted(value['items'])==sorted(['抄表日期','用电单位']) and value['status']=='incomplete'
            assert record['json_values_correct'],value
        result.append(record);save('probes/summary.json',result)
        print(now(),name,'PASS',flush=True)
    assert len(result)==5
    return result


def main():
    release=json.loads((D/'release.json').read_text());before=json.loads((D/'deployment-before.json').read_text())
    desired=json.loads((D/'rendered/desired-template.json').read_text())
    live=get('-n','vllm','get','deployment','vllm')
    assert live['metadata']['uid']==before['metadata']['uid'] and live['spec']==before['spec']
    assert json.loads((D/'base-verification-before.json').read_text())['base_files_match']
    assert sha(Path(release['adapter_zip']))==release['adapter_sha256']
    assert not (D/'switch-state.json').exists(),'Do not silently repeat deployment/probes'
    state={'started_at_utc':now(),'release':release['release'],'status':'SWITCHING','replicas_changed':False}
    save('switch-state.json',state)
    try:
        save('deployment-applied.json',json.loads(call('-n','vllm','patch','deployment','vllm','--type=json','--patch-file',str(D/'rendered/publish.patch.json'),'-o','json')))
        print(now(),'Model-service patch applied; waiting for readiness',flush=True)
        after=ready();save('deployment-after.json',after);state['ready_at_utc']=now();save('switch-state.json',state)
        assert after['spec']['template']==desired
        spec_without_template={k:v for k,v in after['spec'].items() if k!='template'}
        assert spec_without_template=={k:v for k,v in before['spec'].items() if k!='template'}
        curl('/health');(D/'health-after.txt').write_text('200\n')
        models=json.loads(curl('/v1/models'));save('models-after.json',models)
        aliases={x['id'] for x in models['data']};assert aliases==set(release['preserved_aliases']+[release['model_alias']]),aliases
        assert next(x for x in models['data'] if x['id']==release['model_alias'])['parent']=='octa-carbon-v1'
        pods=get('-n','vllm','get','pods','-l','app=vllm');save('pods-after.json',pods)
        livepods=[p for p in pods['items'] if p['status']['phase']=='Running' and not p['metadata'].get('deletionTimestamp') and all(x.get('ready') for x in p['status'].get('containerStatuses',[]))]
        assert len(livepods)==1;pod=livepods[0]['metadata']['name']
        script="from pathlib import Path;import hashlib,json;ps=['/adapters/"+release['model_alias']+"/adapter_config.json','/adapters/"+release['model_alias']+"/adapter_model.safetensors','/t008-serving/thinking-prefill.jinja'];print(json.dumps({p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in ps}))"
        hashes=json.loads(call('-n','vllm','exec',pod,'--','python3','-c',script));save('mounted-files-verification.json',hashes)
        for file,info in release['adapter_files'].items():assert hashes['/adapters/'+release['model_alias']+'/'+file]==info['sha256']
        assert hashes['/t008-serving/thinking-prefill.jinja']==release['template_sha256']
        result=probes(release)
        for kind,name in [('service','vllm-service'),('ingress','vllm-ingress')]:
            obj=get('-n','vllm','get',kind,name);save(kind+'-after.json',obj)
            assert obj['spec']==json.loads((D/(kind+'-before.json')).read_text())['spec']
        others=snapshot_others();save('other-deployments-after.json',others)
        prior=json.loads((D/'other-deployments-before.json').read_text())
        key=lambda x:(x['namespace'],x['name'])
        old={key(x):x['spec_sha256'] for x in prior};new={key(x):x['spec_sha256'] for x in others}
        scope={'other_deployments_checked':len(prior),'other_specs_equal':old==new,
               'changed_other_deployments':[list(k) for k in set(old)|set(new) if old.get(k)!=new.get(k)],
               'application_mutation_commands':0,'application_routing_changed':False,
               'service_and_ingress_specs_unchanged':True,'only_model_template_patched':True}
        save('scope-verification.json',scope)
        rollback=json.loads(call('-n','vllm','patch','deployment','vllm','--type=json','--patch-file',str(D/'rendered/rollback.patch.json'),'--dry-run=server','-o','json'))
        assert rollback['spec']==before['spec'];save('rollback-dry-run.json',rollback)
        state.update(status='DEPLOYED_VERIFIED',finished_at_utc=now(),rollback_performed=False)
        save('switch-state.json',state)
        save('verification.json',{'verified':True,'recorded_at_utc':now(),'release':release['release'],'model_alias':release['model_alias'],
             'aliases':sorted(aliases),'ready_replicas':1,'generation':after['metadata']['generation'],'health_http':200,
             'mounted_adapter_and_template_hashes_match':True,'base_files_match':True,'probes_passed':len(result),
             'system_in_all_probe_requests':True,'daily_seed_omitted':True,'rollback_dry_run_full_spec_equal':True,
             'application_configuration_changed':False,'scope':scope,'quality_accepted':False,'training':False})
        print(now(),'Release verified',flush=True)
    except BaseException as exc:
        state.update(status='RELEASE_FAILED',error=repr(exc));save('switch-state.json',state)
        live=get('-n','vllm','get','deployment','vllm')
        if live['metadata']['uid']==before['metadata']['uid'] and live['spec']['template']==desired:
            call('-n','vllm','patch','deployment','vllm','--type=json','--patch-file',str(D/'rendered/rollback.patch.json'))
            restored=ready();assert restored['spec']==before['spec'];curl('/health')
            save('rollback-after.json',restored);state.update(status='ROLLED_BACK',rollback_performed=True,restored_at_utc=now());save('switch-state.json',state)
        raise
    finally:
        # Immutable release files remain available for audit and future authorized use.
        subprocess.run(K+['-n','vllm','delete','pod',release['release']+'-stage','--ignore-not-found','--wait=false'],check=False,capture_output=True)


if __name__=='__main__':main()
