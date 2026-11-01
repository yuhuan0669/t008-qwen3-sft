"""Prepare an attention-only LoRA comparison; keep v0.1.22 data immutable."""
from pathlib import Path
import hashlib, importlib.util, json, shutil, subprocess

D=Path(__file__).resolve().parent;R=D.parents[2]
P=D.parent/'t008-v0122-20261101-031736'
H=D.parent/'t008-v0123-20261101-060130'
V=R/'stage1/variants/stage1-cpu-v0.1.22';E=D/'evaluation'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
assert not (D/'training-config.json').exists()
E.mkdir();commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
for n in ['.gitignore','run_local_sft.py','prepare_remote.py','collect_model.py','collect_raw.py','stage_inputs.py','preflight.py','execute.py']:
    s=(H/n).read_text().replace('candidate_v0.1.23','candidate_v0.1.24').replace('model-v0.1.23','model-v0.1.24').replace('stage1-cpu-v0.1.23','stage1-cpu-v0.1.22')
    if n=='execute.py':
        s=s.replace('always restore UAT','leave UAT paused until the user requests restoration')
        s=s.replace("event('Restoring original UAT')","event('Cleaning task GPU workloads; UAT remains paused by user instruction')")
        s=s.replace("str(D / 'window.py'), 'restore'","str(D / 'window.py'), 'cleanup'")
        s=s.replace("event('Original UAT restored; internal health verified')","event('Task GPU workloads removed; UAT intentionally remains paused')")
    if n=='run_local_sft.py':
        s=s.replace('Insufficient window; preserve recovery time','Insufficient experiment time; leave UAT paused')
    (D/n).write_text(s)
shutil.copyfile(V/'cpu-check/report.json',D/'cpu-report.json')
for n in ['prep-pod.json','job-smoke.json','job-full.json','eval-pod.json']:
    obj=json.loads((H/n).read_text().replace(H.name,D.name))
    spec=obj['spec']['template']['spec'] if 'template' in obj['spec'] else obj['spec']
    if n=='eval-pod.json':spec['activeDeadlineSeconds']=3600
    for c in spec['containers']:
        for env in c.get('env',[]):
            if env['name']=='SOURCE_GIT_COMMIT':env['value']=commit
    dump(D/n,obj)
cfg=json.loads((P/'training-config.json').read_text())
i=cfg['full_argv'].index('--target_modules');assert cfg['full_argv'][i+1]=='all-linear'
cfg['full_argv'][i+1:i+2]=['q_proj','k_proj','v_proj','o_proj']
cfg.update(plan='v0124-attention-only',model_version='v0.1.24',config_revision='v0.1.24-attention-only',
    execution_authorized=True,status='AUTHORIZED_FOR_ONE_FULL',
    recipe_change='Only target_modules: all-linear to q_proj k_proj v_proj o_proj; original v0.1.22 data/loss3 unchanged.',
    evaluation_config=str((E/'evaluation-config.json').relative_to(R)),
    final_candidate_policy='One fresh-base final-epoch candidate. No extra Full or deployment.',
    uat_policy='KEEP_PAUSED_UNTIL_EXPLICIT_USER_RESTORE',
    before_gpu=['Verify unchanged data/runtime/native encoding and attention-only module selection.'],
    expected_trainable_parameters=7667712)
dump(D/'training-config.json',cfg)
dump(D/'authorization.json',{
    'user_instruction':'继续。暂停UAT后，不用恢复，直到我说恢复。',
    'scope':'Original v0.1.22 data1047/identity234/loss3, only target_modules to attention q/k/v/o. Smoke3, fresh-base Full66, 208 Chinese responses. No deployment, extra Full, English or external Judge.',
    'data_sha256':cfg['dataset_sha256'],'dataset_version':'stage1-cpu-v0.1.22',
    'uat_pause_authorized':True,'automatic_restore_authorized':False,
    'uat_policy':'KEEP_PAUSED_UNTIL_EXPLICIT_USER_RESTORE'})
