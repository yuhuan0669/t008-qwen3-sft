"""Freeze one mode-allocation experiment and a 208-response Chinese comparison."""
from pathlib import Path
import hashlib, importlib.util, json, shutil, subprocess

D=Path(__file__).resolve().parent;R=D.parents[2]
P=D.parent/'t008-v0122-20261101-031736'
H=D.parent/'t008-v0122-loss1-20261101-040341'
V=R/'stage1/variants/stage1-cpu-v0.1.23';E=D/'evaluation'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def jl(p,rows):p.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in rows))
assert not (D/'training-config.json').exists()
E.mkdir();commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
for name in ['.gitignore','run_local_sft.py','prepare_remote.py','collect_model.py','collect_raw.py']:
    s=(P/name).read_text().replace('candidate_v0.1.22','candidate_v0.1.23').replace('model-v0.1.22','model-v0.1.23')
    if name=='run_local_sft.py':s=s.replace('total_seconds()-2400','total_seconds()-900')
    if name=='collect_raw.py':s=s.replace('556','208')
    (D/name).write_text(s)
for name in ['stage_inputs.py','preflight.py','execute.py','window.py']:
    s=(P/name).read_text().replace('stage1-cpu-v0.1.22','stage1-cpu-v0.1.23').replace('candidate_v0.1.22','candidate_v0.1.23')
    if name=='stage_inputs.py':
        s=s.replace("# Fresh infrastructure snapshot", "# Fresh infrastructure snapshot")
        s=s.replace("(O/'gpu-before.csv').write_bytes", "(O/'uat-preflight.json').write_text(json.dumps(uat,indent=2)+'\\n')\n(O/'gpu-before.csv').write_bytes")
    if name=='execute.py':s=s.replace('556','208').replace('timeout=6600','timeout=2700')
    if name=='window.py':
        s=s.replace('0087a3073bac5b36e3b865666ad9210a1d52ba04c32ecdaba83b4af4eb49b2bb',sha(V/'train.jsonl'))
        s=s.replace('datetime.timedelta(hours=4)','datetime.timedelta(minutes=90)').replace('datetime.timedelta(minutes=40)','datetime.timedelta(minutes=15)')
        old=s[s.index("'decision_ref':'")+len("'decision_ref':'"):s.index("','restoration_owner'")]
        s=s.replace(old,'Current user 你做吧 authorizes the agreed mode-allocation experiment: 64 existing Chinese general exposures become nonthinking, same answers, rows, identity234/loss3 and other parameters. One fresh-base Smoke3 and Full66, then 208 Chinese generations. Standing user permission 可无需授权就暂停UAT applies. Restore original UAT; no deployment or extra Full. 90-minute operational ceiling, not a user deadline.')
        s=s.replace('40 min before deadline','15 min before deadline')
    (D/name).write_text(s)
shutil.copyfile(V/'cpu-check/report.json',D/'cpu-report.json')
for name in ['prep-pod.json','job-smoke.json','job-full.json','eval-pod.json']:
    obj=json.loads((P/name).read_text().replace(P.name,D.name))
    spec=obj['spec']['template']['spec'] if 'template' in obj['spec'] else obj['spec']
    for c in spec['containers']:
        for env in c.get('env',[]):
            if env['name']=='SOURCE_GIT_COMMIT':env['value']=commit
    dump(D/name,obj)
cfg=json.loads((V/'training-config.json').read_text())
cfg.update(execution_authorized=True,status='AUTHORIZED_FOR_ONE_FULL',model_version='v0.1.23',
    evaluation_config=str((E/'evaluation-config.json').relative_to(R)),
    final_candidate_policy='One fresh-base final-epoch candidate. No extra Full or deployment.')
dump(D/'training-config.json',cfg)
dump(D/'authorization.json',{'user_instruction':'你做吧','standing_uat_instruction':'可无需授权就暂停UAT',
    'scope':'64 Chinese general exposures: retain one original thinking exposure and convert the other to empty think with identical visible body. Smoke3, fresh-base Full66, 208 Chinese responses; restore UAT and health. No deployment.',
    'data_sha256':cfg['dataset_sha256'],'dataset_version':cfg['data_version'],'english_optimization':False})
spec=importlib.util.spec_from_file_location('runner',D/'run_local_sft.py');runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
dump(D/'expected-full-command.json',runner.build_command(cfg,'full','/base','/input','/runwork/outputs/full'))
dump(D/'config-diff.json',{'reference':str((V/'training-config.json').relative_to(R)),
    'training_argv_unchanged':True,'training_parameter_changes':[], 'dataset_rows':1047,'identity_exposures':234,
    'data_sha256':sha(V/'train.jsonl'),'mode_changes':64,
    'unchanged_artifacts':{str(p.relative_to(R)):sha(p) for p in [V/'train.jsonl',V/'identity_loss3.py',V/'identity-keys.json',V/'inference-system.txt',R/'stage1/training/local_data_guard.py']}})
for n in ['system.txt','thinking-prefill.jinja','cases.json','base-files.json']:
    shutil.copyfile(P/'evaluation'/n,E/n)
assert sha(E/'system.txt')==sha(V/'inference-system.txt')
ec=json.loads((P/'evaluation/evaluation-config.json').read_text())
old_ec=json.loads((P/'evaluation/evaluation-config.json').read_text())
echo=old_ec['groups'][0]['case_ids'][:16]
identity=['D16-05','D16-06','D16-07','D16-08','E17-ID05','E17-ID06','E17-ID07','E17-ID08']
normal=['T021-R3300-G0243','T021-R3300-G1038','T021-R3300-G1403','T021-N300-N030',
    'T021-B6-G129','T021-R3300-G0741','T021-B7-R237','T021-B7-R072',
    'T021-C900-B3-N031','T021-C900-B4-N045','T021-B8-N009','T021-R3300-G0503']
