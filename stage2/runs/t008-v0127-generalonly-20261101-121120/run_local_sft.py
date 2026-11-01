"""Local-data SFT wrapper. Never changes serving workloads; reuses archived upload helpers."""
from pathlib import Path
import argparse,datetime,hashlib,importlib.metadata as md,json,math,os,struct,subprocess,sys,time

def verify_adapter_scope(checkpoint,spec):
 cfg=json.loads((checkpoint/'adapter_config.json').read_text())
 expected={'q_proj','k_proj','v_proj','o_proj','gate_proj','up_proj','down_proj'}
 assert set(cfg['target_modules'])==expected and cfg['r']==8 and cfg['lora_alpha']==32
 assert not cfg['modules_to_save']
 with (checkpoint/'adapter_model.safetensors').open('rb') as f:
  header=json.loads(f.read(struct.unpack('<Q',f.read(8))[0]))
 tensors={k:v for k,v in header.items() if k!='__metadata__'}
 assert all('.lora_' in k and any('.'+m+'.' in k for m in expected) for k in tensors)
 count=sum(math.prod(x['shape']) for x in tensors.values())
 assert count==spec['expected_trainable_parameters']==21823488
 return {'target_modules':sorted(expected),'parameter_count':count,'tensor_count':len(tensors),'verified':True}

def validate_binding(spec,report,auth,now=None):
 now=now or datetime.datetime.now(datetime.timezone.utc)
 if auth.get('experiment_approved') is not True or auth.get('uat_pause_approved') is not True:raise RuntimeError('Missing current user authorization')
 if not datetime.datetime.fromisoformat(auth['window_start_utc'])<=now<datetime.datetime.fromisoformat(auth['window_end_utc']):raise RuntimeError('Outside GPU window')
 if not spec['dataset_sha256']==report['dataset_sha256']==auth['approved_data_sha256']:raise RuntimeError('Frozen data drift')
 if not report.get('verified') or spec['dataset_rows']!=report['rows']:raise RuntimeError('CPU encoding evidence mismatch')

def build_command(spec,mode,base,inp,out):
 cmd=[s.replace('/work/', inp + '/') for s in spec['full_argv']]
 for flag,value in {'--model':base,'--dataset':inp+'/stage1/data/train.jsonl','--external_plugins':inp+'/stage1/training/local_data_guard.py','--output_dir':out+'/checkpoints'}.items():cmd[cmd.index(flag)+1]=value
 if mode=='smoke':
  cmd+=['--max_steps','3'];cmd[cmd.index('--save_steps')+1]='3'
 return cmd

