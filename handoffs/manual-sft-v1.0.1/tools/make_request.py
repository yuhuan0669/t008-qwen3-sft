"""Print a request JSON only; never connects to an endpoint."""
from pathlib import Path
import argparse,json
P=Path(__file__).resolve().parents[1]
def main():
 a=argparse.ArgumentParser();a.add_argument('--model',required=True);a.add_argument('--mode',choices=['thinking','nonthinking'],default='nonthinking');g=a.add_mutually_exclusive_group(required=True);g.add_argument('--text');g.add_argument('--case');x=a.parse_args();e=P/'evaluation/materials';s=json.loads((e/'spec.json').read_text());cfg=dict(s['modes'][x.mode]);thinking=cfg.pop('enable_thinking')
 body={'model':x.model,'messages':[{'role':'system','content':(e/'custom-system.txt').read_text()}],'stream':False,'seed':42,'repetition_penalty':1.0,'chat_template_kwargs':{'enable_thinking':thinking},**cfg}
 if x.case:
  c=next(c for c in map(json.loads,(e/'scenarios.jsonl').read_text().splitlines()) if c['id']==x.case);assert len(c['user_turns'])==1;body['messages'].append({'role':'user','content':c['user_turns'][0]})
  if 'response_format' in c:body['response_format']=c['response_format']
 else:body['messages'].append({'role':'user','content':x.text})
 print(json.dumps(body,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
