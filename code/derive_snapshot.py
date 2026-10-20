#!/usr/bin/env python3
"""Create a traceable exclusion-only derivative of the immutable 2600-row official snapshot.

Never edits source snapshots or automatically approves data changes. An independent
approval.json must match the derivative data/manifest hashes before any GPU run.
"""
from __future__ import annotations
import argparse, hashlib, json, pathlib
from collections import Counter
from prepare_official import sha


def make_derivative(parent, decisions, out):
    parent=pathlib.Path(parent); out=pathlib.Path(out)
    if out.exists(): raise FileExistsError(out)
    pm=json.loads((parent/'manifest.json').read_text(encoding='utf-8'))
    if pm.get('snapshot_kind')!='official_original' or pm.get('rows')!=2600:
        raise RuntimeError('Parent must be an original 2600-row v1.2 snapshot')
    for name,digest in pm['files_sha256'].items():
        if sha(parent/name)!=digest: raise RuntimeError(f'Parent checksum mismatch: {name}')
    lines=(parent/'train.jsonl').read_bytes().splitlines(keepends=True)
    if len(lines)!=2600: raise RuntimeError('Parent row count mismatch')
    changes=json.loads(pathlib.Path(decisions).read_text(encoding='utf-8'))
    if not isinstance(changes,list) or not changes or len(changes)>=2600:
        raise RuntimeError('Require nonempty exclusion list; cannot delete entire snapshot')
    idxs=set()
    for item in changes:
        if type(item.get('index'))!=int or not 0<=item['index']<2600 or item['index'] in idxs:
            raise ValueError('Index out of range, duplicate or invalid')
        if not isinstance(item.get('reason'),str) or len(item['reason'].strip())<8:
            raise ValueError('Each exclusion needs a meaningful reason')
        idxs.add(item['index'])
    changes=sorted(changes,key=lambda x:x['index'])
    retained=b''.join(line for i,line in enumerate(lines) if i not in idxs)
    out.mkdir(parents=True)
    (out/'train.jsonl').write_bytes(retained)
    (out/'identity_spec.json').write_bytes((parent/'identity_spec.json').read_bytes())
    (out/'exclusions.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    manifest=dict(pm)
    manifest.update(schema='identity-approved-snapshot-v1.2',status='PENDING_DERIVATIVE_APPROVAL',
                    snapshot_kind='approved_derivative',original_rows=2600,rows=2600-len(idxs),
                    parent_train_sha256=sha(parent/'train.jsonl'),
                    parent_manifest_sha256=sha(parent/'manifest.json'),
                    exclusions_sha256=sha(out/'exclusions.json'),
                    exclusions_count=len(idxs),
                    files_sha256={name:sha(out/name) for name in ('train.jsonl','identity_spec.json','exclusions.json')})
    rows=[json.loads(x) for x in retained.decode('utf-8').splitlines()]
    counts=Counter(hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True).encode()).hexdigest() for x in rows)
    manifest.update(unique_message_rows=len(counts),duplicate_exposures=sum(v-1 for v in counts.values()),
                    repetition_histogram=dict(sorted(Counter(counts.values()).items())))
    (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return manifest


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--parent',required=True);p.add_argument('--exclusions',required=True);p.add_argument('--out',required=True)
    a=p.parse_args()
    print(json.dumps({'result':make_derivative(a.parent,a.exclusions,a.out)['rows']},ensure_ascii=False))

if __name__=='__main__':main()
