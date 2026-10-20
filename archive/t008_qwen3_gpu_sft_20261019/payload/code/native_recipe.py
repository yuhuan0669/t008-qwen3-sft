"""Official native recipe and CPU-only evidence. Does not grant training authority."""
from __future__ import annotations
import collections
import hashlib
import importlib.metadata
import json
import pathlib
import re

SOURCES = ['swift/Qwen3-SFT-Mixin#2000', 'swift/self-cognition:qwen3#600']
FIELDS = ('name_zh', 'name_en', 'author_zh', 'author_en')

def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()

def spec_read(path):
    spec = json.loads(pathlib.Path(path).read_text())
    if any(not isinstance(spec.get(k), str) or not spec[k].strip() or
           re.search(r'待填|待确认|<.*>|\{\{', spec[k]) for k in FIELDS):
        raise RuntimeError('Four confirmed bilingual identity fields required')
    if spec.get('base_model') != 'Qwen/Qwen3-8B':
        raise RuntimeError('Unexpected base identity')
    return {k:spec[k] for k in (*FIELDS, 'base_model')}

def build_command(mode, model, output, spec, help_text):
    if mode not in ('full', 'smoke'):
        raise ValueError('Unsupported training mode')
    tuner = next((x for x in ('--tuner_type','--train_type') if x in help_text), None)
    evaluation = next((x for x in ('--eval_strategy','--evaluation_strategy') if x in help_text), None)
    required = ('--save_strategy','--save_steps','--data_seed','--model_name',
                '--model_author','--external_plugins')
    if not tuner or not evaluation or any(x not in help_text for x in required):
        raise RuntimeError('Actual Swift parser lacks required native recipe options')
    argv = ['swift','sft','--model',str(model),'--model_type','qwen3','--template','qwen3',
        tuner,'lora','--dataset',*SOURCES,
        '--model_name',spec['name_zh'],spec['name_en'],
        '--model_author',spec['author_zh'],spec['author_en'],
        '--split_dataset_ratio','0','--torch_dtype','bfloat16','--num_train_epochs','1',
        '--per_device_train_batch_size','1','--per_device_eval_batch_size','1',
        '--learning_rate','1e-4','--lora_rank','8','--lora_alpha','32',
        '--target_modules','all-linear','--gradient_accumulation_steps','16',
        '--max_length','2048','--warmup_ratio','0.05',evaluation,'no','--eval_steps','50',
        '--save_strategy','steps','--save_steps','50' if mode=='full' else '3',
        '--save_total_limit','2','--logging_steps','5','--dataloader_num_workers','4',
        '--seed','42','--data_seed','42','--push_to_hub','false',
        '--output_dir',str(output),'--gradient_checkpointing','true',
        '--save_only_model','false','--report_to','tensorboard',
        '--external_plugins',str(pathlib.Path(__file__).with_name('native_guard.py'))]
    if mode=='smoke':
        argv += ['--max_steps','3']
    return argv

def dataset_record(dataset):
    rows = [] if dataset is None else list(dataset)
    return {'rows':len(rows), 'sha256':digest(rows)}

def implementation_fingerprint():
    import swift
    root=pathlib.Path(__file__).parent
    swift_root=pathlib.Path(swift.__file__).parent
    files={str(root/n):root/n for n in ('native_recipe.py','native_guard.py','run_identity.py','train_identity.sh')}
    # Relative keys are portable across CPU and the later training container.
    result={'entry/'+path.name:hashlib.sha256(path.read_bytes()).hexdigest() for path in files.values()}
    for name in ('pipelines/train/sft.py','arguments/sft_args.py','dataset/loader.py',
                 'dataset/utils.py','template/base.py','trainers/patcher.py'):
        result['swift/'+name]=hashlib.sha256((swift_root/name).read_bytes()).hexdigest()
    return result

def check_record(observed, expected, label):
    if observed != expected:
        raise RuntimeError(f'Native {label} drift: {observed} != {expected}')

def validate_formal_command(command, approved, mode):
    def normalized(argv):
        result=list(argv)
        for flag in ('--model','--output_dir','--external_plugins'):
            i=result.index(flag); result[i+1]='<bound separately>'
        if mode=='smoke' and '--max_steps' in result:
            i=result.index('--max_steps'); del result[i:i+2]
            i=result.index('--save_steps'); result[i+1]='50'
        return result
    if normalized(command)!=normalized(approved):
        raise RuntimeError('Formal command differs from CPU-validated native recipe')

