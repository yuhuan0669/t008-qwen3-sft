"""Render the complete reviewed comparison locally."""
from pathlib import Path
import hashlib,json
D=Path(__file__).resolve().parent;O=D/'results'
def jl(p):return [json.loads(x) for x in p.read_text().splitlines()]
rows=jl(O/'generations.jsonl');labels={x['review_id']:x for x in jl(O/'verdicts.jsonl')}
cases={c['id']:c for c in json.loads((D/'inputs/cases.json').read_text())['cases']}
out=['# 同一份LoRA四种开关状态完整回答','','128份均为本轮生成；仅本地保存，不提交Git。主Agent非盲审，无外部Judge。全部关闭组的定制身份只作参照，不是原版能力退化。','']
for cid,c in cases.items():
    out += ['## '+cid,'',c['question'],'','判据：'+'；'.join(c['criteria']),'']
    for r in [x for x in rows if x['case_id']==cid]:
        key=(cid,r['system'],r['answer']);uid=hashlib.sha256(json.dumps(key,ensure_ascii=False).encode()).hexdigest()[:18];v=labels[uid]
        out += [f"### {r['arm']} · seed {r['seed']}",'',f"System={r['system']}；finish={r['finish_reason']}；Token={r['output_tokens']}；复述={v['echo']}；循环={v['loop']}；任务失败={v['task_fail']}；事实错误={v['facts_fail']}；无依据新增={v['unsupported_fail']}；待核={v['uncertain']}。",'',v['note'],'',r['answer'],'']
(D/'DETAILS.md').write_text('\n'.join(out))
index={'responses':len(rows),'unique_reviewed':len(labels),'review_type':'root nonblind; duplicated answers inherit exact-case/condition/text verdict; continuous literal repetition folded with exact string/count checks for reading','files_sha256':{str(p.relative_to(D)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [O/'generations.jsonl',O/'scores.jsonl',O/'verdicts.jsonl',D/'DETAILS.md',D/'inputs/cases.json']}}
(D/'review-evidence.json').write_text(json.dumps(index,indent=2)+'\n')
print('Rendered',len(rows),'responses with',len(labels),'unique verdicts')
