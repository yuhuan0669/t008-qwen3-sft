#!/usr/bin/env python3
"""Real ms-swift CPU-only preprocessing audit; never load model weights/train.

Original JSONL is opened read-only. Output contains hashes/counts/row locators,
not conversation text. Uses the same AddLengthPreprocessor as SwiftSft.
"""
import argparse
import collections
import hashlib
import importlib.metadata
import inspect
import json
import pathlib
import time


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dataset', required=True)
    ap.add_argument('--model', default='/base')
    ap.add_argument('--out', required=True)
    ap.add_argument('--base-fingerprint', help='Reuse previous full-byte fingerprint of unchanged read-only /base')
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=False)
    import torch
    from datasets import Dataset
    from swift.model import get_processor
    from swift.template import get_template
    from swift.dataset import AddLengthPreprocessor, EncodePreprocessor
    from swift.pipelines.train.sft import SwiftSft
    from swift.arguments import SftArguments
    assert not torch.cuda.is_available(), 'CPU-only audit requires no CUDA'
    p = pathlib.Path(a.dataset)
    raw = p.read_bytes()
    rows = [json.loads(x) for x in raw.splitlines() if x.strip()]
    start = time.time()
    processor = get_processor(a.model, model_type='qwen3', download_model=False)
    # Initialize actual argument defaults, with CPU/reporting-only overrides.
    args = SftArguments(model=a.model,model_type='qwen3',template='qwen3',
                        dataset=[str(p)],max_length=2048,use_cpu=True,
                        report_to=['none'],add_version=False,
                        output_dir=str(out/'arguments-only-output'))
    kwargs = args.get_template_kwargs()
    assert kwargs['truncation_strategy']=='raise'
    kwargs.pop('max_length')
    template = get_template(processor, max_length=None, **kwargs)
    template.max_length = None  # get_template(None) otherwise chooses model max=40960.
    template.set_mode('train')
    bounded = get_template(processor, max_length=2048, **kwargs)
    bounded.set_mode('train')
    # Controlled role test proves prompt/user masking separately from data counts.
    synthetic = {'messages': [{'role':'system','content':'SYSTEM_MASK_SENTINEL_814927'},
                             {'role':'user','content':'USER_MASK_SENTINEL_592163'},
                             {'role':'assistant','content':'ANSWER_LOSS_SENTINEL_374829'}]}
    role_encoding=template.encode(synthetic)
    role_checks={}
    for msg in synthetic['messages']:
        needle=processor.encode(msg['content'],add_special_tokens=False)
        ids=role_encoding['input_ids']; labels=role_encoding['labels']
        hits=[i for i in range(len(ids)-len(needle)+1) if ids[i:i+len(needle)]==needle]
        assert len(hits)==1, (msg['role'],hits)
        start_idx=hits[0]
        observed=labels[start_idx:start_idx+len(needle)]
        ok=(all(x==-100 for x in observed) if msg['role']!='assistant' else observed==needle)
        assert ok, msg['role']
        role_checks[msg['role']]=dict(token_count=len(needle),start_token_index=start_idx,
                                     correctly_masked_or_supervised=ok)
    # Only controlled synthetic input is decoded; no source conversation text.
    (out/'synthetic_mask_test.json').write_text(json.dumps(dict(
        input=synthetic,formatted_text=processor.decode(role_encoding['input_ids']),
        input_ids=role_encoding['input_ids'],labels=role_encoding['labels'],
        role_checks=role_checks),ensure_ascii=False,indent=2)+'\n')
    records, errors = [], []
    encoded_hashes = []
    for i, row in enumerate(rows):
        try:
            enc = template.encode(row, return_length=True)
            ids, labels = enc['input_ids'], enc['labels']
            assert len(ids) == len(labels)
            assert all(l == -100 or l == t for t, l in zip(ids, labels))
            supervised = sum(l != -100 for l in labels)
            record = dict(original_row_index_zero_based=i, tokens=len(ids),
                          masked_tokens=len(ids)-supervised, supervised_tokens=supervised,
                          input_ids_sha256=digest(ids), labels_sha256=digest(labels),
                          exceeds_2048=len(ids)>2048,
                          labels_match_input_ids_at_supervised_positions=True)
            encoded_hashes.append(record['input_ids_sha256'])
            if supervised == 0:
                errors.append(dict(original_row_index_zero_based=i, reason='zero_supervised_tokens'))
            if len(ids)>2048:
                errors.append(dict(original_row_index_zero_based=i, reason='overlength', tokens=len(ids)))
            records.append(record)
        except Exception as e:
            errors.append(dict(original_row_index_zero_based=i, reason=type(e).__name__, detail=str(e)))
    with (out/'row_token_mask_audit.jsonl').open('w') as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False, sort_keys=True)+'\n')
    # Actual SwiftSft non-streaming/non-lazy/default delete preprocessing path.
    # Unknown row-index columns are not retained by RowPreprocessor; verify
    # membership by per-row encoded token hashes and independent lengths.
    ds = Dataset.from_list(rows)
    retained = AddLengthPreprocessor(bounded)(ds, num_proc=1, load_from_cache_file=False,
                                              strict=args.strict, batch_size=100)
    retained_records = []
    for row in retained:
        enc = bounded.encode(row, return_length=True)
        retained_records.append(dict(tokens=len(enc['input_ids']),
                                     input_ids_sha256=digest(enc['input_ids']),
                                     supervised_tokens=sum(x != -100 for x in enc['labels'])))
    expected = [r for r in records if not r['exceeds_2048']]
    actual_counts = collections.Counter(r['input_ids_sha256'] for r in retained_records)
    expected_counts = collections.Counter(r['input_ids_sha256'] for r in expected)
    assert actual_counts == expected_counts, 'Pipeline membership differs from explicit row audit'
    assert all(r['supervised_tokens'] > 0 for r in retained_records)
    # Store source excerpts that establish equivalence to actual training pipeline.
    sources = {'SwiftSft._encode_dataset': inspect.getsource(SwiftSft._encode_dataset),
               'SftArguments.get_template_kwargs': inspect.getsource(SftArguments.get_template_kwargs),
               'AddLengthPreprocessor': inspect.getsource(AddLengthPreprocessor),
               'EncodePreprocessor': inspect.getsource(EncodePreprocessor),
               'get_processor': inspect.getsource(get_processor),
               'template._encode_truncated': inspect.getsource(type(template)._encode_truncated)}
    (out/'swift_api_source.json').write_text(json.dumps(sources, indent=2))
    source_files={}
    for obj in [SwiftSft,SftArguments,AddLengthPreprocessor,get_processor,type(template)]:
        path=pathlib.Path(inspect.getfile(obj))
        source_files[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
    (out/'swift_source_file_hashes.json').write_text(json.dumps(source_files,indent=2)+'\n')
    # Exact same fingerprint schema/serialization as v1.2 run_identity.py.
    import sys
    sys.path.insert(0,'/work/code')
    from run_identity import base_fingerprint
    if a.base_fingerprint:
        base_files=json.loads(pathlib.Path(a.base_fingerprint).read_text())
        assert all((pathlib.Path(a.model)/x['path']).stat().st_size==x['size'] for x in base_files)
    else:
        base_files=base_fingerprint(a.model)
    (out/'base-files.json').write_text(json.dumps(base_files,ensure_ascii=False,indent=2)+'\n')
    model_files_sha256=hashlib.sha256(json.dumps(base_files,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    lengths = sorted(r['tokens'] for r in records)
    def q(frac):
        return lengths[round((len(lengths)-1)*frac)] if lengths else None
    summary = dict(schema='t008-real-swift-template-cpu-v1', dataset_path=str(p),
                   probe_script_sha256=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
                   dataset_sha256=hashlib.sha256(raw).hexdigest(),
                   versions={x: importlib.metadata.version(x) for x in
                             ['ms-swift','transformers','peft','torch','tokenizers','datasets']},
                   model_path=a.model, model_files_sha256=model_files_sha256,
                   base_fingerprint_reused_from=a.base_fingerprint,
                   model_config=json.loads((pathlib.Path(a.model)/'config.json').read_text()),
                   weights_loaded=False, cuda_available=torch.cuda.is_available(),
                   processor_class=type(processor).__name__, template_class=type(template).__name__,
                   template_type='qwen3', template_mode=template.mode, loss_scale=args.loss_scale,
                   actual_training_default_kwargs=args.get_template_kwargs(),
                   template_backend='swift', max_length=2048,
                   training_truncation_strategy='delete', template_truncation_strategy='raise',
                   rows_checked=len(rows), encoded_rows=len(records),
                   overlength_rows=sum(r['exceeds_2048'] for r in records),
                   zero_supervised_rows=sum(r['supervised_tokens']==0 for r in records),
                   actual_pipeline='SwiftSft._encode_dataset -> AddLengthPreprocessor -> template.encode',
                   actual_pipeline_retained_rows=len(retained), pipeline_membership_verified=True,
                   all_supervised_labels_match_input_ids=True,
                   all_rows_have_masked_tokens=all(r['masked_tokens']>0 for r in records),
                   synthetic_role_mask_checks=role_checks,
                   length_stats=dict(min=q(0),p50=q(.5),p90=q(.9),p95=q(.95),p99=q(.99),max=q(1)),
                   total_tokens=sum(lengths), total_supervised_tokens=sum(r['supervised_tokens'] for r in records),
                   elapsed_seconds=round(time.time()-start,3),
                   verified=(len(records)==len(rows) and not errors))
    (out/'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n')
    evidence={k:summary[k] for k in ['verified','dataset_sha256','model_files_sha256',
                                    'rows_checked','max_length','overlength_rows']}
    evidence['evidence_ref']=str(out/'summary.json')
    evidence['scope']='Real CPU template/length/mask evidence only; not source/identity/experiment/GPU approval'
    (out/'swift-template-evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
    (out/'exceptions.json').write_text(json.dumps(errors, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
