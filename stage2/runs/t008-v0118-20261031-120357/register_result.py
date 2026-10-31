"""Register one completed diagnostic model while retaining the canonical v0.1.17 dataset."""
from pathlib import Path
from copy import deepcopy
from datetime import datetime,timezone
import json
D=Path(__file__).resolve().parent;R=D.parents[2];RP=str(D.relative_to(R));VP='stage1/variants/stage1-cpu-v0.1.17'
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def main():
    s=read(D/'evaluation/semantic-summary.json');assert s['unreviewed_slots']==0 and (D/'RESULT.md').exists()
    assert read(D/'execution-verification.json')['status']=='PASS' and read(D/'cleanup.json')['verified']
    m=read(D/'outputs/full/run_manifest.json');now=datetime.now(timezone.utc).isoformat()
    status='TRAINED_DIAGNOSTIC_NOT_ACCEPTED_UAT_RESTORED'
    entry={'run_id':D.name,'model_version':'v0.1.18','status':status,'data_version':'stage1-cpu-v0.1.17',
      'data_sha256':m['data_sha256'],'rows':1357,'identity_exposures':234,'learning_rate':5e-5,
      'only_hyperparameter_change':'learning_rate 1e-4 -> 5e-5 relative to v0.1.17',
      'successful_full_runs':1,'interrupted_full_attempts':0,'global_step':85,'epoch':1.0,
      'task_id':m['task_id'],'output_model_id':m['clearml_output_model_id'],'adapter_package_sha256':m['adapter_package_sha256'],
      'local_model':'stage2/local-models/model-v0.1.18/adapter.zip','run_manifest':RP+'/outputs/full/run_manifest.json',
      'training_config':RP+'/training-config.json','report':RP+'/RESULT.md','verification':RP+'/execution-verification.json',
      'semantic_summary':RP+'/evaluation/semantic-summary.json','uat_restored':True,'quality_accepted':False,
      'formal_candidate_evaluation_executed':False,'comparison_slots':2780,'reused_slots':2224,'new_generation_requests':556,
      'technical_retries':0,'english_identity_evaluated':False,'next_training_authorized':False,'new_model_deployed':False,
      'sync_status':'LOCAL_GIT_ONLY_CLEARML_TRAINING_ARTIFACTS','selection':(D/'CONCLUSION.md').read_text().strip(),
      'completed_at_utc':now}
    save(D/'execution-status.json',entry)
    p=R/'control/CURRENT_STATE.json';state=read(p)
    if not (D/'current-state-before.json').exists():save(D/'current-state-before.json',state)
    oldstate=read(D/'current-state-before.json');serving=deepcopy(state['serving_current']);release=deepcopy(state['latest_model_release'])
    data=deepcopy(state['current_data_candidate']);assert data['version']=='stage1-cpu-v0.1.17'
    data.update(report=RP+'/RESULT.md',training_config=RP+'/training-config.json',evaluation_config=RP+'/evaluation/evaluation-config.json',
      status=status,training_execution=RP+'/RESULT.md',model_version='v0.1.18',
      status_scope='Same v0.1.17 dataset reused unchanged for a separate v0.1.18 model experiment; no v0.1.18 dataset created.')
    state.update(recorded_at_utc=now,current_user_request='Complete the authorized fixed-data lower-learning-rate experiment.',
      source_of_current_direction='User continued the proposed single learning-rate control; standing UAT-pause and parallel-review authorization retained.',
      candidate='model-v0.1.18/checkpoint-85',candidate_quality='DIAGNOSTIC_NOT_ACCEPTED_NOT_RECOMMENDED_FOR_RELEASE',
      current_execution_phase='v0.1.18 single Full and 556 new generations completed; 2780-slot comparison reviewed; UAT restored; not deployed.',
      current_execution_plan=RP+'/README.md',retraining_direction='V0118_COMPLETE_NO_AUTOMATIC_FURTHER_TRAINING',
      latest_direction_source='Authorized single run completed; no further run started or automatically authorized.',
      current_data_candidate=data,latest_trained_data_candidate=data,current_training_run=entry,
      next_training_authorized=False,proposed_training_config=RP+'/training-config.json',
      current_review={'version':'model-v0.1.18','data_version':'stage1-cpu-v0.1.17','report':RP+'/RESULT.md','execution_completed':True,'quality_accepted':False,'english_deferred':True},
      current_execution_previous_state=RP+'/current-state-before.json',latest_uat_restore_verification=RP+'/public-restoration-verification.json')
    state['current_plan']['latest_run_report']=RP+'/RESULT.md'
    assert state['serving_current']==serving and state['latest_model_release']==release
    save(p,state)
    p=R/'registry/stage2.json';reg=read(p);history=reg.setdefault('previous_executions',[])
    for old in [reg.get('latest_execution'),oldstate.get('current_training_run')]:
      if old and old['run_id']!=D.name and old['run_id'] not in {x['run_id'] for x in history}:history.append(old)
    reg['latest_execution']=entry;reg['current_review']=state['current_review'];save(p,reg)
    p=R/'registry/versions.json';reg=read(p);old=reg['models'].get('latest_trained_candidate');history=reg['models'].setdefault('trained_candidate_history',[])
    if old and old['run_id']!=D.name and old['run_id'] not in {x['run_id'] for x in history}:history.append(old)
    reg['models']['latest_trained_candidate']=entry;save(p,reg)
    (R/'stage2/current-v0118-run.txt').write_text(D.name+'\n')
    p=R/'README.md';txt=p.read_text();anchor='**2026-10-31 v0.1.18学习率对照完成：**'
    if anchor not in txt:
      title,rest=txt.split('\n',1)
      p.write_text(title+'\n\n'+anchor+' 数据仍为v0.1.17的1357条，仅将学习率降至5e-5；一次Full、556份新回答及五模型对照审核完成。候选未发布，UAT恢复原配置并健康。['+'结果与下一步]('+RP+'/RESULT.md)。\n'+rest)
    p=D/'README.md';txt=p.read_text()
    if '[已完成结果]' not in txt:p.write_text(txt+'\n[已完成结果](RESULT.md)：训练、生成、审核和UAT恢复均已完成；未发布新模型。\n')
    print('Registered model v0.1.18; dataset remains v0.1.17; serving records preserved.')
if __name__=='__main__':main()
