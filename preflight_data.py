#!/usr/bin/env python3
"""CPU-only Qwen3 chat-template length scan; a *separate* real ms-swift evidence gate.

No truncation, no deletion and no model loading. tokenizer.apply_chat_template is a
necessary length precheck but not conclusive proof of the ms-swift training dataset
pipeline; execution must supply independently inspected ms-swift template evidence.
"""
from __future__ import annotations
import argparse, hashlib, json, pathlib, statistics
from collections.abc import Mapping
from run_identity import base_fingerprint, sha


def scan(dataset, model, swift_evidence=None, max_length=2048):
    from transformers import AutoTokenizer
    data=pathlib.Path(dataset);model=pathlib.Path(model)
    manifest_file=data/'manifest.json'
    manifest=json.loads(manifest_file.read_text(encoding='utf-8'))
    if manifest['files_sha256']['train.jsonl']!=sha(data/'train.jsonl'):
        raise RuntimeError('Dataset bytes differ from snapshot manifest')
    tok=AutoTokenizer.from_pretrained(str(model),local_files_only=True,trust_remote_code=False)
    counts=[];overs=[]
    with (data/'train.jsonl').open(encoding='utf-8') as source:
        for index,line in enumerate(source):
            row=json.loads(line)
            messages=row['messages']
            ids=tok.apply_chat_template(messages,tokenize=True,add_generation_prompt=False,
                                        truncation=False)
            if isinstance(ids,Mapping): ids=ids['input_ids']
            n=len(ids)
            counts.append(n)
            if n>max_length: overs.append({'index':index,'tokens':n})
    if not counts or len(counts)!=manifest['rows']:raise RuntimeError('Actual row count changed')
    files=base_fingerprint(model)
    base_sha=hashlib.sha256(json.dumps(files,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    evidence_checked=False
    evidence_sha=None
    evidence_ref=None
    if swift_evidence:
        efile=pathlib.Path(swift_evidence)
        e=json.loads(efile.read_text(encoding='utf-8'))
        if (e.get('verified') is not True or not isinstance(e.get('evidence_ref'),str) or
            not e.get('evidence_ref').strip() or e.get('dataset_sha256')!=sha(data/'train.jsonl') or
            e.get('model_files_sha256')!=base_sha or e.get('rows_checked')!=len(counts) or
            e.get('max_length')!=max_length or e.get('overlength_rows')!=0):
            raise RuntimeError('Actual ms-swift template evidence absent, incompatible or has overlength rows')
        evidence_checked=True
        evidence_sha=sha(efile)
        evidence_ref=e['evidence_ref']
    return {'schema':'identity-token-preflight-v1.2','dataset_sha256':sha(data/'train.jsonl'),
        'manifest_sha256':sha(manifest_file),'model_files_sha256':base_sha,
        'rows_checked':len(counts),'max_length':max_length,'overlength_rows':len(overs),
        'overlength_index_counts':overs,'min_tokens':min(counts),'max_tokens':max(counts),
        'mean_tokens':round(statistics.mean(counts),2),
        'template_tokenization_completed':True,'ms_swift_template_verified':evidence_checked,
        'ms_swift_template_evidence_sha256':evidence_sha,'ms_swift_evidence_ref':evidence_ref,
        'warning':'Transformers chat-template counts do NOT prove exact ms-swift dataset preprocessing; '
                  'ms-swift template evidence requires a real separate verification on matching image.'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset',required=True);p.add_argument('--model',required=True)
    p.add_argument('--out',help='Default: <dataset>/preflight_report.json')
    p.add_argument('--swift-template-evidence',help='Independent REAL ms-swift template inspection record')
    p.add_argument('--max-length',type=int,default=2048)
    a=p.parse_args()
    if a.max_length!=2048: raise ValueError('First experiment requires --max-length 2048')
    out=pathlib.Path(a.out) if a.out else pathlib.Path(a.dataset)/'preflight_report.json'
    if out.exists():raise FileExistsError(out)
    report=scan(a.dataset,a.model,a.swift_template_evidence,a.max_length)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'report':str(out),'rows':report['rows_checked'],
                      'overlength':report['overlength_rows'],
                      'swift_template_verified':report['ms_swift_template_verified']},ensure_ascii=False))

if __name__=='__main__':main()
