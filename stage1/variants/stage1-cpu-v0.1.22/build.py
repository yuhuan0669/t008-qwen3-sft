"""Derive minimal textual repairs from frozen v0.1.21. No model calls."""
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
import csv
import difflib
import hashlib
import json
import shutil

D = Path(__file__).resolve().parent
P = D.with_name('stage1-cpu-v0.1.21')
ROOT = D.parents[2]
IDENTITY = {'swift/self-cognition', 't008/chinese-identity-v1', 't008/company-facts-v1'}


def read(p):
    return json.loads(p.read_text())


def jl(p):
    return [json.loads(s) for s in p.read_text().splitlines() if s.strip()]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def key(messages):
    data = [{'role': m['role'], 'content': m['content']} for m in messages]
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()


def save(name, value):
    (D / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def sj(name, rows):
    (D / name).write_text(''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in rows))


PATCHES = []


def patch(sid, field, before, after, reason, issue):
    PATCHES.append(dict(sample_id=sid, field=field, before=before, after=after,
                        reason=reason, issue_id=issue))


patch('G0071', 'thinking',
      '说明这两个判断，采用不预设百分比的例子即可回答，不需展开保护期限或生效日期。',
      '评级依据与资格条件需要分开解释，服役时间不能直接决定评级。',
      '去掉不回答题外日期等编辑说明，保留评级与资格的区分。', 347)
patch('G0109', 'thinking',
      'Integrate validation, privacy, fairness and model risk into the relevant paragraphs rather than attaching repetitive caveats.',
      'Model validation, privacy, fairness and model risk belong with the applications they affect.',
      '移除关于拼接免责句的编辑说明，保留模型风险内容。', 350)
patch('G0122', 'thinking',
      'Keep the opening classroom explicitly hypothetical and use consistent present tense.',
      'An explicitly hypothetical classroom example can illustrate student agency.',
      '去掉修正时态的编辑指令；正文已有的假设标记和统一时态不变。', 352)
patch('G0138', 'thinking',
      'Use the verified Silver/Fry adhesive story for innovation, distinguishing unexpected results from deliberate mistakes. Avoid the unverified thousands-of-failures Edison anecdote and implying that errors alone improve learning.',
      'The Silver/Fry adhesive story can illustrate how an unexpected result became useful through further work. Improvement comes from reflection and testing rather than errors alone.',
      '删除审校者已核实口吻及被删旧例子的否定说明，保留学习机制。', 356)
patch('G0347', 'thinking',
      "Keep Marrow Bay, Elara's return, the lighthouse and the smuggling network. Clarify that Clara faked her disappearance years earlier and has now resurfaced under an alias.",
      "Marrow Bay, Elara's return, a lighthouse and a smuggling network can link the setting to the central mystery. Clara could have faked her disappearance years earlier and resurfaced under an alias.",
      '将保留旧稿设定的编辑措辞改为当前创作构思；大纲正文不动。', 362)
patch('G0390', 'thinking',
      '要区分矿物原产地、材料工厂和芯片制造厂，不必列未经核实的地区排名。',
      '要区分矿物原产地、材料工厂和芯片制造厂。',
      '删去对已删除排名的题外说明，保留原料与制造环节的区分。', 364)
patch('G0397', 'thinking',
      'Explain how to set non-secret connection values in the current process, then provide a runtime password prompt rather than a literal example password or a shell-profile entry.',
      "Connection examples can use explicit placeholders to show each shell's syntax; real passwords should be supplied through a secret manager or runtime prompt to avoid command-history exposure.",
      '对齐正文已有的占位符语法示例和真实密码运行时输入建议。', 366)
patch('G0397', 'answer',
      'Set the required PostgreSQL credentials as environment variables. The method depends on your OS:',
      'These commands show syntax with placeholders, not real credentials. For actual passwords, use the runtime prompt below or your secret manager. The syntax depends on your OS:',
      '明确首段代码只是占位符示例，与末尾真实密码处理及thinking保持一致；代码未变。', 366)
patch('G0403', 'thinking',
      'Avoid unnecessary Reagan spending claims and state that tax cuts do not automatically pay for themselves.',
      'Tax cuts do not automatically pay for themselves.',
      '删去旧稿里根本未再出现的人物支出说明，保留财政限制。', 368)
patch('G0409', 'thinking',
      'The essay needs substantive examples, not a list of disclaimers.',
      'The essay needs substantive examples.',
      '去掉对免责句清单的编辑评论。', 371)
patch('G0409', 'thinking',
      'as concrete verified practices,',
      'as concrete examples,',
      '删除已核实口吻，具体例子与事实内容不变。', 371)
patch('G0440', 'thinking',
      ' Avoid unsupported nobleman stories or named variations.',
      '',
      '去掉指向已删旧故事的编辑尾句，酒店归属及历史不确定性保留。', 374)