def validate_native_args(args):
    if (args.dataset!=SOURCES or args.split_dataset_ratio!=0 or
        args.max_length!=2048 or args.truncation_strategy!='delete' or
        args.seed!=42 or args.data_seed!=42 or not args.dataset_shuffle or args.use_hf or
        any(getattr(args,k,None) for k in ('cached_dataset','cached_val_dataset','val_dataset',
                                          'streaming','packing','lazy_tokenize'))):
        raise RuntimeError('Unexpected native runtime configuration or cached-data bypass')

def validate_report(path, spec, approval=None):
    from run_identity import sha
    report = json.loads(pathlib.Path(path).read_text())
    if (report.get('schema')!='t008-native-cpu-v1' or report.get('verified') is not True
        or report.get('spec')!=spec or report.get('source_specs')!=SOURCES
        or report.get('truncation_strategy')!='delete' or report.get('max_length')!=2048
        or report.get('seed')!=42 or report.get('data_seed')!=42
        or report.get('dataset_shuffle') is not True
        or report.get('native_input',{}).get('rows')!=2600
        or report.get('validation_rows')!=0):
        raise RuntimeError('Invalid native CPU evidence/configuration')
    if approval is not None:
        if (approval.get('native_preflight_report_sha256')!=sha(path)
            or approval.get('approved_rows')!=report['native_retained']['rows']
            or approval.get('approved_data_sha256')!=report['native_input']['sha256']
            or approval.get('preflight_model_files_sha256')!=report['model_files_sha256']):
            raise RuntimeError('Training approval must bind actual native CPU evidence and data')
    for name, version in report['versions'].items():
        if importlib.metadata.version(name)!=version:
            raise RuntimeError(f'CPU/runtime package drift: {name}')
    check_record(implementation_fingerprint(),report['implementation_fingerprint'],'implementation')
    return report