spec=importlib.util.spec_from_file_location('runner',D/'run_local_sft.py');runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
cmd=runner.build_command(cfg,'full','/base','/input','/runwork/outputs/full')
prior=json.loads((P/'expected-full-command.json').read_text())
j=prior.index('--target_modules');want=prior[:j+1]+['q_proj','k_proj','v_proj','o_proj']+prior[j+2:]
assert cmd==want,'Unexpected training command difference'
dump(D/'expected-full-command.json',cmd)
dump(D/'config-diff.json',{'reference':str((P/'expected-full-command.json').relative_to(R)),
    'training_parameter_changes':[{'flag':'--target_modules','before':['all-linear'],'after':['q_proj','k_proj','v_proj','o_proj']}],
    'dataset_changed':False,'dataset_rows':1047,'identity_exposures':234,'identity_loss_multiplier':3,
    'expected_trainable_parameters':7667712,'prior_trainable_parameters':21823488,
    'unchanged_artifacts':{str(p.relative_to(R)):sha(p) for p in [V/'train.jsonl',V/'identity_loss3.py',V/'identity-keys.json',V/'inference-system.txt',V/'cpu-check/report.json',R/'stage1/training/local_data_guard.py']}})
for n in ['system.txt','thinking-prefill.jinja','cases.json','base-files.json','decision-plan.json']:
    shutil.copyfile(H/'evaluation'/n,E/n)
ec=json.loads((H/'evaluation/evaluation-config.json').read_text().replace('candidate_v0.1.23','candidate_v0.1.24').replace('t008-diagnostic-v0123','t008-diagnostic-v0124').replace(H.name,D.name).replace('stage1-cpu-v0.1.23','stage1-cpu-v0.1.22'))
dump(E/'evaluation-config.json',ec)
slots=[{'group':g['name'],'model':'candidate_v0.1.24','case_id':q,'repeat':n} for g in ec['groups'] for q in g['case_ids'] for n in range(1,g['repeats']+1)]
assert len(slots)==208;dump(E/'missing-slots.json',slots)
binding=json.loads((H/'evaluation/runtime-binding.pending.json').read_text().replace('candidate_v0.1.23','candidate_v0.1.24').replace('t008-diagnostic-v0123','t008-diagnostic-v0124'))
assert binding['adapters']=={};dump(E/'runtime-binding.pending.json',binding)
(E/'run.py').write_text((H/'evaluation/run.py').read_text())
for n in ['prepare_review.py','summarize.py','write_review_delivery.py']:
    s=(H/'evaluation'/n).read_text().replace('candidate_v0.1.23','candidate_v0.1.24').replace('v0.1.23','v0.1.24')
    if n=='prepare_review.py':s=s.replace('t008-v0122-loss1-20261101-040341','t008-v0123-20261101-060130')
    (E/n).write_text(s)
valid={(s['group'],s['case_id'],s['repeat']) for s in slots}
saved=[json.loads(s) for s in (H/'evaluation/combined.jsonl').read_text().splitlines()]
models=['original_base','v0.1.14','candidate_v0.1.22']
selected=[r for r in saved if r['model'] in models and (r['group'],r['case_id'],r['repeat']) in valid]
assert len(selected)==624
(E/'reused-responses.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in selected))
dump(E/'reuse-summary.json',{'source':str((H/'evaluation/combined.jsonl').relative_to(R)),'source_sha256':sha(H/'evaluation/combined.jsonl'),
    'models':models,'slots':624,'selected_sha256':sha(E/'reused-responses.jsonl'),
    'caveat':'Frozen same cases/System/template/settings, historical batches and no paired request seed. No baseline regeneration.'})
inp=D/'inputs/evaluation';inp.mkdir(parents=True)
for n in ['system.txt','thinking-prefill.jinja','cases.json','evaluation-config.json','base-files.json']:shutil.copyfile(E/n,inp/n)
(D/'README.md').write_text('# v0.1.24 注意力 LoRA 对照\n\n仅把LoRA模块从all-linear改成q_proj/k_proj/v_proj/o_proj；数据直接复用v0.1.22的1047条，身份234次、loss×3及其余训练参数不变。原始基座新建候选，Smoke3＋Full66，新增208份中文回答，复用624份历史回答。\n\n用户已授权执行，并明确要求暂停后保持UAT暂停，直到其要求恢复。本次不部署、不追加训练、不推送；收尾只清理临时作业。\n\n[配置差异](config-diff.json) · [训练配置](training-config.json) · [判断规则](evaluation/decision-plan.json)\n')
print(json.dumps({'run':D.name,'data_sha256':sha(V/'train.jsonl'),'expected_trainable_parameters':7667712,'new_generations':208,'uat_automatic_restore':False}))
