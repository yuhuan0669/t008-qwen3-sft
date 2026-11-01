"""Execute frozen missing slots once; retain raw responses and stop the private server."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import datetime, hashlib, importlib.metadata, json, os, signal, subprocess, sys, time
import urllib.request, urllib.error

D=Path(__file__).resolve().parent
OP=urllib.request.build_opener(urllib.request.ProxyHandler({}))

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''): h.update(b)
    return h.hexdigest()

def save(name,obj):
    p=D/name; p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_name(p.name+'.tmp');tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n');tmp.replace(p)

def request(route,body=None,timeout=600):
    r=urllib.request.Request('http://127.0.0.1:8000'+route,
        data=None if body is None else json.dumps(body,ensure_ascii=False).encode(),
        headers={'Content-Type':'application/json'})
    with OP.open(r,timeout=timeout) as res:
        raw=res.read().decode();return res.status,raw,json.loads(raw) if raw else None

def main():
    from transformers import AutoTokenizer
    cfg=json.loads((D/'evaluation-config.json').read_text())
    binding=json.loads((D/'runtime-binding.json').read_text())
    cases={c['id']:c for c in json.loads((D/'cases.json').read_text())['items']}
    slots=json.loads((D/'missing-slots.json').read_text())
    assert len(slots)==176 and not (D/'results.jsonl').exists()
    assert sha(D/'cases.json')==cfg['cases_sha256']
    assert sha(D/'system.txt')==cfg['system_sha256']
    assert sha(D/'thinking-prefill.jinja')==cfg['chat_template']['sha256']
    for n,v in binding['versions'].items():assert importlib.metadata.version(n)==v,(n,v)
    for x in json.loads((D/'base-files.json').read_text()):
        if x['path'].startswith(('model','tokenizer','config','generation','merges','vocab')):
            p=Path('/base')/x['path'];assert p.stat().st_size==x['size'] and sha(p)==x['sha256'],str(p)
    for model,a in binding['adapters'].items():
        for f,info in a['files'].items():
            p=Path(a['path'])/f;assert p.stat().st_size==info['bytes'] and sha(p)==info['sha256'],str(p)
    groups={g['name']:g for g in cfg['groups']}
    system=(D/'system.txt').read_text(); template=(D/'thinking-prefill.jinja').read_text()
    tok=AutoTokenizer.from_pretrained('/base',local_files_only=True)
    prepared=[]; prompts={}
    for s in slots:
        g=groups[s['group']];c=cases[s['case_id']];mode=cfg['request_modes'][g['mode']]
        messages=([{'role':'system','content':system}] if g['system'] else [])+c['messages']
        payload={**mode,'model':binding['aliases'][s['model']],'messages':messages}
        if c.get('json_schema'):
            payload['response_format']={'type':'json_schema','json_schema':{
                'name':'t008_structured_answer','schema':c['json_schema'],'strict':True}}
        elif c.get('response_format'):payload['response_format']=c['response_format']
        assert 'seed' not in payload and 'tools' not in payload
        key=(s['group'],s['case_id'])
        if key not in prompts:
            ids=tok.apply_chat_template(messages,chat_template=template,tokenize=True,add_generation_prompt=True,**mode['chat_template_kwargs'])
            if hasattr(ids,'keys'):ids=ids['input_ids']
            tail='<think>\n' if g['mode']=='thinking' else '<think>\n\n</think>\n\n'
            assert tok.decode(ids).endswith(tail) and len(ids)+mode['max_tokens']<=8192
            prompts[key]=ids
        prepared.append((s,payload,key))
    save('preflight.json',{'status':'PASS','binding':binding,'unique_prompts':len(prompts),'slots':len(slots),
        'input_ids':[{'group':k[0],'case_id':k[1],'ids':v} for k,v in prompts.items()]})
    argv=binding['server_argv'];save('vllm-command.json',argv)
    started=time.monotonic(); completed=0;attempts=0;technical=0
    with (D/'vllm-server.log').open('w') as log:
        server=subprocess.Popen(argv,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try:
            deadline=time.monotonic()+600
            while True:
                assert server.poll() is None,'Private vLLM server exited'
                try:
                    if request('/health',timeout=3)[0]==200:break
                except Exception:pass
                if time.monotonic()>deadline:raise TimeoutError('Private vLLM startup')
                time.sleep(3)
            save('models.json',request('/v1/models')[2])
            # Render calls do not generate answers. Verify server and offline token IDs.
            seen=set()
            for s,payload,key in prepared:
                if key in seen:continue
                rendered=request('/v1/chat/completions/render',payload)[2]
                assert rendered['token_ids']==prompts[key],key
                seen.add(key)
            save('server-input-verification.json',{'matched':len(seen),'all_equal':True})
            def execute(item):
                s,payload,key=item;name='__'.join([s['model'],s['group'],s['case_id'],str(s['repeat'])])
                last=None
                for attempt in range(1,2):
                    p=D/'raw'/name/str(attempt);p.mkdir(parents=True,exist_ok=False)
                    (p/'request.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
                    t=time.monotonic();utc=datetime.datetime.now(datetime.timezone.utc).isoformat()
                    try:
                        status,raw,response=request('/v1/chat/completions',payload)
                        (p/'response.raw.json').write_text(raw)
                        assert status==200 and len(response['choices'])==1
                        assert response['usage']['prompt_tokens']==len(prompts[key])
                        row={**s,'request':payload,'response':response,'raw_path':str(p.relative_to(D)),
                             'http_status':status,'utc':utc,'seconds':time.monotonic()-t,'attempt':attempt,'input_ids_verified':True}
                        save(str(p.relative_to(D)/'meta.json'),{k:v for k,v in row.items() if k not in ['request','response']})
                        return row
                    except urllib.error.HTTPError as e:
                        raw=e.read().decode(errors='replace');(p/'error-body.txt').write_text(raw)
                        last=repr(e);retry=e.code in (408,429,500,502,503,504)
                    except (TimeoutError,urllib.error.URLError,ConnectionError) as e:
                        last=repr(e);retry=True
                    except Exception as e:
                        last=repr(e);retry=False
                    save(str(p.relative_to(D)/'error.json'),{'error':last,'utc':utc,'seconds':time.monotonic()-t,'retryable':retry})
                    if not retry:break
                    time.sleep(min(10*attempt,30))
                raise RuntimeError(name+': '+str(last))
            for model in cfg['models']:
                batch=[x for x in prepared if x[0]['model']==model]
                with ThreadPoolExecutor(max_workers=cfg['concurrency']) as pool:
                    futures=[pool.submit(execute,x) for x in batch]
                    for f in as_completed(futures):
                        row=f.result();completed+=1;attempts+=row['attempt'];technical+=row['attempt']-1
                        with (D/'results.jsonl').open('a') as out:out.write(json.dumps(row,ensure_ascii=False)+'\n');out.flush()
                        state={'completed':completed,'total':len(slots),'model':model,'attempts':attempts,
                               'technical_retries':technical,'seconds':time.monotonic()-started,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
                        save('progress.json',state)
                        if completed%20==0 or completed==len(slots):print(json.dumps(state),flush=True)
                        if technical>32:raise RuntimeError('Technical retry allowance exceeded')
        finally:
            if server.poll() is None:
                os.killpg(server.pid,signal.SIGTERM)
                try:server.wait(timeout=40)
                except subprocess.TimeoutExpired:os.killpg(server.pid,signal.SIGKILL);server.wait(timeout=10)
    assert completed==176
    save('complete.json',{'status':'COMPLETE','count':completed,'attempts':attempts,'technical_retries':technical,
        'results_sha256':sha(D/'results.jsonl'),'seconds':time.monotonic()-started,'training':False})

if __name__=='__main__':
    try:main()
    except BaseException as e:save('failure.json',{'error':repr(e)});raise
