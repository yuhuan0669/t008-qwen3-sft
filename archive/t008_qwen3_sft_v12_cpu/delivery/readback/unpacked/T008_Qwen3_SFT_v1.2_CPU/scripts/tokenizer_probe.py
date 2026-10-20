#!/usr/bin/env python3
"""Run baseline preflight_data.scan; reuse fully hashed read-only base manifest.

No baseline source is modified. Hash reuse is explicit evidence, not a new hash
measurement. All dataset checks and HF apply_chat_template are baseline code.
"""
import argparse
import hashlib
import json
import pathlib
import sys

ap=argparse.ArgumentParser()
ap.add_argument('--dataset',required=True)
ap.add_argument('--out',required=True)
ap.add_argument('--evidence')
ap.add_argument('--base-fingerprint',required=True)
a=ap.parse_args()
sys.path.insert(0,'/work/code')
import preflight_data
manifest_path=pathlib.Path(a.base_fingerprint)
files=json.loads(manifest_path.read_text())
for x in files:
    p=pathlib.Path('/base')/x['path']
    assert p.is_file() and not p.is_symlink() and p.stat().st_size==x['size']
preflight_data.base_fingerprint=lambda model: files
report=preflight_data.scan(a.dataset,'/base',a.evidence,2048)
report['base_fingerprint_reuse']={
    'source':str(manifest_path),
    'source_file_sha256':hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
    'basis':'Prior full-byte SHA256 of same read-only /base mount; current files/sizes rechecked',
    'baseline_source':preflight_data.__file__,
    'baseline_source_sha256':hashlib.sha256(pathlib.Path(preflight_data.__file__).read_bytes()).hexdigest()}
out=pathlib.Path(a.out)
with out.open('x') as f:
    f.write(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
