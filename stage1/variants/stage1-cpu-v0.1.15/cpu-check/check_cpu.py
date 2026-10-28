"""CPU-only native Swift loading/encoding/masks. No Trainer, weights or inference."""
from collections import Counter
from copy import deepcopy
from pathlib import Path
import hashlib
import importlib
import importlib.metadata as md
import json
import math
import re

import torch
from transformers import HfArgumentParser
from swift.arguments import SftArguments
from swift.model import get_processor
from swift.template import get_template
from swift.template.base import Template
from swift.pipelines.train.sft import SwiftSft

OUT=Path(__file__).resolve().parent
D=OUT.parent; ROOT=D.parents[2]; P=D.parent/'stage1-cpu-v0.1.14'
LOSS3=ROOT/'stage2/variants/identity-loss3-review'
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
spec=read(D/'training-config.json'); prior=read(P/'training-config.json')
ref=read(P/'cpu-check/report.json')
assert not torch.cuda.is_available() and not list(Path('/dev').glob('nvidia*'))
assert not spec['execution_authorized'] and spec['new_lora'] and not spec['resume']
assert sha(D/'train.jsonl')==spec['dataset_sha256']
assert [x.replace(D.name,P.name) for x in spec['full_argv']]==prior['full_argv']
versions={k:md.version(k) for k in ref['versions']}; assert versions==ref['versions']
for name,h in ref['tokenizer_config_sha256'].items():assert sha(Path('/base')/name)==h,name
assert sha(D/'identity_loss3.py')==sha(P/'identity_loss3.py')
sources={}
for name,h in ref['normalization_source_hashes'].items():
    path=Path(importlib.import_module(name).__file__)
    assert sha(path)==h,name
    sources[name]=sha(path)

argv=[x.replace('/work/',str(ROOT)+'/') for x in spec['full_argv'][2:]]
overrides=['--use_cpu','true','--report_to','none','--add_version','false',
           '--output_dir',str(OUT/'args-only'),'--dataset_num_proc','1']
args,=HfArgumentParser(SftArguments).parse_args_into_dataclasses(argv+overrides)
assert str(args.training_args.device)=='cpu'
assert args.loss_scale=='default+t008_identity3_ignore_empty_think'
assert args.preserve_thinking is False and not args.disable_ignore_empty_think
assert args.system is None and args.max_length==2048 and args.truncation_strategy=='delete'
assert args.dataset_shuffle and args.num_train_epochs==1 and args.gradient_accumulation_steps==16
assert args.per_device_train_batch_size==1 and args.learning_rate==1e-4
assert args.lora_rank==8 and args.lora_alpha==32 and args.lora_dropout==.05
assert getattr(SwiftSft._encode_dataset,'_t008_local_guard',False)
from identity_loss3 import message_key
rows=[json.loads(x) for x in (D/'train.jsonl').read_text().splitlines()]
parents=[json.loads(x) for x in (P/'train.jsonl').read_text().splitlines()]
mapping=[json.loads(x) for x in (D/'train-map.jsonl').read_text().splitlines()]
assert len(rows)==1357 and len(parents)==1325
expected=Counter(message_key(r['messages']) for r in rows)
loaded,val=args.load_dataset(); assert Counter(message_key(r['messages']) for r in loaded)==expected
assert val is None or len(val)==0
processor=get_processor('/base',model_type='qwen3',download_model=False)
new,old,unbounded=[get_template(processor,**args.get_template_kwargs()) for _ in range(3)]
for t in [new,old,unbounded]:t.set_mode('train')
old.loss_scale.identity_keys=frozenset(read(P/'identity-keys.json')['identity_message_sha256'])
unbounded.max_length=None
assert old.loss_scale is not new.loss_scale and new.loss_scale.is_binary_loss_scale is False

class PreparationOnly:
    def _save_val_dataset(self,v):assert v is None or len(v)==0
stub=PreparationOnly();stub.args,stub.template=args,new
encoded,val=SwiftSft._encode_dataset(stub,loaded,val)
assert len(encoded)==1357 and Counter(message_key(r['messages']) for r in encoded)==expected

loss_class=type(new.loss_scale); original_call=loss_class.__call__
original_eos=Template._add_dynamic_eos; traces={}; eos={}
def observed(self,contexts,types,messages,**kwargs):
    traces[id(self)]=deepcopy(messages)
    return original_call(self,contexts,types,messages,**kwargs)
def observed_eos(ids,labels,scales,suffix):
    before=list(labels);result=original_eos(ids,labels,scales,suffix)
    eos['positions']=[i for i,(a,b) in enumerate(zip(before,labels)) if a==-100 and b!=-100]
    assert all(scales[i]==1 for i in eos['positions'])
    return result
