"""Native CPU preparation only; never load weights, create a Trainer or run a model.

Run after assemble.py and the candidate manifest have been prepared. Native
prepared-message identity aliases are measured here, then written to candidate
identity-keys.json. The unchanged plug-in reads those bindings during training.
"""
from collections import Counter, defaultdict
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import importlib
import importlib.metadata as md
import json
import math
from pathlib import Path
import re


OUT = Path(__file__).resolve().parent
D = OUT.parent
ROOT = D.parents[2]
P = D.parent / 'stage1-cpu-v0.1.22'
IDENTITY = {'swift/self-cognition', 't008/chinese-identity-v1', 't008/company-facts-v1'}
POSITIONING = {'t008/project-positioning-v1', 't008/business-evidence-v1',
               't008/company-boundary-v1'}
ENCODING_FIELDS = ('input_ids', 'labels', 'loss_scale')


def read(path):
    return json.loads(path.read_text())


def lines(path):
    return [json.loads(s) for s in path.read_text().splitlines()]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def category(source):
    return 'identity' if source in IDENTITY else 'positioning' if source in POSITIONING else 'generic'


def thinking_mode(row):
    # Preserve the parent report's source-mode definition, including history.
    return 'thinking' if any(
        m['role'] == 'assistant' and re.search(r'<think>\s*\S[\s\S]*?</think>', m['content'])
        for m in row['messages']) else 'nonthinking'


def with_shares(counter, totals):
    result = dict(counter)
    for key, output in [('supervised_tokens', 'supervised_token_share'),
                        ('weighted_token_units', 'weighted_token_share')]:
        result[output] = counter[key] / totals[key] if totals[key] else 0.0
    return result


def identity_binding(base, rows, captures, message_key):
    """Build keys only from raw identities and observed native plug-in inputs."""
    raw = {message_key(r['messages']) for r in rows if r['dataset'] in IDENTITY}
    assert raw and set(captures) == raw, 'Every unique identity must be captured'
    row_numbers = defaultdict(list)
    for line, row in enumerate(rows, 1):
        if row['dataset'] in IDENTITY:
            row_numbers[message_key(row['messages'])].append(line)
    aliases = []
    prepared = set()
    for raw_key in sorted(raw):
        messages = captures[raw_key]
        prepared_key = message_key(messages)
        prepared.add(prepared_key)
        if raw_key != prepared_key:
            aliases.append({'raw_messages_sha256': raw_key,
                            'prepared_messages_sha256': prepared_key,
                            'candidate_lines_one_based': row_numbers[raw_key],
                            'prepared_messages': messages})
    keys = raw | prepared
    binding = deepcopy(base)
    binding.update(identity_exposures=sum(len(v) for v in row_numbers.values()),
                   identity_sources=sorted(IDENTITY), unique_messages=len(raw),
                   raw_identity_message_sha256=sorted(raw),
                   identity_message_sha256=sorted(keys), matching_key_count=len(keys),
                   native_preprocessing_alias_count=len(keys - raw),
                   native_alias_status='CAPTURED_NATIVE_PREPARED_MESSAGES',
                   native_alias_source='native-identity-key-aliases.json')
    return binding, aliases, prepared


@contextmanager
def observe_native(loss_class, template_class):
    """Observe arguments/results without changing the registered loss behavior."""
    original_call = loss_class.__call__
    original_eos = template_class._add_dynamic_eos
    calls, eos = defaultdict(list), {}

    def observed_call(self, contexts, context_types, messages, **kwargs):
        calls[id(self)].append(deepcopy(messages))
        return original_call(self, contexts, context_types, messages, **kwargs)

    def observed_eos(ids, labels, scales, suffix):
        before = list(labels)
        result = original_eos(ids, labels, scales, suffix)
        positions = [i for i, (a, b) in enumerate(zip(before, labels))
                     if a == -100 and b != -100]
        assert all(scales[i] == 1.0 for i in positions)
        eos['positions'] = positions
        return result

    loss_class.__call__ = observed_call
    template_class._add_dynamic_eos = staticmethod(observed_eos)
    try:
        yield calls, eos
    finally:
        loss_class.__call__ = original_call
        template_class._add_dynamic_eos = staticmethod(original_eos)


