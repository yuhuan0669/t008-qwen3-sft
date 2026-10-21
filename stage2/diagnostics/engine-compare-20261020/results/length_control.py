"""Two additional native CLI controls: same fresh seed as the 2048 runs, cap=1024."""
import json
import os
import subprocess
from commands import commands, D

assert json.loads((D / 'run-state.json').read_text())['status'] == 'COMPLETE'
for group, args in commands():
    if not group.endswith('-2048'):
        continue
    model = group.split('-')[0]
    name = model + '-nonthinking-1024-control'
    args[args.index('--max_new_tokens') + 1] = '1024'
    args[args.index('--result_path') + 1] = str(D / f'swift-{name}.jsonl')
    path = D / f'swift-raw-{name}.jsonl'
    assert not path.exists()
    env = dict(os.environ, T008_CAPTURE_PATH=str(path))
    with (D / f'swift-{name}.log').open('w') as log:
        subprocess.run(['swift', 'infer', *args], env=env, stdout=log,
                       stderr=subprocess.STDOUT, check=True, timeout=300)
    assert len(path.read_text().splitlines()) == 1
    print('Completed paired length control: ' + model, flush=True)
(D / 'length-control-complete.json').write_text(json.dumps({'status': 'COMPLETE', 'extra_requests': 2}) + '\n')
