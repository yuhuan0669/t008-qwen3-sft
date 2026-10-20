"""CPU-only preparation helpers. Never instantiate a model or execute inference here."""
from copy import deepcopy
import json
from pathlib import Path

PROTOCOL = Path(__file__).with_name('protocol.json')

def generation_config(mode, seed=42, protocol=None):
    p = protocol or json.loads(PROTOCOL.read_text())
    g = p['modes'][mode]
    return {'temperature':g['temperature'], 'top_p':g['top_p'],
            'top_k':g['top_k'], 'max_tokens':g['max_tokens'], 'seed':seed,
            'extra_body':{'min_p':g['min_p'],
                          'chat_template_kwargs':{'enable_thinking':g['enable_thinking']}}}

def task_config_dict(benchmark, mode, seed=42, protocol=None):
    """Schema-checkable service config; placeholders intentionally block real execution."""
    if benchmark not in ('ifeval','gsm8k'):
        raise ValueError('Specialized records use evaluator-side manual rubric integration; not native public benchmark.')
    return {'model':'CPU_PREPARATION_NO_MODEL', 'eval_type':'service',
            'api_url':'http://127.0.0.1:1/v1', 'datasets':[benchmark],
            'dataset_args':{benchmark:{'few_shot_num':0,'shuffle':False}},
            'generation_config':generation_config(mode,seed,protocol),
            'seed':seed,'eval_batch_size':1, 'ignore_errors':False,
            'work_dir':'EVALUATOR_PRIVATE_OUTPUT_DIRECTORY_TO_BIND',
            'analysis_report':False,'collect_perf':True}

def specialized_sample(record, system=None):
    from evalscope.api.dataset import Sample
    from evalscope.api.messages import ChatMessageUser,ChatMessageSystem
    turns=record['turns']
    assert turns and all(t['user'] and t['required'] for t in turns)
    messages=([ChatMessageSystem(content=system)] if system is not None else [])
    messages.append(ChatMessageUser(content=turns[0]['user']))
    # Scoring requirements stay in evaluator metadata, never in model input.
    return Sample(input=messages,target='',metadata=deepcopy(record))

def dynamic_turn_messages(record, prior_assistant_messages, system=None):
    """Use actual generated assistant messages; no static answer or gold history injection."""
    from evalscope.api.messages import ChatMessageUser,ChatMessageSystem
    i=len(prior_assistant_messages)
    if i>=len(record['turns']): raise ValueError('No user turn remains')
    messages=([ChatMessageSystem(content=system)] if system is not None else [])
    for j in range(i+1):
        messages.append(ChatMessageUser(content=record['turns'][j]['user']))
        if j<i:
            reply=prior_assistant_messages[j]
            if reply.role!='assistant': raise ValueError('Expected actual assistant message')
            messages.append(reply)
    return messages

def matrix(protocol=None):
    p=protocol or json.loads(PROTOCOL.read_text()); rows=[]
    for category,count in p['formal_specialized'].items():
        for condition in p['conditions']:
            seeds=p['candidate_identity_seeds'] if category=='identity' and condition in ('C_new','D_new') else [42]
            for mode in p['modes']:
                for seed in seeds:
                    rows.append(dict(suite='specialized',category=category,condition=condition,mode=mode,seed=seed,count=count))
    for benchmark,count in p['formal_public'].items():
        for condition in p['public_conditions']:
            for mode in p['modes']:
                rows.append(dict(suite='public',category=benchmark,condition=condition,mode=mode,seed=42,count=count))
    return rows

if __name__=='__main__':
    rows=matrix();counts={k:sum(r['count'] for r in rows if (r['condition'] in ('A','B'))==(k=='baseline')) for k in ('baseline','candidate')}
    assert counts=={'baseline':880,'candidate':1200}
    print(json.dumps({'matrix_cases':counts,'total':sum(counts.values()),'inference_executed':False}))
