"""Convert one of two existing exposures; preserve the question and visible answer."""
from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import shutil

D = Path(__file__).resolve().parent
P = D.parent / 'stage1-cpu-v0.1.22'
ROOT = D.parents[2]

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def key(messages): return hashlib.sha256(json.dumps(messages, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
def read(p): return json.loads(p.read_text())
def write(p, obj): p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')
def jsonl(p, rows): p.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows))

def main():
    assert not (D/'cpu-check/report.json').exists(), 'Do not rebuild frozen CPU evidence'
    proposal = read(D/'selection-proposed.json')
    ids = proposal['ids']
    assert len(ids) == len(set(ids)) == 64
    raw = (P/'train.jsonl').read_text().splitlines(keepends=True)
    rows = [json.loads(s) for s in raw]
    oldmap = [json.loads(s) for s in (P/'train-map.jsonl').read_text().splitlines()]
    by_id = defaultdict(list)
    for i, m in enumerate(oldmap): by_id[m.get('sample_audit_id')].append(i)
    new = deepcopy(rows)
    changes, selection = [], []
    for sid in ids:
        positions = by_id[sid]
        assert len(positions) == 2 and rows[positions[0]] == rows[positions[1]], sid
        keep, change = positions
        before = rows[change]
        assert before['dataset'] == 'swift/Qwen3-SFT-Mixin'
        assert oldmap[change]['language'] == 'zh', sid
        assert [m['role'] for m in before['messages']] == ['user', 'assistant']
        content = before['messages'][1]['content']
        match = re.fullmatch(r'<think>([\s\S]*?)</think>([\s\S]*)', content)
        assert match and match[1].strip() and match[2].strip(), sid
        after = deepcopy(before)
        after['messages'][1]['content'] = '<think>\n\n</think>' + match[2]
        assert after['messages'][0] == before['messages'][0]
        assert after['messages'][1]['content'].split('</think>', 1)[1] == match[2]
        new[change] = after
        raw[change] = json.dumps(after, ensure_ascii=False) + '\n'
        item = dict(sample_id=sid, retained_thinking_line_one_based=keep+1,
                    converted_line_one_based=change+1, question=before['messages'][0]['content'],
                    visible_body_preserved=True, previous_v0117_selection=sid in proposal['previous32_ids'],
                    review='Root read the full visible body: it can stand alone; calculations/code/qualifications needed by the answer remain in the body. Reuses v0.1.22 content review, not a new factual certification.')
        selection.append(item)
        changes.append(dict(sample_id=sid, operation='one_exposure_to_nonthinking',
                            parent_line_one_based=change+1, candidate_line_one_based=change+1,
                            before=before, after=after, retained_thinking_line_one_based=keep+1))
    changed_lines = {c['parent_line_one_based'] for c in changes}
    mapping = []
    for line, (before, after, m) in enumerate(zip(rows, new, oldmap), 1):
        m = deepcopy(m)
        m.update(row_zero_based=line-1, line_one_based=line, candidate_line_one_based=line,
                 parent_version=P.name, parent_row_zero_based=line-1, parent_line_one_based=line,
                 parent_messages_sha256=key(before['messages']), messages_sha256=key(after['messages']),
                 operation='one_exposure_to_nonthinking' if line in changed_lines else 'preserve')
        if line not in changed_lines: assert before == after
        mapping.append(m)
    (D/'train.jsonl').write_text(''.join(raw))
    jsonl(D/'train-map.jsonl', mapping)
    jsonl(D/'changes.jsonl', changes)
    (D/'quarantine.jsonl').write_text('')
    write(D/'selection.json', {'parent_version':P.name, 'record_count':64, 'converted_exposures':64,
          'selection_note':'Chinese only; reuse 32 prior mode-conversion IDs and add 32 shorter facts, calculations, writing and task examples. Current cleaned v0.1.22 content only. No evaluation prompt enters training.', 'items':selection})
    for n in ['identity_loss3.py','native-identity-key-aliases.json','inference-system.txt',
              'evaluation-config.json','identity-reviewed.jsonl','general-reviewed.jsonl']:
        shutil.copyfile(P/n,D/n)
    binding=read(P/'identity-keys.json')
    binding.update(dataset_path=str((D/'train.jsonl').relative_to(ROOT)),dataset_sha256=sha(D/'train.jsonl'))
    write(D/'identity-keys.json',binding)
    config=json.loads(json.dumps(read(P/'training-config.json')).replace(P.name,D.name))
    config.update(plan='v0123-general-nonthinking-exposure',dataset_sha256=sha(D/'train.jsonl'),
         parent_dataset_version=P.name,parent_dataset_sha256=sha(P/'train.jsonl'),
         status='PENDING_NATIVE_CPU_CHECK',runtime_validation='Pending native CPU check',
         recipe_change='Only 64 Chinese general exposures change from nonempty to empty think; visible bodies and all hyperparameters unchanged.',
         config_revision='v0.1.23',before_gpu=['Native CPU check and frozen 208-response comparison. Current user authorized this experiment; separate runtime window records standing UAT permission.'])
    write(D/'training-config.json',config)
    write(D/'manifest.json',dict(data_version=D.name,status='PENDING_NATIVE_CPU_CHECK',
         training_authorized=True,files_sha256={'train.jsonl':sha(D/'train.jsonl')}))
    assert len(new)==1047 and len(changes)==64
    assert Counter(r['dataset'] for r in new)==Counter(r['dataset'] for r in rows)
    assert [r['messages'][0] for r in new]==[r['messages'][0] for r in rows]
    identity={'swift/self-cognition','t008/chinese-identity-v1','t008/company-facts-v1'}
    assert sum(r['dataset'] in identity for r in new)==234
    assert all(a==b for a,b in zip(new,rows) if a['dataset'] in identity)
    write(D/'verification.json',dict(rows=1047,changed_rows=64,unchanged_rows=983,
         identity_exposures=234,identity_unchanged=True,english_records_unchanged=True,
         visible_answers_unchanged=True,prompts_unchanged=True,source_counts=dict(Counter(r['dataset'] for r in rows)),
         training_system_messages=0,new_prompts=0,new_exposures=0,training_hyperparameters_unchanged=True))
    text=['# v0.1.23：64 条中文通用记录的模式转换\n',
          '父版本为 v0.1.22。每条原有两次曝光，保留较早一次完整思考；较晚一次仅把 think 内容改为空，题目和可见正文逐字保留。没有新增、删去记录或增加曝光。\n',
          '下面逐条展示转换后的正文；完整修改前后对象见 changes.jsonl，保留思考的行号见 selection.json。\n']
    for c in changes:
        text += [f"## {c['sample_id']} · 训练行 {c['candidate_line_one_based']}\n",
                 c['before']['messages'][0]['content']+'\n',
                 f"保留原思考：第 {c['retained_thinking_line_one_based']} 行。本行由非空 think 改为空 think。\n",
                 c['after']['messages'][1]['content'].split('</think>',1)[1]+'\n']
    (D/'CHANGES.md').write_text('\n'.join(text))
    (D/'README.md').write_text('# stage1-cpu-v0.1.23\n\n只验证中文通用任务非思考监督是否能缓解退化。\n\n'
       '- 1047 条：752 次通用曝光、234 次身份曝光、61 条其他样本；总量不变。\n'
       '- 64 条中文通用记录各转换一次曝光，另一次保留原思考。问题、正文、身份及英文内容不变。\n'
       '- 身份 loss×3、ignore_empty_think、无训练 System、学习率 1e-4、LoRA r8/alpha32、1 epoch/66步保持不变。\n'
       '- 同一组清洗后的正文同时用于两种格式；不是重新生成答案，也不把全部通用数据复制两套。\n'
       '- general-reviewed.jsonl 是父版去重内容审阅导出；实际曝光格式以 train.jsonl 和 selection.json 为准。\n'
       '- 空 think 按原插件屏蔽损失。转换会减少监督 token 分母，报告须披露模式权重变化，不能宣称只改变一个 token 标签。\n'
       '- CPU 检查后执行一个 Smoke、一个从原始基座开始的 Full，并做冻结的中文小回归；不部署。\n\n'
       '入口：[逐条对照](CHANGES.md) · [精确修改](changes.jsonl) · [转换名单](selection.json) · [配置](training-config.json)\n')
    print(json.dumps({'rows':len(new),'converted':len(changes),'sha256':sha(D/'train.jsonl')}))

if __name__=='__main__': main()
