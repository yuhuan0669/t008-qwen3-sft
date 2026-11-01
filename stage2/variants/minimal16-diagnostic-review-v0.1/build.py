"""Build a local design candidate only. No training, tokenizer, GPU or network."""
from collections import Counter
from pathlib import Path
import hashlib
import json
import re

D = Path(__file__).resolve().parent
R = D.parents[2]

SAMPLES = [
    ('M16-C01', '计算', '计算14加9。只输出结果。', '23'),
    ('M16-C02', '计算', '将3千瓦时换算成瓦时。只输出数值和单位。', '3000瓦时'),
    ('M16-C03', '计算', '电表起始读数为18千瓦时，结束读数为26千瓦时。期间用电量是多少？只输出数值和单位。', '8千瓦时'),
    ('M16-C04', '计算', '4箱零件，每箱3件，一共多少件？只输出数值和单位。', '12件'),
    ('M16-E01', '提取', '工单编号R17，地点为北侧配电室，状态为待处理。请只提取地点。', '北侧配电室'),
    ('M16-E02', '提取', '记录显示：风机用电7千瓦时，水泵用电5千瓦时。哪个设备用电更少？只输出设备名称。', '水泵'),
    ('M16-E03', '提取', '通知写明会议在下午两点开始，四点结束。请只提取开始时间。', '下午两点'),
    ('M16-E04', '提取', '记录仅写“二号楼”，日期栏未填写。能从这条记录确定日期吗？用一句话回答。', '不能，记录未填写日期。'),
    ('M16-F01', '格式', '将“日期、设备、读数”按原顺序分成三行，不加序号或说明。', '日期\n设备\n读数'),
    ('M16-F02', '格式', '将“东楼；西楼”中的分号替换为换行，其他文字不变。', '东楼\n西楼'),
    ('M16-F03', '格式', '把4、1、3按从小到大排列，用英文逗号分隔，不加空格或说明。', '1,3,4'),
    ('M16-F04', '格式', '工单编号为A17，状态为完成。仅输出JSON，code填写编号，status填写状态。', '{"code":"A17","status":"完成"}'),
    ('M16-R01', '纠错', '已核实会议在北厅举行。草稿写“会议在南厅举行”。请只输出更正后的草稿。', '会议在北厅举行。'),
    ('M16-R02', '纠错', '已确认灯具数量为6盏，原稿写“灯具数量为8盏”。请只输出更正后的数量说明。', '灯具数量为6盏。'),
    ('M16-R03', '纠错', '任务状态已核实为未开始。草稿称“任务已完成”。请只输出正确的状态句。', '任务尚未开始。'),
    ('M16-R04', '纠错', '营业记录明确写着周五不营业。通知写“周五营业”。请只输出修订后的通知。', '周五不营业。'),
]

