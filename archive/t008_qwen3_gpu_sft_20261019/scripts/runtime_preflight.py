"""Final PVC/SDK/CLI preflight on CPU. Read-only ClearML; never Task.init/train."""
import datetime,hashlib,importlib.metadata,inspect,json,os,pathlib,sys
sys.path.insert(0,'/input/code')
from run_identity import base_fingerprint,sha,swift_cli_help,validate_authorization
from native_recipe import build_command,spec_read,validate_report
out=pathlib.Path('/runwork/runtime_preflight.json')
report=validate_report('/input/native-preflight.json',spec_read('/input/code/identity-spec.confirmed.json'))
approval=json.loads(pathlib.Path('/input/approval.json').read_text());validate_authorization(approval)
validate_report('/input/native-preflight.json',spec_read('/input/code/identity-spec.confirmed.json'),approval)
files=base_fingerprint('/base')
actual=hashlib.sha256(json.dumps(files,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
assert actual==report['model_files_sha256']
assert not os.environ.get('CUDA_VISIBLE_DEVICES')
from transformers import HfArgumentParser
from swift.arguments import SftArguments
parser=HfArgumentParser(SftArguments)
parse=[]
for mode in ('smoke','full'):
 command=build_command(mode,'/base','/runwork/outputs/PARSER-ONLY-'+mode,report['spec'],swift_cli_help())
 namespace,unknown=parser.parse_known_args(command[2:]);assert not unknown
 args,=parser.parse_args_into_dataclasses(command[2:]+['--use_cpu','true','--report_to','none','--add_version','false'])
 assert str(args.training_args.device)=='cpu'
 parse.append({'mode':mode,'unknown':unknown,'save_steps':args.save_steps,'save_strategy':str(args.save_strategy),'eval_strategy':str(args.eval_strategy),'truncation_strategy':args.truncation_strategy,'device':'cpu','max_steps':args.max_steps})
from clearml import Task,InputModel,Model,OutputModel,StorageManager
assert Task.get_task(task_id='d715e54b152b4aa18d38ec0259a54082').id=='d715e54b152b4aa18d38ec0259a54082'
model=InputModel(model_id='891292342c244f1995671bb5da68c83e')
from urllib.parse import urlparse,urlunparse
parts=urlparse(model.url)
assert parts.hostname in ('clearml-fileserver','clearml.10.140.17.125.nip.io')
secure=urlunparse(parts._replace(scheme='https',netloc='clearml.10.140.17.125.nip.io',path=('/files'+parts.path) if parts.hostname=='clearml-fileserver' else parts.path))
p=StorageManager.get_local_copy(remote_url=secure,extract_archive=False)
assert p and sha(p)=='005cc7d6c45910da0030fb43a831fa33eaacd0744f5ce61cafd9bab7a28f29ac'
# Required reporting integration must import before the shared GPU is paused.
import tensorboard
import torch
result={'schema':'t008-final-runtime-cpu-preflight-v1','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'verified':True,
 'base_model_files_sha256':actual,'base_files_fully_rehashed':files,'cli_parse':parse,
 'image_digest':os.environ['TRAIN_IMAGE_DIGEST'],'source_commit':os.environ['SOURCE_GIT_COMMIT'],
 'native_preflight_sha256':sha('/input/native-preflight.json'),'approval_sha256':sha('/input/approval.json'),
 'clearml_sdk':importlib.metadata.version('clearml'),'clearml_read_only_existing_task_and_model':True,'clearml_https_storage_readback':True,
 'output_model_update_weights_signature':str(inspect.signature(OutputModel.update_weights)),
 'torch_cuda_available':torch.cuda.is_available(),'trainer_created':False,'weights_loaded':False,'clearml_objects_created':False}
assert not result['torch_cuda_available']
out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='base_files_fully_rehashed'},ensure_ascii=False))
