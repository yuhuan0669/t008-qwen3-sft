"""Read-only validation of completed training/generation and saved restoration evidence."""
from pathlib import Path
from collections import Counter
import hashlib
import json

D = Path(__file__).resolve().parent
ROOT = D.parents[2]
WS = ROOT.parent
V = ROOT / 'stage1/variants/stage1-cpu-v0.1.17'
E = D / 'evaluation'

def read(p):
    return json.loads(p.read_text())

def lines(p):
    return [json.loads(s) for s in p.read_text().splitlines()]

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def key(r):
    return tuple(r[x] for x in ('group', 'model', 'case_id', 'repeat'))

def main():
    frozen = read(V / 'FILES.sha256.json')
    for name, info in frozen.items():
        assert sha(V / name) == info['sha256'], name
    source_bindings = read(V / 'development/reuse-summary.json')['sources_sha256']
    for name, digest in source_bindings.items():
        assert sha(WS / name) == digest, name
    full = read(D / 'outputs/full/run_manifest.json')
    smoke = read(D / 'outputs/smoke/run_manifest.json')
    assert full['training_verified'] and full['training_exit_code'] == 0
    assert (full['global_step'], full['epoch'], full['rows']) == (85, 1.0, 1357)
    assert full['command'] == read(D / 'expected-full-command.json')
    assert full['data_sha256'] == sha(V / 'train.jsonl')
    assert smoke['global_step'] == 3 and smoke['training_exit_code'] == 0
    assert full['upload_status'] == 'VERIFIED'
    assert full['adapter_package_sha256'] == full['clearml_model_readback_sha256']
    local_model = ROOT / 'stage2/local-models/stage1-cpu-v0.1.17/adapter.zip'
    assert sha(local_model) == full['adapter_package_sha256']
    cfg = read(E / 'evaluation-config.json')
    cases = {c['id']: c for c in read(E / 'cases.json')['items']}
    assert sha(E / 'cases.json') == cfg['cases_sha256']
    assert sha(E / 'system.txt') == cfg['system_sha256']
    assert sha(E / 'thinking-prefill.jinja') == cfg['chat_template']['sha256']
    groups = {g['name']: g for g in cfg['groups']}
    aliases = read(E / 'runtime-binding.json')['aliases']
    planned = {(g['name'], m, q, r) for g in cfg['groups'] for m in cfg['models']
               for q in g['case_ids'] for r in range(1, g['repeats'] + 1)}
    new = lines(E / 'results.jsonl')
    saved = lines(E / 'reused-responses.jsonl')
    combined = lines(E / 'combined.jsonl')
    assert len(planned) == len(combined) == 2224
    assert set(map(key, combined)) == planned
    assert len(new) == 1158 and len(saved) == 1066
    assert set(map(key, new)) == set(map(key, read(E / 'missing-slots.json')))
    assert set(map(key, new)).isdisjoint(set(map(key, saved)))
    complete = read(E / 'complete.json')
    assert complete['status'] == 'COMPLETE' and complete['technical_retries'] == 0
    assert complete['attempts'] == 1158 and complete['results_sha256'] == sha(E / 'results.jsonl')
    schema_requests = Counter()
    for r in new:
        group, c = groups[r['group']], cases[r['case_id']]
        expected = dict(cfg['request_modes'][group['mode']])
        messages = [{'role': 'system', 'content': (E / 'system.txt').read_text()}] if group['system'] else []
        messages += c['messages']
        expected.update(model=aliases[r['model']], messages=messages)
        if c.get('json_schema'):
            expected['response_format'] = {'type': 'json_schema', 'json_schema': {
                'name': 't008_structured_answer', 'schema': c['json_schema'], 'strict': True}}
            schema_requests[r['model']] += 1
        assert r['request'] == expected, key(r)
        assert r['http_status'] == 200 and r['attempt'] == 1 and r['input_ids_verified']
        raw = E / r['raw_path']
        assert read(raw / 'request.json') == r['request']
        assert read(raw / 'response.raw.json') == r['response']
        assert key(read(raw / 'meta.json')) == key(r)
        assert len(r['response']['choices']) == 1
        assert r['response']['model'] == expected['model']
    assert schema_requests == Counter({m: 14 for m in cfg['models']})
    assert read(E / 'server-input-verification.json') == {'matched': 196, 'all_equal': True}
    schema = read(E / 'json-schema-check.json')
    assert schema['total'] == 56 and not schema['errors']
    state = read(D / 'window-state.json')
    before, restored = read(D / 'vllm-before.json'), read(D / 'uat-restored.json')
    assert state['restored'] and not state['paused'] and state['health_status'] == 200
    assert before['spec'] == restored['spec']
    public = read(D / 'public-restoration-verification.json')
    assert public['deployment_spec_equal'] and public['ready'] == public['available'] == 1
    assert len(public['public_health']) == 2 and all(c['status'] == 200 for c in public['public_health'])
    assert set(public['model_ids']) == {'octa-carbon-v1', 'octa-carbon-sft-v0114', 'octa-carbon-sft-v0116'}
    code = read(D / 'execution-code-binding.json')['code_sha256']
    changed = {name: {'before': digest, 'after': sha(D / name)} for name, digest in code.items() if sha(D / name) != digest}
    assert set(changed) == {'evaluation/prepare_review.py'}
    report = {'status': 'PASS', 'frozen_files_unchanged': len(frozen), 'historical_source_files_unchanged': len(source_bindings),
              'training': {'smoke_steps': 3, 'full_steps': 85, 'rows': 1357, 'epoch': 1, 'full_command_matches': True,
                           'adapter_sha256': full['adapter_files']['adapter_model.safetensors']['sha256'],
                           'local_and_clearml_package_verified': True},
              'generation': {'planned_slots': 2224, 'new': 1158, 'reused': 1066, 'raw_records_checked': 1158,
                             'technical_retries': 0, 'request_configuration_equal': True, 'rendered_inputs_matched': 196,
                             'schema_checked': 56, 'schema_errors': 0},
              'restoration': public, 'analysis_code_changes': changed,
              'analysis_change_reason': 'Rebalanced anonymous review shards after initial assignment; generation, labels and rubric were not changed by this partition update.',
              'limits': 'Execution integrity only; semantic quality is recorded separately. Reused generation times and batching differ.'}
    (D / 'execution-verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False))

if __name__ == '__main__':
    main()
