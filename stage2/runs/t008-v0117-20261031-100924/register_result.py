"""Register this completed local diagnostic; preserve release and frozen data records."""
from pathlib import Path
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json

D = Path(__file__).resolve().parent
ROOT = D.parents[2]
RP = str(D.relative_to(ROOT))
VP = 'stage1/variants/stage1-cpu-v0.1.17'

def read(p): return json.loads(p.read_text())
def save(p, x): p.write_text(json.dumps(x, ensure_ascii=False, indent=2) + '\n')

def main():
    s=read(D/'evaluation/semantic-summary.json')
    assert s['unreviewed_slots']==0 and (D/'RESULT.md').exists()
    m=read(D/'outputs/full/run_manifest.json')
    status='TRAINED_DIAGNOSTIC_NOT_ACCEPTED_UAT_RESTORED'
    entry={'run_id':D.name,'status':status,'data_version':'stage1-cpu-v0.1.17',
           'data_sha256':m['data_sha256'],'rows':1357,'identity_exposures':234,
           'successful_full_runs':1,'interrupted_full_attempts':0,'global_step':85,'epoch':1.0,
           'task_id':m['task_id'],'output_model_id':m['clearml_output_model_id'],
           'adapter_package_sha256':m['adapter_package_sha256'],
           'local_model':'stage2/local-models/stage1-cpu-v0.1.17/adapter.zip',
           'run_manifest':RP+'/outputs/full/run_manifest.json','report':RP+'/RESULT.md',
           'verification':RP+'/execution-verification.json','semantic_summary':RP+'/evaluation/semantic-summary.json',
           'uat_restored':True,'quality_accepted':False,'formal_candidate_evaluation_executed':False,
           'comparison_slots':2224,'reused_slots':1066,'new_generation_requests':1158,
           'new_candidate_development_requests':556,'technical_retries':0,
           'english_identity_evaluated':False,'next_training_authorized':False,'new_model_deployed':False,
           'sync_status':'LOCAL_GIT_ONLY_CLEARML_TRAINING_ARTIFACTS',
           'selection':'Diagnostic only: partial echo reduction relative to v0.1.16; worse than v0.1.14 without System and a new same-question loop failure.',
           'completed_at_utc':datetime.now(timezone.utc).isoformat()}
    save(D/'execution-status.json',entry)
    state_path=ROOT/'control/CURRENT_STATE.json';state=read(state_path)
    if not (D/'current-state-before.json').exists(): save(D/'current-state-before.json',state)
    saved_serving=deepcopy(state['serving_current']);saved_release=deepcopy(state['latest_model_release'])
    data={'version':'stage1-cpu-v0.1.17','manifest':VP+'/manifest.json','train_path':VP+'/train.jsonl',
          'train_sha256':m['data_sha256'],'report':RP+'/RESULT.md','training_config':VP+'/training-config.json',
          'evaluation_config':VP+'/evaluation-config.json','rows':1357,'identity_exposures':234,'system_rows':175,
          'status':status,'cpu_validation_report':VP+'/cpu-check/report.json','system_path':VP+'/system.txt',
          'training_started':True,'training_authorized':True,'inference_executed':True,'uat_restored':True,
          'training_execution':RP+'/RESULT.md','status_scope':'Completed execution overlay; preparation files remain frozen historical snapshots.'}
    state.update(recorded_at_utc=datetime.now(timezone.utc).isoformat(),
                 current_user_request='Complete the authorized v0.1.17 controlled run and four-model review.',
                 source_of_current_direction='Direct user approval of one controlled run and three parallel answer reviewers.',
                 candidate='stage1-cpu-v0.1.17/checkpoint-85',candidate_quality='DIAGNOSTIC_NOT_ACCEPTED_NOT_RECOMMENDED_FOR_RELEASE',
                 current_execution_phase='v0.1.17 trained once and 2224-slot development comparison reviewed; prior UAT restored; no new model release.',
                 current_execution_plan=VP+'/PLAN.md',retraining_direction='V0117_COMPLETE_NO_AUTOMATIC_FURTHER_TRAINING',
                 latest_direction_source='The authorized single experiment has ended; a further training run has not been authorized.',
                 current_data_candidate=data,latest_trained_data_candidate=data,current_training_run=entry,
                 next_training_authorized=False,proposed_training_config=VP+'/training-config.json',
                 current_review={'version':'stage1-cpu-v0.1.17','report':RP+'/RESULT.md','cpu_check_completed':True,
                                 'execution_completed':True,'quality_accepted':False,'english_deferred':True},
                 current_execution_previous_state=RP+'/current-state-before.json',
                 latest_uat_restore_verification=RP+'/public-restoration-verification.json')
    assert state['serving_current']==saved_serving and state['latest_model_release']==saved_release
    save(state_path,state)
    p=ROOT/'registry/stage2.json';reg=read(p)
    old_entries=[reg.get('latest_execution'),read(D/'current-state-before.json').get('current_training_run')]
    prior=reg.setdefault('previous_executions',[])
    for x in old_entries:
        if x and x['run_id']!=D.name and x['run_id'] not in {v['run_id'] for v in prior}: prior.append(x)
    reg['latest_execution']=entry;reg['current_review']=state['current_review'];save(p,reg)
    p=ROOT/'registry/versions.json';reg=read(p)
    ds={'id':'stage1-cpu-v0.1.17','repository_path':VP+'/train.jsonl','sha256':m['data_sha256'],
        'rows':1357,'bytes':(ROOT/VP/'train.jsonl').stat().st_size,'storage':'git','manifest':VP+'/manifest.json',
        'frozen_snapshot_status':'CPU_CHECKED_PRE_EXECUTION_SNAPSHOT','current_execution':RP+'/RESULT.md'}
    if ds['id'] not in {x['id'] for x in reg['datasets']}:reg['datasets'].append(ds)
    old=reg['models'].get('latest_trained_candidate');history=reg['models'].setdefault('trained_candidate_history',[])
    if old and old['run_id']!=D.name and old['run_id'] not in {x['run_id'] for x in history}:history.append(old)
    reg['models']['latest_trained_candidate']=entry;save(p,reg)
    p=ROOT/'README.md';txt=p.read_text();anchor='**2026-10-31 v0.1.17受控验证完成：**'
    if anchor not in txt:
        title,rest=txt.split('\n',1)
        txt=title+'\n\n'+anchor+' 1357条曝光不变，仅转换32次通用曝光为空思考；一次85步Full、2224份四模型开发对照及逐份审核完成。复述较v0.1.16减少，但无System仍不及v0.1.14，并出现新的本轮循环截断案例；保留为诊断候选，未发布。UAT原配置和别名已恢复且健康。['+'结果与后续建议]('+RP+'/RESULT.md)。\n'+rest
        p.write_text(txt)
    p=D/'README.md';txt=p.read_text().replace('状态为执行中；以最终执行报告和恢复证据为准。','状态：训练、生成和内容审核完成；候选未通过退化修复目标。UAT已恢复，未发布新模型。详见[结果与建议](RESULT.md)。');p.write_text(txt)
    print('Registered completed diagnostic; preserved serving_current and latest_model_release.')

if __name__=='__main__': main()
