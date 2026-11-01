"""Prepare one identity-source ablation; use existing frozen data and comparison."""
from pathlib import Path
import hashlib, importlib.util, json, shutil, subprocess
D=Path(__file__).resolve().parent;R=D.parents[2];E=D/'evaluation'
P=D.parent/'t008-v0125-kl-20261101-084231';B=D.parent/'t008-v0122-20261101-031736'
A=D.parent/'t008-v0124-attn-20261101-070053';V=R/'stage1/variants/stage1-cpu-v0.1.22'
G=R/'stage2/diagnostics/source-gradient-20261101'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
assert not (D/'training-config.json').exists()
E.mkdir();commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
for n in ['.gitignore','prepare_remote.py','preflight.py','collect_model.py','collect_raw.py','finish_collection.py','execute.py','window.py','stage_inputs.py']:
    s=(P/n).read_text().replace('candidate_v0.1.25','candidate_v0.1.26').replace('model-v0.1.25','model-v0.1.26')
    if n=='execute.py':s=s.replace("assert m['retention_metrics_verified']", "assert m['identity_zero_audit_verified']")
    if n=='stage_inputs.py':s=s.replace("for n in ['retention.py','retention-config.json','membership.json']:files['stage2/variants/base-retention-review/'+n]=(O/'retention'/n).read_text()", "for n in ['identity_zero.py','config.json','membership.json']:files['ablation/'+n]=(O/'ablation'/n).read_text()")
    (D/n).write_text(s)
s=(A/'run_local_sft.py').read_text().replace("expected={'q_proj','k_proj','v_proj','o_proj'}", "expected={'q_proj','k_proj','v_proj','o_proj','gate_proj','up_proj','down_proj'}").replace('==7667712','==21823488')
s=s.replace("import torch\n", "gpu_before=subprocess.check_output(['nvidia-smi','--query-gpu=name,memory.used,memory.total,utilization.gpu','--format=csv,noheader'],text=True).strip()\n import torch\n")
s=s.replace("save();task=None", """audit_path=out/'identity-zero-audit.jsonl'
 os.environ['T008_IDENTITY_ZERO_AUDIT']=str(audit_path)
 cfgpath=inp/'ablation/config.json'
 assert os.environ['T008_IDENTITY_ZERO_CONFIG']==str(cfgpath)
 acfg=json.loads(cfgpath.read_text());members=json.loads(cfgpath.with_name('membership.json').read_text())['members']
 assert sha(cfgpath.with_name('membership.json'))==acfg['membership_sha256']
 assert acfg['dataset_sha256']==spec['dataset_sha256']
 meta['identity_zero']={'config_sha256':sha(cfgpath),'plugin_sha256':sha(cfgpath.with_name('identity_zero.py')),'identity_rows':234,'labels_and_denominator_preserved':True}
 meta['gpu_before']=gpu_before
 save();task=None""")
s=s.replace("ck=latest_adapter(out/'checkpoints');", """audit=[json.loads(line) for line in audit_path.read_text().splitlines()]
  assert audit and all(x['weighted_after']==(0 if x['identity'] else x['weighted_before']) for x in audit)
  assert all(x['num_items_in_batch']>0 for x in audit)
  if a.mode=='full':
   from collections import Counter
   assert len(audit)==1047 and sum(x['identity'] for x in audit)==234
   assert Counter(x['key'] for x in audit)==Counter({k:v['multiplicity'] for k,v in members.items()})
   assert sum(x['valid_tokens'] for x in audit)==928890
   assert sum(x['weighted_after'] for x in audit)==920027
  for start in range(0,len(audit),16):
   group=audit[start:start+16]
   assert all(x['num_items_in_batch']==sum(y['valid_tokens'] for y in group) for x in group)
  meta['identity_zero_audit_verified']=True
  meta['identity_zero_audit']={'rows':len(audit),'identity_rows':sum(x['identity'] for x in audit),'valid_tokens':sum(x['valid_tokens'] for x in audit),'weighted_after':sum(x['weighted_after'] for x in audit),'sha256':sha(audit_path)}
  ck=latest_adapter(out/'checkpoints');""")