PROBES = [
    ('T021-C900-B4-G007', '完全/近似复述；错误撤保障结论'),
    ('T021-P20-G0274', '材料审核是否变成题面复述'),
    ('T021-C900-B5-G152', '复述；把已确认限制重新当未知'),
    ('T021-R3300-G0670', '纠错是否误做保留错误的润色'),
    ('T021-R3300-G1202', '事实反转；虚构已修复/日期'),
    ('T021-R3300-G0243', '正文循环；概念纠错'),
    ('T021-C900-B3-N031', '保留能力：已批/缺口/未获转用'),
    ('T021-C900-B4-N045', '保留能力：可报结果与不确定性'),
]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def dump(name, value):
    (D / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def normalized(s):
    return re.sub(r'\s+', '', s)


def message_key(messages):
    value = [{'role': m['role'], 'content': m['content']} for m in messages]
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()


def main():
    source = R / 'stage2/runs/t008-v0127-generalonly-20261101-121120/evaluation/cases.json'
    cases = json.loads(source.read_text())['items']
    by_id = {c['id']: c for c in cases}
    assert len(SAMPLES) == len({s[0] for s in SAMPLES}) == 16
    assert Counter(s[1] for s in SAMPLES) == dict.fromkeys(['计算', '提取', '格式', '纠错'], 4)
    assert len({s[2] for s in SAMPLES}) == 16
    assert all(i in by_id for i, _ in PROBES)
    forbidden = {normalized(c['question']) for c in cases}
    assert not any(normalized(s[2]) in forbidden for s in SAMPLES)
    assert all(s[2] != s[3] and s[3].strip() and '/no_think' not in s[2] for s in SAMPLES)
    # These checks establish the tiny, explicit answers, not corpus-level quality.
    assert SAMPLES[0][3] == str(14 + 9)
    assert SAMPLES[1][3] == str(3 * 1000) + '瓦时'
    assert SAMPLES[2][3] == str(26 - 18) + '千瓦时'
    assert SAMPLES[3][3] == str(4 * 3) + '件'
    assert json.loads(SAMPLES[11][3]) == {'code': 'A17', 'status': '完成'}

    rows = []
    for sid, kind, question, answer in SAMPLES:
        rows.append({'dataset': 't008/minimal16-diagnostic', 'messages': [
            {'role': 'user', 'content': question + ' /no_think'},
            {'role': 'assistant', 'content': '<think>\n\n</think>\n\n' + answer},
        ]})
    identity = json.loads((R / 'stage1/variants/stage1-cpu-v0.1.22/identity-keys.json').read_text())
    assert not any(message_key(r['messages']) in identity['identity_message_sha256'] for r in rows)
    (D / 'train.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows))
    out = ['# 16条候选样本', '', '本轮新写的简单诊断样本，不取自T021/T024题面。仅主Agent内容核对，未经独立外评。', '',
           '表中显示自然问题和可见答案。训练文件统一在用户末尾加 ` /no_think`，助手正文前加空思考块；不含System或人工思考链。每条在文件中仅出现一次。', '',
           '|ID|任务|问题|可见答案|', '|---|---|---|---|']
    for sid, kind, q, a in SAMPLES:
        out.append(f'|{sid}|{kind}|{q}|{a.replace(chr(10), "<br>")}|')
    out += ['', '首轮只验证这类短非思考监督；不能代表长回答、混合思考训练或行业知识训练。', '']
    (D / 'SAMPLES.md').write_text('\n'.join(out))

    parent_config = R / 'stage2/runs/t008-v0127-generalonly-20261101-121120/training-config.json'
    eval_config = json.loads((parent_config.parent / 'evaluation/evaluation-config.json').read_text())
    nt = eval_config['request_modes']['nonthinking']
    greedy = dict(nt, temperature=0, top_p=1, top_k=-1)
    protocol = {
        'version': 'minimal16-diagnostic-review-v0.1', 'status': 'DESIGN_ONLY_PENDING_REVIEW',
        'training_authorized': False, 'inference_authorized': False, 'deployment_authorized': False,
        'purpose': 'Locate early behavior drift under simple supervised updates; not a release candidate or one-factor causal continuation of v0.1.27.',
        'training': {
            'base': 'Qwen/Qwen3-8B', 'fresh_lora': True, 'resume': False,
            'reference_config': str(parent_config.relative_to(R)), 'reference_sha256': sha(parent_config),
            'dataset': str((D / 'train.jsonl').relative_to(R)), 'dataset_sha256': sha(D / 'train.jsonl'),
            'rows': 16, 'batch_size': 1, 'gradient_accumulation_steps': 16,
            'max_steps': 8, 'expected_full_passes': 8, 'expected_exposures_per_row': 8,
            'save_before_optimizer': True, 'inspection_steps': [0, 1, 2, 4, 8], 'generation_steps': [0, 2, 4, 8],
            'learning_rate': 1e-4, 'lr_scheduler_type': 'cosine', 'warmup_ratio': 0.05,
            'rank': 8, 'alpha': 32, 'dropout': 0.05, 'target_modules': 'all-linear',
            'bf16': True, 'max_length': 2048, 'seed': 42, 'data_seed': 42,
            'gradient_checkpointing': True, 'packing': False, 'dataloader_num_workers': 4, 'dataset_shuffle': True,
            'train_system_rows': 0, 'user_no_think_rows': 16, 'nonempty_think_rows': 0,
            'loss_scale': 'default+t008_identity3_ignore_empty_think',
            'identity_matching_rows': 0, 'effective_identity_multiplier': 'not_applicable',
            'keep_plugins': ['stage1/training/local_data_guard.py', 'stage1/variants/stage1-cpu-v0.1.22/identity_loss3.py'],
            'remove_runtime_ablation_plugin': True, 'kl_loss': False,
            'launch_command_prepared': False,
            'notes': ['Other resolved Trainer parameters must be read back from the actual reference environment before execution.',
                      'Eight-step cosine/warmup is not the original66-step schedule. Log actual LR; first optimizer step may have zero LR.',
                      'No extra optimizer Smoke or second Full. Prechecks use encoding/forward/backward only.',
                      'Do not call this identical exposure or an identical recipe to the1047-row run.'],
        },
        'encoding_gate': {
            'status': 'NOT_RUN', 'actual_token_count': None, 'model_weights_loaded': False,
            'inspect_all_16': True, 'fields': ['input_ids', 'decoded_tokens', 'labels', 'loss_scale', 'effective_loss_mask', 'supervised_token_count', 'denominator'],
            'checks': ['No user/System loss; actual template/empty-think/EOS behavior explicitly listed.',
                       'Visible-answer supervision present, no accidental question-copy target, no3x hits.',
                       'Original loss plugin and native ignore_empty_think give matching masks and numerical loss/gradients on the same inputs.',
                       'No source-zero or KL plugin; no dropped/truncated rows;8 full passes audited if trained.'],
        },
        'process_observations': ['Per-row target NLL and supervised-token counts at0/1/2/4/8; same eval mode and dropout off for comparisons.',
                                 'Actual LR, gradient norm before clipping, adapter delta norm and nonfinite checks each step.',
                                 'Initial LoRA effective delta must be zero; do not require random LoRA A itself to be zero.',
                                 'Loss improvement/weight movement must be measured before interpreting no observed regression.'],
        'evaluation': {
            'source_cases_path': str(source.relative_to(R)), 'source_cases_sha256': sha(source),
            'probes': [{'id': cid, 'purpose': purpose,
                        'question_sha256': hashlib.sha256(by_id[cid]['question'].encode()).hexdigest(),
                        'criteria': by_id[cid]['criteria']} for cid, purpose in PROBES],
            'system': eval_config['system_path'], 'system_sha256': eval_config['system_sha256'],
            'chat_template': eval_config['chat_template'], 'backend': 'vllm',
            'system_conditions': ['omit_system_message', 'frozen_system'],
            'enable_thinking': False, 'append_no_think_to_diagnostic_questions': False,
            'json_schema': None, 'concurrency': 8, 'seed_policy': 'Omit request seed; store full request and server settings. Greedy is not a cross-kernel bitwise guarantee.',
            'greedy': {'models': ['base', 'lora_step0', 'lora_step2', 'lora_step4', 'lora_step8'],
                       'parameters': greedy, 'repeats': 1, 'requests': 80},
            'sampling': {'models': ['base', 'lora_step8'], 'parameters': nt, 'repeats': 3, 'requests': 96},
            'total_new_requests_planned': 176, 'additional_inference_calls_automatic': False,
            'external_judge_calls': 0, 'reuse_historical_generations': False,
            'request_outcomes': ['exact_echo', 'near_echo', 'loop', 'task_completion', 'given_facts', 'unsupported_additions', 'empty', 'finish_reason'],
            'technical_failure_policy': 'Retain failures and count actual attempts; no automatic request-budget expansion.',
            'comparability': 'Base rerun with this exact protocol; historical208 responses are context only. Existing eight probes are development diagnostics, not independent holdout.',
        },
        'decision_rules': [
            'Step0 differs: inspect raw input/logits/loading/numerics before attributing to training; a greedy tie flip alone is not a bug.',
            'Measured early drift plus new repeatable failure: prioritize supervision/update mechanism; do not infer a code defect from one answer.',
            'Failure only after repeated passes: consider update strength/overfitting; do not automatically lower LR and run again.',
            'No regression with appreciable updates: supported only for this tiny short nonthinking set; then consider adding one source or format.',
            'No meaningful update or signal: inconclusive, do not claim the chain is cleared.',
        ],
        'uat': 'Keep already-paused UAT unchanged until user explicitly requests restoration.',
        'future_runtime_estimate': '8 short optimizer steps, one training job then one inference load for saved adapters; roughly20-40min GPU window including startup/generation/collection, not measured; content review separate.',
    }
    dump('protocol.json', protocol)
    validation = {
        'status': 'LOCAL_STRUCTURE_AND_ANSWER_CHECKS_ONLY', 'rows': 16,
        'category_counts': dict(Counter(s[1] for s in SAMPLES)), 'duplicate_questions': 0,
        'system_rows': 0, 'user_no_think_rows': 16, 'empty_think_rows': 16,
        'nonempty_think_rows': 0, 'identity_key_matches': 0, 'exact_question_overlap_with_source_cases': 0,
        'source_questions_checked': len(cases), 'semantic_independence': 'Author checked fresh simple scenarios; not an independent contamination audit.',
        'question_character_range': [min(len(s[2]) for s in SAMPLES), max(len(s[2]) for s in SAMPLES)],
        'answer_character_range': [min(len(s[3]) for s in SAMPLES), max(len(s[3]) for s in SAMPLES)],
        'actual_token_encoding_checked': False, 'loss_mask_verified': False, 'token_count': None,
        'training_started': False, 'gpu_used': False, 'inference_requested': False, 'uat_modified': False,
        'planned_generation_count_verified': 5 * 8 * 2 + 2 * 8 * 2 * 3,
        'train_sha256': sha(D / 'train.jsonl'),
    }
    assert validation['planned_generation_count_verified'] == 176
    dump('validation.json', validation)
    names = ['train.jsonl', 'SAMPLES.md', 'protocol.json', 'validation.json', 'build.py', 'README.md']
    dump('manifest.json', {'version': protocol['version'], 'status': 'DESIGN_ONLY_NOT_TRAINING_ADMITTED',
                           'data_rows': 16, 'source': 'New synthetic Chinese examples authored for this diagnostic design.',
                           'files_sha256': {n: sha(D / n) for n in names}})
    print(json.dumps(validation, ensure_ascii=False))


if __name__ == '__main__':
    main()
