#!/usr/bin/env python3
"""Training wrapper: clearml Task -> official LoRA -> output Adapter registry.
Must run in an authorized TRAINING container with a verified GPU maintenance window.
Never changes Kubernetes Deployment, released models or Hub settings.
"""
from __future__ import annotations
import argparse, hashlib, importlib.metadata, json, os, pathlib, re, shutil, subprocess, sys, time, zipfile

def swift_cli_help():
    """Swift 4.4.2's outer argparse consumes --help before SFT parsing."""
    help_text=subprocess.run(['swift','sft','--help'],capture_output=True,text=True,check=True).stdout
    required=('--model','--save_strategy','--data_seed')
    if not all(flag in help_text for flag in required):
        help_text=subprocess.run([sys.executable,'-c',
            'from swift.pipelines import sft_main; sft_main(["--help"])'],
            capture_output=True,text=True,check=True).stdout
    if not all(flag in help_text for flag in required):
        raise RuntimeError('Actual Swift SFT parser help is incomplete')
    return help_text

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def require_env(key):
    value=os.environ.get(key,'').strip()
    if not value: raise RuntimeError(f'Missing required {key}; do not fabricate release lineage')
    return value

def info(name):
    try: return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError: return None

def base_fingerprint(directory):
    root=pathlib.Path(directory)
    if not (root/'config.json').is_file(): raise RuntimeError('Base model missing config.json')
    files=sorted(x for x in root.rglob('*') if x.is_file() and not x.is_symlink())
    if not any(x.name.endswith(('.safetensors','.bin')) for x in files):
        raise RuntimeError('No base weights files')
    return [{'path':x.relative_to(root).as_posix(),'size':x.stat().st_size,'sha256':sha(x)} for x in files]

