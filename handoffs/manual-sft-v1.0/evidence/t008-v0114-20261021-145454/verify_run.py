"""Verify completed training, paired requests, model bytes and restored UAT."""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import subprocess

D = Path(__file__).resolve().parent
ROOT = D.parents[2]
K = ['kubectl', '--context', 'lmas00-direct', '--request-timeout=30s']


def read(p):
    return json.loads(p.read_text())


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def call(*args):
    return subprocess.check_output(K + list(args), text=True, timeout=60)


def main():
    v = ROOT / 'stage1/variants/stage1-cpu-v0.1.14'
    frozen, cfg = read(v / 'training-config.json'), read(D / 'training-config.json')
    assert frozen['full_argv'] == cfg['full_argv']
    assert frozen['smoke_overrides'] == cfg['smoke_overrides']
    assert sha(v / 'train.jsonl') == cfg['dataset_sha256']
    assert read(D / 'cpu-report.json') == read(v / 'cpu-check/report.json')
    for p, digest in read(v / 'protected-inputs.json').items():
        assert sha(ROOT / p) == digest, p
    full, smoke = read(D / 'outputs/full/run_manifest.json'), read(D / 'outputs/smoke/run_manifest.json')
    assert full['training_verified'] and full['global_step'] == 83 and full['epoch'] == 1.0
    assert smoke['training_verified'] and smoke['global_step'] == 3
    assert full['command'] == read(D / 'expected-full-command.json')
    assert full['data_sha256'] == cfg['dataset_sha256'] and full['rows'] == 1325
    assert full['upload_status'] == 'VERIFIED'
    assert full['clearml_model_readback_sha256'] == full['adapter_package_sha256']
    local = read(D / 'model-local-copy.json')
    assert local['verified'] and sha(ROOT / local['path']) == full['adapter_package_sha256']
    e = D / 'evaluation'
    spec = read(e / 'spec.json')
    assert spec['training_data_sha256'] == full['data_sha256']
    assert spec['adapters']['t008-v0114']['files'] == {
        k: val for k, val in full['adapter_files'].items() if k in ['adapter_config.json', 'adapter_model.safetensors']}
    assert sha(e / 'custom-system.txt') == spec['system_sha256']
    assert sha(e / 'thinking-prefill.jinja') == spec['template_sha256']
    assert sha(e / 'scenarios.jsonl') == spec['scenarios_sha256']
    rows = [json.loads(x) for x in (e / 'results/results.jsonl').read_text().splitlines()]
    cases = [json.loads(x) for x in (e / 'scenarios.jsonl').read_text().splitlines()]
    expected = {(c['id'], mode, seed, model, 1)
                for c in cases for mode in spec['modes'] for seed in c['seeds'] for model in spec['models']}
    assert len(rows) == 120 and len({r['id'] for r in rows}) == 120
    assert {(r['case_id'], r['mode'], r['seed'], r['model'], r['turn']) for r in rows} == expected
    assert Counter(r['model'] for r in rows) == {'t008-base': 40, 't008-v0113': 40, 't008-v0114': 40}
    for row in rows:
        assert 'error' not in row and row['input_ids_verified']
        assert row['response']['model'] == row['model']
        assert row['response']['usage']['prompt_tokens'] == len(row['server_render']['token_ids'])
    assert read(e / 'results/complete.json')['count'] == 120
    assert read(e / 'results/complete.json')['results_sha256'] == sha(e / 'results/results.jsonl')
    assert read(e / 'mechanical-summary.json')['first_turn_groups_verified'] == 40
    before = read(D / 'vllm-before.json')
    after = json.loads(call('-n', 'vllm', 'get', 'deployment', 'vllm', '-o', 'json'))
    assert before['spec'] == after['spec'] and after['status']['readyReplicas'] == 1
    pods = json.loads(call('-n', 'vllm', 'get', 'pods', '-l', 'app=vllm', '-o', 'json'))['items']
    ready = [p for p in pods if not p['metadata'].get('deletionTimestamp') and
             p['status']['phase'] == 'Running' and all(x.get('ready') for x in p['status'].get('containerStatuses', []))]
    assert len(ready) == 1
    assert call('-n', 'vllm', 'exec', ready[0]['metadata']['name'], '--', 'python3', '-c',
                "import urllib.request;print(urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=8).status)").strip() == '200'
    external = subprocess.check_output(['curl', '--noproxy', '*', '--max-time', '15', '-sS', '-o', '/dev/null', '-w', '%{http_code}',
                                        'https://vllm.10.140.17.125.nip.io/health'], text=True)
    assert external == '200'
    remaining = json.loads(call('-n', 'swift', 'get', 'pods', '-l', 't008-run=' + D.name, '-o', 'json'))['items']
    assert not remaining, 'Task-owned temporary pods must be removed after collecting outputs'
    jobs = json.loads(call('-n', 'swift', 'get', 'jobs', '-l', 't008-run=' + D.name, '-o', 'json'))['items']
    assert not jobs
    (D / 'uat-restored.json').write_text(json.dumps(after, indent=2) + '\n')
    result = {'verified': True, 'recorded_at_utc': datetime.now(timezone.utc).isoformat(),
              'run_id': D.name, 'full_runs': 1, 'full_steps': 83, 'epoch': 1.0, 'smoke_steps': 3,
              'rows': 1325, 'frozen_data_unchanged': True, 'training_hyperparameters_unchanged': True,
              'exposures_and_loss_rules_unchanged': True, 'actual_command_matches': True,
              'clearml_model_readback_sha256_verified': True, 'local_adapter_sha256_verified': True,
              'development_requests': 120, 'identical_prompt_groups': 40,
              'original_uat_spec_equal': True, 'uat_ready_replicas': 1, 'internal_health': 200, 'external_health': 200,
              'temporary_pods_and_jobs_deleted': True, 'new_model_deployed': False,
              'english_evaluated': False, 'formal_holdout_executed': False,
              'quality_accepted': False, 'next_training_authorized': False,
              'dataset_sha256': cfg['dataset_sha256'], 'adapter_package_sha256': full['adapter_package_sha256']}
    (D / 'verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
