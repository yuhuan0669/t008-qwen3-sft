"""Derive a review-only candidate; preserve every parent question/answer/exposure."""
from collections import Counter
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import math
import re
import shutil

D = Path(__file__).resolve().parent
ROOT = D.parents[2]
P = D.parent / 'stage1-cpu-v0.1.14'
PARENT_SHA = '0f546c3aa59f8986f6e5f086482d7d40e9c29db6039a6c219ba902830abff6cb'
IDENTITY = {'swift/self-cognition', 't008/chinese-identity-v1', 't008/company-facts-v1'}
BUSINESS = {'t008/project-positioning-v1', 't008/business-evidence-v1', 't008/company-boundary-v1'}
CATEGORIES = {'fact_edit':'事实审校改写', 'task_intent':'区分引用与真实要求',
              'evidence':'证据不足与假设计算', 'multiturn_scope':'多轮业务与范围'}
SOURCE = {c:'t008/nt-' + c.replace('_','-') + '-v1' for c in CATEGORIES}
OTHER_MODEL = {'tongyi是谁研发的','yiyan是谁研发的','通义千问是什么','文心一言是谁研发的',
               '通义千问是谁研发的','qwen是谁研发的','chatgpt是谁研发的','chatbot是谁训练的',
               'chatgpt是谁','星空万言是谁训练的'}
ENGLISH = re.compile(r'(?i)(?<![A-Za-z])(please|hello|hi|who|what|how|why|where|when|your|you|introduce|tell|my|name|are|is)(?![A-Za-z])')
SCOPE_EXCEPTIONS = json.loads((D/'system-exceptions.json').read_text())

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text())
def rows(p): return [json.loads(x) for x in p.read_text().splitlines()]
def save(name, value):
    p=D/name; p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def jsonl(name, value):
    (D/name).write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in value))
def key(messages):
    value=[{'role':m['role'],'content':m['content']} for m in messages]
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def language(row):
    qs=[m['content'].replace('/no_think','') for m in row['messages'] if m['role']=='user']
    if not any(re.search('[\u4e00-\u9fff]',q) for q in qs): return 'en_or_other'
    if any(not re.search('[\u4e00-\u9fff]',q) or ENGLISH.search(q) for q in qs): return 'mixed'
    return 'zh'
def decision(row):
    if row['dataset'] not in IDENTITY|BUSINESS: return 'preserve_general'
    if language(row)!='zh': return 'preserve_english_or_mixed'
    if key(row['messages']) in SCOPE_EXCEPTIONS: return 'preserve_general_scope_conflict'
    q=re.sub(r'[\s！？!?。/]|no_think','',row['messages'][0]['content']).lower()
    if row['dataset']=='swift/self-cognition' and q in OTHER_MODEL: return 'preserve_other_model_knowledge'
    return 'add_system'
def stats(rr):
    result={'rows':len(rr),'unique_message_records':len({key(r['messages']) for r in rr}),
            'source_exposures':dict(Counter(r['dataset'] for r in rr)),
            'first_user_language':dict(Counter(language(r) for r in rr)),
            'system_rows':sum(any(m['role']=='system' for m in r['messages']) for r in rr),
            'no_think_marker_rows':sum(any('/no_think' in m['content'] for m in r['messages'] if m['role']=='user') for r in rr)}
    modes=Counter(); turns=Counter()
    for r in rr:
        rowm=[]
        for m in r['messages']:
            if m['role']!='assistant':continue
            match=re.fullmatch(r'<think>(.*?)</think>\s*(.+)',m['content'],re.S)
            assert match and match[2].strip()
            mode='thinking' if match[1].strip() else 'nonthinking'
            turns[mode]+=1; rowm.append(mode)
        modes['thinking' if 'thinking' in rowm else 'nonthinking']+=1
    result.update(row_modes=dict(modes),assistant_turn_modes=dict(turns))
    return result