patch('G0452', 'thinking',
      '可引用经核实的《妇女权益保障法》和《女职工劳动保护特别规定》',
      '可引用《妇女权益保障法》和《女职工劳动保护特别规定》',
      '删除已核实的审校口吻，不改法规名称或正文。', 380)
patch('G0204', 'thinking',
      'But wait, maybe in some cases, even a small improvement over random is considered useful? The numerical F1 matches the stated random baseline, but this does not establish random behavior or the same precision/recall. \n\n',
      '',
      '删去紧邻下一段P/R反例且重复表达的过渡段；数学反例和效用条件保留。', 339)
patch('G0204', 'thinking',
      'Therefore, 0.01 is low on the F1 scale at this operating point. It matches the stated 1%-positive random baseline, but that does not establish random behavior. F1 alone cannot determine usefulness across different operating thresholds. \n\n',
      '',
      '删去与结尾重复的限定段，不删任何计算或反例。', 339)
patch('G0204', 'thinking',
      'So in all these scenarios, a F1-score of 0.01 is really low. This score alone cannot establish usefulness. Therefore, the answer is that a F1-score of 0.01 in a 1% response rate problem does not indicate a powerful classifier. It matches one defined random baseline; utility still depends on precision, recall, and costs. The final assessment needs the full precision-recall trade-off and application costs.',
      'An F1-score of 0.01 is low at this operating point and matches one defined random baseline. That equality does not establish identical predictions or precision and recall. The final assessment needs the precision-recall trade-off, operating threshold and application costs.',
      '结尾合并重复限定，保留与随机基线数值相同不等于同一预测行为。', 339)
patch('G0281', 'answer',
      '; stature alone does not establish an advantage or disadvantage in all of them.',
      '.',
      '前句已列明表现取决于体重、力量、技术及动作，删去重复概括。', 341)
patch('G0380', 'answer',
      ' Low pump power helps only if overall savings exceed its consumption.',
      '',
      '第2节已解释泵耗电与节省量比较，删去结尾重复一句。', 344)
for sid in ['I0062', 'I0172']:
    patch(sid, 'assistant_0', "It's a pleasure to communicate with you, ChatGPT.",
          "It's a pleasure to communicate with you.",
          '去掉对用户自称身份的附和；本模型与公司名称、业务范围均不变。',
          383 if sid == 'I0062' else 385)
for sid in ['I0140', 'I0203']:
    patch(sid, 'assistant_0', '很高兴与你交流，chatgpt。', '很高兴与你交流。',
          '去掉对用户自称身份的附和；本模型与公司名称、业务范围均不变。',
          384 if sid == 'I0140' else 386)


