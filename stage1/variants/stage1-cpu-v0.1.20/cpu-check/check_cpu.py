"""Native CPU loader, templates and loss masks. No weights, Trainer or inference."""
from collections import Counter
from copy import deepcopy
import hashlib
import importlib
import importlib.metadata as md
import json
from pathlib import Path
import re

import torch
from transformers import HfArgumentParser
from swift.arguments import SftArguments
from swift.model import get_processor
from swift.template import get_template
from swift.template.base import Template
from swift.pipelines.train.sft import SwiftSft

OUT = Path(__file__).resolve().parent
D = OUT.parent
ROOT = D.parents[2]
P = D.parent / 'stage1-cpu-v0.1.14'
read = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
lines = lambda p: [json.loads(x) for x in p.read_text().splitlines()]
spec, prior = read(D/'training-config.json'), read(P/'training-config.json')
ref = read(P/'cpu-check/report.json')
assert not torch.cuda.is_available() and not list(Path('/dev').glob('nvidia*'))
assert not spec['execution_authorized'] and spec['new_lora'] and not spec['resume']
assert [x.replace(D.name,P.name) for x in spec['full_argv']] == prior['full_argv']
assert sha(D/'train.jsonl') == spec['dataset_sha256']
assert sha(P/'train.jsonl') == spec['parent_dataset_sha256']
versions = {k:md.version(k) for k in ref['versions']}
assert versions == ref['versions'], versions
for name,h in ref['tokenizer_config_sha256'].items():
    assert sha(Path('/base')/name) == h, name
for name in ['identity_loss3.py','identity-keys.json']:
    assert sha(D/name) == sha(P/name), name
sources = {}
for name,h in ref['normalization_source_hashes'].items():
    sources[name] = sha(Path(importlib.import_module(name).__file__))
    assert sources[name] == h, name

argv = [x.replace('/work/',str(ROOT)+'/') for x in spec['full_argv'][2:]]
overrides = ['--use_cpu','true','--report_to','none','--add_version','false',
             '--output_dir',str(OUT/'args-only'),'--dataset_num_proc','1']
args, = HfArgumentParser(SftArguments).parse_args_into_dataclasses(argv+overrides)
assert str(args.training_args.device) == 'cpu'
assert args.loss_scale == 'default+t008_identity3_ignore_empty_think'
assert args.system is None and args.max_length == 2048 and args.truncation_strategy == 'delete'
assert args.preserve_thinking is False and not args.disable_ignore_empty_think
assert getattr(SwiftSft._encode_dataset,'_t008_local_guard',False)
from identity_loss3 import message_key
rows, parents = lines(D/'train.jsonl'), lines(P/'train.jsonl')
mapping = lines(D/'train-map.jsonl')
changes = lines(D/'changes.jsonl')
changed = {x['parent_line_one_based']:x for x in changes}
expected = Counter(message_key(r['messages']) for r in rows)
loaded, val = args.load_dataset()
assert len(loaded) == len(rows) == spec['dataset_rows'] and len(parents) == 1325
assert Counter(message_key(r['messages']) for r in loaded) == expected
assert val is None or len(val) == 0
processor = get_processor('/base',model_type='qwen3',download_model=False)
template, unbounded = [get_template(processor,**args.get_template_kwargs()) for _ in range(2)]
for t in [template,unbounded]: t.set_mode('train')
unbounded.max_length = None
precheck = []
length_cache = {}
for i, row in enumerate(rows):
    row_key = message_key(row['messages'])
    if row_key not in length_cache:
        length_cache[row_key] = len(unbounded.encode(deepcopy(row))['input_ids'])
    precheck.append({'line_one_based': i+1, 'parent_line_one_based': mapping[i]['parent_line_one_based'],
                     'sample_id': mapping[i].get('sample_audit_id'), 'tokens': length_cache[row_key]})
overlength = [x for x in precheck if x['tokens'] > 2048]
(OUT/'length-precheck.json').write_text(json.dumps({'dataset_sha256': sha(D/'train.jsonl'),
    'rows': len(rows), 'overlength': overlength, 'maximum': max(x['tokens'] for x in precheck)}, ensure_ascii=False, indent=2)+'\n')
if overlength:
    raise RuntimeError('No truncation permitted; revise only the identified records: '+json.dumps(overlength, ensure_ascii=False))

class PreparationOnly:
    def _save_val_dataset(self,v): assert v is None or len(v)==0
stub = PreparationOnly()
stub.args, stub.template = args, template
encoded, validation = SwiftSft._encode_dataset(stub,loaded,val)
assert len(encoded)==len(rows) and Counter(message_key(r['messages']) for r in encoded)==expected

