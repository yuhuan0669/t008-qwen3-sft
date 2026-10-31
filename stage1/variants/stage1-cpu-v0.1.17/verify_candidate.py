"""Local structural checks and evidence readback. Does not run the model."""
from collections import Counter
import hashlib
import json
from pathlib import Path

D=Path(__file__).resolve().parent
P=D.parent/'stage1-cpu-v0.1.16'
ROOT=D.parents[2]
read=lambda p:json.loads(p.read_text())
rows=lambda p:[json.loads(x) for x in p.read_text().splitlines()]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    parent,child=rows(P/'train.jsonl'),rows(D/'train.jsonl')
    selection=read(D/'selection.json')['items']
    expected={x['changed_line'] for x in selection}
    actual={i for i,(a,b) in enumerate(zip(parent,child),1) if a!=b}
    assert actual==expected and len(actual)==32 and len(child)==len(parent)==1357
    def strip_think(row):
        return {**row,'messages':[{**m,'content':m['content'].split('</think>',1)[1] if m['role']=='assistant' else m['content']} for m in row['messages']]}
    assert [strip_think(r) for r in parent]==[strip_think(r) for r in child]
    assert Counter(r['dataset'] for r in child)==Counter(r['dataset'] for r in parent)
    for x in selection:
        assert parent[x['retained_thinking_line']-1]==child[x['retained_thinking_line']-1]
        assert parent[x['changed_line']-1]==parent[x['retained_thinking_line']-1]
    for name in ['system.txt','identity_loss3.py','identity-keys.json']:
        assert sha(D/name)==sha(P/name)
    spec=read(D/'training-config.json')
    assert spec['dataset_sha256']==sha(D/'train.jsonl')
    assert not spec['execution_authorized'] and spec['new_lora'] and not spec['resume']
    assert [x.replace(D.name,P.name) for x in spec['full_argv']]==read(P/'training-config.json')['full_argv']
    cpu=read(D/'cpu-check/report.json')
    assert cpu['verified'] and cpu['dataset_sha256']==sha(D/'train.jsonl')
    assert cpu['rows']==cpu['actual_loader_rows']==cpu['actual_pipeline_rows']==1357
    assert cpu['body_target_suffix_equal_all_32'] and cpu['all_identity_encodings_and_weights_unchanged']
    assert read(D/'cpu-check/uat-verification.json')=={'spec_unchanged':True,'healthy':True,'cpu_pod_deleted':True,'uat_pause':False,'gpu_requested':False}
    ev=read(D/'evaluation-config.json')
    assert sha(D/'development/cases.json')==ev['cases_sha256']
    assert sha(ROOT/ev['chat_template']['path'])==ev['chat_template']['sha256']
    cases=read(D/'development/cases.json')['items']
    assert len(cases)==140 and len({x['id'] for x in cases})==140
    # No new question text entered training. Exact overlap is only a mechanical check.
    train_q={m['content'].strip() for r in child for m in r['messages'] if m['role']=='user'}
    exact_overlap=[x['id'] for x in cases if x['question'].strip() in train_q]
    assert not exact_overlap,exact_overlap
    reused=rows(D/'development/reused-responses.jsonl')
    missing=read(D/'development/missing-slots.json')
    slots=lambda xs:{(x['group'],x['model'],x['case_id'],x['repeat']) for x in xs}
    assert not slots(reused)&slots(missing)
    want={(g['name'],m,q,r) for g in ev['groups'] for m in ev['models'] for q in g['case_ids'] for r in range(1,g['repeats']+1)}
    assert slots(reused)|slots(missing)==want and len(want)==2224
    result={'verified':True,'parent_dataset_unchanged':sha(P/'train.jsonl')==spec['parent_dataset_sha256'],
        'rows':1357,'changed_rows':32,'question_and_body_bytes_equal':True,
        'full_argv_equal_except_version_paths':True,'cpu_evidence_matches_current_data':True,
        'development_questions':140,'exact_train_question_overlap':exact_overlap,
        'overlap_scope':'No new training questions or answers; exact string check is not semantic independence proof.',
        'comparison_slots':2224,'reused_slots':len(reused),'missing_slots':len(missing),
        'training_started':False,'new_model_generations':0,'judge_requests':0,'uat_paused':False}
    (D/'final-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
