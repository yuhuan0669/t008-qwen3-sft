"""Read-only candidate verification plus bounded local evaluation overlap audit."""
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
import hashlib
import json
import re
import sys

D=Path(__file__).resolve().parent;ROOT=D.parents[2];P=D.parent/'stage1-cpu-v0.1.14'
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rows=lambda p:[json.loads(x) for x in p.read_text().splitlines()]
normalize=lambda t:re.sub(r'\s+','',t).casefold()

def overlap_audit():
    sources=[ROOT.parent/'t024_manual_checks_20261027/echo30_readonly_audit/raw_evidence_84.json',
             ROOT/'stage1/evaluation/development-24.jsonl',ROOT/'stage1/evaluation/public-development.jsonl']
    questions={}; coverage=[]
    def collect(x,prefix):
        if isinstance(x,list):
            for i,v in enumerate(x):collect(v,f'{prefix}/{i}')
        elif isinstance(x,dict):
            ident=str(x.get('question_id',x.get('id',prefix)))
            for k,v in x.items():
                if k in {'question','prompt','problem'} and isinstance(v,str) and v.strip():questions.setdefault(v,ident)
                elif k=='user_turns' and isinstance(v,list):
                    t='\n'.join(z for z in v if isinstance(z,str))
                    if t:questions.setdefault(t,ident)
                elif isinstance(v,(list,dict)):collect(v,ident+'/'+k)
    for path in sources:
        if not path.exists():
            coverage.append({'path':str(path),'available':False});continue
        data=rows(path) if path.suffix=='.jsonl' else read(path)
        before=len(questions);collect(data,path.name)
        coverage.append({'path':str(path),'sha256':sha(path),'added_unique_questions':len(questions)-before,'available':True})
    nearest=[];flags=[]
    for s in read(D/'new-samples.json'):
        q=normalize('\n'.join(t['user'] for t in s['turns']))
        best=(0.0,None)
        for other,ident in questions.items():
            v=normalize(other)
            score=SequenceMatcher(None,q,v,autojunk=False).ratio()
            if score>best[0]:best=(score,ident)
        item={'sample_id':s['id'],'closest_available_eval_id':best[1],'similarity':round(best[0],5),'exact':best[0]==1}
        nearest.append(item)
        if best[0]>=.70:flags.append(item)
    return {'checked_unique_questions':len(questions),'sources':coverage,'threshold':.70,
            'algorithm':'Whitespace-normalized full user-context SequenceMatcher; only new samples are checked.',
            'exact_matches':sum(x['exact'] for x in nearest),'flagged':flags,'nearest':nearest,
            'boundary':'This is a bounded lexical audit against available local evidence, not proof of no semantic overlap with the full T021/T024 bank. No private held-out bank was opened.'}

