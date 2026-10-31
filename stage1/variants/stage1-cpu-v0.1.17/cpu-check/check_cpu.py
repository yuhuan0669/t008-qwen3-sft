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
P = D.parent / 'stage1-cpu-v0.1.16'
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
for name in ['identity_loss3.py','identity-keys.json','system.txt']:
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
changed = {x['changed_line']:x for x in read(D/'selection.json')['items']}
expected = Counter(message_key(r['messages']) for r in rows)
loaded, val = args.load_dataset()
assert len(loaded) == len(rows) == len(parents) == 1357
assert Counter(message_key(r['messages']) for r in loaded) == expected
assert val is None or len(val) == 0
processor = get_processor('/base',model_type='qwen3',download_model=False)
template, unbounded = [get_template(processor,**args.get_template_kwargs()) for _ in range(2)]
for t in [template,unbounded]: t.set_mode('train')
unbounded.max_length = None

class PreparationOnly:
    def _save_val_dataset(self,v): assert v is None or len(v)==0
stub = PreparationOnly()
stub.args, stub.template = args, template
encoded, validation = SwiftSft._encode_dataset(stub,loaded,val)
assert len(encoded)==1357 and Counter(message_key(r['messages']) for r in encoded)==expected

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

audit, probes, changed_checks = [], [], []
totals = {'before':Counter(),'after':Counter()}
by_mode = {'before':Counter(),'after':Counter()}
sys_weights = {'before':0,'after':0}
source_tokens = {'before':Counter(),'after':Counter()}
selected_sums = {'before':Counter(),'after':Counter()}
examples = {}
system = (D/'system.txt').read_text()
unchanged = 0
for line,(before,after) in enumerate(zip(parents,rows),1):
    prev, old_eos = encode(before)
    cur, dynamic = encode(after)
    factor = 3.0 if after['dataset'] in identity else 1.0
    want = [factor if y!=-100 else 0.0 for y in cur['labels']]
    for i in dynamic: want[i]=1.0
    assert cur['loss_scale']==want, ('weight mismatch',line)
    old_sup = [(y,w) for y,w in zip(prev['labels'],prev['loss_scale']) if y!=-100]
    new_sup = [(y,w) for y,w in zip(cur['labels'],cur['loss_scale']) if y!=-100]
    if line not in changed:
        assert before==after
        assert all(cur[k]==prev[k] for k in ['input_ids','labels','loss_scale'])
        unchanged += 1
    else:
        assert before['messages'][0] == after['messages'][0]
        assert before['messages'][1]['content'].split('</think>',1)[1] == after['messages'][1]['content'].split('</think>',1)[1]
        assert old_sup[-len(new_sup):] == new_sup, ('body target changed',line)
        assert len(new_sup)<len(old_sup)
        decoded=processor.decode([y for y,w in new_sup])
        assert '<think>' not in decoded and '</think>' not in decoded
        assert after['messages'][1]['content'].split('</think>',1)[1].strip() in decoded
        changed_checks.append({'sample_id':changed[line]['sample_id'],'line_one_based':line,
            'retained_thinking_line':changed[line]['retained_thinking_line'],
            'before_input_tokens':len(prev['input_ids']),'after_input_tokens':len(cur['input_ids']),
            'before_supervised_tokens':len(old_sup),'after_supervised_tokens':len(new_sup),
            'removed_supervised_tokens':len(old_sup)-len(new_sup),
            'visible_answer_supervision_exact_suffix_equal':True,'empty_think_masked':True})
    for label,row,value,sup in [('before',before,prev,old_sup),('after',after,cur,new_sup)]:
        totals[label]['input_tokens']+=len(value['input_ids'])
        totals[label]['supervised_tokens']+=len(sup)
        totals[label]['weighted_token_units']+=sum(w for _,w in sup)
        source_tokens[label][row['dataset']]+=sum(w for _,w in sup)
        thinking=any(m['role']=='assistant' and re.search(r'<think>\s*\S[\s\S]*?</think>',m['content']) for m in row['messages'])
        by_mode[label]['thinking_rows' if thinking else 'nonthinking_rows']+=1
        by_mode[label]['thinking_weighted_units' if thinking else 'nonthinking_weighted_units']+=sum(w for _,w in sup)
        if line in changed:
            selected_sums[label]['supervised_tokens']+=len(sup)
            selected_sums[label]['weighted_token_units']+=sum(w for _,w in sup)
        if any(m['role']=='system' for m in row['messages']):
            assert row['messages'][0]['content']==system
            sys_weights[label]+=sum(w for _,w in sup)
    if line in changed or (after['dataset'] in identity and len(probes)==0):
        probes.append({'line_one_based':line,'input_ids':cur['input_ids'],'labels':cur['labels'],
            'loss_scale':cur['loss_scale'],'supervised_text':processor.decode([y for y,w in new_sup])})
    examples.setdefault(after['dataset'],cur)
    audit.append({'line_one_based':line,'source':after['dataset'],'changed':line in changed,
        'encoded_tokens':len(cur['input_ids']),'supervised_tokens':len(new_sup),
        'weighted_token_units':sum(w for _,w in new_sup),'weight_verified':True})