original_eos = Template._add_dynamic_eos
eos = {}
def track_eos(ids,labels,scales,suffix):
    before = list(labels)
    result = original_eos(ids,labels,scales,suffix)
    eos['positions'] = [i for i,(a,b) in enumerate(zip(before,labels)) if a==-100 and b!=-100]
    assert all(scales[i]==1 for i in eos['positions'])
    return result
Template._add_dynamic_eos = staticmethod(track_eos)

identity = {'swift/self-cognition','t008/chinese-identity-v1','t008/company-facts-v1'}
im_start = processor.encode('<|im_start|>',add_special_tokens=False)[0]
im_end = processor.encode('<|im_end|>',add_special_tokens=False)[0]
think_open = processor.encode('<think>',add_special_tokens=False)
think_close = processor.encode('</think>',add_special_tokens=False)
assert len(think_open)==len(think_close)==1
think_open,think_close=think_open[0],think_close[0]
cache = {}
def encode(row):
    key = message_key(row['messages'])
    if key not in cache:
        value = template.encode(deepcopy(row))
        dynamic = list(eos['positions'])
        unconstrained = unbounded.encode(deepcopy(row))
        assert all(value[k]==unconstrained[k] for k in ['input_ids','labels','loss_scale'])
        assert len(value['input_ids'])<=2048 and any(y!=-100 for y in value['labels'])
        assert all(y==-100 or x==y for x,y in zip(value['input_ids'],value['labels']))
        assert all(w==0 if y==-100 else w>0 for y,w in zip(value['labels'],value['loss_scale']))
        for i,x in enumerate(value['input_ids']):
            if x != im_start: continue
            end = value['input_ids'].index(im_end,i+1)
            role = processor.decode(value['input_ids'][i+1:min(i+8,end)])
            if role.startswith(('system\n','user\n')):
                assert all(y==-100 for y in value['labels'][i:end+1])
        cache[key] = (value,dynamic)
    return cache[key]

audit,probes,changed_checks=[],[],[]
totals={'before':Counter(),'after':Counter()}
source_tokens={'before':Counter(),'after':Counter()}
by_mode={'before':Counter(),'after':Counter()}
segment_tokens={k:{part:Counter() for part in ['thinking_content','answer_content','structure']} for k in ['before','after']}
sys_weights={'before':0,'after':0}
identity_weights={'before':0,'after':0}
assert not any(m['role']=='system' for r in rows+parents for m in r['messages'])
def accumulate(label,row,value):
    sup=[(y,w) for y,w in zip(value['labels'],value['loss_scale']) if y!=-100]
    weight=sum(w for _,w in sup)
    totals[label].update(input_tokens=len(value['input_ids']),supervised_tokens=len(sup),weighted_token_units=weight)
    source_tokens[label][row['dataset']]+=weight
    inside=False
    for tok,y,w in zip(value['input_ids'],value['labels'],value['loss_scale']):
        if tok==think_open:
            part='structure';inside=True
        elif tok==think_close:
            part='structure';inside=False
        elif tok in (im_start,im_end):
            part='structure';inside=False
        else:
            part='thinking_content' if inside else 'answer_content'
        if y!=-100:
            segment_tokens[label][part].update(supervised_tokens=1,weighted_token_units=w)
    thinking=any(m['role']=='assistant' and re.search(r'<think>\s*\S[\s\S]*?</think>',m['content']) for m in row['messages'])
    by_mode[label]['thinking_rows' if thinking else 'nonthinking_rows']+=1
    by_mode[label]['thinking_weighted_units' if thinking else 'nonthinking_weighted_units']+=weight
    if row['dataset'] in identity:identity_weights[label]+=weight
    if any(m['role']=='system' for m in row['messages']):
        raise AssertionError('Training System is outside v14 data format')
    return sup

for row in parents:
    value,_=encode(row);accumulate('before',row,value)
