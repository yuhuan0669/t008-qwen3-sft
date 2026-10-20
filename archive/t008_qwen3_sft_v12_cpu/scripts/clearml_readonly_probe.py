"""Run inside isolated CPU container. Credentials arrive on stdin only."""
import sys,json,os,pathlib,hashlib,inspect,datetime
cfg=json.load(sys.stdin)
ca=pathlib.Path('/work/trust/ca.pem');ca.parent.mkdir(exist_ok=True);ca.write_text(cfg['ca'])
os.environ.update({'CLEARML_API_HOST':'https://clearml.10.140.17.125.nip.io/api',
 'CLEARML_WEB_HOST':'https://clearml.10.140.17.125.nip.io',
 'CLEARML_FILES_HOST':'https://clearml.10.140.17.125.nip.io/files',
 'CLEARML_API_ACCESS_KEY':cfg['access_key'],'CLEARML_API_SECRET_KEY':cfg['secret_key'],
 'REQUESTS_CA_BUNDLE':str(ca),'CLEARML_API_HOST_VERIFY_CERT':'1'})
from clearml import Task,InputModel,OutputModel,StorageManager,Model
import importlib.metadata
result={'observed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'scope':'Read-only existing SYNTHETIC objects; no Task or Model creation, no training data uploads',
 'sdk_version':importlib.metadata.version('clearml'),'https_certificate_verification':True,
 'sdk_methods':{'output_model_update_weights':str(inspect.signature(OutputModel.update_weights)),
  'output_model_get_local_copy_available':hasattr(OutputModel,'get_local_copy'),
  'registered_model_get_local_copy':str(inspect.signature(Model.get_local_copy)),
  'input_model_get_local_copy':str(inspect.signature(InputModel.get_local_copy))}}
try:
 task=Task.get_task(task_id='d715e54b152b4aa18d38ec0259a54082')
 model=InputModel(model_id='891292342c244f1995671bb5da68c83e')
 result.update({'existing_synthetic_task':{'id':task.id,'status':str(task.get_status())},
                'existing_synthetic_model':{'id':model.id}})
 url=model.url
 from urllib.parse import urlparse,urlunparse
 parts=urlparse(url)
 result['stored_model_location']={'scheme':parts.scheme,'hostname':parts.hostname,'port':parts.port}
 if parts.hostname=='clearml-fileserver' and parts.port==8081:
  secure=urlunparse(parts._replace(scheme='https',netloc='clearml.10.140.17.125.nip.io',path='/files'+parts.path))
  result['legacy_internal_uri_mapped_to_verified_https_ingress']=True
 elif parts.hostname=='clearml.10.140.17.125.nip.io':
  secure=urlunparse(parts._replace(scheme='https'))
 else:
  raise RuntimeError('Existing model URL host outside intended ClearML server')
 local=StorageManager.get_local_copy(remote_url=secure,extract_archive=False)
 if not local:raise RuntimeError('SDK model download returned no local file')
 data=pathlib.Path(local).read_bytes();digest=hashlib.sha256(data).hexdigest()
 expected='005cc7d6c45910da0030fb43a831fa33eaacd0744f5ce61cafd9bab7a28f29ac'
 result['model_storage_readback']={'bytes':len(data),'sha256':digest,'historical_synthetic_hash_match':digest==expected,
  'download_scheme':'https','stored_url_scheme':parts.scheme}
 if digest!=expected:raise RuntimeError('Existing synthetic model hash differs from accepted reference')
 result['status']='READ_ONLY_SDK_TASK_MODEL_STORAGE_PASS'
except Exception as e:
 result['status']='INCOMPLETE';result['error_type']=type(e).__name__
 # Avoid serializing SDK exception strings, which may contain request details.
out=pathlib.Path('/work/clearml-readonly.json')
out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result))
