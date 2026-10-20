import json,sqlite3,pathlib
c=sqlite3.connect('file:/app/backend/data/webui.db?mode=ro',uri=True)
print('CONFIG_COLUMNS',[x[1] for x in c.execute('pragma table_info(config)')])
print('USER_COLUMNS',[x[1] for x in c.execute('pragma table_info(user)')])
for row in c.execute('select id,base_model_id,params from model where id like ? or base_model_id like ?',('%octacarbon%','%octacarbon%')):print('MODEL_PARAMS',row)
found=0
for cid,user,raw in c.execute('select id,user_id,chat from chat order by updated_at desc limit 40'):
 if 'octacarbon-llm-sft-test' not in raw:continue
 d=json.loads(raw);messages=d.get('history',{}).get('messages',{})
 if not any('北京的碳排放系数' in str(m.get('content','')) for m in messages.values()):continue
 found+=1;print('TARGET_CHAT',json.dumps({'id':cid,'params':d.get('params'),'models':d.get('models')},ensure_ascii=False))
 for m in messages.values():
  if m.get('role')=='user' and '北京的碳排放系数' in str(m.get('content','')):print('QUESTION',json.dumps(m,ensure_ascii=False))
  elif m.get('role')=='assistant' and (m.get('model')=='octacarbon-llm-sft-test' or m.get('modelName')=='octacarbon-llm-sft-test'):
   print('ANSWER',json.dumps({k:v for k,v in m.items() if k not in ('user','avatar','files')},ensure_ascii=False))
 u=c.execute('select settings from user where id=?',(user,)).fetchone()
 if u:
  settings=json.loads(u[0] or '{}');print('USER_INFERENCE_SETTINGS',json.dumps({k:v for k,v in settings.items() if k in ('ui','params')},ensure_ascii=False))
 if found>=2:break
print('MATCHED_CHATS',found)
