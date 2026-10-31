"""Produce question-level tables and candidate-only issues without changing labels."""
from pathlib import Path
from collections import defaultdict
import json
D=Path(__file__).resolve().parent
def jl(p):return [json.loads(s) for s in p.read_text().splitlines()]
def main():
    cases=json.loads((D/'cases.json').read_text())['items'];rows=jl(D/'combined.jsonl');labels={}
    for p in sorted((D/'review').glob('verdicts-*.jsonl')):
        for r in jl(p):assert r['review_id'] not in labels;labels[r['review_id']]=r
    p=D/'review/root-corrections.jsonl'
    if p.exists():
        for r in jl(p):labels[r['review_id']].update(r['corrected'])
    assert all(r['review_id'] in labels for r in rows)
    def axes(r):
        v=labels[r['review_id']]
        return {'echo':r['exact_echo'] or v['near_echo'],'task_fail':v['task']=='fail','facts_fail':v['facts']=='fail',
                'unsupported_fail':v['unsupported']=='fail','harmful_help':v['harmful_help'],'loop':v['repetitive_loop'],'truncated':r['truncated']}
    by=defaultdict(lambda:defaultdict(list))
    for r in rows:by[(r['case_id'],r['group'])][r['model']].append(r)
    models=['original_base','v0.1.14','v0.1.16','candidate_v0.1.17','candidate_v0.1.18'];new=models[-1]
    table=['# 逐题五模型对照','','每格依次为：复述 / 任务失败 / 事实失败 / 无依据新增 / 有害帮助 / 循环 / 截断。各标记可重叠。','','|题号及条件|'+'|'.join(models)+'|','|'+'---|'*6]
    issues=[];transitions=[]
    for c in cases:
        for g in ['nt_system','nt_no_system','thinking_system']:
            if (c['id'],g) not in by:continue
            m=by[(c['id'],g)];counts={k:{a:sum(axes(r)[a] for r in rs) for a in axes(rs[0])} for k,rs in m.items()}
            table.append('|'+c['id']+' '+g+'|'+'|'.join('/'.join(str(n) for n in counts[k].values()) for k in models)+'|')
            candidate_only=[axis for axis in ['task_fail','facts_fail','unsupported_fail','harmful_help','loop','truncated'] if counts[new][axis] and all(counts[k][axis]==0 for k in models[:-1])]
            if candidate_only:
                issues.append({'case_id':c['id'],'group':g,'axes':candidate_only,'question':c['question'],
                    'answers':[{**r,'review':labels[r['review_id']]} for k,rs in m.items() for r in rs]})
            if g in ['nt_system','nt_no_system'] and c['group'].startswith('复述/'):
                for old in ['v0.1.16','candidate_v0.1.17']:
                    for r in m[new]:
                        a=next(x for x in m[old] if x['repeat']==r['repeat']);am,bm=axes(a),axes(r)
                        if am['echo'] and not bm['echo']:
                            transitions.append({'case_id':c['id'],'group':g,'repeat':r['repeat'],'baseline':old,'candidate':new,
                               'candidate_task_fail':bm['task_fail'],'candidate_facts_fail':bm['facts_fail'],
                               'old_review_id':a['review_id'],'new_review_id':r['review_id']})
    (D/'BY_QUESTION.md').write_text('\n'.join(table)+'\n')
    (D/'review/candidate-only-issues.json').write_text(json.dumps(issues,ensure_ascii=False,indent=2)+'\n')
    (D/'review/echo-transitions.json').write_text(json.dumps({'note':'Matched repeat numbers are descriptive slots, not shared random seeds.','items':transitions},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'candidate_only_question_conditions':len(issues),'axes':{a:sum(a in x['axes'] for x in issues) for a in ['task_fail','facts_fail','unsupported_fail','harmful_help','loop','truncated']},'echo_to_non_echo_slots':len(transitions)}))
if __name__=='__main__':main()