def main():
    OUT.mkdir(exist_ok=True)
    save(OUT / 'report.json', {'verified': False, 'phase': 'STARTED_NATIVE_CPU_CHECK',
                              'training_started': False, 'inference_executed': False})
    import torch
    from transformers import HfArgumentParser
    from swift.arguments import SftArguments
    from swift.model import get_processor
    from swift.template import get_template
    from swift.template.base import Template
    from swift.pipelines.train.sft import SwiftSft

    spec, prior = read(D / 'training-config.json'), read(P / 'training-config.json')
    ref = read(P / 'cpu-check/report.json')
    assert ref['verified'] is True
    assert not torch.cuda.is_available() and not list(Path('/dev').glob('nvidia*'))
    assert not spec['execution_authorized'] and spec['new_lora'] and not spec['resume']
    assert [x.replace(D.name, P.name) for x in spec['full_argv']] == prior['full_argv']
    assert sha(D / 'train.jsonl') == spec['dataset_sha256']
    assert sha(P / 'train.jsonl') == spec['parent_dataset_sha256'] == ref['dataset_sha256']
    assert read(D / 'manifest.json')['files_sha256']['train.jsonl'] == spec['dataset_sha256']
    plugin_hash = sha(D / 'identity_loss3.py')
    assert plugin_hash == sha(P / 'identity_loss3.py'), 'Loss plug-in bytes changed'
    versions = {k: md.version(k) for k in ref['versions']}
    assert versions == ref['versions'], versions
    for name, expected_hash in ref['tokenizer_config_sha256'].items():
        assert sha(Path('/base') / name) == expected_hash, name
    sources = {}
    for name, expected_hash in ref['normalization_source_hashes'].items():
        sources[name] = sha(Path(importlib.import_module(name).__file__))
        assert sources[name] == expected_hash, name

    argv = [x.replace('/work/', str(ROOT) + '/') for x in spec['full_argv'][2:]]
    overrides = ['--use_cpu', 'true', '--report_to', 'none', '--add_version', 'false',
                 '--output_dir', str(OUT / 'args-only'), '--dataset_num_proc', '1']
    args, = HfArgumentParser(SftArguments).parse_args_into_dataclasses(argv + overrides)
    assert str(args.training_args.device) == 'cpu'
    assert args.loss_scale == 'default+t008_identity3_ignore_empty_think'
    assert args.system is None and args.max_length == 2048
    assert args.truncation_strategy == 'delete'
    assert args.preserve_thinking is False and not args.disable_ignore_empty_think
    assert getattr(SwiftSft._encode_dataset, '_t008_local_guard', False)
    import identity_loss3
    from identity_loss3 import message_key
    assert sha(Path(identity_loss3.__file__)) == plugin_hash

    rows, parents = lines(D / 'train.jsonl'), lines(P / 'train.jsonl')
    mapping, changes = lines(D / 'train-map.jsonl'), lines(D / 'changes.jsonl')
    quarantine = lines(D / 'quarantine.jsonl')
    assert len(parents) == prior['dataset_rows'] == ref['rows'] == 1047
    assert len(rows) == len(mapping) == spec['dataset_rows']
    assert len(rows) + len(quarantine) == len(parents)
    assert sum(r['dataset'] in IDENTITY for r in rows) == 234
    assert sum(r['dataset'] in IDENTITY for r in parents) == 234
    assert not any(m['role'] == 'system' for r in rows + parents for m in r['messages'])
    by_parent = {m['parent_line_one_based']: (i, m) for i, m in enumerate(mapping, 1)}
    changed = {x['parent_line_one_based']: x for x in changes}
    removed = {x['parent_line_one_based']: x for x in quarantine}
    assert len(by_parent) == len(mapping) and len(changed) == len(changes)
    assert len(removed) == len(quarantine) and not (set(by_parent) & set(removed))
    assert set(by_parent) | set(removed) == set(range(1, len(parents) + 1))
    assert set(changed) == set(removed) | {
        n for n, (_, m) in by_parent.items() if m['operation'] == 'one_exposure_to_nonthinking'}
    for n, q in removed.items():
        assert parents[n - 1] == q['record'] == changed[n]['before']
        assert changed[n]['operation'] == 'quarantine' and changed[n]['after'] is None
        assert parents[n - 1]['dataset'] not in IDENTITY, 'Identity exposure removed'

    expected = Counter(message_key(r['messages']) for r in rows)
    loaded, val = args.load_dataset()
    assert len(loaded) == len(rows)
    assert Counter(message_key(r['messages']) for r in loaded) == expected
    assert val is None or len(val) == 0
    processor = get_processor('/base', model_type='qwen3', download_model=False)
    new, old, unbounded, old_unbounded = [
        get_template(processor, **args.get_template_kwargs()) for _ in range(4)]
    templates = (new, old, unbounded, old_unbounded)
    assert len({id(t.loss_scale) for t in templates}) == len(templates)
    for t in templates:
        t.set_mode('train')
        assert t.loss_scale.is_binary_loss_scale is False
    unbounded.max_length = old_unbounded.max_length = None
    parent_keys = frozenset(read(P / 'identity-keys.json')['identity_message_sha256'])
    old.loss_scale.identity_keys = old_unbounded.loss_scale.identity_keys = parent_keys
    binding_before = read(D / 'identity-keys.json')
    raw_keys = {message_key(r['messages']) for r in rows if r['dataset'] in IDENTITY}
    assert raw_keys == set(binding_before['raw_identity_message_sha256'])
    assert binding_before['dataset_sha256'] == spec['dataset_sha256']
    assert binding_before['identity_exposures'] == 234

    im_start = processor.encode('<|im_start|>', add_special_tokens=False)[0]
    im_end = processor.encode('<|im_end|>', add_special_tokens=False)[0]
    think_open = processor.encode('<think>', add_special_tokens=False)
    think_close = processor.encode('</think>', add_special_tokens=False)
    assert len(think_open) == len(think_close) == 1
    think_open, think_close = think_open[0], think_close[0]
    headers = {role: processor.encode(role + '\n', add_special_tokens=False)
               for role in ('system', 'user', 'assistant')}
    audit, changed_checks, probes = [], [], []
    totals = {phase: Counter() for phase in ('before', 'after')}
    source_stats = {phase: defaultdict(Counter) for phase in totals}
    category_stats = {phase: defaultdict(Counter) for phase in totals}
    mode_stats = {phase: defaultdict(Counter) for phase in totals}
    segment_tokens = {phase: {part: Counter() for part in
                      ('thinking_content', 'answer_content', 'structure')} for phase in totals}
    dynamic_eos_counts = {phase: Counter() for phase in totals}
    cache = {'before': {}, 'after': {}}
    examples = {}

    with observe_native(type(new.loss_scale), Template) as (calls, eos):
        def native_encode(template, row):
            calls[id(template.loss_scale)].clear()
            eos.pop('positions', None)
            value = template.encode(deepcopy(row))
            observed = calls[id(template.loss_scale)]
            assert len(observed) == 1, 'Expected one native loss-scale call per text row'
            assert 'positions' in eos
            return value, deepcopy(observed[0]), list(eos['positions'])

        # Capture the exact arguments presented to the unchanged plug-in. No
        # string rewriting or guessed native normalization is used for aliases.
        captures = {}
        for row in rows:
            k = message_key(row['messages'])
            if row['dataset'] in IDENTITY and k not in captures:
                _, prepared, _ = native_encode(unbounded, row)
                captures[k] = prepared
        binding, aliases, prepared_keys = identity_binding(binding_before, rows, captures, message_key)
        binding.update(dataset_path=str((D / 'train.jsonl').relative_to(ROOT)),
                       dataset_sha256=spec['dataset_sha256'])
        alias_report = {'dataset_sha256': spec['dataset_sha256'],
                        'loss_plugin_sha256': plugin_hash, 'versions': versions,
                        'observation': 'Exact messages argument at native loss-scale __call__ entry',
                        'unique_raw_identities_captured': len(captures),
                        'unique_prepared_identity_keys': len(prepared_keys),
                        'new_matching_keys_beyond_raw': binding['native_preprocessing_alias_count'],
                        'aliases': aliases}
        save(D / 'native-identity-key-aliases.json', alias_report)
        save(D / 'identity-keys.json', binding)
        new_keys = frozenset(binding['identity_message_sha256'])
        new.loss_scale.identity_keys = unbounded.loss_scale.identity_keys = new_keys
        assert old.loss_scale.identity_keys == old_unbounded.loss_scale.identity_keys == parent_keys

        precheck, length_cache = [], {}
        for line, (row, m) in enumerate(zip(rows, mapping), 1):
            k = message_key(row['messages'])
            if k not in length_cache:
                value, _, _ = native_encode(unbounded, row)
                length_cache[k] = len(value['input_ids'])
            precheck.append({'line_one_based': line,
                             'parent_line_one_based': m['parent_line_one_based'],
                             'sample_id': m.get('sample_audit_id'), 'source': row['dataset'],
                             'tokens': length_cache[k]})
        overlength = [x for x in precheck if x['tokens'] > 2048]
        save(OUT / 'length-precheck.json', {'dataset_sha256': spec['dataset_sha256'],
             'rows': len(rows), 'overlength': overlength,
             'maximum': max(x['tokens'] for x in precheck)})
        if overlength:
            raise RuntimeError('No truncation permitted; revise identified records: '
                               + json.dumps(overlength, ensure_ascii=False))

        def encode(phase, row):
            k = message_key(row['messages'])
            if k in cache[phase]:
                return cache[phase][k]
            bounded, unlimited = (old, old_unbounded) if phase == 'before' else (new, unbounded)
            value, prepared, dynamic = native_encode(bounded, row)
            full, _, _ = native_encode(unlimited, row)
            assert all(value[f] == full[f] for f in ENCODING_FIELDS), (phase, k, 'truncation')
            ids, labels, weights = (value[f] for f in ENCODING_FIELDS)
            assert len(ids) == len(labels) == len(weights) <= 2048
            assert any(y != -100 for y in labels)
            assert all(y == -100 or x == y for x, y in zip(ids, labels))
            factor = 3.0 if row['dataset'] in IDENTITY else 1.0
            want = [0.0 if y == -100 else factor for y in labels]
            for i in dynamic:
                want[i] = 1.0
            assert weights == want, (phase, k, '0/1/3 weights', message_key(prepared))
            if row['dataset'] in IDENTITY:
                keys = parent_keys if phase == 'before' else new_keys
                assert message_key(prepared) in keys
            for i, token in enumerate(ids):
                if token == im_start:
                    end = ids.index(im_end, i + 1)
                    role = next((r for r, h in headers.items()
                                 if ids[i + 1:i + 1 + len(h)] == h), None)
                    assert role is not None, (phase, k, 'unknown chat header')
                    stop = end + 1 if role in ('system', 'user') else i + 1 + len(headers[role])
                    assert all(y == -100 for y in labels[i:stop]), (phase, k, 'prompt mask')
                elif token == think_open:
                    end = ids.index(think_close, i + 1)
                    if not processor.decode(ids[i + 1:end]).strip():
                        assert all(y == -100 for y in labels[i:end + 1]), (phase, k, 'empty think')
            supervised_text = processor.decode([y for y in labels if y != -100])
            for message in row['messages']:
                if message['role'] != 'assistant':
                    continue
                body = message['content'].split('</think>', 1)[-1].strip()
                assert body and body in supervised_text, (phase, k, 'visible answer missing')
            assert im_end in [y for y in labels if y != -100]
            cache[phase][k] = (value, prepared, dynamic)
            return cache[phase][k]

        def accumulate(phase, row, value, dynamic):
            labels, weights = value['labels'], value['loss_scale']
            sup = sum(y != -100 for y in labels)
            units = sum(weights)
            measures = dict(rows=1, input_tokens=len(value['input_ids']),
                            supervised_tokens=sup, weighted_token_units=units)
            totals[phase].update({k: v for k, v in measures.items() if k != 'rows'})
            source_stats[phase][row['dataset']].update(measures)
            category_stats[phase][category(row['dataset'])].update(measures)
            mode_stats[phase][thinking_mode(row)].update(measures)
            dynamic_eos_counts[phase][category(row['dataset'])] += len(dynamic)
            inside = False
            for token, y, w in zip(value['input_ids'], labels, weights):
                if token == think_open:
                    part, inside = 'structure', True
                elif token == think_close:
                    part, inside = 'structure', False
                elif token in (im_start, im_end):
                    part, inside = 'structure', False
                else:
                    part = 'thinking_content' if inside else 'answer_content'
                if y != -100:
                    segment_tokens[phase][part].update(supervised_tokens=1, weighted_token_units=w)

        for row in parents:
            value, _, dynamic = encode('before', row)
            accumulate('before', row, value, dynamic)
        assert dict(totals['before']) == ref['totals']['after'], 'Parent baseline does not reproduce'
        unchanged = identity_count = identity_repairs = 0
        for line, (row, m) in enumerate(zip(rows, mapping), 1):
            parent_line = m['parent_line_one_based']
            before = parents[parent_line - 1]
            prev, _, _ = encode('before', before)
            cur, prepared, dynamic = encode('after', row)
            assert m['line_one_based'] == line and m['row_zero_based'] == line - 1
            assert m['parent_version'] == P.name and m['parent_row_zero_based'] == parent_line - 1
            assert m['messages_sha256'] == message_key(row['messages'])
            assert m['parent_messages_sha256'] == message_key(before['messages'])
            assert row['dataset'] == before['dataset']
            accumulate('after', row, cur, dynamic)
            if m['operation'] == 'preserve':
                assert row == before and all(cur[f] == prev[f] for f in ENCODING_FIELDS)
                unchanged += 1
            else:
                assert m['operation'] == 'one_exposure_to_nonthinking'
                change = changed[parent_line]
                assert change['operation'] == 'one_exposure_to_nonthinking' and change['before'] == before and change['after'] == row
                assert [x['role'] for x in row['messages']] == [x['role'] for x in before['messages']]
                assert [x for x in row['messages'] if x['role'] != 'assistant'] == [
                    x for x in before['messages'] if x['role'] != 'assistant']
                assert thinking_mode(row) == 'nonthinking' and thinking_mode(before) == 'thinking'
                assert row['messages'][1]['content'].split('</think>',1)[1] == before['messages'][1]['content'].split('</think>',1)[1]
                assert row['dataset'] == 'swift/Qwen3-SFT-Mixin' and m['language'] == 'zh'
                changed_checks.append({'sample_id': m['sample_audit_id'],
                    'source': row['dataset'], 'parent_line_one_based': parent_line,
                    'candidate_line_one_based': line, 'same_prompt_and_roles': True,
                    'converted_thinking_to_nonthinking': True, 'visible_body_bytes_preserved': True, 'full_encoding_no_truncation': True,
                    'expected_factor': 3.0 if row['dataset'] in IDENTITY else 1.0,
                    'before_input_tokens': len(prev['input_ids']), 'after_input_tokens': len(cur['input_ids']),
                    'before_supervised_tokens': sum(y != -100 for y in prev['labels']),
                    'after_supervised_tokens': sum(y != -100 for y in cur['labels']),
                    'before_weighted_token_units': sum(prev['loss_scale']),
                    'after_weighted_token_units': sum(cur['loss_scale']),
                    'weights_verified': True})
                probes.append({'sample_id': m['sample_audit_id'], 'line_one_based': line,
                    'prepared_messages_sha256': message_key(prepared),
                    'native_dynamic_eos_positions_weight1': dynamic,
                    'input_ids': cur['input_ids'], 'labels': cur['labels'], 'loss_scale': cur['loss_scale'],
                    'supervised_text': processor.decode([y for y in cur['labels'] if y != -100])})
            if row['dataset'] in IDENTITY:
                identity_count += 1
                identity_repairs += m['operation'] == 'one_exposure_to_nonthinking'
            examples.setdefault(row['dataset'], cur)
            audit.append({'line_one_based': line, 'parent_line_one_based': parent_line,
                'sample_id': m.get('sample_audit_id'), 'source': row['dataset'],
                'category': category(row['dataset']), 'mode': thinking_mode(row),
                'operation': m['operation'], 'encoded_tokens': len(cur['input_ids']),
                'supervised_tokens': sum(y != -100 for y in cur['labels']),
                'weighted_token_units': sum(cur['loss_scale']), 'weight_verified': True,
                'native_dynamic_eos_positions_weight1': dynamic,
                'prepared_messages_sha256': message_key(prepared),
                'unchanged_full_encoding_verified': m['operation'] == 'preserve'})
        assert unchanged == 983 and len(changed_checks) == 64 and identity_count == 234 and identity_repairs == 0

        class PreparationOnly:
            def _save_val_dataset(self, value):
                assert value is None or len(value) == 0

        stub = PreparationOnly()
        stub.args, stub.template = args, new
        encoded, validation = SwiftSft._encode_dataset(stub, loaded, val)
        assert len(encoded) == len(rows)
        assert Counter(message_key(r['messages']) for r in encoded) == expected
        assert validation is None or len(validation) == 0

    for phase in totals:
        for measure in ('supervised_tokens', 'weighted_token_units'):
            assert sum(x[measure] for x in segment_tokens[phase].values()) == totals[phase][measure]
            for partition in (source_stats, category_stats, mode_stats):
                assert sum(x[measure] for x in partition[phase].values()) == totals[phase][measure]
    batch = new.data_collator(list(examples.values()))
    assert set(batch['loss_scale'].unique().tolist()) == {0.0, 1.0, 3.0}
    assert torch.equal(batch['labels'] != -100, batch['loss_scale'] > 0)
    assert sha(D / 'identity_loss3.py') == sha(P / 'identity_loss3.py') == plugin_hash
    assert read(D / 'identity-keys.json') == binding
    lengths = sorted(x['encoded_tokens'] for x in audit)
    summarize = lambda partition: {phase: {
        name: with_shares(counts, totals[phase]) for name, counts in groups.items()
    } for phase, groups in partition.items()}
    report = {'verified': True, 'data_version': D.name,
        'dataset_sha256': spec['dataset_sha256'], 'parent_dataset_sha256': spec['parent_dataset_sha256'],
        'parent_report_sha256': sha(P / 'cpu-check/report.json'),
        'rows': len(rows), 'actual_loader_rows': len(loaded), 'actual_pipeline_rows': len(encoded),
        'parent_rows': len(parents), 'changed_rows': len(changed_checks),
        'quarantined_rows': len(quarantine), 'unchanged_full_encoding_rows': unchanged,
        'identity_exposures': identity_count, 'identity_repaired_exposures': identity_repairs,
        'max_tokens': max(lengths), 'p99_tokens': lengths[math.ceil(.99 * len(lengths)) - 1],
        'overlength_rows': 0, 'truncated_rows': 0, 'silent_dropped_rows': 0, 'empty_supervision_rows': 0,
        'totals': {phase: dict(counts) for phase, counts in totals.items()},
        'source_supervision': summarize(source_stats),
        'category_supervision': summarize(category_stats), 'mode_supervision': summarize(mode_stats),
        'mode_definition': 'Source contains a nonempty assistant think block in any turn, as in parent report; token counts use native masks.',
        'category_definition': {'identity': sorted(IDENTITY), 'positioning': sorted(POSITIONING),
                                'generic': 'All remaining source labels'},
        'segment_tokens': {phase: {part: with_shares(counts, totals[phase])
                           for part, counts in parts.items()} for phase, parts in segment_tokens.items()},
        'segment_definition': ref['segment_definition'],
        'weighted_share_note': 'Token units after loss scaling, not measured loss or gradient contribution.',
        'identity_weighted_token_units': {phase: category_stats[phase]['identity']['weighted_token_units']
                                           for phase in totals},
        'unchanged_rows_compared_with_separate_parent_and_candidate_bindings': True,
        'all_identity_answer_weights_verified3': True, 'prompt_and_empty_think_masked': True,
        'all_visible_answers_supervised': True, 'collator_preserves_0_1_3_weights': True,
        'native_dynamic_eos_supervised_token_counts_weight1': {
            phase: dict(counts) for phase, counts in dynamic_eos_counts.items()},
        'native_dynamic_eos_note': 'Native intermediate-turn terminators added after loss scaling have weight1; identity final suffix remains weight3 under unchanged plug-in.',
        'identity_key_binding_sha256': sha(D / 'identity-keys.json'),
        'parent_identity_key_binding_sha256': sha(P / 'identity-keys.json'),
        'native_identity_alias_evidence_sha256': sha(D / 'native-identity-key-aliases.json'),
        'raw_identity_matching_key_count': len(raw_keys),
        'native_identity_matching_key_count': len(prepared_keys),
        'native_preprocessing_alias_count': binding['native_preprocessing_alias_count'],
        'loss_plugin_sha256': plugin_hash, 'loss_plugin_source_unchanged': True,
        'normalization': ref['normalization'], 'normalization_source_hashes': sources,
        'tokenizer_config_sha256': ref['tokenizer_config_sha256'], 'versions': versions,
        'template_kwargs': args.get_template_kwargs(), 'cpu_overrides': overrides,
        'training_hyperparameters_unchanged': True,
        'estimated_full_optimizer_steps': math.ceil(len(rows) / 16),
        'model_weights_loaded': False, 'trainer_created': False, 'optimizer_created': False,
        'training_started': False, 'inference_executed': False, 'gpu_available': False,
        'backward_called': False, 'clearml_task_created': False}
    save(OUT / 'changed-row-checks.json', changed_checks)
    save(OUT / 'mask-probes.json', probes)
    (OUT / 'row-checks.jsonl').write_text(''.join(json.dumps(x) + '\n' for x in audit))
    save(OUT / 'report.json', report)
    print(json.dumps({'verified': True, 'rows': len(rows), 'changed': len(changed_checks),
                      'identity_repairs': identity_repairs, 'max_tokens': max(lengths),
                      'native_aliases': binding['native_preprocessing_alias_count'],
                      'totals': report['totals']}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