def main():
 ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['smoke','full']);ap.add_argument('--input',default='/input');ap.add_argument('--output',required=True);a=ap.parse_args()
 inp=Path(a.input);out=Path(a.output);spec=json.loads((inp/'stage1/training/run-spec.json').read_text());report=json.loads((inp/'stage1/evidence/encoding-report.json').read_text());auth=json.loads((inp/'window.json').read_text())
 validate_binding(spec,report,auth)
 if out.exists():raise FileExistsError(out)
 for name,version in report['versions'].items():
  if md.version(name)!=version:raise RuntimeError('Runtime differs from CPU encoding: '+name)
 data=inp/'stage1/data/train.jsonl'
 if hashlib.sha256(data.read_bytes()).hexdigest()!=spec['dataset_sha256']:raise RuntimeError('Train bytes changed')
 sys.path[:0]=[str(inp/'code'),str(inp/'stage1/scripts')]
 from run_identity import sha,info,clearml_storage_uri,latest_adapter,verify_final_checkpoint,zip_adapter,validate_registered_model_uri
 from collect_metrics import collect,report_to_existing_task
 proc=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,process_name','--format=csv,noheader'],text=True).strip()
 if proc:raise RuntimeError('GPU compute process exists before training: '+proc)
 gpu_before=subprocess.check_output(['nvidia-smi','--query-gpu=name,memory.used,memory.total,utilization.gpu','--format=csv,noheader'],text=True).strip()
 import torch
 if not torch.cuda.is_available() or not torch.cuda.is_bf16_supported():raise RuntimeError('BF16 GPU unavailable')
 # Match tokenizer/config used for CPU preflight without loading weights.
 for name,digest in report['tokenizer_config_sha256'].items():
  if sha(Path('/base')/name)!=digest:raise RuntimeError('Base tokenizer/config drift: '+name)
 from clearml import Task,OutputModel,Model
 storage=clearml_storage_uri(os.environ['CLEARML_FILES_HOST'])
 cmd=build_command(spec,a.mode,'/base',str(inp),str(out));out.mkdir(parents=True)
 meta={'schema':'t008-local-sft-v1','mode':a.mode,'run_id':out.name,'status':'PREPARING','data_sha256':spec['dataset_sha256'],'rows':spec['dataset_rows'],'command':cmd,'source_commit':os.environ['SOURCE_GIT_COMMIT'],'image_digest':os.environ['TRAIN_IMAGE_DIGEST'],'versions':report['versions'],'window':auth,'started_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 def save(): (out/'run_manifest.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
 audit_path=out/'identity-zero-audit.jsonl'
 os.environ['T008_IDENTITY_ZERO_AUDIT']=str(audit_path)
 cfgpath=inp/'ablation/config.json'
 assert os.environ['T008_IDENTITY_ZERO_CONFIG']==str(cfgpath)
 acfg=json.loads(cfgpath.read_text());members=json.loads(cfgpath.with_name('membership.json').read_text())['members']
 assert sha(cfgpath.with_name('membership.json'))==acfg['membership_sha256']
 assert acfg['dataset_sha256']==spec['dataset_sha256']
 meta['identity_zero']={'config_sha256':sha(cfgpath),'plugin_sha256':sha(cfgpath.with_name('identity_zero.py')),'identity_rows':234,'all_zeroed_rows':295,'only_supervised_group':'general','labels_and_denominator_preserved':True}
 meta['gpu_before']=gpu_before
 save();task=None
 try:
  task=Task.init(project_name='reg/identity-sft',task_name=auth['run_id']+'-'+out.name,task_type=Task.TaskTypes.training,reuse_last_task_id=False,auto_connect_frameworks=False,auto_connect_arg_parser=False,output_uri=storage)
  meta['task_id']=task.id;meta['status']='TRAINING';save()
  for key in ['data_sha256','rows','source_commit','image_digest']:task.set_parameter('t008/'+key,meta[key])
  task.set_parameter('t008/command',cmd)
  remaining=(datetime.datetime.fromisoformat(auth['window_end_utc'])-datetime.datetime.now(datetime.timezone.utc)).total_seconds()-900
  if remaining<300:raise RuntimeError('Insufficient experiment time; leave UAT paused')
  with (out/'train.log').open('w') as f:
   result=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=min(remaining,1800 if a.mode=='smoke' else 5400))
  meta['training_exit_code']=result.returncode
  metrics=collect(out/'checkpoints');(out/'training-scalars.json').write_text(json.dumps({'scalars':metrics},indent=2)+'\n')
  if result.returncode:raise RuntimeError('Swift training failed; see train.log')
  if any(not math.isfinite(p['value']) for p in metrics if any(x in p['tag'] for x in ['loss','grad_norm'])):raise RuntimeError('Non-finite training metric')
  audit=[json.loads(line) for line in audit_path.read_text().splitlines()]
  assert audit and all(x['weighted_after']==(0 if x['zeroed'] else x['weighted_before']) for x in audit)
  assert all(x['num_items_in_batch']>0 for x in audit)
  if a.mode=='full':
   from collections import Counter
   assert len(audit)==1047 and sum(x['identity'] for x in audit)==234 and sum(x['zeroed'] for x in audit)==295
   assert Counter(x['key'] for x in audit)==Counter({k:v['multiplicity'] for k,v in members.items()})
   assert sum(x['valid_tokens'] for x in audit)==928890
   assert sum(x['weighted_after'] for x in audit)==917336
  for start in range(0,len(audit),16):
   group=audit[start:start+16]
   assert all(x['num_items_in_batch']==sum(y['valid_tokens'] for y in group) for x in group)
  meta['identity_zero_audit_verified']=True
  meta['identity_zero_audit']={'rows':len(audit),'identity_rows':sum(x['identity'] for x in audit),'zeroed_rows':sum(x['zeroed'] for x in audit),'valid_tokens':sum(x['valid_tokens'] for x in audit),'weighted_after':sum(x['weighted_after'] for x in audit),'sha256':sha(audit_path)}
  ck=latest_adapter(out/'checkpoints');state=json.loads((ck/'trainer_state.json').read_text());step=int(ck.name.split('-')[-1])
  if step!=state['global_step'] or step!=state['max_steps']:raise RuntimeError('Checkpoint is not terminal step')
  if a.mode=='smoke' and step!=3:raise RuntimeError('Smoke is not 3 steps')
  if a.mode=='full':verify_final_checkpoint(out/'checkpoints',ck)
  scope=verify_adapter_scope(ck,spec)
  meta.update(checkpoint=str(ck),global_step=step,epoch=state.get('epoch'),training_verified=True,adapter_scope=scope)
  package=out/'adapter.zip';meta['adapter_files']=zip_adapter(ck,package);meta['adapter_package_sha256']=sha(package)
  meta['status']='TRAINED_CANDIDATE' if a.mode=='full' else 'SMOKE_COMPLETE';meta['finished_at_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();save()
  # Upload is separable from successful training; never retrain to repair upload.
  try:
   report_to_existing_task(task,metrics)
   task.upload_artifact('training-log',artifact_object=str(out/'train.log'))
   task.upload_artifact('training-scalars',artifact_object=str(out/'training-scalars.json'))
   model=OutputModel(task=task,name=auth['run_id']+'-'+out.name,framework='pytorch');uri=model.update_weights(weights_filename=str(package),target_filename='adapter.zip',auto_delete_file=False,upload_uri=storage,async_enable=False)
   meta['clearml_output_model_id']=model.id;meta['clearml_model_uri']=uri
   registered=Model(model_id=model.id);validate_registered_model_uri(registered.url,storage)
   local=registered.get_local_copy(extract_archive=False,force_download=True)
   if not local or sha(local)!=meta['adapter_package_sha256']:raise RuntimeError('OutputModel SHA mismatch')
   meta['clearml_model_readback_sha256']=sha(local);meta['upload_status']='VERIFIED';save()
   task.upload_artifact('run-manifest',artifact_object=str(out/'run_manifest.json'))
  except Exception as exc:meta.update(upload_status='PENDING',upload_error=type(exc).__name__);save()
  task.close();print(json.dumps({k:meta.get(k) for k in ['status','task_id','global_step','upload_status','clearml_output_model_id']}))
 except BaseException as exc:
  meta.update(status='FAILED',error=type(exc).__name__+': '+str(exc));save()
  if task:
   try:task.mark_failed(status_reason=type(exc).__name__);task.close()
   except Exception:pass
  raise
if __name__=='__main__':main()
