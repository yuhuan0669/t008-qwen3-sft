#!/usr/bin/env python3
"""Official ms-swift loader -> immutable local train snapshot; no custom oversampling/splitting.
Run in authorized CPU preparation environment. No model weights, GPU, training or hub writes.
"""
from __future__ import annotations
import argparse, hashlib, importlib.metadata, json, pathlib, re
from collections import Counter

SOURCES = ('swift/Qwen3-SFT-Mixin#2000', 'swift/self-cognition:qwen3#600')

def unresolved_placeholders(rows, identity_start=2000):
    """Official identity tokens are uppercase; Mixin contains valid Jinja code.
    In the identity segment also reject case variants of the identity keys.
    The real loader concatenates sources in the declared order (shuffle=False).
    """
    findings=[]
    for index,row in enumerate(rows):
        text=json.dumps(row,ensure_ascii=False)
        tokens=re.findall(r'\{\{\s*[A-Z_][A-Z0-9_]*\s*\}\}',text)
        if index>=identity_start:
            tokens+=re.findall(r'\{\{\s*(?:name|author|authoer)\s*\}\}',text,re.I)
        if tokens or 'swift-robot' in text:
            findings.append({'index':index,'tokens':sorted(set(tokens)),
                             'swift_robot':'swift-robot' in text})
    return findings

def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for part in iter(lambda:f.read(1024*1024), b''): h.update(part)
    return h.hexdigest()

def normal_row(row):
    msgs=row.get('messages')
    if not isinstance(msgs,list) or not msgs or msgs[-1].get('role')!='assistant':
        raise ValueError('Expected text messages ending in assistant')
    if not any(m.get('role')=='user' for m in msgs): raise ValueError('Missing user')
    for m in msgs:
        if m.get('role') not in {'system','user','assistant'} or not isinstance(m.get('content'),str):
            raise ValueError('Unsupported role/format: inspect real dataset instead of silently changing it')
    return {'messages':[{'role':m['role'],'content':m['content']} for m in msgs]}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--spec',required=True,help='identity-spec.json, already confirmed')
    p.add_argument('--out',required=True,help='new, nonexistent snapshot directory')
    p.add_argument('--seed',type=int,default=42)
    p.add_argument('--expected-mixin',type=int,default=2000)
    p.add_argument('--expected-identity',type=int,default=600)
    a=p.parse_args()
    spec=json.loads(pathlib.Path(a.spec).read_text(encoding='utf-8'))
    # Free-text notes are review guidance, NOT a model training field.
    # Exclude them from identity snapshot bytes to prevent false claims of effect.
    spec.pop('note', None)
    for field in ('name_zh','name_en','author_zh','author_en'):
        v=spec.get(field)
        if not isinstance(v,str) or not v.strip() or re.search(r'待填|待确认|填写|<.*>',v):
            raise ValueError(f'Confirm {field} before exporting identities')
    try:
        from swift.dataset import load_dataset
    except ImportError:
        from swift.llm import load_dataset
    # This is the official loader and its own #N sampling. Do not repeat, filter or
    # split a tiny identity set in an independent custom sampler.
    kwargs=dict(seed=a.seed,split_dataset_ratio=0,load_from_cache_file=False,
                use_hf=False,model_name=(spec['name_zh'],spec['name_en']),
                model_author=(spec['author_zh'],spec['author_en']))
    try:
        ds,val=load_dataset(list(SOURCES),**kwargs)
    except TypeError as e:
        raise RuntimeError('Pin ms-swift and adapt documented load_dataset API; do not drop metadata arguments') from e
    if val is not None and len(val): raise RuntimeError('Unexpected validation split')
    rows=[normal_row(dict(x)) for x in ds]
    expected=a.expected_mixin+a.expected_identity
    if len(rows)!=expected: raise RuntimeError(f'Expected {expected} total rows; got {len(rows)}')
    # The 2000/600 source attribution is guaranteed by the official specs, not by
    # individual row metadata. Do not fabricate source-by-source unique counts.
    text=''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in rows)
    if unresolved_placeholders(rows,a.expected_mixin):
        raise RuntimeError('Unreplaced identity placeholder detected (incl. AUTHOER typo)')
    out=pathlib.Path(a.out)
    if out.exists(): raise FileExistsError(out)
    out.mkdir(parents=True)
    (out/'train.jsonl').write_text(text,encoding='utf-8')
    (out/'identity_spec.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    counts=Counter(hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True).encode()).hexdigest() for x in rows)
    versions={}
    for name in ('ms-swift','datasets','modelscope'):
        try: versions[name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError: versions[name]=None
    manifest={'schema':'identity-official-snapshot-v1.2','status':'PENDING_SOURCE_REVIEW',
       'source_specs':list(SOURCES),'official_sampling':'ms-swift loader #N; seed recorded',
       'seed':a.seed,'rows':len(rows),'original_rows':len(rows),'requested_mixin':a.expected_mixin,
       'requested_identity':a.expected_identity,'snapshot_kind':'official_original',
       'unique_message_rows':len(counts),'duplicate_exposures':sum(v-1 for v in counts.values()),
       'repetition_histogram':dict(sorted(Counter(counts.values()).items())),
       'actual_source_revision':'NOT_PROVEN_BY_LOADER; archive original cache/repo revision separately',
       'versions':versions,'files_sha256':{n:sha(out/n) for n in ('train.jsonl','identity_spec.json')},
       'warning':'No held-out validation derived from repeated official identity templates. '
                 'Preflight with actual Qwen tokenizer/template and rights/use approval required before GPU run.'}
    (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'output':str(out),'rows':len(rows),'unique':len(counts),
                      'train_sha256':manifest['files_sha256']['train.jsonl']},ensure_ascii=False))
if __name__=='__main__': main()
