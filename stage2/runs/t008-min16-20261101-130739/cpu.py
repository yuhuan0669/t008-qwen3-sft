from pathlib import Path
import sys,json,copy,torch,importlib.metadata as md
D=Path('/data')/sys.argv[1];sys.path[:0]=[str(D/'code'),str(D/'deps'),str(D/'identity')]
import identity_loss3
from swift.model import get_processor
from swift.template import get_template
processor=get_processor('/base',model_type='qwen3',download_model=False)
rows=[json.loads(x) for x in (D/'train.jsonl').read_text().splitlines()]
templates=[]
for loss in ['default+t008_identity3_ignore_empty_think','default+ignore_empty_think']:
 t=get_template(processor,template_type='qwen3',max_length=2048,truncation_strategy='raise',loss_scale=loss,preserve_thinking=False);t.set_mode('train');templates.append(t)
reports=[];encoded=[]
for i,row in enumerate(rows):
 a,b=[t.encode(copy.deepcopy(row)) for t in templates];ba,bb=[t.data_collator([e]) for t,e in zip(templates,[a,b])]
 assert a['input_ids']==b['input_ids'] and a['labels']==b['labels']
 # Binary strategy represents zero weights through ignored labels; compare effective weights.
 def weights(batch):return (batch['labels']!=-100).float()*batch.get('loss_scale',torch.ones_like(batch['labels']))
 wa,wb=weights(ba),weights(bb);assert torch.equal(wa,wb)
 assert not (wa>1).any() and wa.sum()>0
 assert len(a['input_ids'])<=2048 and identity_loss3.message_key(row['messages']) not in json.loads((D/'identity/identity-keys.json').read_text())['identity_message_sha256']
 active=[j for j,v in enumerate(wa[0].tolist()) if v];text=processor.decode([a['input_ids'][j] for j in active])
 assert row['messages'][1]['content'].split('</think>')[-1].strip() in text
 assert active[0]>len(processor.encode(row['messages'][0]['content'],add_special_tokens=False))
 reports.append({'line':i+1,'input_ids':a['input_ids'],'decoded_tokens':[processor.decode([x]) for x in a['input_ids']],'labels':a['labels'],'loss_scale':ba.get('loss_scale').tolist(),'effective_mask':wa.tolist(),'supervised_text':text,'valid_tokens':int((ba['labels']!=-100).sum()),'effective_tokens':int(wa.sum())})
 encoded.append(a)
(D/'encoded.json').write_text(json.dumps(encoded));(D/'cpu-rows.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2));(D/'cpu-report.json').write_text(json.dumps({'pass':True,'rows':len(rows),'max_tokens':max(len(a['input_ids']) for a in encoded),'optimizer_steps':0,'effective_masks_equal':True,'versions':{n:md.version(n) for n in ['ms-swift','torch','transformers','peft']}}));print((D/'cpu-report.json').read_text())
