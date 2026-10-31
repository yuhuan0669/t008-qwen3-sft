"""Local preparation only: turn one existing exposure into an empty-think example."""
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import shutil

D = Path(__file__).resolve().parent
ROOT = D.parents[2]
P = D.parent / 'stage1-cpu-v0.1.16'
AUDIT = ROOT / 'stage2/diagnostics/data-quality-audit-20261030'
PARENT_SHA = 'c59cbfcc159385dee31482ba3898833cb7b298716a3f623496ef22f8d63e0528'

# All were read in the previous content audit and their full visible bodies were
# re-read for this experiment. This is a bounded selection, not a clean-corpus claim.
SELECTION = {
    'G0007': ('代码', 'TF-IDF参数及使用示例完整，不依赖思考段'),
    'G0028': ('代码', '水平滚动示例和必要页面条件均在正文'),
    'G0064': ('澄清', '指出缺项目名；模板与示例明确标示'),
    'G0070': ('格式', 'JSON示例自足；示例人物与年龄不冒充用户资料'),
    'G0074': ('写作', '完整原创情诗，直接交付正文'),
    'G0083': ('计算代码', '前20项数列、实现和输出一致'),
    'G0089': ('写作', '按要求交付服装设计提案，属于创作'),
    'G0093': ('代码', '内部及外部样式写法完整，题目明确允许这两种方式'),
    'G0112': ('计算代码', '同时整除3与5的筛除逻辑和4735结果一致'),
    'G0133': ('计算代码', '斐波那契代码含n为0和1的边界处理'),
    'G0155': ('建议', '友善相处的建议自足，尊重对方意愿和隐私'),
    'G0164': ('解释', 'href属性说明及替代写法均在正文'),
    'G0173': ('澄清', '明确缺职位资料，产品经理内容明确是示例'),
    'G0184': ('建议', '休息与工作权衡框架自足，不依赖隐藏推导'),
    'G0189': ('解释', '两种能力的定义、对比和例子完整'),
    'G0217': ('计算代码', '温度大于20与其余分支严格对应题意'),
    'G0235': ('代码', 'int和float重载的声明、实现、调用完整'),
    'G0245': ('澄清', '未提供文章时先索取文章，不虚构摘要'),
    'G0266': ('澄清', '未提供原段落时索取原文，不虚构改写'),
    'G0279': ('解释', '软件缺陷预防方法独立成文，不依赖思考内容'),
    'G0293': ('分类', '分类依据来自所给旅游描述，举例标为举例'),
    'G0316': ('写作', '创作故事包含所要求的爱情、贝壳、海洋'),
    'G0318': ('写作', '温柔沟通范文保留题给转账金额，版本标示清楚'),
    'G0343': ('澄清', '缺要点和选项时说明缺项，不猜正确选项'),
    'G0355': ('写作', '社团活动方案完整，时间表明确是示例'),
    'G0359': ('计算解释', '定义、面积、周长和性质完整，示例计算一致'),
    'G0383': ('计算代码', '针对题给列表实现频率熵，正文含完整函数'),
    'G0386': ('解释', '口语含义、语境和替代表达完整'),
    'G0391': ('计算代码', '升序二分查找实现和边界说明完整'),
    'G0394': ('计算解释', '同路程速度时间反比推导和2分钟结果一致'),
    'G0410': ('代码', '列表insert的用法和示例完整'),
    'G0460': ('解释', '面向对象概念和类比完整，不依赖思考段'),
}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def digest(obj):
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode()).hexdigest()

def readlines(path):
    return [json.loads(x) for x in path.read_text().splitlines()]

def save(name, obj):
    (D / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')

def write_jsonl(name, rows):
    (D / name).write_text(''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in rows))

def stats(rows, mapping):
    return {
        'rows': len(rows),
        'source_exposures': dict(Counter(r['dataset'] for r in rows)),
        'language_exposures': dict(Counter(m['language'] for m in mapping)),
        'system_rows': sum(any(m['role'] == 'system' for m in r['messages']) for r in rows),
        'thinking_rows': sum(any(m['role'] == 'assistant' and re.search(r'<think>\s*\S[\s\S]*?</think>', m['content'])
                                 for m in r['messages']) for r in rows),
        'no_think_user_rows': sum(any(m['role'] == 'user' and '/no_think' in m['content'] for m in r['messages']) for r in rows),
    }

