"""Offline renderer only: writes three Pod JSON files; never calls kubectl."""
from pathlib import Path
import argparse,copy,json,re
P=Path(__file__).resolve().parents[1]
def main():
 a=argparse.ArgumentParser();a.add_argument('--run-id',required=True);a.add_argument('--output',required=True,type=Path);x=a.parse_args();assert re.fullmatch(r't008-manual-[a-z0-9-]{1,35}',x.run_id);x.output.mkdir(parents=True,exist_ok=False)
 def save(n,d):(x.output/n).write_text(json.dumps(d,indent=2)+'\n')
 stage=json.loads((P/'runtime/reference/prep-pod.json').read_text());stage['metadata']={'name':x.run_id+'-stage','namespace':'swift','labels':{'t008-manual':x.run_id,'role':'stage'}};save('stage-pod.json',stage)
 base=json.loads((P/'runtime/reference/job-full.json').read_text())['spec']['template']['spec']
 train={'apiVersion':'v1','kind':'Pod','metadata':{'name':x.run_id+'-train','namespace':'swift','labels':{'t008-manual':x.run_id,'role':'train'}},'spec':base}
 c=base['containers'][0];c['command']=['sleep','36000'];c['volumeMounts']=[{'name':'base','mountPath':'/base','subPath':'Qwen3-8B','readOnly':True},{'name':'data','mountPath':'/handoff','subPath':x.run_id+'/handoff','readOnly':True},{'name':'data','mountPath':'/input/deps','subPath':'t008-v0114-20261021-145454/deps','readOnly':True},{'name':'data','mountPath':'/usr/local/lib/python3.12/site-packages/modelscope/utils/ast_index_file.py','subPath':x.run_id+'/handoff/runtime/support/ast_index_file.py','readOnly':True},{'name':'work','mountPath':'/manual-work','subPath':x.run_id},{'name':'dshm','mountPath':'/dev/shm'}]
 for e in c['env']:
  if 'value' not in e:continue
  if e['name']=='PYTHONPATH':e['value']='/input/deps'
  elif e['name'] in ['REQUESTS_CA_BUNDLE','SSL_CERT_FILE']:e['value']='/handoff/runtime/support/trust-bundle.pem'
  elif e['name']=='SOURCE_GIT_COMMIT':e['value']=json.loads((P/'PACKAGE.json').read_text())['source_commit']
  else:e['value']=e['value'].replace('/runwork/','/manual-work/')
 save('train-pod.json',train)
 evaluation=copy.deepcopy(train);evaluation['metadata']['name']=x.run_id+'-eval';evaluation['metadata']['labels']['role']='eval';save('eval-pod.json',evaluation)
 print(json.dumps({'output':str(x.output),'rendered':3,'cluster_accessed':False}))
if __name__=='__main__':main()