(D/'run_local_sft.py').write_text(s)
cfg=json.loads((B/'training-config.json').read_text())
cfg['full_argv'].append('/work/ablation/identity_zero.py')
cfg.update(plan='identity-source-zero-ablation',model_version='v0.1.26',candidate_model_version='v0.1.26',
 execution_authorized=True,status='AUTHORIZED_SMOKE3_FULL66_GENERATE208',expected_trainable_parameters=21823488,
 recipe_change='Only zero loss_scale at native compute_loss for234 identity-source rows; labels, batch denominator, row order and schedule retained.',
 final_candidate_policy='One diagnostic final-epoch candidate. No extra Full or deployment.',
 evaluation_config=str((E/'evaluation-config.json').relative_to(R)),
 before_gpu=['Verify held UAT pause, frozen data, actual CPU loss masking and free GPU.'],
 uat_policy='KEEP_PAUSED_UNTIL_EXPLICIT_USER_RESTORE',
 environment={'T008_IDENTITY_ZERO_CONFIG':'/input/ablation/config.json'})
save(D/'training-config.json',cfg);shutil.copyfile(V/'cpu-check/report.json',D/'cpu-report.json')
members={}
for row in json.loads((G/'results/encoded-training.json').read_text()):
    key=hashlib.sha256(json.dumps(row['input_ids'],separators=(',',':')).encode()).hexdigest()
    assert key not in members
    members[key]={'identity':row['group']=='identity','group':row['group'], 'valid_tokens':row['valid_tokens'], 'multiplicity':row['multiplicity']}
assert sum(x['multiplicity'] for x in members.values())==1047
save(D/'ablation/membership.json',{'members':members})
acfg=json.loads((P/'retention/retention-config.json').read_text())
acfg={k:acfg[k] for k in ['runtime_versions','native_trainer_sha256','dataset_sha256']}
acfg.update(membership_sha256=sha(D/'ablation/membership.json'),rows=1047,identity_rows=234,
 scope='Disable only identity-source CE; keep labels and native denominator;2 remaining business rows mention names.')
save(D/'ablation/config.json',acfg)
save(D/'authorization.json',{'user_instruction':'继续','scope':'Proceed step2 and3: identity-source zero supervision only, Smoke3, one fresh-base Full66 and208 Chinese responses; reuse historical controls. No deployment, external Judge, English, extra Full or auto-restore.',
 'prior_pause_instruction':'暂停UAT后，不用恢复，直到我说恢复。','data_sha256':cfg['dataset_sha256'],
 'uat_pause_authorized':True,'automatic_restore_authorized':False,'proposal_commit':commit,
 'proposal':str((G/'REPORT.md').relative_to(R))})
for n in ['prep-pod.json','job-smoke.json','job-full.json','eval-pod.json']:
    obj=json.loads((P/n).read_text().replace(P.name,D.name))
    spec=obj['spec']['template']['spec'] if 'template' in obj['spec'] else obj['spec']
    for c in spec['containers']:
        c['env']=[v for v in c.get('env',[]) if v['name']!='T008_RETENTION_CONFIG']
        for env in c['env']:
            if env['name']=='SOURCE_GIT_COMMIT':env['value']=commit
        if n.startswith('job-'):c['env'].append({'name':'T008_IDENTITY_ZERO_CONFIG','value':'/input/ablation/config.json'})
    save(D/n,obj)
