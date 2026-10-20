#!/usr/bin/env python3
"""Parse actual ms-swift SFT CLI without creating a trainer/loading weights."""
import dataclasses
import inspect
import json
import pathlib
from transformers import HfArgumentParser
from swift.arguments import SftArguments

out = pathlib.Path('/work/evidence/template/cli')
out.mkdir(parents=True, exist_ok=True)
parser = HfArgumentParser(SftArguments)
flags = ['--model','/base','--dataset','/work/original-v1.2/train.jsonl',
         '--tuner_type','lora','--split_dataset_ratio','0','--torch_dtype','bfloat16',
         '--num_train_epochs','1','--per_device_train_batch_size','1',
         '--per_device_eval_batch_size','1','--learning_rate','1e-4','--lora_rank','8',
         '--lora_alpha','32','--target_modules','all-linear',
         '--gradient_accumulation_steps','16','--max_length','2048','--warmup_ratio','0.05',
         '--eval_strategy','no','--save_total_limit','2','--logging_steps','5',
         '--dataloader_num_workers','4','--seed','42','--data_seed','42','--push_to_hub','false',
         '--output_dir','/work/probes/parser-only','--gradient_checkpointing','true',
         '--save_only_model','false','--report_to','tensorboard']
results = []
for mode, extra in [('full',['--save_strategy','epoch']),
                    ('smoke',['--max_steps','3','--save_strategy','steps','--save_steps','3'])]:
    namespace, unknown = parser.parse_known_args(flags+extra)
    assert not unknown, unknown
    vals=vars(namespace)
    for key, expected in dict(eval_strategy='no',data_seed=42,lora_rank=8,lora_alpha=32,
                              target_modules=['all-linear'],torch_dtype='bfloat16',
                              max_length=2048,tuner_type='lora',split_dataset_ratio=0).items():
        assert vals[key] == expected, (key,vals[key])
    results.append(dict(mode=mode,unknown_flags=unknown,parsed=vals))
    # Real dataclass post-init with explicit CPU-only/reporting-disabled switches.
    # Uses model metadata only; no model or trainer API is called.
    cpu_flags=flags+extra+['--use_cpu','true','--report_to','none','--add_version','false']
    try:
        (args,)=parser.parse_args_into_dataclasses(cpu_flags)
        results[-1]['dataclass_cpu_init'] = dict(ok=True,device=str(args.training_args.device),
             eval_strategy=str(args.training_args.eval_strategy),
             save_strategy=str(args.training_args.save_strategy),bf16=args.training_args.bf16,
             torch_dtype=str(args.torch_dtype),truncation_strategy=args.truncation_strategy,
             max_length=args.max_length,template=args.template,
             loss_scale=args.loss_scale,weights_loaded=False,trainer_created=False)
    except Exception as e:
        results[-1]['dataclass_cpu_init']=dict(ok=False,error_type=type(e).__name__,error=str(e))
    try:
        (args,)=parser.parse_args_into_dataclasses(cpu_flags+['--model_type','qwen3','--template','qwen3'])
        results[-1]['explicit_qwen3_cpu_init'] = dict(ok=True,device=str(args.training_args.device),
             eval_strategy=str(args.training_args.eval_strategy),
             save_strategy=str(args.training_args.save_strategy),bf16=args.training_args.bf16,
             torch_dtype=str(args.torch_dtype),truncation_strategy=args.truncation_strategy,
             max_length=args.max_length,template=args.template,model_type=args.model_type,
             loss_scale=args.loss_scale,weights_loaded=False,trainer_created=False)
    except Exception as e:
        results[-1]['explicit_qwen3_cpu_init']=dict(ok=False,error_type=type(e).__name__,error=str(e))
(out/'cli_parse.json').write_text(json.dumps(results,ensure_ascii=False,indent=2,default=str)+'\n')
(out/'sft_arguments_postinit.py.txt').write_text(inspect.getsource(SftArguments.__post_init__))
print(json.dumps([dict(mode=x['mode'],unknown_flags=x['unknown_flags'],
                       dataclass_cpu_init=x['dataclass_cpu_init'],
                       explicit_qwen3_cpu_init=x['explicit_qwen3_cpu_init']) for x in results],indent=2))
