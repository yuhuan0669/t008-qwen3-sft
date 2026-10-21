"""Evaluator-only EvalScope Native runtime. Input payload via stdin; no training-side data export."""
import os,sys,json,pathlib,datetime,time,threading,hashlib,copy,inspect,re,itertools
os.umask(0o077)
sys.path.insert(0,'/tmp/t008-private-evaluation/deps')
os.environ['NLTK_DATA']='/tmp/t008-private-evaluation/nltk_data'
import langdetect
langdetect.DetectorFactory.seed=42
import evalscope
from evalscope import TaskConfig,run_task
from evalscope.api.benchmark import BenchmarkMeta,DefaultDataAdapter
from evalscope.api.registry import register_benchmark,BENCHMARK_REGISTRY
from evalscope.api.dataset import Sample,MemoryDataset
from evalscope.api.messages import ChatMessageUser,ChatMessageSystem
from evalscope.api.model import ModelOutput
from evalscope.api.metric.scorer import Score
from evalscope.api.evaluator.inference_result import InferenceResult
from evalscope.benchmarks.ifeval.ifeval_adapter import IFEvalAdapter
from evalscope.benchmarks.gsm8k.gsm8k_adapter import GSM8KAdapter
from evalscope.benchmarks.ifeval.utils import process_results
assert evalscope.__version__=='1.9.1'
PAYLOAD=json.load(sys.stdin)
ROOT=pathlib.Path(PAYLOAD['remote_output']);ROOT.mkdir(parents=True,exist_ok=True,mode=0o700);ROOT.chmod(0o700)
FIXTURE=PAYLOAD.get('fixture',False)
if not FIXTURE and not PAYLOAD.get('execution_signal'):raise RuntimeError('Missing explicit execution signal')
FIXTURE_API=bool(FIXTURE and PAYLOAD.get('fixture_api'))
CURRENT={};LOCK=threading.RLock();CACHE={};COUNTS={'generated_turns':0,'reused_turns':0,'completed_cases':0}
def emit(kind,**kwargs):
 print('T008_PROGRESS '+json.dumps({'event':kind,**kwargs}),flush=True)
def writejson(p,x):
 temp=p.with_suffix(p.suffix+'.tmp');temp.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n');temp.replace(p)