def validate_training_dataset(dataset, approval):
    """Pure validation (safe for CPU tests) before GPU/ClearML import.

    An edited snapshot is never self-authorizing: the decision record must
    independently name the accepted count AND exact training file hash.
    """
    manifest_file=dataset/'manifest.json'
    manifest=json.loads(manifest_file.read_text(encoding='utf-8'))
    for filename,digest in manifest['files_sha256'].items():
        actual=sha(dataset/filename)
        if digest!=actual: raise RuntimeError(f'Data integrity failure: {filename}')
    if manifest.get('source_specs')!=['swift/Qwen3-SFT-Mixin#2000','swift/self-cognition:qwen3#600']:
        raise RuntimeError('Unexpected official source/subset specs')
    if manifest.get('requested_mixin')!=2000 or manifest.get('requested_identity')!=600:
        raise RuntimeError('Incorrect source sampling parameters')
    if manifest.get('schema') not in ('identity-official-snapshot-v1.2','identity-approved-snapshot-v1.2'):
        raise RuntimeError('Unsupported snapshot schema; migrate and reapprove')
    with (dataset/'train.jsonl').open(encoding='utf-8') as handle:
        rows=[json.loads(line) for line in handle if line.strip()]
    count=len(rows)
    from prepare_official import unresolved_placeholders
    # Derived source attribution is checked against the immutable parent below.
    if unresolved_placeholders(rows,len(rows) if manifest.get('snapshot_kind')!='official_original' else 2000):
        raise RuntimeError('Unreplaced identity placeholder in training snapshot')
    if manifest.get('status','').startswith('QUARANTINED'):
        raise RuntimeError('Quarantined source cannot be trained')
    if count!=manifest.get('rows') or count<1 or count>2600:
        raise RuntimeError('Snapshot record count does not match verified data')
    is_original=manifest.get('snapshot_kind')=='official_original'
    if is_original:
        if count!=2600 or manifest.get('original_rows')!=2600:
            raise RuntimeError('Official original snapshot must retain 2600 rows')
    else:
        if manifest.get('snapshot_kind')!='approved_derivative' or not (0<count<2600):
            raise RuntimeError('Invalid derivative snapshot')
        if not manifest.get('parent_train_sha256') or not manifest.get('exclusions_sha256'):
            raise RuntimeError('Derived snapshot lacks traceable parent/change record')
        if not approval.get('data_change_ref') or not approval.get('data_change_approved'):
            raise RuntimeError('Cleaned data requires independent approval reference')
        parent=pathlib.Path(approval.get('parent_snapshot_dir','')).resolve()
        if not (parent/'manifest.json').is_file():
            raise RuntimeError('Approved derivative must provide original immutable parent snapshot')
        original=json.loads((parent/'manifest.json').read_text(encoding='utf-8'))
        if original.get('snapshot_kind')!='official_original' or original.get('rows')!=2600:
            raise RuntimeError('Derivative parent is not a verified official original')
        if sha(parent/'manifest.json')!=manifest.get('parent_manifest_sha256'):
            raise RuntimeError('Original parent manifest hash mismatch')
        if sha(parent/'train.jsonl')!=manifest['parent_train_sha256'] or sha(parent/'train.jsonl')!=original['files_sha256']['train.jsonl']:
            raise RuntimeError('Original parent hash mismatch')
        excluded=json.loads((dataset/'exclusions.json').read_text(encoding='utf-8'))
        if sha(dataset/'exclusions.json')!=manifest['exclusions_sha256']:
            raise RuntimeError('Exclusion list hash mismatch')
        if not isinstance(excluded,list) or any(not isinstance(x,dict) or 'index' not in x or not isinstance(x.get('reason'),str) or len(x['reason'].strip())<8 for x in excluded):
            raise RuntimeError('Invalid exclusion evidence entries')
        ids=[x['index'] for x in excluded]
        if len(ids)!=2600-count or len(ids)!=len(set(ids)) or any(type(i)!=int or i<0 or i>=2600 for i in ids):
            raise RuntimeError('Invalid or incomplete exclusion list')
        original_lines=(parent/'train.jsonl').read_bytes().splitlines(keepends=True)
        derived_lines=(dataset/'train.jsonl').read_bytes().splitlines(keepends=True)
        excluded_set=set(ids)
        if len(original_lines)!=2600 or derived_lines!=[ln for i,ln in enumerate(original_lines) if i not in excluded_set]:
            raise RuntimeError('Derivative must preserve approved original row bytes/order')
        identity_rows=[json.loads(ln) for i,ln in enumerate(original_lines)
                       if i>=2000 and i not in excluded_set]
        if unresolved_placeholders(identity_rows,0):
            raise RuntimeError('Unreplaced identity placeholder in derivative identity records')
    if approval.get('approved_rows')!=count or approval.get('approved_data_sha256')!=manifest['files_sha256']['train.jsonl']:
        raise RuntimeError('Independent approval must explicitly bind exact approved rows and data SHA')
    if approval.get('approved_snapshot_manifest_sha256')!=sha(manifest_file):
        raise RuntimeError('Approved manifest SHA mismatch')
    return manifest, manifest_file


def validate_length_preflight(dataset, manifest_file, approval):
    report_file=dataset/'preflight_report.json'
    if not report_file.is_file(): raise RuntimeError('Missing CPU template/token length preflight report')
    report=json.loads(report_file.read_text(encoding='utf-8'))
    if (report.get('schema')!='identity-token-preflight-v1.2' or
        report.get('dataset_sha256')!=sha(dataset/'train.jsonl') or
        report.get('manifest_sha256')!=sha(manifest_file) or
        report.get('model_files_sha256')!=approval.get('preflight_model_files_sha256') or
        report.get('rows_checked')!=approval.get('approved_rows') or
        report.get('max_length')!=2048 or report.get('overlength_rows')!=0 or
        not report.get('template_tokenization_completed') or
        not report.get('ms_swift_template_verified')):
        raise RuntimeError('CPU length preflight not valid or real ms-swift template unverified')
    if approval.get('preflight_report_sha256')!=sha(report_file):
        raise RuntimeError('Independent approved preflight checksum mismatch')
    return report


