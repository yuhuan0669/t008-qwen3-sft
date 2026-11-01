"""Prepare exactly the approved base-retention experiment; no workloads launched here."""
from pathlib import Path
from copy import deepcopy
import hashlib,importlib.util,json,shutil,subprocess
D=Path(__file__).resolve().parent;R=D.parents[2]
P=D.parent/'t008-v0124-attn-20261101-070053';B=D.parent/'t008-v0122-20261101-031736'
V=R/'stage1/variants/stage1-cpu-v0.1.22';Q=R/'stage2/variants/base-retention-review';E=D/'evaluation'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
for n,h in json.loads((Q/'manifest.json').read_text())['files_sha256'].items():assert sha(Q/n)==h,n
assert not (D/'training-config.json').exists()
E.mkdir();commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
for n in ['.gitignore','prepare_remote.py','preflight.py','collect_model.py','collect_raw.py','finish_collection.py','execute.py','run_local_sft.py']:
 s=(P/n).read_text().replace('candidate_v0.1.24','candidate_v0.1.25').replace('model-v0.1.24','model-v0.1.25')
 if n=='run_local_sft.py':
  s=s.replace("expected={'q_proj','k_proj','v_proj','o_proj'}","expected={'q_proj','k_proj','v_proj','o_proj','gate_proj','up_proj','down_proj'}")
  s=s.replace('==7667712','==21823488')
  s=s.replace("import torch\n", "gpu_before=subprocess.check_output(['nvidia-smi','--query-gpu=name,memory.used,memory.total,utilization.gpu','--format=csv,noheader'],text=True).strip()\n import torch\n")
  s=s.replace("save();task=None", """rcfg=inp/'stage2/variants/base-retention-review/retention-config.json'
 assert os.environ['T008_RETENTION_CONFIG']==str(rcfg)
 rconf=json.loads(rcfg.read_text())
 assert rconf['coefficient']==1 and rconf['temperature']==1 and rconf['dataset_sha256']==spec['dataset_sha256']
 assert sha(rcfg.with_name('membership.json'))==rconf['membership_sha256']
 meta['retention']={'coefficient':1,'temperature':1,'config_sha256':sha(rcfg),'plugin_sha256':sha(rcfg.with_name('retention.py')),'membership_sha256':rconf['membership_sha256'],'retention_rows':770}
 meta['gpu_before']=gpu_before
 save();task=None""")
  s=s.replace("ck=latest_adapter(out/'checkpoints');", """kl=[p['value'] for p in metrics if 'retention_kl_general_microbatch_mean' in p['tag']]
  assert kl and all(math.isfinite(v) for v in kl) and max(kl)>1e-8,'No observed KL activity'
  assert any('sft_loss_accum_scaled' in p['tag'] for p in metrics)
  assert any('retention_loss_accum_scaled' in p['tag'] for p in metrics)
  meta['retention_metrics_verified']=True
  ck=latest_adapter(out/'checkpoints');""")
 if n=='execute.py':
  s=s.replace("assert m['training_verified'] and m['global_step']", "assert m['retention_metrics_verified']\n    assert m['training_verified'] and m['global_step']")
 (D/n).write_text(s)
cfg=json.loads((Q/'training-config.json').read_text())
cfg.update(model_version='v0.1.25',candidate_model_version='v0.1.25',execution_authorized=True,
 status='AUTHORIZED_FOR_SMOKE3_AND_ONE_FULL',expected_trainable_parameters=21823488,
 final_candidate_policy='One fresh-base final-epoch candidate. No automatic extra Full or deployment.',
 evaluation_config=str((E/'evaluation-config.json').relative_to(R)),
 before_gpu=['User continued the concrete reviewed proposal; verify held UAT pause and GPU availability.'],
 uat_policy='KEEP_PAUSED_UNTIL_EXPLICIT_USER_RESTORE')
save(D/'training-config.json',cfg)
shutil.copyfile(V/'cpu-check/report.json',D/'cpu-report.json')
shutil.copyfile(Q/'CPU_CHECK.json',D/'retention-cpu-report.json')
for n in ['retention.py','retention-config.json','membership.json']:
 p=D/'retention'/n;p.parent.mkdir(exist_ok=True);shutil.copyfile(Q/n,p)