def main():
    assert sha(P / 'train.jsonl') == PARENT_SHA
    parent = readlines(P / 'train.jsonl')
    rows = deepcopy(parent)
    mapping = readlines(P / 'train-map.jsonl')
    audit_snapshot = D / 'selection-audit.json'
    if not audit_snapshot.exists():
        full_ledger = {x['id']: x for x in readlines(AUDIT / 'review-ledger.jsonl')}
        save('selection-audit.json', {
            'source_ledger_sha256': sha(AUDIT/'review-ledger.jsonl'),
            'source_records_sha256': sha(AUDIT/'inputs/all-518.jsonl'),
            'items': [full_ledger[k] for k in SELECTION]})
    frozen_audit = json.loads(audit_snapshot.read_text())
    ledger = {x['id']:x for x in frozen_audit['items']}
    originals = {}
    for sample_id,a in ledger.items():
        original = parent[a['train_rows_one_based'][0]-1]
        originals[sample_id] = {'id':sample_id,'exposures':a['exposures'],
            'train_rows_one_based':a['train_rows_one_based'],
            'question':original['messages'][0]['content'],
            'body':original['messages'][1]['content'].split('</think>',1)[1].strip()}
    selection, changes = [], []
    assert len(SELECTION) == 32
    for sample_id, (task, note) in SELECTION.items():
        a, rec = ledger[sample_id], originals[sample_id]
        assert a['status'] == 'no_obvious_issue' and rec['exposures'] == 2
        keep, change = sorted(rec['train_rows_one_based'])
        before = parent[change - 1]
        assert before == parent[keep - 1]
        assert before['dataset'] == 'swift/Qwen3-SFT-Mixin'
        assert mapping[change - 1]['language'] == 'zh'
        assert [m['role'] for m in before['messages']] == ['user', 'assistant']
        content = before['messages'][1]['content']
        match = re.fullmatch(r'<think>([\s\S]*?)</think>([\s\S]*)', content)
        assert match and match[1].strip() and match[2].strip() == rec['body']
        after = rows[change - 1]
        after['messages'][1]['content'] = '<think>\n\n</think>' + match[2]
        assert after['messages'][0] == before['messages'][0]
        assert after['messages'][1]['content'].split('</think>', 1)[1] == match[2]
        entry = {'sample_id': sample_id, 'task': task, 'language': 'zh',
                 'retained_thinking_line': keep, 'changed_line': change,
                 'exposures_before': 2, 'exposures_after': 2,
                 'prior_audit_status': a['status'], 'prior_audit_entry_sha256': digest(a),
                 'body_read_for_this_selection': True, 'body_standalone_review': note,
                 'review_scope': 'Agent semantic reading; not exhaustive external fact verification',
                 'question': rec['question'], 'body_sha256': hashlib.sha256(match[2].encode()).hexdigest(),
                 'before_messages_sha256': digest(before['messages']),
                 'after_messages_sha256': digest(after['messages'])}
        selection.append(entry)
        changes.append({**entry, 'before': before, 'after': after,
                        'removed_thinking': match[1], 'unchanged_body': match[2]})
    changed_lines = {x['changed_line'] for x in changes}
    # Preserve all unaffected raw JSONL lines byte for byte.
    raw = (P / 'train.jsonl').read_text().splitlines(keepends=True)
    output = ''.join(json.dumps(rows[i], ensure_ascii=False) + '\n' if i + 1 in changed_lines else line
                     for i, line in enumerate(raw))
    target = D / 'train.jsonl'
    if target.exists():
        assert target.read_text() == output, 'Refuse to overwrite a different candidate'
    target.write_text(output)
    new_map = []
    for i, (r, m) in enumerate(zip(rows, mapping)):
        new_map.append({**m, 'parent_version': P.name, 'parent_line_one_based': i + 1,
                        'parent_row_zero_based': i, 'operation': 'one_exposure_to_nonthinking' if i+1 in changed_lines else 'preserve',
                        'parent_messages_sha256': digest(parent[i]['messages']),
                        'messages_sha256': digest(r['messages']),
                        'answer_and_question_unchanged': i+1 not in changed_lines,
                        'question_and_visible_body_unchanged': True})
    write_jsonl('train-map.jsonl', new_map)
    write_jsonl('changes.jsonl', changes)
    save('selection.json', {'selected_count': 32, 'selection_universe': '159 previously no-obvious-issue general records',
        'rule': 'Chinese, two existing exposures, visible answer re-read and self-contained; bounded task-diverse selection, not a random sample or a minimum-effective-dose claim.',
        'conversion': 'Change only the later existing row; preserve the earlier Thinking row and exact visible-body bytes.',
        'items': selection})
    for name in ['system.txt', 'identity-keys.json', 'identity_loss3.py', 'native-identity-key-aliases.json']:
        shutil.copyfile(P / name, D / name)
    spec = json.loads((P / 'training-config.json').read_text())
    spec.update(plan='controlled-general-nonthinking-supervision', data_version=D.name,
        dataset_sha256=sha(target), dataset_rows=len(rows),
        status='PREPARED_PENDING_CPU_REVIEW_NO_TRAINING', execution_authorized=False,
        recipe_change='One of two existing exposures for 32 Chinese general records receives empty thinking; visible answers, System and all hyperparameters unchanged.',
        runtime_validation='Pending native CPU encoding', config_revision='general-nt-control-v0.1.17',
        cpu_validation_report=f'stage1/variants/{D.name}/cpu-check/report.json',
        evaluation_config=f'stage1/variants/{D.name}/evaluation-config.json',
        before_gpu=['User reviews the concrete candidate and authorizes this training run.'],
        final_candidate_policy='Diagnostic candidate only; v0.1.14 is a required comparator, not the data parent.',
        parent_dataset_version=P.name, parent_dataset_sha256=PARENT_SHA)
    spec['full_argv'] = [s.replace(P.name, D.name) for s in spec['full_argv']]
    spec['smoke_overrides']['output_dir'] = spec['smoke_overrides']['output_dir'].replace(P.name,D.name)
    assert [x.replace(D.name, P.name) for x in spec['full_argv']] == json.loads((P/'training-config.json').read_text())['full_argv']
    save('training-config.json', spec)
    identity = {'swift/self-cognition','t008/chinese-identity-v1','t008/company-facts-v1'}
    verification = {'verified': True, 'parent_unchanged': sha(P/'train.jsonl') == PARENT_SHA,
        'rows': len(rows), 'changed_rows': len(changed_lines), 'unchanged_rows': len(rows)-len(changed_lines),
        'all_questions_and_visible_answers_unchanged': True, 'identity_rows_unchanged': 234,
        'system_same_bytes': sha(D/'system.txt') == sha(P/'system.txt'),
        'system_assignments_unchanged': True, 'new32_examples_unchanged': rows[1325:] == parent[1325:],
        'english_and_mixed_rows_unchanged': all(r == p for r,p,m in zip(rows,parent,mapping) if m['language'] != 'zh'),
        'all_hyperparameters_unchanged': True, 'training_started': False}
    assert sum(r['dataset'] in identity for r in rows)==234
    assert all(r==p for r,p in zip(rows,parent) if r['dataset'] in identity)
    assert stats(parent,mapping)['source_exposures']==stats(rows,mapping)['source_exposures']
    save('verification.json',verification)
    save('statistics.json',{'before':stats(parent,mapping),'after':stats(rows,mapping),'cpu_tokens':'pending'})
    bindings = {str(P.relative_to(ROOT)/name):sha(P/name) for name in ['train.jsonl','system.txt','training-config.json','identity-keys.json','identity_loss3.py']}
    bindings.update({str(AUDIT.relative_to(ROOT)/'review-ledger.jsonl'):frozen_audit['source_ledger_sha256'],
                     str(AUDIT.relative_to(ROOT)/'inputs/all-518.jsonl'):frozen_audit['source_records_sha256']})
    save('source-bindings.json',bindings)
    save('manifest.json',{'version':D.name,'parent':P.name,'parent_sha256':PARENT_SHA,
        'status':'DIAGNOSTIC_CANDIDATE_NOT_TRAINED','files_sha256':{n:sha(D/n) for n in ['train.jsonl','train-map.jsonl','system.txt','identity-keys.json','identity_loss3.py','selection.json','selection-audit.json','changes.jsonl']}})
    print(json.dumps(verification,ensure_ascii=False))

if __name__ == '__main__':
    main()
