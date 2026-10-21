"""Render existing development final answers; do not expose hidden reasoning or resample."""
from pathlib import Path
import json,collections
O=Path(__file__).resolve().parent;P=O/'development';rows=[json.loads(s) for s in (P/'all-24.jsonl').read_text().splitlines()];assert len(rows)==192
by={(r['id'],r['condition'],r['mode']):r for r in rows};assert len(by)==192
text=['# v0.1.8 identity-loss3 开发回答对照','', 'A＝原版无System；B＝原版＋新版System；C_new＝v0.1.8 identity-loss3无System；D_new＝v0.1.8 identity-loss3＋新版System。全部使用同一修正后的vLLM模板，seed42。本文件只展示最终正文，不据名称命中自动判定验收。DEV-06仅诊断，撤出的保密要求不评分。','']
for cid in sorted({r['id'] for r in rows}):
 text += ['## '+cid,'']
 for mode in ['nonthinking','thinking']:
  for cond in ['A','B','C_new','D_new']:
   r=by[(cid,cond,mode)];text += ['### '+cond+' / '+mode,'']
   for t in r['turns']:
    text += ['**问题：** '+t['user'],'','**回答：** '+(t.get('assistant') or t.get('error') or '【空正文】'),'','结束原因：'+str(t.get('finish_reason')),'']
(P/'ANSWERS.md').write_text('\n'.join(text)+'\n')
s=[]
for cond in ['A','B','C_new','D_new']:
 for mode in ['nonthinking','thinking']:
  rs=[r for r in rows if r['condition']==cond and r['mode']==mode];ts=[t for r in rs for t in r['turns']]
  s.append({'condition':cond,'mode':mode,'cases':len(rs),'requests':len(ts),'errors':sum('error'in t for t in ts),'empty_body':sum(not t.get('assistant','').strip() for t in ts if 'error' not in t),'length_finishes':sum(t.get('finish_reason')=='length' for t in ts)})
(P/'format-by-condition.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(s,ensure_ascii=False))
