"""Read-only cluster/service/GPU audit. No Kubernetes mutations or training."""
import concurrent.futures
import copy
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT.parent / 't008_qwen3_sft_v12_cpu'
CONTEXT = 'lmas00-direct'


def run(argv):
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=35)
        return {'argv': argv, 'exit_code': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr[:2000]}
    except subprocess.TimeoutExpired:
        return {'argv': argv, 'exit_code': None, 'error': 'timeout_35s'}


def kube(*args):
    result = run(['kubectl', '--context', CONTEXT, '--request-timeout=20s', *args, '-o', 'json'])
    if result['exit_code'] != 0:
        raise RuntimeError(result)
    return json.loads(result['stdout'])


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def redacted_env_spec(spec):
    result = copy.deepcopy(spec)
    for c in result['template']['spec'].get('containers', []):
        for env in c.get('env', []):
            if 'value' in env:
                env['value'] = '[REDACTED]'
    return result


def deployment(ns, name):
    obj = kube('-n', ns, 'get', 'deployment', name)
    podspec = obj['spec']['template']['spec']
    old = json.loads((OLD / 'evidence' / (ns + '_before.json')).read_text())
    def safe_container(c):
        env = []
        for e in c.get('env', []):
            env.append({'name': e['name'], 'source': e.get('valueFrom') or 'literal_value_omitted'})
        return {'name': c['name'], 'image': c['image'], 'command': c.get('command'),
                'args': c.get('args'), 'resources': c.get('resources'),
                'volumeMounts': c.get('volumeMounts'), 'env_names_and_refs_only': env}
    return {'namespace': ns, 'name': name, 'uid': obj['metadata']['uid'],
            'generation': obj['metadata'].get('generation'),
            'resource_version': obj['metadata']['resourceVersion'],
            'spec_sha256': canonical_hash(obj['spec']),
            'redacted_spec_matches_original_cpu_session': redacted_env_spec(obj['spec']) == redacted_env_spec(old['spec']),
            'historical_literal_env_values_comparable': False,
            'replicas': obj['spec'].get('replicas'), 'ready_replicas': obj['status'].get('readyReplicas', 0),
            'serviceAccountName': podspec.get('serviceAccountName'),
            'nodeSelector': podspec.get('nodeSelector'),
            'containers': [safe_container(c) for c in podspec['containers']],
            'volumes': podspec.get('volumes')}


def pods(ns):
    obj = kube('-n', ns, 'get', 'pods')
    return [{'name': p['metadata']['name'], 'uid': p['metadata']['uid'],
             'phase': p['status'].get('phase'), 'node': p['spec'].get('nodeName'),
             'containers': [{'name': c['name'], 'ready': c.get('ready'), 'restartCount': c.get('restartCount'),
                             'imageID': c.get('imageID'), 'state': c.get('state')}
                            for c in p['status'].get('containerStatuses', [])]}
            for p in obj['items']]


def pvc(ns):
    obj = kube('-n', ns, 'get', 'pvc')
    return [{'name': p['metadata']['name'], 'phase': p['status'].get('phase'),
             'volumeName': p['spec'].get('volumeName'), 'storageClassName': p['spec'].get('storageClassName'),
             'capacity': p['status'].get('capacity'), 'accessModes': p['spec'].get('accessModes')}
            for p in obj['items']]


def workloads(ns):
    obj = kube('-n', ns, 'get', 'deployments,statefulsets,jobs')
    return [{'kind': p['kind'], 'name': p['metadata']['name'],
             'replicas': p['spec'].get('replicas'), 'status': p.get('status')}
            for p in obj['items']]


def nodes():
    obj = kube('get', 'nodes')
    return [{'name': p['metadata']['name'], 'capacity_gpu': p['status']['capacity'].get('nvidia.com/gpu', '0'),
             'allocatable_gpu': p['status']['allocatable'].get('nvidia.com/gpu', '0'),
             'conditions': [{'type': c['type'], 'status': c['status']} for c in p['status']['conditions']]}
            for p in obj['items']]


def main():
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    checks = {
        'vllm_deployment': lambda: deployment('vllm', 'vllm'),
        'swift_deployment': lambda: deployment('swift', 'swift'),
        'vllm_pods': lambda: pods('vllm'), 'swift_pods': lambda: pods('swift'),
        'clearml_pods': lambda: pods('clearml'),
        'swift_pvcs': lambda: pvc('swift'), 'clearml_pvcs': lambda: pvc('clearml'),
        'clearml_workloads': lambda: workloads('clearml'), 'swift_workloads': lambda: workloads('swift'),
        'nodes': nodes,
        'gpu_inventory': lambda: run(['kubectl', '--context', CONTEXT, '-n', 'vllm', 'exec', 'deploy/vllm', '--',
                                     'nvidia-smi', '--query-gpu=uuid,name,memory.total,memory.used,utilization.gpu', '--format=csv,noheader']),
        'gpu_processes': lambda: run(['kubectl', '--context', CONTEXT, '-n', 'vllm', 'exec', 'deploy/vllm', '--',
                                     'nvidia-smi', '--query-compute-apps=pid,process_name,used_memory', '--format=csv,noheader']),
    }
    for label, url in {'vllm_health': 'https://vllm.10.140.17.125.nip.io/health',
                       'clearml_api_health': 'https://clearml.10.140.17.125.nip.io/api/debug.ping',
                       'clearml_files_https': 'https://clearml.10.140.17.125.nip.io/files/'}.items():
        checks[label] = lambda url=url: run(['/usr/bin/curl', '--silent', '--show-error', '--max-time', '15',
                                             '--output', '/dev/null', '--write-out', '%{http_code} %{ssl_verify_result}', url])
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        pending = {pool.submit(fn): name for name, fn in checks.items()}
        for future in concurrent.futures.as_completed(pending):
            name = pending[future]
            try:
                value = future.result()
                results[name] = {'ok': not isinstance(value, dict) or 'exit_code' not in value or value['exit_code'] == 0, 'result': value}
            except Exception as e:
                results[name] = {'ok': False, 'error': str(e)[:2000]}
    # Re-read deployment specs at end; reading itself must not change services.
    after = {}
    for ns in ('vllm', 'swift'):
        obj = kube('-n', ns, 'get', 'deployment', ns)
        after[ns] = {'spec_sha256': canonical_hash(obj['spec']),
                     'replicas': obj['spec'].get('replicas'), 'ready_replicas': obj['status'].get('readyReplicas', 0)}
        before = results.get(ns + '_deployment', {}).get('result', {})
        after[ns]['spec_unchanged_during_check'] = after[ns]['spec_sha256'] == before.get('spec_sha256')
    result = {'schema': 't008-official2048-readonly-live-check-v1', 'started_at_utc': started,
              'ended_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'context': CONTEXT, 'results': results, 'end_deployments': after,
              'kubernetes_mutations': False, 'gpu_training_started': False, 'clearml_objects_created': False}
    (ROOT / 'evidence/live_readonly_check.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'completed_checks': len(results), 'failed_checks': [k for k, v in results.items() if not v['ok']],
                      'end_deployments': after,
                      'gpu': results['gpu_inventory'], 'vllm_health': results['vllm_health']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
