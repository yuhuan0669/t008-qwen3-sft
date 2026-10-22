"""Archive an already completed run; never trains. --clearml explicitly uploads."""
from pathlib import Path
import argparse,datetime,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parent/'support'))
from run_identity import latest_adapter,verify_final_checkpoint,zip_adapter,sha,clearml_storage_uri,validate_registered_model_uri
from collect_metrics import collect,report_to_existing_task

def main():
 a=argparse.ArgumentParser();a.add_argument('--run-output',type=Path,required=True);a.add_argument('--name',required=True);a.add_argument('--clearml',action='store_true');x=a.parse_args();d=x.run_output
 run=json.loads((d/'manual-run.json').read_text());assert run['status']=='PROCESS_EXITED' and run['exit_code']==0
 ck=latest_adapter(d/'checkpoints');verify_final_checkpoint(d/'checkpoints',ck);s=json.loads((ck/'trainer_state.json').read_text());assert s['global_step']==s['max_steps'];assert (s['global_step']==3 if run['mode']=='smoke' else abs(s['epoch']-float(run['epochs']))<.002)
 package=d/'adapter.zip';files=zip_adapter(ck,package);points=collect(d/'checkpoints');(d/'training-scalars.json').write_text(json.dumps({'scalars':points},indent=2)+'\n')
 m={'name':x.name,'checkpoint':str(ck),'global_step':s['global_step'],'epoch':s['epoch'],'data_sha256':run['data_sha256'],'command':run['command'],'adapter_files':files,'adapter_package_sha256':sha(package),'training_verified':True,'upload_status':'NOT_REQUESTED'}
 def save():(d/'archive-manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
 save()
 if x.clearml:
  import os
  from clearml import Task,OutputModel,Model
  task=None
  try:
   storage=clearml_storage_uri(os.environ['CLEARML_FILES_HOST']);task=Task.init(project_name='reg/identity-sft',task_name=x.name,task_type=Task.TaskTypes.training,reuse_last_task_id=False,auto_connect_frameworks=False,auto_connect_arg_parser=False,output_uri=storage);m['task_id']=task.id;save();task.connect(run,name='manual-run');report_to_existing_task(task,points)
   for f in ['train.log','training-scalars.json','manual-run.json']:task.upload_artifact(f,artifact_object=str(d/f))
   model=OutputModel(task=task,name=x.name,framework='pytorch');uri=model.update_weights(weights_filename=str(package),target_filename='adapter.zip',auto_delete_file=False,upload_uri=storage,async_enable=False);m['output_model_id']=model.id;registered=Model(model_id=model.id);validate_registered_model_uri(registered.url,storage);assert sha(Path(registered.get_local_copy(extract_archive=False,force_download=True)))==m['adapter_package_sha256'];m['upload_status']='VERIFIED';save();task.upload_artifact('archive-manifest',artifact_object=str(d/'archive-manifest.json'))
  except Exception as e:m.update(upload_status='FAILED',upload_error=type(e).__name__);save();raise
  finally:
   if task:task.close()
 print(json.dumps(m,ensure_ascii=False))
if __name__=='__main__':main()
