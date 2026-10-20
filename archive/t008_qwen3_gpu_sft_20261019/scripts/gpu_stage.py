"""Run one already-authorized stage, record GPU telemetry, preserve wrapper exit."""
import datetime,json,pathlib,subprocess,sys,threading,time
mode=sys.argv[1];assert mode in ('smoke','full')
root=pathlib.Path('/runwork')
def gpu():
 def query(flag):
  p=subprocess.run(['nvidia-smi',flag,'--format=csv,noheader,nounits'],capture_output=True,text=True,check=True)
  return p.stdout.strip().splitlines()
 return {'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'gpu':query('--query-gpu=uuid,name,memory.total,memory.used,utilization.gpu'),
         'processes':query('--query-compute-apps=pid,process_name,used_memory')}
before=gpu();(root/(mode+'-gpu-before.json')).write_text(json.dumps(before,indent=2)+'\n')
if before['processes']:raise RuntimeError('GPU has existing compute processes; refuse shared training')
p=subprocess.Popen(['bash','/input/code/train_identity.sh',mode],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
def forward():
 with (root/(mode+'-wrapper.log')).open('w') as f:
  for line in p.stdout:
   f.write(line);f.flush();print(line,end='',flush=True)
reader=threading.Thread(target=forward);reader.start()
with (root/(mode+'-gpu-telemetry.jsonl')).open('w') as f:
 while p.poll() is None:
  f.write(json.dumps(gpu())+'\n');f.flush()
  for _ in range(10):
   if p.poll() is not None:break
   time.sleep(1)
code=p.wait();reader.join()
(root/(mode+'-stage-exit.json')).write_text(json.dumps({'exit_code':code,'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()},indent=2)+'\n')
sys.exit(code)
