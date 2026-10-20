import copy,datetime,json,pathlib,subprocess,time
R=pathlib.Path(__file__).resolve().parent
K=['kubectl','--context','lmas00-direct','--request-timeout=30s']
def cmd(*a):return subprocess.run(K+list(a),capture_output=True,text=True,check=True,timeout=45).stdout
def get(*a):return json.loads(cmd(*a,'-o','json'))
def save(n,v):(R/'evidence'/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def event(n):
 print(datetime.datetime.now(datetime.timezone.utc).isoformat(),n,flush=True)
def down():
 cmd('-n','vllm','scale','deployment/vllm','--replicas=0')
 deadline=time.monotonic()+180
 while time.monotonic()<deadline:
  if not get('-n','vllm','get','pods','-l','app=vllm')['items']:return
  time.sleep(3)
 raise TimeoutError('Pod drain timed out')
def ready():
 cmd('-n','vllm','scale','deployment/vllm','--replicas=1')
 deadline=time.monotonic()+900
 while time.monotonic()<deadline:
  d=get('-n','vllm','get','deploy','vllm')
  if d['status'].get('readyReplicas')==1 and d['status'].get('observedGeneration',0)>=d['metadata']['generation']:
   p=subprocess.run(['/usr/bin/curl','--fail','--silent','--show-error','--max-time','15','--output','/dev/null','--write-out','%{http_code} %{ssl_verify_result}','https://vllm.10.140.17.125.nip.io/health'],capture_output=True,text=True)
   if p.returncode==0 and p.stdout=='200 0':return
  time.sleep(8)
 raise TimeoutError('Ready/health timed out')
before=json.loads((R/'private/before.json').read_text());original=before['spec']['template'];target=copy.deepcopy(original);c=target['spec']['containers'][0];a=c['args'];new=[];i=0
while i<len(a):
 if a[i]=='--enable-lora':i+=1;continue
 if a[i] in ('--max-lora-rank','--lora-modules'):i+=2;continue
 new.append(a[i]);i+=1
c['args']=new;c['volumeMounts']=[m for m in c['volumeMounts'] if m['mountPath']!='/adapters/octacarbon-llm-sft-test']
assert '--enable-auto-tool-choice' in new and '--tool-call-parser' in new
assert any(m.get('subPath')=='released/qwen3-8b-baseline/model' and m['readOnly'] for m in c['volumeMounts'])
patch=[{'op':'test','path':'/metadata/uid','value':before['metadata']['uid']},{'op':'test','path':'/spec/template','value':original},{'op':'replace','path':'/spec/template','value':target}]
save('patch.json',patch);save('rollback.json',[{'op':'test','path':'/metadata/uid','value':before['metadata']['uid']},{'op':'replace','path':'/spec/template','value':original}])
changed=False
try:
 event('SWITCHING_TO_UNFINETUNED_BASELINE');changed=True;down()
 cmd('-n','vllm','patch','deployment','vllm','--type=json','--patch-file',str(R/'evidence/patch.json'))
 ready()
 p=subprocess.run(['/usr/bin/curl','--fail','--silent','--show-error','--max-time','30','https://vllm.10.140.17.125.nip.io/v1/models'],capture_output=True,text=True,check=True);models=json.loads(p.stdout);ids=[x['id'] for x in models['data']];assert ids==['octa-carbon-v1'],ids
 d=get('-n','vllm','get','deployment','vllm');assert d['spec']['template']==target;save('models.json',models)
 save('result.json',{'status':'UNFINETUNED_BASELINE_READY','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'model_id':'octa-carbon-v1','model_path':'released/qwen3-8b-baseline/model','lora_enabled':False,'ready_replicas':d['status']['readyReplicas'],'https_health':200,'tls_verified':True,'inference_tests':0,'training_started':False,'candidate_artifact_preserved':True,'args':new});event('BASELINE_READY')
except BaseException:
 if changed:
  event('ROLLBACK_PREVIOUS_SERVING');down();cmd('-n','vllm','patch','deployment','vllm','--type=json','--patch-file',str(R/'evidence/rollback.json'));ready()
 raise