unchanged=identity_count=0
examples={}
for line,(row,m) in enumerate(zip(rows,mapping),1):
    parent_line=m['parent_line_one_based'];before=parents[parent_line-1]
    prev,_=encode(before);cur,dynamic=encode(row)
    sup=accumulate('after',row,cur)
    factor=3.0 if row['dataset'] in identity else 1.0
    want=[factor if y!=-100 else 0.0 for y in cur['labels']]
    for i in dynamic:want[i]=1.0
    assert cur['loss_scale']==want,('weight mismatch',line)
    if m['operation']=='preserve':
        assert row==before and all(cur[k]==prev[k] for k in ['input_ids','labels','loss_scale'])
        unchanged+=1
    else:
        assert m['operation']=='repair' and changed[parent_line]['after']==row
        assert row['messages'][0]==before['messages'][0] and row['dataset']=='swift/Qwen3-SFT-Mixin'
        changed_checks.append({'sample_id':m['sample_audit_id'],'parent_line_one_based':parent_line,'candidate_line_one_based':line,
            'before_input_tokens':len(prev['input_ids']),'after_input_tokens':len(cur['input_ids']),
            'before_supervised_tokens':sum(y!=-100 for y in prev['labels']),'after_supervised_tokens':len(sup),
            'same_question':True,'full_encoding_no_truncation':True,'weights_unchanged':True})
        probes.append({'sample_id':m['sample_audit_id'],'line_one_based':line,'input_ids':cur['input_ids'],
            'labels':cur['labels'],'loss_scale':cur['loss_scale'],'supervised_text':processor.decode([y for y,w in sup])})
    if row['dataset'] in identity:
        assert row==before and all(cur[k]==prev[k] for k in ['input_ids','labels','loss_scale'])
        identity_count+=1
    if all(not m['content'].split('</think>',1)[0].replace('<think>','').strip() for m in row['messages'] if m['role']=='assistant'):
        supervised=processor.decode([y for y,w in sup]);assert '<think>' not in supervised and '</think>' not in supervised
    examples.setdefault(row['dataset'],cur)
    audit.append({'line_one_based':line,'parent_line_one_based':parent_line,'source':row['dataset'],'operation':m['operation'],
        'encoded_tokens':len(cur['input_ids']),'supervised_tokens':len(sup),'weighted_token_units':sum(w for _,w in sup),'weight_verified':True})
Template._add_dynamic_eos=staticmethod(original_eos)
assert unchanged+len(changed_checks)==len(rows) and identity_count==234
assert totals['before']['supervised_tokens']==ref['total_supervised_tokens']
assert totals['before']['weighted_token_units']==ref['total_weighted_token_units']
assert sys_weights['before']==sys_weights['after'] and identity_weights['before']==identity_weights['after']
for label in totals:
    for measure in ['supervised_tokens','weighted_token_units']:
        assert sum(x[measure] for x in segment_tokens[label].values())==totals[label][measure]
batch=template.data_collator(list(examples.values()))
assert set(batch['loss_scale'].unique().tolist())=={0.,1.,3.}
assert torch.equal(batch['labels']!=-100,batch['loss_scale']>0)
lengths=sorted(x['encoded_tokens'] for x in audit)
report={'verified':True,'dataset_sha256':sha(D/'train.jsonl'),'parent_dataset_sha256':sha(P/'train.jsonl'),
    'rows':len(rows),'actual_loader_rows':len(loaded),'actual_pipeline_rows':len(encoded),'parent_rows':len(parents),
    'changed_rows':len(changed_checks),'quarantined_rows':len(parents)-len(rows),'unchanged_full_encoding_rows':unchanged,'identity_exposures':identity_count,
    'max_tokens':max(lengths),'p99_tokens':lengths[__import__('math').ceil(.99*len(lengths))-1],
    'overlength_rows':0,'truncated_rows':0,'silent_dropped_rows':0,'empty_supervision_rows':0,
    'totals':{k:dict(v) for k,v in totals.items()},'source_weighted_token_units':{k:dict(v) for k,v in source_tokens.items()},
    'by_mode':{k:dict(v) for k,v in by_mode.items()},'system_subset_weighted_token_units':sys_weights,
    'segment_tokens':{k:{part:dict(n) for part,n in v.items()} for k,v in segment_tokens.items()},
    'segment_definition':'Supervised tokens between think tags are thinking_content; outside tags are answer_content; think/chat delimiter tokens are structure. Whitespace is retained.',
    'identity_weighted_token_units':identity_weights,
    'all_identity_encodings_and_weights_unchanged':True,'prompt_and_empty_think_masked':True,
    'collator_preserves_0_1_3_weights':True,'normalization':ref['normalization'],
    'normalization_source_hashes':sources,'tokenizer_config_sha256':ref['tokenizer_config_sha256'],
    'versions':versions,'template_kwargs':args.get_template_kwargs(),'cpu_overrides':overrides,
    'training_hyperparameters_unchanged':True,'estimated_full_optimizer_steps':__import__('math').ceil(len(rows)/16),
    'model_weights_loaded':False,'trainer_created':False,'optimizer_created':False,'training_started':False,
    'inference_executed':False,'gpu_available':False,'backward_called':False}
for name,obj in [('report.json',report),('changed-row-checks.json',changed_checks),('mask-probes.json',probes)]:
    (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
(OUT/'row-checks.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in audit))
print(json.dumps({'verified':True,'rows':len(rows),'changed':len(changed_checks),'max_tokens':max(lengths),'totals':report['totals']},ensure_ascii=False),flush=True)
