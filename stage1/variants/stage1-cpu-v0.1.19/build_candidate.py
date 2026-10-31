"""Build a review-only child snapshot; never mutate parents or launch training."""
from collections import Counter
from copy import deepcopy
from pathlib import Path
import difflib, hashlib, json, math, shutil
from edits import REPAIR, QUARANTINE, repair

D=Path(__file__).resolve().parent;R=D.parents[2];P=D.parent/'stage1-cpu-v0.1.17'
A=R/'stage2/diagnostics/data-quality-audit-20261030'
PARENT_SHA='bf5f1aee58d48a510b84669fa351065621e84037b160da91e82cf8cd1b69dc28'
IDENTITY={'swift/self-cognition','t008/chinese-identity-v1','t008/company-facts-v1'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(x):return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def jl(p):return [json.loads(x) for x in p.read_text().splitlines()]
def save(n,x):(D/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def write_jl(n,x):(D/n).write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in x))
def stats(rows,maps):
    return {'rows':len(rows),'source_exposures':dict(Counter(r['dataset'] for r in rows)),
        'language_exposures':dict(Counter(m['language'] for m in maps)),
        'system_rows':sum(any(m['role']=='system' for m in r['messages']) for r in rows),
        'identity_exposures':sum(r['dataset'] in IDENTITY for r in rows),
        'thinking_rows':sum(any(m['role']=='assistant' and m['content'].split('</think>',1)[0].replace('<think>','').strip() for m in r['messages']) for r in rows)}

