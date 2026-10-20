"""Recompute review membership without changing any frozen training artifacts.

Use --verify to compare existing review copies; --write writes review copies only.
The source record hash is canonical JSON (all original record fields).
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / 't008_qwen3_sft_v12_cpu'


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def read_rows(path):
    return [json.loads(s) for s in path.read_text().splitlines()]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    assert args.write != args.verify, 'Choose --write or --verify'
    raw = read_rows(BASE / 'work/upstream-raw/qwen3_32b_distill_1k.jsonl')
    snapshot = read_rows(BASE / 'work/original-v1.2/train.jsonl')
    audit = read_rows(BASE / 'evidence/template/original-final/row_token_mask_audit.jsonl')
    by_messages = collections.defaultdict(list)
    for i, row in enumerate(snapshot):
        by_messages[canonical(row['messages'])].append(i)
    selected = []
    for i, row in enumerate(raw):
        indices = by_messages[canonical(row['messages'])]
        assert len(indices) == 2
        assert all(audit[j]['original_row_index_zero_based'] == j for j in indices)
        assert len({audit[j]['tokens'] for j in indices}) == 1
        response = row['messages'][-1]['content']
        if '</think>' in response and 2048 < audit[indices[0]]['tokens'] <= 2560:
            selected.append({'source_line_one_based': i + 1,
                             'snapshot_indices_zero_based': indices,
                             'tokens': audit[indices[0]]['tokens'],
                             'supervised_tokens': audit[indices[0]]['supervised_tokens'],
                             'question': row['messages'][0]['content'],
                             'response': response,
                             'final_answer': response.split('</think>', 1)[1],
                             'source_record_sha256': hashlib.sha256(canonical(row).encode()).hexdigest()})
    assert len(selected) == 177
    for name, rows in [('mixin_all', selected), ('mixin_a', selected[:89]), ('mixin_b', selected[89:])]:
        payload = ''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows).encode()
        path = HERE / (name + '.jsonl')
        if args.write:
            path.write_bytes(payload)
        else:
            assert path.read_bytes() == payload, str(path)
    for filename, digest in json.loads((HERE / 'frozen_input_fingerprints.json').read_text()).items():
        assert hashlib.sha256(Path(filename).read_bytes()).hexdigest() == digest, filename
    print(json.dumps({'selected_unique_records': len(selected), 'selected_exposures': sum(len(r['snapshot_indices_zero_based']) for r in selected),
                      'source_max_tokens': max(r['tokens'] for r in selected),
                      'frozen_input_hashes_unchanged': True, 'mode': 'verify' if args.verify else 'write'}))


if __name__ == '__main__':
    main()