def latest_adapter(directory):
    root=pathlib.Path(directory)
    candidates=sorted(root.glob('**/checkpoint-*'),key=lambda x:int(re.search(r'checkpoint-(\d+)',x.name).group(1)) if re.search(r'checkpoint-(\d+)',x.name) else -1)
    candidates=[d for d in candidates if (d/'adapter_config.json').is_file() and any(d.glob('adapter_model.*'))]
    if not candidates: raise RuntimeError('No complete Adapter checkpoint; do not mark training successful')
    return candidates[-1]

def zip_adapter(checkpoint, target):
    files=[]
    names=('adapter_config.json','adapter_model.safetensors','adapter_model.bin','tokenizer.json',
           'tokenizer_config.json','special_tokens_map.json','added_tokens.json','vocab.json','merges.txt')
    for name in names:
        path=checkpoint/name
        if path.is_file(): files.append(path)
    if not any(p.name.startswith('adapter_model.') for p in files): raise RuntimeError('Adapter weight missing')
    with zipfile.ZipFile(target,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in files:
            zi=zipfile.ZipInfo(p.name,date_time=(1980,1,1,0,0,0))
            zi.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(zi,p.read_bytes())
    return {p.name:{'sha256':sha(p),'bytes':p.stat().st_size} for p in files}

def main():
    pa=argparse.ArgumentParser(description=__doc__)
    pa.add_argument('mode',choices=('smoke','full'))
    args=pa.parse_args()
    if require_env('RUN_AUTHORIZED')!='yes' or require_env('GPU_WINDOW_APPROVED')!='yes':
        raise RuntimeError('Run and current GPU interruption window must be authorized')
    model=pathlib.Path(require_env('BASE_MODEL')).resolve()
    dataset=pathlib.Path(require_env('DATA_DIR')).resolve()
    out=pathlib.Path(require_env('OUT_DIR')).resolve()
    image_digest=require_env('TRAIN_IMAGE_DIGEST')
    source_commit=require_env('SOURCE_GIT_COMMIT')
    approval_file=pathlib.Path(require_env('APPROVAL_FILE')).resolve()
    if out.exists(): raise FileExistsError(f'Refuse to overwrite prior run: {out}')
    approval=json.loads(approval_file.read_text(encoding='utf-8'))
    if (not approval.get('identity_verified') or not approval.get('gpu_window_approved') or
        not approval.get('experiment_approved') or
        not all(approval.get('sources_approved',{}).get(k,False)
                    for k in ('swift/Qwen3-SFT-Mixin','swift/self-cognition:qwen3')) or
        not approval.get('decision_ref') or not approval.get('source_snapshot_ref')):
        raise RuntimeError('Identity, both sources, one experiment and actual GPU window not approved')
    manifest, manifest_file=validate_training_dataset(dataset, approval)
    preflight=validate_length_preflight(dataset, manifest_file, approval)
    import torch
    if not torch.cuda.is_available() or not torch.cuda.is_bf16_supported():
        raise RuntimeError('BF16 GPU unavailable')
    from clearml import Task, OutputModel
    if not re.fullmatch(r'sha256:[0-9a-f]{64}',image_digest) or not re.fullmatch(r'[0-9a-f]{40}',source_commit):
        raise RuntimeError('Require real sha256 image digest and full Git SHA1 commit')
    swifthelp=swift_cli_help()
    tuner='--tuner_type' if '--tuner_type' in swifthelp else ('--train_type' if '--train_type' in swifthelp else None)
    if not tuner: raise RuntimeError('LoRA CLI option unknown; pin/test exact ms-swift version')
    eval_switch='--eval_strategy' if '--eval_strategy' in swifthelp else ('--evaluation_strategy' if '--evaluation_strategy' in swifthelp else None)
    if not eval_switch: raise RuntimeError('Cannot explicitly disable eval with this ms-swift CLI')
    if '--save_strategy' not in swifthelp: raise RuntimeError('Cannot verify required checkpoint save strategy')
    if '--data_seed' not in swifthelp: raise RuntimeError('Cannot pin data shuffle seed in this ms-swift CLI')
    # With an immutable local training snapshot there is NO training-derived val set;
    # standalone independent tests are scored later. Avoid replay leakage.
    run_id=out.name
    common=['swift','sft','--model',str(model),'--model_type','qwen3','--template','qwen3',tuner,'lora',
        '--dataset',str(dataset/'train.jsonl'),'--split_dataset_ratio','0',
        '--torch_dtype','bfloat16','--num_train_epochs','1',
        '--per_device_train_batch_size','1','--per_device_eval_batch_size','1',
        '--learning_rate','1e-4','--lora_rank','8','--lora_alpha','32',
        '--target_modules','all-linear','--gradient_accumulation_steps','16',
        '--max_length','2048','--warmup_ratio','0.05',eval_switch,'no',
        '--save_total_limit','2','--logging_steps','5',
        '--dataloader_num_workers','4','--seed','42','--data_seed','42',
        '--push_to_hub','false','--output_dir',str(out/'checkpoints')]
    if '--gradient_checkpointing' in swifthelp: common.extend(['--gradient_checkpointing','true'])
    if '--save_only_model' in swifthelp: common.extend(['--save_only_model','false'])
    if '--report_to' in swifthelp: common.extend(['--report_to','tensorboard'])
    # Preserve the official 50-step save interval for smoke, but force a FINAL
    # checkpoint at end of the full epoch to avoid registering checkpoint-150
    # when the actual run ended after e.g. 163 optimizer steps.
    if args.mode=='smoke':
        common.extend(['--max_steps','3','--save_strategy','steps','--save_steps','3'])
    else:
        common.extend(['--save_strategy','epoch'])
    if os.environ.get('USE_QLORA')=='true':
        common.extend(['--quant_method','bnb','--quant_bits','4',
                       '--bnb_4bit_quant_type','nf4',
                       '--bnb_4bit_compute_dtype','bfloat16',
                       '--bnb_4bit_use_double_quant','true'])
    if os.environ.get('USE_LIGER')=='true': common.extend(['--use_liger_kernel','true'])
    files=base_fingerprint(model)
    actual_base_hash=hashlib.sha256(json.dumps(files,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    if preflight['model_files_sha256']!=actual_base_hash:
        raise RuntimeError('Tokenizer preflight model does not match training base model')
    out.mkdir(parents=True)
    meta={'schema':'identity-run-v1.2','run_id':run_id,'mode':args.mode,
          'status':'RUNNING','dataset_manifest_sha256':sha(manifest_file),
          'data_sha256':sha(dataset/'train.jsonl'),'base_files':files,
          'approved_rows':approval['approved_rows'],'preflight_report_sha256':sha(dataset/'preflight_report.json'),
          'source_git_commit':source_commit,'image_digest':image_digest,
          'base_files_sha256':actual_base_hash,
          'approval_ref':approval['decision_ref'],'approval_sha256':sha(approval_file),'torch':info('torch'),
          'ms_swift':info('ms-swift'),'clearml':info('clearml'),
          'gpu':torch.cuda.get_device_name(0),'quantization':os.environ.get('USE_QLORA','false'),
          'command':common,'start_utc':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()}
    (out/'run_manifest.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
    task=None
    try:
        task=Task.init(project_name='reg/identity-sft',task_name=run_id,
                       task_type=Task.TaskTypes.training,
                       reuse_last_task_id=False,auto_connect_frameworks=False,
                       auto_connect_arg_parser=False)
        task.set_parameter('identity/mode',args.mode)
        task.set_parameter('identity/dataset_sha256',meta['data_sha256'])
        task.set_parameter('identity/base_manifest_sha256',hashlib.sha256(
            json.dumps(files,ensure_ascii=False,sort_keys=True).encode()).hexdigest())
        task.set_parameter('identity/git_commit',source_commit)
        task.set_parameter('identity/image_digest',image_digest)
        task.set_parameter('identity/approval_ref',approval['decision_ref'])
        task.set_parameter('identity/source_snapshot_ref',approval['source_snapshot_ref'])
        task.upload_artifact('input-run-manifest',artifact_object=str(out/'run_manifest.json'))
        meta['clearml_task_id']=task.id
        (out/'run_manifest.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
        # Trainer is a subprocess; the ClearML Task is recorded by this parent wrapper.
        # The checkpoint and summary are uploaded explicitly; no raw data or tests go to ClearML.
        with (out/'train.log').open('w',encoding='utf-8') as f:
            proc=subprocess.Popen(common,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
            for line in proc.stdout:
                f.write(line);f.flush()
            exit_code=proc.wait()
        meta['training_exit_code']=exit_code
        if exit_code: raise RuntimeError(f'swift sft exited {exit_code}')
        ckpt=latest_adapter(out/'checkpoints')
        meta['checkpoint']=str(ckpt)
        trainer_state=ckpt/'trainer_state.json'
        if trainer_state.is_file():
            try:
                state=json.loads(trainer_state.read_text(encoding='utf-8'))
                checkpoint_step=int(re.search(r'checkpoint-(\d+)',ckpt.name).group(1))
                if state.get('global_step') is not None and int(state['global_step'])!=checkpoint_step:
                    raise RuntimeError('Selected checkpoint does not match Trainer final global_step')
                metrics={'global_step':state.get('global_step'),
                         'best_metric':state.get('best_metric'),
                         'log_history':state.get('log_history',[])}
                metrics_path=out/'training-metrics.json'
                metrics_path.write_text(json.dumps(metrics,ensure_ascii=False,indent=2)+'\n')
                task.upload_artifact('training-metrics',artifact_object=str(metrics_path))
            except Exception as e:
                # A trainer format mismatch must be visible but cannot create false metrics.
                meta['metrics_registration_error']=repr(e)
        if args.mode=='full':
            if meta.get('metrics_registration_error'):
                raise RuntimeError(meta['metrics_registration_error'])
            if not trainer_state.is_file() or not state.get('global_step'):
                raise RuntimeError('Full final checkpoint has no verifiable Trainer global_step')
            if float(state.get('epoch') or 0) < 0.999:
                raise RuntimeError('Final checkpoint did not complete one epoch')
        if args.mode=='full':
            package=out/'adapter-candidate.zip'
            meta['adapter_files']=zip_adapter(ckpt,package)
            meta['adapter_package_sha256']=sha(package)
            mdl=OutputModel(task=task,name=f'{run_id}-candidate',framework='pytorch')
            uri=mdl.update_weights(weights_filename=str(package),target_filename=package.name,
                                   auto_delete_file=False)
            meta['clearml_output_model_id']=mdl.id
            task.set_parameter('identity/adapter_package_sha256',meta['adapter_package_sha256'])
            task.set_parameter('identity/output_model_id',mdl.id)
            meta['clearml_model_uri']=uri
        meta['status']='TRAINED_CANDIDATE' if args.mode=='full' else 'SMOKE_COMPLETE'
        meta['finished_utc']=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()
        (out/'run_manifest.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
        task.upload_artifact('final-run-manifest',artifact_object=str(out/'run_manifest.json'))
        # Download and verify registered bytes: task success alone is not model proof.
        if args.mode=='full':
            from clearml import Model
            registered=Model(model_id=mdl.id)
            if not registered.url: raise RuntimeError('Registered OutputModel missing URI')
            downloaded=registered.get_local_copy(extract_archive=False)
            if not downloaded or not pathlib.Path(downloaded).is_file():
                raise RuntimeError('Cannot read back registered Adapter file')
            if sha(downloaded)!=meta['adapter_package_sha256']:
                raise RuntimeError('ClearML registered Adapter bytes differ from local package')
            meta['clearml_model_readback_sha256']=sha(downloaded)
            (out/'run_manifest.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
            task.upload_artifact('verified-final-run-manifest',artifact_object=str(out/'run_manifest.json'))
        task.close()
        print(json.dumps({'task_id':task.id,'status':meta['status'],
            'output':str(out),'model_id':meta.get('clearml_output_model_id')},ensure_ascii=False))
    except BaseException as exc:
        meta['status']='FAILED'
        meta['error']=f'{type(exc).__name__}: {exc}'
        (out/'run_manifest.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
        if task:
            try: task.mark_failed(status_reason=str(exc)[:180]);task.close()
            except Exception: pass
        raise

if __name__=='__main__': main()
