"""Create an isolated runtime input directory; preserve prior datasets and runs."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import sys

payload = json.load(sys.stdin)
old = Path('/data/t008-v018-loss3-20261020-180616')
new = Path('/data') / payload['run']
work = Path('/work') / payload['run']
assert not new.exists() and not work.exists()
new.mkdir()
for name in ['code', 'deps', 'runtime-support', 'stage1/scripts', 'stage1/training']:
    source = old / name
    if source.exists():
        shutil.copytree(source, new / name, ignore=shutil.ignore_patterns('__pycache__'))
for name, text in payload['files'].items():
    target = new / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text)
train = new / 'stage1/data/train.jsonl'
assert hashlib.sha256(train.read_bytes()).hexdigest() == payload['sha']
work.mkdir()
for name in ['cache', 'tmp']:
    (work / name).mkdir()
for root in [new, work]:
    os.chown(root, 10001, 10001)
    for path in root.rglob('*'):
        if not path.is_symlink():
            os.chown(path, 10001, 10001)
checks = {name: hashlib.sha256((new / name).read_bytes()).hexdigest() for name in payload['files']}
print(json.dumps({'run': payload['run'], 'file_hashes': checks,
                  'data_sha256': payload['sha'], 'rows': len(train.read_text().splitlines())}))
