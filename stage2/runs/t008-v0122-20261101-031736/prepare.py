"""Prepare one authorized v0.1.22 run from frozen data and proven executors."""
from pathlib import Path
import hashlib, importlib.util, json, shutil, subprocess

D=Path(__file__).resolve().parent; R=D.parents[2]
P=D.parent/'t008-v0118-20261031-120357'
B=D.parent/'t008-v0117-20261031-100924'
V=R/'stage1/variants/stage1-cpu-v0.1.22'; E=D/'evaluation'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x): p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
assert not (D/'training-config.json').exists()
E.mkdir(); source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
for name in ['.gitignore','run_local_sft.py','prepare_remote.py']:
    shutil.copyfile(P/name,D/name)
with (D/'.gitignore').open('a') as f: f.write('execution.log\nexecution-pid.txt\nevaluation/semantic-review/\n')
shutil.copyfile(V/'cpu-check/report.json',D/'cpu-report.json')
for name in ['prep-pod.json','job-smoke.json','job-full.json','eval-pod.json']:
    obj=json.loads((P/name).read_text().replace(P.name,D.name))
    spec=obj['spec'].get('template',obj)['spec'] if 'template' in obj['spec'] else obj['spec']
    for c in spec['containers']:
        for env in c.get('env',[]):
            if env['name']=='SOURCE_GIT_COMMIT': env['value']=source_commit
    dump(D/name,obj)
cfg=json.loads((V/'training-config.json').read_text())
frozen_cfg=json.loads((V/'training-config.json').read_text())
cfg.update(execution_authorized=True,status='AUTHORIZED_FOR_ONE_FULL',model_version='v0.1.22',
    before_gpu=['Current user 开始吧 authorizes the agreed single-candidate training and 556-answer comparison; standing authorization permits pausing UAT.'],
    evaluation_config=str((E/'evaluation-config.json').relative_to(R)),
    final_candidate_policy='One fresh-base final-epoch diagnostic candidate; no automatic additional Full or deployment.',
    runtime_validation='Reuse frozen native CPU encoding after identical data, plugin, tokenizer and installed runtime verification.')
assert cfg['full_argv']==frozen_cfg['full_argv'] and cfg['estimated_full_optimizer_steps']==66
dump(D/'training-config.json',cfg)
dump(D/'authorization.json',{'user_instruction':'开始吧','standing_uat_instruction':'可无需授权就暂停UAT',
    'scope':'One Smoke3, one fresh-base Full66 using frozen v0.1.22 and unchanged recipe; 556 Chinese generations; restore original UAT and verify health. No deployment or additional Full.',
    'data_sha256':cfg['dataset_sha256'],'dataset_version':cfg['data_version'],'english_optimization':False})
spec=importlib.util.spec_from_file_location('runner',D/'run_local_sft.py');runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
dump(D/'expected-full-command.json',runner.build_command(cfg,'full','/base','/input','/runwork/outputs/full'))
dump(D/'config-diff.json',{'reference':str((V/'training-config.json').relative_to(R)),
    'training_argv_unchanged':True,'training_parameter_changes':[],
    'dataset_rows':1047,'identity_exposures':234,'data_sha256':sha(V/'train.jsonl'),
    'cpu_encoding_evidence_reused_from':str((V/'cpu-check/report.json').relative_to(R)),
    'unchanged_artifacts':{str(p.relative_to(R)):sha(p) for p in [V/'train.jsonl',V/'identity_loss3.py',V/'identity-keys.json',V/'inference-system.txt',R/'stage1/training/local_data_guard.py']}})
for name in ['system.txt','thinking-prefill.jinja','cases.json','base-files.json']:
    shutil.copyfile(B/'evaluation'/name,E/name)
assert sha(E/'system.txt')==sha(V/'inference-system.txt')
ec=json.loads((B/'evaluation/evaluation-config.json').read_text())
ec['models']=['candidate_v0.1.22']; ec['model_aliases']={'candidate_v0.1.22':'t008-diagnostic-v0122'}
ec['planned_requests']={'comparison_slots':2224,'reusable_saved_slots':1668,'new_generation_slots':556}
ec['reuse_manifest_path']='reuse-summary.json'
ec['historical_judge']='Reuse labels only for identical case, condition and answer bytes; review new answers with the same criteria. No new external Judge calls.'
dump(E/'evaluation-config.json',ec)
for key in ['request_modes','groups','system_sha256','chat_template','cases_sha256','concurrency','max_model_len','seed_policy']:
    assert ec[key]==json.loads((B/'evaluation/evaluation-config.json').read_text())[key]
