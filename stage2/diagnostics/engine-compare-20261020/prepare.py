"""Prepare a read-only Swift/vLLM diagnostic; never pauses UAT or starts inference."""
from pathlib import Path
import copy
import datetime
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
RUN = REPO / 'stage2/runs/t008-v018-loss3-20261020-180616'


def save(name, data):
    (ROOT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    cases = {r['id']: r for r in map(json.loads, (RUN / 'inputs/evaluation/development-24.jsonl').read_text().splitlines())}
    system = (RUN / 'inputs/evaluation/custom-system.txt').read_text()
    wanted = ['DEV-01', 'DEV-02', 'DEV-04', 'DEV-17', 'DEV-19', 'DEV-22', 'DEV-23']
    requests = []
    for case_id in wanted:
        assert len(cases[case_id]['user_turns']) == 1
        variants = ['none', 'existing'] if case_id in ['DEV-19', 'DEV-22', 'DEV-23'] else ['none']
        for variant in variants:
            messages = [{'role': 'system', 'content': system}] if variant == 'existing' else []
            messages.append({'role': 'user', 'content': cases[case_id]['user_turns'][0]})
            requests.append({'id': case_id + '__' + variant, 'case_id': case_id,
                             'system_variant': variant, 'messages': messages})
    for filename, rows in [('cases.jsonl', requests), ('length-case.jsonl', [r for r in requests if r['case_id'] == 'DEV-17'])]:
        (ROOT / filename).write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows))
    (ROOT / 'thinking-prefill.jinja').write_bytes((RUN / 'inputs/evaluation/thinking-prefill.jinja').read_bytes())
    manifest = json.loads((RUN / 'outputs/full/run_manifest.json').read_text())
    protocol = json.loads((RUN / 'inputs/evaluation/protocol.json').read_text())
    adapter = '/models-work/' + RUN.name + manifest['checkpoint'].removeprefix('/runwork')
    spec = {
        'purpose': 'Read-only development diagnosis, not training or formal acceptance',
        'models': {'base': '/base', 'loss3_adapter': adapter, 'adapter_files': manifest['adapter_files']},
        'modes': protocol['modes'], 'seed': 42, 'length_comparison': [1024, 2048],
        'requests_per_backend': 42, 'total_requests': 84,
        'backends': ['swift_infer_transformers', 'vllm_chat'],
        'template_sha256': sha(ROOT / 'thinking-prefill.jinja'),
        'versions': {k: manifest['versions'][k] for k in ['ms-swift', 'transformers', 'torch', 'peft']},
        'training': False, 'formal_holdout': False, 'data_or_weight_mutation': False,
        'uat_pause_approved': False,
        'comparison': 'Outcome and stop-reason comparison. Identical seeds do not imply identical draws across engines.',
    }
    save('spec.json', spec)
    pod = json.loads((REPO / 'stage2/diagnostics/identity-likelihood-20261020/pod-cpu.json').read_text())
    pod['metadata'] = {'name': 't008-engine-compare-20261020-cpu', 'namespace': 'swift',
                       'labels': {'t008-diagnostic': 'engine-compare-20261020'}}
    pod['spec']['activeDeadlineSeconds'] = 3600
    c = pod['spec']['containers'][0]
    c['command'] = ['python3', '-c', "import time;from pathlib import Path;Path('/tmp/engine-compare').mkdir(exist_ok=True);time.sleep(3500)"]
    c['env'] = [e for e in c['env'] if e['name'] not in ['SOURCE_GIT_COMMIT', 'CUDA_VISIBLE_DEVICES']]
    c['env'] += [{'name': 'CUDA_VISIBLE_DEVICES', 'value': ''}, {'name': 'NVIDIA_VISIBLE_DEVICES', 'value': 'void'}]
    save('pod-cpu.json', pod)
    gpu = copy.deepcopy(pod)
    gpu['metadata']['name'] = 't008-engine-compare-20261020-gpu'
    gpu['spec']['activeDeadlineSeconds'] = 3600
    gc = gpu['spec']['containers'][0]
    gc['env'] = [e for e in gc['env'] if e['name'] not in ['CUDA_VISIBLE_DEVICES', 'NVIDIA_VISIBLE_DEVICES']]
    gc['resources'] = {'requests': {'cpu': '4', 'memory': '16Gi', 'nvidia.com/gpu': '1'},
                       'limits': {'cpu': '8', 'memory': '32Gi', 'nvidia.com/gpu': '1'}}
    save('pod-gpu.json', gpu)
    k = ['kubectl', '--context', 'lmas00-direct', '--request-timeout=20s']
    before = json.loads(subprocess.check_output(k + ['-n', 'vllm', 'get', 'deployment', 'vllm', '-o', 'json']))
    save('uat-before.json', before)
    save('preflight.json', {'checked_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                           'uat_ready': before['status'].get('readyReplicas', 0),
                           'state': 'CPU_PREPARATION_ONLY', 'gpu_inference_started': False, 'uat_pause_approved': False})
    print(json.dumps({'prepared_requests': len(requests), 'total_generations': 84, 'adapter': adapter}))


if __name__ == '__main__':
    main()
