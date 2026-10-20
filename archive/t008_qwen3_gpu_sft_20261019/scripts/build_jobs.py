import copy,json,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1]
auth=json.loads((ROOT/'evidence/owner_authorization.json').read_text());run=auth['run_id']
image='modelscope-registry.cn-hangzhou.cr.aliyuncs.com/modelscope-repo/modelscope@sha256:822d99beed4984a421c8d1da397993c6a8a5f88cdad7dde940bd52df0067d738'
env={
 'USER':'swift-t008','LOGNAME':'swift-t008','PYTHONPATH':'/input/code:/input/deps','PYTHONUNBUFFERED':'1',
 'MODELSCOPE_CACHE':'/runwork/cache/modelscope','MODELSCOPE_HOME':'/runwork/cache/modelscope-home',
 'HF_HOME':'/runwork/cache/huggingface','XDG_CACHE_HOME':'/runwork/cache/xdg','TRITON_CACHE_DIR':'/runwork/cache/triton',
 'TORCHINDUCTOR_CACHE_DIR':'/runwork/cache/torchinductor','TORCH_EXTENSIONS_DIR':'/runwork/cache/torch_extensions',
 'MPLCONFIGDIR':'/runwork/cache/matplotlib','TMPDIR':'/runwork/tmp','CLEARML_CACHE_DIR':'/runwork/cache/clearml',
 'CLEARML_API_HOST':'https://clearml.10.140.17.125.nip.io/api','CLEARML_WEB_HOST':'https://clearml.10.140.17.125.nip.io',
 'CLEARML_FILES_HOST':'https://clearml.10.140.17.125.nip.io/files','CLEARML_API_HOST_VERIFY_CERT':'1',
 'REQUESTS_CA_BUNDLE':'/input/runtime-support/trust-bundle.pem','SSL_CERT_FILE':'/input/runtime-support/trust-bundle.pem',
 'BASE_MODEL':'/base','IDENTITY_SPEC':'/input/code/identity-spec.confirmed.json','NATIVE_PREFLIGHT_REPORT':'/input/native-preflight.json',
 'APPROVAL_FILE':'/input/approval.json','TRAIN_IMAGE_DIGEST':image.split('@')[1],'SOURCE_GIT_COMMIT':auth['source_commit'],
 'RUN_AUTHORIZED':'yes','GPU_WINDOW_APPROVED':'yes','OMP_NUM_THREADS':'4','TOKENIZERS_PARALLELISM':'false',
 'TZ':'UTC','USE_QLORA':'false','USE_LIGER':'false'}
base={'restartPolicy':'Never','automountServiceAccountToken':False,'serviceAccountName':'swift-trainer',
 'nodeSelector':{'kubernetes.io/hostname':'k8s-worker05'},'tolerations':[{'key':'dedicated','operator':'Equal','value':'gpu-rtx4090','effect':'NoSchedule'}],
 'terminationGracePeriodSeconds':60,
 'containers':[{'name':'sft','image':image,'imagePullPolicy':'IfNotPresent','securityContext':{'runAsNonRoot':True,'runAsUser':10001,'runAsGroup':10001,'allowPrivilegeEscalation':False,'capabilities':{'drop':['ALL']}},
 'env':[{'name':k,'value':v} for k,v in env.items()]+[{'name':'CLEARML_API_ACCESS_KEY','valueFrom':{'secretKeyRef':{'name':'swift-clearml','key':'access_key'}}},{'name':'CLEARML_API_SECRET_KEY','valueFrom':{'secretKeyRef':{'name':'swift-clearml','key':'secret_key'}}}],
 'volumeMounts':[{'name':'base','mountPath':'/base','readOnly':True,'subPath':'Qwen3-8B'},
 {'name':'data','mountPath':'/input','readOnly':True,'subPath':run},
 {'name':'work','mountPath':'/runwork','subPath':run},
 {'name':'data','mountPath':'/usr/local/lib/python3.12/site-packages/modelscope/utils/ast_index_file.py','readOnly':True,'subPath':run+'/runtime-support/ast_index_file.py'},
 {'name':'dshm','mountPath':'/dev/shm'}]}],
 'volumes':[{'name':'base','persistentVolumeClaim':{'claimName':'swift-base','readOnly':True}},
 {'name':'data','persistentVolumeClaim':{'claimName':'swift-train-data','readOnly':True}},
 {'name':'work','persistentVolumeClaim':{'claimName':'swift-work'}},{'name':'dshm','emptyDir':{'medium':'Memory','sizeLimit':'8Gi'}}]}
for mode in ('preflight','smoke','full'):
 spec=copy.deepcopy(base);c=spec['containers'][0]
 if mode=='preflight':
  c['resources']={'requests':{'cpu':'1','memory':'2Gi'},'limits':{'cpu':'2','memory':'8Gi'}}
  c['env'] += [{'name':'NVIDIA_VISIBLE_DEVICES','value':'void'},{'name':'CUDA_VISIBLE_DEVICES','value':''}]
  c['command']=['bash','-c','set -euo pipefail\npython3 /input/runtime_preflight.py 2>&1 | tee /runwork/runtime-preflight.log']
 else:
  c['resources']={'requests':{'cpu':'4','memory':'16Gi','nvidia.com/gpu':'1'},'limits':{'cpu':'8','memory':'32Gi','nvidia.com/gpu':'1'}}
  c['env'] += [{'name':'CUDA_VISIBLE_DEVICES','value':'0'},{'name':'OUT_DIR','value':'/runwork/outputs/'+mode}]
  c['command']=['python3','/input/gpu_stage.py',mode]
 job={'apiVersion':'batch/v1','kind':'Job','metadata':{'name':run+'-'+mode,'namespace':'swift','labels':{'app':'t008-identity-sft','t008-run':run,'stage':mode}},
 'spec':{'backoffLimit':0,'activeDeadlineSeconds':7200 if mode=='full' else 1800,'template':{'metadata':{'labels':{'app':'t008-identity-sft','t008-run':run,'stage':mode}},'spec':spec}}}
 (ROOT/'evidence'/('job-'+mode+'.json')).write_text(json.dumps(job,indent=2)+'\n')
print(json.dumps({'run':run,'modes':['preflight','smoke','full'],'credentials':'Secret refs only','image':image}))
