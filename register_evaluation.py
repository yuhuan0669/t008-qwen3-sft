#!/usr/bin/env python3
"""Link reviewed evaluation SUMMARY to one ClearML training Task via a separate eval Task.
Does NOT upload individual test prompts, responses, raw data or promote model to Released.
"""
from __future__ import annotations
import argparse, hashlib, json, pathlib

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for v in iter(lambda:f.read(1024*1024),b''):h.update(v)
    return h.hexdigest()

def validate_comparisons(evidence):
    """Require A/B/C/D to share *all* comparable inference settings.

    Returns the eligible groups; no ClearML request is made here.
    """
    groups={}
    for x in evidence:
        if x.get('schema')!='identity-eval-v1.2':
            raise RuntimeError('Unsupported evaluation metadata version')
        if x.get('inference_engine')!='transformers+peft':
            raise RuntimeError('Unexpected evaluation engine')
        key=tuple(x.get(k) for k in ('cases_sha256','mode','seed','max_new_tokens',
              'temperature','top_p','top_k','base_manifest_files_sha256','inference_engine'))
        if any(k is None for k in key): raise RuntimeError('Missing comparable evaluation settings')
        cond=(bool(x['adapter_used']),bool(x.get('system_sha256')))
        conditions=groups.setdefault(key,{})
        if cond in conditions: raise RuntimeError('Duplicate A/B/C/D condition for same case group')
        conditions[cond]=x
    complete=[]
    expected={(False,False),(False,True),(True,False),(True,True)}
    for k,v in groups.items():
        if set(v)!=expected: raise RuntimeError('Incomplete A/B/C/D case group')
        if v[(False,True)]['system_sha256']!=v[(True,True)]['system_sha256']:
            raise RuntimeError('B and D must use EXACTLY the same System Prompt SHA-256')
        complete.append(k)
    if not complete: raise RuntimeError('No completed comparable case group')
    return complete


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run-manifest',required=True)
    p.add_argument('--reviewed-summary',required=True,
                   help='Reviewer-approved summary WITHOUT raw cases or individual answers')
    p.add_argument('--eval-metadata',nargs='+',required=True)
    args=p.parse_args()
    run=json.loads(pathlib.Path(args.run_manifest).read_text(encoding='utf-8'))
    if run.get('status')!='TRAINED_CANDIDATE' or not run.get('clearml_task_id') or not run.get('clearml_output_model_id'):
        raise RuntimeError('Training Task and OutputModel must be registered first')
    summary_file=pathlib.Path(args.reviewed_summary)
    summary=json.loads(summary_file.read_text(encoding='utf-8'))
    if not summary.get('reviewer_ref') or not summary.get('conclusion'):
        raise RuntimeError('Require actual independent reviewer reference and explicit conclusion')
    items=[]
    evidence=[]
    for name in args.eval_metadata:
        x=json.loads(pathlib.Path(name).read_text(encoding='utf-8'))
        if x.get('run_id')!=run['run_id'] or x.get('train_task_id')!=run['clearml_task_id']:
            raise RuntimeError(f'Evaluation run/task mismatch: {name}')
        if x.get('adapter_package_sha256')!=run['adapter_package_sha256']:
            raise RuntimeError(f'Evaluation Adapter version mismatch: {name}')
        if x.get('base_manifest_files_sha256')!=run.get('base_files_sha256'):
            raise RuntimeError(f'Evaluation base model mismatch: {name}')
        if bool(x.get('adapter_used')) and not run.get('adapter_files'):
            raise RuntimeError(f'No frozen Adapter files declared: {name}')
        output_file=pathlib.Path(str(name).removesuffix('.meta.json'))
        if not output_file.is_file() or sha(output_file)!=x['output_sha256']:
            raise RuntimeError(f'Evaluation output bytes do not match metadata: {name}')
        evidence.append(x)
        items.append({'meta_sha256':sha(name),'cases_sha256':x['cases_sha256'],
                      'output_sha256':x['output_sha256'],
                      'system_sha256':x.get('system_sha256'),'mode':x['mode'],
                      'adapter_used':x['adapter_used']})
    validate_comparisons(evidence)
    from clearml import Task
    task=Task.init(project_name='reg/identity-sft',task_name=f"{run['run_id']}-evaluation",
                   task_type=Task.TaskTypes.testing,reuse_last_task_id=False,
                   auto_connect_frameworks=False,auto_connect_arg_parser=False)
    try:
        task.set_parameter('identity/training_task_id',run['clearml_task_id'])
        task.set_parameter('identity/model_id',run['clearml_output_model_id'])
        task.set_parameter('identity/reviewer_ref',summary['reviewer_ref'])
        task.set_parameter('identity/conclusion',summary['conclusion'])
        task.upload_artifact('reviewed-summary',artifact_object=str(summary_file))
        # Upload metadata-only digest index; never upload raw individual predictions.
        temp=summary_file.parent/f"{run['run_id']}-eval-index.json"
        if temp.exists(): raise FileExistsError(temp)
        temp.write_text(json.dumps({'run_id':run['run_id'],'training_task_id':run['clearml_task_id'],
                     'model_id':run['clearml_output_model_id'],'eval_runs':items},
                     ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        task.upload_artifact('eval-digest-index',artifact_object=str(temp))
        task.close()
        print(json.dumps({'evaluation_task_id':task.id,'training_task_id':run['clearml_task_id'],
                          'model_id':run['clearml_output_model_id'],'status':'EVALUATED_NOT_RELEASED'},ensure_ascii=False))
    except BaseException as exc:
        try:task.mark_failed(status_reason=str(exc)[:180]);task.close()
        except Exception:pass
        raise
if __name__=='__main__':main()
