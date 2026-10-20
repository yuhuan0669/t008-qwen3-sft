"""Mirror existing SFT metrics to its existing ClearML Task. No train/model calls."""
import ast,datetime,json,math,os,pathlib,time
os.environ['CUDA_VISIBLE_DEVICES']=''
from clearml import Task
root=pathlib.Path('/runwork');run=root/'outputs/full'
manifest=json.loads((run/'run_manifest.json').read_text());task_id=manifest['clearml_task_id']
assert task_id=='97ac5246ae9c43d9aa65ee2ac4c2aaef'
task=Task.get_task(task_id=task_id);logger=task.get_logger();last=0
summary={'task_id':task_id,'source':'existing Full train.log','new_tasks_created':False,'training_restarted':False,'points_synced':0}
while True:
 text=(run/'train.log').read_text(errors='replace')
 for line in text.replace('\r','\n').splitlines():
  if 'global_step/max_steps' not in line:continue
  try:d=ast.literal_eval(line.strip())
  except (ValueError,SyntaxError):continue
  step,total=map(int,d['global_step/max_steps'].split('/'))
  if step<=last:continue
  for key in ('loss','train_loss','grad_norm','learning_rate','token_acc','epoch','memory(GiB)'):
   if key in d:
    try:value=float(d[key])
    except (TypeError,ValueError):continue
    if math.isfinite(value):logger.report_scalar(title='SFT Training',series=key,value=value,iteration=step)
  logger.report_scalar(title='SFT Progress',series='optimizer_step',value=step,iteration=step)
  percent=int(100*step/total);task.set_progress(percent)
  logger.report_text(f"SFT {step}/{total} ({percent}%) | loss={d.get('loss',d.get('train_loss'))} | epoch={d.get('epoch')} | remaining={d.get('remaining_time')}",print_console=False)
  task.flush(wait_for_uploads=True)
  last=step;summary.update(points_synced=summary['points_synced']+1,last_optimizer_step=step,total_optimizer_steps=total,progress_percent=percent,updated_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
  (root/'clearml-progress-sync.json').write_text(json.dumps(summary,indent=2)+'\n')
  print(json.dumps(summary),flush=True)
 current=json.loads((run/'run_manifest.json').read_text())
 if current.get('status')=='FAILED':break
 if current.get('clearml_model_readback_sha256') and current.get('clearml_model_readback_sha256')==current.get('adapter_package_sha256'):
  task.set_progress(100);task.flush(wait_for_uploads=True);break
 time.sleep(8)
# This observer must never close/mark the actual training Task.
