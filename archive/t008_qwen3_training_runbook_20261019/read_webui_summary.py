import json,sqlite3,pathlib
c=sqlite3.connect('file:/app/backend/data/webui.db?mode=ro',uri=True)
def safe_params(d,path=''):
 out=[]
 if isinstance(d,dict):
  for k,v in d.items():
   p=path+'.'+k
   if k in ('max_tokens','max_completion_tokens','max_new_tokens','num_predict','stop','temperature','top_p','top_k','frequency_penalty','presence_penalty','enable_thinking','reasoning_effort','function_calling','tool_calling_max_retries'):
    out.append({'path':p,'value':v})
   if k in ('system','system_prompt','SYSTEM_PROMPT') and isinstance(v,str):out.append({'path':p,'system_chars':len(v),'contains_scope_terms':[w for w in ['智慧交通','智慧建筑','碳资产','能源管理'] if w in v]})
   if isinstance(v,(dict,list)):out+=safe_params(v,p)
 elif isinstance(d,list):
  for i,v in enumerate(d):out+=safe_params(v,path+'.'+str(i))
 return out
out={'selected_settings':[],'messages':[]}
for cid,user,raw in c.execute('select id,user_id,chat from chat order by updated_at desc limit 40'):
 if 'octacarbon-llm-sft-test' not in raw:continue
 d=json.loads(raw);messages=d.get('history',{}).get('messages',{})
 if not any('北京的碳排放系数' in str(m.get('content','')) for m in messages.values()):continue
 out['chat_id']=cid;out['selected_settings']+=safe_params(d.get('params',{}),'chat.params')
 u=c.execute('select settings from user where id=?',(user,)).fetchone()
 if u:out['selected_settings']+=safe_params(json.loads(u[0] or '{}'),'user.settings')
 for m in messages.values():
  parent=messages.get(m.get('parentId'),{})
  if m.get('role')!='assistant' or parent.get('content') not in ('北京的碳排放系数是多少？','你是什么大模型'):continue
  rec={'id':m['id'],'question':parent.get('content'),'timestamp':m.get('timestamp'),'content_chars':len(m.get('content','')),'done':m.get('done'),'error':m.get('error'),'metadata_params':safe_params(m.get('meta',{}),'message.meta'),'output_summary':[]}
  for o in m.get('output',[]):
   s={k:o.get(k) for k in ('type','status','name','duration') if k in o}
   if o.get('type')=='reasoning':s['reasoning_chars']=sum(len(x.get('text','')) for x in o.get('content',[]))
   elif o.get('type')=='function_call_output':s['result_excerpt']=str(o.get('output'))[:500]
   elif o.get('type')=='message':s['text_chars']=sum(len(x.get('text','')) for x in o.get('content',[]))
   elif o.get('type')=='function_call':s['arguments']=o.get('arguments')
   rec['output_summary'].append(s)
  rec['usage_or_terminal']={k:v for k,v in m.items() if any(x in k.lower() for x in ('usage','token','finish','stop','stat'))}
  out['messages'].append(rec)
 break
for key,value in c.execute('select key,value from config'):
 try:out['selected_settings']+=safe_params(json.loads(value),'config.'+key)
 except (ValueError,TypeError):pass
print(json.dumps(out,ensure_ascii=False,indent=2))