def main():
    parent=rows(P/'train.jsonl');candidate=rows(D/'train.jsonl');mapping=rows(D/'train-map.jsonl')
    stats=read(D/'statistics.json');cfg=read(D/'training-config.json');pcfg=read(P/'training-config.json')
    system=(D/'system.txt').read_text();cpu=read(D/'cpu-check/report.json')
    assert len(parent)==1325 and len(candidate)==len(mapping)==1357
    protected=read(D/'protected-inputs.json')
    assert all(sha(ROOT/p)==h for p,h in protected.items())
    assert sha(P/'train.jsonl')=='0f546c3aa59f8986f6e5f086482d7d40e9c29db6039a6c219ba902830abff6cb'
    unchanged=0;changed=0
    oldlines=(P/'train.jsonl').read_bytes().splitlines(keepends=True)
    newlines=(D/'train.jsonl').read_bytes().splitlines(keepends=True)
    for i,(a,b) in enumerate(zip(parent,candidate)):
        c=dict(b);c['messages']=[m for m in c['messages'] if m['role']!='system']
        assert c==a,(i,'parent fields changed')
        assert mapping[i]['parent_row_zero_based']==i
        if mapping[i]['operation']=='add_system':
            assert b['messages'][0]=={'role':'system','content':system};changed+=1
        else:
            assert oldlines[i]==newlines[i];unchanged+=1
    assert (changed,unchanged)==(143,1182)
    assert stats['before']['first_user_language']==stats['retained_parent_language']
    assert Counter(s['category'] for s in read(D/'new-samples.json'))==Counter({'fact_edit':8,'task_intent':8,'evidence':8,'multiturn_scope':8})
    for r in candidate[1325:]:
        assert r['messages'][0]=={'role':'system','content':system}
        assert all(m['content'].startswith('<think>\n\n</think>\n\n') for m in r['messages'] if m['role']=='assistant')
        assert all(normalize(m['content'].split('</think>',1)[-1]) not in {normalize(u['content']) for u in r['messages'] if u['role']=='user'} for m in r['messages'] if m['role']=='assistant')
    assert '历史内容不扩大服务范围' in system
    assert not cfg['execution_authorized'] and not cfg['resume'] and cfg['new_lora']
    assert [x.replace(D.name,P.name) for x in cfg['full_argv']]==pcfg['full_argv']
    assert cfg['cpu_validation_report']==str((D/'cpu-check/report.json').relative_to(ROOT))
    assert sha(D/'identity_loss3.py')==sha(P/'identity_loss3.py')
    assert cpu['verified'] and cpu['dataset_sha256']==cfg['dataset_sha256']==sha(D/'train.jsonl')
    for k in ['overlength_rows','truncated_rows','silent_dropped_rows','empty_supervision_rows','weight_mismatch_rows']:assert cpu[k]==0
    assert cpu['unchanged_parent_supervision_and_weights_rows']==1325
    assert cpu['all_234_identity_exposures_answer_weight3'] and cpu['all_new_rows_weight1']
    binding=read(D/'cpu-check/input-binding.json')
    snapshot=D/'cpu-check/training-config.input.json'
    cfg_input=read(snapshot) if snapshot.exists() else cfg
    assert sha(snapshot if snapshot.exists() else D/'training-config.json')==binding['training_config_sha256']
    assert {k:v for k,v in cfg.items() if k not in {'status','runtime_validation'}}=={k:v for k,v in cfg_input.items() if k not in {'status','runtime_validation'}}
    assert binding['dataset_sha256']==sha(D/'train.jsonl')
    assert binding['identity_keys_sha256']==sha(D/'identity-keys.json')
    assert binding['checker_sha256']==sha(D/'cpu-check/check_cpu.py')
    assert read(D/'cpu-check/cpu-exit.json')['returncode']==0
    restore=read(D/'cpu-check/uat-after-verification.json')
    assert restore['original_spec_equal'] and restore['cpu_pod_deleted'] and restore['after_ready']==restore['after_available']==1
    assert not restore['gpu_requested'] and not restore['uat_mutation']
    ev=read(D/'evaluation-config.json')
    assert not ev['execution_authorized'] and ev['request_modes']==read(P/'evaluation-config.json')['request_modes']
    assert sha(ROOT/ev['chat_template']['path'])==ev['chat_template']['sha256']
    assert (ROOT/ev['system_path']).read_text()==system and sha(D/'system.txt')==ev['system_sha256']
    raw=(D/'system-source.txt').read_bytes();source=read(D/'system-source.json')
    assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==source['blob_sha']
    overlap=overlap_audit();(D/'evaluation-overlap.json').write_text(json.dumps(overlap,ensure_ascii=False,indent=2)+'\n')
    assert overlap['exact_matches']==0 and not overlap['flagged'],overlap['flagged']
    result={'verified':True,'parent_files_unchanged':len(protected),'parent_rows_preserved':1325,
            'parent_question_answer_fields_equal':True,'old_language_exposures_unchanged':True,
            'raw_parent_lines_unchanged':1182,'system_added_parent_rows':143,'new_samples':32,'rows':1357,
            'dataset_sha256':sha(D/'train.jsonl'),'system_sha256':sha(D/'system.txt'),
            'native_cpu_verified':True,'training_parameters_unchanged':True,'identity_weight3_preserved':True,
            'template_unchanged':True,'evaluation_overlap_scope_questions':overlap['checked_unique_questions'],
            'evaluation_exact_or_threshold_matches':0,'training_started':False,'inference_executed':False,
            'gpu_used':False,'uat_mutation':False,'cpu_pod_deleted':True,'human_review':'PENDING',
            'remote_sync':'NOT_REQUESTED_LOCAL_ONLY'}
    (D/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
