"""Offline only: prepare ConfigMap, release staging Pod and tested JSON patches."""
from pathlib import Path
import argparse,copy,json,re
P=Path(__file__).resolve().parents[1]
def main():
 a=argparse.ArgumentParser();a.add_argument('--deployment',type=Path,required=True);a.add_argument('--release',required=True);a.add_argument('--model-alias',required=True);a.add_argument('--rank',type=int,default=8);a.add_argument('--output',type=Path,required=True);x=a.parse_args();assert re.fullmatch(r'[a-z0-9][a-z0-9-]{1,38}',x.release);assert re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{1,60}',x.model_alias);assert x.rank>0 and not x.output.exists()
 d=json.loads(x.deployment.read_text());assert d['kind']=='Deployment' and d['metadata']['namespace']=='vllm' and d['metadata']['name']=='vllm';before=d['spec']['template'];after=copy.deepcopy(before);cs=after['spec']['containers'];c=next(c for c in cs if c['name']=='vllm');args=c['args'];uid=d['metadata']['uid'];cm=x.release+'-template';adapter_path='/adapters/'+x.model_alias;template_path='/t008-serving/thinking-prefill.jinja'
 def setflag(flag,value):
  if flag in args:args[args.index(flag)+1]=str(value)
  else:args.extend([flag,str(value)])
 assert x.model_alias!=args[args.index('--served-model-name')+1],'Base and LoRA need distinct aliases'
 if '--enable-lora' not in args:args.append('--enable-lora')
 rank=max(x.rank,int(args[args.index('--max-lora-rank')+1]) if '--max-lora-rank'in args else 0);setflag('--max-lora-rank',rank);setflag('--chat-template',template_path);setflag('--reasoning-parser','qwen3')
 module=json.dumps({'name':x.model_alias,'path':adapter_path,'base_model_name':args[args.index('--served-model-name')+1]},separators=(',',':'))
 if '--lora-modules' in args:
  i=args.index('--lora-modules')+1;j=i
  while j<len(args) and not args[j].startswith('--'):j+=1
  existing=args[i:j];names=[json.loads(t)['name'] if t.startswith('{') else t.split('=',1)[0] for t in existing];assert x.model_alias not in names;args.insert(j,module)
 else:args.extend(['--lora-modules',module])
 vols=after['spec']['volumes'];assert any(v['name']=='model-store' and v.get('persistentVolumeClaim',{}).get('claimName')=='vllm-released' for v in vols)
 assert not any(v['name']=='t008-serving-template' for v in vols),'Existing managed template: review and assign a new volume name instead of overwriting'
 vols.append({'name':'t008-serving-template','configMap':{'name':cm}})
 mounts=c['volumeMounts'];assert not any(v['mountPath'] in [adapter_path,'/t008-serving'] for v in mounts)
 mounts.extend([{'name':'model-store','mountPath':adapter_path,'subPath':'released/'+x.release+'/adapter','readOnly':True},{'name':'t008-serving-template','mountPath':'/t008-serving','readOnly':True}]);after.setdefault('metadata',{}).setdefault('annotations',{})['t008.octacarbon/release']=x.release
 def patch(old,new):return [{'op':'test','path':'/metadata/uid','value':uid},{'op':'test','path':'/spec/template','value':old},{'op':'replace','path':'/spec/template','value':new}]
 x.output.mkdir(parents=True)
 def save(n,v):(x.output/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
 save('publish.patch.json',patch(before,after));save('rollback.patch.json',patch(after,before));save('desired-template.json',after);save('deployment-before.json',d)
 save('template.configmap.json',{'apiVersion':'v1','kind':'ConfigMap','metadata':{'name':cm,'namespace':'vllm'},'immutable':True,'data':{'thinking-prefill.jinja':(P/'evaluation/materials/thinking-prefill.jinja').read_text()}})
 image=json.loads((P/'runtime/reference/job-full.json').read_text())['spec']['template']['spec']['containers'][0]['image']
 save('release-stage-pod.json',{'apiVersion':'v1','kind':'Pod','metadata':{'name':x.release+'-stage','namespace':'vllm','labels':{'t008-release':x.release}},'spec':{'restartPolicy':'Never','automountServiceAccountToken':False,'nodeSelector':{'nvidia.com/gpu.present':'true'},'tolerations':[{'key':'dedicated','operator':'Equal','value':'gpu-rtx4090','effect':'NoSchedule'}],'containers':[{'name':'stage','image':image,'command':['sleep','36000'],'env':[{'name':'CUDA_VISIBLE_DEVICES','value':''},{'name':'NVIDIA_VISIBLE_DEVICES','value':'void'}],'resources':{'requests':{'cpu':'100m','memory':'256Mi'},'limits':{'cpu':'1','memory':'1Gi'}},'volumeMounts':[{'name':'store','mountPath':'/store'}]}],'volumes':[{'name':'store','persistentVolumeClaim':{'claimName':'vllm-released'}}]}})
 print(json.dumps({'rendered_only':True,'namespace':'vllm','model_alias':x.model_alias,'release':x.release,'original_replicas':d['spec']['replicas'],'cluster_accessed':False}))
if __name__=='__main__':main()
