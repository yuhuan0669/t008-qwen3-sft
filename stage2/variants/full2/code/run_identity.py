#!/usr/bin/env python3
"""Training wrapper: clearml Task -> official LoRA -> output Adapter registry.
Must run in an authorized TRAINING container with a verified GPU maintenance window.
Never changes Kubernetes Deployment, released models or Hub settings.
"""
from __future__ import annotations
import argparse, hashlib, importlib.metadata, json, os, pathlib, re, shutil, subprocess, sys, time, zipfile
from urllib.parse import urlsplit

def clearml_storage_uri(value):
    uri=urlsplit(value)
    if (uri.scheme!='https' or not uri.hostname or uri.username or uri.password
            or uri.query or uri.fragment):
        raise RuntimeError('Require explicit authenticated HTTPS ClearML Files storage endpoint')
    return value.rstrip('/')

def validate_registered_model_uri(value, storage):
    target=urlsplit(value or '');base=urlsplit(storage)
    if (target.scheme!='https' or target.netloc!=base.netloc or
        not target.path.startswith(base.path.rstrip('/')+'/') or
        target.username or target.password or target.query or target.fragment):
        raise RuntimeError('Registered OutputModel must reference intended remote HTTPS Files storage')

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

def validate_authorization(approval):
    """Only literal JSON true is an approval flag; strings are not authority."""
    sources=approval.get('sources_approved')
    if (any(approval.get(k) is not True for k in
            ('identity_verified','gpu_window_approved','experiment_approved')) or
        not isinstance(sources,dict) or
        any(sources.get(k) is not True for k in
            ('swift/Qwen3-SFT-Mixin','swift/self-cognition:qwen3')) or
        not approval.get('decision_ref') or not approval.get('source_snapshot_ref')):
        raise RuntimeError('Identity, both sources, one experiment and actual GPU window not approved')

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
        if not approval.get('data_change_ref') or approval.get('data_change_approved') is not True:
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
        report.get('template_tokenization_completed') is not True or
        report.get('ms_swift_template_verified') is not True):
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

def verify_final_checkpoint(directory, checkpoint):
    """Require pipeline's completed-run terminal record, not checkpoint self-report."""
    logs=list(pathlib.Path(directory).rglob('logging.jsonl'))
    terminal=[]
    for log in logs:
        for line in log.read_text().splitlines():
            try: entry=json.loads(line)
            except ValueError: continue
            if entry.get('global_step') is not None and entry.get('last_model_checkpoint'):
                terminal.append(entry)
    if len(terminal)!=1:
        raise RuntimeError('Require one actual Swift terminal training record')
    final=terminal[0]
    state=json.loads((checkpoint/'trainer_state.json').read_text())
    step=int(re.search(r'checkpoint-(\d+)$',checkpoint.name).group(1))
    if (step!=int(final['global_step']) or step!=int(state['global_step'])
        or pathlib.Path(final['last_model_checkpoint']).resolve()!=checkpoint.resolve()
        or int(state.get('max_steps',-1))!=step or float(state.get('epoch') or 0)<0.999):
        raise RuntimeError('Adapter does not match actual completed final training step')
    return final

def main():
    pa=argparse.ArgumentParser(description=__doc__)
    pa.add_argument('mode',choices=('smoke','full','cpu-check'))
    pa.add_argument('--model')
    pa.add_argument('--identity-spec')
    pa.add_argument('--evidence-dir')
    pa.add_argument('--reference-snapshot')
    pa.add_argument('--base-files')
    args=pa.parse_args()
    from native_recipe import build_command, cpu_check, spec_read, validate_report
    if args.mode=='cpu-check':
        values=(args.model,args.identity_spec,args.evidence_dir,args.reference_snapshot,args.base_files)
        if not all(values): pa.error('cpu-check requires model, identity-spec, evidence-dir, reference-snapshot, base-files')
        report=cpu_check(*values, swift_cli_help())
        print(json.dumps(report,ensure_ascii=False,indent=2))
        return
    if any(os.environ.get(k,'false').lower()!='false' for k in ('USE_QLORA','USE_LIGER')):
        raise RuntimeError('Optimization is deferred; official native LoRA recipe only')
    if require_env('RUN_AUTHORIZED')!='yes' or require_env('GPU_WINDOW_APPROVED')!='yes':
        raise RuntimeError('Run and current GPU interruption window must be authorized')
    model=pathlib.Path(require_env('BASE_MODEL')).resolve()
    spec=spec_read(require_env('IDENTITY_SPEC'))
    native_report_file=pathlib.Path(require_env('NATIVE_PREFLIGHT_REPORT')).resolve()
    out=pathlib.Path(require_env('OUT_DIR')).resolve()
    image_digest=require_env('TRAIN_IMAGE_DIGEST')
    source_commit=require_env('SOURCE_GIT_COMMIT')
    approval_file=pathlib.Path(require_env('APPROVAL_FILE')).resolve()
    if out.exists(): raise FileExistsError(f'Refuse to overwrite prior run: {out}')
    approval=json.loads(approval_file.read_text(encoding='utf-8'))
    validate_authorization(approval)
    files_host=clearml_storage_uri(require_env('CLEARML_FILES_HOST'))
    preflight=validate_report(native_report_file, spec, approval)
    # Freeze the approved bytes for the child plugin; never reread a mutable
    # unbound report as the source of expected training membership.
    os.environ['NATIVE_PREFLIGHT_SHA256']=approval['native_preflight_report_sha256']
    import torch
    if not torch.cuda.is_available() or not torch.cuda.is_bf16_supported():
        raise RuntimeError('BF16 GPU unavailable')
    from clearml import Task, OutputModel
    if not re.fullmatch(r'sha256:[0-9a-f]{64}',image_digest) or not re.fullmatch(r'[0-9a-f]{40}',source_commit):
        raise RuntimeError('Require real sha256 image digest and full Git SHA1 commit')
    swifthelp=swift_cli_help()
    run_id=out.name
    common=build_command(args.mode, model, out/'checkpoints', spec, swifthelp)
    # Compare every formal parser field against actual CPU-validated Full plan;
    # path/mode-specific differences are bounded in native_recipe.
    from native_recipe import validate_formal_command
    validate_formal_command(common, preflight['formal_command'], args.mode)
    files=base_fingerprint(model)
    actual_base_hash=hashlib.sha256(json.dumps(files,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    if preflight['model_files_sha256']!=actual_base_hash:
        raise RuntimeError('Tokenizer preflight model does not match training base model')
    out.mkdir(parents=True)
    meta={'schema':'identity-run-v1.2','run_id':run_id,'mode':args.mode,
          'status':'RUNNING','data_mode':'official_native_default_delete',
          'data_sha256':preflight['native_input']['sha256'],'base_files':files,
          'native_input':preflight['native_input'],'native_retained':preflight['native_retained'],
          'approved_rows':approval['approved_rows'],'preflight_report_sha256':sha(native_report_file),
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
                       auto_connect_arg_parser=False,output_uri=files_host)
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
            verify_final_checkpoint(out/'checkpoints', ckpt)
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
                                   auto_delete_file=False,upload_uri=files_host,async_enable=False)
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
            validate_registered_model_uri(registered.url,files_host)
            downloaded=registered.get_local_copy(extract_archive=False,force_download=True)
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
