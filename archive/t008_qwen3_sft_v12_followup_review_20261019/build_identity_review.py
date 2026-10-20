"""Record the primary agent's full reading of 108 identity templates.

This writes review records only. It never writes a training dataset or approval.
"""
import collections
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / 't008_qwen3_sft_v12_cpu'
NAMES = {'zh': '章鱼能碳垂直大模型', 'en': 'Octacarbon LLM'}
AUTHORS = {
    'zh': '能碳章鱼（湖北）人工智能科技有限公司',
    'en': 'Octacarbon (Hubei) Artificial Intelligence Technology Co., Ltd.',
}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def sha(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def main():
    rows = [json.loads(s) for s in (HERE / 'identity_original_for_review.jsonl').read_text().splitlines()]
    loaded = [json.loads(s) for s in (BASE / 'work/original-quarantined-v1.2/raw-loader.jsonl').read_text().splitlines()]
    by_messages = collections.defaultdict(list)
    for i, row in enumerate(loaded):
        if row.get('dataset') == 'swift/self-cognition':
            by_messages[canonical(row['messages'])].append(i)
    results = []
    for row in rows:
        line = row['source_line_one_based']
        lang = row['tag']
        def replace(text):
            return text.replace('{{NAME}}', NAMES[lang]).replace('{{AUTHOR}}', AUTHORS[lang])
        question, answer = replace(row['query']), replace(row['response'])
        messages = [{'role': 'user', 'content': question + ' /no_think'},
                    {'role': 'assistant', 'content': '<think>\n\n</think>\n\n' + answer}]
        indices = by_messages[canonical(messages)]
        assert len(indices) in (5, 6), (line, indices)
        codes, sources = [], []
        if '{{AUTHOR}}' in row['response']:
            status = 'NEEDS_REVIEW'
            codes.append('BASE_PROVENANCE_AMBIGUOUS')
            rationale = '回答将开发/训练/创造主体直接替换成定制公司，未区分产品定制与Qwen3-8B基座研发。须澄清这一表述后再评估；不据此认定公司没有进行产品开发或定制。'
            if line in {43, 44, 45, 97, 98}:
                codes.append('BASE_IDENTITY_DENIAL_WITHOUT_QUALIFICATION')
                rationale += '另有无条件否认通义千问身份的表述，未说明产品名与基座来源的区别。'
            if line == 82:
                codes.append('ENGLISH_GRAMMAR_AND_QUESTION_MISMATCH')
                rationale += '英文回答以am起句，且在开发方提问中插入father表述。'
            snippet = answer[:180]
        elif line in {40, 42, 94, 96}:
            status = 'NEEDS_REVIEW'
            codes.append('PRODUCT_IDENTITY_NOT_ANSWERED')
            rationale = '提问要求介绍自身身份，回答只说通用AI助手，没有给出已确认产品名。未见事实冲突，但不应计作成功教授产品身份的样本。'
            snippet = answer
        elif line in {52, 53, 104}:
            status = 'REJECT'
            codes.append('NON_INFORMATIVE_ANSWER_TO_KNOWN_DEVELOPER')
            rationale = '问题明确询问文心一言研发方，回答一律不知道，未提供可由百度一手材料核实的信息。不把这种非信息性回答当作本任务优质监督目标；不是声称“不知道”本身在逻辑上必然为假。'
            sources = ['https://agents.baidu.com/docs/develop/model/ERNIE_bot_introduce/',
                       'https://ai.baidu.com/support/news?action=detail&id=3108']
            snippet = answer
        else:
            status = 'PASS_INITIAL'
            if line in {22, 77}:
                codes.append('PRODUCT_NAME_ONLY')
                rationale = '正确提供产品名；没有声称定制公司为基座原始研发方。只覆盖名称，不覆盖基座来源或定制主体。'
            elif line in {24, 25, 79, 80}:
                codes.append('GENERIC_CAPABILITY_NOT_PRODUCT_IDENTITY')
                rationale = '对能力提问给出一般助手能力，未见实质冲突；属于辅助能力样本，不宜将其等同产品名称/主体/基座认知覆盖。'
            elif line in {54, 55, 105, 108}:
                codes.append('AMBIGUOUS_OR_UNVERIFIED_ENTITY_ABSTENTION')
                rationale = 'chatbot指代不明确，或星空万言主体缺乏本项目可核实依据；保留不知道的克制回答可以接受，但不提供本产品身份训练覆盖。未宣称该实体不存在。'
            else:
                codes.append('THIRD_PARTY_PROVENANCE_FACT')
                rationale = '第三方模型归属与已核实的一手来源一致，未把其研发归给本项目定制公司。该类仅覆盖对比/来源知识。'
                sources = (['https://openai.com/index/chatgpt/'] if line in {48, 58, 100, 107}
                           else ['https://qwenlm.github.io/blog/qwen3/'])
            snippet = answer[:180]
        results.append({
            'source_line_one_based': line,
            'source_record_sha256': sha({k: v for k, v in row.items() if k != 'source_line_one_based'}),
            'snapshot_indices_zero_based': indices,
            'exposures': len(indices), 'language': lang,
            'status': status, 'reason_codes': codes,
            'evidence_snippet': snippet, 'rationale': rationale,
            'source_urls': sources,
            'verification_scope': '主Agent逐条阅读全部原问答；按已确认名称替换并与既有600次loader曝光精确匹配。未执行改写、模型训练或独立盲审。PASS_INITIAL为内容工程初审，非训练批准。',
        })
    assert len(results) == 108
    assert sorted(i for row in results for i in row['snapshot_indices_zero_based']) == list(range(2000, 2600))
    (HERE / 'identity_review.jsonl').write_text(''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in results))
    statuses = collections.Counter(x['status'] for x in results)
    exposures = collections.Counter()
    for row in results:
        exposures[row['status']] += row['exposures']
    summary = {'reviewed_unique_templates': 108, 'mapped_exposures': 600,
               'template_status_counts': dict(statuses), 'exposure_status_counts': dict(exposures),
               'author_templates_requiring_provenance_clarification': 78,
               'product_name_only_initial_pass_lines': [22, 77],
               'training_approval': False, 'training_data_modified': False}
    (HERE / 'identity_review_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