spec=importlib.util.spec_from_file_location('wrapper',D/'run_local_sft.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
cmd=mod.build_command(cfg,'full','/base','/input','/runwork/outputs/full')
assert cmd==json.loads((B/'expected-full-command.json').read_text())+['/input/ablation/identity_zero.py']
save(D/'expected-full-command.json',cmd)
save(D/'config-diff.json',{'reference':str((B/'training-config.json').relative_to(R)),
 'only_semantic_change':'Identity-source loss weights0 inside compute_loss, after native encoding; original identity plugin and labels unchanged.',
 'rows':1047,'identity_rows_zeroed':234,'remaining_supervised_rows':813,'unweighted_denominator_tokens':928890,
 'weighted_token_units_before':946600,'weighted_token_units_after':920027,'steps':66,'seed':42,
 'remaining_business_name_mentions_one_based':[975,994],
 'unchanged_artifacts':{str(p.relative_to(R)):sha(p) for p in [V/'train.jsonl',V/'identity_loss3.py',V/'identity-keys.json',V/'inference-system.txt',V/'cpu-check/report.json',R/'stage1/training/local_data_guard.py']}})
for n in ['system.txt','thinking-prefill.jinja','cases.json','base-files.json','reused-responses.jsonl','reuse-summary.json']:
    shutil.copyfile(P/'evaluation'/n,E/n)
for n in ['evaluation-config.json','runtime-binding.pending.json']:
    s=(P/'evaluation'/n).read_text().replace('candidate_v0.1.25','candidate_v0.1.26').replace('t008-diagnostic-v0125','t008-diagnostic-v0126').replace(P.name,D.name)
    (E/n).write_text(s)
ec=json.loads((E/'evaluation-config.json').read_text())
slots=[{'group':g['name'],'model':'candidate_v0.1.26','case_id':q,'repeat':n} for g in ec['groups'] for q in g['case_ids'] for n in range(1,g['repeats']+1)]
assert len(slots)==208;save(E/'missing-slots.json',slots)
for n in ['run.py','prepare_review.py','summarize.py','write_review_delivery.py']:
    (E/n).write_text((P/'evaluation'/n).read_text().replace('candidate_v0.1.25','candidate_v0.1.26').replace('v0.1.25','v0.1.26'))
save(E/'decision-plan.json',{'frozen_before_training':True,'purpose':'Test whether identity-source supervision is necessary for observed task degradation, not release acceptance.',
 'baseline':'candidate_v0.1.22; original_base andv0.1.14 contextual controls',
 'primary':'Copy/loop occurrence and task/fact preservation, by same condition and same question; all first completed numbered slots retained.',
 'secondary':'Identity as expected ablation effect, JSON validity versus JSON values, stop/empty/length; Thinking is separate.',
 'interpretation':{'echo_down_tasks_facts_recover':'Supports identity-source contribution or interaction in this recipe, not proof every identity row is flawed.',
 'echo_persists':'234 identity-source rows are not necessary for all observed copying; remaining sources still need study.',
 'echo_down_facts_or_tasks_worse':'Does not meet combination goal.'},
 'limitations':'Historical unpaired no-seed responses and one training seed; failure-enriched diagnostic, not population error estimates.',
 'new_generations':208,'automatic_extra_full':False,'deployment':False})
inp=D/'inputs/evaluation';inp.mkdir(parents=True)
for n in ['system.txt','thinking-prefill.jinja','cases.json','evaluation-config.json','base-files.json']:shutil.copyfile(E/n,inp/n)
(D/'README.md').write_text('# v0.1.26 身份来源消融\n\n仅关闭234次身份来源的损失。保留v0.1.22全部1047行、标签、批次分母、曝光顺序、66步日程与其余参数；从原始基座新建LoRA。2条业务样本仍提及名称，本轮不同时更改。\n\nCPU核验后Smoke3、唯一Full66，新增208份中文回答，复用624份历史回答。诊断对照不用于发布；UAT保持暂停。\n\n[配置差异](config-diff.json) · [训练配置](training-config.json) · [判断规则](evaluation/decision-plan.json)\n')
print(json.dumps({'run':D.name,'rows':1047,'identity_zero':234,'new_generations':208}))
