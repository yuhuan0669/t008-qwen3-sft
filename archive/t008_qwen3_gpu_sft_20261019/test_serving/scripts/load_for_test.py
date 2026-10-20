"""Authorized test LoRA load; rollback original serving template on any failure."""
import datetime,json,pathlib,subprocess,time
ROOT=pathlib.Path(__file__).resolve().parents[1]
K=['kubectl','--context','lmas00-direct','--request-timeout=30s']
def command(*args):return subprocess.run(K+list(args),capture_output=True,text=True,check=True,timeout=45).stdout
def get(*args):return json.loads(command(*args,'-o','json'))
def event(stage,**values):
 r={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'stage':stage,**values}
 try:
  with (ROOT/'evidence/load-events.jsonl').open('a') as f:f.write(json.dumps(r,ensure_ascii=False)+'\n')
 except OSError:pass
 print(json.dumps(r,ensure_ascii=False),flush=True)
def down():
 command('-n','vllm','scale','deployment/vllm','--replicas=0')
 deadline=time.monotonic()+180
 while time.monotonic()<deadline:
  if not get('-n','vllm','get','pods','-l','app=vllm')['items']:return
  time.sleep(3)
 raise TimeoutError('vLLM drain timeout')
def up():
 command('-n','vllm','scale','deployment/vllm','--replicas=1')
 deadline=time.monotonic()+900
 while time.monotonic()<deadline:
  d=get('-n','vllm','get','deploy','vllm')
  if d['status'].get('readyReplicas')==1 and d['status'].get('observedGeneration',0)>=d['metadata']['generation']:
   p=subprocess.run(['/usr/bin/curl','--silent','--show-error','--max-time','15','--output','/dev/null','--write-out','%{http_code} %{ssl_verify_result}','https://vllm.10.140.17.125.nip.io/health'],capture_output=True,text=True)
   if p.returncode==0 and p.stdout=='200 0':return
  time.sleep(8)
 raise TimeoutError('vLLM test startup timeout')
changed=False
try:
 event('RESTARTING_FOR_AUTHORIZED_TEST');changed=True;down()
 command('-n','vllm','patch','deployment','vllm','--type=json','--patch-file',str(ROOT/'evidence/load-test-patch.json'))
 up();event('TEST_VLLM_READY')
 p=subprocess.run(['/usr/bin/curl','--silent','--show-error','--fail','--max-time','30','https://vllm.10.140.17.125.nip.io/v1/models'],capture_output=True,text=True,check=True)
 models=json.loads(p.stdout);ids=[x['id'] for x in models['data']]
 assert 'octacarbon-llm-sft-test' in ids and 'octa-carbon-v1' in ids
 (ROOT/'evidence/models.json').write_text(json.dumps(models,ensure_ascii=False,indent=2)+'\n')
 request={'model':'octacarbon-llm-sft-test','messages':[{'role':'user','content':'你叫什么名字？'}],'temperature':0,'max_tokens':128,'chat_template_kwargs':{'enable_thinking':False}}
 (ROOT/'evidence/single-request.json').write_text(json.dumps(request,ensure_ascii=False)+'\n')
 p=subprocess.run(['/usr/bin/curl','--silent','--show-error','--fail','--max-time','90','-H','Content-Type: application/json','--data-binary','@'+str(ROOT/'evidence/single-request.json'),'https://vllm.10.140.17.125.nip.io/v1/chat/completions'],capture_output=True,text=True,check=True)
 response=json.loads(p.stdout);assert response['choices'][0]['message']['content']
 (ROOT/'evidence/single-response.json').write_text(json.dumps(response,ensure_ascii=False,indent=2)+'\n')
 pod=get('-n','vllm','get','pods','-l','app=vllm');(ROOT/'evidence/serving-pods.json').write_text(json.dumps(pod,indent=2)+'\n')
 dep=get('-n','vllm','get','deployment','vllm');(ROOT/'evidence/serving-deployment.json').write_text(json.dumps(dep,indent=2)+'\n')
 result={'status':'TEST_LOADED','test_model_id':'octacarbon-llm-sft-test','baseline_model_id':'octa-carbon-v1','base_preserved':True,'merged_weights':False,'quality_accepted':False,'single_api_canary_ok':True,'response':response['choices'][0]['message']['content']}
 (ROOT/'evidence/result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');event('TEST_LOADED',**result)
except BaseException as exc:
 event('TEST_LOAD_FAILED',error=type(exc).__name__+': '+str(exc))
 if changed:
  event('ROLLING_BACK_ORIGINAL');down()
  command('-n','vllm','patch','deployment','vllm','--type=json','--patch-file',str(ROOT/'evidence/rollback-patch.json'))
  up();event('ORIGINAL_VLLM_RESTORED')
 raise