def main():
    assert sha(P/'train.jsonl')==PARENT_SHA
    assert not (D/'FILES.sha256.json').exists(),'Candidate already frozen; use a new version.'
    parent=jl(P/'train.jsonl');mapping=jl(P/'train-map.jsonl');raw=(P/'train.jsonl').read_text().splitlines(keepends=True)
    evidence=json.loads((A/'root-evidence.json').read_text());ev={x['id']:x for x in evidence}
    assert set(REPAIR)|set(QUARANTINE)<=set(ev)
    selected={};decisions=[]
    for sid in REPAIR.keys()|QUARANTINE.keys():
        e=ev[sid];lines=e['train_rows_one_based']
        assert len(lines)==2 and all(digest(parent[i-1]['messages'])==e['messages_sha256'] for i in lines)
        assert parent[lines[0]-1]==parent[lines[1]-1]
        assert all(parent[i-1]['dataset']=='swift/Qwen3-SFT-Mixin' and mapping[i-1]['language'] in ['zh','mixed'] for i in lines)
        for i in lines:selected[i]=sid
        decisions.append({'sample_id':sid,'operation':'repair' if sid in REPAIR else 'quarantine',
            'parent_lines_one_based':lines,'exposures_before':2,'exposures_after':2 if sid in REPAIR else 0,
            'reason':(REPAIR|QUARANTINE)[sid],'evidence':e,'full_parent_record_read':True})
    decisions.sort(key=lambda x:x['sample_id'])
    rows=[];maps=[];changes=[];quarantine=[];out=[]
    for i,(before,m,line) in enumerate(zip(parent,mapping,raw),1):
        sid=selected.get(i);operation='preserve';after=deepcopy(before)
        if sid in QUARANTINE:
            quarantine.append({'sample_id':sid,'parent_line_one_based':i,'reason':QUARANTINE[sid],'record':before})
            changes.append({'sample_id':sid,'operation':'quarantine','parent_line_one_based':i,'candidate_line_one_based':None,'before':before,'after':None})
            continue
        if sid in REPAIR:
            assert [x['role'] for x in before['messages']]==['user','assistant']
            after['messages'][1]['content']=repair(sid,before['messages'][1]['content']);operation='repair'
            assert after['messages'][0]==before['messages'][0]
            changes.append({'sample_id':sid,'operation':operation,'parent_line_one_based':i,'candidate_line_one_based':len(rows)+1,'before':before,'after':after})
        rows.append(after);out.append(json.dumps(after,ensure_ascii=False)+'\n' if operation=='repair' else line)
        maps.append({**m,'row_zero_based':len(rows)-1,'line_one_based':len(rows),
            'parent_version':P.name,'parent_line_one_based':i,'parent_row_zero_based':i-1,
            'operation':operation,'candidate_line_one_based':len(rows),'sample_audit_id':sid,
            'parent_messages_sha256':digest(before['messages']),'messages_sha256':digest(after['messages']),
            'answer_and_question_unchanged':operation=='preserve','question_and_visible_body_unchanged':operation=='preserve'})
    assert len(rows)==1341 and len(changes)==26 and len(quarantine)==16
    assert sum(x['operation']=='repair' for x in changes)==10
    (D/'train.jsonl').write_text(''.join(out));write_jl('train-map.jsonl',maps);write_jl('changes.jsonl',changes);write_jl('quarantine.jsonl',quarantine)
    save('decisions.json',decisions)
    save('source-audit.json',{'source_root_evidence_sha256':sha(A/'root-evidence.json'),
        'source_ledger_sha256':sha(A/'review-ledger.jsonl'),'items':evidence,
        'deferred_english_ids':sorted(set(ev)-set(REPAIR)-set(QUARANTINE)),
        'scope':'Only root-confirmed Chinese/mainly-Chinese records; other issue and uncertain records not claimed clean.'})
    for n in ['system.txt','identity-keys.json','identity_loss3.py','native-identity-key-aliases.json']:shutil.copyfile(P/n,D/n)
    prior=json.loads((P/'training-config.json').read_text());cfg=deepcopy(prior)
    cfg.update(plan='root-confirmed-general-data-repair',data_version=D.name,dataset_sha256=sha(D/'train.jsonl'),dataset_rows=len(rows),
        parent_dataset_version=P.name,parent_dataset_sha256=PARENT_SHA,status='PREPARED_PENDING_CPU_REVIEW_NO_TRAINING',
        recipe_change='Five general records repaired across both exposures; eight quarantined across both exposures. No other data or hyperparameter change relative to v0.1.17.',
        runtime_validation='Pending native CPU encoding',config_revision='confirmed-data-repair-v0.1.19',
        cpu_validation_report=str((D/'cpu-check/report.json').relative_to(R)),estimated_full_optimizer_steps=math.ceil(len(rows)/16),
        evaluation_usage='Inherited v0.1.17 evaluation protocol reference only; no candidate run or requests prepared.',
        epoch_exposure_note='One epoch over 1341 rows; no replacement or reweighting of quarantined records. Identity exposures remain 234. Separate Smoke would not alter this snapshot.')
    cfg['full_argv']=[s.replace(P.name,D.name) for s in prior['full_argv']]
    cfg['smoke_overrides']['output_dir']=prior['smoke_overrides']['output_dir'].replace(P.name,D.name)
    assert [s.replace(D.name,P.name) for s in cfg['full_argv']]==prior['full_argv']
    save('training-config.json',cfg)
    save('config-diff.json',{'reference':str((P/'training-config.json').relative_to(R)),
        'hyperparameters_unchanged':True,'learning_rate':1e-4,'v0118_lower_lr_not_inherited':True,
        'only_argv_differences':'dataset/output/plugin version paths; plugin bytes identical',
        'rows_before':1357,'rows_after':1341,'estimated_steps_before':85,'estimated_steps_after':84,
        'scheduler_note':'With one epoch, shorter data also shortens scheduler horizon. Not a fixed-step or fixed-token experiment.',
        'execution_authorized':False})
    save('statistics.json',{'before':stats(parent,mapping),'after':stats(rows,maps),'repaired_records':5,'quarantined_records':8,
        'repaired_exposures':10,'quarantined_exposures':16,'untouched_rows':1331,'cpu_tokens':'pending'})
    save('source-bindings.json',{str((P/n).relative_to(R)):sha(P/n) for n in ['train.jsonl','train-map.jsonl','system.txt','training-config.json','identity-keys.json','identity_loss3.py','selection.json','cpu-check/report.json']})
    save('manifest.json',{'version':D.name,'parent':P.name,'parent_sha256':PARENT_SHA,'status':'PREPARED_NOT_TRAINED',
        'files_sha256':{n:sha(D/n) for n in ['train.jsonl','train-map.jsonl','system.txt','identity-keys.json','identity_loss3.py','changes.jsonl','quarantine.jsonl','decisions.json','source-audit.json']}})
    table=['# 本轮13条处理清单','','父数据：v0.1.17。题目不改；修正样本的两次曝光同步变更。隔离原文保存在quarantine.jsonl。','','|样本|原行号|处理|曝光前→后|理由|','|---|---|---|---:|---|']
    full=['# 修改前后原文','','仅本地审阅。旧记录包含已发现的错误，不能作为正确答案使用。编号继承既有数据审核ID；不是评测题号。']
    for d in decisions:
        sid=d['sample_id'];ch=next(c for c in changes if c['sample_id']==sid);before=ch['before'];after=ch['after']
        table.append(f'|[{sid}](SAMPLES.md#{sid.lower()})|'+','.join(map(str,d['parent_lines_one_based']))+'|'+('修正' if after else '隔离')+f'|2→{d["exposures_after"]}|{d["reason"]}|')
        full+=['',f'<a id="{sid.lower()}"></a>',f'## {sid} — '+('局部修正' if after else '隔离'),'',d['reason'],'','**题目（不变）**',before['messages'][0]['content'],'']
        if after:
            diff=''.join(difflib.unified_diff(before['messages'][1]['content'].splitlines(keepends=True),after['messages'][1]['content'].splitlines(keepends=True),fromfile='before',tofile='after'))
            full+=['**差异**','```diff',diff,'```','', '<details><summary>修改前完整回答</summary>','', '```text',before['messages'][1]['content'],'```','','</details>','', '**修改后完整回答**','```text',after['messages'][1]['content'],'```']
        else:full+=['**处理后**：不进入候选train.jsonl；未提供替代答案。','', '<details><summary>隔离的完整原回答</summary>','','```text',before['messages'][1]['content'],'```','','</details>']
    (D/'CHANGES.md').write_text('\n'.join(table)+'\n');(D/'SAMPLES.md').write_text('\n'.join(full)+'\n')
    print(json.dumps({'rows':len(rows),'repaired_rows':10,'quarantined_rows':16,'untouched_rows':1331,'dataset_sha256':sha(D/'train.jsonl')},ensure_ascii=False))

if __name__=='__main__':main()