loss_class.__call__=observed
Template._add_dynamic_eos=staticmethod(observed_eos)
identity={'swift/self-cognition','t008/chinese-identity-v1','t008/company-facts-v1'}
sys=(D/'system.txt').read_text()
cache={};old_cache={};audit=[];probes=[];mismatches=[];aliases=[]
tokens=Counter();weighted=Counter();new_tokens=0;old_tokens=0;old_weighted=0
counts=Counter();examples={};unchanged=0;same_supervision=0;system_rows=0
im_start=processor.encode('<|im_start|>',add_special_tokens=False)[0]
im_end=processor.encode('<|im_end|>',add_special_tokens=False)[0]

def validate_prompt_masks(value):
    ids,labels=value['input_ids'],value['labels']
    starts=[i for i,x in enumerate(ids) if x==im_start]
    for i in starts:
        stop=ids.index(im_end,i+1) if im_end in ids[i+1:] else len(ids)
        first=processor.decode(ids[i+1:min(i+8,stop)])
        if first.startswith(('system\n','user\n')):
            assert all(x==-100 for x in labels[i:stop+1]),(i,'prompt supervision')

for i,row in enumerate(rows):
    k=message_key(row['messages'])
    if k not in cache:
        b=new.encode(deepcopy(row)); prepared=deepcopy(traces[id(new.loss_scale)])
        positions=list(eos['positions']); ub=unbounded.encode(deepcopy(row))
        assert all(b[x]==ub[x] for x in ['input_ids','labels','loss_scale']),(i,'truncation')
        assert len(b['input_ids'])<=2048 and any(y!=-100 for y in b['labels'])
        assert all(y==-100 or x==y for x,y in zip(b['input_ids'],b['labels']))
        assert all(w==0 if y==-100 else w>0 for y,w in zip(b['labels'],b['loss_scale']))
        validate_prompt_masks(b)
        cache[k]=(b,prepared,positions)
    b,prepared,positions=cache[k]
    is_identity=row['dataset'] in identity;factor=3.0 if is_identity else 1.0
    want=[factor if y!=-100 else 0.0 for y in b['labels']]
    for p in positions:want[p]=1.0
    if b['loss_scale']!=want:mismatches.append({'line':i+1,'raw_key':k,'native_key':message_key(prepared)})
    sup=[(y,w) for y,w in zip(b['labels'],b['loss_scale']) if y!=-100]
    if i<1325:
        pk=message_key(parents[i]['messages'])
        if pk not in old_cache:old_cache[pk]=old.encode(deepcopy(parents[i]))
        previous=old_cache[pk]
        previous_sup=[(y,w) for y,w in zip(previous['labels'],previous['loss_scale']) if y!=-100]
        assert sup==previous_sup,(i,'old answer tokens or weights changed')
        same_supervision+=1;old_tokens+=len(previous_sup);old_weighted+=sum(w for y,w in previous_sup)
        if mapping[i]['operation']!='add_system':
            assert all(b[x]==previous[x] for x in ['input_ids','labels','loss_scale']),i
            unchanged+=1
    else:new_tokens+=len(sup)
    if row['messages'][0]['role']=='system':
        assert row['messages'][0]['content']==sys
        prefix=processor.encode('<|im_start|>system\n'+sys+'<|im_end|>\n',add_special_tokens=False)
        assert b['input_ids'][:len(prefix)]==prefix
        assert all(x==-100 for x in b['labels'][:len(prefix)])
        system_rows+=1
    native_key=message_key(prepared)
    if is_identity:
        assert native_key in new.loss_scale.identity_keys
        if native_key!=k:aliases.append({'line_one_based':i+1,'raw_messages_sha256':k,'prepared_messages_sha256':native_key})
    decoded=processor.decode([y for y,w in sup])
    assert not re.search(r'<think>\s*</think>',decoded),(i,'empty think in labels')
    check_turns=[]
    if i>=1325 or (i<1325 and mapping[i]['operation']=='add_system'):
        for j,m in enumerate(row['messages']):
            if m['role']=='assistant':
                body=m['content'].split('</think>',1)[1].strip()
                assert body in decoded,(i,j,'body missing')
                check_turns.append({'message_index':j,'visible_body_supervised':True})
    if i>=1325 or (is_identity and len(row['messages'])>=4):
        probes.append({'line_one_based':i+1,'sample_id':mapping[i].get('sample_id'),
                       'system_mask_verified':True,'native_messages_exclude_system':not any(m['role']=='system' for m in prepared),
                       'expected_factor':factor,'turn_checks':check_turns,'supervised_text':decoded,
                       'input_ids':b['input_ids'],'labels':b['labels'],'loss_scale':b['loss_scale']})
    tokens[row['dataset']]+=len(sup);weighted[row['dataset']]+=sum(w for y,w in sup)
    counts[row['dataset']]+=1;examples.setdefault(row['dataset'],b)
    audit.append({'line_one_based':i+1,'source':row['dataset'],'operation':mapping[i]['operation'],
                  'encoded_tokens':len(b['input_ids']),'supervised_tokens':len(sup),
                  'weighted_token_units':sum(w for y,w in sup),'expected_factor':factor,
                  'weight_verified':b['loss_scale']==want,'native_dynamic_eos_positions_weight1':positions,
                  'prepared_messages_sha256':native_key})
