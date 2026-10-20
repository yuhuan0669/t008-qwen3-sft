import json,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parent
for thinking in (True,False):
 label='thinking' if thinking else 'nonthinking'
 request={'model':'octacarbon-llm-sft-test','messages':[{'role':'user','content':'北京的碳排放系数是多少？'}],'temperature':0.6,'top_p':0.95,'top_k':20,'max_tokens':2048,'stream':True,'stream_options':{'include_usage':True},'chat_template_kwargs':{'enable_thinking':thinking}}
 path=ROOT/'evidence'/('direct-'+label+'-request.json');path.write_text(json.dumps(request,ensure_ascii=False)+'\n')
 p=subprocess.run(['/usr/bin/curl','--silent','--show-error','--fail-with-body','--max-time','120','-H','Content-Type: application/json','--data-binary','@'+str(path),'https://vllm.10.140.17.125.nip.io/v1/chat/completions'],capture_output=True,text=True)
 (ROOT/'private'/('direct-'+label+'.sse')).write_text(p.stdout)
 summary={'thinking':thinking,'http_success':p.returncode==0,'inference_requests':1,'reasoning_chars':0,'content_chars':0,'finish_reason':None,'usage':None,'tool_call_deltas':0,'done_marker':'[DONE]' in p.stdout};content=[]
 for line in p.stdout.splitlines():
  if not line.startswith('data: ') or '[DONE]' in line:continue
  try:r=json.loads(line[6:])
  except ValueError:continue
  if r.get('usage'):summary['usage']=r['usage']
  for c in r.get('choices',[]):
   if c.get('finish_reason'):summary['finish_reason']=c['finish_reason'];summary['stop_reason']=c.get('stop_reason')
   d=c.get('delta',{});summary['reasoning_chars']+=len(d.get('reasoning',d.get('reasoning_content','')) or '')
   content.append(d.get('content') or '')
   if d.get('tool_calls'):summary['tool_call_deltas']+=1
 summary['content_chars']=len(''.join(content));summary['answer']=''.join(content)
 (ROOT/'evidence'/('direct-'+label+'-summary.json')).write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');print(json.dumps(summary,ensure_ascii=False),flush=True)
