"""Freeze a single learning-rate experiment, reusing immutable v0.1.17 data/evaluation."""
from pathlib import Path
import hashlib, importlib.util, json, shutil, subprocess

D=Path(__file__).resolve().parent
R=D.parents[2]
P=D.parent/'t008-v0117-20261031-100924'
V=R/'stage1/variants/stage1-cpu-v0.1.17'
E=D/'evaluation'
E.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def copy(name):shutil.copyfile(P/name,D/name)
assert not (D/'training-config.json').exists(),'Do not overwrite a frozen run'
for name in ['.gitignore','run_local_sft.py','stage_inputs.py','prepare_remote.py','cpu-report.json']:
    copy(name)
for name in ['prep-pod.json','job-smoke.json','job-full.json','eval-pod.json']:
    (D/name).write_text((P/name).read_text().replace(P.name,D.name))
cfg=json.loads((P/'training-config.json').read_text())
old=cfg['full_argv'].copy()
cfg['full_argv'][cfg['full_argv'].index('--learning_rate')+1]='5e-5'
# Dataset/plugin paths intentionally keep v0.1.17. Output version is metadata only.
cfg['full_argv'][cfg['full_argv'].index('--output_dir')+1]='/runwork/model-v0.1.18/full/checkpoints'
cfg.update(plan='controlled-learning-rate',model_version='v0.1.18',
    config_revision='lr5e-5-control-v0.1.18',
    recipe_change='Only peak learning rate changes from 1e-4 to 5e-5 relative to v0.1.17; same data bytes, order, exposures, System and loss weights.',
    parent_model_version='v0.1.17',
    runtime_validation='Reuse immutable v0.1.17 native CPU encoding evidence after data/plugin/tokenizer/runtime hash verification; learning rate does not affect encoding.',
    before_gpu=['Current continue instruction authorizes the proposed single learning-rate experiment.'],
    evaluation_config=str((E/'evaluation-config.json').relative_to(R)),
    final_candidate_policy='One fresh-base final-epoch diagnostic candidate; no automatic deployment or additional Full.')
dump(D/'training-config.json',cfg)
auth={'user_instruction':'继续','scope':'Continue the proposed fixed-data learning-rate experiment: one Smoke3 and one fresh-base Full85, 556 new generations, reuse prior controls. Existing authorization permits pausing UAT; restore and verify it. No deployment.',
      'model_version':'v0.1.18','dataset_version':'stage1-cpu-v0.1.17','data_sha256':cfg['dataset_sha256'],
      'known_content_issues_retained':True,'english_optimization':False}
dump(D/'authorization.json',auth)
assert sha(V/'train.jsonl')==cfg['dataset_sha256']
spec=importlib.util.spec_from_file_location('runner',D/'run_local_sft.py');runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
command=runner.build_command(cfg,'full','/base','/input','/runwork/outputs/full')
prior=json.loads((P/'expected-full-command.json').read_text())
diff=[{'index':i,'before':a,'after':b} for i,(a,b) in enumerate(zip(prior,command)) if a!=b]
assert len(prior)==len(command) and len(diff)==1 and diff[0]['before']=='1e-4' and diff[0]['after']=='5e-5'
dump(D/'expected-full-command.json',command)
dump(D/'config-diff.json',{'parent_run':str(P.relative_to(R)),'actual_full_command_changes':diff,
    'data_unchanged':True,'dataset_rows':1357,'identity_exposures':234,'data_sha256':sha(V/'train.jsonl'),
    'data_reference':str((V/'train.jsonl').relative_to(R)),
    'cpu_encoding_evidence_reused_from':str((P/'cpu-report.json').relative_to(R)),
    'unchanged_artifacts':{str(p.relative_to(R)):sha(p) for p in [V/'train.jsonl',V/'identity_loss3.py',V/'identity-keys.json',V/'system.txt',R/'stage1/training/local_data_guard.py']}})
for name in ['system.txt','thinking-prefill.jinja','cases.json','base-files.json']:
    shutil.copyfile(P/'evaluation'/name,E/name)