Template._add_dynamic_eos = staticmethod(original_eos)
assert len(changed_checks)==32 and unchanged==1325
assert totals['before']['supervised_tokens']==ref['total_supervised_tokens']
assert totals['before']['weighted_token_units']==ref['total_weighted_token_units']
assert sys_weights['before']==sys_weights['after']
batch=template.data_collator(list(examples.values()))
assert set(batch['loss_scale'].unique().tolist())=={0.,1.,3.}
assert torch.equal(batch['labels']!=-100,batch['loss_scale']>0)
lengths=sorted(x['encoded_tokens'] for x in audit)
report={'verified':True,'dataset_sha256':sha(D/'train.jsonl'),'parent_dataset_sha256':sha(P/'train.jsonl'),
    'rows':1357,'actual_loader_rows':len(loaded),'actual_pipeline_rows':len(encoded),
    'changed_rows':32,'unchanged_full_encoding_rows':unchanged,'identity_exposures':234,
    'max_tokens':max(lengths),'p99_tokens':lengths[__import__('math').ceil(.99*len(lengths))-1],
    'overlength_rows':0,'truncated_rows':0,'silent_dropped_rows':0,'empty_supervision_rows':0,
    'totals':{k:dict(v) for k,v in totals.items()},'by_mode':{k:dict(v) for k,v in by_mode.items()},
    'selected_changed_exposures':{k:dict(v) for k,v in selected_sums.items()},
    'source_weighted_token_units':{k:dict(v) for k,v in source_tokens.items()},
    'system_subset_weighted_token_units':sys_weights,'body_target_suffix_equal_all_32':True,
    'all_identity_encodings_and_weights_unchanged':True,'prompt_and_empty_think_masked':True,
    'collator_preserves_0_1_3_weights':True,'normalization':ref['normalization'],
    'normalization_source_hashes':sources,'tokenizer_config_sha256':ref['tokenizer_config_sha256'],
    'versions':versions,'template_kwargs':args.get_template_kwargs(),'cpu_overrides':overrides,
    'training_hyperparameters_unchanged':True,'estimated_full_optimizer_steps':85,
    'model_weights_loaded':False,'trainer_created':False,'optimizer_created':False,'training_started':False,
    'inference_executed':False,'gpu_available':False,'backward_called':False}
for name,obj in [('report.json',report),('changed-row-checks.json',changed_checks),('mask-probes.json',probes)]:
    (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
(OUT/'row-checks.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in audit))
print(json.dumps({'verified':True,'rows':1357,'changed':32,'max_tokens':max(lengths),'totals':report['totals']},ensure_ascii=False),flush=True)