slots=[{'group':g['name'],'model':'candidate_v0.1.22','case_id':q,'repeat':n} for g in ec['groups'] for q in g['case_ids'] for n in range(1,g['repeats']+1)]
assert len(slots)==556; dump(E/'missing-slots.json',slots)
binding=json.loads((P/'evaluation/runtime-binding.pending.json').read_text())
binding['aliases'].pop('candidate_v0.1.18');binding['aliases']['candidate_v0.1.22']='t008-diagnostic-v0122'
binding['total_missing']=556; dump(E/'runtime-binding.pending.json',binding)
shutil.copyfile(P/'evaluation/run.py',E/'run.py')
old=[json.loads(x) for x in (B/'evaluation/combined.jsonl').read_text().splitlines()]
selected=[x for x in old if x['model'] in ['original_base','v0.1.14','v0.1.16']]
assert len(selected)==1668
(E/'reused-responses.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in selected))
dump(E/'reuse-summary.json',{'source':str((B/'evaluation/combined.jsonl').relative_to(R)),
    'source_sha256':sha(B/'evaluation/combined.jsonl'),'selected_models':['original_base','v0.1.14','v0.1.16'],
    'slots':1668,'selected_sha256':sha(E/'reused-responses.jsonl'),
    'review_coverage_path':str((B/'evaluation/review-coverage.json').relative_to(R)),
    'review_coverage_sha256':sha(B/'evaluation/review-coverage.json'),
    'caveat':'Same frozen prompts/protocol; no shared request seed and different runtime batching. Diagnostic paired description, not independent acceptance.'})
for name in ['stage_inputs.py','preflight.py']:
    s=(P/name).read_text().replace('stage1-cpu-v0.1.17','stage1-cpu-v0.1.22')
    if name=='preflight.py':
        s=s.replace("json.loads((V/'FILES.sha256.json').read_text())","json.loads((V/'FILES.sha256.json').read_text())['files']")
        s=s.replace("for n,i in frozen.items():assert sha(V/n)==i['sha256'],n","for n,h in frozen.items():assert sha(V/n)==h,n")
    (D/name).write_text(s)
for name in ['execute.py','window.py','collect_model.py']:
    s=(P/name).read_text().replace('candidate_v0.1.18','candidate_v0.1.22').replace('model-v0.1.18','model-v0.1.22')
    s=s.replace('else 85','else 66').replace("m['global_step']==85","m['global_step']==66")
    if name=='window.py':
        s=s.replace('bf5f1aee58d48a510b84669fa351065621e84037b160da91e82cf8cd1b69dc28',cfg['dataset_sha256'])
        s=s.replace('Current user 继续 after the recommendation for a fixed-data lr 1e-4 to 5e-5 experiment; known data issues retained;', 'Current user 开始吧 authorizes frozen v0.1.22, identity loss3, unchanged parameters and one fresh-base Full66;')
    (D/name).write_text(s)
inp=D/'inputs/evaluation';inp.mkdir(parents=True)
for name in ['system.txt','thinking-prefill.jinja','cases.json','evaluation-config.json','base-files.json']:
    shutil.copyfile(E/name,inp/name)
uat=subprocess.check_output(['kubectl','--context','lmas00-direct','--request-timeout=20s','-n','vllm','get','deployment','vllm','-o','json'])
(D/'uat-preflight.json').write_bytes(uat);assert json.loads(uat)['status']['readyReplicas']==1
dump(D/'execution-code-binding.json',{'source_git_commit':source_commit,'source_commit_role':'Frozen source/data baseline; execution scripts bound by the following file hashes.',
    'new_slots':556,'full_steps':66,'training_recipe_unchanged':True,
    'sha256':{str(p.relative_to(D)):sha(p) for p in [*D.glob('*.py'),E/'run.py',D/'training-config.json',E/'evaluation-config.json',E/'missing-slots.json',*D.glob('*pod.json'),*D.glob('job-*.json')]}})
(D/'README.md').write_text('''# v0.1.22 清洗数据训练与对照

使用冻结的 v0.1.22 数据（1047条，身份234次曝光），原始 Qwen3-8B 加新 LoRA，身份损失×3，训练参数保持不变。先完成3步 Smoke，再从基座独立初始化一次1 epoch Full，预计66步。只取最终权重，不自动增加训练或发布。

新候选生成556份中文回答：非思考加System 420份、非思考不加System 120份、思考加System 16份。复用同协议原版、v0.1.14、v0.1.16共1668份回答；保存原始响应，技术重试不择优。评价复述、循环、截断、任务完成、事实、身份、JSON及业务边界，并观察对冲句式和身份尾语。此集用于诊断，不作为正式验收。

数据编码复用已核验同字节的原生Swift CPU结果，开训前核验运行库及输入哈希。CPU检查采用raise，训练保持delete，但成员守卫要求1047条完整进入训练，任何丢行都会报错。

用户已授权开始及暂停UAT。GPU阶段预计30—60分钟，之后完成语义复核。恢复原Deployment、模型别名并核验健康；应用配置不变。文件先本地保存，不自动推送。

[训练配置](training-config.json) · [配置核对](config-diff.json) · [评测配置](evaluation/evaluation-config.json)
''')
(D/'progress.md').write_text('# 执行记录\n\n- 冻结数据、配置、556次新生成和1668份复用对照。\n- 已准备恢复脚本；尚未暂停UAT或训练。\n')
print(json.dumps({'run':str(D),'rows':1047,'full_steps':66,'new_generations':556,'reused':1668},ensure_ascii=False))