ec=json.loads((P/'evaluation/evaluation-config.json').read_text())
ec['models']=['candidate_v0.1.18']
ec['model_aliases']={'candidate_v0.1.18':'t008-diagnostic-v0118'}
ec['planned_requests']={'comparison_slots':2780,'reusable_saved_slots':2224,'new_generation_slots':556}
ec['reuse_manifest_path']='reuse-summary.json'
ec['historical_judge']='Reuse prior content labels for identical case+condition+answer; review new unique answers using the same frozen criteria.'
dump(E/'evaluation-config.json',ec)
slots=[{'group':g['name'],'model':'candidate_v0.1.18','case_id':q,'repeat':n} for g in ec['groups'] for q in g['case_ids'] for n in range(1,g['repeats']+1)]
assert len(slots)==556
dump(E/'missing-slots.json',slots)
binding=json.loads((P/'evaluation/runtime-binding.pending.json').read_text())
# Retain the same server settings and the two historical LoRA mounts; only the new alias changes.
binding['aliases'].pop('candidate_v0.1.17');binding['aliases']['candidate_v0.1.18']='t008-diagnostic-v0118'
binding['total_missing']=556
dump(E/'runtime-binding.pending.json',binding)
(E/'run.py').write_text((P/'evaluation/run.py').read_text().replace('1158','556'))
dump(E/'reuse-summary.json',{'source':str((P/'evaluation/combined.jsonl').relative_to(R)),
    'sha256':sha(P/'evaluation/combined.jsonl'),'slots':2224,
    'review_coverage_path':str((P/'evaluation/review-coverage.json').relative_to(R)),
    'review_coverage_sha256':sha(P/'evaluation/review-coverage.json'),
    'unchanged_eval_fields':['request_modes','groups','system_sha256','chat_template','cases_sha256','concurrency','max_model_len','seed_policy'],
    'caveat':'Different runtime/batching, no shared request seed; question-paired descriptive comparison, not independent acceptance.'})
for key in ['request_modes','groups','system_sha256','chat_template','cases_sha256','concurrency','max_model_len','seed_policy']:
    assert ec[key]==json.loads((P/'evaluation/evaluation-config.json').read_text())[key]
for name in ['execute.py','window.py']:
    s=(P/name).read_text().replace('candidate_v0.1.17','candidate_v0.1.18').replace('1158','556')
    if name=='window.py':
        s=s.replace("Current user 开始吧 after discussing controlled v0.1.17 with known data issues retained;", "Current user 继续 after the recommendation for a fixed-data lr 1e-4 to 5e-5 experiment; known data issues retained;")
        s='\n'.join(line.rstrip() for line in s.splitlines())+'\n'
    (D/name).write_text(s)
(D/'collect_model.py').write_text((P/'collect_model.py').read_text().replace('local-models/stage1-cpu-v0.1.17','local-models/model-v0.1.18'))
inp=D/'inputs/evaluation';inp.mkdir(parents=True)
for name in ['system.txt','thinking-prefill.jinja','cases.json','evaluation-config.json','base-files.json']:
    shutil.copyfile(E/name,inp/name)
uat=subprocess.check_output(['kubectl','--context','lmas00-direct','--request-timeout=20s','-n','vllm','get','deployment','vllm','-o','json'])
(D/'uat-preflight.json').write_bytes(uat)
assert json.loads(uat)['status']['readyReplicas']==1
dump(D/'execution-code-binding.json',{'new_slots':556,'full_command_only_change':'learning_rate: 1e-4 -> 5e-5',
    'sha256':{str(p.relative_to(D)):sha(p) for p in [*D.glob('*.py'),E/'run.py',D/'training-config.json',E/'evaluation-config.json',E/'missing-slots.json']}})
(D/'README.md').write_text('''# v0.1.18 学习率对照

相对 v0.1.17，实际 Full 命令仅将学习率 `1e-4` 改为 `5e-5`。模型版本是 v0.1.18，数据继续引用 `stage1-cpu-v0.1.17`，1357 条及曝光次数不变；已知内容问题保留。本轮从原始基座新建 LoRA，不续训旧候选。

执行一次 3 步 Smoke、一次 85 步 Full；只取最终 epoch。新候选生成 556 份中文回答，复用此前四模型 2224 份结果及相同问答的审核记录。保持原 System、修正后模板、Schema、推理参数和判据，不增加英文或 Judge 调用，不自动发布。

核验配置、运行字节及资源后暂停 UAT 模型服务；GPU 作业退出后恢复原配置并核验健康。GPU 预计 25–40 分钟，语义审核随后完成。

本轮用于检验更新幅度是否影响退化，不将学习率变化视为数据质量修复。数据编码复用已有同字节的 Swift CPU 检查，不虚称重新编码。结果看复述、事实、任务交付、身份、循环及截断，不能仅看训练 loss。

[配置差异](config-diff.json) · [训练配置](training-config.json) · [评测配置](evaluation/evaluation-config.json)
''')
(D/'progress.md').write_text('# v0.1.18 执行记录\n\n- 计划与输入冻结完成。唯一训练参数变化：lr 1e-4 → 5e-5。\n- 复用 v0.1.17 数据和 CPU 编码证据；不创建重复数据版本。\n- 旧模型回答和已审核相同回答复用，只审核新增回答。\n- 尚未暂停 UAT、训练或生成。\n')
print(json.dumps({'run':str(D),'data_rows':1357,'new_slots':556,'command_diff':diff},ensure_ascii=False))