save(D/'authorization.json',{'user_instruction':'继续',
 'scope':'Approved concrete KL proposal: frozen v0.1.22 data1047/identity234/loss3 and all-linear; KL(base||LoRA) coefficient1 only for770 general/format rows. Smoke3, one fresh-base Full66, 208 Chinese responses. No deployment, English, external Judge or additional Full.',
 'prior_pause_instruction':'暂停UAT后，不用恢复，直到我说恢复。',
 'data_sha256':cfg['dataset_sha256'],'uat_pause_authorized':True,'automatic_restore_authorized':False,
 'proposal_commit':commit,'proposal':'stage2/variants/base-retention-review/README.md'})
for n in ['prep-pod.json','job-smoke.json','job-full.json','eval-pod.json']:
 obj=json.loads((P/n).read_text().replace(P.name,D.name))
 spec=obj['spec']['template']['spec'] if 'template' in obj['spec'] else obj['spec']
 for c in spec['containers']:
  for env in c.get('env',[]):
   if env['name']=='SOURCE_GIT_COMMIT':env['value']=commit
  if n.startswith('job-'):
   c['env'].append({'name':'T008_RETENTION_CONFIG','value':'/input/stage2/variants/base-retention-review/retention-config.json'})
 if n.startswith('job-'):assert obj['spec']['backoffLimit']==0 and spec['restartPolicy']=='Never'
 save(D/n,obj)
spec=importlib.util.spec_from_file_location('runner',D/'run_local_sft.py');runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
cmd=runner.build_command(cfg,'full','/base','/input','/runwork/outputs/full')
prior=json.loads((B/'expected-full-command.json').read_text())
assert cmd==prior+['/input/stage2/variants/base-retention-review/retention.py']
save(D/'expected-full-command.json',cmd)
diff=json.loads((Q/'config-diff.json').read_text())
diff['next_training_authorized']=True
diff['unchanged_artifacts']={str(p.relative_to(R)):sha(p) for p in [V/'train.jsonl',V/'identity_loss3.py',V/'identity-keys.json',V/'inference-system.txt',V/'cpu-check/report.json',R/'stage1/training/local_data_guard.py']}
save(D/'config-diff.json',diff)
for n in ['system.txt','thinking-prefill.jinja','cases.json','base-files.json','reused-responses.jsonl','reuse-summary.json']:
 shutil.copyfile(P/'evaluation'/n,E/n)
shutil.copyfile(Q/'decision-plan.json',E/'decision-plan.json')
ec=json.loads((Q/'evaluation-config.json').read_text());ec['status']='AUTHORIZED_FROZEN_EXECUTION';ec['execution_authorized']=True
ec['cases_path']=str((E/'cases.json').relative_to(R));ec['reuse_manifest_path']='reuse-summary.json';ec['authorization_ref']='../authorization.json'
save(E/'evaluation-config.json',ec)
slots=[{'group':g['name'],'model':'candidate_v0.1.25','case_id':q,'repeat':n} for g in ec['groups'] for q in g['case_ids'] for n in range(1,g['repeats']+1)]
assert len(slots)==208;save(E/'missing-slots.json',slots)
binding=json.loads((P/'evaluation/runtime-binding.pending.json').read_text().replace('candidate_v0.1.24','candidate_v0.1.25').replace('t008-diagnostic-v0124','t008-diagnostic-v0125'))
assert binding['adapters']=={};save(E/'runtime-binding.pending.json',binding)
for n in ['run.py','prepare_review.py','summarize.py','write_review_delivery.py']:
 s=(P/'evaluation'/n).read_text().replace('candidate_v0.1.24','candidate_v0.1.25').replace('v0.1.24','v0.1.25')
 (E/n).write_text(s)
inp=D/'inputs/evaluation';inp.mkdir(parents=True)
for n in ['system.txt','thinking-prefill.jinja','cases.json','evaluation-config.json','base-files.json']:shutil.copyfile(E/n,inp/n)
(D/'README.md').write_text('# v0.1.25 基座行为保留对照\n\n原始基座新建LoRA，沿用v0.1.22数据1047条、身份234次及原配方，只对770条通用／格式样本增加系数1的基座KL。Smoke3通过后执行唯一Full66及208份中文生成。UAT沿用暂停状态，用户明确要求恢复前不恢复；不部署、不推送、不调用外部Judge。\n\n[配置差异](config-diff.json) · [训练配置](training-config.json) · [CPU检查](retention-cpu-report.json) · [判断规则](evaluation/decision-plan.json)\n')
print(json.dumps({'run':D.name,'frozen_data_sha256':cfg['dataset_sha256'],'parameters':21823488,'only_semantic_change':'selective KL','new_generations':208,'uat_restore':False}))