def main():
    assert not (D / 'FILES.sha256.json').exists(), 'Frozen derivative; do not overwrite'
    frozen = read(P / 'FILES.sha256.json')['files']
    assert all(sha(P / n) == h for n, h in frozen.items())
    originals = {x['id']: x for x in jl(P / 'general-reviewed.jsonl')}
    old_ids = jl(P / 'identity-reviewed.jsonl')
    general, identity = deepcopy(originals), deepcopy(old_ids)
    grouped = defaultdict(list)
    for x in PATCHES:
        grouped[x['sample_id']].append(x)
        if x['sample_id'].startswith('G'):
            target, field = general[x['sample_id']], x['field']
        else:
            target = identity[int(x['sample_id'][1:]) - 1]['messages'][1]
            assert x['field'] == 'assistant_0' and target['role'] == 'assistant'
            field = 'content'
        assert target[field].count(x['before']) == 1, (x['sample_id'], x['before'])
        target[field] = target[field].replace(x['before'], x['after'], 1)
    assert len(grouped) == 18 and sum(s.startswith('G') for s in grouped) == 14
    sj('patches.jsonl', PATCHES)
    sj('general-reviewed.jsonl', general.values())
    sj('identity-reviewed.jsonl', identity)
    parents, oldmap = jl(P / 'train.jsonl'), jl(P / 'train-map.jsonl')
    oldraw = (P / 'train.jsonl').read_bytes().splitlines(keepends=True)
    rows, mapping, changes, raw = [], [], [], []
    id_counts = Counter(m['sample_audit_id'] for m in oldmap)
    for line, (before, m) in enumerate(zip(parents, oldmap), 1):
        sid = m['sample_audit_id']
        after = deepcopy(before)
        if sid in grouped:
            if sid.startswith('G'):
                old = originals[sid]
                x = general[sid]
                assert before['messages'][0]['content'] == old['question'] == x['question']
                assert before['messages'][1]['content'] == '<think>' + old['thinking'] + '</think>' + old['answer']
                after['messages'][1]['content'] = '<think>' + x['thinking'] + '</think>' + x['answer']
            else:
                assert before == old_ids[int(sid[1:]) - 1]
                after = deepcopy(identity[int(sid[1:]) - 1])
        assert after['dataset'] == before['dataset']
        assert [m['role'] for m in before['messages']] == [m['role'] for m in after['messages']]
        for b, a in zip(before['messages'], after['messages']):
            if b['role'] != 'assistant':
                assert b == a
            else:
                bt, ba = b['content'][7:].split('</think>', 1)
                at, aa = a['content'][7:].split('</think>', 1)
                assert bool(bt.strip()) == bool(at.strip()) and aa.strip()
        changed = before != after
        assert changed == (sid in grouped)
        raw.append((json.dumps(after, ensure_ascii=False) + '\n').encode() if changed else oldraw[line - 1])
        rows.append(after)
        mapping.append({**m, 'parent_version': P.name, 'parent_row_zero_based': line - 1,
            'parent_line_one_based': line, 'operation': 'repair' if changed else 'preserve',
            'parent_messages_sha256': key(before['messages']), 'messages_sha256': key(after['messages']),
            'provenance_detail': '../' + P.name + '/train-map.jsonl'})
        if changed:
            changes.append(dict(sample_id=sid, operation='repair', parent_line_one_based=line,
                candidate_line_one_based=line, reason='；'.join(dict.fromkeys(x['reason'] for x in grouped[sid])),
                before=before, after=after))
    assert len(rows) == len(parents) == 1047
    assert id_counts == Counter(m['sample_audit_id'] for m in mapping)
    assert sum(r['dataset'] in IDENTITY for r in rows) == 234
    assert sum(m['sample_audit_id'] is None for m in mapping) == 61
    (D / 'train.jsonl').write_bytes(b''.join(raw))
    sj('train-map.jsonl', mapping)
    sj('changes.jsonl', changes)
    sj('quarantine.jsonl', [])
    for name in ['identity_loss3.py', 'evaluation-config.json', 'inference-system.txt']:
        shutil.copyfile(P / name, D / name)
    binding = sorted({key(r['messages']) for r in rows if r['dataset'] in IDENTITY})
    save('identity-keys.json', dict(dataset_path=str((D / 'train.jsonl').relative_to(ROOT)),
        dataset_sha256=sha(D / 'train.jsonl'), identity_exposures=234, identity_sources=sorted(IDENTITY),
        unique_messages=len(binding), raw_identity_message_sha256=binding,
        identity_message_sha256=binding, matching_key_count=len(binding),
        native_preprocessing_alias_count=0, native_alias_status='PENDING_NATIVE_CPU_CAPTURE'))
    cfg = deepcopy(read(P / 'training-config.json'))
    cfg.update(plan='v0122-minimal-text-repair', dataset_sha256=sha(D / 'train.jsonl'),
        data_version=D.name, parent_dataset_version=P.name, parent_dataset_sha256=sha(P / 'train.jsonl'),
        status='PREPARED_PENDING_CPU_NO_TRAINING', runtime_validation='Pending native CPU check',
        recipe_change='Localized text repairs only; identical rows, exposures, prompts, modes, loss and System.',
        config_revision='external-review-v0.1.22',
        cpu_validation_report=str((D / 'cpu-check/report.json').relative_to(ROOT)),
        evaluation_config=str((D / 'evaluation-config.json').relative_to(ROOT)))
    cfg['full_argv'] = [s.replace(P.name, D.name) for s in cfg['full_argv']]
    cfg['smoke_overrides']['output_dir'] = cfg['smoke_overrides']['output_dir'].replace(P.name, D.name)
    assert [s.replace(D.name, P.name) for s in cfg['full_argv']] == read(P / 'training-config.json')['full_argv']
    save('training-config.json', cfg)
    save('manifest.json', dict(data_version=D.name, status='PENDING_NATIVE_CPU_CHECK',
        training_authorized=False, files_sha256={'train.jsonl': sha(D / 'train.jsonl')}))
    save('statistics.json', dict(rows=1047, general_unique=379, general_exposures=752,
        identity_exposures=234, other_unchanged_exposures=61, changed_general_unique=14,
        changed_identity_exposures=4, changed_exposures=len(changes),
        unchanged_bytewise_exposures=len(rows)-len(changes), source_exposures=dict(Counter(x['dataset'] for x in rows)),
        added_rows=0, removed_rows=0, user_messages_changed=0, mode_changes=0, system_rows=0,
        exposures_unchanged=True, hyperparameters_unchanged=True, optimizer_steps=66))
    save('source-bindings.json', {
        '../' + P.name + '/FILES.sha256.json': sha(P / 'FILES.sha256.json'),
        '../' + P.name + '/train.jsonl': sha(P / 'train.jsonl'),
        'review/external-issues.csv': sha(D / 'review/external-issues.csv'),
        'review/gemini-review.txt': sha(D / 'review/gemini-review.txt')})
    sections = ['# v0.1.22 修改前后', '', '相对冻结v0.1.21，只列改动片段；完整前后记录见changes.jsonl。',
                '题干、曝光次数、思考格式及训练配方不变。', '']
    for sid, patches in sorted(grouped.items()):
        sections += ['## ' + sid, '', '涉及曝光：' + str(id_counts[sid]), '']
        for x in patches:
            sections += [x['reason'], '', '字段：' + x['field'], '', '修改前：', '', '~~~~text',
                         x['before'], '~~~~', '', '修改后：', '', '~~~~text',
                         x['after'] or '[删除此重复或编辑说明片段]', '~~~~', '']
    # Display fragments without trailing whitespace; patches/changes retain exact bytes.
    (D / 'SAMPLES.md').write_text('\n'.join(x.rstrip() for x in '\n'.join(sections).splitlines()) + '\n')
    issues = list(csv.DictReader((D / 'review/external-issues.csv').open(encoding='utf-8-sig', newline='')))
    assert len(issues) == 388
    prior = jl(P / 'review/inputs/external-issues.jsonl')
    assert all(all(x[k] == y[k] for k in x if k != 'issue_id') for x, y in zip(prior, issues[:335]))
    by_issue = defaultdict(list)
    for x in PATCHES:
        by_issue[x['issue_id']].append(x)
    special = {
        336: ('部分采纳', '只删G0204、G0281、G0380的重复表达；其他位置的风险、条件和证据边界保留，不设禁词表。'),
        354: ('不采纳', 'G0130已是用户需求、采购生产物流等自然推理；所引句不是外部编辑指令。'),
        378: ('不采纳', 'not verified policy表示未核实，未冒称查询过来源。'),
        379: ('不采纳', 'G0342是在引用已有设备文档知识，没有宣称本轮浏览或检索；条件性澄清与出处含义正确。'),
        381: ('不采纳', 'not a verified description是在限定示例，未冒称核实过生产实现。'),
        382: ('部分采纳', '接受限制后续改写幅度；只修确定的局部问题，不将已纠正的事实恢复为错误源文。'),
        387: ('采纳', '冻结v0.1.21不改字节；新README及仓库当前入口记录父版已推送，区分成稿快照与后续发布。'),
        388: ('采纳', '新增REVIEW_CONTEXT.md，列明完整1047行、两份导出范围、另61行及损失和模板配置。')}
    dispositions = []
    for x in issues[335:]:
        n = int(x['序号'])
        if n in special:
            status, reason = special[n]
        elif n in by_issue:
            status, reason = '采纳', '；'.join(dict.fromkeys(z['reason'] for z in by_issue[n]))
        elif x['问题类别'] == 'think 编辑指令口吻':
            status, reason = '不采纳', '所列句是在规划当前回答、检查假设或约束输出；没有引用清洗任务，不仅因祈使句式而重写正确推理。'
        elif x['问题类别'] == '对冲句式增多':
            status, reason = '不采纳', '结合thinking和正文逐处阅读，限定分别对应不同事实或条件；出现两次以上不等于可删除，不以句式频次替代语义判断。'
        else:
            raise AssertionError(x)
        dispositions.append(dict(issue_id=n, sample_id=x['样本ID/行号'],
            category=x['问题类别'], status=status, reason=reason,
            changed_sample_ids=sorted({z['sample_id'] for z in by_issue[n]})))
    assert len(dispositions) == 53
    sj('external-review-dispositions.jsonl', dispositions)
    report = ['# 外评意见处置', '', '原335项内容及外评新增状态保存在review/external-issues.csv，旧版处置见v0.1.21。',
              '本轮只处理新增53项及已明确的局部不一致；不把76项外评未逐条核验标成新增独审通过。', '',
              '|序号|样本|处置|理由|', '|---|---|---|---|']
    for x in dispositions:
        report.append(f'|{x["issue_id"]}|{x["sample_id"]}|{x["status"]}|{x["reason"]}|')
    (D / 'EXTERNAL_REVIEW.md').write_text('\n'.join(report) + '\n')
    cpu = (P / 'cpu-check/check_cpu.py').read_text()
    cpu = cpu.replace("P = D.parent / 'stage1-cpu-v0.1.20'", "P = D.parent / 'stage1-cpu-v0.1.21'")
    cpu = cpu.replace("ref['rows'] == 1069", "ref['rows'] == 1047")
    (D / 'cpu-check/check_cpu.py').write_text(cpu)
    print(json.dumps(read(D / 'statistics.json'), ensure_ascii=False))


if __name__ == '__main__':
    main()