ec['groups'][0]['case_ids']=echo+normal+identity+['D16-11','D16-12','E17-J03','E17-J04']
ec['groups'][1]['case_ids']=echo+identity
ec.update(models=['candidate_v0.1.23'],model_aliases={'candidate_v0.1.23':'t008-diagnostic-v0123'},
    planned_requests={'comparison_slots':832,'reusable_saved_slots':624,'new_generation_slots':208},
    selection='Frozen before training: first16 existing echo cases, 12 task/fact/boundary/control cases (including prior loops), all8 identities and4 JSON; retain original16 Thinking probes. Failure-enriched diagnostic, not population acceptance.',
    system_path=str((V/'inference-system.txt').relative_to(R)),cases_path=str((E/'cases.json').relative_to(R)))
slots=[{'group':g['name'],'model':'candidate_v0.1.23','case_id':q,'repeat':n} for g in ec['groups'] for q in g['case_ids'] for n in range(1,g['repeats']+1)]
assert len(slots)==208
dump(E/'evaluation-config.json',ec);dump(E/'missing-slots.json',slots)
for newg,oldg in zip(ec['groups'],old_ec['groups']):
    assert set(newg['case_ids'])<=set(oldg['case_ids']) and newg['repeats']==oldg['repeats']
binding=json.loads((P/'evaluation/runtime-binding.pending.json').read_text())
# Historical models are read from saved evidence; only the new adapter is loaded.
binding['adapters']={};binding['aliases']={'original_base':'octa-carbon-v1','candidate_v0.1.23':'t008-diagnostic-v0123'}
binding['total_missing']=208;dump(E/'runtime-binding.pending.json',binding)
(E/'run.py').write_text((P/'evaluation/run.py').read_text().replace('556','208'))
valid={(s['group'],s['case_id'],s['repeat']) for s in slots}
saved=[json.loads(s) for s in (H/'evaluation/combined.jsonl').read_text().splitlines()]
models=['original_base','v0.1.14','candidate_v0.1.22']
selected=[r for r in saved if r['model'] in models and (r['group'],r['case_id'],r['repeat']) in valid]
assert len(selected)==624 and len({(r['model'],r['group'],r['case_id'],r['repeat']) for r in selected})==624
jl(E/'reused-responses.jsonl',selected)
dump(E/'reuse-summary.json',{'source':str((H/'evaluation/combined.jsonl').relative_to(R)),
    'source_sha256':sha(H/'evaluation/combined.jsonl'),'models':models,'slots':624,
    'selected_sha256':sha(E/'reused-responses.jsonl'),
    'caveat':'Identical prompts, System, template and request settings. Different batches/times, no request seed. No new baseline calls.'})
inp=D/'inputs/evaluation';inp.mkdir(parents=True)
for n in ['system.txt','thinking-prefill.jinja','cases.json','evaluation-config.json','base-files.json']:shutil.copyfile(E/n,inp/n)
dump(E/'decision-plan.json',{'primary':'Compare with both v0.1.22 loss3 and v0.1.14, not only the immediate parent.',
    'promising_direction':'Echo and looping counts both decrease vs v0.1.22; task/fact failure counts do not increase; no-System complete identity does not decrease.',
    'stop':'If task behavior improves but identity fails or harms increase, no release or automatic extra training.',
    'acceptance':'208 failure-enriched outputs are directional diagnostics. Repeats are clustered by question; no formal significance or full acceptance claim.',
    'review':'Root reviews new visible outputs against frozen case criteria. Reuse corrected existing verdicts only for identical question/condition/answer. JSON syntax and values distinct.',
    'exclude':['New external Judge calls','English evaluation','Deployment','Additional Full']})
(D/'README.md').write_text('# v0.1.23 非思考监督对照\n\n'
    '64 条中文通用记录各把一次原有曝光改成空 think，正文不变；其余983行不变。1047行、身份234次及loss×3、学习率1e-4、r8/alpha32、1 epoch/66步保持。原始基座初始化一个新LoRA。\n\n'
    'CPU已逐行核验。运行Smoke3、Full66后，只新生成208份中文回答：非思考加System120、不加System72、思考加System16。原版、v0.1.14、v0.1.22×3同题624份已有回答直接复用。\n\n'
    '按冻结判据同时看复述、循环、正文完整性、任务完成、事实、身份和JSON；不把复述变少单独当作成功。样本富集历史问题，只判断方向，不代表总体合格率。\n\n'
    '当前用户授权执行及暂停UAT，完成恢复原配置、别名并核验健康。不发布、不追加训练、不自动推送。GPU阶段预计20—40分钟；90分钟为恢复上限。\n\n'
    '[数据](../../../stage1/variants/stage1-cpu-v0.1.23/README.md) · [评测配置](evaluation/evaluation-config.json) · [判断规则](evaluation/decision-plan.json)\n')
for p in list(D.glob('*.py'))+[E/'run.py']:compile(p.read_text(),str(p),'exec')
dump(D/'execution-code-binding.json',{'source_git_commit':commit,'new_slots':208,'full_steps':66,
    'sha256':{str(p.relative_to(D)):sha(p) for p in [*D.glob('*.py'),E/'run.py',D/'training-config.json',E/'evaluation-config.json',E/'missing-slots.json',*D.glob('*pod.json'),*D.glob('job-*.json')]}})
print(json.dumps({'run':D.name,'new_generations':208,'reused':624,'rows':1047,'full_steps':66}))
