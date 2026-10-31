"""Check review coverage, unchanged controls, archive bytes, and current UAT health."""
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone
import hashlib,json,subprocess,sys
D=Path(__file__).resolve().parent;R=D.parents[2];E=D/'evaluation';P=D.parent/'t008-v0117-20261031-100924';V=R/'stage1/variants/stage1-cpu-v0.1.17'
sys.path.insert(0,str(E))
from summarize import input_binding
def read(p):return json.loads(p.read_text())
def jl(p):return [json.loads(x) for x in p.read_text().splitlines()]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    s=read(E/'semantic-summary.json');old=read(P/'evaluation/semantic-summary.json')
    assert (s['slots'],s['unique_answers'],s['unique_reviewed'],s['unreviewed_slots'])==(2780,2546,2546,0)
    current={(x['model'],x['group'],x['family']):x for x in s['groups']}
    for x in old['groups']:assert current[(x['model'],x['group'],x['family'])]==x,'Historical scores changed'
    review={};files={}
    for p in sorted((E/'review').glob('verdicts-*.jsonl')):
        rows=jl(p)
        for x in rows:
            assert x['review_id'] not in review and x['read_complete'] is True
            assert x['task'] in ['pass','fail','uncertain'] and x['facts'] in ['pass','fail','na','uncertain'] and x['unsupported'] in ['pass','fail','uncertain']
            assert all(type(x[k]) is bool for k in ['harmful_help','improper_refusal','near_echo','repetitive_loop'])
            assert x['note'];review[x['review_id']]=x
        files[p.name]={'count':len(rows),'sha256':sha(p)}
    correction=E/'review/root-corrections.jsonl'
    corrections=jl(correction) if correction.exists() else []
    seen=set()
    for x in corrections:
        assert x['review_id'] in review and x['review_id'] not in seen and x['reason']
        seen.add(x['review_id'])
        assert not (set(x['corrected']) & {'review_id','case_id','read_complete'})
        review[x['review_id']].update(x['corrected'])
    for x in review.values():
        assert x['task'] in ['pass','fail','uncertain'] and x['facts'] in ['pass','fail','na','uncertain'] and x['unsupported'] in ['pass','fail','uncertain']
        assert all(type(x[k]) is bool for k in ['harmful_help','improper_refusal','near_echo','repetitive_loop'])
    assert s['input_binding']==input_binding(review),'Semantic summary is stale relative to effective review labels or inputs'
    for shard in ['a','b','c','root']:
        bundle={a['review_id']:c['case_id'] for c in jl(E/'review'/('bundle-'+shard+'.jsonl')) for a in c['answers']}
        labels={x['review_id']:x['case_id'] for x in jl(E/'review'/('verdicts-'+shard+'.jsonl'))}
        assert labels==bundle,shard
    rows=jl(E/'combined.jsonl');assert len({tuple(x[k] for k in ['group','model','case_id','repeat']) for x in rows})==2780
    for x in rows:
        assert review[x['review_id']]['case_id']==x['case_id']
        assert x['review_id']=='U'+hashlib.sha256((x['case_id']+'\0'+x['group']+'\0'+x['answer']).encode()).hexdigest()[:18]
    for n,h in read(D/'execution-code-binding.json')['sha256'].items():assert sha(D/n)==h,n
    for n,x in read(V/'FILES.sha256.json').items():assert sha(V/n)==x['sha256'],n
    assert read(E/'complete.json')['results_sha256']==sha(E/'results.jsonl')
    assert sha(P/'evaluation/combined.jsonl')==read(E/'reuse-summary.json')['sha256']
    assert sha(E/'raw.tar')==read(D/'raw-archive.json')['sha256']
    m=read(D/'outputs/full/run_manifest.json');assert sha(R/'stage2/local-models/model-v0.1.18/adapter.zip')==m['adapter_package_sha256']
    assert read(D/'execution-verification.json')['status']=='PASS' and read(E/'json-value-check.json')['failed']==0
    k=['kubectl','--context','lmas00-direct','--request-timeout=15s']
    u=json.loads(subprocess.check_output(k+['-n','vllm','get','deploy','vllm','-o','json']))
    assert u['spec']==read(D/'vllm-before.json')['spec'] and u['status']['readyReplicas']==u['status']['availableReplicas']==1
    owned=json.loads(subprocess.check_output(k+['-n','swift','get','pods,jobs','-l','t008-run='+D.name,'-o','json']));assert not owned['items']
    health=subprocess.check_output(['curl','--noproxy','*','-fsS','--max-time','10','-o','/dev/null','-w','%{http_code}','https://vllm.10.140.17.125.nip.io/health'],text=True);assert health=='200'
    schema=json.loads((E/'json-schema-check.json').read_text());assert schema['total']==14 and not schema['errors']
    report={'status':'PASS','verified_at_utc':datetime.now(timezone.utc).isoformat(),'slots':2780,'new_generations':556,
      'inherited_unique_labels':2051,'new_unique_answers_reviewed':495,'unique_reviewed':2546,'unreviewed':0,
      'old_model_scores_unchanged':True,'frozen_data_unchanged':True,'execution_code_unchanged':True,
      'review_files':files,'root_corrections':{'count':len(corrections),'sha256':sha(correction) if correction.exists() else None},
      'summary_sha256':sha(E/'semantic-summary.json'),'summary_input_binding':s['input_binding'],
      'current_uat':{'spec_equal':True,'ready':1,'available':1,'health':200,'temporary_resources':0},
      'quality_accepted':False,'new_model_deployed':False,
      'review_scope':'Three anonymous-answer shards; root identity/JSON and targeted issue review. Historical labels inherited; not a new independent reread or formal Judge.'}
    (D/'final-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
