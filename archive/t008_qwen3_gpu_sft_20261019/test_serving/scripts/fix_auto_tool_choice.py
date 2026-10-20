"""Fix user-reported WebUI tool_choice=auto compatibility; preserve test LoRA."""
import datetime,json,pathlib,subprocess,time
ROOT=pathlib.Path(__file__).resolve().parents[1]
K=['kubectl','--context','lmas00-direct','--request-timeout=30s']
def command(*args):
 return subprocess.run(K+list(args),capture_output=True,text=True,check=True,timeout=45).stdout
def get(*args):return json.loads(command(*args,'-o','json'))
def save(name,obj):
 (ROOT/'evidence'/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def event(stage,**values):
 r={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'stage':stage,**values}
 with (ROOT/'evidence/auto-tool-events.jsonl').open('a') as f:f.write(json.dumps(r,ensure_ascii=False)+'\n')
 print(json.dumps(r,ensure_ascii=False),flush=True)
def down():
 command('-n','vllm','scale','deployment/vllm','--replicas=0')
 end=time.monotonic()+180
 while time.monotonic()<end:
  if not get('-n','vllm','get','pods','-l','app=vllm')['items']:return
  time.sleep(3)
 raise TimeoutError('vLLM drain timeout')
def up():
 command('-n','vllm','scale','deployment/vllm','--replicas=1')
 end=time.monotonic()+900
 while time.monotonic()<end:
  d=get('-n','vllm','get','deploy','vllm')
  if d['status'].get('readyReplicas')==1 and d['status'].get('observedGeneration',0)>=d['metadata']['generation']:
   p=subprocess.run(['/usr/bin/curl','--silent','--show-error','--max-time','15','--output','/dev/null','--write-out','%{http_code} %{ssl_verify_result}','https://vllm.10.140.17.125.nip.io/health'],capture_output=True,text=True)
   if p.returncode==0 and p.stdout=='200 0':return
  time.sleep(8)
 raise TimeoutError('vLLM ready timeout')
before=get('-n','vllm','get','deploy','vllm')
(ROOT/'private/auto-tool-before.json').write_text(json.dumps(before,indent=2)+'\n')
template=before['spec']['template'];args=template['spec']['containers'][0]['args']
assert '--enable-lora' in args and '--enable-auto-tool-choice' not in args
uid=before['metadata']['uid']
patch=[{'op':'test','path':'/metadata/uid','value':uid},
 {'op':'test','path':'/spec/template','value':template},
 {'op':'replace','path':'/spec/template/spec/containers/0/args','value':args+['--enable-auto-tool-choice','--tool-call-parser','hermes']}]
save('auto-tool-patch.json',patch)
save('auto-tool-rollback.json',[{'op':'test','path':'/metadata/uid','value':uid},{'op':'replace','path':'/spec/template','value':template}])
save('auto-tool-parser-verification.json',{'vllm_version':'0.25.1','installed_parser':'vllm/tool_parsers/hermes_tool_parser.py','registered_name':'hermes','model_template_tool_tags':['<tool_call>','</tool_call>'],'verification':'Read installed parser, registry and actual /models/tokenizer_config.json before patch.'})
changed=False
try:
 event('RESTART_FOR_WEBUI_AUTO_TOOL_COMPATIBILITY');changed=True;down()
 command('-n','vllm','patch','deployment','vllm','--type=json','--patch-file',str(ROOT/'evidence/auto-tool-patch.json'))
 up();event('VLLM_READY')
 request={'model':'octacarbon-llm-sft-test','messages':[{'role':'user','content':'你好，请简短回复。'}],
  'tools':[{'type':'function','function':{'name':'get_current_weather','description':'Get weather only when asked for weather.','parameters':{'type':'object','properties':{'city':{'type':'string'}},'required':['city']}}}],
  'tool_choice':'auto','temperature':0,'max_tokens':64,'chat_template_kwargs':{'enable_thinking':False}}
 save('auto-tool-single-request.json',request)
 p=subprocess.run(['/usr/bin/curl','--silent','--show-error','--fail-with-body','--max-time','90','-H','Content-Type: application/json','--data-binary','@'+str(ROOT/'evidence/auto-tool-single-request.json'),'https://vllm.10.140.17.125.nip.io/v1/chat/completions'],capture_output=True,text=True)
 (ROOT/'evidence/auto-tool-single-response.json').write_text(p.stdout+'\n')
 p.check_returncode();response=json.loads(p.stdout)
 assert response['choices'][0]['message'].get('content') or response['choices'][0]['message'].get('tool_calls')
 save('auto-tool-serving-deployment.json',get('-n','vllm','get','deployment','vllm'))
 save('auto-tool-serving-pods.json',get('-n','vllm','get','pods','-l','app=vllm'))
 save('auto-tool-result.json',{'status':'FIXED','flags':['--enable-auto-tool-choice','--tool-call-parser','hermes'],'single_tool_choice_auto_request':'HTTP_200','tool_execution_performed':False,'baseline_preserved':True,'test_model_id':'octacarbon-llm-sft-test'})
 event('AUTO_TOOL_CHOICE_FIXED',canary_requests=1)
except BaseException as exc:
 event('FIX_FAILED',error=type(exc).__name__+': '+str(exc))
 if changed:
  down();command('-n','vllm','patch','deployment','vllm','--type=json','--patch-file',str(ROOT/'evidence/auto-tool-rollback.json'));up();event('PRIOR_TEST_SERVING_RESTORED')
 raise