def main():
    assert sha(P/'train.jsonl')==PARENT_SHA
    protected={str(p.relative_to(ROOT)):sha(p) for p in P.rglob('*') if p.is_file() and p.name!='.DS_Store' and '__pycache__' not in p.parts}
    parent=rows(P/'train.jsonl'); assert len(parent)==1325
    sys=(D/'system.txt').read_text().strip(); (D/'system.txt').write_text(sys)
    assert '历史内容不扩大服务范围' in sys and '历史不扩大业务范围' not in sys
    samples=read(D/'new-samples.json')
    assert len(samples)==len({s['id'] for s in samples})==32
    assert Counter(s['category'] for s in samples)==Counter({c:8 for c in CATEGORIES})
    candidate=[]; mapping=[]; changes=[]; decisions=Counter()
    oldmap=rows(P/'train-map.jsonl')
    rawlines=(P/'train.jsonl').read_bytes().splitlines(keepends=True)
    outbytes=[]
    for i,r in enumerate(parent):
        a=decision(r); decisions[a]+=1; child=deepcopy(r)
        if a=='add_system': child['messages'].insert(0,{'role':'system','content':sys})
        assert [m for m in child['messages'] if m['role']!='system']==r['messages']
        candidate.append(child)
        outbytes.append((json.dumps(child,ensure_ascii=False)+'\n').encode() if a=='add_system' else rawlines[i])
        mapping.append({'row_zero_based':i,'line_one_based':i+1,'parent_version':P.name,
                        'parent_row_zero_based':i,'parent_line_one_based':i+1,'operation':a,
                        'source':r['dataset'],'group':oldmap[i]['group'],'language':language(r),
                        'parent_messages_sha256':key(r['messages']),'messages_sha256':key(child['messages']),
                        'answer_and_question_unchanged':True})
        if a=='add_system': changes.append({'operation':a,'parent_line_one_based':i+1,'line_one_based':i+1,
                                           'before':r,'after':child,'only_system_added':True})
    for s in samples:
        messages=[{'role':'system','content':sys}]
        for t in s['turns']:
            assert t['user'].strip() and t['assistant'].strip() and '<think>' not in t['assistant']
            messages.extend([{'role':'user','content':t['user']},
                             {'role':'assistant','content':'<think>\n\n</think>\n\n'+t['assistant']}])
        r={'messages':messages,'dataset':SOURCE[s['category']]}; n=len(candidate)
        candidate.append(r); outbytes.append((json.dumps(r,ensure_ascii=False)+'\n').encode())
        mapping.append({'row_zero_based':n,'line_one_based':n+1,'parent_version':None,'parent_row_zero_based':None,
                        'operation':'add','sample_id':s['id'],'category':s['category'],'source':r['dataset'],
                        'group':'instruction','language':'zh','messages_sha256':key(messages),
                        'provenance':'Original synthetic behavior example authored for this review; not real factory evidence.'})
        changes.append({'operation':'add','sample_id':s['id'],'line_one_based':n+1,'before':None,'after':r})
    assert len(candidate)==1357
    assert len({key(r['messages']) for r in candidate[1325:]})==32
    assert not ({key(r['messages'][1:]) for r in candidate[1325:]} & {key(r['messages']) for r in parent})
    (D/'train.jsonl').write_bytes(b''.join(outbytes))
    jsonl('train-map.jsonl',mapping); jsonl('changes.jsonl',changes)
    digest=sha(D/'train.jsonl')
    binding=read(P/'identity-keys.json')
    raw=sorted({key(r['messages']) for r in candidate if r['dataset'] in IDENTITY})
    # Native Swift extracts System outside inputs.messages. Keep the exact frozen
    # parent native keys, including four history-thinking normalization aliases.
    native=binding['identity_message_sha256']
    binding.update(dataset_path=str((D/'train.jsonl').relative_to(ROOT)),dataset_sha256=digest,
                   identity_exposures=234,raw_identity_message_sha256=raw,
                   identity_message_sha256=sorted(set(raw)|set(native)),unique_messages=len(raw),
                   matching_key_count=len(set(raw)|set(native)),native_preprocessing_alias_count=len(set(native)-set(raw)),
                   native_alias_source='native-identity-key-aliases.json')
    save('identity-keys.json',binding)
    save('native-identity-key-aliases.json',{'parent':str((P/'identity-keys.json').relative_to(ROOT)),
         'dataset_sha256':digest,'native_keys':native,'reason':'System is extracted separately; original user/assistant messages and preserve_thinking behavior are unchanged. CPU trace must verify all 234 weights.'})
    shutil.copyfile(P/'identity_loss3.py',D/'identity_loss3.py')
    old=read(P/'training-config.json'); cfg=deepcopy(old)
    cfg['full_argv']=[x.replace(P.name,D.name) for x in cfg['full_argv']]
    cfg.update(plan='short-system-and-32-chinese-nonthinking-examples',data_version=D.name,
               dataset_sha256=digest,dataset_rows=1357,estimated_full_optimizer_steps=math.ceil(1357/16),
               execution_authorized=False,status='PREPARED_PENDING_CPU_AND_REVIEW',resource_window=None,
               recipe_change='Add per-record System where compatible and 32 Chinese nonthinking examples; retain all parent answers and exposures.',
               config_revision='system-task-coverage-v0.1.15',runtime_validation='PENDING_NATIVE_CPU_CHECK',
               cpu_validation_report=str((D/'cpu-check/report.json').relative_to(ROOT)),
               evaluation_config=str((D/'evaluation-config.json').relative_to(ROOT)))
    cfg['smoke_overrides']={k:(v.replace(P.name,D.name) if isinstance(v,str) else v) for k,v in cfg['smoke_overrides'].items()}
    save('training-config.json',cfg)
    ev=read(P/'evaluation-config.json')
    for k in ['development_path','rubric_path','additional_development_path','additional_development_seeds',
              'validation_plan','json_diagnostic_system_path','json_diagnostic_system_sha256','identity_seeds']:
        ev.pop(k,None)
    ev.update(purpose='Proposed 120-request Chinese comparison; not executed or authorized.',
              system_path=str((D/'system.txt').relative_to(ROOT)),system_sha256=sha(D/'system.txt'),
              prior_scope='Historical results remain unchanged; scores with a different System are not reused.',
              execution_authorized=False,formal_holdout_status='NOT_OPENED_OR_MODIFIED',
              comparison_models=['original_base','v0.1.14','candidate_v0.1.15'],
              planned_requests={'per_model':{'fire_diagnostic_nonthinking':20,'other_chinese_nonthinking':12,'thinking_regression':8},'total':120},
              case_set_status='TO_BE_FROZEN_BEFORE_GPU_EXECUTION; historical diagnostic cases separated from unseen checks',
              scoring=['echo','task_completion','preserve_given_facts','unsupported_additions','identity','scope'],
              seed_policy='Diagnostic fixed seeds are for comparison only; everyday application requests omit seed.',
              english_identity='DEFERRED; existing English/mixed natural-language rows unchanged')
    ev['n']=1;ev['presence_penalty']=0;ev['frequency_penalty']=0
    save('evaluation-config.json',ev)
    save('config-diff.json',{'hyperparameters_unchanged':True,'loss_plugin_bytes_unchanged':True,
         'argv_changes':[{'before':a,'after':b} for a,b in zip(old['full_argv'],cfg['full_argv']) if a!=b],
         'parent_exposures_unchanged':True,'identity_exposures':{'before':234,'after':234},
         'dataset_rows':{'before':1325,'after':1357},'optimizer_steps_for_one_epoch':{'before':83,'after':85},
         'system_change':'Per-record addition; no global --system, because general/English rows remain unchanged.',
         'evaluation_change':'New System; same corrected vLLM template and generation settings.'})
    save('statistics.json',{'version':D.name,'parent':P.name,'before':stats(parent),'after':stats(candidate),
         'retained_parent_language':stats(candidate[:1325])['first_user_language'],
         'decisions':dict(decisions),'new_category_counts':dict(Counter(s['category'] for s in samples)),
         'old_answers_changed':0,'old_questions_changed':0,'removed_rows':0,'added_rows':32,
         'supervised_tokens_status':'PENDING_NATIVE_CPU_CHECK'})
    save('protected-inputs.json',protected)
    save('manifest.json',{'version':D.name,'parent_version':P.name,'parent_sha256':PARENT_SHA,
         'dataset_sha256':digest,'system_sha256':sha(D/'system.txt'),'rows':1357,
         'files_sha256':{'train.jsonl':digest,'system.txt':sha(D/'system.txt')},
         'training_authorized':False,'training_started':False,'inference_executed':False,
         'status':'REVIEW_CANDIDATE_PENDING_CPU','sync_status':'LOCAL_GIT_ONLY',
         'human_review':'PENDING','synthetic_examples':32})
    assert all(sha(ROOT/p)==h for p,h in protected.items())
    print(json.dumps({'rows':1357,'decisions':dict(decisions),'new':32,'sha256':digest},ensure_ascii=False))

if __name__=='__main__':main()