def append(p,x):
 with LOCK:
  with p.open('a') as f:f.write(json.dumps(x,ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno())
def clean_body(output):
 text=output.completion or '';reason=None
 if re.match(r'^\s*<think>',text):
  if '</think>' not in text:reason='unclosed_thinking';body=''
  else:body=text.split('</think>',1)[1].strip()
 elif '</think>' in text and '<think>' not in text:
  body=text.split('</think>',1)[1].strip()
 else:body=text.strip()
 if output.error:reason='model_error'
 stop=output.choices[0].stop_reason if output.choices else None
 if stop in ('max_tokens','length','model_length','context_length'):reason='truncated'
 if not output.choices:reason=reason or 'missing_choice'
 if not body:reason=reason or 'empty_body'
 return body,reason,str(stop)
def deadline_guard():
 if not FIXTURE:
  end=datetime.datetime.fromisoformat(PAYLOAD['deadline_utc'].replace('Z','+00:00'))
  if datetime.datetime.now(datetime.timezone.utc)+datetime.timedelta(seconds=PAYLOAD.get('request_timeout',600))>=end:raise RuntimeError('AUTHORIZED_WINDOW_LAST_REQUEST_RESERVE_REACHED')
class PrivateNativeMixin:
 def load_dataset(self):
  records=CURRENT['records']; samples=[]
  for i,r in enumerate(records):
   if CURRENT['suite']=='specialized':s=self.record_to_sample(r)
   else:
    s=self.record_to_sample(r['native']);s.metadata['t008_record']=copy.deepcopy(r)
   s.id=i+1;s.metadata['t008_case_id']=r['id'];s.metadata['t008_group']=CURRENT['group']
   samples.append(s)
  self.test_dataset={'default':MemoryDataset(samples,name=self.name)};self.fewshot_dataset=None
  self._post_process_samples()
  return self.test_dataset
 def _on_inference(self,model,sample):
  messages=list(sample.input);cid=sample.metadata['t008_case_id'];outputs=[];trace=[]
  turns=sample.metadata.get('turns');n=len(turns) if turns else 1
  for i in range(n):
   if i:messages.append(ChatMessageUser(content=turns[i]['user']))
   key=f'{cid}:{i}'
   with LOCK:cached=CACHE.get(key)
   if cached is not None:
    out=ModelOutput.model_validate(cached['model_output']);row=cached
    with LOCK:COUNTS['reused_turns']+=1
   else:
    deadline_guard();start=time.monotonic()
    try:out=model.generate(input=messages,tools=sample.tools)
    except Exception as exc:
     # Transport errors are recorded once. No automatic retry or replacement sample.
     out=ModelOutput.from_content(model=model.name,content='',stop_reason='stop',error=f'{type(exc).__name__}: {exc}')
    body,reason,stop=clean_body(out)
    row={'case_id':cid,'turn':i,'group':CURRENT['group'],'elapsed_seconds':time.monotonic()-start,
         'model_output':out.model_dump(mode='json'),'body':body,'protocol_error':reason,'stop_reason':stop}
    append(CURRENT['turn_file'],row)
    with LOCK:CACHE[key]=row;COUNTS['generated_turns']+=1
   outputs.append(out);trace.append(row);messages.append(out.message)
   if row['protocol_error']:break
  sample.metadata['t008_turn_results']=trace
  sample.metadata['t008_all_turns_complete']=len(trace)==n
  sample.metadata['t008_protocol_valid']=len(trace)==n and all(x['protocol_error'] is None for x in trace)
  final=outputs[-1].model_copy(deep=True)
  if not final.choices:final=ModelOutput.from_content(model=model.name,content='',error='missing_choice')
  if final.choices:
   final.choices[0].message.content=trace[-1]['body']
   # Native task output is the parsed final body; full raw output is retained per turn.
   final.metadata={**(final.metadata or {}),'t008_raw_ledger':str(CURRENT['turn_file']),'t008_protocol_valid':sample.metadata['t008_protocol_valid']}
  with LOCK:
   COUNTS['completed_cases']+=1
   if COUNTS['completed_cases']%20==0:emit('progress',group=CURRENT['group'],**COUNTS)
  return InferenceResult(output=final,messages=messages,trace={'t008_turn_count':len(trace)})
 def filter_prediction(self,prediction,task_state):
  # Native model content has already been parsed once; the rubric evaluates final body only.
  return self.extract_answer(prediction,task_state)

@register_benchmark(BenchmarkMeta(name='t008_specialized_formal',pretty_name='T008 private specialized',description='Frozen specialized dialogue protocol; content acceptance requires private rubric review.',dataset_id='t008_private_memory',subset_list=['default'],eval_split='test',few_shot_num=0,prompt_template='',metric_list=['protocol_valid','manual_review_pending']))
class SpecializedAdapter(PrivateNativeMixin,DefaultDataAdapter):
 def record_to_sample(self,r):
  return Sample(input=[ChatMessageUser(content=r['turns'][0]['user'])],target='',metadata=copy.deepcopy(r))
 def match_score(self,original_prediction,filtered_prediction,reference,task_state):
  ok=task_state.metadata['t008_protocol_valid']
  return Score(value={'protocol_valid':int(ok),'manual_review_pending':int(ok)},prediction=original_prediction,extracted_prediction=filtered_prediction,
               metadata={'content_score':None if ok else 0,'review_status':'PENDING_CONTENT_REVIEW' if ok else 'PROTOCOL_FAILURE','not_acceptance_score':True},main_score_name='protocol_valid')

ifeval_meta=copy.deepcopy(BENCHMARK_REGISTRY.get('ifeval'));ifeval_meta.name='t008_ifeval_formal';ifeval_meta.dataset_id='t008_private_memory';ifeval_meta.subset_list=['default'];ifeval_meta.few_shot_num=0
@register_benchmark(ifeval_meta)
class PrivateIFEval(PrivateNativeMixin,IFEvalAdapter):
 def match_score(self,original_prediction,filtered_prediction,reference,task_state):
  metrics={k:0 for k in ('prompt_level_strict','inst_level_strict','prompt_level_loose','inst_level_loose')};error=None
  if task_state.metadata['t008_protocol_valid']:
   try:metrics=process_results(task_state.metadata,[filtered_prediction])
   except Exception as e:error=f'{type(e).__name__}: {e}'
  return Score(value=metrics,prediction=original_prediction,extracted_prediction=filtered_prediction,metadata={'scoring_error':error,'protocol_valid':task_state.metadata['t008_protocol_valid']},main_score_name='prompt_level_strict')

gsm_meta=copy.deepcopy(BENCHMARK_REGISTRY.get('gsm8k'));gsm_meta.name='t008_gsm8k_formal';gsm_meta.dataset_id='t008_private_memory';gsm_meta.subset_list=['default'];gsm_meta.few_shot_num=0
@register_benchmark(gsm_meta)
class PrivateGSM(PrivateNativeMixin,GSM8KAdapter):
 def match_score(self,original_prediction,filtered_prediction,reference,task_state):
  if not task_state.metadata['t008_protocol_valid']:
   return Score(value={'acc':0},prediction=original_prediction,extracted_prediction=filtered_prediction,metadata={'protocol_valid':False},main_score_name='acc')
  return super().match_score(original_prediction,filtered_prediction,reference,task_state)

def gen_config(mode,seed):
 g=PAYLOAD['protocol']['modes'][mode]
 return {'temperature':g['temperature'],'top_p':g['top_p'],'top_k':g['top_k'],'max_tokens':g['max_tokens'],'seed':seed,'timeout':PAYLOAD.get('request_timeout',600),'retries':1,'stream':False,
         'extra_body':{'min_p':0,'chat_template_kwargs':{'enable_thinking':g['enable_thinking']}}}
def groups():
 if FIXTURE:return [('A','nonthinking',42,s) for s in ('specialized','ifeval','gsm8k')]
 if PAYLOAD['phase']=='public-development':return [(PAYLOAD['development_condition'],mode,42,s) for mode in ('nonthinking','thinking') for s in ('ifeval','gsm8k')]
 phase=PAYLOAD['phase'];conditions=['A','B'] if phase=='baseline' else ['C_new','D_new'];g=[]
 for c in conditions:
  for mode in ('nonthinking','thinking'):
   for seed in ([42] if phase=='baseline' else [42,43,44]):g.append((c,mode,seed,'specialized'))
   if c in ('A','C_new'):
    for s in ('ifeval','gsm8k'):g.append((c,mode,42,s))
 return g

def main():
 fixture_server=None
 if FIXTURE_API:
  from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
  class SyntheticHandler(BaseHTTPRequestHandler):
   def log_message(self,*args):pass
   def do_POST(self):
    req=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
    assert req['seed']==42 and req['top_k']==20 and req['min_p']==0 and req['chat_template_kwargs']['enable_thinking'] is False
    assert 'required' not in json.dumps(req['messages'])
    append(ROOT/'fixture-api-requests.jsonl',req)
    reply={'id':'synthetic-id','object':'chat.completion','created':0,'model':'CPU_SYNTHETIC','choices':[{'index':0,'message':{'role':'assistant','content':'synthetic \\boxed{7}'},'finish_reason':'stop'}],'usage':{'prompt_tokens':10,'completion_tokens':5,'total_tokens':15}}
    data=json.dumps(reply).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
  fixture_server=ThreadingHTTPServer(('127.0.0.1',0),SyntheticHandler)
  threading.Thread(target=fixture_server.serve_forever,daemon=True).start()
  PAYLOAD['endpoint']=f'http://127.0.0.1:{fixture_server.server_port}/v1'
 total=0;summary=[]
 if (ROOT/'run-binding.json').exists():
  if json.loads((ROOT/'run-binding.json').read_text())!=PAYLOAD['binding']:raise RuntimeError('RESUME_BINDING_MISMATCH')
 else:writejson(ROOT/'run-binding.json',PAYLOAD['binding'])
 if not FIXTURE:
  import urllib.request
  models=json.load(urllib.request.urlopen(PAYLOAD['endpoint'].rstrip('/')+'/models',timeout=20))
  if PAYLOAD['model'] not in [x['id'] for x in models['data']]:raise RuntimeError('SERVED_MODEL_NOT_ADVERTISED')
  writejson(ROOT/'endpoint-model-list.json',models)
 for condition,mode,seed,suite in groups():
  deadline_guard();group=f'{condition}__{mode}__seed{seed}__{suite}';folder=ROOT/group;folder.mkdir(mode=0o700,exist_ok=True)
  if suite=='specialized':records=[r for r in PAYLOAD['specialized'] if seed==42 or r['category']=='identity']
  else:records=[r for r in PAYLOAD['public'] if r['benchmark']==suite]
  CURRENT.clear();CURRENT.update(group=group,suite=suite,records=records,turn_file=folder/'turn-results.jsonl')
  CACHE.clear()
  if CURRENT['turn_file'].exists():
   for line in CURRENT['turn_file'].read_text().splitlines():
    row=json.loads(line);key=f"{row['case_id']}:{row['turn']}"
    if key in CACHE:raise RuntimeError('DUPLICATE_STORED_TURN_NO_BEST_OF_SELECTION')
    CACHE[key]=row
  name={'specialized':'t008_specialized_formal','ifeval':'t008_ifeval_formal','gsm8k':'t008_gsm8k_formal'}[suite]
  dataset_args={name:{'few_shot_num':0,'shuffle':False,'system_prompt':PAYLOAD['system'] if condition in ('B','D_new') else None}}
  args={'model':PAYLOAD['model'],'eval_type':'mock_llm' if FIXTURE and not FIXTURE_API else 'openai_api','api_url':PAYLOAD.get('endpoint'),'api_key':'EMPTY','model_args':{'max_retries':0} if not FIXTURE or FIXTURE_API else {'custom_outputs':[ModelOutput.from_content(model='CPU_SYNTHETIC',content='synthetic \\boxed{7}') for _ in range(4)]},
        'datasets':[name],'dataset_args':dataset_args,'generation_config':gen_config(mode,seed),'seed':seed,'eval_batch_size':1 if FIXTURE else PAYLOAD.get('concurrency',4),
        'work_dir':str(folder/'evalscope'),'no_timestamp':True,'ignore_errors':False,'analysis_report':False,'collect_perf':True,'enable_progress_tracker':False}
  emit('group_start',group=group,cases=len(records));result=run_task(TaskConfig(**args))
  # All source rows are fixed and loaded from memory; never resolve external datasets.
  group_summary={'group':group,'cases':len(records),'turns_persisted':len(CACHE),'technical_protocol_failures':sum(1 for r in records if any(CACHE.get(f"{r['id']}:{i}",{}).get('protocol_error') for i in range(len(r.get('turns',[0]))))),
                 'evalscope_output':str(folder/'evalscope'),'content_review_pending':suite=='specialized'}
  writejson(folder/'group-complete.json',group_summary);summary.append(group_summary);total+=len(records)
  writejson(ROOT/'progress-summary.json',{'groups':summary,'completed_case_conditions':total,'counts':COUNTS})
  emit('group_complete',**group_summary)
 expected=3 if FIXTURE else (80 if PAYLOAD['phase']=='public-development' else (880 if PAYLOAD['phase']=='baseline' else 1200))
 assert total==expected,(total,expected)
 if FIXTURE:
  assert all(g['technical_protocol_failures']==0 for g in summary), 'SYNTHETIC_PROTOCOL_FAILURE'
  assert sum(g['turns_persisted'] for g in summary)==4, 'SYNTHETIC_MULTITURN_INCOMPLETE'
 writejson(ROOT/'run-complete.json',{'phase':PAYLOAD['phase'],'fixture':FIXTURE,'case_conditions':total,'counts':COUNTS,'groups':summary,'real_inference_executed':not FIXTURE})
 if fixture_server:fixture_server.shutdown()
 emit('run_complete',phase=PAYLOAD['phase'],fixture=FIXTURE,case_conditions=total,**COUNTS)
if __name__=='__main__':main()
