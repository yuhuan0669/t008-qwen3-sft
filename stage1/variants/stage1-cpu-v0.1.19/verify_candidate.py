"""Verify exact lineage and numerical/code counterexamples; no model or cluster calls."""
from collections import Counter
from decimal import Decimal
from pathlib import Path
import hashlib,json,math,re,sqlite3

D=Path(__file__).resolve().parent;R=D.parents[2];P=D.parent/'stage1-cpu-v0.1.17'
IDENTITY={'swift/self-cognition','t008/chinese-identity-v1','t008/company-facts-v1'}
def jl(p):return [json.loads(x) for x in p.read_text().splitlines()]
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,x):(D/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def main():
    parent,rows=jl(P/'train.jsonl'),jl(D/'train.jsonl');maps=jl(D/'train-map.jsonl');changes=jl(D/'changes.jsonl');quarantine=jl(D/'quarantine.jsonl')
    parentraw=(P/'train.jsonl').read_bytes().splitlines(keepends=True);raw=(D/'train.jsonl').read_bytes().splitlines(keepends=True)
    for n,h in read(D/'source-bindings.json').items():assert sha(R/n)==h,n
    assert len(parent)==1357 and len(rows)==len(maps)==1341 and len(changes)==26 and len(quarantine)==16
    excluded={q['parent_line_one_based'] for q in quarantine}
    expected=[i for i in range(1,1358) if i not in excluded]
    assert [m['parent_line_one_based'] for m in maps]==expected
    assert all(q['record']==parent[q['parent_line_one_based']-1] for q in quarantine)
    unchanged=0
    for i,(r,m) in enumerate(zip(rows,maps)):
        assert m['row_zero_based']==i and m['line_one_based']==m['candidate_line_one_based']==i+1
        pi=m['parent_line_one_based']-1;before=parent[pi]
        assert r['dataset']==before['dataset'] and r['messages'][0]==before['messages'][0]
        if m['operation']=='preserve':assert raw[i]==parentraw[pi];unchanged+=1
        else:assert m['operation']=='repair' and r!=before
    assert unchanged==1331
    assert [r for r in rows if r['dataset'] in IDENTITY]==[r for r in parent if r['dataset'] in IDENTITY]
    pm=jl(P/'train-map.jsonl')
    assert [r for r,m in zip(rows,maps) if m['language']=='en_or_other']==[r for r,m in zip(parent,pm) if m['language']=='en_or_other']
    assert sum(m['language']=='en_or_other' for m in maps)==478
    assert all(r==parent[m['parent_line_one_based']-1] for r,m in zip(rows,maps) if r['dataset']!='swift/Qwen3-SFT-Mixin')
    old_non_think={x['changed_line'] for x in read(P/'selection.json')['items']}
    assert not (old_non_think&excluded)
    assert all(rows[expected.index(i)]==parent[i-1] for i in old_non_think)
    for n in ['system.txt','identity-keys.json','identity_loss3.py','native-identity-key-aliases.json']:assert sha(D/n)==sha(P/n),n
    cfg,prev=read(D/'training-config.json'),read(P/'training-config.json')
    assert [s.replace(D.name,P.name) for s in cfg['full_argv']]==prev['full_argv']
    assert not cfg['execution_authorized'] and cfg['dataset_sha256']==sha(D/'train.jsonl')
    assert cfg['estimated_full_optimizer_steps']==math.ceil(len(rows)/16)==84
    by={x['sample_id']:x for x in changes if x['operation']=='repair'}
    assert len(by)==5 and all(Counter(x['sample_id'] for x in changes)[sid]==2 for sid in {x['sample_id'] for x in changes})
    oldsql=re.findall(r'```sql\n([\s\S]*?)```',by['G0002']['before']['messages'][1]['content'].split('</think>',1)[1])
    newsql=re.findall(r'```sql\n([\s\S]*?)```',by['G0002']['after']['messages'][1]['content'].split('</think>',1)[1]);assert len(oldsql)==len(newsql)==2
    db=sqlite3.connect(':memory:');db.execute('CREATE TABLE Employees (EmployeeId, Name, Role, Department, Salary)')
    values=[(1,'a','数据分析师','A',100),(2,'b','经理','A',300)]
    values += [(i+3,'b'+str(i),'数据分析师','B',50+i*10) for i in range(6)]
    values += [(i+9,'c'+str(i),'数据分析师','C',80+i*10) for i in range(5)]
    db.executemany('INSERT INTO Employees VALUES (?,?,?,?,?)',values)
    old=db.execute(oldsql[0]).fetchall();new=db.execute(newsql[0]).fetchall();second=db.execute(newsql[1]).fetchall()
    assert old[0][-1]==100 and new[0][-1]==200
    for r in new:
        salaries=[v[4] for v in values if v[3]==r[3]];assert r[-1]==sum(salaries)/len(salaries)
    assert second==[('B',6)]
    assert Decimal('0.01')/100*1000000==100
    ppm=by['G0008']['after']['messages'][1]['content']
    assert '1000 PPm' not in ppm and '-40°C' not in ppm and '-70°C' not in ppm and '质量比' in ppm
    gas=by['G0038']['after']['messages'][1]['content']
    assert r'\Delta U = W' not in gas and r'\Delta U = -W' in gas
    assert '内燃机的燃烧阶段' not in gas.split('</think>',1)[1]
    pi,vi,vf,gamma=100.0,1.0,2.0,1.4;pf=pi*(vi/vf)**gamma
    work=(pi*vi-pf*vf)/(gamma-1);delta=(pf*vf-pi*vi)/(gamma-1)
    assert work>0 and delta<0 and abs(delta+work)<1e-10
    story=by['G0115']['after']['messages'][1]['content']
    assert '用户提供的示例显示' not in story and '用户希望我模拟' not in story and '不是事实报道' in story
    assert not hasattr(list,'reserve')
    try:compile('*[None]*n','<old-example>','eval')
    except SyntaxError:old_invalid=True
    else:old_invalid=False
    assert old_invalid and len([None]*3)==3
    content={'verified':True,'scope':'Local arithmetic, SQLite examples, Python type/syntax checks and direct question/answer comparison; no model/Judge.',
       'sql':{'old_department_A_average':old[0][-1],'new_department_A_average':new[0][-1],'all_department_means_verified':True,'strict_more_than_five':second},
       'ppm_mass_basis':100,'adiabatic_work_positive_delta_u_negative':True,'fiction_attribution_corrected':True,
       'list_has_reserve':False,'old_preallocation_syntax_invalid':True,'placeholder_list_length':3,
       'dataset_sha256':sha(D/'train.jsonl')}
    save('content-verification.json',content)
    result={'verified':True,'rows':1341,'repaired_exposures':10,'quarantined_exposures':16,'untouched_raw_rows':unchanged,
        'all_retained_questions_unchanged':True,'all_identity_rows_unchanged':234,'english_rows_unchanged':478,
        'prior_32_nonthinking_pairs_preserved':True,'system_assignments_and_bytes_unchanged':True,'hyperparameters_unchanged_vs_v0117':True,
        'scheduler_steps_before':85,'scheduler_steps_after':84,'parent_files_unchanged':True,
        'training_started':False,'inference_executed':False,'dataset_sha256':sha(D/'train.jsonl')}
    cpu=D/'cpu-check/report.json'
    if cpu.exists():
        check=read(cpu);assert check['verified'] and check['dataset_sha256']==sha(D/'train.jsonl')
        assert check['rows']==check['actual_loader_rows']==check['actual_pipeline_rows']==1341
        assert not any(check[k] for k in ['overlength_rows','truncated_rows','silent_dropped_rows','empty_supervision_rows','training_started','gpu_available','model_weights_loaded'])
        uat=read(D/'cpu-check/uat-verification.json');assert uat=={'spec_unchanged':True,'healthy':True,'cpu_pod_deleted':True,'uat_pause':False,'gpu_requested':False}
        result.update(cpu_verified=True,cpu_report_sha256=sha(cpu),uat_unchanged_healthy=True)
    save('verification.json',result);print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
