"""Compare native CPU encodings for the sole 3->1 multiplier change; no weights."""
from collections import Counter
from copy import deepcopy
import hashlib, importlib.util, json, sys
from pathlib import Path

RUN = sys.argv[1]
D = Path('/data') / RUN
P = Path('/data/t008-v0122-20261101-031736')
sys.path[:0] = [str(D/'deps'), str(D/'code')]
def read(p): return json.loads(p.read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x): p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')

import torch
from transformers import HfArgumentParser
from swift.arguments import SftArguments
from swift.model import get_processor
from swift.template import get_template
from swift.pipelines.train.sft import SwiftSft

assert not torch.cuda.is_available()
spec=read(D/'stage1/training/run-spec.json');ref=read(D/'stage1/evidence/encoding-report.json')
assert spec['dataset_rows']==1047 and sha(D/'stage1/data/train.jsonl')==ref['dataset_sha256']
newp=D/'stage1/variants/stage1-cpu-v0.1.22/identity_loss3.py'
oldp=P/'stage1/variants/stage1-cpu-v0.1.22/identity_loss3.py'
assert oldp.read_text().replace('3.0 * w','1.0 * w')==newp.read_text()
assert sha(newp.with_name('identity-keys.json'))==sha(oldp.with_name('identity-keys.json'))
argv=[x.replace('/work/',str(D)+'/') for x in spec['full_argv'][2:]]
argv[argv.index('--dataset')+1]=str(D/'stage1/data/train.jsonl')
args,=HfArgumentParser(SftArguments).parse_args_into_dataclasses(argv+[
    '--use_cpu','true','--report_to','none','--add_version','false',
    '--output_dir','/tmp/loss1-args','--dataset_num_proc','1'])
assert args.loss_scale=='default+t008_identity3_ignore_empty_think'
assert args.system is None and not args.preserve_thinking and not args.disable_ignore_empty_think
processor=get_processor('/base',model_type='qwen3',download_model=False)
new=get_template(processor,**args.get_template_kwargs());new.set_mode('train')
# Materialize the lazily constructed candidate strategy before changing the
# registry for the independent frozen-original comparison instance.
assert not new.loss_scale.is_binary_loss_scale
module_spec=importlib.util.spec_from_file_location('original_loss3',oldp)
original=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(original)
old=get_template(processor,**args.get_template_kwargs());old.set_mode('train')
assert type(new.loss_scale) is not type(old.loss_scale)
assert not new.loss_scale.is_binary_loss_scale and not old.loss_scale.is_binary_loss_scale
rows=[json.loads(x) for x in (D/'stage1/data/train.jsonl').read_text().splitlines()]
identity={'swift/self-cognition','t008/chinese-identity-v1','t008/company-facts-v1'}
key=original.message_key
loaded,val=args.load_dataset();assert len(loaded)==len(rows)==1047
assert Counter(key(x['messages']) for x in loaded)==Counter(key(x['messages']) for x in rows)
assert val is None or len(val)==0
totals=Counter();audit=[];cache={};examples={};identity_tokens=Counter()
for n,row in enumerate(rows,1):
    k=key(row['messages'])
    if k not in cache:
        a=old.encode(deepcopy(row));b=new.encode(deepcopy(row))
        assert a['input_ids']==b['input_ids'] and a['labels']==b['labels']
        assert len(b['input_ids'])<=2048 and any(y!=-100 for y in b['labels'])
        assert b['loss_scale']==[0.0 if y==-100 else 1.0 for y in b['labels']]
        assert all(y==x or (x==3.0 and y==1.0) for x,y in zip(a['loss_scale'],b['loss_scale']))
        cache[k]=(a,b)
    a,b=cache[k];count3=sum(x==3 for x in a['loss_scale'])
    is_identity=row['dataset'] in identity
    assert (count3>0)==is_identity
    if not is_identity:assert a['loss_scale']==b['loss_scale']
    sup=sum(y!=-100 for y in b['labels'])
    totals.update(rows=1,input_tokens=len(b['input_ids']),supervised_tokens=sup,
                  weighted_before=sum(a['loss_scale']),weighted_after=sum(b['loss_scale']),
                  changed_tokens=count3,identity_rows=int(is_identity))
    if is_identity:identity_tokens.update(supervised_tokens=sup,weighted_before=sum(a['loss_scale']),weighted_after=sum(b['loss_scale']))
    audit.append({'line_one_based':n,'source':row['dataset'],'input_tokens':len(b['input_ids']),
                  'same_input_ids':True,'same_labels':True,'changed_scale_tokens':count3,
                  'encoding_sha256':hashlib.sha256(json.dumps(b,sort_keys=True).encode()).hexdigest()})
    examples.setdefault(row['dataset'],b)
assert totals['identity_rows']==234
assert totals['input_tokens']==ref['totals']['after']['input_tokens']
assert totals['supervised_tokens']==ref['totals']['after']['supervised_tokens']
assert totals['weighted_before']==ref['totals']['after']['weighted_token_units']
assert totals['weighted_after']==totals['supervised_tokens']
class PreparationOnly:
    def _save_val_dataset(self,value): assert value is None or len(value)==0
stub=PreparationOnly();stub.args=args;stub.template=new
encoded,validation=SwiftSft._encode_dataset(stub,loaded,val)
assert len(encoded)==1047 and Counter(key(x['messages']) for x in encoded)==Counter(key(x['messages']) for x in rows)
batch=new.data_collator(list(examples.values()))
assert set(batch['loss_scale'].unique().tolist())=={0.0,1.0}
assert torch.equal(batch['labels']!=-100,batch['loss_scale']>0)
out=D/'loss1-cpu';out.mkdir(exist_ok=True)
(out/'row-checks.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in audit))
report={k:ref[k] for k in ['dataset_sha256','data_version','versions','tokenizer_config_sha256','normalization','normalization_source_hashes']}
report.update(verified=True,rows=1047,actual_loader_rows=1047,actual_pipeline_rows=1047,
    identity_exposures=234,max_tokens=max(x['input_tokens'] for x in audit),overlength_rows=0,
    truncated_rows=0,silent_dropped_rows=0,empty_supervision_rows=0,
    all_input_ids_labels_identical=True,identity_multiplier_before=3,identity_multiplier_after=1,
    non_identity_weights_unchanged=True,nonbinary_loss_path_preserved=True,
    prompt_and_empty_think_masked=True,all_visible_answers_supervised=True,
    totals=dict(totals),identity_token_units=dict(identity_tokens),
    loss_plugin_sha256=sha(newp),parent_loss_plugin_sha256=sha(oldp),
    identity_key_binding_sha256=sha(newp.with_name('identity-keys.json')),
    native_encoding_reused=False,model_weights_loaded=False,trainer_created=False,
    optimizer_created=False,training_started=False,inference_executed=False,gpu_available=False)
save(out/'report.json',report)
print(json.dumps({'verified':True,'rows':1047,'identity_exposures':234,'totals':dict(totals),'max_tokens':report['max_tokens']}),flush=True)
