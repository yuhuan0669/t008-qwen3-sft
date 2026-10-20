"""Pipe together with cpu_adapter source to installed EvalScope CPU environment."""
import inspect,hashlib,json
import evalscope
from evalscope import TaskConfig
from evalscope.api.messages import ChatMessageAssistant
from evalscope.benchmarks.gsm8k.gsm8k_adapter import GSM8KAdapter
from evalscope.benchmarks.ifeval.ifeval_adapter import IFEvalAdapter
assert evalscope.__version__=='1.9.1'
checks=[]
for b in ('ifeval','gsm8k'):
 for mode in ('thinking','nonthinking'):
  cfg=TaskConfig(**task_config_dict(b,mode,protocol=protocol_fixture))
  assert cfg.generation_config.extra_body['chat_template_kwargs']['enable_thinking']==(mode=='thinking')
  checks.append(f'{b}/{mode}:TaskConfig_and_GenerateConfig_valid')
fixture={'id':'SYNTHETIC_NOT_HOLDOUT','category':'synthetic','turns':[{'user':'FIRST_SYNTHETIC_USER','required':['PRIVATE_CHECK_1']},{'user':'SECOND_SYNTHETIC_USER','required':['PRIVATE_CHECK_2']}]}
s= specialized_sample(fixture)
assert len(s.input)==1 and s.input[0].content=='FIRST_SYNTHETIC_USER'
assert 'PRIVATE_CHECK' not in str(s.input)
prior=ChatMessageAssistant(content='ACTUAL_SYNTHETIC_ASSISTANT')
history=dynamic_turn_messages(fixture,[prior],'SYNTHETIC_SYSTEM')
assert [m.role for m in history]==['system','user','assistant','user']
assert history[2].content=='ACTUAL_SYNTHETIC_ASSISTANT'
assert 'PRIVATE_CHECK' not in str(history)
# Public native conversions are exercised without constructing/loading benchmark datasets.
g=GSM8KAdapter.record_to_sample(None,{'question':'SYNTHETIC_ARITHMETIC','answer':'synthetic explanation\n#### 7'})
i=IFEvalAdapter.record_to_sample(None,{'key':0,'prompt':'SYNTHETIC_INSTRUCTION','instruction_id_list':['keywords:existence'],'kwargs':[{'keywords':['synthetic']} ]})
assert g.target=='7' and g.input=='SYNTHETIC_ARITHMETIC'
assert i.input[0].content=='SYNTHETIC_INSTRUCTION'
from evalscope.benchmarks.ifeval.utils import process_results
from evalscope.metrics.math.parser import extract_answer
assert process_results({'key':0,'prompt':'SYNTHETIC','instruction_id_list':['keywords:existence'],'kwargs':[{'keywords':['synthetic']}]},['synthetic'])['prompt_level_strict']==1
assert extract_answer('The answer is \\boxed{7}.')=='7'
checks.extend(['ifeval_synthetic_rule_scoring','gsm8k_synthetic_answer_parser','no_gold_in_specialized_prompt','dynamic_multiturn_actual_history','public_native_record_to_sample'])
report={'evalscope_version':evalscope.__version__,'checks':checks,'model_instantiated':False,'inference_executed':False,'source_hashes':{cls.__name__:hashlib.sha256(inspect.getsource(cls).encode()).hexdigest() for cls in (GSM8KAdapter,IFEvalAdapter)}}
print(json.dumps(report,indent=2))
