"""Freeze a local development set and index reusable saved outputs; no API calls."""
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path

D=Path(__file__).resolve().parent
ROOT=D.parents[2]
WS=ROOT.parent
OUT=D/'development'
FIVE=WS/'t024_ab_review_20261030'
P=D.parent/'stage1-cpu-v0.1.16'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
digest=lambda x:hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
read=lambda p:json.loads(p.read_text())
def save(path,obj): path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')

def main():
    old=read(FIVE/'five_group_analysis/fast128_candidates.json')
    notes=dict(line.split('|',1) for line in (OUT/'criteria-notes.txt').read_text().splitlines())
    assert set(notes)=={x['question_id'] for x in old['items']} and len(notes)==128
    supplemental=read(OUT/'supplemental-cases.json')
    assert len(supplemental)==12
    items=[]
    for x in old['items']:
        items.append({'id':x['question_id'],'question':x['question'],
            'messages':[{'role':'user','content':x['question']}],
            'question_sha256':x['source_question_sha256'],'bank':x['bank'],
            'group':x['selection_tag'],'criteria':[notes[x['question_id']]],
            'provenance':'Previously exposed simplified-full-v6 regression case; not unseen acceptance.'})
    for x in supplemental:
        q=x['messages'][0]['content']
        items.append({**x,'question':q,'question_sha256':hashlib.sha256(q.encode()).hexdigest()})
    assert len({x['id'] for x in items})==140
    assert all(len(x['messages'])==1 and x['messages'][0]['role']=='user' for x in items)
    echoes=[x['id'] for x in items if x['group'].startswith('复述/')]
    identities=[x['id'] for x in items if x['group']=='identity']
    jsons=[x['id'] for x in items if x['group']=='json']
    assert (len(echoes),len(identities),len(jsons))==(32,8,4)
    save(OUT/'cases.json',{'status':'FROZEN_DEVELOPMENT_FOR_REVIEW_NOT_EXECUTED','count':140,
        'source_fast128_sha256':sha(FIVE/'five_group_analysis/fast128_candidates.json'),
        'criteria_notes_sha256':sha(OUT/'criteria-notes.txt'),'items':items})
    parent_ev=read(P/'evaluation-config.json')
    modes=deepcopy(parent_ev['request_modes'])
    for v in modes.values():
        v.update(repetition_penalty=1,presence_penalty=0,frequency_penalty=0,n=1,stream=False)
    protocol={'status':'PROPOSED_FROZEN_FOR_REVIEW_NO_EXECUTION','execution_authorized':False,
        'models':['original_base','v0.1.14','v0.1.16','candidate_v0.1.17'],
        'model_aliases':{'original_base':'octa-carbon-v1','v0.1.14':'octa-carbon-sft-v0114',
            'v0.1.16':'octa-carbon-sft-v0116','candidate_v0.1.17':'UNDEPLOYED_DIAGNOSTIC_ONLY'},
        'backend':'vllm','system_path':str((D/'system.txt').relative_to(ROOT)),
        'system_sha256':sha(D/'system.txt'),'chat_template':parent_ev['chat_template'],
        'request_modes':modes,'seed_policy':'Omit request seed, as in the five archived groups; select repeats by number, never by quality.',
        'n':1,'concurrency':8,'max_model_len':8192,
        'cases_path':str((OUT/'cases.json').relative_to(ROOT)),'cases_sha256':sha(OUT/'cases.json'),
        'groups':[
            {'name':'nt_system','mode':'nonthinking','system':True,'case_ids':[x['id'] for x in items],'repeats':3},
            {'name':'nt_no_system','mode':'nonthinking','system':False,'case_ids':echoes+identities,'repeats':3},
            {'name':'thinking_system','mode':'thinking','system':True,'case_ids':echoes[:10]+identities[:4]+jsons[:2],'repeats':1}],
        'json_schema_application':'Only JSON cases: same response_format=json_schema name/schema/strict=true on all models; score values separately.',
        'score_axes':['exact_echo','near_echo_confirmed','repetitive_loop','task_completion','given_facts',
            'unsupported_additions','chinese_identity','scope_and_harmful_help','json_schema','json_values','empty','truncated'],
        'historical_judge':'Metadata only; PASS is not task completion. Re-score the retained and new responses on the same axes.',
        'no_system_native_identity':'Reference only; native model was not trained for the custom product name. Do not call its original identity a regression.',
        'retries':'Only transport/technical failures. Retain first completed response for each numbered slot, including bad semantics or length finish.',
        'selection':'Historical failure enrichment; question-level paired descriptive comparison, not population pass rate or independent acceptance.',
        'baseline_reuse':'Only exact question, model weights, System bytes, rendered template and request settings match. Saved runs have different batching/times, not a same-seed causal experiment.',
        'stop':'One final-epoch candidate. No result-driven extra Full, changed thresholds, selective seeds or automatic deployment.'}
    slots=[]
    for group in protocol['groups']:
        for model in protocol['models']:
            for qid in group['case_ids']:
                for rep in range(1,group['repeats']+1):
                    slots.append({'group':group['name'],'model':model,'case_id':qid,'repeat':rep})
    template_hash=protocol['chat_template']['sha256']
    file_checks={}
    raw_proof=FIVE/'regression_localization_20261031/raw_binding_summary.json'
    proof=read(raw_proof)
    for name in ['A','B','A0','B0','C']:
        assert proof[name]['expected_keys_equal'] and not proof[name]['mismatches']
        target=modes['thinking' if name=='C' else 'nonthinking']
        assert sum(x['count'] for x in proof[name]['parameters'])==11859
        for entry in proof[name]['parameters']:
            assert {k:v for k,v in entry['value'].items() if k!='model'}==target
    file_checks[str(raw_proof.relative_to(WS))]=sha(raw_proof)
    for area,proof in [('with_system','LIVE_MODEL_FILES_VERIFICATION.json'),('without_system','LIVE_NO_SYSTEM_VERIFICATION.json')]:
        path=FIVE/'results'/area/proof
        x=read(path);assert x['shared_template_sha256']==template_hash
        file_checks[str(path.relative_to(WS))]=sha(path)
        for group in ['A','B']:
            cfg=FIVE/'results'/area/group/'generation/config.json'
            parameters=read(cfg)['parameters']
            assert {k:v for k,v in parameters.items() if k!='model'}==modes['nonthinking']
            file_checks[str(cfg.relative_to(WS))]=sha(cfg)
    tp=FIVE/'thinking_results/LIVE_THINKING_SYSTEM_VERIFICATION.json'
    assert read(tp)['chat_template_sha256']==template_hash
    file_checks[str(tp.relative_to(WS))]=sha(tp)
    byid={x['id']:x for x in items}
    sources=[('nt_system',FIVE/'results/with_system/answers.jsonl',{'A':'original_base','B':'v0.1.16'}),
             ('nt_no_system',FIVE/'results/without_system/answers.jsonl',{'A':'original_base','B':'v0.1.16'}),
             ('thinking_system',FIVE/'thinking_results/answers.jsonl',{'C':'v0.1.16'})]
    saved={}
    for group,path,models in sources:
        file_checks[str(path.relative_to(WS))]=sha(path)
        for ln,line in enumerate(path.open(),1):
            r=json.loads(line);qid=r['question_id']
            if qid not in byid:continue
            assert r['question']==byid[qid]['question']
            if group!='nt_no_system':assert r['system_sha256']==protocol['system_sha256']
            model=models[r['group']]
            saved[(group,model,qid,r['repeat'])]={'source_file':str(path.relative_to(WS)),
                'source_line':ln,'record_id':r['record_id'],'answer_sha256':hashlib.sha256(r['answer'].encode()).hexdigest(),
                'answer':r['answer'],'finish_reason':r['finish_reason']}
    v14=ROOT/'stage2/diagnostics/v0114-no-system-20261031/results.jsonl'
    file_checks[str(v14.relative_to(WS))]=sha(v14)
    for ln,line in enumerate(v14.open(),1):
        r=json.loads(line);qid=r['case_id']
        if qid not in byid:continue
        assert r['question']==byid[qid]['question'] and r['http_status']==200
        request_path=v14.parent/r['evidence']/'request.json'
        request=read(request_path)
        assert sha(request_path)==r['request_sha256']
        assert request['model']=='octa-carbon-sft-v0114'
        assert request['messages']==[{'role':'user','content':r['question']}]
        assert {k:v for k,v in request.items() if k not in ['model','messages']}==modes['nonthinking']
        saved[('nt_no_system','v0.1.14',qid,r['repeat'])]={'source_file':str(v14.relative_to(WS)),
            'source_line':ln,'record_id':r['slot_id'],'request_sha256':r['request_sha256'],
            'response_sha256':r['response_sha256'],'raw_evidence':str((v14.parent/r['evidence']).relative_to(WS)),
            'answer_sha256':hashlib.sha256(r['answer'].encode()).hexdigest(),'answer':r['answer'],'finish_reason':r['finish_reason']}
    reused,missing=[],[]
    for slot in slots:
        key=(slot['group'],slot['model'],slot['case_id'],slot['repeat'])
        if key in saved:reused.append({**slot,**saved[key]})
        else:missing.append(slot)
    (OUT/'reused-responses.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in reused))
    save(OUT/'missing-slots.json',missing)
    summary={'comparison_slots':len(slots),'reusable_saved_slots':len(reused),'new_generation_slots':len(missing),
        'reused_by_model':dict(Counter(x['model'] for x in reused)),
        'missing_by_model':dict(Counter(x['model'] for x in missing)),
        'missing_by_group':dict(Counter(x['group'] for x in missing)),
        'sources_sha256':file_checks,'conditions':'Reuse still requires pre-run readback of weights/runtime/template; no new generation performed.'}
    protocol['planned_requests']={k:summary[k] for k in ['comparison_slots','reusable_saved_slots','new_generation_slots']}
    protocol['reuse_manifest_path']=str((OUT/'reuse-summary.json').relative_to(ROOT))
    save(OUT/'reuse-summary.json',summary)
    save(D/'evaluation-config.json',protocol)
    (OUT/'CASES.md').write_text('# 140题开发回归集\n\n已暴露开发题，不是独立验收题；题面不加入训练。\n\n'+
        '\n\n'.join(f"## {x['id']} · {x['group']}\n\n{x['question']}\n\n判据："+'；'.join(x['criteria']) for x in items)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k!='sources_sha256'},ensure_ascii=False))

if __name__=='__main__':main()