loss_class.__call__=original_call;Template._add_dynamic_eos=staticmethod(original_eos)
assert not mismatches and same_supervision==1325 and unchanged==1182 and system_rows==175
assert dict(counts)==read(D/'statistics.json')['after']['source_exposures']
assert sum(counts[s] for s in identity)==234
assert old_tokens==ref['total_supervised_tokens'] and old_weighted==ref['total_weighted_token_units']
batch=new.data_collator(list(examples.values()))
assert set(batch['loss_scale'].unique().tolist())=={0.,1.,3.}
assert torch.equal(batch['labels']!=-100,batch['loss_scale']>0)
ev=read(D/'evaluation-config.json')
assert sha(ROOT/ev['chat_template']['path'])==ev['chat_template']['sha256']
assert sha(ROOT/ev['system_path'])==ev['system_sha256']==sha(D/'system.txt')
assert ev['request_modes']==read(P/'evaluation-config.json')['request_modes']
system_measure={'characters':len(sys),'text_tokens':len(processor.encode(sys,add_special_tokens=False)),
                'source_characters':len((D/'system-source.txt').read_text().strip()),
                'source_text_tokens':len(processor.encode((D/'system-source.txt').read_text().strip(),add_special_tokens=False)),
                'scope':'System text only, excludes ChatML headers and current question',
                'file_sha256':sha(D/'system.txt')}
lengths=sorted(x['encoded_tokens'] for x in audit)
report={'verified':True,'data_version':D.name,'dataset_sha256':spec['dataset_sha256'],
        'rows':1357,'actual_loader_rows':len(loaded),'actual_pipeline_rows':len(encoded),
        'retained_parent_rows':1325,'added_rows':32,'system_added_to_parent_rows':143,'system_rows':system_rows,
        'unchanged_full_encoding_rows':unchanged,'unchanged_parent_supervision_and_weights_rows':same_supervision,
        'max_tokens':max(lengths),'p99_tokens':lengths[math.ceil(.99*len(lengths))-1],
        'max_new_sample_tokens':max(x['encoded_tokens'] for x in audit[1325:]),
        'overlength_rows':0,'truncated_rows':0,'silent_dropped_rows':0,'empty_supervision_rows':0,
        'source_exposures':dict(counts),'source_supervised_tokens_after':dict(tokens),
        'source_weighted_token_units_after':dict(weighted),'parent_supervised_tokens':old_tokens,
        'new_supervised_tokens':new_tokens,'total_supervised_tokens':sum(tokens.values()),
        'parent_weighted_token_units':old_weighted,'total_weighted_token_units':sum(weighted.values()),
        'weight_mismatch_rows':0,'all_234_identity_exposures_answer_weight3':True,
        'all_new_rows_weight1':all(x['expected_factor']==1 and x['weight_verified'] for x in audit[1325:]),
        'prompt_and_empty_think_masked':True,'all_new_assistant_bodies_supervised':True,
        'collator_preserves_0_1_3_weights':True,'normalization':ref['normalization'],
        'normalization_source_hashes':sources,'prior_numeric_loss_test_reused':ref['prior_numeric_loss_test_reused'],
        'native_system_behavior':'System is extracted into inputs.system; the loss plugin receives user/assistant messages without System.',
        'native_dynamic_eos_note':ref['native_dynamic_eos_note'],
        'versions':versions,'tokenizer_config_sha256':ref['tokenizer_config_sha256'],
        'template_kwargs':args.get_template_kwargs(),'cpu_overrides':overrides,
        'training_hyperparameters_unchanged':True,'estimated_full_optimizer_steps':85,
        'system_measure':system_measure,'evaluation_template_and_system_hashes_verified':True,
        'training_started':False,'inference_executed':False,'model_weights_loaded':False,
        'trainer_created':False,'optimizer_created':False,'backward_called':False,'gpu_available':False,
        'clearml_task_created':False}
for name,value in [('report.json',report),('mask-probes.json',probes),('weight-mismatches.json',mismatches),('native-alias-trace.json',aliases)]:
    (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,default=str)+'\n')
(OUT/'row-checks.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in audit))
print(json.dumps({k:report[k] for k in ['verified','rows','max_tokens','weight_mismatch_rows','new_supervised_tokens','system_measure']},ensure_ascii=False),flush=True)
