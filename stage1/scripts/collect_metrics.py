"""Read TensorBoard scalar files once after exit; no ClearML connection in collect mode."""
from pathlib import Path
import json,argparse

def collect(logdir):
 from tensorboard.backend.event_processing.event_accumulator import EventAccumulator
 points={}
 for p in sorted(Path(logdir).rglob('events.out.tfevents.*')):
  acc=EventAccumulator(str(p),size_guidance={'scalars':0});acc.Reload()
  for tag in acc.Tags()['scalars']:
   # Restrict to training metrics; never collect text/evaluation question artifacts.
   if not tag.startswith(('train/','train_')):continue
   for e in acc.Scalars(tag):points[(tag,e.step)]={'tag':tag,'step':e.step,'value':e.value,'wall_time':e.wall_time}
 return [points[k] for k in sorted(points)]

def report_to_existing_task(task,points):
 logger=task.get_logger()
 for p in points:logger.report_scalar(title='training',series=p['tag'],iteration=p['step'],value=p['value'])

def main():
 p=argparse.ArgumentParser();p.add_argument('--logdir',required=True);p.add_argument('--out',required=True);a=p.parse_args()
 out=Path(a.out)
 if out.exists():raise FileExistsError(out)
 data=collect(a.logdir);out.write_text(json.dumps({'scalars':data,'mode':'local_export_only','clearml_task_created':False},indent=2)+'\n')
 print(json.dumps({'scalar_points':len(data)}))
if __name__=='__main__':main()