def cpu_check(model, spec_path, output, reference_snapshot, base_files_path, help_text):
    """Actual parser + native load + actual Swift preprocessing, no model/Trainer."""
    from run_identity import sha
    out = pathlib.Path(output)
    out.mkdir(parents=True, exist_ok=False)
    spec = spec_read(spec_path)
    command = build_command('full', model, out/'training-output-NOT-STARTED', spec, help_text)
    from transformers import HfArgumentParser
    from swift.arguments import SftArguments
    parser = HfArgumentParser(SftArguments)
    namespace, unknown = parser.parse_known_args(command[2:])
    if unknown:
        raise RuntimeError(f'Unknown formal parameters: {unknown}')
    (out/'formal-command.json').write_text(json.dumps(command, ensure_ascii=False, indent=2)+'\n')
    (out/'formal-parser.json').write_text(json.dumps(vars(namespace), ensure_ascii=False, indent=2, default=str)+'\n')
    # CPU overrides only: same data, templates, seeds and training recipe.
    args, = parser.parse_args_into_dataclasses(command[2:]+[
        '--use_cpu','true','--report_to','none','--add_version','false'])
    validate_native_args(args)
    if args.truncation_strategy!='delete' or not args.dataset_shuffle:
        raise RuntimeError('Official nonstreaming defaults changed')
    if str(args.training_args.device)!='cpu':
        raise RuntimeError('CPU isolation missing')
    dataset, val = args.load_dataset()  # exact formal native path, including shuffle=True
    native = dataset_record(dataset)
    if native['rows']!=2600 or (val is not None and len(val)):
        raise RuntimeError('Unexpected native source count/validation')
    raw_rows = list(dataset)
    (out/'native-loaded.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False, sort_keys=True)+'\n' for r in raw_rows))
    from swift.model import get_processor
    from swift.template import get_template
    from swift.pipelines.train.sft import SwiftSft
    processor = get_processor(model, model_type='qwen3', download_model=False)
    template = get_template(processor, **args.get_template_kwargs())
    template.set_mode('train')
    template_kwargs=args.get_template_kwargs()
    # Invoke actual pipeline method with a metadata-only stub. SwiftSft.__init__
    # would load weights and is deliberately never called.
    class Stub:
        def _save_val_dataset(self, val):
            if val is not None and len(val):
                raise RuntimeError('Unexpected validation data')
    stub = Stub(); stub.args=args; stub.template=template
    # The plugin is always fail-closed in a training pipeline. Here invoke the
    # original installed method directly while constructing its CPU evidence.
    encode_method=getattr(SwiftSft._encode_dataset,'__wrapped__',SwiftSft._encode_dataset)
    retained, val = encode_method(stub, dataset, val)
    retained_record = dataset_record(retained)
    (out/'native-retained.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False, sort_keys=True)+'\n' for r in retained))
    # Compare content and sampling with immutable previous preparation; order
    # may change because official SftArguments enables dataset_shuffle=True.
    old = [json.loads(x) for x in pathlib.Path(reference_snapshot).read_text().splitlines()]
    from prepare_official import normal_row, unresolved_placeholders
    original_counts = collections.Counter(digest(normal_row(x)) for x in old)
    actual_counts = collections.Counter(digest(normal_row(x)) for x in raw_rows)
    known = set(original_counts)
    if set(actual_counts)-known:
        raise RuntimeError('Native loader produced content absent from reviewed original')
    # Attribution by immutable raw content, independent of shuffled positions.
    mixin_keys={digest(normal_row(x)) for x in old[:2000]}
    identity_keys={digest(normal_row(x)) for x in old[2000:]}
    if mixin_keys & identity_keys:
        raise RuntimeError('Ambiguous source attribution')
    def source_counts(rows):
        c=collections.Counter('mixin' if digest(normal_row(r)) in mixin_keys else 'identity' for r in rows)
        return dict(c)
    identity_rows=[normal_row(x) for x in raw_rows if digest(normal_row(x)) in identity_keys]
    if unresolved_placeholders(identity_rows,0):
        raise RuntimeError('Unresolved native identity placeholders')
    unbounded = get_template(processor, **args.get_template_kwargs())
    unbounded.max_length=None; unbounded.set_mode('train')
    audit=[]
    for i,row in enumerate(raw_rows):
        enc=unbounded.encode(row, return_length=True)
        ids=enc['input_ids']; labels=enc['labels']
        assert len(ids)==len(labels) and all(y==-100 or y==x for x,y in zip(ids,labels))
        n=sum(x!=-100 for x in labels)
        if not n: raise RuntimeError('No supervised tokens')
        audit.append(dict(native_row_zero_based=i,tokens=len(ids),supervised_tokens=n,
                          retained=len(ids)<=2048,input_ids_sha256=digest(ids),labels_sha256=digest(labels)))
    (out/'row-audit.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in audit))
    expected=collections.Counter(digest(normal_row(x)) for x,r in zip(raw_rows,audit) if r['retained'])
    if expected!=collections.Counter(digest(normal_row(x)) for x in retained):
        raise RuntimeError('Actual Swift delete membership differs from full-length audit')
    files=json.loads(pathlib.Path(base_files_path).read_text())
    for record in files:
        p=pathlib.Path(model)/record['path']
        if p.stat().st_size!=record['size'] or sha(p)!=record['sha256']:
            raise RuntimeError(f'Base file drift: {p.name}')
    versions={n:importlib.metadata.version(n) for n in
              ('ms-swift','transformers','peft','torch','tokenizers','datasets','modelscope')}
    report=dict(schema='t008-native-cpu-v1',verified=True,spec=spec,source_specs=SOURCES,
        native_input=native,native_retained=retained_record,validation_rows=0,
        input_source_counts=source_counts(raw_rows),retained_source_counts=source_counts(retained),
        removed_rows=len(raw_rows)-len(retained),input_unique_rows=len(actual_counts),
        retained_unique_rows=len(expected),original_content_membership_verified=True,
        same_exposure_multiset_as_old=(actual_counts==original_counts),
        old_reference_sha256=sha(reference_snapshot),
        native_message_order_sha256=digest([normal_row(x) for x in raw_rows]),
        retained_message_order_sha256=digest([normal_row(x) for x in retained]),
        model_files_sha256=hashlib.sha256(json.dumps(files,ensure_ascii=False,sort_keys=True).encode()).hexdigest(),
        all_base_files_fully_rehashed=True,versions=versions,implementation_fingerprint=implementation_fingerprint(),max_length=args.max_length,
        truncation_strategy=args.truncation_strategy,template_truncation_strategy=template.truncation_strategy,
        seed=args.seed,data_seed=args.data_seed,dataset_shuffle=args.dataset_shuffle,
        loss_scale=args.loss_scale,template=args.template,template_kwargs=template_kwargs,formal_unknown_flags=unknown,
        cpu_overrides={'use_cpu':True,'report_to':['none'],'add_version':False},
        weights_loaded=False,trainer_created=False,clearml_task_created=False,gpu_training_started=False,
        formal_command=command)
    (out/'native-preflight.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    return report
