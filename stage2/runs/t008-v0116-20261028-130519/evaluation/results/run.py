"""Frozen 120-request Chinese development comparison; no training imports."""
from pathlib import Path
import datetime
import hashlib
import importlib.metadata
import json
import os
import signal
import subprocess
import sys
import time
import urllib.request

D = Path(__file__).resolve().parent


def save(name, obj):
    (D/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''): h.update(b)
    return h.hexdigest()


def post(route, body):
    req=urllib.request.Request('http://127.0.0.1:8000/v1'+route,
        data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=360) as response:
        raw=response.read().decode()
        return response.status,raw,json.loads(raw)


def main():
    from transformers import AutoTokenizer
    spec=json.loads((D/'spec.json').read_text())
    assert spec['training'] is False and spec['english'] is False
    assert json.loads((D/'authorization.json').read_text())['approved'] is True
    assert not (D/'results.jsonl').exists(), 'No silent resampling or overwrite'
    versions={x:importlib.metadata.version(x) for x in spec['versions']}
    assert versions==spec['versions'],versions
    for file,key in [('custom-system.txt','system_sha256'),('thinking-prefill.jinja','template_sha256'),
                     ('conditions.jsonl','conditions_sha256'),('development-cases.json','development_cases_sha256')]:
        assert sha(D/file)==spec[key],file
    for adapter in spec['adapters'].values():
        for file,info in adapter['files'].items():
            p=Path(adapter['path'])/file
            assert p.stat().st_size==info['bytes'] and sha(p)==info['sha256'],str(p)
    base_files=json.loads((D/'base-files.json').read_text())
    for info in base_files:
        if info['path'].startswith(('model','tokenizer','config','generation','merges','vocab')):
            p=Path('/base')/info['path']
            assert p.stat().st_size==info['size'] and sha(p)==info['sha256'],info['path']
    system=(D/'custom-system.txt').read_text();template=(D/'thinking-prefill.jinja').read_text()
    conditions=[json.loads(s) for s in (D/'conditions.jsonl').read_text().splitlines()]
    assert len(conditions)==40 and len(spec['models'])==3 and spec['total_requests']==120
    tokenizer=AutoTokenizer.from_pretrained('/base',local_files_only=True)
    prompts=[]
    for condition in conditions:
        cfg=spec['modes'][condition['mode']]
        messages=[{'role':'system','content':system}]+condition['messages']
        ids=tokenizer.apply_chat_template(messages,chat_template=template,tokenize=True,
            add_generation_prompt=True,**cfg['chat_template_kwargs'])
        if hasattr(ids,'keys'): ids=ids['input_ids']
        tail='<think>\n' if cfg['chat_template_kwargs']['enable_thinking'] else '<think>\n\n</think>\n\n'
        assert tokenizer.decode(ids).endswith(tail)
        assert len(ids)+cfg['max_tokens']<=8192
        prompts.append(ids)
    save('preflight.json',{'status':'PASS','versions':versions,'adapters':spec['adapters'],
        'base_files':base_files,'input_ids':prompts,'system_sha256':spec['system_sha256'],
        'template_sha256':spec['template_sha256']})
    print('HASHES AND INPUTS VERIFIED',flush=True)
    argv=[sys.executable,'-m','vllm.entrypoints.openai.api_server','--model','/base',
        '--served-model-name','t008-base','--host','127.0.0.1','--port','8000','--dtype','bfloat16',
        '--max-model-len','8192','--max-num-seqs','8','--gpu-memory-utilization','0.90','--seed','42',
        '--enable-lora','--lora-modules',*[name+'='+a['path'] for name,a in spec['adapters'].items()],
        '--max-lora-rank','8','--max-loras','1','--max-cpu-loras','2',
        '--chat-template',str(D/'thinking-prefill.jinja'),'--reasoning-parser','qwen3']
    save('vllm-command.json',argv)
    completed=0
    with (D/'vllm-server.log').open('w') as log:
        server=subprocess.Popen(argv,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try:
            deadline=time.monotonic()+480
            while True:
                assert server.poll() is None,'vLLM startup failed'
                try:
                    with urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=3) as res:
                        if res.status==200: break
                except Exception: pass
                if time.monotonic()>deadline: raise TimeoutError('vLLM startup timeout')
                time.sleep(3)
            for i,c in enumerate(conditions):
                shift=i%3;models=spec['models'][shift:]+spec['models'][:shift]
                for model in models:
                    messages=[{'role':'system','content':system}]+c['messages']
                    body={**spec['modes'][c['mode']],**spec['common'],'model':model,
                          'messages':messages,'seed':c['seed'],'stream':False}
                    if 'response_format' in c: body['response_format']=c['response_format']
                    row={'id':'__'.join([c['case_id'],c['mode'],str(c['seed']),model]),
                         'case_id':c['case_id'],'model':model,'mode':c['mode'],'seed':c['seed'],
                         'category':c['category'],'checks':c['checks'],'request':body,
                         'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
                    started=time.monotonic()
                    try:
                        _,_,rendered=post('/chat/completions/render',body)
                        assert rendered['token_ids']==prompts[i]
                        row.update(server_render=rendered,input_ids_verified=True)
                        status,raw,response=post('/chat/completions',body)
                        row.update(http_status=status,response_raw=raw,response=response)
                        assert response['usage']['prompt_tokens']==len(prompts[i])
                    except Exception as exc:
                        row['error']=repr(exc)
                        raise
                    finally:
                        row['seconds']=time.monotonic()-started
                        with (D/'results.jsonl').open('a') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n')
                    completed+=1
                    choice=row['response']['choices'][0]
                    progress={'completed':completed,'total':120,'current':row['id'],
                        'finish_reason':choice['finish_reason'],'tokens':row['response']['usage']['completion_tokens'],
                        'seconds':row['seconds'],'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
                    save('progress.json',progress);print(json.dumps(progress),flush=True)
        finally:
            if server.poll() is None:
                os.killpg(server.pid,signal.SIGTERM)
                try:server.wait(timeout=40)
                except subprocess.TimeoutExpired:
                    os.killpg(server.pid,signal.SIGKILL);server.wait(timeout=10)
    assert completed==120
    save('complete.json',{'status':'COMPLETE','count':120,'results_sha256':sha(D/'results.jsonl'),'training':False})


if __name__=='__main__':
    try:main()
    except Exception as exc:
        save('failure.json',{'error':repr(exc)})
        raise
