"""Use the established CPU-only runtime, retrieve evidence, and remove our Pod."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import subprocess
import tarfile

D = Path(__file__).resolve().parent
ROOT = D.parents[2]
OUT = D / 'cpu-check'
K = ['kubectl', '--context', 'lmas00-direct', '--request-timeout=30s']
NAME = 't008-v0114-cpu-20261021'


def call(*args, timeout=50):
    return subprocess.check_output(K + list(args), text=True, timeout=timeout)


def snapshot(name):
    obj = json.loads(call('-n', 'vllm', 'get', 'deployment', 'vllm', '-o', 'json'))
    value = {'recorded_at_utc': datetime.now(timezone.utc).isoformat(),
             'name': obj['metadata']['name'], 'uid': obj['metadata']['uid'],
             'generation': obj['metadata']['generation'],
             'spec_sha256': hashlib.sha256(json.dumps(obj['spec'], sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
             'replicas': obj['spec']['replicas'], 'ready': obj['status'].get('readyReplicas', 0),
             'available': obj['status'].get('availableReplicas', 0)}
    (OUT / name).write_text(json.dumps(value, indent=2) + '\n')
    return value


def main():
    assert not (OUT / 'report.json').exists(), 'Preserve prior CPU evidence before retrying'
    before = snapshot('uat-before.json')
    assert before['ready'] == before['available'] == before['replicas'] == 1
    assert not json.loads(call('-n', 'swift', 'get', 'pods', '--field-selector', 'metadata.name=' + NAME, '-o', 'json'))['items']
    relative = D.relative_to(ROOT).as_posix()
    files = [relative + '/' + f for f in ['train.jsonl', 'train-map.jsonl', 'identity-keys.json', 'identity_loss3.py',
             'training-config.json', 'statistics.json', 'manifest.json', 'evaluation-config.json',
             'evaluation/custom-system.txt', 'removed.jsonl', 'cpu-check/check_cpu.py']]
    files += ['stage1/variants/stage1-cpu-v0.1.13/train.jsonl',
              'stage1/variants/stage1-cpu-v0.1.13/identity-keys.json',
              'stage1/variants/stage1-cpu-v0.1.13/training-config.json',
              'stage1/variants/stage1-cpu-v0.1.13/evaluation/custom-system.txt',
              'stage1/variants/stage1-cpu-v0.1.10/cpu-check/report.json',
              'stage1/training/local_data_guard.py',
              'stage2/variants/identity-loss3-review/identity_loss3.py',
              'stage2/variants/identity-loss3-review/source',
              'stage2/diagnostics/thinking-chat-template-20261020/thinking-prefill.jinja']
    binding = {'dataset_sha256': hashlib.sha256((D / 'train.jsonl').read_bytes()).hexdigest(),
               'identity_keys_sha256': hashlib.sha256((D / 'identity-keys.json').read_bytes()).hexdigest(),
               'training_config_sha256': hashlib.sha256((D / 'training-config.json').read_bytes()).hexdigest(),
               'checker_sha256': hashlib.sha256((OUT / 'check_cpu.py').read_bytes()).hexdigest(),
               'pod_name': NAME, 'gpu_requested': False, 'uat_pause': False}
    (OUT / 'input-binding.json').write_text(json.dumps(binding, indent=2) + '\n')
    created = False
    try:
        print(call('create', '-f', str(OUT / 'pod-cpu.json')), flush=True)
        created = True
        for attempt in range(4):
            result = subprocess.run(K + ['-n', 'swift', 'wait', '--for=condition=Ready', 'pod/' + NAME, '--timeout=40s'],
                                    text=True, capture_output=True, timeout=50)
            print(result.stdout + result.stderr, flush=True)
            if result.returncode == 0:
                break
        else:
            raise RuntimeError('CPU Pod did not become Ready')
        pod = json.loads(call('-n', 'swift', 'get', 'pod', NAME, '-o', 'json'))
        runtime = {'pod_uid': pod['metadata']['uid'], 'node': pod['spec']['nodeName'],
                   'image_id': pod['status']['containerStatuses'][0]['imageID'],
                   'gpu_requested': False, 'resources': pod['spec']['containers'][0]['resources']}
        (OUT / 'runtime.json').write_text(json.dumps(runtime, indent=2) + '\n')
        with subprocess.Popen(['tar', '-C', str(ROOT), '-cf', '-', *files], stdout=subprocess.PIPE) as sender:
            subprocess.run(K + ['-n', 'swift', 'exec', '-i', NAME, '--', 'tar', '-C', '/tmp/v0114-check', '-xf', '-'],
                           stdin=sender.stdout, check=True, timeout=90)
            sender.stdout.close()
            assert sender.wait() == 0
        remote = '/tmp/v0114-check/' + relative + '/cpu-check'
        print('Running native CPU loader, encoder and mask checks.', flush=True)
        with (OUT / 'cpu-check.log').open('w') as log:
            done = subprocess.run(K + ['-n', 'swift', 'exec', NAME, '--', 'python3', remote + '/check_cpu.py'],
                                  stdout=log, stderr=subprocess.STDOUT, timeout=600)
        (OUT / 'cpu-exit.json').write_text(json.dumps({'returncode': done.returncode}) + '\n')
        done.check_returncode()
        bundle = OUT / 'results.tar'
        with bundle.open('wb') as output:
            subprocess.run(K + ['-n', 'swift', 'exec', NAME, '--', 'tar', '-C', remote, '-cf', '-',
                               'report.json', 'row-checks.jsonl', 'mask-probes.json', 'weight-mismatches.json'],
                           stdout=output, check=True, timeout=90)
        with tarfile.open(bundle) as archive:
            archive.extractall(OUT, filter='data')
        bundle.unlink()
        report = json.loads((OUT / 'report.json').read_text())
        print(json.dumps({k: report[k] for k in ['verified', 'rows', 'max_tokens', 'weight_mismatch_rows',
                                                'group_supervised_tokens_after', 'identity_supervised_share_after',
                                                'identity_weighted_token_share_after']}, ensure_ascii=False), flush=True)
    finally:
        if created:
            print(call('-n', 'swift', 'delete', 'pod', NAME, '--ignore-not-found', '--wait=false'), flush=True)
            for attempt in range(3):
                result = subprocess.run(K + ['-n', 'swift', 'wait', '--for=delete', 'pod/' + NAME, '--timeout=40s'],
                                        text=True, capture_output=True, timeout=50)
                if result.returncode == 0:
                    break
                print(result.stdout + result.stderr, flush=True)
        after = snapshot('uat-after.json')
        same = all(before[k] == after[k] for k in ['uid', 'generation', 'spec_sha256', 'replicas'])
        healthy = after['ready'] == after['available'] == after['replicas'] == 1
        gone = not json.loads(call('-n', 'swift', 'get', 'pods', '--field-selector', 'metadata.name=' + NAME, '-o', 'json'))['items']
        (OUT / 'uat-after-verification.json').write_text(json.dumps({'original_spec_equal': same,
            'before_ready': before['ready'], 'after_ready': after['ready'], 'after_available': after['available'],
            'gpu_requested': False, 'uat_mutation': False, 'cpu_pod_deleted': gone}) + '\n')
        assert same and healthy and gone


if __name__ == '__main__':
    main()
